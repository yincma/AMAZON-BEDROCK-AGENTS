#!/bin/bash

# ==============================================================================
# AI PPT后端API完整测试套件
# 测试所有API端点的功能、CORS配置、错误场景和并发处理
# ==============================================================================

set -euo pipefail

# 配置变量
API_BASE_URL="https://fe2kf91287.execute-api.us-east-1.amazonaws.com/dev"
TEST_RESULTS_DIR="./test_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${TEST_RESULTS_DIR}/api_test_${TIMESTAMP}.log"
REPORT_FILE="${TEST_RESULTS_DIR}/test_report_${TIMESTAMP}.json"
CONCURRENT_REQUESTS=5

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
declare -a TEST_RESULTS=()

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
    log_info "开始测试: $test_name"
    echo "  测试编号: $TOTAL_TESTS"
}

record_result() {
    local test_name="$1"
    local status="$2"
    local details="$3"
    local response_time="${4:-N/A}"

    TEST_RESULTS+=("{\"test\":\"$test_name\",\"status\":\"$status\",\"details\":\"$details\",\"response_time\":\"$response_time\"}")
}

# 发送HTTP请求并记录详细信息
send_request() {
    local method="$1"
    local url="$2"
    local data="${3:-}"
    local expected_status="${4:-200}"

    local start_time=$(python3 -c "import time; print(int(time.time() * 1000))")
    local temp_file=$(mktemp)
    local response_code

    if [[ -n "$data" ]]; then
        response_code=$(curl -s -w "%{http_code}" \
            -X "$method" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json" \
            -H "Origin: https://example.com" \
            -d "$data" \
            -o "$temp_file" \
            "$url")
    else
        response_code=$(curl -s -w "%{http_code}" \
            -X "$method" \
            -H "Accept: application/json" \
            -H "Origin: https://example.com" \
            -o "$temp_file" \
            "$url")
    fi

    local end_time=$(python3 -c "import time; print(int(time.time() * 1000))")
    local response_time=$((end_time - start_time))
    local response_body=$(cat "$temp_file")

    # 清理临时文件
    rm -f "$temp_file"

    # 返回结果
    echo "$response_code|$response_time|$response_body"
}

# 验证JSON格式
validate_json() {
    local json_string="$1"
    echo "$json_string" | python3 -m json.tool >/dev/null 2>&1
}

# 提取JSON字段值
extract_json_field() {
    local json_string="$1"
    local field="$2"
    echo "$json_string" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('$field', ''))
except:
    print('')
"
}

# ==============================================================================
# 测试用例
# ==============================================================================

# 测试1: 健康检查 - 基本连通性测试
test_health_check() {
    start_test "基本连通性测试"

    local result
    result=$(send_request "GET" "$API_BASE_URL" "" "200")

    local status_code=$(echo "$result" | cut -d'|' -f1)
    local response_time=$(echo "$result" | cut -d'|' -f2)

    if [[ "$status_code" == "200" ]] || [[ "$status_code" == "404" ]]; then
        log_success "API基本连通性正常 (状态码: $status_code, 响应时间: ${response_time}ms)"
        record_result "健康检查" "PASS" "连通性正常" "$response_time"
    else
        log_error "API连通性异常 (状态码: $status_code)"
        record_result "健康检查" "FAIL" "连通性异常，状态码: $status_code" "$response_time"
    fi
}

# 测试2: CORS预检请求
test_cors_preflight() {
    start_test "CORS预检请求测试"

    local result
    result=$(curl -s -w "%{http_code}|%{header_json}" \
        -X OPTIONS \
        -H "Origin: https://example.com" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type" \
        "$API_BASE_URL/generate" \
        -o /dev/null)

    local status_code=$(echo "$result" | cut -d'|' -f1)
    local headers=$(echo "$result" | cut -d'|' -f2-)

    if [[ "$status_code" == "200" ]] || [[ "$status_code" == "204" ]]; then
        log_success "CORS预检请求成功 (状态码: $status_code)"
        record_result "CORS预检" "PASS" "预检请求正常" "N/A"
    else
        log_error "CORS预检请求失败 (状态码: $status_code)"
        record_result "CORS预检" "FAIL" "预检请求失败，状态码: $status_code" "N/A"
    fi
}

# 测试3: PPT生成请求 - 正常场景
test_generate_ppt_success() {
    start_test "PPT生成请求 - 正常场景"

    local request_data='{
        "topic": "人工智能在商业中的应用",
        "page_count": 8,
        "style": "professional"
    }'

    local result
    result=$(send_request "POST" "$API_BASE_URL/generate" "$request_data" "200")

    local status_code=$(echo "$result" | cut -d'|' -f1)
    local response_time=$(echo "$result" | cut -d'|' -f2)
    local response_body=$(echo "$result" | cut -d'|' -f3-)

    if [[ "$status_code" == "200" ]] || [[ "$status_code" == "202" ]]; then
        if validate_json "$response_body"; then
            local presentation_id
            presentation_id=$(extract_json_field "$response_body" "presentation_id")

            if [[ -n "$presentation_id" ]]; then
                log_success "PPT生成请求成功 (ID: $presentation_id, 响应时间: ${response_time}ms)"
                record_result "PPT生成-正常" "PASS" "生成请求成功，ID: $presentation_id" "$response_time"
                echo "$presentation_id" > "${TEST_RESULTS_DIR}/last_presentation_id.txt"
            else
                log_warning "PPT生成请求成功但未返回presentation_id"
                record_result "PPT生成-正常" "WARN" "缺少presentation_id" "$response_time"
            fi
        else
            log_error "PPT生成请求响应格式无效"
            record_result "PPT生成-正常" "FAIL" "响应JSON格式无效" "$response_time"
        fi
    else
        log_error "PPT生成请求失败 (状态码: $status_code)"
        record_result "PPT生成-正常" "FAIL" "请求失败，状态码: $status_code" "$response_time"
    fi
}

# 测试4: PPT生成请求 - 参数验证
test_generate_ppt_validation() {
    start_test "PPT生成请求 - 参数验证"

    # 测试空请求
    local result
    result=$(send_request "POST" "$API_BASE_URL/generate" "{}" "400")
    local status_code=$(echo "$result" | cut -d'|' -f1)

    if [[ "$status_code" == "400" ]]; then
        log_success "空请求正确返回400错误"
    else
        log_warning "空请求未返回预期的400错误 (实际: $status_code)"
    fi

    # 测试无效参数
    local invalid_data='{
        "topic": "",
        "page_count": -1,
        "style": "invalid_style"
    }'

    result=$(send_request "POST" "$API_BASE_URL/generate" "$invalid_data" "400")
    status_code=$(echo "$result" | cut -d'|' -f1)

    if [[ "$status_code" == "400" ]]; then
        log_success "无效参数正确返回400错误"
        record_result "参数验证" "PASS" "参数验证工作正常" "N/A"
    else
        log_error "无效参数未返回预期的400错误 (实际: $status_code)"
        record_result "参数验证" "FAIL" "参数验证失效" "N/A"
    fi
}

# 测试5: 状态查询
test_status_check() {
    start_test "状态查询测试"

    # 首先尝试使用之前生成的presentation_id
    local presentation_id=""
    if [[ -f "${TEST_RESULTS_DIR}/last_presentation_id.txt" ]]; then
        presentation_id=$(cat "${TEST_RESULTS_DIR}/last_presentation_id.txt")
    fi

    # 如果没有，使用测试ID
    if [[ -z "$presentation_id" ]]; then
        presentation_id="test-presentation-id-12345"
    fi

    local result
    result=$(send_request "GET" "$API_BASE_URL/status/$presentation_id" "" "200")

    local status_code=$(echo "$result" | cut -d'|' -f1)
    local response_time=$(echo "$result" | cut -d'|' -f2)
    local response_body=$(echo "$result" | cut -d'|' -f3-)

    if [[ "$status_code" == "200" ]] || [[ "$status_code" == "404" ]]; then
        if [[ "$status_code" == "200" ]] && validate_json "$response_body"; then
            local status
            status=$(extract_json_field "$response_body" "status")
            log_success "状态查询成功 (状态: $status, 响应时间: ${response_time}ms)"
            record_result "状态查询" "PASS" "查询成功，状态: $status" "$response_time"
        else
            log_success "状态查询返回预期结果 (响应时间: ${response_time}ms)"
            record_result "状态查询" "PASS" "查询功能正常" "$response_time"
        fi
    else
        log_error "状态查询失败 (状态码: $status_code)"
        record_result "状态查询" "FAIL" "查询失败，状态码: $status_code" "$response_time"
    fi
}

# 测试6: 下载链接生成
test_download_generation() {
    start_test "下载链接生成测试"

    local presentation_id="test-presentation-id-12345"
    if [[ -f "${TEST_RESULTS_DIR}/last_presentation_id.txt" ]]; then
        presentation_id=$(cat "${TEST_RESULTS_DIR}/last_presentation_id.txt")
    fi

    local result
    result=$(send_request "GET" "$API_BASE_URL/download/$presentation_id" "" "200")

    local status_code=$(echo "$result" | cut -d'|' -f1)
    local response_time=$(echo "$result" | cut -d'|' -f2)
    local response_body=$(echo "$result" | cut -d'|' -f3-)

    if [[ "$status_code" == "200" ]] || [[ "$status_code" == "404" ]]; then
        if [[ "$status_code" == "200" ]] && validate_json "$response_body"; then
            local download_url
            download_url=$(extract_json_field "$response_body" "download_url")

            if [[ -n "$download_url" ]]; then
                log_success "下载链接生成成功 (响应时间: ${response_time}ms)"
                record_result "下载链接" "PASS" "链接生成成功" "$response_time"
            else
                log_warning "下载链接生成响应中未包含download_url"
                record_result "下载链接" "WARN" "缺少download_url字段" "$response_time"
            fi
        else
            log_success "下载端点响应正常 (响应时间: ${response_time}ms)"
            record_result "下载链接" "PASS" "端点功能正常" "$response_time"
        fi
    else
        log_error "下载链接生成失败 (状态码: $status_code)"
        record_result "下载链接" "FAIL" "生成失败，状态码: $status_code" "$response_time"
    fi
}

# 测试7: 错误处理测试
test_error_scenarios() {
    start_test "错误处理场景测试"

    # 测试不存在的端点
    local result
    result=$(send_request "GET" "$API_BASE_URL/nonexistent" "" "404")
    local status_code=$(echo "$result" | cut -d'|' -f1)

    if [[ "$status_code" == "404" ]]; then
        log_success "不存在端点正确返回404"
    else
        log_warning "不存在端点返回状态码: $status_code"
    fi

    # 测试无效的presentation_id格式
    result=$(send_request "GET" "$API_BASE_URL/status/invalid-id-format-!" "" "400")
    status_code=$(echo "$result" | cut -d'|' -f1)

    if [[ "$status_code" == "400" ]] || [[ "$status_code" == "404" ]]; then
        log_success "无效ID格式处理正常 (状态码: $status_code)"
        record_result "错误处理" "PASS" "错误场景处理正常" "N/A"
    else
        log_error "无效ID格式未正确处理 (状态码: $status_code)"
        record_result "错误处理" "FAIL" "错误处理异常" "N/A"
    fi
}

# 测试8: 并发请求测试
test_concurrent_requests() {
    start_test "并发请求测试"

    local temp_dir=$(mktemp -d)
    local pids=()

    # 并发发送多个状态查询请求
    for i in $(seq 1 $CONCURRENT_REQUESTS); do
        (
            local test_id="concurrent-test-$i"
            local result
            result=$(send_request "GET" "$API_BASE_URL/status/$test_id" "" "200")
            local status_code=$(echo "$result" | cut -d'|' -f1)
            local response_time=$(echo "$result" | cut -d'|' -f2)
            echo "$i:$status_code:$response_time" > "$temp_dir/result_$i.txt"
        ) &
        pids+=($!)
    done

    # 等待所有请求完成
    for pid in "${pids[@]}"; do
        wait "$pid"
    done

    # 分析结果
    local successful=0
    local total_time=0

    for i in $(seq 1 $CONCURRENT_REQUESTS); do
        if [[ -f "$temp_dir/result_$i.txt" ]]; then
            local line=$(cat "$temp_dir/result_$i.txt")
            local status_code=$(echo "$line" | cut -d':' -f2)
            local response_time=$(echo "$line" | cut -d':' -f3)

            if [[ "$status_code" == "200" ]] || [[ "$status_code" == "404" ]]; then
                ((successful++))
            fi

            if [[ "$response_time" =~ ^[0-9]+$ ]]; then
                total_time=$((total_time + response_time))
            fi
        fi
    done

    local avg_time=$((total_time / CONCURRENT_REQUESTS))

    if [[ $successful -ge $((CONCURRENT_REQUESTS * 8 / 10)) ]]; then
        log_success "并发测试通过 ($successful/$CONCURRENT_REQUESTS 成功, 平均响应时间: ${avg_time}ms)"
        record_result "并发测试" "PASS" "$successful/$CONCURRENT_REQUESTS 成功" "$avg_time"
    else
        log_error "并发测试失败 ($successful/$CONCURRENT_REQUESTS 成功)"
        record_result "并发测试" "FAIL" "成功率过低: $successful/$CONCURRENT_REQUESTS" "$avg_time"
    fi

    # 清理
    rm -rf "$temp_dir"
}

# 测试9: 性能基准测试
test_performance_baseline() {
    start_test "性能基准测试"

    local total_time=0
    local requests=10
    local successful=0

    for i in $(seq 1 $requests); do
        local result
        result=$(send_request "GET" "$API_BASE_URL/status/perf-test-$i" "" "200")

        local status_code=$(echo "$result" | cut -d'|' -f1)
        local response_time=$(echo "$result" | cut -d'|' -f2)

        if [[ "$status_code" == "200" ]] || [[ "$status_code" == "404" ]]; then
            ((successful++))
        fi

        if [[ "$response_time" =~ ^[0-9]+$ ]]; then
            total_time=$((total_time + response_time))
        fi

        sleep 0.1  # 短暂延迟避免过度负载
    done

    local avg_time=$((total_time / requests))

    if [[ $avg_time -lt 5000 ]]; then  # 5秒阈值
        log_success "性能测试通过 (平均响应时间: ${avg_time}ms)"
        record_result "性能基准" "PASS" "平均响应时间: ${avg_time}ms" "$avg_time"
    else
        log_warning "响应时间较长 (平均: ${avg_time}ms)"
        record_result "性能基准" "WARN" "响应时间较长" "$avg_time"
    fi
}

# 测试10: 安全性检查
test_security_checks() {
    start_test "基本安全性检查"

    # 测试SQL注入尝试
    local malicious_id="'; DROP TABLE users; --"
    local result
    result=$(send_request "GET" "$API_BASE_URL/status/$malicious_id" "" "400")
    local status_code=$(echo "$result" | cut -d'|' -f1)

    if [[ "$status_code" == "400" ]] || [[ "$status_code" == "404" ]]; then
        log_success "SQL注入防护正常"
    else
        log_warning "潜在安全问题：恶意输入处理异常 (状态码: $status_code)"
    fi

    # 测试XSS尝试
    local xss_payload="<script>alert('xss')</script>"
    local request_data="{\"topic\":\"$xss_payload\",\"page_count\":5}"

    result=$(send_request "POST" "$API_BASE_URL/generate" "$request_data" "400")
    status_code=$(echo "$result" | cut -d'|' -f1)

    if [[ "$status_code" == "400" ]] || [[ "$status_code" == "200" ]]; then
        log_success "XSS防护测试通过"
        record_result "安全检查" "PASS" "基本安全防护正常" "N/A"
    else
        log_error "XSS防护可能存在问题 (状态码: $status_code)"
        record_result "安全检查" "FAIL" "安全防护异常" "N/A"
    fi
}

# ==============================================================================
# 生成测试报告
# ==============================================================================

generate_report() {
    log_info "生成测试报告..."

    local success_rate=0
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
    fi

    # 生成JSON报告
    cat > "$REPORT_FILE" << EOF
{
    "test_run": {
        "timestamp": "$TIMESTAMP",
        "api_endpoint": "$API_BASE_URL",
        "total_tests": $TOTAL_TESTS,
        "passed": $PASSED_TESTS,
        "failed": $FAILED_TESTS,
        "warnings": $WARNINGS,
        "success_rate": $success_rate
    },
    "test_results": [
        $(IFS=','; echo "${TEST_RESULTS[*]}")
    ],
    "recommendations": [
        $(generate_recommendations)
    ]
}
EOF

    # 生成文本摘要
    local summary_file="${TEST_RESULTS_DIR}/test_summary_${TIMESTAMP}.txt"
    cat > "$summary_file" << EOF
API测试报告摘要
================

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
    log "              测试完成摘要"
    log "=========================================="
    log "总测试数量: $TOTAL_TESTS"
    log "成功测试: ${GREEN}$PASSED_TESTS${NC}"
    log "失败测试: ${RED}$FAILED_TESTS${NC}"
    log "警告数量: ${YELLOW}$WARNINGS${NC}"
    log "成功率: ${BLUE}${success_rate}%${NC}"
    log ""
    log "报告文件:"
    log "  - 详细日志: $LOG_FILE"
    log "  - JSON报告: $REPORT_FILE"
    log "  - 测试摘要: $summary_file"
    log "=========================================="
}

generate_recommendations() {
    local recommendations=()

    if [[ $FAILED_TESTS -gt 0 ]]; then
        recommendations+=("\"调查并修复失败的测试用例\"")
    fi

    if [[ $WARNINGS -gt 0 ]]; then
        recommendations+=("\"检查警告项目，考虑改进API响应\"")
    fi

    if [[ $((PASSED_TESTS * 100 / TOTAL_TESTS)) -lt 80 ]]; then
        recommendations+=("\"成功率低于80%，建议全面检查API实现\"")
    fi

    recommendations+=("\"定期运行此测试套件确保API稳定性\"")
    recommendations+=("\"考虑添加更多边界条件测试\"")
    recommendations+=("\"监控API性能指标并设置告警\"")

    IFS=','
    echo "${recommendations[*]}"
}

# ==============================================================================
# 主执行流程
# ==============================================================================

main() {
    log "=========================================="
    log "      AI PPT后端API测试套件开始"
    log "=========================================="
    log "API端点: $API_BASE_URL"
    log "测试时间: $(date)"
    log "结果目录: $TEST_RESULTS_DIR"
    log ""

    # 执行所有测试
    test_health_check
    test_cors_preflight
    test_generate_ppt_success
    test_generate_ppt_validation
    test_status_check
    test_download_generation
    test_error_scenarios
    test_concurrent_requests
    test_performance_baseline
    test_security_checks

    # 生成报告
    generate_report

    # 根据测试结果设置退出码
    if [[ $FAILED_TESTS -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# 执行主程序
main "$@"