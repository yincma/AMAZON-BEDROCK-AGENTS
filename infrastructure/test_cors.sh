#!/bin/bash

# ==============================================================================
# CORS配置专项测试脚本
# 详细测试API的跨域资源共享配置
# ==============================================================================

set -euo pipefail

# 配置变量
API_BASE_URL="https://fe2kf91287.execute-api.us-east-1.amazonaws.com/dev"
TEST_RESULTS_DIR="./test_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${TEST_RESULTS_DIR}/cors_test_${TIMESTAMP}.log"
REPORT_FILE="${TEST_RESULTS_DIR}/cors_report_${TIMESTAMP}.json"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 创建测试结果目录
mkdir -p "$TEST_RESULTS_DIR"

# 初始化测试统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNINGS=0

# 测试结果数组
declare -a CORS_RESULTS=()

# ==============================================================================
# 工具函数
# ==============================================================================

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[PASS]${NC} $1"
    ((PASSED_TESTS++))
}

log_error() {
    log "${RED}[FAIL]${NC} $1"
    ((FAILED_TESTS++))
}

log_warning() {
    log "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

start_test() {
    local test_name="$1"
    ((TOTAL_TESTS++))
    log_info "开始CORS测试: $test_name"
    echo "  测试编号: $TOTAL_TESTS"
}

# 执行CORS请求并返回关键信息
cors_request() {
    local method="$1"
    local endpoint="$2"
    local origin="${3:-https://example.com}"
    local request_method="${4:-GET}"
    local request_headers="${5:-Content-Type}"

    local temp_file=$(mktemp)
    local temp_headers=$(mktemp)

    local response_code
    if [[ "$method" == "OPTIONS" ]]; then
        response_code=$(curl -s -w "%{http_code}" \
            -X OPTIONS \
            -H "Origin: $origin" \
            -H "Access-Control-Request-Method: $request_method" \
            -H "Access-Control-Request-Headers: $request_headers" \
            -D "$temp_headers" \
            -o "$temp_file" \
            "$API_BASE_URL$endpoint")
    else
        response_code=$(curl -s -w "%{http_code}" \
            -X "$method" \
            -H "Origin: $origin" \
            -H "Content-Type: application/json" \
            -D "$temp_headers" \
            -o "$temp_file" \
            "$API_BASE_URL$endpoint")
    fi

    # 提取CORS相关头部
    local access_control_allow_origin=""
    local access_control_allow_methods=""
    local access_control_allow_headers=""
    local access_control_max_age=""
    local access_control_allow_credentials=""

    if [[ -f "$temp_headers" ]]; then
        access_control_allow_origin=$(grep -i "access-control-allow-origin:" "$temp_headers" | cut -d' ' -f2- | tr -d '\r\n' || echo "")
        access_control_allow_methods=$(grep -i "access-control-allow-methods:" "$temp_headers" | cut -d' ' -f2- | tr -d '\r\n' || echo "")
        access_control_allow_headers=$(grep -i "access-control-allow-headers:" "$temp_headers" | cut -d' ' -f2- | tr -d '\r\n' || echo "")
        access_control_max_age=$(grep -i "access-control-max-age:" "$temp_headers" | cut -d' ' -f2- | tr -d '\r\n' || echo "")
        access_control_allow_credentials=$(grep -i "access-control-allow-credentials:" "$temp_headers" | cut -d' ' -f2- | tr -d '\r\n' || echo "")
    fi

    # 清理临时文件
    rm -f "$temp_file" "$temp_headers"

    # 返回结果（用|分隔）
    echo "$response_code|$access_control_allow_origin|$access_control_allow_methods|$access_control_allow_headers|$access_control_max_age|$access_control_allow_credentials"
}

# ==============================================================================
# CORS测试用例
# ==============================================================================

# 测试1: 基本OPTIONS预检请求
test_basic_preflight() {
    start_test "基本OPTIONS预检请求"

    local result
    result=$(cors_request "OPTIONS" "/generate" "https://example.com" "POST" "Content-Type")

    local status_code=$(echo "$result" | cut -d'|' -f1)
    local allow_origin=$(echo "$result" | cut -d'|' -f2)
    local allow_methods=$(echo "$result" | cut -d'|' -f3)
    local allow_headers=$(echo "$result" | cut -d'|' -f4)

    if [[ "$status_code" == "200" ]] || [[ "$status_code" == "204" ]]; then
        log_success "OPTIONS预检请求成功 (状态码: $status_code)"

        # 检查必要的CORS头部
        local cors_issues=()

        if [[ -z "$allow_origin" ]] || [[ "$allow_origin" == "null" ]]; then
            cors_issues+=("缺少Access-Control-Allow-Origin头")
        elif [[ "$allow_origin" != "*" ]] && [[ "$allow_origin" != "https://example.com" ]]; then
            cors_issues+=("Access-Control-Allow-Origin配置可能有问题: $allow_origin")
        fi

        if [[ -z "$allow_methods" ]]; then
            cors_issues+=("缺少Access-Control-Allow-Methods头")
        elif [[ "$allow_methods" != *"POST"* ]]; then
            cors_issues+=("Access-Control-Allow-Methods不包含POST方法")
        fi

        if [[ -z "$allow_headers" ]]; then
            cors_issues+=("缺少Access-Control-Allow-Headers头")
        elif [[ "$allow_headers" != *"Content-Type"* ]]; then
            cors_issues+=("Access-Control-Allow-Headers不包含Content-Type")
        fi

        if [[ ${#cors_issues[@]} -eq 0 ]]; then
            log_success "CORS头部配置正确"
            CORS_RESULTS+=("{\"test\":\"基本OPTIONS预检\",\"status\":\"PASS\",\"details\":\"CORS头部配置正确\",\"headers\":{\"origin\":\"$allow_origin\",\"methods\":\"$allow_methods\",\"headers\":\"$allow_headers\"}}")
        else
            log_warning "CORS配置存在问题: ${cors_issues[*]}"
            CORS_RESULTS+=("{\"test\":\"基本OPTIONS预检\",\"status\":\"WARN\",\"details\":\"CORS配置问题: $(IFS=', '; echo "${cors_issues[*]}")\",\"headers\":{\"origin\":\"$allow_origin\",\"methods\":\"$allow_methods\",\"headers\":\"$allow_headers\"}}")
        fi
    else
        log_error "OPTIONS预检请求失败 (状态码: $status_code)"
        CORS_RESULTS+=("{\"test\":\"基本OPTIONS预检\",\"status\":\"FAIL\",\"details\":\"预检请求失败，状态码: $status_code\"}")
    fi
}

# 测试2: 不同来源域名测试
test_different_origins() {
    start_test "不同来源域名CORS测试"

    local origins=(
        "https://localhost:3000"
        "https://example.org"
        "https://test.example.com"
        "http://localhost:8080"
        "https://cors-test.com"
    )

    local origin_results=()
    local successful_origins=0

    for origin in "${origins[@]}"; do
        local result
        result=$(cors_request "OPTIONS" "/generate" "$origin" "POST" "Content-Type")

        local status_code=$(echo "$result" | cut -d'|' -f1)
        local allow_origin=$(echo "$result" | cut -d'|' -f2)

        if [[ "$status_code" == "200" ]] || [[ "$status_code" == "204" ]]; then
            if [[ "$allow_origin" == "*" ]] || [[ "$allow_origin" == "$origin" ]]; then
                origin_results+=("✓ $origin - 允许访问")
                ((successful_origins++))
            else
                origin_results+=("✗ $origin - Origin头不匹配: $allow_origin")
            fi
        else
            origin_results+=("✗ $origin - 请求失败 (状态码: $status_code)")
        fi
    done

    if [[ $successful_origins -gt 0 ]]; then
        log_success "多来源测试完成 ($successful_origins/${#origins[@]} 成功)"
        CORS_RESULTS+=("{\"test\":\"不同来源域名\",\"status\":\"PASS\",\"details\":\"$successful_origins/${#origins[@]} 来源测试通过\",\"origin_results\":$(printf '%s\n' "${origin_results[@]}" | jq -R . | jq -s .)}")
    else
        log_error "所有来源都被拒绝"
        CORS_RESULTS+=("{\"test\":\"不同来源域名\",\"status\":\"FAIL\",\"details\":\"所有来源都被拒绝\",\"origin_results\":$(printf '%s\n' "${origin_results[@]}" | jq -R . | jq -s .)}")
    fi
}

# 测试3: 不同HTTP方法的CORS支持
test_different_methods() {
    start_test "不同HTTP方法CORS支持测试"

    local methods=("GET" "POST" "PUT" "DELETE" "PATCH")
    local method_results=()
    local supported_methods=0

    for method in "${methods[@]}"; do
        local result
        result=$(cors_request "OPTIONS" "/generate" "https://example.com" "$method" "Content-Type")

        local status_code=$(echo "$result" | cut -d'|' -f1)
        local allow_methods=$(echo "$result" | cut -d'|' -f3)

        if [[ "$status_code" == "200" ]] || [[ "$status_code" == "204" ]]; then
            if [[ "$allow_methods" == *"$method"* ]] || [[ "$allow_methods" == "*" ]]; then
                method_results+=("✓ $method - 支持")
                ((supported_methods++))
            else
                method_results+=("✗ $method - 不在允许方法列表中")
            fi
        else
            method_results+=("✗ $method - 预检请求失败")
        fi
    done

    if [[ $supported_methods -ge 2 ]]; then  # 至少支持2个方法
        log_success "HTTP方法测试通过 ($supported_methods/${#methods[@]} 方法支持)"
        CORS_RESULTS+=("{\"test\":\"HTTP方法支持\",\"status\":\"PASS\",\"details\":\"$supported_methods/${#methods[@]} 方法支持\",\"method_results\":$(printf '%s\n' "${method_results[@]}" | jq -R . | jq -s .)}")
    else
        log_warning "HTTP方法支持较少 ($supported_methods/${#methods[@]})"
        CORS_RESULTS+=("{\"test\":\"HTTP方法支持\",\"status\":\"WARN\",\"details\":\"方法支持较少: $supported_methods/${#methods[@]}\",\"method_results\":$(printf '%s\n' "${method_results[@]}" | jq -R . | jq -s .)}")
    fi
}

# 测试4: 不同请求头的CORS支持
test_different_headers() {
    start_test "不同请求头CORS支持测试"

    local headers_to_test=(
        "Content-Type"
        "Authorization"
        "X-Api-Key"
        "Accept"
        "X-Requested-With"
        "X-Custom-Header"
    )

    local header_results=()
    local supported_headers=0

    for header in "${headers_to_test[@]}"; do
        local result
        result=$(cors_request "OPTIONS" "/generate" "https://example.com" "POST" "$header")

        local status_code=$(echo "$result" | cut -d'|' -f1)
        local allow_headers=$(echo "$result" | cut -d'|' -f4)

        if [[ "$status_code" == "200" ]] || [[ "$status_code" == "204" ]]; then
            if [[ "$allow_headers" == *"$header"* ]] || [[ "$allow_headers" == "*" ]]; then
                header_results+=("✓ $header - 支持")
                ((supported_headers++))
            else
                header_results+=("✗ $header - 不在允许头部列表中")
            fi
        else
            header_results+=("✗ $header - 预检请求失败")
        fi
    done

    if [[ $supported_headers -ge 3 ]]; then  # 至少支持3个常用头部
        log_success "请求头测试通过 ($supported_headers/${#headers_to_test[@]} 头部支持)"
        CORS_RESULTS+=("{\"test\":\"请求头支持\",\"status\":\"PASS\",\"details\":\"$supported_headers/${#headers_to_test[@]} 头部支持\",\"header_results\":$(printf '%s\n' "${header_results[@]}" | jq -R . | jq -s .)}")
    else
        log_warning "请求头支持较少 ($supported_headers/${#headers_to_test[@]})"
        CORS_RESULTS+=("{\"test\":\"请求头支持\",\"status\":\"WARN\",\"details\":\"头部支持较少: $supported_headers/${#headers_to_test[@]}\",\"header_results\":$(printf '%s\n' "${header_results[@]}" | jq -R . | jq -s .)}")
    fi
}

# 测试5: 实际跨域请求测试
test_actual_cors_request() {
    start_test "实际跨域请求测试"

    # 测试实际的POST请求
    local temp_file=$(mktemp)
    local temp_headers=$(mktemp)

    local request_data='{"topic":"CORS测试主题","page_count":5}'

    local response_code
    response_code=$(curl -s -w "%{http_code}" \
        -X POST \
        -H "Origin: https://example.com" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$request_data" \
        -D "$temp_headers" \
        -o "$temp_file" \
        "$API_BASE_URL/generate")

    # 检查CORS响应头
    local cors_origin=""
    if [[ -f "$temp_headers" ]]; then
        cors_origin=$(grep -i "access-control-allow-origin:" "$temp_headers" | cut -d' ' -f2- | tr -d '\r\n' || echo "")
    fi

    # 清理临时文件
    rm -f "$temp_file" "$temp_headers"

    if [[ "$response_code" == "200" ]] || [[ "$response_code" == "202" ]]; then
        if [[ -n "$cors_origin" ]]; then
            log_success "实际跨域请求成功 (状态码: $response_code, CORS Origin: $cors_origin)"
            CORS_RESULTS+=("{\"test\":\"实际跨域请求\",\"status\":\"PASS\",\"details\":\"跨域请求成功，状态码: $response_code\",\"cors_origin\":\"$cors_origin\"}")
        else
            log_warning "实际请求成功但缺少CORS头 (状态码: $response_code)"
            CORS_RESULTS+=("{\"test\":\"实际跨域请求\",\"status\":\"WARN\",\"details\":\"请求成功但缺少CORS响应头\",\"status_code\":$response_code}")
        fi
    elif [[ "$response_code" == "400" ]]; then
        # 400可能是参数验证失败，但CORS应该仍然工作
        if [[ -n "$cors_origin" ]]; then
            log_success "CORS功能正常 (请求因参数错误返回400，但包含CORS头)"
            CORS_RESULTS+=("{\"test\":\"实际跨域请求\",\"status\":\"PASS\",\"details\":\"CORS正常，请求参数错误\",\"status_code\":$response_code}")
        else
            log_warning "请求失败且缺少CORS头 (状态码: $response_code)"
            CORS_RESULTS+=("{\"test\":\"实际跨域请求\",\"status\":\"WARN\",\"details\":\"请求失败且缺少CORS头\",\"status_code\":$response_code}")
        fi
    else
        log_error "实际跨域请求失败 (状态码: $response_code)"
        CORS_RESULTS+=("{\"test\":\"实际跨域请求\",\"status\":\"FAIL\",\"details\":\"跨域请求失败，状态码: $response_code\",\"status_code\":$response_code}")
    fi
}

# 测试6: 所有API端点的CORS支持
test_all_endpoints_cors() {
    start_test "所有API端点CORS支持测试"

    local endpoints=(
        "/generate"
        "/status/test-id"
        "/download/test-id"
    )

    local endpoint_results=()
    local cors_enabled_endpoints=0

    for endpoint in "${endpoints[@]}"; do
        local result
        result=$(cors_request "OPTIONS" "$endpoint" "https://example.com" "GET" "Content-Type")

        local status_code=$(echo "$result" | cut -d'|' -f1)
        local allow_origin=$(echo "$result" | cut -d'|' -f2)

        if [[ "$status_code" == "200" ]] || [[ "$status_code" == "204" ]]; then
            if [[ -n "$allow_origin" ]] && [[ "$allow_origin" != "null" ]]; then
                endpoint_results+=("✓ $endpoint - CORS已启用")
                ((cors_enabled_endpoints++))
            else
                endpoint_results+=("✗ $endpoint - 缺少CORS头")
            fi
        else
            endpoint_results+=("✗ $endpoint - OPTIONS请求失败 (状态码: $status_code)")
        fi
    done

    if [[ $cors_enabled_endpoints -eq ${#endpoints[@]} ]]; then
        log_success "所有端点CORS配置正常 ($cors_enabled_endpoints/${#endpoints[@]})"
        CORS_RESULTS+=("{\"test\":\"所有端点CORS\",\"status\":\"PASS\",\"details\":\"所有端点CORS正常\",\"endpoint_results\":$(printf '%s\n' "${endpoint_results[@]}" | jq -R . | jq -s .)}")
    elif [[ $cors_enabled_endpoints -gt 0 ]]; then
        log_warning "部分端点CORS配置正常 ($cors_enabled_endpoints/${#endpoints[@]})"
        CORS_RESULTS+=("{\"test\":\"所有端点CORS\",\"status\":\"WARN\",\"details\":\"部分端点CORS正常: $cors_enabled_endpoints/${#endpoints[@]}\",\"endpoint_results\":$(printf '%s\n' "${endpoint_results[@]}" | jq -R . | jq -s .)}")
    else
        log_error "所有端点都缺少CORS配置"
        CORS_RESULTS+=("{\"test\":\"所有端点CORS\",\"status\":\"FAIL\",\"details\":\"所有端点都缺少CORS配置\",\"endpoint_results\":$(printf '%s\n' "${endpoint_results[@]}" | jq -R . | jq -s .)}")
    fi
}

# 测试7: CORS缓存测试
test_cors_caching() {
    start_test "CORS预检缓存测试"

    local result
    result=$(cors_request "OPTIONS" "/generate" "https://example.com" "POST" "Content-Type")

    local status_code=$(echo "$result" | cut -d'|' -f1)
    local max_age=$(echo "$result" | cut -d'|' -f5)

    if [[ "$status_code" == "200" ]] || [[ "$status_code" == "204" ]]; then
        if [[ -n "$max_age" ]] && [[ "$max_age" != "null" ]]; then
            if [[ "$max_age" -gt 0 ]]; then
                log_success "CORS预检缓存配置正常 (Max-Age: $max_age 秒)"
                CORS_RESULTS+=("{\"test\":\"CORS预检缓存\",\"status\":\"PASS\",\"details\":\"缓存配置正常，Max-Age: $max_age 秒\",\"max_age\":\"$max_age\"}")
            else
                log_warning "CORS预检缓存时间为0"
                CORS_RESULTS+=("{\"test\":\"CORS预检缓存\",\"status\":\"WARN\",\"details\":\"缓存时间为0\",\"max_age\":\"$max_age\"}")
            fi
        else
            log_warning "未配置CORS预检缓存 (缺少Max-Age头)"
            CORS_RESULTS+=("{\"test\":\"CORS预检缓存\",\"status\":\"WARN\",\"details\":\"未配置预检缓存\"}")
        fi
    else
        log_error "CORS预检请求失败，无法测试缓存"
        CORS_RESULTS+=("{\"test\":\"CORS预检缓存\",\"status\":\"FAIL\",\"details\":\"预检请求失败\"}")
    fi
}

# ==============================================================================
# 生成CORS测试报告
# ==============================================================================

generate_cors_report() {
    log_info "生成CORS测试报告..."

    local success_rate=0
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
    fi

    # 生成JSON报告
    cat > "$REPORT_FILE" << EOF
{
    "cors_test_run": {
        "timestamp": "$TIMESTAMP",
        "api_endpoint": "$API_BASE_URL",
        "total_tests": $TOTAL_TESTS,
        "passed": $PASSED_TESTS,
        "failed": $FAILED_TESTS,
        "warnings": $WARNINGS,
        "success_rate": $success_rate
    },
    "cors_test_results": [
        $(IFS=','; echo "${CORS_RESULTS[*]}")
    ],
    "cors_recommendations": [
        $(generate_cors_recommendations)
    ]
}
EOF

    # 生成文本摘要
    local summary_file="${TEST_RESULTS_DIR}/cors_summary_${TIMESTAMP}.txt"
    cat > "$summary_file" << EOF
CORS配置测试报告摘要
====================

测试时间: $(date)
API端点: $API_BASE_URL
总测试数: $TOTAL_TESTS
成功: $PASSED_TESTS
失败: $FAILED_TESTS
警告: $WARNINGS
成功率: ${success_rate}%

详细结果请查看:
- 完整日志: $LOG_FILE
- JSON报告: $REPORT_FILE

EOF

    log ""
    log "=========================================="
    log "            CORS测试完成摘要"
    log "=========================================="
    log "总测试数量: $TOTAL_TESTS"
    log "成功测试: ${GREEN}$PASSED_TESTS${NC}"
    log "失败测试: ${RED}$FAILED_TESTS${NC}"
    log "警告数量: ${YELLOW}$WARNINGS${NC}"
    log "成功率: ${BLUE}${success_rate}%${NC}"
    log ""
    log "CORS报告文件:"
    log "  - 详细日志: $LOG_FILE"
    log "  - JSON报告: $REPORT_FILE"
    log "  - 测试摘要: $summary_file"
    log "=========================================="
}

generate_cors_recommendations() {
    local recommendations=()

    if [[ $FAILED_TESTS -gt 0 ]]; then
        recommendations+=("\"检查并修复失败的CORS配置项\"")
    fi

    if [[ $WARNINGS -gt 0 ]]; then
        recommendations+=("\"优化CORS配置以解决警告项目\"")
    fi

    recommendations+=("\"确保所有生产环境使用的域名都在CORS白名单中\"")
    recommendations+=("\"考虑配置适当的CORS预检缓存时间(Max-Age)\"")
    recommendations+=("\"定期验证CORS配置的安全性\"")
    recommendations+=("\"避免在生产环境使用通配符(*)作为允许来源\"")

    IFS=','
    echo "${recommendations[*]}"
}

# ==============================================================================
# 主执行流程
# ==============================================================================

main() {
    log "=========================================="
    log "        CORS配置专项测试开始"
    log "=========================================="
    log "API端点: $API_BASE_URL"
    log "测试时间: $(date)"
    log "结果目录: $TEST_RESULTS_DIR"
    log ""

    # 执行所有CORS测试
    test_basic_preflight
    test_different_origins
    test_different_methods
    test_different_headers
    test_actual_cors_request
    test_all_endpoints_cors
    test_cors_caching

    # 生成报告
    generate_cors_report

    # 根据测试结果设置退出码
    if [[ $FAILED_TESTS -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# 检查依赖
if ! command -v jq &> /dev/null; then
    echo "警告: 未找到jq命令，部分JSON处理功能可能不可用"
    echo "请安装jq: brew install jq (macOS) 或 apt-get install jq (Ubuntu)"
fi

# 执行主程序
main "$@"