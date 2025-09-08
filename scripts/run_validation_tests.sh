#!/bin/bash

# API 参数验证测试运行脚本
# 此脚本设置环境并运行完整的API验证测试套件

set -e  # 遇到错误时退出

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INFRASTRUCTURE_DIR="$PROJECT_DIR/infrastructure"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}❌ ERROR:${NC} $1"
}

# 函数：检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 未安装"
        exit 1
    fi
    
    # 检查requests库
    if ! python3 -c "import requests" &> /dev/null; then
        log_warning "requests库未安装，正在安装..."
        pip3 install requests
    fi
    
    # 检查terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform 未安装"
        exit 1
    fi
    
    # 检查aws cli
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI 未安装"
        exit 1
    fi
    
    log_success "所有依赖检查通过"
}

# 函数：获取API信息
get_api_info() {
    log_info "获取API Gateway信息..."
    
    cd "$INFRASTRUCTURE_DIR"
    
    # 获取API Gateway URL
    API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
    if [[ -z "$API_URL" ]]; then
        log_error "无法获取API Gateway URL。请确保基础设施已部署"
        exit 1
    fi
    
    # 获取API Key
    API_KEY=$(terraform output -raw api_gateway_api_key 2>/dev/null || echo "")
    if [[ -z "$API_KEY" ]]; then
        log_error "无法获取API Key。请确保基础设施已部署"
        exit 1
    fi
    
    log_success "API信息获取成功"
    log_info "API URL: $API_URL"
    log_info "API Key: ${API_KEY:0:8}..." # 只显示前8位
}

# 函数：运行基本连接测试
test_basic_connectivity() {
    log_info "测试基本连接性..."
    
    # 测试健康检查端点（不需要API Key）
    HEALTH_URL="$API_URL/health"
    
    if curl -s --max-time 10 "$HEALTH_URL" > /dev/null; then
        log_success "API Gateway连接正常"
    else
        log_error "API Gateway连接失败"
        exit 1
    fi
}

# 函数：运行验证测试
run_validation_tests() {
    log_info "运行API参数验证测试..."
    
    export API_BASE_URL="$API_URL"
    export API_KEY="$API_KEY"
    
    cd "$PROJECT_DIR"
    
    # 运行Python测试脚本
    if python3 scripts/test_api_validation.py; then
        log_success "API参数验证测试全部通过"
        return 0
    else
        log_error "API参数验证测试失败"
        return 1
    fi
}

# 函数：生成测试报告
generate_test_report() {
    log_info "生成测试报告..."
    
    REPORT_FILE="$PROJECT_DIR/test_validation_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$REPORT_FILE" << EOF
# API参数验证测试报告

**生成时间**: $(date '+%Y-%m-%d %H:%M:%S')
**API Gateway URL**: $API_URL
**测试脚本**: scripts/test_api_validation.py

## 测试概要

此测试验证了以下API Gateway功能：

### ✅ JSON Schema验证
- 请求体结构验证
- 必需字段验证
- 数据类型验证
- 枚举值验证
- 字符串长度验证
- 数值范围验证

### ✅ 路径参数验证
- UUID格式验证
- 路径参数存在性验证

### ✅ 查询参数验证
- 参数类型验证
- 参数范围验证
- 可选参数处理

### ✅ 错误响应格式化
- 友好的错误消息
- 统一的错误响应结构
- 适当的HTTP状态码
- CORS头设置

### ✅ API密钥验证
- API密钥存在性检查
- 无效密钥拒绝

## 测试覆盖的端点

1. **POST /presentations** - 生成演示文稿
2. **GET /tasks/{task_id}** - 获取任务状态
3. **GET /templates** - 获取模板列表
4. **POST /sessions** - 创建会话

## 验证配置详情

### JSON Schema模型
- GeneratePresentationRequest
- CreateSessionRequest
- ExecuteAgentRequest
- ErrorResponse
- PathParameters
- QueryParameters

### 请求验证器
- validate_all - 验证请求体和参数
- validate_body - 仅验证请求体
- validate_parameters - 仅验证参数

### 错误响应处理
- BAD_REQUEST_BODY (400)
- BAD_REQUEST_PARAMETERS (400)
- MISSING_AUTHENTICATION_TOKEN (403)
- THROTTLED (429)
- DEFAULT_5XX (500)

## 部署建议

1. **监控告警**: 为400/403错误设置CloudWatch告警
2. **日志分析**: 定期检查验证失败的请求模式
3. **性能优化**: 监控验证对请求延迟的影响
4. **文档更新**: 确保API文档与验证规则保持同步

---
*此报告由自动化测试脚本生成*
EOF

    log_success "测试报告已生成: $REPORT_FILE"
}

# 函数：清理环境变量
cleanup() {
    unset API_BASE_URL
    unset API_KEY
    log_info "环境变量已清理"
}

# 主函数
main() {
    echo "🧪 API参数验证测试套件"
    echo "=========================="
    
    # 检查依赖
    check_dependencies
    
    # 获取API信息
    get_api_info
    
    # 测试基本连接
    test_basic_connectivity
    
    # 运行验证测试
    if run_validation_tests; then
        log_success "所有测试通过！"
        
        # 生成测试报告
        generate_test_report
        
        # 清理环境变量
        cleanup
        
        echo ""
        echo "🎉 API参数验证配置验证完成！"
        echo ""
        echo "📋 下一步建议："
        echo "1. 检查CloudWatch日志中的验证错误"
        echo "2. 配置监控告警"
        echo "3. 更新API文档"
        echo "4. 通知前端团队验证规则变更"
        
        exit 0
    else
        log_error "测试失败，请检查配置"
        cleanup
        exit 1
    fi
}

# 处理脚本退出
trap cleanup EXIT

# 运行主函数
main "$@"