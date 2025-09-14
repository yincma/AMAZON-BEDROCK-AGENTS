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

# Lambda性能优化配置
variable "lambda_reserved_concurrency" {
  description = "Lambda预留并发执行数"
  type        = number
  default     = 10  # 预留10个并发，避免冷启动
}

variable "lambda_provisioned_concurrency" {
  description = "Lambda预配置并发数（用于消除冷启动）"
  type        = number
  default     = 2  # 预热2个实例
}

variable "enable_lambda_snapstart" {
  description = "是否启用Lambda SnapStart（Java运行时）"
  type        = bool
  default     = false
}

variable "lambda_ephemeral_storage" {
  description = "Lambda临时存储大小（MB）"
  type        = number
  default     = 512  # 默认512MB，最大10240MB
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

# IAM Policy for Lambda - 遵循最小权限原则
resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3权限 - 仅限特定桶
      {
        Sid    = "S3ObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObjectVersion"
        ]
        Resource = "${aws_s3_bucket.presentations.arn}/*"
      },
      {
        Sid    = "S3BucketAccess"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning"
        ]
        Resource = aws_s3_bucket.presentations.arn
      },
      # Bedrock权限 - 特定模型
      {
        Sid    = "BedrockModelAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-*",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-instant-*",
          "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.nova-*"
        ]
      },
      # Lambda自调用权限（异步模式）
      {
        Sid    = "LambdaSelfInvoke"
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
          "lambda:InvokeAsync"
        ]
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:ai-ppt-generate-${var.environment}"
        ]
      },
      # CloudWatch Logs权限 - 限制到特定日志组
      {
        Sid    = "CloudWatchLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/ai-ppt-*"
        ]
      },
      # DynamoDB权限 - 仅限特定表
      {
        Sid    = "DynamoDBTableAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          aws_dynamodb_table.presentations.arn,
          "${aws_dynamodb_table.presentations.arn}/index/*"
        ]
      },
      # X-Ray追踪权限
      {
        Sid    = "XRayAccess"
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"  # X-Ray需要通配符
      },
      # KMS权限（用于S3加密）
      {
        Sid    = "KMSAccess"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "arn:aws:kms:${var.aws_region}:${data.aws_caller_identity.current.account_id}:key/*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = "s3.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}

# VPC权限（如果启用VPC）
resource "aws_iam_role_policy" "lambda_vpc_policy" {
  count = var.enable_vpc ? 1 : 0
  name  = "lambda-vpc-policy"
  role  = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "VPCNetworkInterfaceAccess"
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda基础执行策略附加
resource "aws_iam_role_policy_attachment" "lambda_main_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# 自动构建Lambda部署包
resource "null_resource" "build_lambda_package" {
  triggers = {
    # 当Lambda代码或依赖发生变化时重新构建
    lambda_code_hash = filemd5("../lambdas/generate_ppt_complete.py")
    build_script_hash = filemd5("../scripts/build_lambda.sh")
    # 添加其他关键文件的hash以触发重建
    image_generator_hash = filemd5("../lambdas/image_generator.py")
    # 使用timestamp确保每次都重新构建（可选，开发阶段使用）
    # always_rebuild = timestamp()
  }

  provisioner "local-exec" {
    command = "cd ${path.module}/.. && bash scripts/build_lambda.sh"
    interpreter = ["bash", "-c"]
  }
}

# Lambda函数间调用权限
resource "aws_iam_role_policy" "lambda_invoke_policy" {
  name = "lambda-invoke-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaInvokeAccess"
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
          "lambda:InvokeAsync"
        ]
        Resource = [
          "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:ai-ppt-*"
        ]
      }
    ]
  })
}

# Lambda Function - API Handler（优化配置）
resource "aws_lambda_function" "api_handler" {
  filename         = "../lambda-packages/api_handler.zip"
  function_name    = "ai-ppt-api-handler-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.handler"
  runtime         = "python3.11"
  memory_size     = 1024  # 降低内存，API Handler不需要太多内存
  timeout         = 30

  # 预留并发执行数，避免冷启动
  # 注释掉以避免账户并发限制问题
  # reserved_concurrent_executions = 5

  # 临时存储配置
  ephemeral_storage {
    size = 512  # MB
  }

  # 启用X-Ray追踪
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.presentations.id
      ENVIRONMENT = var.environment
      # 性能优化环境变量
      PYTHONPATH = "/opt/python"
      PYTHONDONTWRITEBYTECODE = "1"  # 不生成.pyc文件，减少磁盘I/O
      PYTHONUNBUFFERED = "1"  # 无缓冲输出，实时日志
    }
  }

  tags = {
    Environment = var.environment
    Project     = "ai-ppt-assistant"
  }
}

# Lambda Function - Generate PPT Complete（优化配置）
resource "aws_lambda_function" "generate_ppt" {
  filename         = "../lambda-packages/generate_ppt_complete.zip"
  function_name    = "ai-ppt-generate-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "generate_ppt_complete.lambda_handler"
  runtime         = "python3.11"
  memory_size     = 3008  # 增加内存到3GB，获得2个vCPU，提升计算性能
  timeout         = 300   # 保持5分钟超时

  # 当ZIP文件内容变化时自动更新Lambda
  # 注意：这个hash在null_resource构建后会变化，所以只在文件存在时计算
  source_code_hash = fileexists("../lambda-packages/generate_ppt_complete.zip") ? filebase64sha256("../lambda-packages/generate_ppt_complete.zip") : null

  # 确保在构建脚本完成后才部署Lambda
  depends_on = [null_resource.build_lambda_package]

  # 预留并发执行数
  # 注释掉以避免账户并发限制问题
  # reserved_concurrent_executions = var.lambda_reserved_concurrency

  # 临时存储配置（用于PPT生成的临时文件）
  ephemeral_storage {
    size = 2048  # 2GB临时存储
  }

  # 启用X-Ray追踪
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.presentations.id
      ENVIRONMENT = var.environment
      ENABLE_ASYNC_MODE = "true"  # 启用异步模式
      # 性能优化环境变量
      PYTHONPATH = "/opt/python"
      PYTHONDONTWRITEBYTECODE = "1"
      PYTHONUNBUFFERED = "1"
      # Bedrock优化
      BEDROCK_MAX_RETRIES = "3"
      BEDROCK_TIMEOUT = "120"
      # 并发控制
      MAX_CONCURRENT_BEDROCK_CALLS = "5"
      # 缓存配置
      ENABLE_RESPONSE_CACHE = "true"
      CACHE_TTL = "3600"
    }
  }

  tags = {
    Environment = var.environment
    Project     = "ai-ppt-assistant"
  }
}

# Lambda Function - Status Check（优化配置）
resource "aws_lambda_function" "status_check" {
  filename         = "../lambda-packages/status_check.zip"
  function_name    = "ai-ppt-status-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.handler"
  runtime         = "python3.11"
  memory_size     = 512   # 降低内存，状态检查不需要太多资源
  timeout         = 10    # 降低超时，状态检查应该很快

  # 预留并发执行数
  # 注释掉以避免账户并发限制问题
  # reserved_concurrent_executions = 5

  # 临时存储配置
  ephemeral_storage {
    size = 512  # MB
  }

  # 启用X-Ray追踪
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.presentations.id
      ENVIRONMENT = var.environment
      # 性能优化环境变量
      PYTHONPATH = "/opt/python"
      PYTHONDONTWRITEBYTECODE = "1"
      PYTHONUNBUFFERED = "1"
      # DynamoDB优化
      DYNAMODB_MAX_RETRIES = "2"
      DYNAMODB_TIMEOUT = "5"
    }
  }

  tags = {
    Environment = var.environment
    Project     = "ai-ppt-assistant"
  }
}

# Lambda Function - Download PPT（优化配置）
resource "aws_lambda_function" "download_ppt" {
  filename         = "../lambda-packages/download_ppt.zip"
  function_name    = "ai-ppt-download-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.handler"
  runtime         = "python3.11"
  memory_size     = 1024  # 保持1GB用于文件传输
  timeout         = 30

  # 预留并发执行数
  # 注释掉以避免账户并发限制问题
  # reserved_concurrent_executions = 5

  # 临时存储配置
  ephemeral_storage {
    size = 1024  # 1GB用于临时文件存储
  }

  # 启用X-Ray追踪
  tracing_config {
    mode = var.enable_xray_tracing ? "Active" : "PassThrough"
  }

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.presentations.id
      ENVIRONMENT = var.environment
      # 性能优化环境变量
      PYTHONPATH = "/opt/python"
      PYTHONDONTWRITEBYTECODE = "1"
      PYTHONUNBUFFERED = "1"
      # S3优化
      S3_TRANSFER_ACCELERATION = "true"
      S3_MAX_RETRIES = "3"
      S3_TIMEOUT = "20"
      # 预签名URL配置
      PRESIGNED_URL_EXPIRY = "3600"  # 1小时有效期
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

# Gateway Response for 4XX errors with CORS headers
resource "aws_api_gateway_gateway_response" "response_4xx" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Accept'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
  }

  response_templates = {
    "application/json" = "{\"error\":\"$context.error.message\",\"requestId\":\"$context.requestId\"}"
  }
}

# Gateway Response for 5XX errors with CORS headers
resource "aws_api_gateway_gateway_response" "response_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Accept'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
  }

  response_templates = {
    "application/json" = "{\"error\":\"Internal server error\",\"requestId\":\"$context.requestId\"}"
  }
}

# Gateway Response for timeout errors with CORS headers
resource "aws_api_gateway_gateway_response" "timeout" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  response_type = "INTEGRATION_TIMEOUT"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Accept'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
  }

  response_templates = {
    "application/json" = "{\"error\":\"Request timeout\",\"requestId\":\"$context.requestId\"}"
  }
}

# Gateway Response for missing authentication token with CORS headers
resource "aws_api_gateway_gateway_response" "missing_authentication_token" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  response_type = "MISSING_AUTHENTICATION_TOKEN"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Accept'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
  }

  response_templates = {
    "application/json" = "{\"error\":\"Missing authentication token\",\"requestId\":\"$context.requestId\"}"
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
    "method.response.header.Access-Control-Max-Age"       = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "generate_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.generate.id
  http_method = aws_api_gateway_method.generate_options.http_method
  status_code = aws_api_gateway_method_response.generate_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Accept,Accept-Language'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }

  depends_on = [
    aws_api_gateway_integration.generate_options
  ]
}

# Method Response for POST /generate
resource "aws_api_gateway_method_response" "generate_post" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.generate.id
  http_method = aws_api_gateway_method.generate_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }

  response_models = {
    "application/json" = "Empty"
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
    "method.response.header.Access-Control-Max-Age"       = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_options.http_method
  status_code = aws_api_gateway_method_response.status_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Accept,Accept-Language'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }

  depends_on = [
    aws_api_gateway_integration.status_options
  ]
}

# Method Response for GET /status/{id}
resource "aws_api_gateway_method_response" "status_get" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_get.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Credentials" = true
  }

  response_models = {
    "application/json" = "Empty"
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
    "method.response.header.Access-Control-Max-Age"       = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "download_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.download_id.id
  http_method = aws_api_gateway_method.download_options.http_method
  status_code = aws_api_gateway_method_response.download_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Accept,Accept-Language'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
    "method.response.header.Access-Control-Max-Age"       = "'86400'"
  }

  depends_on = [
    aws_api_gateway_integration.download_options
  ]
}

# Method Response for GET /download/{id}
resource "aws_api_gateway_method_response" "download_get" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.download_id.id
  http_method = aws_api_gateway_method.download_get.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin"      = true
    "method.response.header.Access-Control-Allow-Headers"     = true
    "method.response.header.Access-Control-Allow-Credentials" = true
    "method.response.header.Content-Type"                     = true
    "method.response.header.Content-Disposition"              = true
  }

  response_models = {
    "application/json"              = "Empty"
    "application/vnd.ms-powerpoint" = "Empty"
  }
}

# API Gateway Deployment with automatic triggers
resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = var.environment  # 直接在deployment中管理stage

  # Trigger redeployment when configuration changes
  triggers = {
    redeployment = sha1(jsonencode([
      # Include all method configurations
      aws_api_gateway_method.generate_post.id,
      aws_api_gateway_method.generate_options.id,
      aws_api_gateway_method.status_get.id,
      # Include gateway responses for CORS
      aws_api_gateway_gateway_response.response_4xx.id,
      aws_api_gateway_gateway_response.response_5xx.id,
      aws_api_gateway_gateway_response.timeout.id,
      aws_api_gateway_gateway_response.missing_authentication_token.id,
      aws_api_gateway_method.status_options.id,
      aws_api_gateway_method.download_get.id,
      aws_api_gateway_method.download_options.id,

      # Include all integration configurations
      aws_api_gateway_integration.generate_integration.id,
      aws_api_gateway_integration.generate_options.id,
      aws_api_gateway_integration.status_integration.id,
      aws_api_gateway_integration.status_options.id,
      aws_api_gateway_integration.download_integration.id,
      aws_api_gateway_integration.download_options.id,

      # Include all integration response configurations
      aws_api_gateway_integration_response.generate_options.id,
      aws_api_gateway_integration_response.status_options.id,
      aws_api_gateway_integration_response.download_options.id,

      # Include all method response configurations
      aws_api_gateway_method_response.generate_post.id,
      aws_api_gateway_method_response.generate_options.id,
      aws_api_gateway_method_response.status_get.id,
      aws_api_gateway_method_response.status_options.id,
      aws_api_gateway_method_response.download_get.id,
      aws_api_gateway_method_response.download_options.id,

      # Include resource configurations
      aws_api_gateway_resource.generate.id,
      aws_api_gateway_resource.status.id,
      aws_api_gateway_resource.status_id.id,
      aws_api_gateway_resource.download.id,
      aws_api_gateway_resource.download_id.id
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    # Methods
    aws_api_gateway_method.generate_post,
    aws_api_gateway_method.generate_options,
    aws_api_gateway_method.status_get,
    aws_api_gateway_method.status_options,
    aws_api_gateway_method.download_get,
    aws_api_gateway_method.download_options,

    # Integrations
    aws_api_gateway_integration.generate_integration,
    aws_api_gateway_integration.generate_options,
    aws_api_gateway_integration.status_integration,
    aws_api_gateway_integration.status_options,
    aws_api_gateway_integration.download_integration,
    aws_api_gateway_integration.download_options,

    # Integration Responses
    aws_api_gateway_integration_response.generate_options,
    aws_api_gateway_integration_response.status_options,
    aws_api_gateway_integration_response.download_options,

    # Method Responses
    aws_api_gateway_method_response.generate_post,
    aws_api_gateway_method_response.generate_options,
    aws_api_gateway_method_response.status_get,
    aws_api_gateway_method_response.status_options,
    aws_api_gateway_method_response.download_get,
    aws_api_gateway_method_response.download_options,

    # Gateway Responses for CORS
    aws_api_gateway_gateway_response.response_4xx,
    aws_api_gateway_gateway_response.response_5xx,
    aws_api_gateway_gateway_response.timeout,
    aws_api_gateway_gateway_response.missing_authentication_token
  ]
}

# API Gateway Stage with proper configuration
# 注释掉独立的stage资源，因为deployment已经创建了stage
# resource "aws_api_gateway_stage" "api" {
#   deployment_id = aws_api_gateway_deployment.api.id
#   rest_api_id   = aws_api_gateway_rest_api.api.id
#   stage_name    = var.environment
#
#   # Enable CloudWatch logging
#   xray_tracing_enabled = var.enable_xray_tracing
#
#   # 缓存集群配置（可选，需要额外成本）
#   # cache_cluster_enabled = true
#   # cache_cluster_size   = "0.5"  # 0.5 GB缓存
#
#   # Stage settings
#   variables = {
#     environment = var.environment
#     deployed_at = timestamp()
#   }
#
#   tags = {
#     Environment = var.environment
#     Project     = var.project_name
#   }
# }

# Lambda Permissions for API Gateway - 限制到特定路径和方法
resource "aws_lambda_permission" "api_gateway_generate" {
  statement_id  = "AllowAPIGatewayInvokeGenerate"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.generate_ppt.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/POST/generate"
}

resource "aws_lambda_permission" "api_gateway_status" {
  statement_id  = "AllowAPIGatewayInvokeStatus"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.status_check.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/GET/status/*"
}

resource "aws_lambda_permission" "api_gateway_download" {
  statement_id  = "AllowAPIGatewayInvokeDownload"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.download_ppt.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/GET/download/*"
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

# API Gateway Method Settings for better performance
resource "aws_api_gateway_method_settings" "api_settings" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = var.environment
  method_path = "*/*"

  settings {
    metrics_enabled        = var.enable_monitoring
    logging_level         = var.log_level == "DEBUG" ? "INFO" : "ERROR"
    data_trace_enabled    = var.log_level == "DEBUG"
    throttling_burst_limit = 5000
    throttling_rate_limit  = 10000
    caching_enabled       = false  # 全局缓存关闭，仅在特定端点启用
  }

  depends_on = [
    aws_api_gateway_deployment.api
  ]
}

# API Gateway缓存策略 - 仅对GET请求启用
resource "aws_api_gateway_method_settings" "status_cache" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = var.environment
  method_path = "status/*/GET"  # 仅对status端点的GET请求启用缓存

  settings {
    metrics_enabled        = var.enable_monitoring
    logging_level         = var.log_level == "DEBUG" ? "INFO" : "ERROR"
    data_trace_enabled    = var.log_level == "DEBUG"
    throttling_burst_limit = 5000
    throttling_rate_limit  = 10000
    caching_enabled       = true
    cache_ttl_in_seconds  = 30  # 30秒缓存
    cache_data_encrypted  = true
  }

  depends_on = [
    aws_api_gateway_deployment.api
  ]
}

resource "aws_api_gateway_method_settings" "download_cache" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = var.environment
  method_path = "download/*/GET"  # 对download端点的GET请求启用缓存

  settings {
    metrics_enabled        = var.enable_monitoring
    logging_level         = var.log_level == "DEBUG" ? "INFO" : "ERROR"
    data_trace_enabled    = var.log_level == "DEBUG"
    throttling_burst_limit = 5000
    throttling_rate_limit  = 10000
    caching_enabled       = true
    cache_ttl_in_seconds  = 300  # 5分钟缓存
    cache_data_encrypted  = true
  }

  depends_on = [
    aws_api_gateway_deployment.api
  ]
}

# Lambda预配置并发（消除冷启动）
# 注释掉，因为需要先发布Lambda版本才能使用
# resource "aws_lambda_provisioned_concurrency_config" "generate_ppt_concurrency" {
#   count = var.lambda_provisioned_concurrency > 0 ? 1 : 0
#
#   function_name                     = aws_lambda_function.generate_ppt.function_name
#   provisioned_concurrent_executions = var.lambda_provisioned_concurrency
#   qualifier                         = aws_lambda_function.generate_ppt.version
#
#   depends_on = [aws_lambda_function.generate_ppt]
# }

# API Gateway使用计划和API密钥（可选，用于限流管理）
resource "aws_api_gateway_usage_plan" "api_usage_plan" {
  name         = "${var.project_name}-usage-plan-${var.environment}"
  description  = "Usage plan for API rate limiting"

  api_stages {
    api_id = aws_api_gateway_rest_api.api.id
    stage  = var.environment
  }

  quota_settings {
    limit  = 10000  # 每天10000个请求
    period = "DAY"
  }

  throttle_settings {
    rate_limit  = 100   # 每秒100个请求
    burst_limit = 200   # 突发200个请求
  }

  depends_on = [aws_api_gateway_deployment.api]
}

# API密钥（可选）
resource "aws_api_gateway_api_key" "api_key" {
  name        = "${var.project_name}-api-key-${var.environment}"
  description = "API key for ${var.project_name}"
  enabled     = true
}

# 关联API密钥到使用计划
resource "aws_api_gateway_usage_plan_key" "api_usage_plan_key" {
  key_id        = aws_api_gateway_api_key.api_key.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.api_usage_plan.id
}

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