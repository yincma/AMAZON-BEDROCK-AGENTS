#!/bin/bash

# ====================================================================
# 简单直接的修复脚本 - 解决DynamoDB表冲突
# ====================================================================

set -euo pipefail

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "======================================================================"
echo "🔧 简单修复流程 - 直接处理资源冲突"
echo "======================================================================"

# 1. 删除现有的DynamoDB表
log_info "删除现有的DynamoDB表..."
for table in "ai-ppt-assistant-dev-sessions" "ai-ppt-assistant-dev-tasks" "ai-ppt-assistant-dev-checkpoints"; do
    if aws dynamodb describe-table --table-name "$table" &>/dev/null; then
        log_warning "删除表: $table"
        aws dynamodb delete-table --table-name "$table" --region us-east-1 || true
        
        # 等待表删除
        log_info "等待表 $table 删除..."
        aws dynamodb wait table-not-exists --table-name "$table" --region us-east-1 || true
    else
        log_info "表 $table 不存在"
    fi
done

# 2. 进入infrastructure目录
cd infrastructure

# 3. 初始化和刷新Terraform
log_info "初始化Terraform..."
terraform init -upgrade

log_info "刷新Terraform状态..."
terraform refresh

# 4. 应用Terraform配置
log_info "应用Terraform配置..."
terraform apply -auto-approve

# 5. 获取输出
log_info "获取部署输出..."
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
API_KEY=$(terraform output -raw api_gateway_api_key 2>/dev/null || echo "")

if [ -z "$API_URL" ] || [ -z "$API_KEY" ]; then
    log_error "无法获取API配置"
    exit 1
fi

cd ..

# 6. 更新配置文件
log_info "更新api_config_info.json..."
cat > api_config_info.json <<EOF
{
  "project": "ai-ppt-assistant",
  "environment": "dev",
  "region": "us-east-1",
  "api_gateway_url": "${API_URL}",
  "api_key": "${API_KEY}",
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "updated_by": "simple_fix.sh"
}
EOF

# 7. 更新test_backend_apis.py
if [ -f "test_backend_apis.py" ]; then
    log_info "更新test_backend_apis.py..."
    
    # 创建备份
    cp test_backend_apis.py test_backend_apis.py.bak
    
    # 使用Python更新文件
    python3 -c "
import re

with open('test_backend_apis.py', 'r') as f:
    content = f.read()

# 更新API_BASE_URL
content = re.sub(r'API_BASE_URL = \".*\"', 'API_BASE_URL = \"${API_URL}\"', content)

# 更新API_KEY
content = re.sub(r'API_KEY = \".*\"', 'API_KEY = \"${API_KEY}\"', content)

with open('test_backend_apis.py', 'w') as f:
    f.write(content)

print('文件更新成功')
"
fi

# 8. 验证部署
log_info "验证API健康状态..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "x-api-key: ${API_KEY}" \
    "${API_URL}/health" 2>/dev/null || echo "000")

if [ "$response" = "200" ]; then
    log_success "✅ API健康检查通过"
else
    log_warning "⚠️ API健康检查返回: $response"
    log_info "等待API Gateway完全部署..."
    sleep 10
    
    # 重试
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "x-api-key: ${API_KEY}" \
        "${API_URL}/health" 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ]; then
        log_success "✅ API健康检查通过（第二次尝试）"
    else
        log_error "❌ API健康检查失败: $response"
    fi
fi

# 9. 运行测试
log_info "运行API测试..."
python3 test_backend_apis.py || log_warning "测试未通过，请检查日志"

echo ""
echo "======================================================================"
log_success "✅ 修复流程完成！"
echo "======================================================================"
echo "API Gateway URL: ${API_URL}"
echo "API Key: ${API_KEY:0:20}..."
echo ""
echo "如果还有问题，请检查："
echo "1. AWS Console中的API Gateway是否正确部署"
echo "2. Lambda函数是否都正常运行"
echo "3. IAM权限是否正确配置"
echo "======================================================================"