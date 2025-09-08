# Outputs for CloudWatch Monitoring Module

# ============================================================================
# SNS Topic Outputs
# ============================================================================

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "sns_topic_name" {
  description = "Name of the SNS topic for alerts"
  value       = aws_sns_topic.alerts.name
}

output "kms_key_id" {
  description = "ID of the KMS key used for SNS encryption"
  value       = aws_kms_key.sns_key.key_id
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for SNS encryption"
  value       = aws_kms_key.sns_key.arn
}

# ============================================================================
# Lambda Alarm Outputs
# ============================================================================

output "lambda_error_alarm_names" {
  description = "Names of Lambda error rate alarms"
  value = {
    for k, v in aws_cloudwatch_metric_alarm.lambda_error_rate : k => v.alarm_name
  }
}

output "lambda_duration_alarm_names" {
  description = "Names of Lambda duration alarms"
  value = {
    for k, v in aws_cloudwatch_metric_alarm.lambda_duration : k => v.alarm_name
  }
}

output "lambda_throttle_alarm_names" {
  description = "Names of Lambda throttle alarms"
  value = {
    for k, v in aws_cloudwatch_metric_alarm.lambda_throttles : k => v.alarm_name
  }
}

output "lambda_error_alarm_arns" {
  description = "ARNs of Lambda error rate alarms"
  value = {
    for k, v in aws_cloudwatch_metric_alarm.lambda_error_rate : k => v.arn
  }
}

output "lambda_duration_alarm_arns" {
  description = "ARNs of Lambda duration alarms"
  value = {
    for k, v in aws_cloudwatch_metric_alarm.lambda_duration : k => v.arn
  }
}

output "lambda_throttle_alarm_arns" {
  description = "ARNs of Lambda throttle alarms"
  value = {
    for k, v in aws_cloudwatch_metric_alarm.lambda_throttles : k => v.arn
  }
}

# ============================================================================
# API Gateway Alarm Outputs
# ============================================================================

output "api_gateway_4xx_alarm_name" {
  description = "Name of API Gateway 4XX error alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_4xx_error_rate.alarm_name
}

output "api_gateway_4xx_alarm_arn" {
  description = "ARN of API Gateway 4XX error alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_4xx_error_rate.arn
}

output "api_gateway_5xx_alarm_name" {
  description = "Name of API Gateway 5XX error alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_5xx_error_rate.alarm_name
}

output "api_gateway_5xx_alarm_arn" {
  description = "ARN of API Gateway 5XX error alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_5xx_error_rate.arn
}

output "api_gateway_latency_alarm_name" {
  description = "Name of API Gateway latency alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_latency.alarm_name
}

output "api_gateway_latency_alarm_arn" {
  description = "ARN of API Gateway latency alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_latency.arn
}

output "api_gateway_count_alarm_name" {
  description = "Name of API Gateway high traffic alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_count.alarm_name
}

output "api_gateway_count_alarm_arn" {
  description = "ARN of API Gateway high traffic alarm"
  value       = aws_cloudwatch_metric_alarm.api_gateway_count.arn
}

# ============================================================================
# DynamoDB Alarm Outputs
# ============================================================================

output "dynamodb_read_throttle_alarm_name" {
  description = "Name of DynamoDB read throttle alarm (if enabled)"
  value       = var.enable_dynamodb_monitoring && length(aws_cloudwatch_metric_alarm.dynamodb_read_throttles) > 0 ? aws_cloudwatch_metric_alarm.dynamodb_read_throttles[0].alarm_name : null
}

output "dynamodb_read_throttle_alarm_arn" {
  description = "ARN of DynamoDB read throttle alarm (if enabled)"
  value       = var.enable_dynamodb_monitoring && length(aws_cloudwatch_metric_alarm.dynamodb_read_throttles) > 0 ? aws_cloudwatch_metric_alarm.dynamodb_read_throttles[0].arn : null
}

output "dynamodb_write_throttle_alarm_name" {
  description = "Name of DynamoDB write throttle alarm (if enabled)"
  value       = var.enable_dynamodb_monitoring && length(aws_cloudwatch_metric_alarm.dynamodb_write_throttles) > 0 ? aws_cloudwatch_metric_alarm.dynamodb_write_throttles[0].alarm_name : null
}

output "dynamodb_write_throttle_alarm_arn" {
  description = "ARN of DynamoDB write throttle alarm (if enabled)"
  value       = var.enable_dynamodb_monitoring && length(aws_cloudwatch_metric_alarm.dynamodb_write_throttles) > 0 ? aws_cloudwatch_metric_alarm.dynamodb_write_throttles[0].arn : null
}

# ============================================================================
# CloudWatch Dashboard Outputs
# ============================================================================

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "dashboard_arn" {
  description = "ARN of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_arn
}

output "dashboard_url" {
  description = "URL to access the CloudWatch dashboard"
  value       = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

# ============================================================================
# Log Group Outputs
# ============================================================================

output "insights_log_group_name" {
  description = "Name of the CloudWatch Insights log group"
  value       = aws_cloudwatch_log_group.insights_queries.name
}

output "insights_log_group_arn" {
  description = "ARN of the CloudWatch Insights log group"
  value       = aws_cloudwatch_log_group.insights_queries.arn
}

# ============================================================================
# Summary Outputs
# ============================================================================

output "monitoring_summary" {
  description = "Summary of monitoring components created"
  value = {
    sns_topic               = aws_sns_topic.alerts.name
    dashboard_name          = aws_cloudwatch_dashboard.main.dashboard_name
    lambda_functions_monitored = length(var.lambda_function_names)
    email_subscriptions     = length(var.alert_email_addresses)
    total_alarms_created   = (
      length(aws_cloudwatch_metric_alarm.lambda_error_rate) +
      length(aws_cloudwatch_metric_alarm.lambda_duration) +
      length(aws_cloudwatch_metric_alarm.lambda_throttles) +
      1 + # API Gateway 4XX
      1 + # API Gateway 5XX  
      1 + # API Gateway latency
      1 + # API Gateway count
      (var.enable_dynamodb_monitoring && var.dynamodb_table_name != "" ? 2 : 0) # DynamoDB throttles
    )
  }
}