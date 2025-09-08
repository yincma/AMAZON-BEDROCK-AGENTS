variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "lifecycle_rules" {
  description = "S3 lifecycle rules configuration"
  type = object({
    transition_to_ia_days      = number
    noncurrent_expiration_days = number
  })
  default = {
    transition_to_ia_days      = 30
    noncurrent_expiration_days = 30
  }
}

variable "cors_configuration" {
  description = "CORS configuration for the S3 bucket"
  type = object({
    allowed_headers = list(string)
    allowed_methods = list(string)
    allowed_origins = list(string)
    expose_headers  = list(string)
    max_age_seconds = number
  })
  default = {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "PUT", "POST"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

variable "enable_cloudfront" {
  description = "Whether to enable CloudFront integration"
  type        = bool
  default     = false
}

variable "cloudfront_oai_arn" {
  description = "CloudFront Origin Access Identity ARN"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
