# API Gateway CORS Module - Helper for configuring CORS
# This module sets up CORS configuration for API Gateway resources

# OPTIONS method for CORS preflight
resource "aws_api_gateway_method" "options" {
  rest_api_id   = var.rest_api_id
  resource_id   = var.resource_id
  http_method   = "OPTIONS"
  authorization = "NONE"
  api_key_required = false
}

# Mock integration for OPTIONS (CORS preflight)
resource "aws_api_gateway_integration" "options" {
  rest_api_id = var.rest_api_id
  resource_id = var.resource_id
  http_method = aws_api_gateway_method.options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }

  passthrough_behavior = "WHEN_NO_MATCH"
}

# Method response for OPTIONS
resource "aws_api_gateway_method_response" "options" {
  rest_api_id = var.rest_api_id
  resource_id = var.resource_id
  http_method = aws_api_gateway_method.options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
    "method.response.header.Access-Control-Max-Age"       = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

# Integration response for OPTIONS
resource "aws_api_gateway_integration_response" "options" {
  rest_api_id = var.rest_api_id
  resource_id = var.resource_id
  http_method = aws_api_gateway_method.options.http_method
  status_code = aws_api_gateway_method_response.options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'${join(",", var.allowed_headers)}'"
    "method.response.header.Access-Control-Allow-Methods" = "'${join(",", var.allowed_methods)}'"
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.allowed_origins[0]}'"  # For simplicity, using first origin
    "method.response.header.Access-Control-Max-Age"       = "'${var.max_age_seconds}'"
  }

  response_templates = {
    "application/json" = ""
  }
}