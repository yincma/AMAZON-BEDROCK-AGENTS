# Lambda 函数 - Get Task
# 独立的Lambda函数定义，用于处理GET /tasks/{task_id}请求

resource "aws_lambda_function" "get_task" {
  filename      = "${path.module}/../lambdas/api/get_task.zip"
  function_name = "ai-ppt-assistant-get-task"
  role          = module.lambda.lambda_execution_role_arn
  handler       = "get_task.lambda_handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 10
  memory_size   = 256

  environment {
    variables = {
      TASKS_TABLE_NAME = "${local.name_prefix}-tasks"
      LOG_LEVEL        = "INFO"
    }
  }

  tags = {
    Name        = "ai-ppt-assistant-get-task"
    Environment = var.environment
    Project     = var.project_name
  }

  depends_on = [module.lambda]
}

# Lambda 权限 - 允许API Gateway调用
resource "aws_lambda_permission" "get_task_permission" {
  statement_id  = "AllowAPIGatewayInvoke-get-task"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_task.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${module.api_gateway.rest_api_id}/*/*"
}