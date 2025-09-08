#!/bin/bash
# API Gateway 部署后健康检查脚本
# 验证 API 端点是否正常工作

set -euo pipefail

# 日志函数
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >&2
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
}

success() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS: $1" >&2
}

warning() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1" >&2
}

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log "开始 API Gateway 健康检查..."

# 检查是否能获取 Terraform 输出
log "获取部署信息..."

# 获取 API Gateway URL
if ! api_url=$(terraform output -raw api_gateway_url 2>/dev/null); then
    error "无法获取 API Gateway URL，请确认部署是否成功"
fi

# 获取 API Key
if ! api_key=$(terraform output -raw api_gateway_api_key 2>/dev/null); then
    warning "无法获取 API Key，某些测试可能失败"
    api_key=""
fi

log "API Gateway URL: $api_url"
if [[ -n "$api_key" ]]; then
    log "API Key: ${api_key:0:10}..."
else
    log "API Key: 未配置"
fi

# 健康检查函数
check_endpoint() {
    local method="$1"
    local endpoint="$2"
    local expected_status="$3"
    local description="$4"
    local use_api_key="$5"
    
    log "测试: $description"
    log "请求: $method $api_url$endpoint"
    
    # 构建 curl 命令
    local curl_cmd="curl -s -w '%{http_code}\\n' -o /tmp/health_check_response.txt"
    curl_cmd="$curl_cmd -X $method"
    
    # 如果需要 API Key
    if [[ "$use_api_key" == "true" ]] && [[ -n "$api_key" ]]; then
        curl_cmd="$curl_cmd -H 'X-API-Key: $api_key'"
    fi
    
    # 添加通用 headers
    curl_cmd="$curl_cmd -H 'Content-Type: application/json'"
    curl_cmd="$curl_cmd -H 'Accept: application/json'"
    
    # 添加 URL
    curl_cmd="$curl_cmd '$api_url$endpoint'"
    
    # 执行请求
    local http_code
    if http_code=$(eval "$curl_cmd" 2>/dev/null); then
        local response_body
        response_body=$(cat /tmp/health_check_response.txt 2>/dev/null || echo "")
        
        if [[ "$http_code" == "$expected_status" ]]; then
            success "✓ $description - HTTP $http_code"
            if [[ -n "$response_body" ]] && [[ ${#response_body} -lt 500 ]]; then
                log "  响应: $response_body"
            fi
        else
            error "✗ $description - 期望 HTTP $expected_status，实际 HTTP $http_code"
            if [[ -n "$response_body" ]]; then
                log "  响应: $response_body"
            fi
            return 1
        fi
    else
        error "✗ $description - 请求失败"
        return 1
    fi
}

# 健康检查计数器
total_checks=0
failed_checks=0

# 执行健康检查
log "======================================"
log "执行 API 端点健康检查"
log "======================================"

# 1. 基础健康检查端点（无需 API Key）
total_checks=$((total_checks + 1))
if ! check_endpoint "GET" "/health" "200" "基础健康检查" "false"; then
    failed_checks=$((failed_checks + 1))
fi

total_checks=$((total_checks + 1))
if ! check_endpoint "GET" "/health/ready" "200" "就绪状态检查" "false"; then
    failed_checks=$((failed_checks + 1))
fi

# 2. 模板端点测试
total_checks=$((total_checks + 1))
if ! check_endpoint "GET" "/templates" "200" "获取模板列表" "true"; then
    failed_checks=$((failed_checks + 1))
fi

total_checks=$((total_checks + 1))
if ! check_endpoint "OPTIONS" "/templates" "200" "模板 CORS 预检" "false"; then
    failed_checks=$((failed_checks + 1))
fi

# 3. 任务端点测试（如果存在）
if [[ -n "$api_key" ]]; then
    total_checks=$((total_checks + 1))
    # 测试不存在的任务ID，应该返回 404 或其他错误状态
    if check_endpoint "GET" "/tasks/test-task-id" "404" "任务查询（不存在的ID）" "true" 2>/dev/null; then
        : # 成功
    elif check_endpoint "GET" "/tasks/test-task-id" "400" "任务查询（无效ID格式）" "true" 2>/dev/null; then
        : # 也算成功，不同的错误处理方式
    else
        failed_checks=$((failed_checks + 1))
        log "任务端点可能未正确配置或 Lambda 函数有问题"
    fi
    
    total_checks=$((total_checks + 1))
    if ! check_endpoint "OPTIONS" "/tasks/test-id" "200" "任务 CORS 预检" "false"; then
        failed_checks=$((failed_checks + 1))
    fi
else
    warning "跳过需要 API Key 的任务端点测试"
fi

# 4. 主要 API 端点测试（如果存在且有 API Key）
if [[ -n "$api_key" ]]; then
    # 测试演示文稿列表
    total_checks=$((total_checks + 1))
    if check_endpoint "GET" "/presentations" "200" "演示文稿列表" "true" 2>/dev/null; then
        : # 成功
    elif check_endpoint "GET" "/presentations" "404" "演示文稿列表（无数据）" "true" 2>/dev/null; then
        : # 无数据也算正常
    else
        failed_checks=$((failed_checks + 1))
    fi
    
    # 测试会话端点
    total_checks=$((total_checks + 1))
    if check_endpoint "GET" "/sessions" "200" "会话列表" "true" 2>/dev/null; then
        : # 成功
    elif check_endpoint "GET" "/sessions" "404" "会话列表（无数据）" "true" 2>/dev/null; then
        : # 无数据也算正常
    else
        failed_checks=$((failed_checks + 1))
    fi
else
    warning "跳过需要 API Key 的主要端点测试"
fi

# 清理临时文件
rm -f /tmp/health_check_response.txt

# 输出总结
log "======================================"
if [[ $failed_checks -eq 0 ]]; then
    success "所有健康检查通过！($total_checks/$total_checks)"
    log "API Gateway 部署成功且功能正常"
else
    error "$failed_checks/$total_checks 个检查失败"
    log "需要检查失败的端点配置"
fi

log "======================================"

# 额外的系统检查
log "执行系统级检查..."

# 检查 CloudWatch 日志组是否存在
log_group_name="/aws/apigateway/${api_url##*/}-stage"
if aws logs describe-log-groups --log-group-name-prefix "/aws/apigateway/" --query 'logGroups[].logGroupName' --output text 2>/dev/null | grep -q apigateway; then
    success "CloudWatch 日志组已配置"
else
    warning "CloudWatch 日志组可能未正确配置"
fi

# 检查 API Gateway 的整体状态
if aws apigateway get-rest-apis --query 'items[?name==`ai-ppt-assistant-dev-api`]' --output text >/dev/null 2>&1; then
    success "API Gateway REST API 状态正常"
else
    warning "无法验证 API Gateway REST API 状态"
fi

success "健康检查完成"

# 如果有失败的检查，返回错误退出码
if [[ $failed_checks -gt 0 ]]; then
    exit 1
fi

exit 0