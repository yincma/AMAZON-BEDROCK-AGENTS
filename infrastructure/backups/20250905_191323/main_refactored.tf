# AI PPT Assistant Infrastructure - Refactored Configuration
# This configuration resolves circular dependencies using a layered approach

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = var.owner
      CostCenter  = var.cost_center
    }
  }
}

# Data sources for account and region info
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values for consistent naming and tagging
locals {
  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = var.owner
      CostCenter  = var.cost_center
    },
    var.additional_tags
  )
  
  # Naming convention for resources
  name_prefix = "${var.project_name}-${var.environment}"
}

# Random ID for unique S3 bucket naming (import existing if it exists)
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# ============================================================================
# Layer 1: Foundation Resources (No dependencies)
# ============================================================================

# VPC Module - Foundation network layer
module "vpc" {
  source = "./modules/vpc"
  
  project_name = var.project_name
  environment  = var.environment
  
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  
  enable_vpc_endpoints = var.enable_vpc_endpoints
  enable_nat_gateway   = var.enable_nat_gateway
  
  enable_flow_logs        = var.enable_vpc_flow_logs
  flow_log_retention_days = var.vpc_flow_log_retention_days
  
  tags = local.common_tags
}

# ============================================================================
# Layer 2: Storage Resources (Minimal dependencies)
# ============================================================================

# S3 Module for presentation storage
module "s3" {
  source = "./modules/s3"
  
  project_name = var.project_name
  environment  = var.environment
  
  # Use the existing random suffix if importing existing bucket
  bucket_suffix = random_id.bucket_suffix.hex
  
  lifecycle_rules    = var.s3_lifecycle_rules
  cors_configuration = var.s3_cors_configuration
  
  tags = local.common_tags
}

# DynamoDB Module for session state
module "dynamodb" {
  source = "./modules/dynamodb"
  
  project_name = var.project_name
  environment  = var.environment
  
  ttl_attribute = "expiry"
  ttl_enabled   = true
  billing_mode  = var.dynamodb_billing_mode
  
  tags = local.common_tags
}

# SQS Queues for async processing
resource "aws_sqs_queue" "task_queue" {
  name = "${local.name_prefix}-tasks"
  
  visibility_timeout_seconds = 300
  message_retention_seconds  = 86400
  
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
  
  tags = local.common_tags
}

resource "aws_sqs_queue" "dlq" {
  name = "${local.name_prefix}-dlq"
  
  message_retention_seconds = 1209600 # 14 days
  
  tags = local.common_tags
}

# ============================================================================
# Layer 3: API Gateway (Independent of Lambda initially)
# ============================================================================

module "api_gateway" {
  source = "./modules/api_gateway"
  
  project_name = var.project_name
  environment  = var.environment
  
  api_description      = "API Gateway for AI PPT Assistant"
  throttle_rate_limit  = var.api_throttle_rate_limit
  throttle_burst_limit = var.api_throttle_burst_limit
  api_key_required     = true
  
  tags = local.common_tags
}

# ============================================================================
# Layer 4: Lambda Functions (Depends on Layer 1-3)
# ============================================================================

# Lambda module with resolved dependencies
module "lambda" {
  source = "./modules/lambda"
  
  project_name = var.project_name
  environment  = var.environment
  
  runtime      = "python3.13"
  architecture = var.lambda_architecture
  
  layer_name       = "${local.name_prefix}-shared-layer"
  lambda_functions = var.lambda_functions
  
  # VPC configuration (optional)
  enable_vpc_config      = var.enable_lambda_vpc_config
  vpc_id                 = module.vpc.vpc_id
  vpc_subnet_ids         = module.vpc.private_subnet_ids
  vpc_security_group_ids = [module.vpc.lambda_security_group_id]
  
  # Environment variables using module outputs
  environment_variables = {
    ENVIRONMENT          = var.environment
    BEDROCK_REGION       = var.bedrock_region
    S3_BUCKET           = module.s3.bucket_name
    DYNAMODB_TABLE      = module.dynamodb.table_name
    CHECKPOINTS_TABLE   = module.dynamodb.checkpoints_table_name
    SQS_QUEUE_URL       = aws_sqs_queue.task_queue.url
    API_GATEWAY_URL     = module.api_gateway.api_url
    LOG_LEVEL           = var.log_level
    VPC_ENABLED         = var.enable_lambda_vpc_config ? "true" : "false"
  }
  
  # Pass ARNs for IAM permissions
  s3_bucket_arn         = module.s3.bucket_arn
  dynamodb_table_arn    = module.dynamodb.table_arn
  checkpoints_table_arn = module.dynamodb.checkpoints_table_arn
  sqs_queue_arn         = aws_sqs_queue.task_queue.arn
  api_gateway_arn       = module.api_gateway.api_arn
  
  tags = local.common_tags
  
  # Explicit dependencies to ensure proper creation order
  depends_on = [
    module.vpc,
    module.s3,
    module.dynamodb,
    module.api_gateway
  ]
}

# ============================================================================
# Layer 5: Bedrock Agents (Depends on Lambda)
# ============================================================================

module "bedrock" {
  source = "./modules/bedrock"
  
  project_name = var.project_name
  environment  = var.environment
  
  model_id      = var.bedrock_model_id
  model_version = var.bedrock_model_version
  
  # Agent configurations
  agents = var.bedrock_agents
  
  # Lambda function ARNs for agent actions
  lambda_function_arns = module.lambda.function_arns
  
  tags = local.common_tags
  
  depends_on = [module.lambda]
}

# ============================================================================
# Layer 6: API Gateway Integration (Connect API to Lambda)
# ============================================================================

# API Gateway to Lambda integrations
# This is done separately to avoid circular dependencies
resource "aws_api_gateway_integration" "lambda_integrations" {
  for_each = var.lambda_functions
  
  rest_api_id = module.api_gateway.api_id
  resource_id = module.api_gateway.resource_ids[each.key]
  http_method = "POST"
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = module.lambda.function_invoke_arns[each.key]
  
  depends_on = [
    module.api_gateway,
    module.lambda
  ]
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_gateway_permissions" {
  for_each = var.lambda_functions
  
  statement_id  = "AllowAPIGatewayInvoke-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.function_names[each.key]
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${module.api_gateway.api_arn}/*/*"
  
  depends_on = [
    module.api_gateway,
    module.lambda
  ]
}

# ============================================================================
# Outputs
# ============================================================================

# Core infrastructure outputs
output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS Region"
  value       = data.aws_region.current.name
}

# VPC outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

# Storage outputs
output "s3_bucket_name" {
  description = "S3 Bucket Name"
  value       = module.s3.bucket_name
}

output "dynamodb_table_name" {
  description = "DynamoDB Table Name"
  value       = module.dynamodb.table_name
}

# API outputs
output "api_gateway_url" {
  description = "API Gateway URL"
  value       = module.api_gateway.api_url
}

# Lambda outputs
output "lambda_function_names" {
  description = "Lambda Function Names"
  value       = module.lambda.function_names
}

# SQS outputs
output "sqs_queue_url" {
  description = "SQS Queue URL"
  value       = aws_sqs_queue.task_queue.url
}