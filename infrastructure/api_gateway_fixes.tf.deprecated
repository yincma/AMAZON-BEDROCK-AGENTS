# API Gateway 修复配置
# 添加缺失的资源和路由

# ==========================================
# 1. 添加 /tasks 资源和路由
# ==========================================

# /tasks 资源
resource "aws_api_gateway_resource" "tasks" {
  rest_api_id = module.api_gateway.rest_api_id
  parent_id   = module.api_gateway.rest_api_root_resource_id
  path_part   = "tasks"
}

# /tasks/{taskId} 资源
resource "aws_api_gateway_resource" "task_id" {
  rest_api_id = module.api_gateway.rest_api_id
  parent_id   = aws_api_gateway_resource.tasks.id
  path_part   = "{taskId}"
}

# GET /tasks/{taskId} 方法
resource "aws_api_gateway_method" "get_task" {
  rest_api_id   = module.api_gateway.rest_api_id
  resource_id   = aws_api_gateway_resource.task_id.id
  http_method   = "GET"
  authorization = "NONE"
  api_key_required = true

  request_parameters = {
    "method.request.path.taskId" = true
  }
}

# GET /tasks/{taskId} 集成
resource "aws_api_gateway_integration" "get_task" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.task_id.id
  http_method = aws_api_gateway_method.get_task.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.lambda.function_invoke_arns["presentation_status"]

  depends_on = [
    aws_api_gateway_method.get_task
  ]
}

# ==========================================
# 2. 添加 /templates 资源和路由（Mock响应）
# ==========================================

# /templates 资源
resource "aws_api_gateway_resource" "templates" {
  rest_api_id = module.api_gateway.rest_api_id
  parent_id   = module.api_gateway.rest_api_root_resource_id
  path_part   = "templates"
}

# GET /templates 方法
resource "aws_api_gateway_method" "get_templates" {
  rest_api_id   = module.api_gateway.rest_api_id
  resource_id   = aws_api_gateway_resource.templates.id
  http_method   = "GET"
  authorization = "NONE"
  api_key_required = true
}

# GET /templates Mock集成（暂时返回静态数据）
resource "aws_api_gateway_integration" "get_templates" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.templates.id
  http_method = aws_api_gateway_method.get_templates.http_method

  type = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }

  depends_on = [
    aws_api_gateway_method.get_templates
  ]
}

# GET /templates 方法响应
resource "aws_api_gateway_method_response" "get_templates_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.templates.id
  http_method = aws_api_gateway_method.get_templates.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# GET /templates 集成响应
resource "aws_api_gateway_integration_response" "get_templates_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.templates.id
  http_method = aws_api_gateway_method.get_templates.http_method
  status_code = aws_api_gateway_method_response.get_templates_200.status_code

  response_templates = {
    "application/json" = jsonencode([
      {
        template_id = "executive_summary"
        name = "执行摘要"
        description = "适用于高管汇报的专业模板"
        category = "商务"
        style = "corporate"
        default_slide_count = 15
      },
      {
        template_id = "technology_showcase"
        name = "技术展示"
        description = "展示技术产品和创新的模板"
        category = "技术"
        style = "modern"
        default_slide_count = 20
      },
      {
        template_id = "sales_pitch"
        name = "销售演示"
        description = "用于产品销售和推广的模板"
        category = "销售"
        style = "creative"
        default_slide_count = 12
      },
      {
        template_id = "educational"
        name = "教育培训"
        description = "用于培训和教育场景的模板"
        category = "教育"
        style = "minimal"
        default_slide_count = 25
      }
    ])
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [
    aws_api_gateway_integration.get_templates
  ]
}

# ==========================================
# 3. 创建正确的 GET /presentations Lambda 函数
# ==========================================

# 创建一个简单的 Lambda 函数来处理 GET /presentations
resource "aws_lambda_function" "list_presentations" {
  filename         = "${path.module}/lambda_functions/list_presentations.zip"
  function_name    = "ai-ppt-assistant-list-presentations"
  role            = module.lambda.lambda_execution_role_arn
  handler         = "list_presentations.handler"
  runtime         = "python3.12"
  architectures   = ["arm64"]
  timeout         = 10
  memory_size     = 256

  environment {
    variables = {
      DYNAMODB_TABLE = module.dynamodb.table_name
    }
  }

  tags = {
    Name = "ai-ppt-assistant-list-presentations"
    Environment = "dev"
  }
}

# Lambda 权限
resource "aws_lambda_permission" "list_presentations_permission" {
  statement_id  = "AllowAPIGatewayInvoke-list-presentations"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.list_presentations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${module.api_gateway.rest_api_id}/*/*"
}

# 更新 GET /presentations 集成
resource "aws_api_gateway_integration" "list_presentations_fixed" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = module.api_gateway.resource_ids["presentations"]
  http_method = "GET"

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/${aws_lambda_function.list_presentations.arn}/invocations"

  depends_on = [
    aws_lambda_permission.list_presentations_permission
  ]
}

# ==========================================
# 4. CORS 配置
# ==========================================

# OPTIONS /templates
resource "aws_api_gateway_method" "templates_options" {
  rest_api_id   = module.api_gateway.rest_api_id
  resource_id   = aws_api_gateway_resource.templates.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "templates_options" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.templates.id
  http_method = aws_api_gateway_method.templates_options.http_method

  type = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "templates_options_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.templates.id
  http_method = aws_api_gateway_method.templates_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "templates_options_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.templates.id
  http_method = aws_api_gateway_method.templates_options.http_method
  status_code = aws_api_gateway_method_response.templates_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS /tasks/{taskId}
resource "aws_api_gateway_method" "task_options" {
  rest_api_id   = module.api_gateway.rest_api_id
  resource_id   = aws_api_gateway_resource.task_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "task_options" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.task_id.id
  http_method = aws_api_gateway_method.task_options.http_method

  type = "MOCK"
  
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "task_options_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.task_id.id
  http_method = aws_api_gateway_method.task_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "task_options_200" {
  rest_api_id = module.api_gateway.rest_api_id
  resource_id = aws_api_gateway_resource.task_id.id
  http_method = aws_api_gateway_method.task_options.http_method
  status_code = aws_api_gateway_method_response.task_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}