# API Gateway CORS Module Outputs

output "options_method_id" {
  description = "ID of the OPTIONS method"
  value       = aws_api_gateway_method.options.id
}

output "cors_configuration" {
  description = "CORS configuration details"
  value = {
    allowed_origins = var.allowed_origins
    allowed_methods = var.allowed_methods
    allowed_headers = var.allowed_headers
    max_age_seconds = var.max_age_seconds
  }
}