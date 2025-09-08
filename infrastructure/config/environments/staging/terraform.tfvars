# Staging Environment Configuration
# This file contains staging-specific settings

environment = "staging"
aws_region  = "us-east-1"

# Moderate limits for staging
api_throttle_rate_limit  = 75
api_throttle_burst_limit = 150

# Moderate Lambda configurations for staging
lambda_functions = {
  create_outline = {
    handler             = "create_outline.handler"
    memory_size         = 768
    timeout             = 30
    reserved_concurrent = 2
    description         = "Generate presentation outline from topic"
  }
  generate_content = {
    handler             = "generate_content.handler"
    memory_size         = 768
    timeout             = 60
    reserved_concurrent = 3
    description         = "Generate detailed slide content"
  }
  generate_image = {
    handler             = "generate_image.handler"
    memory_size         = 1536
    timeout             = 120
    reserved_concurrent = 2
    description         = "Generate images using Amazon Nova"
  }
  find_image = {
    handler             = "find_image.handler"
    memory_size         = 384
    timeout             = 30
    reserved_concurrent = 2
    description         = "Find relevant images from library"
  }
  generate_speaker_notes = {
    handler             = "generate_speaker_notes.handler"
    memory_size         = 768
    timeout             = 30
    reserved_concurrent = 2
    description         = "Generate speaker notes for slides"
  }
  compile_pptx = {
    handler             = "compile_pptx.handler"
    memory_size         = 1536
    timeout             = 300
    reserved_concurrent = 2
    description         = "Compile final PowerPoint file"
  }
  generate_presentation = {
    handler             = "generate_presentation.handler"
    memory_size         = 384
    timeout             = 30
    reserved_concurrent = 3
    description         = "API endpoint for presentation generation"
  }
  presentation_status = {
    handler             = "presentation_status.handler"
    memory_size         = 192
    timeout             = 10
    reserved_concurrent = 3
    description         = "API endpoint for status checking"
  }
  presentation_download = {
    handler             = "presentation_download.handler"
    memory_size         = 192
    timeout             = 10
    reserved_concurrent = 3
    description         = "API endpoint for file download"
  }
  modify_slide = {
    handler             = "handler.handler"
    memory_size         = 768
    timeout             = 60
    reserved_concurrent = 2
    description         = "API endpoint for slide modification"
  }
}

# Staging logging
log_level          = "INFO"
log_retention_days = 14

# Monitoring for staging
enable_monitoring = true

# Staging tags
additional_tags = {
  Environment = "Staging"
  Purpose     = "Pre-production Testing"
  QA          = "true"
}