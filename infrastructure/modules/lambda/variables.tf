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