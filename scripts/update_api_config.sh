#!/bin/bash

# AWS Expert: API Configuration Auto-Update Script
# 自动获取和更新API Key及相关配置，确保测试脚本始终使用正确的配置

set -e  # 遇到错误时退出

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置信息
PROJECT_NAME="ai-ppt-assistant"
ENVIRONMENT="dev"
AWS_REGION="${AWS_REGION:-us-east-1}"

# 文件路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_FILES=(
    "$PROJECT_ROOT/comprehensive_backend_test.py"
    "$PROJECT_ROOT/test_all_backend_apis.py"
    "$PROJECT_ROOT/system_health_check.py"
)

echo -e "${BLUE}🔧 AI PPT Assistant API配置自动更新工具${NC}"
echo -e "${BLUE}======================================${NC}"
echo -e "项目: $PROJECT_NAME"
echo -e "环境: $ENVIRONMENT"
echo -e "区域: $AWS_REGION"
echo

# 函数：获取API Gateway URL
get_api_gateway_url() {
    echo -e "${YELLOW}🔍 获取API Gateway URL...${NC}" >&2
    
    # 查找API Gateway (尝试多种命名模式)
    local api_id=$(aws apigateway get-rest-apis \
        --region "$AWS_REGION" \
        --query "items[?name=='${PROJECT_NAME}-${ENVIRONMENT}-api' || name=='${PROJECT_NAME}-${ENVIRONMENT}' || name=='${PROJECT_NAME}'].id" \
        --output text 2>/dev/null)
    
    # 如果还没找到，尝试查找包含项目名的API
    if [ -z "$api_id" ] || [ "$api_id" = "None" ]; then
        api_id=$(aws apigateway get-rest-apis \
            --region "$AWS_REGION" \
            --query "items[?contains(name, '${PROJECT_NAME}')].id" \
            --output text 2>/dev/null | head -1)
    fi
    
    if [ -z "$api_id" ] || [ "$api_id" = "None" ]; then
        echo -e "${RED}❌ 未找到API Gateway: ${PROJECT_NAME}-${ENVIRONMENT}${NC}" >&2
        return 1
    fi
    
    local api_url="https://${api_id}.execute-api.${AWS_REGION}.amazonaws.com/legacy"
    echo -e "${GREEN}✅ API Gateway URL: $api_url${NC}" >&2
    echo "$api_url"
}

# 函数：获取API Key
get_api_key() {
    echo -e "${YELLOW}🔑 获取API Key...${NC}" >&2
    
    # 查找API Key
    local api_key=$(aws apigateway get-api-keys \
        --region "$AWS_REGION" \
        --include-values \
        --query "items[?name=='${PROJECT_NAME}-${ENVIRONMENT}-api-key'].value" \
        --output text 2>/dev/null)
    
    if [ -z "$api_key" ] || [ "$api_key" = "None" ]; then
        echo -e "${RED}❌ 未找到API Key: ${PROJECT_NAME}-${ENVIRONMENT}-api-key${NC}" >&2
        return 1
    fi
    
    echo -e "${GREEN}✅ API Key: ${api_key:0:8}...${api_key: -8}${NC}" >&2
    echo "$api_key"
}

# 函数：验证AWS CLI和权限
validate_aws_access() {
    echo -e "${YELLOW}🔐 验证AWS访问权限...${NC}"
    
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI 未安装${NC}"
        return 1
    fi
    
    if ! aws sts get-caller-identity --region "$AWS_REGION" &>/dev/null; then
        echo -e "${RED}❌ AWS 权限验证失败${NC}"
        echo -e "请检查 AWS credentials 配置"
        return 1
    fi
    
    echo -e "${GREEN}✅ AWS 访问权限验证成功${NC}"
}

# 函数：更新Python测试文件中的配置
update_python_file() {
    local file_path="$1"
    local api_url="$2"
    local api_key="$3"
    
    # 使用Python脚本进行更安全的配置更新
    if command -v python3 &> /dev/null; then
        python3 "$SCRIPT_DIR/update_config.py" \
            --api-url "$api_url" \
            --api-key "$api_key" \
            "$file_path"
    else
        echo -e "${RED}❌ Python3 未找到，无法更新配置文件${NC}"
        return 1
    fi
}

# 函数：验证更新后的配置
validate_configuration() {
    local api_url="$1"
    local api_key="$2"
    
    echo -e "${YELLOW}🧪 验证API配置...${NC}"
    
    # 测试基础连通性
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "X-API-Key: $api_key" \
        -H "Content-Type: application/json" \
        "$api_url/health" \
        --connect-timeout 10 \
        --max-time 30)
    
    if [ "$response_code" = "200" ]; then
        echo -e "${GREEN}✅ API配置验证成功 (HTTP $response_code)${NC}"
        return 0
    else
        echo -e "${RED}❌ API配置验证失败 (HTTP $response_code)${NC}"
        echo -e "${YELLOW}💡 这可能是正常的，如果API Gateway刚刚部署${NC}"
        return 1
    fi
}

# 函数：生成配置信息文件
generate_config_info() {
    local api_url="$1"
    local api_key="$2"
    
    local config_file="$PROJECT_ROOT/api_config_info.json"
    
    cat > "$config_file" << EOF
{
  "project": "$PROJECT_NAME",
  "environment": "$ENVIRONMENT",
  "region": "$AWS_REGION",
  "api_gateway_url": "$api_url",
  "api_key": "$api_key",
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "updated_by": "update_api_config.sh",
  "files_updated": [
$(for file in "${TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "    \"$(basename "$file")\","
    fi
done | sed '$ s/,$//')
  ]
}
EOF
    
    echo -e "${GREEN}📄 配置信息已保存到: $config_file${NC}"
}

# 函数：显示使用帮助
show_help() {
    cat << EOF
${BLUE}用法: $0 [选项]${NC}

${YELLOW}选项:${NC}
  -h, --help          显示此帮助信息
  -v, --validate-only 仅验证配置，不更新文件
  -r, --region REGION 指定AWS区域 (默认: us-east-1)
  -d, --dry-run       干运行模式，显示将要执行的操作但不实际执行

${YELLOW}示例:${NC}
  $0                           # 自动更新所有配置
  $0 --validate-only           # 仅验证当前配置
  $0 --region us-west-2        # 指定不同区域
  $0 --dry-run                 # 查看将要执行的操作

${YELLOW}集成到部署流程:${NC}
  make deploy && scripts/update_api_config.sh
EOF
}

# 主执行逻辑
main() {
    local validate_only=false
    local dry_run=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--validate-only)
                validate_only=true
                shift
                ;;
            -r|--region)
                AWS_REGION="$2"
                shift 2
                ;;
            -d|--dry-run)
                dry_run=true
                shift
                ;;
            *)
                echo -e "${RED}❌ 未知选项: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 验证AWS访问
    validate_aws_access || exit 1
    
    # 获取配置信息
    local api_url=$(get_api_gateway_url) || exit 1
    local api_key=$(get_api_key) || exit 1
    
    if [ "$validate_only" = true ]; then
        echo -e "\n${YELLOW}🧪 验证模式${NC}"
        validate_configuration "$api_url" "$api_key"
        exit 0
    fi
    
    if [ "$dry_run" = true ]; then
        echo -e "\n${YELLOW}🏃 干运行模式 - 将要执行的操作:${NC}"
        echo -e "API Gateway URL: $api_url"
        echo -e "API Key: ${api_key:0:8}...${api_key: -8}"
        echo -e "将更新的文件:"
        for file in "${TEST_FILES[@]}"; do
            if [ -f "$file" ]; then
                echo -e "  - $(basename "$file")"
            fi
        done
        exit 0
    fi
    
    echo -e "\n${YELLOW}📝 开始更新配置文件...${NC}"
    
    # 更新所有测试文件
    for file in "${TEST_FILES[@]}"; do
        update_python_file "$file" "$api_url" "$api_key"
    done
    
    # 生成配置信息
    generate_config_info "$api_url" "$api_key"
    
    # 验证配置
    echo
    validate_configuration "$api_url" "$api_key"
    
    echo -e "\n${GREEN}🎉 API配置更新完成！${NC}"
    echo -e "${YELLOW}💡 提示: 现在可以运行测试脚本验证系统功能${NC}"
    echo -e "   python3 comprehensive_backend_test.py"
}

# 如果脚本被直接执行（不是被source）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi