#!/bin/bash

BACKUP_DIR="$HOME/Desktop/ppt-system-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "开始备份关键数据..."

# 1. 备份Lambda函数代码
echo "备份Lambda函数代码..."
aws lambda get-function --function-name ai-ppt-generate-dev --region us-east-1 \
  --query 'Code.Location' --output text > "$BACKUP_DIR/lambda-code-url.txt"

# 2. 备份API Gateway配置
echo "备份API Gateway配置..."
aws apigateway get-rest-api --rest-api-id n1s8cxndac --region us-east-1 > "$BACKUP_DIR/api-gateway.json"

# 3. 备份DynamoDB表数据
echo "备份DynamoDB表数据..."
aws dynamodb scan --table-name ai-ppt-presentations --region us-east-1 > "$BACKUP_DIR/dynamodb-presentations.json"

# 4. 备份S3存储桶列表
echo "备份S3对象列表..."
aws s3 ls s3://ai-ppt-presentations-dev-375004070918/ --recursive > "$BACKUP_DIR/s3-objects.txt"

# 5. 备份当前工作的Lambda部署包
echo "备份Lambda部署包..."
cp lambda-deployment.zip "$BACKUP_DIR/"
cp lambda_function.zip "$BACKUP_DIR/"

# 6. 备份Terraform状态
echo "备份Terraform状态..."
cd ../infrastructure
terraform state pull > "$BACKUP_DIR/terraform.tfstate"
cp terraform.tfvars "$BACKUP_DIR/" 2>/dev/null || true

echo "备份完成: $BACKUP_DIR"
ls -la "$BACKUP_DIR"
