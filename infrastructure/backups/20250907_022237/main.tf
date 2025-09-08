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

  lifecycle_rules = length(var.s3_lifecycle_rules) > 0 ? {
    transition_to_ia_days      = var.s3_lifecycle_rules[0].days_to_ia
    noncurrent_expiration_days = var.s3_lifecycle_rules[0].days_to_expiration
    } : {
    transition_to_ia_days      = 30
    noncurrent_expiration_days = 365
  }

  cors_configuration = length(var.s3_cors_configuration) > 0 ? {
    allowed_headers = var.s3_cors_configuration[0].allowed_headers
    allowed_methods = var.s3_cors_configuration[0].allowed_methods
    allowed_origins = var.s3_cors_configuration[0].allowed_origins
    expose_headers  = var.s3_cors_configuration[0].expose_headers
    max_age_seconds = var.s3_cors_configuration[0].max_age_seconds
    } : {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "PUT", "POST"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }

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

  # 禁用内部部署，将在主配置中创建
  create_deployment = false

  # Initially create API Gateway without Lambda integrations
  lambda_integrations = {}

  tags = local.common_tags
}

# ============================================================================
# Layer 4: Lambda Functions (Depends on Layer 1-3)
# ============================================================================

# Lambda module with resolved dependencies
module "lambda" {
  source = "./modules/lambda"

  project_name = var.project_name
  aws_region   = var.aws_region

  # Required bucket and table names
  s3_bucket_name      = module.s3.bucket_name
  dynamodb_table_name = module.dynamodb.table_name

  # ARNs for IAM permissions
  s3_bucket_arn         = module.s3.bucket_arn
  dynamodb_table_arn    = module.dynamodb.table_arn
  checkpoints_table_arn = module.dynamodb.checkpoints_table_arn
  sqs_queue_url         = aws_sqs_queue.task_queue.url
  sqs_queue_arn         = aws_sqs_queue.task_queue.arn

  # Bedrock Agent IDs (use placeholders for now)
  orchestrator_agent_id = "placeholder-orchestrator-agent-id"
  orchestrator_alias_id = "placeholder-orchestrator-alias-id"
  content_agent_id      = "placeholder-content-agent-id"
  content_alias_id      = "placeholder-content-alias-id"
  visual_agent_id       = "placeholder-visual-agent-id"
  visual_alias_id       = "placeholder-visual-alias-id"
  compiler_agent_id     = "placeholder-compiler-agent-id"
  compiler_alias_id     = "placeholder-compiler-alias-id"

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

# Temporarily disabled due to parameter mismatch
# module "bedrock" {
#   source = "./modules/bedrock"
#   
#   project_name = var.project_name
#   environment  = var.environment
#   
#   model_id      = var.bedrock_model_id
#   model_version = var.bedrock_model_version
#   
#   # Agent configurations
#   agents = var.bedrock_agents
#   
#   # Lambda function ARNs for agent actions
#   lambda_function_arns = module.lambda.function_arns
#   
#   tags = local.common_tags
#   
#   depends_on = [module.lambda]
# }

# ============================================================================
# Layer 6: API Gateway Integration (Connect API to Lambda)
# ============================================================================

# Create API Gateway integrations separately after Lambda functions are created
resource "aws_api_gateway_integration" "create_presentation" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = module.api_gateway.resource_ids["presentations"]
  http_method = "POST"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.lambda.function_invoke_arns["generate_presentation"]

  timeout_milliseconds = 29000

  depends_on = [module.lambda, module.api_gateway]
}

resource "aws_api_gateway_integration" "get_presentation" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = module.api_gateway.resource_ids["presentation_id"]
  http_method = "GET"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.lambda.function_invoke_arns["presentation_status"]

  timeout_milliseconds = 10000

  depends_on = [module.lambda, module.api_gateway]
}

resource "aws_api_gateway_integration" "list_presentations" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = module.api_gateway.resource_ids["presentations"]
  http_method = "GET"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/${aws_lambda_function.list_presentations.arn}/invocations"

  timeout_milliseconds = 10000

  depends_on = [module.lambda, module.api_gateway]
}

resource "aws_api_gateway_integration" "create_session" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = module.api_gateway.resource_ids["sessions"]
  http_method = "POST"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.lambda.function_invoke_arns["generate_presentation"]

  timeout_milliseconds = 29000

  depends_on = [module.lambda, module.api_gateway]
}

resource "aws_api_gateway_integration" "get_session" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = module.api_gateway.resource_ids["session_id"]
  http_method = "GET"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.lambda.function_invoke_arns["presentation_status"]

  timeout_milliseconds = 10000

  depends_on = [module.lambda, module.api_gateway]
}

resource "aws_api_gateway_integration" "execute_agent" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = module.api_gateway.resource_ids["agent_execute"]
  http_method = "POST"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.lambda.function_invoke_arns["generate_presentation"]

  timeout_milliseconds = 29000

  depends_on = [module.lambda, module.api_gateway]
}

# ============================================================================
# Health Check Endpoints (no API key required)
# ============================================================================

# /health resource
resource "aws_api_gateway_resource" "health" {
  rest_api_id = module.api_gateway.rest_api_id
  parent_id   = module.api_gateway.rest_api_root_resource_id
  path_part   = "health"
}

# /health/ready resource
resource "aws_api_gateway_resource" "health_ready" {
  rest_api_id = module.api_gateway.rest_api_id
  parent_id   = aws_api_gateway_resource.health.id
  path_part   = "ready"
}

# GET /health method (no API key required)
resource "aws_api_gateway_method" "health_get" {
  rest_api_id      = module.api_gateway.rest_api_id
  resource_id      = aws_api_gateway_resource.health.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = false
}

# GET /health/ready method (no API key required)
resource "aws_api_gateway_method" "health_ready_get" {
  rest_api_id      = module.api_gateway.rest_api_id
  resource_id      = aws_api_gateway_resource.health_ready.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = false
}

# Mock integration for /health
resource "aws_api_gateway_integration" "health" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# Mock integration for /health/ready
resource "aws_api_gateway_integration" "health_ready" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.health_ready.id
  http_method = aws_api_gateway_method.health_ready_get.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# Method response for /health
resource "aws_api_gateway_method_response" "health_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

# Method response for /health/ready
resource "aws_api_gateway_method_response" "health_ready_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.health_ready.id
  http_method = aws_api_gateway_method.health_ready_get.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }
}

# Integration response for /health
resource "aws_api_gateway_integration_response" "health_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  status_code = aws_api_gateway_method_response.health_200.status_code

  response_templates = {
    "application/json" = jsonencode({
      status    = "healthy"
      timestamp = "$context.requestTime"
    })
  }

  depends_on = [
    aws_api_gateway_integration.health
  ]
}

# Integration response for /health/ready
resource "aws_api_gateway_integration_response" "health_ready_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.health_ready.id
  http_method = aws_api_gateway_method.health_ready_get.http_method
  status_code = aws_api_gateway_method_response.health_ready_200.status_code

  response_templates = {
    "application/json" = jsonencode({
      status    = "ready"
      timestamp = "$context.requestTime"
    })
  }

  depends_on = [
    aws_api_gateway_integration.health_ready
  ]
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "generate_presentation_permission" {
  statement_id  = "AllowAPIGatewayInvoke-generate-presentation"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.function_names["generate_presentation"]
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${module.api_gateway.rest_api_id}/*/*"

  depends_on = [module.lambda, module.api_gateway]
}

resource "aws_lambda_permission" "presentation_status_permission" {
  statement_id  = "AllowAPIGatewayInvoke-presentation-status"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.function_names["presentation_status"]
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${module.api_gateway.rest_api_id}/*/*"

  depends_on = [module.lambda, module.api_gateway]
}

# Create a new deployment to include the integrations
resource "aws_api_gateway_deployment" "integration_deployment" {
  rest_api_id = module.api_gateway.rest_api_id

  triggers = {
    # Redeploy when any integration changes
    redeployment = sha1(jsonencode([
      aws_api_gateway_integration.create_presentation,
      aws_api_gateway_integration.get_presentation,
      aws_api_gateway_integration.list_presentations,
      aws_api_gateway_integration.create_session,
      aws_api_gateway_integration.get_session,
      aws_api_gateway_integration.execute_agent,
      aws_api_gateway_integration.health,
      aws_api_gateway_integration.health_ready,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.create_presentation,
    aws_api_gateway_integration.get_presentation,
    aws_api_gateway_integration.list_presentations,
    aws_api_gateway_integration.create_session,
    aws_api_gateway_integration.get_session,
    aws_api_gateway_integration.execute_agent,
    aws_api_gateway_integration.health,
    aws_api_gateway_integration.health_ready,
  ]
}

# Create API Gateway Stage (since module doesn't create it when deployment is disabled)
resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.integration_deployment.id
  rest_api_id   = module.api_gateway.rest_api_id
  stage_name    = var.stage_name

  xray_tracing_enabled = true

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-api-stage"
    }
  )

  depends_on = [
    aws_api_gateway_deployment.integration_deployment
  ]
}

# Create Usage Plan (since module doesn't create it when deployment is disabled)
resource "aws_api_gateway_usage_plan" "main" {
  name        = "${var.project_name}-${var.environment}-usage-plan"
  description = "Usage plan for ${var.project_name} ${var.environment}"

  api_stages {
    api_id = module.api_gateway.rest_api_id
    stage  = aws_api_gateway_stage.main.stage_name
  }

  quota_settings {
    limit  = var.api_quota_limit
    period = var.api_quota_period
  }

  throttle_settings {
    rate_limit  = var.api_throttle_rate_limit
    burst_limit = var.api_throttle_burst_limit
  }

  tags = merge(
    local.common_tags,
    {
      Name        = "${var.project_name}-${var.environment}-usage-plan"
      Environment = var.environment
    }
  )

  depends_on = [
    aws_api_gateway_stage.main
  ]
}

# Associate API Key with Usage Plan
resource "aws_api_gateway_usage_plan_key" "main" {
  key_id        = module.api_gateway.api_key_id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.main.id
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

output "api_gateway_api_key" {
  description = "API Gateway API Key"
  value       = module.api_gateway.api_key_value
  sensitive   = true
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