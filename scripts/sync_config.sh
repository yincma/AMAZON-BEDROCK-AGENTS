#!/bin/bash

# ====================================================================
# 配置同步脚本 - 自动从Terraform输出更新所有配置
# 确保测试脚本和配置文件始终使用正确的值
# ====================================================================

set -euo pipefail

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 切换到项目根目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

log_info "开始同步配置..."

# 检查Terraform输出
cd infrastructure

if ! terraform output &>/dev/null; then
    log_error "无法获取Terraform输出，请先运行部署"
    exit 1
fi

# 获取Terraform输出
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
API_KEY=$(terraform output -raw api_gateway_api_key 2>/dev/null || echo "")

if [ -z "$API_URL" ] || [ -z "$API_KEY" ]; then
    log_error "无法获取API配置，请检查Terraform部署"
    exit 1
fi

cd ..

# 验证API密钥长度
KEY_LENGTH=${#API_KEY}
if [ $KEY_LENGTH -ne 40 ]; then
    log_warning "API密钥长度异常: $KEY_LENGTH 字符（预期40字符）"
fi

# 更新api_config_info.json
log_info "更新 api_config_info.json..."
cat > api_config_info.json <<EOF
{
  "project": "ai-ppt-assistant",
  "environment": "dev",
  "region": "us-east-1",
  "api_gateway_url": "${API_URL}",
  "api_key": "${API_KEY}",
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "updated_by": "sync_config.sh"
}
EOF

# 更新test_backend_apis.py
if [ -f "test_backend_apis.py" ]; then
    log_info "更新 test_backend_apis.py..."
    
    # 使用临时文件避免sed的平台差异
    cp test_backend_apis.py test_backend_apis.py.bak
    
    # 更新API URL
    sed "s|API_BASE_URL = .*|API_BASE_URL = \"${API_URL}\"|" test_backend_apis.py.bak > test_backend_apis.py.tmp
    
    # 更新API Key
    sed "s|API_KEY = .*|API_KEY = \"${API_KEY}\"|" test_backend_apis.py.tmp > test_backend_apis.py
    
    # 清理临时文件
    rm -f test_backend_apis.py.tmp test_backend_apis.py.bak
fi

# 更新其他测试文件（如果存在）
for test_file in comprehensive_backend_test.py test_all_backend_apis.py system_health_check.py; do
    if [ -f "$test_file" ]; then
        log_info "更新 $test_file..."
        
        # 创建备份
        cp "$test_file" "${test_file}.bak"
        
        # 更新配置
        sed "s|https://[a-z0-9]*.execute-api.[a-z0-9-]*.amazonaws.com/[a-z]*|${API_URL}|g" "${test_file}.bak" > "${test_file}.tmp"
        sed "s|\"x-api-key\": \"[A-Za-z0-9]*\"|\"x-api-key\": \"${API_KEY}\"|g" "${test_file}.tmp" > "$test_file"
        
        # 清理临时文件
        rm -f "${test_file}.tmp" "${test_file}.bak"
    fi
done

# 显示配置摘要
echo ""
echo "======================================================================"
log_info "配置同步完成！"
echo "======================================================================"
echo "API Gateway URL: ${API_URL}"
echo "API Key: ${API_KEY:0:20}... (${KEY_LENGTH}字符)"
echo "更新时间: $(date)"
echo "======================================================================"

# 验证配置
log_info "验证配置..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "x-api-key: ${API_KEY}" \
    "${API_URL}/health" 2>/dev/null || echo "000")

if [ "$response" = "200" ]; then
    log_info "✅ API健康检查通过"
else
    log_warning "⚠️ API健康检查返回: $response"
    log_warning "请检查API Gateway部署状态"
fi

echo ""
log_info "下一步: 运行 'python3 test_backend_apis.py' 进行测试"