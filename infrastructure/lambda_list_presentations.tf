# Lambda 函数 - List Presentations
# 独立的Lambda函数定义，用于处理GET /presentations请求

resource "aws_lambda_function" "list_presentations" {
  filename      = "${path.module}/../lambdas/api/list_presentations.zip"
  function_name = "ai-ppt-assistant-list-presentations"
  role          = module.lambda.lambda_execution_role_arn
  handler       = "list_presentations.handler"
  runtime       = "python3.12"
  architectures = ["arm64"]
  timeout       = 10
  memory_size   = 256

  environment {
    variables = {
      DYNAMODB_TABLE = module.dynamodb.table_name
    }
  }

  tags = {
    Name        = "ai-ppt-assistant-list-presentations"
    Environment = var.environment
    Project     = var.project_name
  }

  depends_on = [module.lambda]
}

# Lambda 权限 - 允许API Gateway调用
resource "aws_lambda_permission" "list_presentations_permission" {
  statement_id  = "AllowAPIGatewayInvoke-list-presentations"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.list_presentations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${module.api_gateway.rest_api_id}/*/*"
}