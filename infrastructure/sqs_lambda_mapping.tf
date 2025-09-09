# SQS to Lambda Event Source Mapping Configuration
# Critical for async task processing - connects SQS queue to processing functions

# AWS Expert: Single task processor orchestrates the entire workflow
# Only task_processor should consume from SQS queue - it coordinates other functions
resource "aws_lambda_event_source_mapping" "task_processor" {
  event_source_arn = aws_sqs_queue.task_queue.arn
  function_name    = module.lambda.lambda_function_names["api_task_processor"]
  enabled          = true
  
  # AWS Expert: Optimal batch configuration for orchestration function
  batch_size                         = 1
  maximum_batching_window_in_seconds = 5
  function_response_types = ["ReportBatchItemFailures"]
  
  depends_on = [module.lambda]
}

# AWS Expert: CloudWatch monitoring for event source mappings
resource "aws_cloudwatch_metric_alarm" "sqs_processing_errors" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-${var.environment}-sqs-processing-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors from SQS processing"
  alarm_actions       = var.enable_monitoring ? [module.monitoring[0].sns_topic_arn] : []

  dimensions = {
    FunctionName = module.lambda.lambda_function_names["api_task_processor"]
  }
}

# Note: SNS topic is created by the monitoring module

# Dead Letter Queue monitoring
resource "aws_cloudwatch_metric_alarm" "dlq_message_count" {
  count = var.enable_monitoring ? 1 : 0
  
  alarm_name          = "${var.project_name}-${var.environment}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfVisibleMessages"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors messages in dead letter queue"
  alarm_actions       = []

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }
}