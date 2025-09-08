project_name = "ai-ppt-assistant"
environment  = "dev"
aws_region   = "us-east-1"

# Owner and Cost Center (required variables)
owner       = "AI-Team"
cost_center = "Engineering"

# Monitoring Configuration
enable_monitoring = true
alert_email_addresses = [
  # "your-email@example.com"  # Uncomment and add your email
]

# Monitoring Thresholds
lambda_error_threshold    = 5     # Number of errors before alert
lambda_duration_threshold = 25000 # 25 seconds in milliseconds
api_latency_threshold     = 10000 # 10 seconds in milliseconds
api_4xx_threshold         = 10    # Number of 4XX errors
api_5xx_threshold         = 5     # Number of 5XX errors

# DynamoDB Monitoring
enable_dynamodb_monitoring = true

# API Versioning Configuration
api_versions = {
  v1 = {
    version_name     = "v1"
    description      = "API Version 1 - Current stable version for backward compatibility"
    stage_name       = "v1"
    is_default       = true
    lambda_mappings  = {
      "generate_presentation" = "generate_presentation"
      "presentation_status"   = "presentation_status"
      "presentation_download" = "presentation_download"
      "modify_slide"         = "modify_slide"
      "get_task"             = "presentation_status"
    }
    deprecation_date = "2026-12-31"
    status          = "active"
  }
  v2 = {
    version_name     = "v2"
    description      = "API Version 2 - Enhanced endpoints with improved features"
    stage_name       = "v2"
    is_default       = false
    lambda_mappings  = {
      "generate_presentation" = "generate_presentation"
      "presentation_status"   = "presentation_status"
      "presentation_download" = "presentation_download"
      "modify_slide"         = "modify_slide"
      "get_task"             = "presentation_status"
    }
    deprecation_date = ""
    status          = "active"
  }
}

# Multi-Environment Stages Configuration
api_stages = {
  dev = {
    stage_name           = "dev"
    deployment_id        = ""
    description          = "Development stage for testing"
    cache_enabled        = false
    cache_ttl_seconds   = 0
    throttle_rate_limit  = 50
    throttle_burst_limit = 100
    log_level           = "INFO"
    data_trace_enabled  = true
    metrics_enabled     = true
  }
  staging = {
    stage_name           = "staging"
    deployment_id        = ""
    description          = "Staging stage for pre-production testing"
    cache_enabled        = true
    cache_ttl_seconds   = 300
    throttle_rate_limit  = 100
    throttle_burst_limit = 200
    log_level           = "ERROR"
    data_trace_enabled  = false
    metrics_enabled     = true
  }
  prod = {
    stage_name           = "prod"
    deployment_id        = ""
    description          = "Production stage"
    cache_enabled        = true
    cache_ttl_seconds   = 600
    throttle_rate_limit  = 200
    throttle_burst_limit = 400
    log_level           = "ERROR"
    data_trace_enabled  = false
    metrics_enabled     = true
  }
}

tags = {
  Project     = "AI PPT Assistant"
  Environment = "dev"
  ManagedBy   = "Terraform"
  DeployedAt  = "2025-09-07"
  Feature     = "API-Versioning"
}