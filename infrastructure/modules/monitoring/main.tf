# CloudWatch Monitoring and Alerting Module
# This module implements comprehensive monitoring for AI PPT Assistant

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data sources for current AWS account and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values for consistent naming
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  
  # Common tags for all resources
  common_tags = merge(
    var.tags,
    {
      Module = "monitoring"
    }
  )
}

# ============================================================================
# SNS Topic for Alerts
# ============================================================================

resource "aws_sns_topic" "alerts" {
  name         = "${local.name_prefix}-alerts"
  display_name = "AI PPT Assistant Alerts"
  
  # Enable encryption at rest
  kms_master_key_id = aws_kms_key.sns_key.id
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-alerts"
    }
  )
}

# KMS key for SNS encryption
resource "aws_kms_key" "sns_key" {
  description             = "KMS key for SNS topic encryption"
  deletion_window_in_days = 7
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })
  
  tags = local.common_tags
}

resource "aws_kms_alias" "sns_key_alias" {
  name          = "alias/${local.name_prefix}-sns-key"
  target_key_id = aws_kms_key.sns_key.key_id
}

# SNS Topic subscription (email notification)
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = length(var.alert_email_addresses)
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email_addresses[count.index]
}

# ============================================================================
# Lambda Function Error Rate Alarms
# ============================================================================

# Lambda Error Rate Alarm for each function
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  for_each = var.lambda_function_names
  
  alarm_name        = "${local.name_prefix}-lambda-${each.key}-error-rate"
  alarm_description = "High error rate for Lambda function ${each.value}"
  
  # Metric configuration
  metric_name = "Errors"
  namespace   = "AWS/Lambda"
  statistic   = "Sum"
  
  dimensions = {
    FunctionName = each.value
  }
  
  # Alarm thresholds
  period              = var.lambda_error_alarm_period
  evaluation_periods  = var.lambda_error_evaluation_periods
  threshold           = var.lambda_error_threshold
  comparison_operator = "GreaterThanThreshold"
  
  # What happens when alarm state changes
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
  
  # Treat missing data points as good
  treat_missing_data = "notBreaching"
  
  tags = merge(
    local.common_tags,
    {
      Name         = "${local.name_prefix}-lambda-${each.key}-error-rate"
      AlarmType    = "Lambda"
      FunctionName = each.value
    }
  )
}

# Lambda Duration Alarm for each function
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  for_each = var.lambda_function_names
  
  alarm_name        = "${local.name_prefix}-lambda-${each.key}-duration"
  alarm_description = "High duration for Lambda function ${each.value}"
  
  # Metric configuration
  metric_name = "Duration"
  namespace   = "AWS/Lambda"
  statistic   = "Average"
  
  dimensions = {
    FunctionName = each.value
  }
  
  # Alarm thresholds (in milliseconds)
  period              = var.lambda_duration_alarm_period
  evaluation_periods  = var.lambda_duration_evaluation_periods
  threshold           = var.lambda_duration_threshold
  comparison_operator = "GreaterThanThreshold"
  
  # What happens when alarm state changes
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
  
  # Treat missing data points as good
  treat_missing_data = "notBreaching"
  
  tags = merge(
    local.common_tags,
    {
      Name         = "${local.name_prefix}-lambda-${each.key}-duration"
      AlarmType    = "Lambda"
      FunctionName = each.value
    }
  )
}

# Lambda Throttle Alarm for each function
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  for_each = var.lambda_function_names
  
  alarm_name        = "${local.name_prefix}-lambda-${each.key}-throttles"
  alarm_description = "Lambda function ${each.value} is being throttled"
  
  # Metric configuration
  metric_name = "Throttles"
  namespace   = "AWS/Lambda"
  statistic   = "Sum"
  
  dimensions = {
    FunctionName = each.value
  }
  
  # Alarm thresholds
  period              = var.lambda_throttle_alarm_period
  evaluation_periods  = var.lambda_throttle_evaluation_periods
  threshold           = var.lambda_throttle_threshold
  comparison_operator = "GreaterThanThreshold"
  
  # What happens when alarm state changes
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
  
  # Treat missing data points as good
  treat_missing_data = "notBreaching"
  
  tags = merge(
    local.common_tags,
    {
      Name         = "${local.name_prefix}-lambda-${each.key}-throttles"
      AlarmType    = "Lambda"
      FunctionName = each.value
    }
  )
}

# ============================================================================
# API Gateway Latency and Error Alarms
# ============================================================================

# API Gateway 4XX Error Rate
resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx_error_rate" {
  alarm_name        = "${local.name_prefix}-api-gateway-4xx-errors"
  alarm_description = "High 4XX error rate for API Gateway"
  
  # Metric configuration
  metric_name = "4XXError"
  namespace   = "AWS/ApiGateway"
  statistic   = "Sum"
  
  dimensions = {
    ApiName   = var.api_gateway_name
    Stage     = var.api_gateway_stage
  }
  
  # Alarm thresholds
  period              = var.api_4xx_alarm_period
  evaluation_periods  = var.api_4xx_evaluation_periods
  threshold           = var.api_4xx_threshold
  comparison_operator = "GreaterThanThreshold"
  
  # What happens when alarm state changes
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = merge(
    local.common_tags,
    {
      Name      = "${local.name_prefix}-api-gateway-4xx-errors"
      AlarmType = "API Gateway"
    }
  )
}

# API Gateway 5XX Error Rate
resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx_error_rate" {
  alarm_name        = "${local.name_prefix}-api-gateway-5xx-errors"
  alarm_description = "High 5XX error rate for API Gateway"
  
  # Metric configuration
  metric_name = "5XXError"
  namespace   = "AWS/ApiGateway"
  statistic   = "Sum"
  
  dimensions = {
    ApiName   = var.api_gateway_name
    Stage     = var.api_gateway_stage
  }
  
  # Alarm thresholds
  period              = var.api_5xx_alarm_period
  evaluation_periods  = var.api_5xx_evaluation_periods
  threshold           = var.api_5xx_threshold
  comparison_operator = "GreaterThanThreshold"
  
  # What happens when alarm state changes
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = merge(
    local.common_tags,
    {
      Name      = "${local.name_prefix}-api-gateway-5xx-errors"
      AlarmType = "API Gateway"
    }
  )
}

# API Gateway Latency Alarm
resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  alarm_name        = "${local.name_prefix}-api-gateway-latency"
  alarm_description = "High latency for API Gateway"
  
  # Metric configuration
  metric_name = "Latency"
  namespace   = "AWS/ApiGateway"
  statistic   = "Average"
  
  dimensions = {
    ApiName   = var.api_gateway_name
    Stage     = var.api_gateway_stage
  }
  
  # Alarm thresholds (in milliseconds)
  period              = var.api_latency_alarm_period
  evaluation_periods  = var.api_latency_evaluation_periods
  threshold           = var.api_latency_threshold
  comparison_operator = "GreaterThanThreshold"
  
  # What happens when alarm state changes
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = merge(
    local.common_tags,
    {
      Name      = "${local.name_prefix}-api-gateway-latency"
      AlarmType = "API Gateway"
    }
  )
}

# API Gateway Count Alarm (for monitoring traffic)
resource "aws_cloudwatch_metric_alarm" "api_gateway_count" {
  alarm_name        = "${local.name_prefix}-api-gateway-high-traffic"
  alarm_description = "Unusually high traffic for API Gateway"
  
  # Metric configuration
  metric_name = "Count"
  namespace   = "AWS/ApiGateway"
  statistic   = "Sum"
  
  dimensions = {
    ApiName   = var.api_gateway_name
    Stage     = var.api_gateway_stage
  }
  
  # Alarm thresholds
  period              = var.api_count_alarm_period
  evaluation_periods  = var.api_count_evaluation_periods
  threshold           = var.api_count_threshold
  comparison_operator = "GreaterThanThreshold"
  
  # What happens when alarm state changes
  alarm_actions = [aws_sns_topic.alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = merge(
    local.common_tags,
    {
      Name      = "${local.name_prefix}-api-gateway-high-traffic"
      AlarmType = "API Gateway"
    }
  )
}

# ============================================================================
# CloudWatch Dashboard
# ============================================================================

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.name_prefix}-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            for func_key, func_name in var.lambda_function_names : [
              "AWS/Lambda", "Invocations", "FunctionName", func_name,
              { "stat" : "Sum" }
            ]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Lambda Function Invocations"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            for func_key, func_name in var.lambda_function_names : [
              "AWS/Lambda", "Errors", "FunctionName", func_name,
              { "stat" : "Sum" }
            ]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Lambda Function Errors"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            for func_key, func_name in var.lambda_function_names : [
              "AWS/Lambda", "Duration", "FunctionName", func_name,
              { "stat" : "Average" }
            ]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "Lambda Function Duration (ms)"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", var.api_gateway_name, "Stage", var.api_gateway_stage],
            [".", "4XXError", ".", ".", ".", "."],
            [".", "5XXError", ".", ".", ".", "."],
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "API Gateway Request Count and Errors"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 24
        height = 6
        
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiName", var.api_gateway_name, "Stage", var.api_gateway_stage, { "stat" : "Average" }],
            [".", ".", ".", ".", ".", ".", { "stat" : "p95" }],
            [".", ".", ".", ".", ".", ".", { "stat" : "p99" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = data.aws_region.current.name
          title   = "API Gateway Latency (ms) - Average, p95, p99"
          period  = 300
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      }
    ]
  })
  
  # CloudWatch Dashboard does not support tags
}

# ============================================================================
# DynamoDB Monitoring (if enabled)
# ============================================================================

# DynamoDB Read Capacity Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_read_throttles" {
  count = var.enable_dynamodb_monitoring ? 1 : 0
  
  alarm_name        = "${local.name_prefix}-dynamodb-read-throttles"
  alarm_description = "DynamoDB table read throttles"
  
  # Metric configuration
  metric_name = "ReadThrottleEvents"
  namespace   = "AWS/DynamoDB"
  statistic   = "Sum"
  
  dimensions = {
    TableName = var.dynamodb_table_name
  }
  
  # Alarm thresholds
  period              = var.dynamodb_throttle_alarm_period
  evaluation_periods  = var.dynamodb_throttle_evaluation_periods
  threshold           = var.dynamodb_throttle_threshold
  comparison_operator = "GreaterThanThreshold"
  
  # What happens when alarm state changes
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = merge(
    local.common_tags,
    {
      Name      = "${local.name_prefix}-dynamodb-read-throttles"
      AlarmType = "DynamoDB"
    }
  )
}

# DynamoDB Write Capacity Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_write_throttles" {
  count = var.enable_dynamodb_monitoring ? 1 : 0
  
  alarm_name        = "${local.name_prefix}-dynamodb-write-throttles"
  alarm_description = "DynamoDB table write throttles"
  
  # Metric configuration
  metric_name = "WriteThrottleEvents"
  namespace   = "AWS/DynamoDB"
  statistic   = "Sum"
  
  dimensions = {
    TableName = var.dynamodb_table_name
  }
  
  # Alarm thresholds
  period              = var.dynamodb_throttle_alarm_period
  evaluation_periods  = var.dynamodb_throttle_evaluation_periods
  threshold           = var.dynamodb_throttle_threshold
  comparison_operator = "GreaterThanThreshold"
  
  # What happens when alarm state changes
  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
  
  treat_missing_data = "notBreaching"
  
  tags = merge(
    local.common_tags,
    {
      Name      = "${local.name_prefix}-dynamodb-write-throttles"
      AlarmType = "DynamoDB"
    }
  )
}

# ============================================================================
# CloudWatch Log Groups for Retention
# ============================================================================

# Log group for CloudWatch Logs Insights queries
resource "aws_cloudwatch_log_group" "insights_queries" {
  name              = "/aws/cloudwatch/insights/${local.name_prefix}"
  retention_in_days = var.log_retention_days
  
  tags = merge(
    local.common_tags,
    {
      Name = "${local.name_prefix}-insights-logs"
    }
  )
}