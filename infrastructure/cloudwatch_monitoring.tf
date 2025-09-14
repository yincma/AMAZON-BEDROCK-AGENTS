# CloudWatch监控和告警配置 - 图片生成服务
# 包含指标、告警、仪表板等监控组件

# SNS主题用于告警通知
resource "aws_sns_topic" "image_processing_alerts" {
  name = "${var.project_name}-image-processing-alerts-${var.environment}"

  tags = {
    Name        = "${var.project_name}-image-processing-alerts"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# 邮件订阅（如果提供了邮箱地址）
resource "aws_sns_topic_subscription" "email_alerts" {
  count = var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.image_processing_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Lambda函数错误率告警
resource "aws_cloudwatch_metric_alarm" "lambda_error_rate" {
  alarm_name          = "${var.project_name}-image-generator-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "图片生成Lambda函数错误率过高"
  alarm_actions       = [aws_sns_topic.image_processing_alerts.arn]
  ok_actions         = [aws_sns_topic.image_processing_alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.image_generator.function_name
  }

  tags = {
    Name        = "${var.project_name}-image-generator-error-rate"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# Lambda函数执行时长告警
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.project_name}-image-generator-duration-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "240000"  # 4分钟（毫秒）
  alarm_description   = "图片生成Lambda函数执行时间过长"
  alarm_actions       = [aws_sns_topic.image_processing_alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.image_generator.function_name
  }

  tags = {
    Name        = "${var.project_name}-image-generator-duration"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# Lambda函数并发执行数告警
resource "aws_cloudwatch_metric_alarm" "lambda_concurrent_executions" {
  alarm_name          = "${var.project_name}-image-generator-concurrency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ConcurrentExecutions"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "80"  # 80个并发执行
  alarm_description   = "图片生成Lambda函数并发执行数过高"
  alarm_actions       = [aws_sns_topic.image_processing_alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.image_generator.function_name
  }

  tags = {
    Name        = "${var.project_name}-image-generator-concurrency"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# 优化版Lambda函数的告警（如果存在）
resource "aws_cloudwatch_metric_alarm" "lambda_optimized_error_rate" {
  count = length(aws_lambda_function.image_generator_optimized) > 0 ? 1 : 0

  alarm_name          = "${var.project_name}-image-generator-optimized-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "优化图片生成Lambda函数错误率过高"
  alarm_actions       = [aws_sns_topic.image_processing_alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.image_generator_optimized[0].function_name
  }

  tags = {
    Name        = "${var.project_name}-image-generator-optimized-error-rate"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# 自定义指标告警 - 图片生成成功率
resource "aws_cloudwatch_metric_alarm" "image_generation_success_rate" {
  alarm_name          = "${var.project_name}-image-generation-success-rate-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ImageGenerationSuccessRate"
  namespace           = "AI-PPT-Assistant/ImageGeneration"
  period              = "300"
  statistic           = "Average"
  threshold           = "90"  # 成功率低于90%时告警
  alarm_description   = "图片生成成功率过低"
  alarm_actions       = [aws_sns_topic.image_processing_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-image-generation-success-rate"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# 自定义指标告警 - 缓存命中率
resource "aws_cloudwatch_metric_alarm" "cache_hit_rate" {
  count = var.enable_caching ? 1 : 0

  alarm_name          = "${var.project_name}-image-cache-hit-rate-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "ImageCacheHitRate"
  namespace           = "AI-PPT-Assistant/ImageGeneration"
  period              = "300"
  statistic           = "Average"
  threshold           = "30"  # 缓存命中率低于30%时告警
  alarm_description   = "图片缓存命中率过低，可能影响性能"
  alarm_actions       = [aws_sns_topic.image_processing_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-image-cache-hit-rate"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# 自定义指标告警 - 平均生成时间
resource "aws_cloudwatch_metric_alarm" "average_generation_time" {
  alarm_name          = "${var.project_name}-image-generation-time-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ImageGenerationAvgTime"
  namespace           = "AI-PPT-Assistant/ImageGeneration"
  period              = "300"
  statistic           = "Average"
  threshold           = "30"  # 平均生成时间超过30秒时告警
  alarm_description   = "图片平均生成时间过长"
  alarm_actions       = [aws_sns_topic.image_processing_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-image-generation-time"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# Bedrock服务限制告警
resource "aws_cloudwatch_metric_alarm" "bedrock_throttling" {
  alarm_name          = "${var.project_name}-bedrock-throttling-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "UserErrors"
  namespace           = "AWS/Bedrock"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Bedrock服务出现限流或用户错误"
  alarm_actions       = [aws_sns_topic.image_processing_alerts.arn]
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "${var.project_name}-bedrock-throttling"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# S3存储空间告警
resource "aws_cloudwatch_metric_alarm" "s3_bucket_size" {
  alarm_name          = "${var.project_name}-s3-bucket-size-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "BucketSizeBytes"
  namespace           = "AWS/S3"
  period              = "86400"  # 每天检查一次
  statistic           = "Average"
  threshold           = "5368709120"  # 5GB
  alarm_description   = "S3存储桶大小超过阈值"
  alarm_actions       = [aws_sns_topic.image_processing_alerts.arn]

  dimensions = {
    BucketName  = aws_s3_bucket.presentations.bucket
    StorageType = "StandardStorage"
  }

  tags = {
    Name        = "${var.project_name}-s3-bucket-size"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# CloudWatch仪表板
resource "aws_cloudwatch_dashboard" "image_processing" {
  dashboard_name = "${var.project_name}-image-processing-${var.environment}"

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
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.image_generator.function_name],
            [".", "Errors", ".", "."],
            [".", "Duration", ".", "."],
            [".", "Throttles", ".", "."]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Lambda函数基础指标"
          view   = "timeSeries"
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
            ["AI-PPT-Assistant/ImageGeneration", "ImageGenerationSuccessRate"],
            [".", "ImageGenerationAvgTime"],
            [".", "ImageCacheHitRate"],
            [".", "ImageGenerationCost"]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "图片生成业务指标"
          view   = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", aws_lambda_function.image_generator.function_name]
          ]
          period = 300
          stat   = "Maximum"
          region = var.aws_region
          title  = "Lambda并发执行数"
          view   = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 6
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/S3", "BucketSizeBytes", "BucketName", aws_s3_bucket.presentations.bucket, "StorageType", "StandardStorage"],
            [".", "NumberOfObjects", ".", ".", ".", "AllStorageTypes"]
          ]
          period = 86400
          stat   = "Average"
          region = var.aws_region
          title  = "S3存储指标"
          view   = "timeSeries"
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 6
        width  = 8
        height = 6

        properties = {
          metrics = [
            ["AWS/Bedrock", "Invocations", "ModelId", var.nova_model_id],
            [".", "UserErrors", ".", "."],
            [".", "ClientErrors", ".", "."]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Bedrock模型指标"
          view   = "timeSeries"
        }
      },
      {
        type   = "log"
        x      = 0
        y      = 12
        width  = 24
        height = 6

        properties = {
          query   = "SOURCE '/aws/lambda/${aws_lambda_function.image_generator.function_name}'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 50"
          region  = var.aws_region
          title   = "最近的错误日志"
        }
      }
    ]
  })
}

# X-Ray服务地图（如果启用了追踪）
resource "aws_xray_sampling_rule" "image_processing" {
  count = var.enable_xray_tracing ? 1 : 0

  rule_name      = "img-proc-${var.environment}"
  priority       = 9000
  version        = 1
  reservoir_size = 1
  fixed_rate     = 0.1
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "*"
  service_name   = "image-processing"
  resource_arn   = "*"

  tags = {
    Name        = "${var.project_name}-image-processing-sampling"
    Environment = var.environment
    Component   = "Monitoring"
  }
}

# 输出
output "monitoring_sns_topic_arn" {
  description = "监控告警SNS主题ARN"
  value       = aws_sns_topic.image_processing_alerts.arn
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch仪表板URL"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.image_processing.dashboard_name}"
}

output "log_group_names" {
  description = "Lambda函数日志组名称"
  value = {
    image_generator = aws_cloudwatch_log_group.image_generator_logs.name
    image_generator_optimized = length(aws_cloudwatch_log_group.image_generator_optimized_logs) > 0 ? aws_cloudwatch_log_group.image_generator_optimized_logs[0].name : null
  }
}