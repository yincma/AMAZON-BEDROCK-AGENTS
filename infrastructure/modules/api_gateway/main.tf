# API Gateway Module - AI PPT Assistant
# This module creates and configures the REST API Gateway for the presentation generation system

# Data sources
data "aws_region" "current" {}

# REST API
resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-${var.environment}-api"
  description = "API Gateway for AI PPT Assistant - ${var.environment}"

  endpoint_configuration {
    types = [var.endpoint_type]
  }

  # Binary media types for file uploads
  binary_media_types = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
    "image/*",
    "multipart/form-data"
  ]

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-api"
      Environment = var.environment
      Purpose     = "AI PPT Assistant API"
    }
  )
}

# API Deployment (条件创建)
resource "aws_api_gateway_deployment" "main" {
  count = var.create_deployment ? 1 : 0
  
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    # Redeploy when any resource configuration changes
    redeployment = sha1(jsonencode([
      aws_api_gateway_rest_api.main.body,
      aws_api_gateway_resource.presentations,
      aws_api_gateway_resource.sessions,
      aws_api_gateway_resource.agents,
      aws_api_gateway_method.create_presentation,
      aws_api_gateway_method.get_presentation,
      aws_api_gateway_method.list_presentations,
      aws_api_gateway_method.create_session,
      aws_api_gateway_method.get_session,
      aws_api_gateway_method.execute_agent,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_method.create_presentation,
    aws_api_gateway_method.get_presentation,
    aws_api_gateway_method.list_presentations,
    aws_api_gateway_method.create_session,
    aws_api_gateway_method.get_session,
    aws_api_gateway_method.execute_agent,
    aws_api_gateway_method_response.create_presentation_200,
    aws_api_gateway_method_response.get_presentation_200,
    aws_api_gateway_method_response.list_presentations_200,
    aws_api_gateway_method_response.create_session_200,
    aws_api_gateway_method_response.get_session_200,
    aws_api_gateway_method_response.execute_agent_200,
  ]
}

# API Stage (条件创建)
resource "aws_api_gateway_stage" "main" {
  count = var.create_deployment ? 1 : 0
  
  deployment_id = aws_api_gateway_deployment.main[0].id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.stage_name

  # CloudWatch logging
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      error          = "$context.error.message"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  # X-Ray tracing
  xray_tracing_enabled = var.enable_xray_tracing

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-${var.stage_name}"
      Environment = var.environment
    }
  )
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-api-logs"
      Environment = var.environment
    }
  )
}

# API Resources
# /presentations
resource "aws_api_gateway_resource" "presentations" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "presentations"
}

# /presentations/{id}
resource "aws_api_gateway_resource" "presentation_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.presentations.id
  path_part   = "{id}"
}

# /sessions
resource "aws_api_gateway_resource" "sessions" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "sessions"
}

# /sessions/{id}
resource "aws_api_gateway_resource" "session_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.sessions.id
  path_part   = "{id}"
}

# /agents
resource "aws_api_gateway_resource" "agents" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "agents"
}

# /agents/{name}/execute
resource "aws_api_gateway_resource" "agent_name" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.agents.id
  path_part   = "{name}"
}

resource "aws_api_gateway_resource" "agent_execute" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.agent_name.id
  path_part   = "execute"
}

# API Methods
# POST /presentations - Create new presentation
resource "aws_api_gateway_method" "create_presentation" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.presentations.id
  http_method   = "POST"
  authorization = var.api_key_required ? "NONE" : "NONE"
  api_key_required = var.api_key_required

  request_parameters = {
    "method.request.header.Content-Type" = true
  }

  request_validator_id = aws_api_gateway_request_validator.validate_body.id
}

# GET /presentations/{id} - Get presentation by ID
resource "aws_api_gateway_method" "get_presentation" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.presentation_id.id
  http_method   = "GET"
  authorization = var.api_key_required ? "NONE" : "NONE"
  api_key_required = var.api_key_required

  request_parameters = {
    "method.request.path.id" = true
  }

  request_validator_id = aws_api_gateway_request_validator.validate_params.id
}

# GET /presentations - List presentations
resource "aws_api_gateway_method" "list_presentations" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.presentations.id
  http_method   = "GET"
  authorization = var.api_key_required ? "NONE" : "NONE"
  api_key_required = var.api_key_required

  request_parameters = {
    "method.request.querystring.limit"  = false
    "method.request.querystring.offset" = false
    "method.request.querystring.status" = false
  }
}

# POST /sessions - Create new session
resource "aws_api_gateway_method" "create_session" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.sessions.id
  http_method   = "POST"
  authorization = var.api_key_required ? "NONE" : "NONE"
  api_key_required = var.api_key_required

  request_parameters = {
    "method.request.header.Content-Type" = true
  }

  request_validator_id = aws_api_gateway_request_validator.validate_body.id
}

# GET /sessions/{id} - Get session by ID
resource "aws_api_gateway_method" "get_session" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.session_id.id
  http_method   = "GET"
  authorization = var.api_key_required ? "NONE" : "NONE"
  api_key_required = var.api_key_required

  request_parameters = {
    "method.request.path.id" = true
  }

  request_validator_id = aws_api_gateway_request_validator.validate_params.id
}

# POST /agents/{name}/execute - Execute agent
resource "aws_api_gateway_method" "execute_agent" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.agent_execute.id
  http_method   = "POST"
  authorization = var.api_key_required ? "NONE" : "NONE"
  api_key_required = var.api_key_required

  request_parameters = {
    "method.request.path.name" = true
    "method.request.header.Content-Type" = true
  }

  request_validator_id = aws_api_gateway_request_validator.validate_all.id
}

# Request Validators
resource "aws_api_gateway_request_validator" "validate_body" {
  name                        = "${var.project_name}-validate-body"
  rest_api_id                 = aws_api_gateway_rest_api.main.id
  validate_request_body       = true
  validate_request_parameters = false
}

resource "aws_api_gateway_request_validator" "validate_params" {
  name                        = "${var.project_name}-validate-params"
  rest_api_id                 = aws_api_gateway_rest_api.main.id
  validate_request_body       = false
  validate_request_parameters = true
}

resource "aws_api_gateway_request_validator" "validate_all" {
  name                        = "${var.project_name}-validate-all"
  rest_api_id                 = aws_api_gateway_rest_api.main.id
  validate_request_body       = true
  validate_request_parameters = true
}

# API Key
resource "aws_api_gateway_api_key" "main" {
  count = var.api_key_required ? 1 : 0

  name        = "${var.project_name}-${var.environment}-api-key"
  description = "API Key for ${var.project_name} ${var.environment}"
  enabled     = true

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-api-key"
      Environment = var.environment
    }
  )
}

# Usage Plan
resource "aws_api_gateway_usage_plan" "main" {
  count = var.api_key_required && var.create_deployment ? 1 : 0

  name        = "${var.project_name}-${var.environment}-usage-plan"
  description = "Usage plan for ${var.project_name} ${var.environment}"

  api_stages {
    api_id = aws_api_gateway_rest_api.main.id
    stage  = aws_api_gateway_stage.main[0].stage_name
  }

  quota_settings {
    limit  = var.quota_limit
    period = var.quota_period
  }

  throttle_settings {
    rate_limit  = var.throttle_rate_limit
    burst_limit = var.throttle_burst_limit
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-usage-plan"
      Environment = var.environment
    }
  )
}

# Usage Plan Key
resource "aws_api_gateway_usage_plan_key" "main" {
  count = var.api_key_required && var.create_deployment ? 1 : 0

  key_id        = aws_api_gateway_api_key.main[0].id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.main[0].id
}

# CORS Configuration for all resources
module "cors_presentations" {
  source = "../api_gateway_cors"

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentations.id

  allowed_origins = var.cors_allowed_origins
  allowed_methods = ["GET", "POST", "OPTIONS"]
  allowed_headers = var.cors_allowed_headers
  max_age_seconds = var.cors_max_age_seconds
}

module "cors_presentation_id" {
  source = "../api_gateway_cors"

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentation_id.id

  allowed_origins = var.cors_allowed_origins
  allowed_methods = ["GET", "PUT", "DELETE", "OPTIONS"]
  allowed_headers = var.cors_allowed_headers
  max_age_seconds = var.cors_max_age_seconds
}

module "cors_sessions" {
  source = "../api_gateway_cors"

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.sessions.id

  allowed_origins = var.cors_allowed_origins
  allowed_methods = ["GET", "POST", "OPTIONS"]
  allowed_headers = var.cors_allowed_headers
  max_age_seconds = var.cors_max_age_seconds
}

module "cors_session_id" {
  source = "../api_gateway_cors"

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.session_id.id

  allowed_origins = var.cors_allowed_origins
  allowed_methods = ["GET", "PUT", "DELETE", "OPTIONS"]
  allowed_headers = var.cors_allowed_headers
  max_age_seconds = var.cors_max_age_seconds
}

module "cors_agent_execute" {
  source = "../api_gateway_cors"

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.agent_execute.id

  allowed_origins = var.cors_allowed_origins
  allowed_methods = ["POST", "OPTIONS"]
  allowed_headers = var.cors_allowed_headers
  max_age_seconds = var.cors_max_age_seconds
}

# ============================================================================
# API Gateway Integrations
# ============================================================================

# Note: Integrations are now handled in the main configuration to avoid circular dependencies
# This allows the API Gateway to be created first, then Lambda functions, then integrations

# ============================================================================
# Method Responses
# ============================================================================

# Method responses for proper API Gateway configuration
resource "aws_api_gateway_method_response" "create_presentation_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentations.id
  http_method = aws_api_gateway_method.create_presentation.http_method
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

resource "aws_api_gateway_method_response" "get_presentation_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentation_id.id
  http_method = aws_api_gateway_method.get_presentation.http_method
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

resource "aws_api_gateway_method_response" "list_presentations_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentations.id
  http_method = aws_api_gateway_method.list_presentations.http_method
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

resource "aws_api_gateway_method_response" "create_session_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.sessions.id
  http_method = aws_api_gateway_method.create_session.http_method
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

resource "aws_api_gateway_method_response" "get_session_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.session_id.id
  http_method = aws_api_gateway_method.get_session.http_method
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

resource "aws_api_gateway_method_response" "execute_agent_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.agent_execute.id
  http_method = aws_api_gateway_method.execute_agent.http_method
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

# ============================================================================
# Integration Responses
# ============================================================================

# Note: Integration responses are now handled in the main configuration with the integrations
# This follows the AWS_PROXY integration pattern where responses are managed by Lambda functions

# ============================================================================
# Lambda Permissions for API Gateway
# ============================================================================

# Note: Lambda permissions are now handled in the main configuration with the integrations
# This ensures proper dependency ordering and avoids circular dependencies

# WAF Web ACL Association (optional)
resource "aws_wafv2_web_acl_association" "api_gateway" {
  count = var.waf_web_acl_arn != "" && var.create_deployment ? 1 : 0

  resource_arn = aws_api_gateway_stage.main[0].arn
  web_acl_arn  = var.waf_web_acl_arn
}