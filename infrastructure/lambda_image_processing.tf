# Lambda函数配置 - 图片生成服务
# 包含基础版本和优化版本的Lambda函数定义

# Lambda执行角色
resource "aws_iam_role" "image_lambda_role" {
  name = "${var.project_name}-image-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-image-lambda-role"
    Environment = var.environment
    Component   = "ImageProcessing"
  }
}

# Lambda基础执行策略
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.image_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Bedrock访问策略
resource "aws_iam_role_policy" "lambda_bedrock_policy" {
  name = "${var.project_name}-lambda-bedrock-policy-${var.environment}"
  role = aws_iam_role.image_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel"
        ]
        Resource = [
          "arn:aws:bedrock:*::foundation-model/amazon.nova-canvas-v1*",
          "arn:aws:bedrock:*::foundation-model/stability.stable-diffusion-xl-v1*",
          "arn:aws:bedrock:*::foundation-model/*"
        ]
      }
    ]
  })
}

# S3访问策略（用于缓存和存储）
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "${var.project_name}-lambda-s3-policy-${var.environment}"
  role = aws_iam_role.image_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:HeadObject",
          "s3:HeadBucket"
        ]
        Resource = [
          aws_s3_bucket.presentations.arn,
          "${aws_s3_bucket.presentations.arn}/*"
        ]
      }
    ]
  })
}

# CloudWatch监控策略
resource "aws_iam_role_policy" "lambda_cloudwatch_policy" {
  name = "${var.project_name}-lambda-cloudwatch-policy-${var.environment}"
  role = aws_iam_role.image_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}

# DynamoDB访问策略（用于缓存和状态管理）
resource "aws_iam_role_policy" "lambda_dynamodb_policy" {
  name = "${var.project_name}-lambda-dynamodb-policy-${var.environment}"
  role = aws_iam_role.image_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.presentations.arn
      }
    ]
  })
}

# Lambda依赖层
resource "aws_lambda_layer_version" "image_processing_layer" {
  filename                 = "../dist/image_processing_layer.zip"
  layer_name              = "${var.project_name}-image-processing-layer-${var.environment}"
  compatible_runtimes     = ["python3.11", "python3.12"]
  compatible_architectures = ["x86_64"]

  description = "图片处理服务依赖层 - 包含boto3、Pillow等核心依赖"

  depends_on = [null_resource.build_lambda_packages]
}

# 构建Lambda包的资源
resource "null_resource" "build_lambda_packages" {
  triggers = {
    # 当源代码文件变更时重新构建
    image_service = filemd5("../lambdas/image_processing_service.py")
    image_config  = filemd5("../lambdas/image_config.py")
    build_script  = filemd5("../scripts/package_lambdas.sh")
  }

  provisioner "local-exec" {
    command = "cd .. && ./scripts/package_lambdas.sh"
  }
}

# 基础图片生成Lambda函数
resource "aws_lambda_function" "image_generator" {
  filename         = "../dist/image_generator.zip"
  function_name    = "${var.project_name}-image-generator-${var.environment}"
  role            = aws_iam_role.image_lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.11"
  timeout         = 300  # 5分钟
  memory_size     = 1024 # 1GB内存
  architectures   = ["x86_64"]

  layers = [aws_lambda_layer_version.image_processing_layer.arn]

  environment {
    variables = {
      IMAGE_BUCKET          = aws_s3_bucket.presentations.bucket
      NOVA_MODEL_ID         = "amazon.nova-canvas-v1:0"
      IMAGE_WIDTH           = "1200"
      IMAGE_HEIGHT          = "800"
      MAX_RETRY_ATTEMPTS    = "3"
      ENVIRONMENT           = var.environment
      LOG_LEVEL            = "INFO"
      ENABLE_XRAY_TRACING  = "true"
    }
  }

  # 启用X-Ray追踪
  tracing_config {
    mode = "Active"
  }

  # VPC配置（可选）
  dynamic "vpc_config" {
    for_each = var.enable_vpc ? [1] : []
    content {
      subnet_ids         = var.private_subnet_ids
      security_group_ids = [aws_security_group.lambda_sg[0].id]
    }
  }

  depends_on = [
    null_resource.build_lambda_packages,
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.lambda_bedrock_policy,
    aws_iam_role_policy.lambda_s3_policy,
    aws_iam_role_policy.lambda_cloudwatch_policy
  ]

  tags = {
    Name        = "${var.project_name}-image-generator"
    Environment = var.environment
    Component   = "ImageProcessing"
    Version     = "basic"
  }
}

# 优化图片生成Lambda函数
resource "aws_lambda_function" "image_generator_optimized" {
  count = fileexists("../dist/image_generator_optimized.zip") ? 1 : 0

  filename         = "../dist/image_generator_optimized.zip"
  function_name    = "${var.project_name}-image-generator-optimized-${var.environment}"
  role            = aws_iam_role.image_lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.11"
  timeout         = 900  # 15分钟（支持批处理）
  memory_size     = 2048 # 2GB内存（优化版需要更多内存）
  architectures   = ["x86_64"]

  layers = [aws_lambda_layer_version.image_processing_layer.arn]

  environment {
    variables = {
      IMAGE_BUCKET              = aws_s3_bucket.presentations.bucket
      NOVA_MODEL_ID             = "amazon.nova-canvas-v1:0"
      IMAGE_WIDTH               = "1200"
      IMAGE_HEIGHT              = "800"
      MAX_RETRY_ATTEMPTS        = "3"
      ENVIRONMENT               = var.environment
      LOG_LEVEL                = "INFO"
      ENABLE_XRAY_TRACING      = "true"
      ENABLE_CACHING           = "true"
      ENABLE_MONITORING        = "true"
      ENABLE_BATCHING          = "true"
      ENABLE_PRELOADING        = "true"
      MAX_CONCURRENT_REQUESTS  = "10"
      CACHE_TTL_SECONDS        = "3600"
      PRELOAD_QUEUE_SIZE       = "50"
    }
  }

  # 启用X-Ray追踪
  tracing_config {
    mode = "Active"
  }

  # 并发控制
  reserved_concurrent_executions = 50

  # VPC配置（可选）
  dynamic "vpc_config" {
    for_each = var.enable_vpc ? [1] : []
    content {
      subnet_ids         = var.private_subnet_ids
      security_group_ids = [aws_security_group.lambda_sg[0].id]
    }
  }

  depends_on = [
    null_resource.build_lambda_packages,
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.lambda_bedrock_policy,
    aws_iam_role_policy.lambda_s3_policy,
    aws_iam_role_policy.lambda_cloudwatch_policy
  ]

  tags = {
    Name        = "${var.project_name}-image-generator-optimized"
    Environment = var.environment
    Component   = "ImageProcessing"
    Version     = "optimized"
  }
}

# Lambda安全组（如果启用VPC）
resource "aws_security_group" "lambda_sg" {
  count = var.enable_vpc ? 1 : 0

  name        = "${var.project_name}-lambda-image-sg-${var.environment}"
  description = "Security group for image processing Lambda functions"
  vpc_id      = data.aws_vpc.default.id

  # 出站规则 - HTTPS访问Bedrock和S3
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS outbound for AWS services"
  }

  # 出站规则 - DNS解析
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS resolution"
  }

  tags = {
    Name        = "${var.project_name}-lambda-image-sg"
    Environment = var.environment
    Component   = "ImageProcessing"
  }
}

# CloudWatch日志组
resource "aws_cloudwatch_log_group" "image_generator_logs" {
  name              = "/aws/lambda/${aws_lambda_function.image_generator.function_name}"
  retention_in_days = 14

  tags = {
    Name        = "${var.project_name}-image-generator-logs"
    Environment = var.environment
    Component   = "ImageProcessing"
  }
}

resource "aws_cloudwatch_log_group" "image_generator_optimized_logs" {
  count = length(aws_lambda_function.image_generator_optimized) > 0 ? 1 : 0

  name              = "/aws/lambda/${aws_lambda_function.image_generator_optimized[0].function_name}"
  retention_in_days = 14

  tags = {
    Name        = "${var.project_name}-image-generator-optimized-logs"
    Environment = var.environment
    Component   = "ImageProcessing"
  }
}

# Lambda函数别名（用于蓝绿部署）
resource "aws_lambda_alias" "image_generator_live" {
  name             = "live"
  description      = "Live alias for image generator"
  function_name    = aws_lambda_function.image_generator.function_name
  function_version = aws_lambda_function.image_generator.version

  routing_config {
    additional_version_weights = {
      "$LATEST" = 0.1  # 10%流量给最新版本
    }
  }
}

resource "aws_lambda_alias" "image_generator_optimized_live" {
  count = length(aws_lambda_function.image_generator_optimized) > 0 ? 1 : 0

  name             = "live"
  description      = "Live alias for optimized image generator"
  function_name    = aws_lambda_function.image_generator_optimized[0].function_name
  function_version = aws_lambda_function.image_generator_optimized[0].version

  routing_config {
    additional_version_weights = {
      "$LATEST" = 0.1  # 10%流量给最新版本
    }
  }
}

# Lambda函数URL（可选，用于直接HTTP访问）
resource "aws_lambda_function_url" "image_generator_url" {
  count = var.enable_lambda_url ? 1 : 0

  function_name      = aws_lambda_function.image_generator.function_name
  qualifier         = aws_lambda_alias.image_generator_live.name
  authorization_type = "NONE"  # 或 "AWS_IAM" 如果需要认证

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["POST", "OPTIONS"]
    allow_headers     = ["date", "keep-alive", "content-type", "x-api-key", "authorization"]
    expose_headers    = ["date", "keep-alive"]
    max_age          = 86400
  }
}

resource "aws_lambda_function_url" "image_generator_optimized_url" {
  count = var.enable_lambda_url && length(aws_lambda_function.image_generator_optimized) > 0 ? 1 : 0

  function_name      = aws_lambda_function.image_generator_optimized[0].function_name
  qualifier         = aws_lambda_alias.image_generator_optimized_live[0].name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["POST", "OPTIONS"]
    allow_headers     = ["date", "keep-alive", "content-type", "x-api-key", "authorization"]
    expose_headers    = ["date", "keep-alive"]
    max_age          = 86400
  }
}

# 输出
output "image_generator_function_name" {
  description = "基础图片生成Lambda函数名"
  value       = aws_lambda_function.image_generator.function_name
}

output "image_generator_function_arn" {
  description = "基础图片生成Lambda函数ARN"
  value       = aws_lambda_function.image_generator.arn
}

output "image_generator_optimized_function_name" {
  description = "优化图片生成Lambda函数名"
  value       = length(aws_lambda_function.image_generator_optimized) > 0 ? aws_lambda_function.image_generator_optimized[0].function_name : null
}

output "image_generator_function_url" {
  description = "图片生成Lambda函数URL"
  value       = var.enable_lambda_url ? aws_lambda_function_url.image_generator_url[0].function_url : null
  sensitive   = false
}

output "lambda_role_arn" {
  description = "Lambda执行角色ARN"
  value       = aws_iam_role.image_lambda_role.arn
}

output "lambda_layer_arn" {
  description = "Lambda依赖层ARN"
  value       = aws_lambda_layer_version.image_processing_layer.arn
}