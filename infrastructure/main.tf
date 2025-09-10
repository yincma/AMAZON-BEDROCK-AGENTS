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
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
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

  visibility_timeout_seconds = 950  # Must be greater than task_processor Lambda timeout (900s)
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
  dynamodb_table_name = module.dynamodb.tasks_table_name

  # ARNs for IAM permissions
  s3_bucket_arn           = module.s3.bucket_arn
  dynamodb_table_arn      = module.dynamodb.tasks_table_arn
  checkpoints_table_name  = module.dynamodb.checkpoints_table_name
  checkpoints_table_arn   = module.dynamodb.checkpoints_table_arn
  sqs_queue_url         = aws_sqs_queue.task_queue.url
  sqs_queue_arn         = aws_sqs_queue.task_queue.arn

  # Bedrock model configuration
  bedrock_model_id = var.bedrock_model_id
  bedrock_orchestrator_model_id = var.bedrock_orchestrator_model_id
  nova_model_id = var.nova_model_id

  # Bedrock Agent IDs - Dynamically fetched from deployed agents
  orchestrator_agent_id = local.orchestrator_agent_id
  orchestrator_alias_id = local.orchestrator_alias_id
  content_agent_id      = local.content_agent_id
  content_alias_id      = local.content_alias_id
  visual_agent_id       = local.visual_agent_id
  visual_alias_id       = local.visual_alias_id
  compiler_agent_id     = local.compiler_agent_id
  compiler_alias_id     = local.compiler_alias_id

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

# Bedrock Agents Module - Now enabled with Terraform management
module "bedrock" {
  source = "./modules/bedrock"
  
  project_name = var.project_name
  aws_region   = var.aws_region
  
  # Agent configurations - using module default values with correct inference profiles
  # This will use the defaults defined in modules/bedrock/variables.tf
  
  # Lambda function ARNs for agent actions  
  lambda_function_arns = {
    orchestrator = {
      create_outline = module.lambda.function_arns["create_outline"]
    }
    content = {
      generate_content = module.lambda.function_arns["generate_content"]
    }
    visual = {
      generate_image = module.lambda.function_arns["generate_image"]
    }
    compiler = {
      compile_pptx = module.lambda.function_arns["compile_pptx"]
    }
  }
  
  # Required resources for agent permissions
  s3_bucket_arn      = module.s3.bucket_arn
  dynamodb_table_arn = module.dynamodb.tasks_table_arn
  
  tags = local.common_tags
  
  depends_on = [module.lambda, module.dynamodb, module.s3]
}

# ============================================================================
# Layer 5.5: SQS Lambda Event Source Mapping (Task Processing)
# ============================================================================
# Include the SQS Lambda mapping configuration
# This creates the task processor function and connects it to SQS
# Critical for async task processing

# Note: The configuration is in a separate file for modularity
# See: sqs_lambda_mapping.tf

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

resource "aws_api_gateway_integration" "download_presentation" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = module.api_gateway.resource_ids["presentation_download"]
  http_method = "GET"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.lambda.function_invoke_arns["presentation_download"]

  timeout_milliseconds = 10000

  depends_on = [module.lambda, module.api_gateway]
}

resource "aws_api_gateway_integration" "list_presentations" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = module.api_gateway.resource_ids["presentations"]
  http_method = "GET"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${var.aws_region}:lambda:path/2015-03-31/functions/${aws_lambda_function.list_presentations.arn}/invocations"

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

# ============================================================================
# Lambda Permissions for API Gateway
# ============================================================================

# Lambda permissions must be created before API Gateway deployment
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

resource "aws_lambda_permission" "presentation_download_permission" {
  statement_id  = "AllowAPIGatewayInvoke-presentation-download"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.function_names["presentation_download"]
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${module.api_gateway.rest_api_id}/*/*"

  depends_on = [module.lambda, module.api_gateway]
}

# Note: list_presentations_permission is defined in lambda_list_presentations.tf
# to avoid duplication

# Create a new deployment to include all integrations and responses
# Note: This is the legacy deployment for v0 (unversioned) endpoints
# Versioned endpoints use aws_api_gateway_deployment.versioned_deployment
resource "aws_api_gateway_deployment" "integration_deployment" {
  rest_api_id = module.api_gateway.rest_api_id

  triggers = {
    # Redeploy when any integration or response changes
    redeployment = sha1(jsonencode([
      # Main integrations
      aws_api_gateway_integration.create_presentation,
      aws_api_gateway_integration.get_presentation,
      aws_api_gateway_integration.list_presentations,
      aws_api_gateway_integration.create_session,
      aws_api_gateway_integration.get_session,
      aws_api_gateway_integration.execute_agent,
      aws_api_gateway_integration.health,
      aws_api_gateway_integration.health_ready,
      # Additional integrations
      aws_api_gateway_integration.get_task,
      # Integration responses
      aws_api_gateway_integration_response.health_200,
      aws_api_gateway_integration_response.health_ready_200,
      # aws_api_gateway_integration_response.get_templates_200,
      # aws_api_gateway_integration_response.templates_options_200,
      # aws_api_gateway_integration_response.task_options_200,
      # Gateway responses for validation errors
      # aws_api_gateway_gateway_response.bad_request,
      # aws_api_gateway_gateway_response.bad_request_parameters,
      # aws_api_gateway_gateway_response.missing_authentication_token,
      # aws_api_gateway_gateway_response.throttled,
      # aws_api_gateway_gateway_response.default_5xx,
      # Include versioned resources in deployment triggers
      # aws_api_gateway_deployment.versioned_deployment,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    # Ensure all method responses are created first
    aws_api_gateway_method_response.health_200,
    aws_api_gateway_method_response.health_ready_200,
    aws_api_gateway_method_response.get_task_200,
    # Then integrations
    aws_api_gateway_integration.create_presentation,
    aws_api_gateway_integration.get_presentation,
    aws_api_gateway_integration.download_presentation,
    aws_api_gateway_integration.list_presentations,
    aws_api_gateway_integration.create_session,
    aws_api_gateway_integration.get_session,
    aws_api_gateway_integration.execute_agent,
    aws_api_gateway_integration.health,
    aws_api_gateway_integration.health_ready,
    aws_api_gateway_integration.get_task,
    # Then integration responses
    aws_api_gateway_integration_response.health_200,
    aws_api_gateway_integration_response.health_ready_200,
    # aws_api_gateway_integration_response.get_templates_200,
    # aws_api_gateway_integration_response.templates_options_200,
    # aws_api_gateway_integration_response.task_options_200,
    # Lambda permissions (critical for avoiding 502 errors)
    aws_lambda_permission.generate_presentation_permission,
    aws_lambda_permission.presentation_status_permission,
    aws_lambda_permission.presentation_download_permission,
    # aws_lambda_permission.get_task_permission is defined in lambda_get_task.tf
    # Gateway responses for validation errors
    # Gateway responses commented out - resources not defined
    # aws_api_gateway_gateway_response.bad_request,
    # aws_api_gateway_gateway_response.bad_request_parameters,
    # aws_api_gateway_gateway_response.missing_authentication_token,
    # aws_api_gateway_gateway_response.throttled,
    # aws_api_gateway_gateway_response.default_5xx,
    # Wait for versioned deployment to complete
    # aws_api_gateway_deployment.versioned_deployment,
    # Ensure Lambda functions and API Gateway are available
    module.lambda,
    module.api_gateway,
  ]
}

# Create API Gateway Stage (since module doesn't create it when deployment is disabled)
resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.integration_deployment.id
  rest_api_id   = module.api_gateway.rest_api_id
  stage_name    = var.stage_name

  # Enable X-Ray tracing for better debugging
  xray_tracing_enabled = true

  # CloudWatch settings for monitoring
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_stage.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      ip               = "$context.identity.sourceIp"
      caller           = "$context.identity.caller"
      user             = "$context.identity.user"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      resourcePath     = "$context.resourcePath"
      status           = "$context.status"
      protocol         = "$context.protocol"
      responseLength   = "$context.responseLength"
      responseTime     = "$context.responseTime"
      error            = "$context.error.message"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-api-stage"
    }
  )

  depends_on = [
    aws_api_gateway_deployment.integration_deployment,
    aws_cloudwatch_log_group.api_gateway_stage
  ]
}

# CloudWatch Log Group for API Gateway Stage
resource "aws_cloudwatch_log_group" "api_gateway_stage" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}-stage"
  retention_in_days = var.log_retention_days

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-stage-logs"
    }
  )
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
# Layer 6.5: Additional API Gateway Resources (/tasks endpoint)
# ============================================================================

# /tasks 资源
resource "aws_api_gateway_resource" "tasks" {
  rest_api_id = module.api_gateway.rest_api_id
  parent_id   = module.api_gateway.rest_api_root_resource_id
  path_part   = "tasks"
}

# /tasks/{taskId} 资源
resource "aws_api_gateway_resource" "task_id" {
  rest_api_id = module.api_gateway.rest_api_id
  parent_id   = aws_api_gateway_resource.tasks.id
  path_part   = "{taskId}"
}

# GET /tasks/{taskId} 方法
resource "aws_api_gateway_method" "get_task" {
  rest_api_id      = module.api_gateway.rest_api_id
  resource_id      = aws_api_gateway_resource.task_id.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true

  request_parameters = {
    "method.request.path.taskId" = true
  }
}

# GET /tasks/{taskId} 集成
resource "aws_api_gateway_integration" "get_task" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.task_id.id
  http_method = aws_api_gateway_method.get_task.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${var.aws_region}:lambda:path/2015-03-31/functions/${aws_lambda_function.get_task.arn}/invocations"

  depends_on = [
    aws_api_gateway_method.get_task
  ]
}

# GET /tasks/{taskId} 方法响应
resource "aws_api_gateway_method_response" "get_task_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.task_id.id
  http_method = aws_api_gateway_method.get_task.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

# Lambda permission for get_task is defined in lambda_get_task.tf to avoid duplication

# ============================================================================
# Layer 7: Monitoring and Alerting (Depends on all infrastructure components)
# ============================================================================

# CloudWatch Monitoring Module
module "monitoring" {
  count  = var.enable_monitoring ? 1 : 0
  source = "./modules/monitoring"

  # General configuration
  project_name = var.project_name
  environment  = var.environment

  # SNS configuration
  alert_email_addresses = var.alert_email_addresses

  # Lambda monitoring configuration
  lambda_function_names     = module.lambda.function_names
  lambda_error_threshold    = var.lambda_error_threshold
  lambda_duration_threshold = var.lambda_duration_threshold

  # API Gateway monitoring configuration
  api_gateway_name      = "${var.project_name}-${var.environment}"
  api_gateway_stage     = aws_api_gateway_stage.main.stage_name
  api_latency_threshold = var.api_latency_threshold
  api_4xx_threshold     = var.api_4xx_threshold
  api_5xx_threshold     = var.api_5xx_threshold

  # DynamoDB monitoring configuration
  enable_dynamodb_monitoring = var.enable_dynamodb_monitoring
  dynamodb_table_name        = module.dynamodb.tasks_table_name

  # Log retention
  log_retention_days = var.log_retention_days

  # Tags
  tags = local.common_tags

  # Dependencies to ensure proper creation order
  depends_on = [
    module.lambda,
    module.api_gateway,
    module.dynamodb,
    aws_api_gateway_stage.main,
    aws_api_gateway_deployment.integration_deployment
  ]
}

# ============================================================================
# Update Lambda Environment Variables with Real Bedrock Agent IDs
# ============================================================================

# Update Lambda function environment variables after Bedrock agents are created
resource "null_resource" "update_lambda_bedrock_configs" {
  # This resource will run after bedrock module is created
  depends_on = [module.bedrock, module.lambda]

  # Trigger when agent IDs change
  triggers = {
    orchestrator_agent_id = module.bedrock.agent_ids["orchestrator"]
    orchestrator_alias_id = module.bedrock.agent_alias_ids["orchestrator"]
    content_agent_id      = module.bedrock.agent_ids["content"]
    content_alias_id      = module.bedrock.agent_alias_ids["content"]
    visual_agent_id       = module.bedrock.agent_ids["visual"]
    visual_alias_id       = module.bedrock.agent_alias_ids["visual"]
    compiler_agent_id     = module.bedrock.agent_ids["compiler"]
    compiler_alias_id     = module.bedrock.agent_alias_ids["compiler"]
  }

  # Update all relevant Lambda functions with real agent IDs
  provisioner "local-exec" {
    command = <<-EOF
      echo "Updating Lambda functions with real Bedrock Agent IDs..."
      
      # Update generate_presentation function
      aws lambda update-function-configuration \
        --function-name ${module.lambda.function_names["generate_presentation"]} \
        --environment Variables="{
          S3_BUCKET=${module.s3.bucket_name},
          DYNAMODB_TABLE=${module.dynamodb.tasks_table_name},
          CHECKPOINTS_TABLE=${module.dynamodb.checkpoints_table_name},
          SQS_QUEUE_URL=${aws_sqs_queue.task_queue.url},
          ORCHESTRATOR_AGENT_ID=${module.bedrock.agent_ids["orchestrator"]},
          ORCHESTRATOR_ALIAS_ID=${module.bedrock.agent_alias_ids["orchestrator"]},
          CONTENT_AGENT_ID=${module.bedrock.agent_ids["content"]},
          CONTENT_ALIAS_ID=${module.bedrock.agent_alias_ids["content"]},
          VISUAL_AGENT_ID=${module.bedrock.agent_ids["visual"]},
          VISUAL_ALIAS_ID=${module.bedrock.agent_alias_ids["visual"]},
          COMPILER_AGENT_ID=${module.bedrock.agent_ids["compiler"]},
          COMPILER_ALIAS_ID=${module.bedrock.agent_alias_ids["compiler"]},
          BEDROCK_MODEL_ID=${var.bedrock_model_id},
          BEDROCK_ORCHESTRATOR_MODEL_ID=${var.bedrock_orchestrator_model_id},
          NOVA_MODEL_ID=${var.nova_model_id},
          LOG_LEVEL=INFO
        }" \
        --region ${var.aws_region}

      # Update core Lambda functions that use Bedrock Agents
      for func_name in create_outline generate_content generate_image compile_pptx; do
        echo "Updating Lambda function: $func_name"
        aws lambda update-function-configuration \
          --function-name ${var.project_name}-$func_name \
          --environment Variables="{
            S3_BUCKET=${module.s3.bucket_name},
            DYNAMODB_TABLE=${module.dynamodb.tasks_table_name},
            CHECKPOINTS_TABLE=${module.dynamodb.checkpoints_table_name},
            ORCHESTRATOR_AGENT_ID=${module.bedrock.agent_ids["orchestrator"]},
            ORCHESTRATOR_ALIAS_ID=${module.bedrock.agent_alias_ids["orchestrator"]},
            CONTENT_AGENT_ID=${module.bedrock.agent_ids["content"]},
            CONTENT_ALIAS_ID=${module.bedrock.agent_alias_ids["content"]},
            VISUAL_AGENT_ID=${module.bedrock.agent_ids["visual"]},
            VISUAL_ALIAS_ID=${module.bedrock.agent_alias_ids["visual"]},
            COMPILER_AGENT_ID=${module.bedrock.agent_ids["compiler"]},
            COMPILER_ALIAS_ID=${module.bedrock.agent_alias_ids["compiler"]},
            BEDROCK_MODEL_ID=${var.bedrock_model_id},
            BEDROCK_ORCHESTRATOR_MODEL_ID=${var.bedrock_orchestrator_model_id},
            NOVA_MODEL_ID=${var.nova_model_id},
            LOG_LEVEL=INFO
          }" \
          --region ${var.aws_region} || echo "Failed to update $func_name, continuing..."
      done

      echo "Lambda functions updated successfully with real Bedrock Agent IDs"
    EOF
  }
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
  value       = aws_api_gateway_stage.main.invoke_url
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

# Monitoring outputs
output "monitoring_dashboard_url" {
  description = "CloudWatch Dashboard URL"
  value       = var.enable_monitoring && length(module.monitoring) > 0 ? module.monitoring[0].dashboard_url : null
}

output "monitoring_sns_topic_arn" {
  description = "SNS Topic ARN for alerts"
  value       = var.enable_monitoring && length(module.monitoring) > 0 ? module.monitoring[0].sns_topic_arn : null
}

output "monitoring_summary" {
  description = "Summary of monitoring components"
  value       = var.enable_monitoring && length(module.monitoring) > 0 ? module.monitoring[0].monitoring_summary : null
}

# Bedrock Agents outputs
output "bedrock_agent_ids" {
  description = "Map of Bedrock Agent IDs"
  value       = module.bedrock.agent_ids
}

output "bedrock_agent_alias_ids" {
  description = "Map of Bedrock Agent Alias IDs"  
  value       = module.bedrock.agent_alias_ids
}

output "bedrock_orchestrator_agent_id" {
  description = "Orchestrator Agent ID for Lambda environment variables"
  value       = module.bedrock.agent_ids["orchestrator"]
}

output "bedrock_orchestrator_alias_id" {
  description = "Orchestrator Agent Alias ID for Lambda environment variables"
  value       = module.bedrock.agent_alias_ids["orchestrator"]
}