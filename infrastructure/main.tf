terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "ai-ppt-assistant"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name"
  type        = string
  default     = "ai-ppt-presentations"
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = ""
}

# Lambda配置变量
variable "enable_vpc" {
  description = "是否启用VPC配置"
  type        = bool
  default     = false
}

variable "enable_lambda_url" {
  description = "是否启用Lambda函数URL"
  type        = bool
  default     = true
}

variable "private_subnet_ids" {
  description = "私有子网ID列表（当enable_vpc为true时需要）"
  type        = list(string)
  default     = []
}

variable "lambda_timeout_seconds" {
  description = "Lambda函数超时时间（秒）"
  type        = number
  default     = 300
}

variable "lambda_memory_mb" {
  description = "Lambda函数内存大小（MB）"
  type        = number
  default     = 1024
}

# 图片处理配置变量
variable "nova_model_id" {
  description = "Amazon Nova模型ID"
  type        = string
  default     = "amazon.nova-canvas-v1:0"
}

variable "default_image_width" {
  description = "默认图片宽度"
  type        = number
  default     = 1200
}

variable "default_image_height" {
  description = "默认图片高度"
  type        = number
  default     = 800
}

variable "max_retry_attempts" {
  description = "最大重试次数"
  type        = number
  default     = 3
}

# 性能配置变量
variable "enable_caching" {
  description = "是否启用缓存"
  type        = bool
  default     = true
}

variable "enable_monitoring" {
  description = "是否启用监控"
  type        = bool
  default     = true
}

variable "enable_batching" {
  description = "是否启用批处理"
  type        = bool
  default     = true
}

variable "cache_ttl_seconds" {
  description = "缓存TTL时间（秒）"
  type        = number
  default     = 3600
}

# 安全配置变量
variable "enable_xray_tracing" {
  description = "是否启用X-Ray追踪"
  type        = bool
  default     = true
}

variable "log_level" {
  description = "日志级别"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "日志级别必须是 DEBUG, INFO, WARNING, 或 ERROR 之一。"
  }
}

# Data sources
data "aws_vpc" "default" {
  default = true
}
data "aws_caller_identity" "current" {}

# DynamoDB Table for presentation metadata
resource "aws_dynamodb_table" "presentations" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "presentation_id"

  attribute {
    name = "presentation_id"
    type = "S"
  }

  tags = {
    Name        = "${var.project_name}-presentations"
    Environment = var.environment
  }
}

# S3 Bucket for PPT storage
resource "aws_s3_bucket" "presentations" {
  bucket = "ai-ppt-presentations-${var.environment}-${data.aws_caller_identity.current.account_id}"

  # 允许在桶非空时删除
  force_destroy = true

  tags = {
    Environment = var.environment
    Project     = "ai-ppt-assistant"
  }
}

resource "aws_s3_bucket_versioning" "presentations" {
  bucket = aws_s3_bucket.presentations.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "presentations" {
  bucket = aws_s3_bucket.presentations.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "presentations" {
  bucket = aws_s3_bucket.presentations.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lambda Layer for dependencies
resource "aws_lambda_layer_version" "dependencies" {
  filename            = "../ai-ppt-dependencies-layer.zip"
  layer_name          = "ai-ppt-dependencies-${var.environment}"
  compatible_runtimes = ["python3.11"]
  description         = "Dependencies for AI PPT Assistant"
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "ai-ppt-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.presentations.arn}/*"
      },
      {
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = aws_s3_bucket.presentations.arn
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*:*:foundation-model/anthropic.claude-*",
          "arn:aws:bedrock:*:*:foundation-model/amazon.nova-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.presentations.arn
        ]
      }
    ]
  })
}

# Lambda Function - API Handler
resource "aws_lambda_function" "api_handler" {
  filename         = "../lambda-packages/api_handler.zip"
  function_name    = "ai-ppt-api-handler-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.handler"
  runtime         = "python3.11"
  memory_size     = 2048
  timeout         = 30

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.presentations.id
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Environment = var.environment
    Project     = "ai-ppt-assistant"
  }
}

# Lambda Function - Generate PPT Complete
resource "aws_lambda_function" "generate_ppt" {
  filename         = "../lambda-packages/generate_ppt_complete.zip"
  function_name    = "ai-ppt-generate-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.handler"
  runtime         = "python3.11"
  memory_size     = 2048
  timeout         = 300

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.presentations.id
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Environment = var.environment
    Project     = "ai-ppt-assistant"
  }
}

# Lambda Function - Status Check
resource "aws_lambda_function" "status_check" {
  filename         = "../lambda-packages/status_check.zip"
  function_name    = "ai-ppt-status-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.handler"
  runtime         = "python3.11"
  memory_size     = 1024
  timeout         = 30

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.presentations.id
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Environment = var.environment
    Project     = "ai-ppt-assistant"
  }
}

# Lambda Function - Download PPT
resource "aws_lambda_function" "download_ppt" {
  filename         = "../lambda-packages/download_ppt.zip"
  function_name    = "ai-ppt-download-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.handler"
  runtime         = "python3.11"
  memory_size     = 1024
  timeout         = 30

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.presentations.id
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Environment = var.environment
    Project     = "ai-ppt-assistant"
  }
}

# API Gateway
resource "aws_api_gateway_rest_api" "api" {
  name        = "ai-ppt-api-${var.environment}"
  description = "AI PPT Generation API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# /generate endpoint
resource "aws_api_gateway_resource" "generate" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "generate"
}

resource "aws_api_gateway_method" "generate_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.generate.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "generate_integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.generate.id
  http_method = aws_api_gateway_method.generate_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.generate_ppt.invoke_arn
}

# CORS for /generate
resource "aws_api_gateway_method" "generate_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.generate.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "generate_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.generate.id
  http_method = aws_api_gateway_method.generate_options.http_method

  type = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "generate_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.generate.id
  http_method = aws_api_gateway_method.generate_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "generate_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.generate.id
  http_method = aws_api_gateway_method.generate_options.http_method
  status_code = aws_api_gateway_method_response.generate_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Method Response for POST /generate
resource "aws_api_gateway_method_response" "generate_post" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.generate.id
  http_method = aws_api_gateway_method.generate_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# /status/{id} endpoint
resource "aws_api_gateway_resource" "status" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "status"
}

resource "aws_api_gateway_resource" "status_id" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.status.id
  path_part   = "{id}"
}

resource "aws_api_gateway_method" "status_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.status_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "status_integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.status_check.invoke_arn
}

# CORS for /status/{id}
resource "aws_api_gateway_method" "status_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.status_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_options.http_method

  type = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_options.http_method
  status_code = aws_api_gateway_method_response.status_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Method Response for GET /status/{id}
resource "aws_api_gateway_method_response" "status_get" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_get.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# /download/{id} endpoint
resource "aws_api_gateway_resource" "download" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "download"
}

resource "aws_api_gateway_resource" "download_id" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.download.id
  path_part   = "{id}"
}

resource "aws_api_gateway_method" "download_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.download_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "download_integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.download_id.id
  http_method = aws_api_gateway_method.download_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.download_ppt.invoke_arn
}

# CORS for /download/{id}
resource "aws_api_gateway_method" "download_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.download_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "download_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.download_id.id
  http_method = aws_api_gateway_method.download_options.http_method

  type = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "download_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.download_id.id
  http_method = aws_api_gateway_method.download_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "download_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.download_id.id
  http_method = aws_api_gateway_method.download_options.http_method
  status_code = aws_api_gateway_method_response.download_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Method Response for GET /download/{id}
resource "aws_api_gateway_method_response" "download_get" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.download_id.id
  http_method = aws_api_gateway_method.download_get.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = var.environment

  depends_on = [
    aws_api_gateway_integration.generate_integration,
    aws_api_gateway_integration.generate_options,
    aws_api_gateway_integration_response.generate_options,
    aws_api_gateway_method_response.generate_post,
    aws_api_gateway_integration.status_integration,
    aws_api_gateway_integration.status_options,
    aws_api_gateway_integration_response.status_options,
    aws_api_gateway_method_response.status_get,
    aws_api_gateway_integration.download_integration,
    aws_api_gateway_integration.download_options,
    aws_api_gateway_integration_response.download_options,
    aws_api_gateway_method_response.download_get
  ]
}

# Lambda Permissions for API Gateway
resource "aws_lambda_permission" "api_gateway_generate" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.generate_ppt.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_status" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status_check.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_download" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.download_ppt.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# CloudWatch Log Groups
# 注释掉以避免与monitoring.tf中的定义冲突
# resource "aws_cloudwatch_log_group" "lambda_logs" {
#   for_each = {
#     api_handler  = aws_lambda_function.api_handler.function_name
#     generate_ppt = aws_lambda_function.generate_ppt.function_name
#     status_check = aws_lambda_function.status_check.function_name
#     download_ppt = aws_lambda_function.download_ppt.function_name
#   }
#
#   name              = "/aws/lambda/${each.value}"
#   retention_in_days = 7
# }

# Outputs
output "api_gateway_url" {
  value       = "https://${aws_api_gateway_rest_api.api.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
  description = "API Gateway URL"
}

output "s3_bucket_name" {
  value       = aws_s3_bucket.presentations.id
  description = "S3 bucket name"
}

output "lambda_functions" {
  value = {
    api_handler  = aws_lambda_function.api_handler.function_name
    generate_ppt = aws_lambda_function.generate_ppt.function_name
    status_check = aws_lambda_function.status_check.function_name
    download_ppt = aws_lambda_function.download_ppt.function_name
  }
  description = "Lambda function names"
}