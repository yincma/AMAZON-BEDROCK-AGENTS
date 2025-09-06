# API Gateway Module Variables - AI PPT Assistant

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod"
  }
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "stage_name" {
  description = "API Gateway stage name"
  type        = string
  default     = "v1"
}

variable "endpoint_type" {
  description = "API Gateway endpoint type (EDGE, REGIONAL, PRIVATE)"
  type        = string
  default     = "REGIONAL"
  validation {
    condition     = contains(["EDGE", "REGIONAL", "PRIVATE"], var.endpoint_type)
    error_message = "Endpoint type must be one of: EDGE, REGIONAL, PRIVATE"
  }
}

# API Key and Usage Plan
variable "api_key_required" {
  description = "Whether API key is required for API access"
  type        = bool
  default     = true
}

variable "quota_limit" {
  description = "Maximum number of requests per period"
  type        = number
  default     = 10000
}

variable "quota_period" {
  description = "Time period for quota (DAY, WEEK, MONTH)"
  type        = string
  default     = "DAY"
  validation {
    condition     = contains(["DAY", "WEEK", "MONTH"], var.quota_period)
    error_message = "Quota period must be one of: DAY, WEEK, MONTH"
  }
}

variable "throttle_rate_limit" {
  description = "API request steady-state rate limit"
  type        = number
  default     = 100
}

variable "throttle_burst_limit" {
  description = "API request burst limit"
  type        = number
  default     = 200
}

# Logging and Monitoring
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention must be a valid CloudWatch retention period"
  }
}

variable "log_level" {
  description = "API Gateway logging level (OFF, ERROR, INFO)"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["OFF", "ERROR", "INFO"], var.log_level)
    error_message = "Log level must be one of: OFF, ERROR, INFO"
  }
}

variable "enable_xray_tracing" {
  description = "Enable AWS X-Ray tracing"
  type        = bool
  default     = true
}

variable "enable_detailed_metrics" {
  description = "Enable detailed CloudWatch metrics"
  type        = bool
  default     = true
}

# CORS Configuration
variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "cors_allowed_headers" {
  description = "List of allowed headers for CORS"
  type        = list(string)
  default     = [
    "Content-Type",
    "X-Amz-Date",
    "Authorization",
    "X-Api-Key",
    "X-Amz-Security-Token"
  ]
}

variable "cors_max_age_seconds" {
  description = "How long browsers can cache CORS preflight response"
  type        = number
  default     = 300
}

# WAF Configuration
variable "waf_web_acl_arn" {
  description = "ARN of WAF Web ACL to associate (optional)"
  type        = string
  default     = ""
}

# Lambda Integration Variables (for future use)
variable "lambda_integrations" {
  description = "Map of Lambda function ARNs for API integrations"
  type = map(object({
    function_arn     = string
    function_name    = string
    invoke_arn       = string
    timeout_milliseconds = optional(number, 29000)
  }))
  default = {}
}

# Deployment Control Variables
variable "create_deployment" {
  description = "Whether to create deployment and stage within the module"
  type        = bool
  default     = true  # 保持向后兼容
}

variable "external_deployment_id" {
  description = "External deployment ID when create_deployment is false"
  type        = string
  default     = null
}

# Custom Domain (optional)
variable "custom_domain_name" {
  description = "Custom domain name for API Gateway"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for custom domain"
  type        = string
  default     = ""
}

# VPC Configuration (for PRIVATE endpoints)
variable "vpc_endpoint_ids" {
  description = "List of VPC Endpoint IDs for PRIVATE API Gateway"
  type        = list(string)
  default     = []
}

# Resource Policy
variable "resource_policy" {
  description = "JSON policy document for API Gateway resource policy"
  type        = string
  default     = ""
}

# API Models and Schemas
variable "enable_request_validation" {
  description = "Enable request validation using models"
  type        = bool
  default     = true
}

# Rate Limiting per Method (optional override)
variable "method_throttle_settings" {
  description = "Per-method throttle settings"
  type = map(object({
    rate_limit  = number
    burst_limit = number
  }))
  default = {}
}

# API Documentation
variable "api_description" {
  description = "Description of the API"
  type        = string
  default     = "AI-powered PowerPoint presentation generation API"
}

# Deployment Configuration
variable "deployment_description" {
  description = "Description for API deployment"
  type        = string
  default     = "Automated deployment via Terraform"
}

# Stage Variables
variable "stage_variables" {
  description = "Map of stage variables"
  type        = map(string)
  default     = {}
}

# Cache Configuration
variable "cache_cluster_enabled" {
  description = "Enable API Gateway caching"
  type        = bool
  default     = false
}

variable "cache_cluster_size" {
  description = "Size of the cache cluster (GB)"
  type        = string
  default     = "0.5"
  validation {
    condition     = contains(["0.5", "1.6", "6.1", "13.5", "28.4", "58.2", "118", "237"], var.cache_cluster_size)
    error_message = "Cache cluster size must be a valid API Gateway cache size"
  }
}

# Canary Release Configuration
variable "canary_settings" {
  description = "Canary release settings for staged deployments"
  type = object({
    percent_traffic          = number
    stage_variable_overrides = map(string)
    use_stage_cache         = bool
  })
  default = null
}