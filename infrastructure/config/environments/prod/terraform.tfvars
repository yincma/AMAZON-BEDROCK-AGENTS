# Production Environment Configuration
# This file contains production-specific settings

environment = "prod"
aws_region  = "us-east-1"

# Production limits
api_throttle_rate_limit  = 100
api_throttle_burst_limit = 200

# Optimized Lambda configurations for production
lambda_functions = {
  create_outline = {
    handler             = "create_outline.handler"
    memory_size         = 1024
    timeout             = 30
    reserved_concurrent = 5
    description         = "Generate presentation outline from topic"
  }
  generate_content = {
    handler             = "generate_content.handler"
    memory_size         = 1024
    timeout             = 60
    reserved_concurrent = 10
    description         = "Generate detailed slide content"
  }
  generate_image = {
    handler             = "generate_image.handler"
    memory_size         = 2048
    timeout             = 120
    reserved_concurrent = 5
    description         = "Generate images using Amazon Nova"
  }
  find_image = {
    handler             = "find_image.handler"
    memory_size         = 512
    timeout             = 30
    reserved_concurrent = 5
    description         = "Find relevant images from library"
  }
  generate_speaker_notes = {
    handler             = "generate_speaker_notes.handler"
    memory_size         = 1024
    timeout             = 30
    reserved_concurrent = 5
    description         = "Generate speaker notes for slides"
  }
  compile_pptx = {
    handler             = "compile_pptx.handler"
    memory_size         = 2048
    timeout             = 300
    reserved_concurrent = 5
    description         = "Compile final PowerPoint file"
  }
  generate_presentation = {
    handler             = "generate_presentation.handler"
    memory_size         = 512
    timeout             = 30
    reserved_concurrent = 10
    description         = "API endpoint for presentation generation"
  }
  presentation_status = {
    handler             = "presentation_status.handler"
    memory_size         = 256
    timeout             = 10
    reserved_concurrent = 10
    description         = "API endpoint for status checking"
  }
  presentation_download = {
    handler             = "presentation_download.handler"
    memory_size         = 256
    timeout             = 10
    reserved_concurrent = 10
    description         = "API endpoint for file download"
  }
  modify_slide = {
    handler             = "modify_slide.handler"
    memory_size         = 1024
    timeout             = 60
    reserved_concurrent = 5
    description         = "API endpoint for slide modification"
  }
}

# Production logging
log_level          = "WARNING" # Less verbose in production
log_retention_days = 90        # Longer retention for compliance

# Full monitoring in production
enable_monitoring = true

# Production S3 lifecycle (longer retention)
s3_lifecycle_rules = [
  {
    id                 = "presentation-lifecycle-prod"
    status             = "Enabled"
    days_to_ia         = 60  # Keep in standard storage longer
    days_to_glacier    = 180 # Archive after 6 months
    days_to_expiration = 730 # Keep for 2 years
  }
]

# Production tags
additional_tags = {
  Environment     = "Production"
  Purpose         = "Live Production Service"
  SLA             = "99.9"
  BackupRequired  = "true"
  ComplianceLevel = "High"
}