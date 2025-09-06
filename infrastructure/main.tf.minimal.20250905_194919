# Minimal Terraform Configuration for Quick Deployment
# This file creates only the essential resources without complex dependencies

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  
  default_tags {
    tags = {
      Project     = "ai-ppt-assistant"
      Environment = "dev"
      ManagedBy   = "Terraform"
    }
  }
}

# S3 Bucket for presentations
resource "aws_s3_bucket" "presentations" {
  bucket = "ai-ppt-assistant-dev-presentations-${random_id.bucket_suffix.hex}"
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

# DynamoDB Table for sessions
resource "aws_dynamodb_table" "sessions" {
  name           = "ai-ppt-assistant-dev-sessions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  ttl {
    attribute_name = "expiry"
    enabled        = true
  }
}

# DynamoDB Table for checkpoints
resource "aws_dynamodb_table" "checkpoints" {
  name           = "ai-ppt-assistant-dev-checkpoints"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "checkpoint_id"

  attribute {
    name = "checkpoint_id"
    type = "S"
  }

  ttl {
    attribute_name = "expiry"
    enabled        = true
  }
}

# Random ID for unique bucket naming
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# SQS Queue (if needed for Lambda)
resource "aws_sqs_queue" "task_queue" {
  name = "ai-ppt-assistant-dev-tasks"
  
  visibility_timeout_seconds = 300
  message_retention_seconds  = 86400
  
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "dlq" {
  name = "ai-ppt-assistant-dev-tasks-dlq"
  message_retention_seconds = 1209600  # 14 days
}

# Lambda Layer for dependencies
resource "aws_lambda_layer_version" "dependencies" {
  filename            = "../lambdas/layers/python.zip"
  layer_name          = "ai-ppt-assistant-dev-dependencies"
  compatible_runtimes = ["python3.12"]
  source_code_hash    = filebase64sha256("../lambdas/layers/python.zip")
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "ai-ppt-assistant-dev-lambda-role"

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
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_permissions" {
  name = "lambda-permissions"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.presentations.arn,
          "${aws_s3_bucket.presentations.arn}/*"
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
          aws_dynamodb_table.sessions.arn,
          aws_dynamodb_table.checkpoints.arn
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
        Resource = [
          aws_sqs_queue.task_queue.arn,
          aws_sqs_queue.dlq.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      }
    ]
  })
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "api" {
  name        = "ai-ppt-assistant-dev-api"
  description = "API for AI PPT Assistant"
}

resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = "v1"

  lifecycle {
    create_before_destroy = true
  }
  
  depends_on = [aws_api_gateway_rest_api.api]
}

# Outputs
output "s3_bucket_name" {
  value = aws_s3_bucket.presentations.id
}

output "dynamodb_sessions_table" {
  value = aws_dynamodb_table.sessions.name
}

output "dynamodb_checkpoints_table" {
  value = aws_dynamodb_table.checkpoints.name
}

output "sqs_queue_url" {
  value = aws_sqs_queue.task_queue.url
}

output "api_gateway_url" {
  value = aws_api_gateway_deployment.api.invoke_url
}

output "lambda_layer_arn" {
  value = aws_lambda_layer_version.dependencies.arn
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda_role.arn
}