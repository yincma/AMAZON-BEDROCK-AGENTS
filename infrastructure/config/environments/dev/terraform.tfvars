# Development Environment Configuration
# This file contains development-specific settings

environment = "dev"
aws_region  = "us-east-1"

# Lower limits for development
api_throttle_rate_limit  = 50
api_throttle_burst_limit = 100

# Smaller Lambda configurations for dev
lambda_functions = {
  create_outline = {
    handler             = "create_outline.handler"
    memory_size        = 512  # Reduced for dev
    timeout            = 30
    reserved_concurrent = 1   # Minimal for dev
    description        = "Generate presentation outline from topic"
  }
  generate_content = {
    handler             = "generate_content.handler"
    memory_size        = 512
    timeout            = 60
    reserved_concurrent = 2
    description        = "Generate detailed slide content"
  }
  generate_image = {
    handler             = "generate_image.handler"
    memory_size        = 1024
    timeout            = 120
    reserved_concurrent = 1
    description        = "Generate images using Amazon Nova"
  }
  find_image = {
    handler             = "find_image.handler"
    memory_size        = 256
    timeout            = 30
    reserved_concurrent = 1
    description        = "Find relevant images from library"
  }
  generate_speaker_notes = {
    handler             = "generate_speaker_notes.handler"
    memory_size        = 512
    timeout            = 30
    reserved_concurrent = 1
    description        = "Generate speaker notes for slides"
  }
  compile_pptx = {
    handler             = "compile_pptx.handler"
    memory_size        = 1024
    timeout            = 300
    reserved_concurrent = 1
    description        = "Compile final PowerPoint file"
  }
  generate_presentation = {
    handler             = "generate_presentation.handler"
    memory_size        = 256
    timeout            = 30
    reserved_concurrent = 2
    description        = "API endpoint for presentation generation"
  }
  presentation_status = {
    handler             = "presentation_status.handler"
    memory_size        = 128
    timeout            = 10
    reserved_concurrent = 2
    description        = "API endpoint for status checking"
  }
  presentation_download = {
    handler             = "presentation_download.handler"
    memory_size        = 128
    timeout            = 10
    reserved_concurrent = 2
    description        = "API endpoint for file download"
  }
  modify_slide = {
    handler             = "modify_slide.handler"
    memory_size        = 512
    timeout            = 60
    reserved_concurrent = 1
    description        = "API endpoint for slide modification"
  }
}

# Development logging
log_level          = "DEBUG"
log_retention_days = 7

# Cost optimization for dev
enable_cost_optimization = true
enable_monitoring       = false  # Disable extensive monitoring in dev

# Development tags
additional_tags = {
  Environment = "Development"
  Purpose     = "Testing and Development"
  AutoShutdown = "true"
}