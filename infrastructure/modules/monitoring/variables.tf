# Variables for CloudWatch Monitoring Module

# ============================================================================
# General Configuration
# ============================================================================

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  
  validation {
    condition     = length(var.project_name) > 0 && length(var.project_name) <= 50
    error_message = "Project name must be between 1 and 50 characters."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}

# ============================================================================
# SNS Configuration
# ============================================================================

variable "alert_email_addresses" {
  description = "List of email addresses to receive alerts"
  type        = list(string)
  default     = []
  
  validation {
    condition = alltrue([
      for email in var.alert_email_addresses :
      can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", email))
    ])
    error_message = "All email addresses must be valid."
  }
}

# ============================================================================
# Lambda Function Configuration
# ============================================================================

variable "lambda_function_names" {
  description = "Map of Lambda function names to monitor (key = short_name, value = full_function_name)"
  type        = map(string)
  default     = {}
}

# Lambda Error Alarm Configuration
variable "lambda_error_threshold" {
  description = "Threshold for Lambda function error count"
  type        = number
  default     = 5
  
  validation {
    condition     = var.lambda_error_threshold > 0
    error_message = "Lambda error threshold must be greater than 0."
  }
}

variable "lambda_error_alarm_period" {
  description = "Period in seconds for Lambda error alarm"
  type        = number
  default     = 300
  
  validation {
    condition     = contains([60, 300, 900, 3600], var.lambda_error_alarm_period)
    error_message = "Lambda error alarm period must be one of: 60, 300, 900, 3600."
  }
}

variable "lambda_error_evaluation_periods" {
  description = "Number of evaluation periods for Lambda error alarm"
  type        = number
  default     = 2
  
  validation {
    condition     = var.lambda_error_evaluation_periods >= 1 && var.lambda_error_evaluation_periods <= 5
    error_message = "Lambda error evaluation periods must be between 1 and 5."
  }
}

# Lambda Duration Alarm Configuration
variable "lambda_duration_threshold" {
  description = "Threshold for Lambda function duration in milliseconds"
  type        = number
  default     = 25000
  
  validation {
    condition     = var.lambda_duration_threshold > 0 && var.lambda_duration_threshold <= 900000
    error_message = "Lambda duration threshold must be between 1 and 900000 milliseconds."
  }
}

variable "lambda_duration_alarm_period" {
  description = "Period in seconds for Lambda duration alarm"
  type        = number
  default     = 300
  
  validation {
    condition     = contains([60, 300, 900, 3600], var.lambda_duration_alarm_period)
    error_message = "Lambda duration alarm period must be one of: 60, 300, 900, 3600."
  }
}

variable "lambda_duration_evaluation_periods" {
  description = "Number of evaluation periods for Lambda duration alarm"
  type        = number
  default     = 3
  
  validation {
    condition     = var.lambda_duration_evaluation_periods >= 1 && var.lambda_duration_evaluation_periods <= 5
    error_message = "Lambda duration evaluation periods must be between 1 and 5."
  }
}

# Lambda Throttle Alarm Configuration
variable "lambda_throttle_threshold" {
  description = "Threshold for Lambda function throttle count"
  type        = number
  default     = 1
  
  validation {
    condition     = var.lambda_throttle_threshold >= 0
    error_message = "Lambda throttle threshold must be greater than or equal to 0."
  }
}

variable "lambda_throttle_alarm_period" {
  description = "Period in seconds for Lambda throttle alarm"
  type        = number
  default     = 300
  
  validation {
    condition     = contains([60, 300, 900, 3600], var.lambda_throttle_alarm_period)
    error_message = "Lambda throttle alarm period must be one of: 60, 300, 900, 3600."
  }
}

variable "lambda_throttle_evaluation_periods" {
  description = "Number of evaluation periods for Lambda throttle alarm"
  type        = number
  default     = 1
  
  validation {
    condition     = var.lambda_throttle_evaluation_periods >= 1 && var.lambda_throttle_evaluation_periods <= 5
    error_message = "Lambda throttle evaluation periods must be between 1 and 5."
  }
}

# ============================================================================
# API Gateway Configuration
# ============================================================================

variable "api_gateway_name" {
  description = "Name of the API Gateway to monitor"
  type        = string
}

variable "api_gateway_stage" {
  description = "Stage name of the API Gateway to monitor"
  type        = string
  default     = "dev"
}

# API Gateway 4XX Error Alarm Configuration
variable "api_4xx_threshold" {
  description = "Threshold for API Gateway 4XX error count"
  type        = number
  default     = 10
  
  validation {
    condition     = var.api_4xx_threshold > 0
    error_message = "API 4XX error threshold must be greater than 0."
  }
}

variable "api_4xx_alarm_period" {
  description = "Period in seconds for API Gateway 4XX error alarm"
  type        = number
  default     = 300
  
  validation {
    condition     = contains([60, 300, 900, 3600], var.api_4xx_alarm_period)
    error_message = "API 4XX alarm period must be one of: 60, 300, 900, 3600."
  }
}

variable "api_4xx_evaluation_periods" {
  description = "Number of evaluation periods for API Gateway 4XX error alarm"
  type        = number
  default     = 2
  
  validation {
    condition     = var.api_4xx_evaluation_periods >= 1 && var.api_4xx_evaluation_periods <= 5
    error_message = "API 4XX evaluation periods must be between 1 and 5."
  }
}

# API Gateway 5XX Error Alarm Configuration
variable "api_5xx_threshold" {
  description = "Threshold for API Gateway 5XX error count"
  type        = number
  default     = 5
  
  validation {
    condition     = var.api_5xx_threshold > 0
    error_message = "API 5XX error threshold must be greater than 0."
  }
}

variable "api_5xx_alarm_period" {
  description = "Period in seconds for API Gateway 5XX error alarm"
  type        = number
  default     = 300
  
  validation {
    condition     = contains([60, 300, 900, 3600], var.api_5xx_alarm_period)
    error_message = "API 5XX alarm period must be one of: 60, 300, 900, 3600."
  }
}

variable "api_5xx_evaluation_periods" {
  description = "Number of evaluation periods for API Gateway 5XX error alarm"
  type        = number
  default     = 1
  
  validation {
    condition     = var.api_5xx_evaluation_periods >= 1 && var.api_5xx_evaluation_periods <= 5
    error_message = "API 5XX evaluation periods must be between 1 and 5."
  }
}

# API Gateway Latency Alarm Configuration
variable "api_latency_threshold" {
  description = "Threshold for API Gateway latency in milliseconds"
  type        = number
  default     = 10000
  
  validation {
    condition     = var.api_latency_threshold > 0
    error_message = "API latency threshold must be greater than 0."
  }
}

variable "api_latency_alarm_period" {
  description = "Period in seconds for API Gateway latency alarm"
  type        = number
  default     = 300
  
  validation {
    condition     = contains([60, 300, 900, 3600], var.api_latency_alarm_period)
    error_message = "API latency alarm period must be one of: 60, 300, 900, 3600."
  }
}

variable "api_latency_evaluation_periods" {
  description = "Number of evaluation periods for API Gateway latency alarm"
  type        = number
  default     = 3
  
  validation {
    condition     = var.api_latency_evaluation_periods >= 1 && var.api_latency_evaluation_periods <= 5
    error_message = "API latency evaluation periods must be between 1 and 5."
  }
}

# API Gateway Request Count Alarm Configuration
variable "api_count_threshold" {
  description = "Threshold for API Gateway request count (high traffic alert)"
  type        = number
  default     = 1000
  
  validation {
    condition     = var.api_count_threshold > 0
    error_message = "API count threshold must be greater than 0."
  }
}

variable "api_count_alarm_period" {
  description = "Period in seconds for API Gateway request count alarm"
  type        = number
  default     = 300
  
  validation {
    condition     = contains([60, 300, 900, 3600], var.api_count_alarm_period)
    error_message = "API count alarm period must be one of: 60, 300, 900, 3600."
  }
}

variable "api_count_evaluation_periods" {
  description = "Number of evaluation periods for API Gateway request count alarm"
  type        = number
  default     = 2
  
  validation {
    condition     = var.api_count_evaluation_periods >= 1 && var.api_count_evaluation_periods <= 5
    error_message = "API count evaluation periods must be between 1 and 5."
  }
}

# ============================================================================
# DynamoDB Configuration
# ============================================================================

variable "enable_dynamodb_monitoring" {
  description = "Whether to enable DynamoDB monitoring alarms"
  type        = bool
  default     = true
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB table to monitor"
  type        = string
  default     = ""
}

variable "dynamodb_throttle_threshold" {
  description = "Threshold for DynamoDB throttle events"
  type        = number
  default     = 1
  
  validation {
    condition     = var.dynamodb_throttle_threshold >= 0
    error_message = "DynamoDB throttle threshold must be greater than or equal to 0."
  }
}

variable "dynamodb_throttle_alarm_period" {
  description = "Period in seconds for DynamoDB throttle alarm"
  type        = number
  default     = 300
  
  validation {
    condition     = contains([60, 300, 900, 3600], var.dynamodb_throttle_alarm_period)
    error_message = "DynamoDB throttle alarm period must be one of: 60, 300, 900, 3600."
  }
}

variable "dynamodb_throttle_evaluation_periods" {
  description = "Number of evaluation periods for DynamoDB throttle alarm"
  type        = number
  default     = 1
  
  validation {
    condition     = var.dynamodb_throttle_evaluation_periods >= 1 && var.dynamodb_throttle_evaluation_periods <= 5
    error_message = "DynamoDB throttle evaluation periods must be between 1 and 5."
  }
}

# ============================================================================
# General Monitoring Configuration
# ============================================================================

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
  
  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653
    ], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}