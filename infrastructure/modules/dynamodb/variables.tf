variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "billing_mode" {
  description = "DynamoDB billing mode"
  type        = string
  default     = "PAY_PER_REQUEST" # On-demand as per spec
}

variable "ttl_attribute" {
  description = "TTL attribute name"
  type        = string
  default     = "ttl"
}

variable "ttl_enabled" {
  description = "Whether to enable TTL"
  type        = bool
  default     = true
}

variable "ttl_days" {
  description = "Number of days for TTL (30 days as per spec)"
  type        = number
  default     = 30
}

variable "create_tasks_table" {
  description = "Whether to create a separate tasks table"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
