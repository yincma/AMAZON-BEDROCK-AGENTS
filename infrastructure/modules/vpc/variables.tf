# Variables for VPC Module

variable "project_name" {
  type        = string
  description = "Project name for resource naming"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC"
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  type        = list(string)
  description = "List of availability zones to use"
  default     = ["us-west-2a", "us-west-2b"]
}

variable "enable_nat_gateway" {
  type        = bool
  description = "Enable NAT Gateway for private subnet internet access"
  default     = true
}

variable "enable_vpc_endpoints" {
  type        = bool
  description = "Enable VPC endpoints for AWS services"
  default     = true
}

variable "enable_sqs_endpoint" {
  type        = bool
  description = "Enable SQS VPC endpoint"
  default     = false
}

variable "enable_flow_logs" {
  type        = bool
  description = "Enable VPC Flow Logs"
  default     = true
}

variable "flow_log_retention_days" {
  type        = number
  description = "Retention period for VPC flow logs"
  default     = 30
}

variable "s3_bucket_name" {
  type        = string
  description = "S3 bucket name for VPC endpoint policy"
  default     = ""
}

variable "tags" {
  type        = map(string)
  description = "Additional tags for resources"
  default     = {}
}