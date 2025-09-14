# CloudWatch Dashboard for AI-PPT-Assistant Image Generation Performance

resource "aws_cloudwatch_dashboard" "ai_ppt_performance" {
  dashboard_name = "AI-PPT-Assistant-Performance"

  dashboard_body = jsonencode({
    widgets = [
      # 总览统计
      {
        type = "metric"
        properties = {
          title   = "Image Generation Overview"
          region  = var.aws_region
          stacked = false
          metrics = [
            ["AI-PPT-Assistant/ImageGeneration", "total_requests"],
            ["AI-PPT-Assistant/ImageGeneration", "successful_generations"],
            ["AI-PPT-Assistant/ImageGeneration", "generation_errors"]
          ]
          period = 300
          stat   = "Sum"
          view   = "timeSeries"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
        x      = 0
        y      = 0
        width  = 8
        height = 6
      },

      # API延迟
      {
        type = "metric"
        properties = {
          title   = "API Latency by Model"
          region  = var.aws_region
          stacked = false
          metrics = [
            ["AI-PPT-Assistant/ImageGeneration", "api_latency_amazon.nova-canvas-v1:0"],
            ["AI-PPT-Assistant/ImageGeneration", "api_latency_stability.stable-diffusion-xl-v1"]
          ]
          period = 60
          stat   = "Average"
          view   = "timeSeries"
          yAxis = {
            left = {
              min   = 0
              label = "Latency (ms)"
            }
          }
        }
        x      = 8
        y      = 0
        width  = 8
        height = 6
      },

      # 缓存性能
      {
        type = "metric"
        properties = {
          title   = "Cache Performance"
          region  = var.aws_region
          stacked = false
          metrics = [
            ["AI-PPT-Assistant/ImageGeneration", "cache_hits"],
            ["AI-PPT-Assistant/ImageGeneration", "cache_misses"]
          ]
          period = 300
          stat   = "Sum"
          view   = "timeSeries"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
        x      = 16
        y      = 0
        width  = 8
        height = 6
      },

      # 缓存命中率
      {
        type = "metric"
        properties = {
          title  = "Cache Hit Rate"
          region = var.aws_region
          metrics = [
            [{
              expression = "m1 / (m1 + m2) * 100"
              label      = "Hit Rate %"
              id         = "e1"
            }],
            ["AI-PPT-Assistant/ImageGeneration", "cache_hits", { id = "m1", visible = false }],
            [".", "cache_misses", { id = "m2", visible = false }]
          ]
          period = 300
          stat   = "Average"
          view   = "singleValue"
        }
        x      = 0
        y      = 6
        width  = 4
        height = 4
      },

      # 平均生成时间
      {
        type = "metric"
        properties = {
          title  = "Average Generation Time"
          region = var.aws_region
          metrics = [
            ["AI-PPT-Assistant/ImageGeneration", "GenerationLatency"]
          ]
          period = 300
          stat   = "Average"
          view   = "singleValue"
        }
        x      = 4
        y      = 6
        width  = 4
        height = 4
      },

      # 成功率
      {
        type = "metric"
        properties = {
          title  = "Success Rate"
          region = var.aws_region
          metrics = [
            [{
              expression = "m1 / m2 * 100"
              label      = "Success Rate %"
              id         = "e1"
            }],
            ["AI-PPT-Assistant/ImageGeneration", "successful_generations", { id = "m1", visible = false }],
            [".", "total_requests", { id = "m2", visible = false }]
          ]
          period = 300
          stat   = "Average"
          view   = "singleValue"
        }
        x      = 8
        y      = 6
        width  = 4
        height = 4
      },

      # 并发请求数
      {
        type = "metric"
        properties = {
          title   = "Concurrent Requests"
          region  = var.aws_region
          stacked = false
          metrics = [
            ["AI-PPT-Assistant/ImageGeneration", "concurrent_requests"],
            ["AI-PPT-Assistant/ImageGeneration", "concurrent_requests"]
          ]
          period = 60
          stat   = "Average"
          view   = "timeSeries"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
        x      = 12
        y      = 6
        width  = 6
        height = 6
      },

      # 错误分布
      {
        type = "metric"
        properties = {
          title   = "Error Distribution"
          region  = var.aws_region
          stacked = true
          metrics = [
            ["AI-PPT-Assistant/ImageGeneration", "errors"],
            ["AI-PPT-Assistant/ImageGeneration", "errors"],
            ["AI-PPT-Assistant/ImageGeneration", "errors"],
            ["AI-PPT-Assistant/ImageGeneration", "errors"]
          ]
          period = 300
          stat   = "Sum"
          view   = "timeSeries"
        }
        x      = 18
        y      = 6
        width  = 6
        height = 6
      },

      # 模型使用分布
      {
        type = "metric"
        properties = {
          title  = "Model Usage Distribution"
          region = var.aws_region
          metrics = [
            ["AI-PPT-Assistant/ImageGeneration", "model_usage"],
            ["AI-PPT-Assistant/ImageGeneration", "model_usage"],
            ["AI-PPT-Assistant/ImageGeneration", "model_usage"]
          ]
          period = 3600
          stat   = "Sum"
          view   = "pie"
        }
        x      = 0
        y      = 12
        width  = 6
        height = 6
      },

      # 批处理性能
      {
        type = "metric"
        properties = {
          title   = "Batch Processing Performance"
          region  = var.aws_region
          stacked = false
          metrics = [
            ["AI-PPT-Assistant/ImageGeneration", "batch_size"],
            ["AI-PPT-Assistant/ImageGeneration", "batch_generation_time"]
          ]
          period = 300
          stat   = "Average"
          view   = "timeSeries"
          yAxis = {
            left = {
              min   = 0
              label = "Batch Size"
            }
            right = {
              min   = 0
              label = "Time (s)"
            }
          }
        }
        x      = 6
        y      = 12
        width  = 9
        height = 6
      },

      # Lambda性能
      {
        type = "metric"
        properties = {
          title   = "Lambda Performance"
          region  = var.aws_region
          stacked = false
          metrics = [
            ["AWS/Lambda", "Duration"],
            ["AWS/Lambda", "Errors"],
            ["AWS/Lambda", "ConcurrentExecutions"]
          ]
          period = 60
          stat   = "Average"
          view   = "timeSeries"
        }
        x      = 15
        y      = 12
        width  = 9
        height = 6
      },

      # 成本追踪
      {
        type = "metric"
        properties = {
          title   = "Estimated API Costs"
          region  = var.aws_region
          stacked = true
          metrics = [
            [{
              expression = "m1 * 0.04"  # Nova Canvas cost per image
              label      = "Nova Canvas Cost ($)"
              id         = "e1"
            }],
            [{
              expression = "m2 * 0.02"  # Stability AI cost per image
              label      = "Stability AI Cost ($)"
              id         = "e2"
            }],
            ["AI-PPT-Assistant/ImageGeneration", "api_calls_amazon.nova-canvas-v1:0", { id = "m1", visible = false }],
            [".", "api_calls_stability.stable-diffusion-xl-v1", { id = "m2", visible = false }]
          ]
          period = 3600
          stat   = "Sum"
          view   = "timeSeries"
          yAxis = {
            left = {
              min   = 0
              label = "Cost ($)"
            }
          }
        }
        x      = 0
        y      = 18
        width  = 12
        height = 6
      },

      # 系统健康度
      {
        type = "metric"
        properties = {
          title  = "System Health Score"
          region = var.aws_region
          metrics = [
            [{
              expression = "(m1 / m2 * 100) * (m3 / (m3 + m4)) * (1 - m5 / 100)"
              label      = "Health Score"
              id         = "e1"
            }],
            ["AI-PPT-Assistant/ImageGeneration", "successful_generations"],
            ["AI-PPT-Assistant/ImageGeneration", "total_requests"],
            ["AI-PPT-Assistant/ImageGeneration", "cache_hits"],
            ["AI-PPT-Assistant/ImageGeneration", "cache_misses"],
            ["AWS/Lambda", "Errors"]
          ]
          period = 900
          stat   = "Average"
          view   = "gauge"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
        x      = 12
        y      = 18
        width  = 6
        height = 6
      },

      # 实时日志
      {
        type = "log"
        properties = {
          title  = "Recent Errors and Warnings"
          region = var.aws_region
          query  = <<-EOT
            SOURCE '/aws/lambda/ai-ppt-image-generator'
            | fields @timestamp, @message
            | filter @message like /ERROR|WARNING/
            | sort @timestamp desc
            | limit 20
          EOT
        }
        x      = 18
        y      = 18
        width  = 6
        height = 6
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_api_latency" {
  alarm_name          = "ai-ppt-high-api-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "api_latency_amazon.nova-canvas-v1:0"
  namespace          = "AI-PPT-Assistant/ImageGeneration"
  period             = "300"
  statistic          = "Average"
  threshold          = "5000"
  alarm_description  = "This metric monitors API latency"
  alarm_actions      = [aws_sns_topic.alerts.arn]

  dimensions = {
    Model = "amazon.nova-canvas-v1:0"
  }
}

resource "aws_cloudwatch_metric_alarm" "low_cache_hit_rate" {
  alarm_name          = "ai-ppt-low-cache-hit-rate"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  threshold          = "30"
  alarm_description  = "Cache hit rate is below 30%"

  metric_query {
    id          = "e1"
    expression  = "m1 / (m1 + m2) * 100"
    label       = "Cache Hit Rate"
    return_data = true
  }

  metric_query {
    id = "m1"
    metric {
      metric_name = "cache_hits"
      namespace   = "AI-PPT-Assistant/ImageGeneration"
      period      = "300"
      stat        = "Sum"
    }
  }

  metric_query {
    id = "m2"
    metric {
      metric_name = "cache_misses"
      namespace   = "AI-PPT-Assistant/ImageGeneration"
      period      = "300"
      stat        = "Sum"
    }
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "ai-ppt-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  threshold          = "10"
  alarm_description  = "Error rate is above 10%"

  metric_query {
    id          = "e1"
    expression  = "(m2 / m1) * 100"
    label       = "Error Rate"
    return_data = true
  }

  metric_query {
    id = "m1"
    metric {
      metric_name = "total_requests"
      namespace   = "AI-PPT-Assistant/ImageGeneration"
      period      = "300"
      stat        = "Sum"
    }
  }

  metric_query {
    id = "m2"
    metric {
      metric_name = "generation_errors"
      namespace   = "AI-PPT-Assistant/ImageGeneration"
      period      = "300"
      stat        = "Sum"
    }
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "ai-ppt-performance-alerts"
}

# 暂时注释掉 email 订阅，因为没有配置有效的 email 地址
# resource "aws_sns_topic_subscription" "alert_email" {
#   topic_arn = aws_sns_topic.alerts.arn
#   protocol  = "email"
#   endpoint  = var.alert_email
# }

# Outputs
output "dashboard_url" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.ai_ppt_performance.dashboard_name}"
}