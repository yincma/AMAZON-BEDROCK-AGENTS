# AI PPT Assistant Infrastructure Variables
# This file defines all input variables for the Terraform configuration

# General Configuration
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ai-ppt-assistant"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "owner" {
  description = "Owner of the resources"
  type        = string
}

variable "cost_center" {
  description = "Cost center for billing purposes"
  type        = string
}

# State Management (for remote backend)
variable "state_bucket" {
  description = "S3 bucket for Terraform state storage"
  type        = string
  default     = ""
}

variable "state_lock_table" {
  description = "DynamoDB table for state locking"
  type        = string
  default     = ""
}

# S3 Configuration
variable "s3_lifecycle_rules" {
  description = "S3 lifecycle rules configuration"
  type = list(object({
    id                     = string
    status                 = string
    days_to_ia            = number
    days_to_glacier       = number
    days_to_expiration    = number
  }))
  default = [
    {
      id                  = "presentation-lifecycle"
      status              = "Enabled"
      days_to_ia         = 30
      days_to_glacier    = 90
      days_to_expiration = 365
    }
  ]
}

variable "s3_cors_configuration" {
  description = "CORS configuration for S3 bucket"
  type = list(object({
    allowed_headers = list(string)
    allowed_methods = list(string)
    allowed_origins = list(string)
    expose_headers  = list(string)
    max_age_seconds = number
  }))
  default = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["GET", "HEAD", "PUT", "POST", "DELETE"]
      allowed_origins = ["*"]  # Update with specific domains in production
      expose_headers  = ["ETag", "x-amz-server-side-encryption"]
      max_age_seconds = 3000
    }
  ]
}

# DynamoDB Configuration
variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode (PAY_PER_REQUEST or PROVISIONED)"
  type        = string
  default     = "PAY_PER_REQUEST"
  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.dynamodb_billing_mode)
    error_message = "Billing mode must be PAY_PER_REQUEST or PROVISIONED"
  }
}

variable "dynamodb_read_capacity" {
  description = "Read capacity units (only used if billing mode is PROVISIONED)"
  type        = number
  default     = 5
}

variable "dynamodb_write_capacity" {
  description = "Write capacity units (only used if billing mode is PROVISIONED)"
  type        = number
  default     = 5
}

# API Gateway Configuration
variable "api_throttle_rate_limit" {
  description = "API Gateway throttle rate limit (requests per second)"
  type        = number
  default     = 100
}

variable "api_throttle_burst_limit" {
  description = "API Gateway throttle burst limit"
  type        = number
  default     = 200
}

variable "api_keys" {
  description = "List of API keys to create"
  type = list(object({
    name        = string
    description = string
  }))
  default = []
}

# Lambda Configuration
variable "lambda_architecture" {
  description = "Lambda function architecture (x86_64 or arm64)"
  type        = string
  default     = "arm64" # Graviton2 for cost optimization
  validation {
    condition     = contains(["x86_64", "arm64"], var.lambda_architecture)
    error_message = "Architecture must be x86_64 or arm64"
  }
}

variable "lambda_functions" {
  description = "Map of Lambda function configurations"
  type = map(object({
    handler          = string
    memory_size      = number
    timeout          = number
    reserved_concurrent = number
    description      = string
  }))
  default = {
    create_outline = {
      handler          = "create_outline.handler"
      memory_size      = 1024
      timeout          = 30
      reserved_concurrent = 2
      description      = "Generate presentation outline from topic"
    }
    generate_content = {
      handler          = "generate_content.handler"
      memory_size      = 1024
      timeout          = 60
      reserved_concurrent = 5
      description      = "Generate detailed slide content"
    }
    generate_image = {
      handler          = "generate_image.handler"
      memory_size      = 2048
      timeout          = 120
      reserved_concurrent = 3
      description      = "Generate images using Amazon Nova"
    }
    find_image = {
      handler          = "find_image.handler"
      memory_size      = 512
      timeout          = 30
      reserved_concurrent = 2
      description      = "Find relevant images from library"
    }
    generate_speaker_notes = {
      handler          = "generate_speaker_notes.handler"
      memory_size      = 1024
      timeout          = 30
      reserved_concurrent = 2
      description      = "Generate speaker notes for slides"
    }
    compile_pptx = {
      handler          = "compile_pptx.handler"
      memory_size      = 2048
      timeout          = 300
      reserved_concurrent = 2
      description      = "Compile final PowerPoint file"
    }
    generate_presentation = {
      handler          = "generate_presentation.handler"
      memory_size      = 512
      timeout          = 30
      reserved_concurrent = 5
      description      = "API endpoint for presentation generation"
    }
    presentation_status = {
      handler          = "presentation_status.handler"
      memory_size      = 256
      timeout          = 10
      reserved_concurrent = 5
      description      = "API endpoint for status checking"
    }
    presentation_download = {
      handler          = "presentation_download.handler"
      memory_size      = 256
      timeout          = 10
      reserved_concurrent = 5
      description      = "API endpoint for file download"
    }
    modify_slide = {
      handler          = "modify_slide.handler"
      memory_size      = 1024
      timeout          = 60
      reserved_concurrent = 2
      description      = "API endpoint for slide modification"
    }
  }
}

# Bedrock Configuration
variable "bedrock_region" {
  description = "AWS region for Bedrock services"
  type        = string
  default     = "us-east-1"
}

variable "bedrock_model_id" {
  description = "Bedrock model ID"
  type        = string
  default     = "anthropic.claude-4-0"
}

variable "bedrock_model_version" {
  description = "Bedrock model version"
  type        = string
  default     = "1.0"
}

variable "bedrock_agents" {
  description = "Map of Bedrock agent configurations"
  type = map(object({
    name         = string
    description  = string
    instructions = string
    action_groups = list(object({
      name        = string
      description = string
      actions     = list(string)
    }))
  }))
  default = {
    orchestrator = {
      name         = "orchestrator-agent"
      description  = "Main workflow orchestration agent"
      instructions = "Coordinate the overall presentation generation workflow"
      action_groups = []
    }
    content = {
      name         = "content-agent"
      description  = "Content generation agent"
      instructions = "Generate text content for presentations"
      action_groups = [
        {
          name        = "content-generation"
          description = "Actions for content generation"
          actions     = ["create_outline", "generate_content", "generate_speaker_notes"]
        }
      ]
    }
    visual = {
      name         = "visual-agent"
      description  = "Visual content generation agent"
      instructions = "Generate and find images for presentations"
      action_groups = [
        {
          name        = "visual-generation"
          description = "Actions for visual content"
          actions     = ["generate_image", "find_image"]
        }
      ]
    }
    compiler = {
      name         = "compiler-agent"
      description  = "File compilation agent"
      instructions = "Compile final presentation files"
      action_groups = [
        {
          name        = "file-compilation"
          description = "Actions for file compilation"
          actions     = ["compile_pptx"]
        }
      ]
    }
  }
}

# Logging Configuration
variable "log_level" {
  description = "Log level for Lambda functions"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# Monitoring and Alerting
variable "enable_monitoring" {
  description = "Enable CloudWatch monitoring and alarms"
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
  default     = ""
}

# Cost Optimization
variable "enable_cost_optimization" {
  description = "Enable cost optimization features"
  type        = bool
  default     = true
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services"
  type        = bool
  default     = true
}

variable "enable_sqs_endpoint" {
  description = "Enable SQS VPC endpoint"
  type        = bool
  default     = false
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnet internet access"
  type        = bool
  default     = true
}

variable "enable_lambda_vpc_config" {
  description = "Enable VPC configuration for Lambda functions"
  type        = bool
  default     = true
}

variable "enable_vpc_flow_logs" {
  description = "Enable VPC Flow Logs for network monitoring"
  type        = bool
  default     = true
}

variable "vpc_flow_log_retention_days" {
  description = "Retention period for VPC flow logs"
  type        = number
  default     = 30
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}