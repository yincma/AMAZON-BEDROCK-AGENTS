# Image Generation Service Resources

# DynamoDB table for image cache
resource "aws_dynamodb_table" "image_cache" {
  name         = "${var.project_name}-image-cache"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cache_key"

  attribute {
    name = "cache_key"
    type = "S"
  }

  # TTL配置
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  # Global Secondary Index for prompt search
  global_secondary_index {
    name            = "prompt-index"
    hash_key        = "prompt_hash"
    projection_type = "ALL"
  }

  attribute {
    name = "prompt_hash"
    type = "S"
  }

  tags = {
    Name        = "${var.project_name}-image-cache"
    Environment = var.environment
    Purpose     = "AI Image Generation Cache"
  }
}

# S3 bucket for image cache storage
resource "aws_s3_bucket" "image_cache" {
  bucket = "${var.project_name}-image-cache-${var.environment}-${data.aws_caller_identity.current.account_id}"

  force_destroy = true

  tags = {
    Name        = "${var.project_name}-image-cache"
    Environment = var.environment
    Purpose     = "AI Generated Images Cache"
  }
}

# S3 bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "image_cache" {
  bucket = aws_s3_bucket.image_cache.id

  rule {
    id     = "cleanup-old-cache"
    status = "Enabled"

    filter {}

    transition {
      days          = 7
      storage_class = "INTELLIGENT_TIERING"
    }

    expiration {
      days = 30
    }
  }

  rule {
    id     = "cleanup-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# CloudWatch Log Group for image generation
resource "aws_cloudwatch_log_group" "image_generation" {
  name              = "/aws/lambda/${var.project_name}-image-generation"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Service     = "ImageGeneration"
  }
}

# CloudWatch Alarms for image generation
resource "aws_cloudwatch_metric_alarm" "image_generation_errors" {
  alarm_name          = "${var.project_name}-image-generation-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors image generation errors"
  alarm_actions       = var.alert_email != "" ? [aws_sns_topic.image_gen_alerts.arn] : []

  dimensions = {
    FunctionName = aws_lambda_function.generate_ppt.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "image_gen_bedrock_throttling" {
  alarm_name          = "${var.project_name}-bedrock-throttling"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "UserErrors"
  namespace           = "AWS/Bedrock"
  period              = "60"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when Bedrock API is throttling requests"
  alarm_actions       = var.alert_email != "" ? [aws_sns_topic.image_gen_alerts.arn] : []
}

# SNS Topic for alerts
resource "aws_sns_topic" "image_gen_alerts" {
  name = "${var.project_name}-alerts"

  tags = {
    Environment = var.environment
    Purpose     = "System Alerts"
  }
}

resource "aws_sns_topic_subscription" "image_gen_email_alerts" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.image_gen_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# IAM policy for image generation
resource "aws_iam_policy" "image_generation" {
  name        = "${var.project_name}-image-generation-policy"
  description = "Policy for image generation Lambda functions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:*:*:foundation-model/amazon.nova-canvas-v1:0",
          "arn:aws:bedrock:*:*:foundation-model/stability.stable-diffusion-xl-v1",
          "arn:aws:bedrock:*:*:foundation-model/amazon.titan-image-generator-v2:0"
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
          aws_dynamodb_table.image_cache.arn,
          "${aws_dynamodb_table.image_cache.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.image_cache.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach the policy to Lambda execution role
resource "aws_iam_role_policy_attachment" "lambda_image_generation" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.image_generation.arn
}

# CloudWatch Dashboard for monitoring
resource "aws_cloudwatch_dashboard" "image_generation" {
  dashboard_name = "${var.project_name}-image-generation"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { stat = "Sum" }],
            [".", "Errors", { stat = "Sum" }],
            [".", "Duration", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Lambda Image Generation Metrics"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Bedrock", "InvocationLatency", { stat = "Average" }],
            [".", "InvocationClientErrors", { stat = "Sum" }],
            [".", "InvocationServerErrors", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Bedrock API Metrics"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", { stat = "Sum" }],
            [".", "ConsumedWriteCapacityUnits", { stat = "Sum" }],
            [".", "UserErrors", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "DynamoDB Cache Metrics"
        }
      }
    ]
  })
}

# Outputs
output "image_cache_table_name" {
  value       = aws_dynamodb_table.image_cache.name
  description = "Name of the DynamoDB table for image cache"
}

output "image_cache_bucket_name" {
  value       = aws_s3_bucket.image_cache.id
  description = "Name of the S3 bucket for image cache"
}

output "image_gen_cloudwatch_dashboard_url" {
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.image_generation.dashboard_name}"
  description = "URL to CloudWatch dashboard for image generation monitoring"
}