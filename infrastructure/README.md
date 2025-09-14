# AI PPT Assistant Infrastructure

## 系统架构概述

AI PPT Assistant 是一个基于 AWS 的无服务器应用，使用 Amazon Bedrock 生成专业的演示文稿。系统采用事件驱动架构，通过 Lambda 函数处理各种操作，并通过 API Gateway 提供 RESTful 接口。

## 最新更新（2024年9月14日）

### 🔧 重要修复
- **Lambda Handler 统一**: 所有 Lambda 函数的 handler 现已统一为 `lambda_handler`
- **CORS 配置完善**: API Gateway 完整支持跨域请求
- **性能优化**: 实施了内存配置、并发控制和缓存策略
- **权限修复**: 解决了所有 IAM 权限问题

## 资源清单

### 核心服务
- **S3 Buckets**:
  - PPT 存储桶：存储生成的演示文稿
  - 图片存储桶：存储生成的图片资源

- **Lambda Functions**:
  - `generate_ppt`: 处理PPT生成请求（异步，15分钟超时）
  - `status_check`: 检查生成状态（同步，30秒超时）
  - `download_ppt`: 提供下载链接（同步，30秒超时）
  - `api_handler`: 统一API路由处理（3分钟超时）
  - `image_processing`: 图片生成和处理（5分钟超时）

- **API Gateway**: RESTful API 端点，完整 CORS 支持
- **CloudWatch**: 监控、日志和告警
- **IAM Roles**: 细粒度权限控制

## 部署步骤

### 1. 前置准备

```bash
# 确保已安装以下工具
# - Terraform >= 1.0
# - AWS CLI 已配置
# - Python 3.9+

# 克隆仓库
git clone <repository-url>
cd AMAZON-BEDROCK-AGENTS/infrastructure
```

### 2. 初始化 Terraform

```bash
terraform init
```

### 3. 配置环境变量

```bash
# 复制示例配置
cp terraform.tfvars.example terraform.tfvars

# 编辑配置文件
vim terraform.tfvars
```

**重要配置项**：
```hcl
aws_region     = "us-west-2"      # AWS 区域
environment    = "production"      # 环境名称
project_name   = "ai-ppt"         # 项目名称
lambda_timeout = 900               # Lambda 超时时间（秒）
lambda_memory  = 3008              # Lambda 内存（MB）
```

### 4. 准备 Lambda 部署包

```bash
# 使用部署脚本创建 Lambda 包
./deploy_ai_ppt.sh

# 或手动创建
cd ../lambdas
zip -r lambda-deployment.zip *.py services/ utils/ controllers/
cd ../infrastructure
```

### 5. 验证配置

```bash
# 验证 Terraform 语法
terraform validate

# 查看执行计划
terraform plan -out=tfplan

# 检查将要创建的资源
terraform show tfplan
```

### 6. 部署基础设施

```bash
# 应用配置
terraform apply tfplan

# 或直接部署（需要确认）
terraform apply
```

### 7. 验证部署

```bash
# 获取 API Gateway URL
terraform output api_gateway_url

# 测试 API 健康检查
curl -X GET "$(terraform output -raw api_gateway_url)/health"
```

## API 端点详细说明

### 基础 URL
```
https://{api-id}.execute-api.{region}.amazonaws.com/prod
```

### 1. 生成 PPT
**端点**: `POST /generate`

**请求头**:
```http
Content-Type: application/json
Access-Control-Allow-Origin: *
```

**请求体**:
```json
{
  "topic": "AI技术在教育领域的应用",
  "pages": 10,
  "style": "professional",
  "language": "zh-CN",
  "template": "modern",
  "include_images": true
}
```

**响应**:
```json
{
  "statusCode": 200,
  "body": {
    "presentation_id": "ppt-123456-789abc",
    "status": "processing",
    "message": "PPT generation started",
    "estimated_time": 120
  }
}
```

### 2. 检查状态
**端点**: `GET /status/{presentation_id}`

**响应示例**:
```json
{
  "statusCode": 200,
  "body": {
    "presentation_id": "ppt-123456-789abc",
    "status": "completed",
    "progress": 100,
    "current_step": "finalized",
    "slides_completed": 10,
    "total_slides": 10,
    "download_url": "https://...",
    "expires_at": "2024-09-15T12:00:00Z"
  }
}
```

**状态值**:
- `pending`: 等待处理
- `processing`: 正在生成
- `completed`: 生成完成
- `failed`: 生成失败
- `expired`: 已过期

### 3. 下载 PPT
**端点**: `GET /download/{presentation_id}`

**响应**:
- 成功：返回预签名的 S3 URL（302 重定向）
- 失败：返回错误信息

```json
{
  "statusCode": 200,
  "body": {
    "download_url": "https://s3.amazonaws.com/...",
    "expires_in": 3600,
    "file_size": 2048576,
    "filename": "presentation_20240914.pptx"
  }
}
```

### 4. 健康检查
**端点**: `GET /health`

**响应**:
```json
{
  "statusCode": 200,
  "body": {
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2024-09-14T10:00:00Z",
    "services": {
      "bedrock": "operational",
      "s3": "operational",
      "lambda": "operational"
    }
  }
}
```

### CORS 配置
所有端点都支持 CORS，允许的方法：
- `GET, POST, OPTIONS`
- 允许的源：`*`（生产环境应配置具体域名）
- 允许的头：`Content-Type, X-Amz-Date, Authorization, X-Api-Key`

## 环境变量配置

### Lambda 函数环境变量

#### 通用配置
```bash
AWS_REGION="us-west-2"                    # AWS 区域
ENVIRONMENT="production"                  # 环境标识
LOG_LEVEL="INFO"                          # 日志级别
PYTHONPATH="/var/task:/opt/python"        # Python 路径
```

#### S3 配置
```bash
S3_BUCKET="ai-ppt-storage-{account-id}"   # PPT 存储桶
IMAGE_BUCKET="ai-ppt-images-{account-id}" # 图片存储桶
S3_REGION="us-west-2"                     # S3 区域
PRESIGNED_URL_EXPIRY="3600"              # URL 过期时间（秒）
```

#### Bedrock 配置
```bash
BEDROCK_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0"  # 模型 ID
BEDROCK_ENDPOINT="bedrock-runtime.us-west-2.amazonaws.com"   # 端点
MAX_TOKENS="4096"                                            # 最大令牌数
TEMPERATURE="0.7"                                           # 温度参数
```

#### 性能配置
```bash
LAMBDA_MEMORY_SIZE="3008"                 # 内存大小（MB）
LAMBDA_TIMEOUT="900"                      # 超时时间（秒）
RESERVED_CONCURRENT_EXECUTIONS="10"       # 预留并发数
MAX_RETRIES="3"                           # 最大重试次数
ENABLE_XRAY="true"                       # X-Ray 追踪
```

#### 图片处理配置
```bash
IMAGE_MODEL_ID="stability.stable-diffusion-xl-v1"  # 图片模型
IMAGE_WIDTH="1024"                                  # 图片宽度
IMAGE_HEIGHT="768"                                  # 图片高度
IMAGE_QUALITY="high"                                # 图片质量
MAX_IMAGE_SIZE="10485760"                          # 最大图片大小（10MB）
```

## 故障排查指南

### 常见问题及解决方案

#### 1. Lambda Handler 错误
**问题**: "Unable to import module 'lambda_function'"

**解决方案**:
```bash
# 确保 handler 配置正确
# main.tf 中应为：
handler = "lambda_function.lambda_handler"  # 不是 "handler"

# 验证文件结构
cd lambdas/
ls -la lambda_function.py  # 确保文件存在
grep "def lambda_handler" lambda_function.py  # 确保函数名正确
```

#### 2. CORS 错误
**问题**: "Access-Control-Allow-Origin" 头缺失

**解决方案**:
```python
# Lambda 响应必须包含 CORS 头
return {
    'statusCode': 200,
    'headers': {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    },
    'body': json.dumps(response_data)
}
```

#### 3. 权限错误
**问题**: Lambda 无法访问 S3 或 Bedrock

**解决方案**:
```bash
# 检查 IAM 角色权限
aws iam get-role-policy --role-name ai-ppt-lambda-role --policy-name ai-ppt-lambda-policy

# 确保包含必要权限
- s3:GetObject, s3:PutObject
- bedrock:InvokeModel
- logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents
```

#### 4. 超时错误
**问题**: Lambda 函数超时

**解决方案**:
```hcl
# 在 terraform.tfvars 中调整
lambda_timeout = 900  # 最大 15 分钟
lambda_memory = 3008  # 增加内存也会增加 CPU

# 对于长时间运行的任务，考虑使用 Step Functions
```

#### 5. S3 访问错误
**问题**: 403 Forbidden 访问 S3

**解决方案**:
```bash
# 检查桶策略
aws s3api get-bucket-policy --bucket ai-ppt-storage-{account-id}

# 确保 Lambda 执行角色有权限
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::{account-id}:role/ai-ppt-lambda-role \
  --action-names s3:GetObject s3:PutObject \
  --resource-arns arn:aws:s3:::ai-ppt-storage-{account-id}/*
```

### 日志查看

#### CloudWatch Logs
```bash
# 查看 Lambda 日志
aws logs tail /aws/lambda/ai-ppt-generate --follow
aws logs tail /aws/lambda/ai-ppt-status --follow
aws logs tail /aws/lambda/ai-ppt-download --follow

# 搜索错误
aws logs filter-log-events \
  --log-group-name /aws/lambda/ai-ppt-generate \
  --filter-pattern "ERROR"
```

#### X-Ray 追踪
```bash
# 获取追踪信息
aws xray get-trace-summaries \
  --time-range-type LastHour \
  --query 'TraceSummaries[?ServiceNames[?contains(@, `ai-ppt`)]]'
```

### 性能监控

#### CloudWatch Metrics
```bash
# 查看 Lambda 指标
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=ai-ppt-generate \
  --start-time 2024-09-14T00:00:00Z \
  --end-time 2024-09-14T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum
```

#### 性能优化建议

1. **冷启动优化**
   - 使用预留并发：`reserved_concurrent_executions = 5`
   - 减少依赖包大小
   - 使用 Lambda Layers 共享代码

2. **内存优化**
   - 监控实际使用：`aws lambda get-function-configuration`
   - 调整内存大小：3008MB 提供 2 vCPU

3. **并发优化**
   - 设置并发限制避免限流
   - 使用 SQS 进行异步处理

## 最佳实践

### 1. 部署流程
```bash
# 始终按此顺序执行
1. terraform plan -out=tfplan
2. terraform show tfplan  # 仔细检查
3. terraform apply tfplan
4. ./performance_test.sh  # 验证性能
```

### 2. 代码组织
```
lambdas/
├── lambda_function.py     # 主入口，统一 handler
├── api_handler.py         # API 路由处理
├── services/              # 业务逻辑
│   ├── ppt_service.py
│   ├── image_service.py
│   └── bedrock_service.py
└── utils/                 # 工具函数
    ├── logger.py
    └── validator.py
```

### 3. 错误处理
```python
def lambda_handler(event, context):
    try:
        # 业务逻辑
        result = process_request(event)
        return success_response(result)
    except ValidationError as e:
        return error_response(400, str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return error_response(500, "Internal server error")
```

### 4. 监控告警
```hcl
# 设置关键指标告警
- Lambda 错误率 > 1%
- Lambda 持续时间 > 10秒（P95）
- API Gateway 4xx > 10%
- API Gateway 5xx > 1%
```

## 安全最佳实践

### 1. IAM 最小权限原则
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:GetObject",
      "s3:PutObject"
    ],
    "Resource": "arn:aws:s3:::ai-ppt-storage-*/*"
  }]
}
```

### 2. 环境变量加密
```bash
# 使用 AWS Systems Manager Parameter Store
aws ssm put-parameter \
  --name "/ai-ppt/prod/api-key" \
  --value "secret-key" \
  --type SecureString
```

### 3. API 限流
```hcl
# API Gateway 限流配置
throttle_burst_limit = 100
throttle_rate_limit = 50
```

## 清理资源

### 安全删除
```bash
# 1. 备份重要数据
./backup_critical_data.sh

# 2. 删除 S3 对象
aws s3 rm s3://ai-ppt-storage-{account-id} --recursive
aws s3 rm s3://ai-ppt-images-{account-id} --recursive

# 3. 销毁基础设施
terraform destroy -auto-approve

# 4. 验证清理
aws s3 ls | grep ai-ppt  # 应该为空
```

## 维护和支持

### 定期维护
- 每周检查 CloudWatch 日志
- 每月更新 Lambda 层依赖
- 每季度进行性能评估
- 每年进行安全审计

### 联系方式
- 技术支持：[团队邮箱]
- 紧急联系：[值班电话]
- 文档更新：[Wiki 链接]

## 更新历史

### 2024-09-14
- 修复 Lambda handler 命名问题
- 完善 CORS 配置
- 优化性能配置
- 添加详细故障排查指南

### 2024-09-13
- 初始版本发布
- 基础架构搭建