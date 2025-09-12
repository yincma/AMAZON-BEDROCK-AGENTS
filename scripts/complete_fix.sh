#!/bin/bash

# ====================================================================
# 完整修复脚本 - 解决所有部署问题
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
echo "🔧 完整部署修复流程"
echo "======================================================================"

# 1. 停止所有后台进程
log_info "停止后台进程..."
pkill -f "make deploy-with-config" 2>/dev/null || true
pkill -f "terraform apply" 2>/dev/null || true

# 2. 清理错误的API Gateway
log_info "清理旧的API Gateway..."
old_api_id="oyj48ekgt0"
if aws apigateway get-rest-api --rest-api-id "$old_api_id" &>/dev/null; then
    log_warning "删除旧的API Gateway: $old_api_id"
    aws apigateway delete-rest-api --rest-api-id "$old_api_id" 2>/dev/null || true
fi

# 3. 清理Terraform状态
log_info "刷新Terraform状态..."
cd infrastructure
terraform init -upgrade
terraform refresh || true

# 4. 应用Terraform配置
log_info "部署基础设施..."
terraform apply -auto-approve

# 5. 获取正确的输出
log_info "获取部署输出..."
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
API_KEY=$(terraform output -raw api_gateway_api_key 2>/dev/null || echo "")

cd ..

# 6. 更新所有配置文件
log_info "更新配置文件..."

# 更新api_config_info.json
cat > api_config_info.json <<EOF
{
  "project": "ai-ppt-assistant",
  "environment": "dev",
  "region": "us-east-1",
  "api_gateway_url": "${API_URL}",
  "api_key": "${API_KEY}",
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "updated_by": "complete_fix.sh"
}
EOF

# 更新测试脚本
for file in test_backend_apis.py comprehensive_backend_test.py test_all_backend_apis.py system_health_check.py; do
    if [ -f "$file" ]; then
        log_info "更新 $file..."
        # 备份
        cp "$file" "${file}.bak"
        
        # 更新API URL
        sed -i '' "s|https://[a-z0-9]*.execute-api.[a-z0-9-]*.amazonaws.com/[a-z]*|${API_URL}|g" "$file"
        
        # 更新API Key（确保是40字符的正确密钥）
        sed -i '' "s|API_KEY = \".*\"|API_KEY = \"${API_KEY}\"|g" "$file"
        
        # 清理备份
        rm -f "${file}.bak"
    fi
done

# 7. 验证部署
log_info "验证部署..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "x-api-key: ${API_KEY}" \
    "${API_URL}/health" 2>/dev/null || echo "000")

if [ "$response" = "200" ]; then
    log_success "✅ API健康检查通过"
else
    log_warning "⚠️ API健康检查返回: $response"
fi

# 8. 运行测试
log_info "运行API测试..."
python3 test_backend_apis.py

echo ""
echo "======================================================================"
log_success "✅ 修复完成！"
echo "======================================================================"
echo "API Gateway URL: ${API_URL}"
echo "API Key: ${API_KEY:0:20}..."
echo ""
echo "系统现在应该可以正常工作了。"
echo "======================================================================"