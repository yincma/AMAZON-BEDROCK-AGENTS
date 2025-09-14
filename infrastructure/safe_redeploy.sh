#!/bin/bash
set -e

echo "========================================="
echo "安全重新部署 AI PPT Assistant"
echo "========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 预检查
echo -e "${YELLOW}步骤1: 预检查${NC}"
cd ../infrastructure

# 检查是否有未提交的更改
if [[ -n $(git status -s) ]]; then
    echo -e "${RED}警告: 有未提交的Git更改${NC}"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 2. 备份S3数据（可选）
echo -e "${YELLOW}步骤2: 是否需要备份S3数据?${NC}"
read -p "备份S3数据会花费时间但更安全 (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    BACKUP_BUCKET="ai-ppt-backup-$(date +%Y%m%d-%H%M%S)"
    echo "创建备份存储桶: $BACKUP_BUCKET"
    aws s3 mb "s3://$BACKUP_BUCKET" --region us-east-1
    aws s3 sync s3://ai-ppt-presentations-dev-375004070918/ "s3://$BACKUP_BUCKET/" --region us-east-1
    echo -e "${GREEN}S3数据已备份到: $BACKUP_BUCKET${NC}"
fi

# 3. 保存Lambda部署包
echo -e "${YELLOW}步骤3: 准备Lambda部署包${NC}"
cd ../lambdas
if [ -f "lambda-deployment.zip" ]; then
    cp lambda-deployment.zip /tmp/lambda-deployment-backup.zip
    echo -e "${GREEN}Lambda部署包已备份${NC}"
else
    echo -e "${YELLOW}创建新的Lambda部署包...${NC}"
    ../create_stable_deployment.sh
fi

# 4. 执行Terraform destroy（保留S3）
echo -e "${YELLOW}步骤4: 销毁基础设施（保留S3数据）${NC}"
cd ../infrastructure

# 先移除S3存储桶的Terraform管理
terraform state rm aws_s3_bucket.presentations || true
terraform state rm aws_s3_bucket.image_cache || true

# 执行销毁
terraform destroy -auto-approve

# 5. 重新创建基础设施
echo -e "${YELLOW}步骤5: 重新创建基础设施${NC}"
terraform apply -auto-approve

# 6. 导入现有S3存储桶
echo -e "${YELLOW}步骤6: 导入现有S3存储桶${NC}"
terraform import aws_s3_bucket.presentations ai-ppt-presentations-dev-375004070918
terraform import aws_s3_bucket.image_cache ai-ppt-assistant-image-cache-dev-375004070918

# 7. 部署Lambda函数代码
echo -e "${YELLOW}步骤7: 部署Lambda函数代码${NC}"
cd ../lambdas
if [ -f "/tmp/lambda-deployment-backup.zip" ]; then
    cp /tmp/lambda-deployment-backup.zip lambda-deployment.zip
fi

aws lambda update-function-code \
    --function-name ai-ppt-generate-dev \
    --zip-file fileb://lambda-deployment.zip \
    --region us-east-1

# 8. 验证部署
echo -e "${YELLOW}步骤8: 验证部署${NC}"
sleep 5
curl -X POST 'https://n1s8cxndac.execute-api.us-east-1.amazonaws.com/dev/generate' \
    -H 'Content-Type: application/json' \
    -d '{"topic":"部署测试","page_count":3,"style":"professional"}' \
    --max-time 60 -s | jq '.'

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}重新部署完成！${NC}"
echo -e "${GREEN}=========================================${NC}"
