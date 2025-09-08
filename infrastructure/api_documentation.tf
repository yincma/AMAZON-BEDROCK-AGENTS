# API文档自动生成基础设施配置
# 创建API Gateway文档资源和S3托管的文档页面

# ============================================================================
# 本地变量定义
# ============================================================================

locals {
  # 文档相关的命名
  documentation_name_prefix = "${var.project_name}-${var.environment}-docs"
  
  # OpenAPI规范文件路径
  openapi_spec_path = "${path.root}/../docs/openapi.yaml"
  
  # 文档版本（基于OpenAPI文件的修改时间）
  documentation_version = formatdate("YYYY-MM-DD-hhmm", timestamp())
}

# ============================================================================
# S3存储桶用于托管文档
# ============================================================================

# 创建专用于API文档的S3存储桶
resource "aws_s3_bucket" "api_documentation" {
  count = var.enable_api_documentation ? 1 : 0

  bucket = "${local.documentation_name_prefix}-${random_id.bucket_suffix.hex}"

  tags = merge(
    local.common_tags,
    {
      Name        = "${local.documentation_name_prefix}-bucket"
      Purpose     = "API Documentation Hosting"
      Environment = var.environment
    }
  )
}

# 配置存储桶的公共访问设置
resource "aws_s3_bucket_public_access_block" "api_documentation" {
  count = var.enable_api_documentation ? 1 : 0

  bucket = aws_s3_bucket.api_documentation[0].id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# 配置存储桶策略以允许公共读取访问
resource "aws_s3_bucket_policy" "api_documentation" {
  count = var.enable_api_documentation ? 1 : 0

  bucket = aws_s3_bucket.api_documentation[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.api_documentation[0].arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.api_documentation]
}

# 配置存储桶网站托管
resource "aws_s3_bucket_website_configuration" "api_documentation" {
  count = var.enable_api_documentation ? 1 : 0

  bucket = aws_s3_bucket.api_documentation[0].id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

# ============================================================================
# API Gateway文档资源
# ============================================================================

# 创建API Gateway文档版本
resource "aws_api_gateway_documentation_version" "main" {
  count = var.enable_api_documentation ? 1 : 0

  version     = local.documentation_version
  rest_api_id = module.api_gateway.rest_api_id
  description = "API Documentation - Generated on ${formatdate("YYYY-MM-DD hh:mm:ss", timestamp())}"

  depends_on = [
    aws_api_gateway_documentation_part.api,
    aws_api_gateway_documentation_part.resources,
    aws_api_gateway_documentation_part.methods
  ]
}

# API级别的文档
resource "aws_api_gateway_documentation_part" "api" {
  count = var.enable_api_documentation ? 1 : 0

  rest_api_id = module.api_gateway.rest_api_id
  location {
    type = "API"
  }
  properties = jsonencode({
    info = {
      title       = "AI PPT Assistant API"
      version     = "1.0.0"
      description = "AI驱动的PowerPoint演示文稿生成和管理API"
      contact = {
        name  = "AI PPT Assistant Support"
        email = "support@ai-ppt-assistant.com"
      }
    }
    host     = replace(module.api_gateway.api_url, "https://", "")
    basePath = "/${var.stage_name}"
    schemes  = ["https"]
    consumes = ["application/json"]
    produces = ["application/json", "application/vnd.openxmlformats-officedocument.presentationml.presentation"]
    securityDefinitions = {
      ApiKeyAuth = {
        type = "apiKey"
        name = "X-API-Key"
        in   = "header"
      }
    }
    security = [
      {
        ApiKeyAuth = []
      }
    ]
  })
}

# 资源级别的文档
resource "aws_api_gateway_documentation_part" "resources" {
  for_each = var.enable_api_documentation ? {
    presentations = {
      path        = "/presentations"
      description = "演示文稿资源 - 用于创建和管理AI生成的PowerPoint演示文稿"
    }
    presentation_id = {
      path        = "/presentations/{id}"
      description = "单个演示文稿资源 - 用于获取特定演示文稿的详细信息和状态"
    }
    presentation_download = {
      path        = "/presentations/{id}/download"
      description = "演示文稿下载资源 - 用于下载已完成的演示文稿文件"
    }
    sessions = {
      path        = "/sessions"
      description = "会话资源 - 用于创建和管理用户会话"
    }
    session_id = {
      path        = "/sessions/{id}"
      description = "单个会话资源 - 用于获取特定会话的详细信息"
    }
    agents = {
      path        = "/agents/{name}/execute"
      description = "AI代理执行资源 - 用于执行特定的AI代理任务"
    }
    tasks = {
      path        = "/tasks/{task_id}"
      description = "任务状态资源 - 用于跟踪异步任务的执行状态"
    }
    templates = {
      path        = "/templates"
      description = "模板资源 - 用于获取可用的演示文稿模板列表"
    }
    health = {
      path        = "/health"
      description = "健康检查资源 - 用于检查API服务的健康状态"
    }
    health_ready = {
      path        = "/health/ready"
      description = "就绪检查资源 - 用于检查API服务是否准备好接受请求"
    }
  } : {}

  rest_api_id = module.api_gateway.rest_api_id
  location {
    type = "RESOURCE"
    path = each.value.path
  }
  properties = jsonencode({
    description = each.value.description
  })
}

# 方法级别的文档
resource "aws_api_gateway_documentation_part" "methods" {
  for_each = var.enable_api_documentation ? {
    # POST /presentations
    create_presentation = {
      path        = "/presentations"
      method      = "POST"
      description = "创建新的AI生成演示文稿任务"
      summary     = "生成演示文稿"
      operationId = "createPresentation"
    }
    # GET /presentations
    list_presentations = {
      path        = "/presentations"
      method      = "GET"
      description = "获取演示文稿列表，支持分页和状态过滤"
      summary     = "列出演示文稿"
      operationId = "listPresentations"
    }
    # GET /presentations/{id}
    get_presentation = {
      path        = "/presentations/{id}"
      method      = "GET"
      description = "获取指定演示文稿的详细状态信息"
      summary     = "获取演示文稿状态"
      operationId = "getPresentationStatus"
    }
    # GET /tasks/{task_id}
    get_task = {
      path        = "/tasks/{task_id}"
      method      = "GET"
      description = "获取指定任务的执行状态和结果"
      summary     = "获取任务状态"
      operationId = "getTaskStatus"
    }
    # GET /templates
    get_templates = {
      path        = "/templates"
      method      = "GET"
      description = "获取可用的演示文稿模板列表"
      summary     = "获取模板列表"
      operationId = "getTemplates"
    }
    # GET /health
    health_check = {
      path        = "/health"
      method      = "GET"
      description = "检查API服务的健康状态"
      summary     = "健康检查"
      operationId = "healthCheck"
    }
    # GET /health/ready
    readiness_check = {
      path        = "/health/ready"
      method      = "GET"
      description = "检查API服务是否准备好接受请求"
      summary     = "就绪检查"
      operationId = "readinessCheck"
    }
  } : {}

  rest_api_id = module.api_gateway.rest_api_id
  location {
    type   = "METHOD"
    path   = each.value.path
    method = each.value.method
  }
  properties = jsonencode({
    summary     = each.value.summary
    description = each.value.description
    operationId = each.value.operationId
    tags        = [split("/", each.value.path)[1]]
  })
}

# ============================================================================
# Lambda函数用于生成和更新文档
# ============================================================================

# 创建Lambda函数的ZIP包
data "archive_file" "documentation_generator" {
  count = var.enable_api_documentation ? 1 : 0

  type        = "zip"
  output_path = "${path.module}/documentation_generator.zip"
  
  source {
    content = templatefile("${path.module}/documentation_generator.py", {
      s3_bucket_name    = aws_s3_bucket.api_documentation[0].bucket
      api_gateway_id    = module.api_gateway.rest_api_id
      api_gateway_stage = var.stage_name
    })
    filename = "lambda_function.py"
  }
}

# 创建IAM角色用于Lambda函数
resource "aws_iam_role" "documentation_generator" {
  count = var.enable_api_documentation ? 1 : 0

  name = "${local.documentation_name_prefix}-lambda-role"

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

  tags = local.common_tags
}

# 附加基础Lambda执行策略
resource "aws_iam_role_policy_attachment" "documentation_generator_basic" {
  count = var.enable_api_documentation ? 1 : 0

  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.documentation_generator[0].name
}

# 创建自定义IAM策略用于S3和API Gateway访问
resource "aws_iam_role_policy" "documentation_generator" {
  count = var.enable_api_documentation ? 1 : 0

  name = "${local.documentation_name_prefix}-lambda-policy"
  role = aws_iam_role.documentation_generator[0].id

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
          aws_s3_bucket.api_documentation[0].arn,
          "${aws_s3_bucket.api_documentation[0].arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "apigateway:GET",
          "apigateway:POST",
          "apigateway:PUT",
          "apigateway:PATCH",
          "apigateway:DELETE"
        ]
        Resource = [
          "arn:aws:apigateway:${var.aws_region}::/restapis/${module.api_gateway.rest_api_id}/*",
          "arn:aws:apigateway:${var.aws_region}::/restapis/${module.api_gateway.rest_api_id}"
        ]
      }
    ]
  })
}

# CloudWatch日志组
resource "aws_cloudwatch_log_group" "documentation_generator" {
  count = var.enable_api_documentation ? 1 : 0

  name              = "/aws/lambda/${local.documentation_name_prefix}-generator"
  retention_in_days = var.documentation_retention_days

  tags = merge(
    local.common_tags,
    {
      Name        = "${local.documentation_name_prefix}-generator-logs"
      Environment = var.environment
    }
  )
}

# 创建Lambda函数
resource "aws_lambda_function" "documentation_generator" {
  count = var.enable_api_documentation ? 1 : 0

  filename         = data.archive_file.documentation_generator[0].output_path
  function_name    = "${local.documentation_name_prefix}-generator"
  role            = aws_iam_role.documentation_generator[0].arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.12"
  timeout         = var.documentation_lambda_timeout
  memory_size     = var.documentation_lambda_memory

  source_code_hash = data.archive_file.documentation_generator[0].output_base64sha256

  environment {
    variables = {
      S3_BUCKET_NAME        = aws_s3_bucket.api_documentation[0].bucket
      API_GATEWAY_ID        = module.api_gateway.rest_api_id
      API_GATEWAY_STAGE     = var.stage_name
      API_GATEWAY_URL       = module.api_gateway.api_url
      OPENAPI_SPEC_PATH     = local.openapi_spec_path
      DOCUMENTATION_VERSION = local.documentation_version
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name        = "${local.documentation_name_prefix}-generator"
      Purpose     = "API Documentation Generator"
      Environment = var.environment
    }
  )

  depends_on = [
    aws_iam_role_policy_attachment.documentation_generator_basic,
    aws_iam_role_policy.documentation_generator,
    aws_cloudwatch_log_group.documentation_generator
  ]
}

# ============================================================================
# CloudFront分发用于文档网站（可选）
# ============================================================================

# CloudFront Origin Access Identity
resource "aws_cloudfront_origin_access_identity" "api_documentation" {
  count = var.enable_api_documentation && var.enable_documentation_cdn ? 1 : 0

  comment = "OAI for ${local.documentation_name_prefix}"
}

# CloudFront分发
resource "aws_cloudfront_distribution" "api_documentation" {
  count = var.enable_api_documentation && var.enable_documentation_cdn ? 1 : 0

  origin {
    domain_name = aws_s3_bucket.api_documentation[0].bucket_regional_domain_name
    origin_id   = "${local.documentation_name_prefix}-origin"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.api_documentation[0].cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "API Documentation Distribution"
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "${local.documentation_name_prefix}-origin"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
  }

  # 配置Swagger UI的缓存行为
  ordered_cache_behavior {
    path_pattern     = "/swagger-ui/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "${local.documentation_name_prefix}-origin"

    forwarded_values {
      query_string = false
      headers      = ["Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method"]
      cookies {
        forward = "none"
      }
    }

    min_ttl                = 0
    default_ttl            = 86400
    max_ttl                = 31536000
    compress               = true
    viewer_protocol_policy = "redirect-to-https"
  }

  # 配置API规范文件的缓存行为
  ordered_cache_behavior {
    path_pattern     = "/openapi.yaml"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "${local.documentation_name_prefix}-origin"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl                = 0
    default_ttl            = 300  # 5分钟缓存，以便及时更新
    max_ttl                = 3600
    compress               = true
    viewer_protocol_policy = "redirect-to-https"
  }

  price_class = var.documentation_price_class

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/error.html"
  }

  tags = merge(
    local.common_tags,
    {
      Name        = "${local.documentation_name_prefix}-distribution"
      Purpose     = "API Documentation CDN"
      Environment = var.environment
    }
  )
}

# 更新S3存储桶策略以允许CloudFront访问
resource "aws_s3_bucket_policy" "api_documentation_cloudfront" {
  count = var.enable_api_documentation && var.enable_documentation_cdn ? 1 : 0

  bucket = aws_s3_bucket.api_documentation[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.api_documentation[0].iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.api_documentation[0].arn}/*"
      },
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.api_documentation[0].arn}/*"
      }
    ]
  })

  depends_on = [
    aws_cloudfront_origin_access_identity.api_documentation,
    aws_s3_bucket_public_access_block.api_documentation
  ]
}

# ============================================================================
# 触发器：手动调用Lambda函数来初始化文档
# ============================================================================

# 使用null_resource触发初始文档生成
resource "null_resource" "initial_documentation_generation" {
  count = var.enable_api_documentation ? 1 : 0

  # 依赖于API Gateway部署和Lambda函数
  depends_on = [
    aws_lambda_function.documentation_generator,
    aws_api_gateway_deployment.integration_deployment
  ]

  # 当API Gateway部署发生变化时重新生成文档
  triggers = {
    deployment_id = aws_api_gateway_deployment.integration_deployment.id
  }

  # 调用Lambda函数生成初始文档
  provisioner "local-exec" {
    command = <<EOF
      aws lambda invoke \
        --function-name ${aws_lambda_function.documentation_generator[0].function_name} \
        --region ${var.aws_region} \
        --payload '{}' \
        response.json || echo "Lambda invoke failed, continuing..."
      rm -f response.json
    EOF
  }
}

# ============================================================================
# 输出变量
# ============================================================================

output "api_documentation_url" {
  description = "API文档网站URL"
  value = var.enable_api_documentation ? (
    var.enable_documentation_cdn && length(aws_cloudfront_distribution.api_documentation) > 0 ?
    "https://${aws_cloudfront_distribution.api_documentation[0].domain_name}" :
    length(aws_s3_bucket.api_documentation) > 0 ?
    "https://${aws_s3_bucket.api_documentation[0].bucket_regional_domain_name}" :
    null
  ) : null
}

output "swagger_ui_url" {
  description = "Swagger UI界面URL"
  value = var.enable_api_documentation ? (
    var.enable_documentation_cdn && length(aws_cloudfront_distribution.api_documentation) > 0 ?
    "https://${aws_cloudfront_distribution.api_documentation[0].domain_name}/swagger-ui/" :
    length(aws_s3_bucket.api_documentation) > 0 ?
    "https://${aws_s3_bucket.api_documentation[0].bucket_regional_domain_name}/swagger-ui/" :
    null
  ) : null
}

output "openapi_spec_url" {
  description = "OpenAPI规范文件URL"
  value = var.enable_api_documentation ? (
    var.enable_documentation_cdn && length(aws_cloudfront_distribution.api_documentation) > 0 ?
    "https://${aws_cloudfront_distribution.api_documentation[0].domain_name}/openapi.yaml" :
    length(aws_s3_bucket.api_documentation) > 0 ?
    "https://${aws_s3_bucket.api_documentation[0].bucket_regional_domain_name}/openapi.yaml" :
    null
  ) : null
}

output "postman_collection_url" {
  description = "Postman集合下载URL"
  value = var.enable_api_documentation ? (
    var.enable_documentation_cdn && length(aws_cloudfront_distribution.api_documentation) > 0 ?
    "https://${aws_cloudfront_distribution.api_documentation[0].domain_name}/postman-collection.json" :
    length(aws_s3_bucket.api_documentation) > 0 ?
    "https://${aws_s3_bucket.api_documentation[0].bucket_regional_domain_name}/postman-collection.json" :
    null
  ) : null
}

output "documentation_s3_bucket" {
  description = "文档存储的S3存储桶名称"
  value       = var.enable_api_documentation && length(aws_s3_bucket.api_documentation) > 0 ? aws_s3_bucket.api_documentation[0].bucket : null
}

output "documentation_lambda_function" {
  description = "文档生成Lambda函数名称"
  value       = var.enable_api_documentation && length(aws_lambda_function.documentation_generator) > 0 ? aws_lambda_function.documentation_generator[0].function_name : null
}