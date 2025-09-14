# AI PPT Assistant 部署流程指南

## 概述
本文档详细记录了 AI PPT Assistant 项目的完整部署流程，包括基础设施部署、Lambda函数配置、权限设置等关键步骤。

## 部署架构
```
┌─────────────────────────────────────────────────────────┐
│                     用户请求                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
         ┌──────────────────────┐
         │   API Gateway        │
         └──────────┬───────────┘
                    │
     ┌──────────────┴──────────────┬────────────────┬─────────────────┐
     ▼                              ▼                ▼                 ▼
┌─────────────┐         ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ Generate    │         │ Status      │   │ Download    │   │ API Handler │
│ Lambda      │         │ Lambda      │   │ Lambda      │   │ Lambda      │
└──────┬──────┘         └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                        │                  │                  │
       ├────────────────────────┴──────────────────┴──────────────────┤
       │                                                               │
       ▼                                                               ▼
┌─────────────┐                                           ┌──────────────────┐
│  DynamoDB   │                                           │   S3 Bucket      │
│  (状态存储)  │                                           │  (PPT文件存储)    │
└─────────────┘                                           └──────────────────┘
       │                                                               │
       └───────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Amazon Bedrock     │
                    │  (Nova Canvas)      │
                    └─────────────────────┘
```

## 前置条件

### 1. 环境要求
- AWS CLI 已配置 (`aws configure`)
- Terraform >= 1.0
- Python 3.12
- Node.js >= 18
- Git

### 2. AWS 账户准备
```bash
# 验证AWS配置
aws sts get-caller-identity

# 确认当前区域
echo $AWS_REGION  # 应该是 us-east-1
```

### 3. Bedrock 模型访问
```bash
# 请求 Nova Canvas 模型访问权限
aws bedrock request-model-access \
  --model-id amazon.nova-canvas-v1:0 \
  --region us-east-1
```

## 部署流程

### 第一步：准备项目结构
```bash
# 1. 进入项目目录
cd /Users/umatoratatsu/Documents/AWS/AWS-Handson/ABA/AMAZON-BEDROCK-AGENTS

# 2. 确认目录结构
tree -L 2 -d
# 应该包含:
# ├── infrastructure/  (Terraform配置)
# ├── lambdas/        (Lambda函数代码)
# ├── frontend/       (前端代码)
# └── docs/          (文档)
```

### 第二步：创建 Lambda 层
```bash
# 1. 进入 lambdas 目录
cd lambdas

# 2. 创建依赖层目录
mkdir -p layers/python

# 3. 安装依赖
pip install -t layers/python \
  boto3 \
  botocore \
  pillow \
  python-pptx \
  requests \
  pydantic

# 4. 打包层
cd layers
zip -r ../ai-ppt-dependencies.zip python/
cd ..

# 5. 验证包大小
ls -lh ai-ppt-dependencies.zip
# 应该在 10-50MB 之间
```

### 第三步：准备 Lambda 函数代码
```bash
# 1. 打包各个Lambda函数
cd lambdas

# 生成PPT函数
zip -j generate_ppt.zip \
  generate_ppt.py \
  image_processing_service.py \
  image_config.py \
  exceptions/*.py \
  services/*.py

# API处理函数
zip -j api_handler.zip \
  api_handler.py \
  lambda_handler.py

# 状态检查函数
zip -j status_check.zip \
  status_check.py

# 下载函数
zip -j download_ppt.zip \
  download_ppt.py

# 2. 验证包
ls -lh *.zip
```

### 第四步：初始化 Terraform
```bash
# 1. 进入 infrastructure 目录
cd ../infrastructure

# 2. 初始化 Terraform
terraform init

# 3. 创建或选择工作空间
terraform workspace new dev || terraform workspace select dev

# 4. 验证配置
terraform validate
```

### 第五步：配置 Terraform 变量
```bash
# 1. 创建 terraform.tfvars
cat > terraform.tfvars <<EOF
environment = "dev"
project_name = "ai-ppt-assistant"
aws_region = "us-east-1"

# Lambda 配置
lambda_timeout = 300
lambda_memory_size = 3008

# 监控配置
enable_monitoring = true
enable_xray_tracing = false
alert_email = ""

# API 配置
api_throttle_burst_limit = 100
api_throttle_rate_limit = 50
EOF
```

### 第六步：执行 Terraform 部署
```bash
# 1. 查看部署计划
terraform plan

# 2. 执行部署
terraform apply -auto-approve

# 3. 保存输出
terraform output -json > deployment-output.json
```

### 第七步：部署 Lambda 函数代码
```bash
# 1. 获取函数名称
GENERATE_FUNC="ai-ppt-generate-dev"
API_FUNC="ai-ppt-api-handler-dev"
STATUS_FUNC="ai-ppt-status-dev"
DOWNLOAD_FUNC="ai-ppt-download-dev"

# 2. 更新函数代码
cd ../lambdas

aws lambda update-function-code \
  --function-name $GENERATE_FUNC \
  --zip-file fileb://generate_ppt.zip

aws lambda update-function-code \
  --function-name $API_FUNC \
  --zip-file fileb://api_handler.zip

aws lambda update-function-code \
  --function-name $STATUS_FUNC \
  --zip-file fileb://status_check.zip

aws lambda update-function-code \
  --function-name $DOWNLOAD_FUNC \
  --zip-file fileb://download_ppt.zip
```

### 第八步：配置环境变量
```bash
# 1. 获取资源信息
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="ai-ppt-presentations-dev-${ACCOUNT_ID}"

# 2. 更新Lambda环境变量
for FUNC in $GENERATE_FUNC $API_FUNC $STATUS_FUNC $DOWNLOAD_FUNC; do
  aws lambda update-function-configuration \
    --function-name $FUNC \
    --environment Variables="{
      ENVIRONMENT=dev,
      S3_BUCKET=$S3_BUCKET,
      DYNAMODB_TABLE=ai-ppt-presentations,
      NOVA_MODEL_ID=amazon.nova-canvas-v1:0,
      STABILITY_MODEL_ID=stability.stable-diffusion-xl-v1,
      TITAN_MODEL_ID=amazon.titan-image-generator-v2:0,
      LOG_LEVEL=INFO
    }"
done
```

### 第九步：配置 IAM 权限
```bash
# 1. 添加 Bedrock 权限
aws iam attach-role-policy \
  --role-name ai-ppt-lambda-role-dev \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# 2. 验证权限
aws iam list-attached-role-policies \
  --role-name ai-ppt-lambda-role-dev
```

### 第十步：创建必要的 S3 存储桶
```bash
# 1. 创建缓存桶
aws s3api create-bucket \
  --bucket ai-ppt-image-cache-dev \
  --region us-east-1

# 2. 配置生命周期策略
aws s3api put-bucket-lifecycle-configuration \
  --bucket ai-ppt-image-cache-dev \
  --lifecycle-configuration file:///tmp/lifecycle.json

# 3. 验证存储桶
aws s3api list-buckets --query "Buckets[?contains(Name, 'ai-ppt')].[Name]" --output table
```

## 验证部署

### 1. 基础设施验证
```bash
# Lambda 函数
aws lambda list-functions \
  --query "Functions[?contains(FunctionName, 'ai-ppt')].[FunctionName,State]" \
  --output table

# DynamoDB 表
aws dynamodb describe-table \
  --table-name ai-ppt-presentations \
  --query "Table.TableStatus"

# API Gateway
aws apigatewayv2 get-apis \
  --query "Items[?contains(Name, 'ai-ppt')].[Name,ApiEndpoint]" \
  --output table
```

### 2. 功能测试
```bash
# 测试 Lambda 函数
aws lambda invoke \
  --function-name ai-ppt-generate-dev \
  --payload '{"action":"test"}' \
  /tmp/test_response.json

# 查看响应
cat /tmp/test_response.json | jq

# 测试图片生成
aws lambda invoke \
  --function-name ai-ppt-generate-dev \
  --payload '{
    "action": "generate_image",
    "slide_content": {
      "title": "测试图片",
      "content": ["AI技术", "机器学习", "深度学习"]
    }
  }' \
  /tmp/image_response.json

# 查看响应
cat /tmp/image_response.json | jq
```

### 3. 运行完整测试脚本
```bash
cd /Users/umatoratatsu/Documents/AWS/AWS-Handson/ABA/AMAZON-BEDROCK-AGENTS
python test_lambda_deployment.py
```

## 故障排除

### 常见问题及解决方案

#### 1. Terraform 资源冲突
```bash
# 清理并重新部署
terraform destroy -auto-approve
terraform apply -auto-approve
```

#### 2. Lambda 函数超时
```bash
# 增加超时时间
aws lambda update-function-configuration \
  --function-name ai-ppt-generate-dev \
  --timeout 900
```

#### 3. Bedrock 权限问题
```bash
# 重新附加权限
aws iam detach-role-policy \
  --role-name ai-ppt-lambda-role-dev \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam attach-role-policy \
  --role-name ai-ppt-lambda-role-dev \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

#### 4. S3 存储桶不存在
```bash
# 创建缺失的存储桶
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3api create-bucket \
  --bucket ai-ppt-presentations-dev-${ACCOUNT_ID} \
  --region us-east-1
```

## 清理资源

当需要清理环境时：
```bash
cd infrastructure

# 使用 Terraform 清理
terraform destroy -auto-approve

# 或使用清理脚本
../scripts/cleanup-environment.sh dev
```

## 监控和日志

### CloudWatch 日志
```bash
# 查看最新日志
aws logs tail /aws/lambda/ai-ppt-generate-dev --follow

# 搜索错误
aws logs filter-log-events \
  --log-group-name /aws/lambda/ai-ppt-generate-dev \
  --filter-pattern "ERROR"
```

### CloudWatch 指标
```bash
# 查看 Lambda 指标
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=ai-ppt-generate-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

## 部署检查清单

- [ ] AWS CLI 已配置
- [ ] Terraform 已安装
- [ ] Bedrock 模型访问已授权
- [ ] Lambda 层已创建
- [ ] Lambda 函数代码已打包
- [ ] Terraform 初始化完成
- [ ] Terraform 部署成功
- [ ] Lambda 函数已更新
- [ ] 环境变量已配置
- [ ] IAM 权限已设置
- [ ] S3 存储桶已创建
- [ ] 基础测试通过
- [ ] 图片生成测试通过

## 相关资源

- [Terraform 文档](https://www.terraform.io/docs)
- [AWS Lambda 文档](https://docs.aws.amazon.com/lambda/)
- [Amazon Bedrock 文档](https://docs.aws.amazon.com/bedrock/)
- [项目 README](../README.md)

---
最后更新: 2025-01-14
版本: 2.0