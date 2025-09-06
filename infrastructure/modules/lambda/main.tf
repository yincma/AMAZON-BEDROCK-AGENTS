# Lambda Module - All Lambda Functions for AI PPT Assistant

# Lambda Layer for shared dependencies
resource "aws_lambda_layer_version" "shared_dependencies" {
  filename            = "${path.module}/../../../lambdas/layers/python.zip"
  layer_name          = "${var.project_name}-shared-deps"
  compatible_runtimes = ["python3.13"]
  compatible_architectures = ["arm64"]
  
  description = "Shared dependencies for all Lambda functions"
}

# IAM Role for Lambda Functions
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-execution-role"

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

  tags = var.tags
}

# IAM Policy for Lambda Functions
resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.project_name}-lambda-policy"
  description = "Policy for Lambda functions to access AWS services"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      },
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
        Resource = [
          var.dynamodb_table_arn,
          var.checkpoints_table_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = var.sqs_queue_arn
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock-runtime:InvokeAgent"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AttachNetworkInterface",
          "ec2:DetachNetworkInterface"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ec2:Region" = "${var.aws_region}"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  policy_arn = aws_iam_policy.lambda_policy.arn
  role       = aws_iam_role.lambda_execution_role.name
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution_role.name
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# Lambda Function: Create Outline
resource "aws_lambda_function" "create_outline" {
  filename         = "${path.module}/../../../lambdas/controllers/create_outline.zip"
  function_name    = "${var.project_name}-create-outline"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "create_outline.lambda_handler"
  runtime         = "python3.13"
  architectures   = ["arm64"]
  timeout         = 60
  memory_size     = 1024

  layers = [aws_lambda_layer_version.shared_dependencies.arn]

  environment {
    variables = {
      S3_BUCKET          = var.s3_bucket_name
      DYNAMODB_TABLE     = var.dynamodb_table_name
      BEDROCK_MODEL_ID   = "anthropic.claude-4-0"
      LOG_LEVEL          = var.log_level
    }
  }
  
  # VPC configuration for enhanced security
  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = var.tags
}

# Lambda Function: Generate Content
resource "aws_lambda_function" "generate_content" {
  filename         = "${path.module}/../../../lambdas/controllers/generate_content.zip"
  function_name    = "${var.project_name}-generate-content"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "generate_content.lambda_handler"
  runtime         = "python3.13"
  architectures   = ["arm64"]
  timeout         = 120
  memory_size     = 2048

  layers = [aws_lambda_layer_version.shared_dependencies.arn]

  environment {
    variables = {
      S3_BUCKET          = var.s3_bucket_name
      DYNAMODB_TABLE     = var.dynamodb_table_name
      BEDROCK_MODEL_ID   = "anthropic.claude-4-0"
      LOG_LEVEL          = var.log_level
    }
  }
  
  # VPC configuration for enhanced security
  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = var.tags
}

# Lambda Function: Generate Image
resource "aws_lambda_function" "generate_image" {
  filename         = "${path.module}/../../../lambdas/controllers/generate_image.zip"
  function_name    = "${var.project_name}-generate-image"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "generate_image.lambda_handler"
  runtime         = "python3.13"
  architectures   = ["arm64"]
  timeout         = 90
  memory_size     = 1024

  layers = [aws_lambda_layer_version.shared_dependencies.arn]

  environment {
    variables = {
      S3_BUCKET          = var.s3_bucket_name
      DYNAMODB_TABLE     = var.dynamodb_table_name
      NOVA_MODEL_ID      = "amazon.nova-canvas-v1:0"
      LOG_LEVEL          = var.log_level
    }
  }
  
  # VPC configuration for enhanced security
  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = var.tags
}

# Lambda Function: Find Image
resource "aws_lambda_function" "find_image" {
  filename         = "${path.module}/../../../lambdas/controllers/find_image.zip"
  function_name    = "${var.project_name}-find-image"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "find_image.lambda_handler"
  runtime         = "python3.13"
  architectures   = ["arm64"]
  timeout         = 30
  memory_size     = 512

  layers = [aws_lambda_layer_version.shared_dependencies.arn]

  environment {
    variables = {
      S3_BUCKET          = var.s3_bucket_name
      DYNAMODB_TABLE     = var.dynamodb_table_name
      LOG_LEVEL          = var.log_level
    }
  }
  
  # VPC configuration for enhanced security
  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = var.tags
}

# Lambda Function: Generate Speaker Notes
resource "aws_lambda_function" "generate_speaker_notes" {
  filename         = "${path.module}/../../../lambdas/controllers/generate_speaker_notes.zip"
  function_name    = "${var.project_name}-generate-speaker-notes"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "generate_speaker_notes.lambda_handler"
  runtime         = "python3.13"
  architectures   = ["arm64"]
  timeout         = 60
  memory_size     = 1024

  layers = [aws_lambda_layer_version.shared_dependencies.arn]

  environment {
    variables = {
      S3_BUCKET          = var.s3_bucket_name
      DYNAMODB_TABLE     = var.dynamodb_table_name
      BEDROCK_MODEL_ID   = "anthropic.claude-4-0"
      LOG_LEVEL          = var.log_level
    }
  }
  
  # VPC configuration for enhanced security
  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = var.tags
}

# Lambda Function: Compile PPTX
resource "aws_lambda_function" "compile_pptx" {
  filename         = "${path.module}/../../../lambdas/controllers/compile_pptx.zip"
  function_name    = "${var.project_name}-compile-pptx"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "compile_pptx.lambda_handler"
  runtime         = "python3.13"
  architectures   = ["arm64"]
  timeout         = 180
  memory_size     = 3008

  layers = [aws_lambda_layer_version.shared_dependencies.arn]

  environment {
    variables = {
      S3_BUCKET          = var.s3_bucket_name
      DYNAMODB_TABLE     = var.dynamodb_table_name
      LOG_LEVEL          = var.log_level
    }
  }
  
  # VPC configuration for enhanced security
  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = var.tags
}

# API Lambda Functions

# Lambda Function: Generate Presentation API
resource "aws_lambda_function" "api_generate_presentation" {
  filename         = "${path.module}/../../../lambdas/api/generate_presentation.zip"
  function_name    = "${var.project_name}-api-generate-presentation"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "generate_presentation.lambda_handler"
  runtime         = "python3.13"
  architectures   = ["arm64"]
  timeout         = 30
  memory_size     = 512

  layers = [aws_lambda_layer_version.shared_dependencies.arn]

  environment {
    variables = {
      DYNAMODB_TABLE        = var.dynamodb_table_name
      S3_BUCKET            = var.s3_bucket_name
      SQS_QUEUE_URL        = var.sqs_queue_url
      ORCHESTRATOR_AGENT_ID = var.orchestrator_agent_id
      ORCHESTRATOR_ALIAS_ID = var.orchestrator_alias_id
      LOG_LEVEL            = var.log_level
    }
  }
  
  # VPC configuration for enhanced security
  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = var.tags
}

# Lambda Function: Presentation Status API
resource "aws_lambda_function" "api_presentation_status" {
  filename         = "${path.module}/../../../lambdas/api/presentation_status.zip"
  function_name    = "${var.project_name}-api-presentation-status"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "presentation_status.lambda_handler"
  runtime         = "python3.13"
  architectures   = ["arm64"]
  timeout         = 10
  memory_size     = 256

  layers = [aws_lambda_layer_version.shared_dependencies.arn]

  environment {
    variables = {
      DYNAMODB_TABLE = var.dynamodb_table_name
      LOG_LEVEL      = var.log_level
    }
  }
  
  # VPC configuration for enhanced security
  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = var.tags
}

# Lambda Function: Presentation Download API
resource "aws_lambda_function" "api_presentation_download" {
  filename         = "${path.module}/../../../lambdas/api/presentation_download.zip"
  function_name    = "${var.project_name}-api-presentation-download"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "presentation_download.lambda_handler"
  runtime         = "python3.13"
  architectures   = ["arm64"]
  timeout         = 10
  memory_size     = 256

  layers = [aws_lambda_layer_version.shared_dependencies.arn]

  environment {
    variables = {
      DYNAMODB_TABLE         = var.dynamodb_table_name
      S3_BUCKET             = var.s3_bucket_name
      DOWNLOAD_EXPIRY_SECONDS = "3600"
      LOG_LEVEL             = var.log_level
    }
  }
  
  # VPC configuration for enhanced security
  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = var.tags
}

# Lambda Function: Modify Slide API
resource "aws_lambda_function" "api_modify_slide" {
  filename         = "${path.module}/../../../lambdas/api/modify_slide.zip"
  function_name    = "${var.project_name}-api-modify-slide"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "modify_slide.lambda_handler"
  runtime         = "python3.13"
  architectures   = ["arm64"]
  timeout         = 30
  memory_size     = 512

  layers = [aws_lambda_layer_version.shared_dependencies.arn]

  environment {
    variables = {
      DYNAMODB_TABLE    = var.dynamodb_table_name
      S3_BUCKET        = var.s3_bucket_name
      SQS_QUEUE_URL    = var.sqs_queue_url
      CONTENT_AGENT_ID  = var.content_agent_id
      CONTENT_ALIAS_ID  = var.content_alias_id
      VISUAL_AGENT_ID   = var.visual_agent_id
      VISUAL_ALIAS_ID   = var.visual_alias_id
      COMPILER_AGENT_ID = var.compiler_agent_id
      COMPILER_ALIAS_ID = var.compiler_alias_id
      LOG_LEVEL        = var.log_level
    }
  }
  
  # VPC configuration for enhanced security
  dynamic "vpc_config" {
    for_each = var.enable_vpc_config ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  tags = var.tags
}

# Outputs
output "lambda_function_arns" {
  value = {
    create_outline           = aws_lambda_function.create_outline.arn
    generate_content        = aws_lambda_function.generate_content.arn
    generate_image          = aws_lambda_function.generate_image.arn
    find_image              = aws_lambda_function.find_image.arn
    generate_speaker_notes  = aws_lambda_function.generate_speaker_notes.arn
    compile_pptx            = aws_lambda_function.compile_pptx.arn
    api_generate_presentation = aws_lambda_function.api_generate_presentation.arn
    api_presentation_status = aws_lambda_function.api_presentation_status.arn
    api_presentation_download = aws_lambda_function.api_presentation_download.arn
    api_modify_slide        = aws_lambda_function.api_modify_slide.arn
  }
}

output "lambda_function_names" {
  value = {
    create_outline           = aws_lambda_function.create_outline.function_name
    generate_content        = aws_lambda_function.generate_content.function_name
    generate_image          = aws_lambda_function.generate_image.function_name
    find_image              = aws_lambda_function.find_image.function_name
    generate_speaker_notes  = aws_lambda_function.generate_speaker_notes.function_name
    compile_pptx            = aws_lambda_function.compile_pptx.function_name
    api_generate_presentation = aws_lambda_function.api_generate_presentation.function_name
    api_presentation_status = aws_lambda_function.api_presentation_status.function_name
    api_presentation_download = aws_lambda_function.api_presentation_download.function_name
    api_modify_slide        = aws_lambda_function.api_modify_slide.function_name
  }
}

output "lambda_execution_role_arn" {
  value = aws_iam_role.lambda_execution_role.arn
}