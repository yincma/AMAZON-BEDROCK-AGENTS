# API Gateway CORS Module Variables

variable "rest_api_id" {
  description = "The ID of the REST API"
  type        = string
}

variable "resource_id" {
  description = "The ID of the API Gateway resource"
  type        = string
}

variable "allowed_origins" {
  description = "List of allowed origins for CORS"
  type        = list(string)
  default     = ["*"]
}

variable "allowed_methods" {
  description = "List of allowed HTTP methods"
  type        = list(string)
  default     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
}

variable "allowed_headers" {
  description = "List of allowed headers"
  type        = list(string)
  default = [
    "Content-Type",
    "X-Amz-Date",
    "Authorization",
    "X-Api-Key",
    "X-Amz-Security-Token"
  ]
}

variable "max_age_seconds" {
  description = "How long the browser can cache the preflight response"
  type        = number
  default     = 300
}