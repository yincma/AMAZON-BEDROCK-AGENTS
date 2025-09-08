# Variables for Lambda module

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table"
  type        = string
}

variable "checkpoints_table_arn" {
  description = "ARN of the DynamoDB checkpoints table"
  type        = string
}

variable "sqs_queue_url" {
  description = "URL of the SQS queue"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of the SQS queue"
  type        = string
}

variable "orchestrator_agent_id" {
  description = "ID of the Orchestrator Bedrock Agent"
  type        = string
}

variable "orchestrator_alias_id" {
  description = "Alias ID of the Orchestrator Bedrock Agent"
  type        = string
}

variable "content_agent_id" {
  description = "ID of the Content Bedrock Agent"
  type        = string
}

variable "content_alias_id" {
  description = "Alias ID of the Content Bedrock Agent"
  type        = string
}

variable "visual_agent_id" {
  description = "ID of the Visual Bedrock Agent"
  type        = string
}

variable "visual_alias_id" {
  description = "Alias ID of the Visual Bedrock Agent"
  type        = string
}

variable "compiler_agent_id" {
  description = "ID of the Compiler Bedrock Agent"
  type        = string
}

variable "compiler_alias_id" {
  description = "Alias ID of the Compiler Bedrock Agent"
  type        = string
}

variable "log_level" {
  description = "Logging level for Lambda functions"
  type        = string
  default     = "INFO"
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for Claude content generation (Claude 4.0)"
  type        = string
}

variable "bedrock_orchestrator_model_id" {
  description = "Bedrock model ID for Orchestrator Agent (Claude 4.1)"
  type        = string
}

variable "nova_model_id" {
  description = "Amazon Nova model ID for image generation"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# VPC Configuration Variables
variable "vpc_id" {
  type        = string
  description = "VPC ID for Lambda functions"
  default     = ""
}

variable "vpc_subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for Lambda functions in VPC"
  default     = []
}

variable "vpc_security_group_ids" {
  type        = list(string)
  description = "Security group IDs for Lambda functions in VPC"
  default     = []
}

variable "enable_vpc_config" {
  type        = bool
  description = "Enable VPC configuration for Lambda functions"
  default     = false
}

# Performance Optimization Variables
variable "enable_provisioned_concurrency" {
  type        = bool
  description = "Enable provisioned concurrency for high-frequency Lambda functions"
  default     = true
}

variable "provisioned_concurrency_config" {
  type = map(object({
    provisioned_concurrent_executions = number
    qualifier                         = string
  }))
  description = "Provisioned concurrency configuration for Lambda functions"
  default = {
    api_presentation_status   = { provisioned_concurrent_executions = 5, qualifier = "$LATEST" }
    api_generate_presentation = { provisioned_concurrent_executions = 3, qualifier = "$LATEST" }
    api_presentation_download = { provisioned_concurrent_executions = 2, qualifier = "$LATEST" }
    api_modify_slide          = { provisioned_concurrent_executions = 2, qualifier = "$LATEST" }
  }
}