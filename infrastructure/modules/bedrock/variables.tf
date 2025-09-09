# Variables for Bedrock module

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket for presentations"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  type        = string
}

variable "lambda_function_arns" {
  description = "Map of Lambda function ARNs for each agent"
  type        = map(map(string))
  default = {
    orchestrator = {}
    content      = {}
    visual       = {}
    compiler     = {}
  }
}

variable "agents" {
  description = "Configuration for each Bedrock agent"
  type = map(object({
    model_id    = string
    temperature = number
    top_p       = number
    top_k       = number
    max_length  = number
  }))
  default = {
    orchestrator = {
      model_id    = "us.anthropic.claude-opus-4-1-20250805-v1:0"
      temperature = 0.7
      top_p       = 0.9
      top_k       = 250
      max_length  = 2048
    }
    content = {
      model_id    = "us.anthropic.claude-opus-4-20250514-v1:0"
      temperature = 0.8
      top_p       = 0.95
      top_k       = 250
      max_length  = 4096
    }
    visual = {
      model_id    = "us.anthropic.claude-opus-4-20250514-v1:0"
      temperature = 0.9
      top_p       = 0.95
      top_k       = 250
      max_length  = 2048
    }
    compiler = {
      model_id    = "us.anthropic.claude-opus-4-20250514-v1:0"
      temperature = 0.3
      top_p       = 0.95
      top_k       = 250
      max_length  = 2048
    }
  }
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}