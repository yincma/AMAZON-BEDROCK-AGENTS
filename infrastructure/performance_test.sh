#!/bin/bash

# Lambda和API Gateway性能测试脚本
# 用于验证性能优化效果

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
API_GATEWAY_URL=""
TEST_DURATION=60  # 测试持续时间（秒）
CONCURRENT_USERS=10  # 并发用户数

# 函数：打印帮助信息
show_help() {
    echo "使用方法: ./performance_test.sh -u <API_GATEWAY_URL> [选项]"
    echo ""
    echo "选项:"
    echo "  -u URL    API Gateway URL（必需）"
    echo "  -d SEC    测试持续时间（默认: 60秒）"
    echo "  -c NUM    并发用户数（默认: 10）"
    echo "  -h        显示帮助信息"
    echo ""
    echo "示例:"
    echo "  ./performance_test.sh -u https://xxx.execute-api.us-east-1.amazonaws.com/dev"
    echo "  ./performance_test.sh -u https://xxx.execute-api.us-east-1.amazonaws.com/dev -d 120 -c 20"
}

# 解析命令行参数
while getopts "u:d:c:h" opt; do
    case $opt in
        u) API_GATEWAY_URL="$OPTARG" ;;
        d) TEST_DURATION="$OPTARG" ;;
        c) CONCURRENT_USERS="$OPTARG" ;;
        h) show_help; exit 0 ;;
        \?) echo "无效选项: -$OPTARG" >&2; exit 1 ;;
    esac
done

# 检查必需参数
if [ -z "$API_GATEWAY_URL" ]; then
    echo -e "${RED}错误: 必须提供API Gateway URL${NC}"
    show_help
    exit 1
fi

# 检查依赖工具
check_dependencies() {
    echo -e "${YELLOW}检查依赖工具...${NC}"

    # 检查curl
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}错误: curl未安装${NC}"
        exit 1
    fi

    # 检查jq
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}警告: jq未安装，安装jq以获得更好的JSON解析${NC}"
        echo "安装命令: brew install jq (macOS) 或 apt-get install jq (Linux)"
    fi

    # 检查Apache Bench (ab)
    if ! command -v ab &> /dev/null; then
        echo -e "${YELLOW}警告: Apache Bench (ab)未安装，跳过负载测试${NC}"
        echo "安装命令: apt-get install apache2-utils (Linux) 或 brew install httpd (macOS)"
    fi

    echo -e "${GREEN}依赖检查完成${NC}"
}

# 测试1: 冷启动测试
test_cold_start() {
    echo -e "\n${YELLOW}=== 测试1: Lambda冷启动时间 ===${NC}"
    echo "测试说明: 每次请求间隔60秒，让Lambda容器回收，测试冷启动"

    TOTAL_TIME=0
    COUNT=5

    for i in $(seq 1 $COUNT); do
        echo -n "测试 $i/$COUNT: "

        # 使用time命令测量请求时间
        START=$(date +%s%N)
        RESPONSE=$(curl -s -w "\n%{http_code}" "${API_GATEWAY_URL}/status/test-${i}")
        END=$(date +%s%N)

        # 计算响应时间（毫秒）
        DURATION=$((($END - $START) / 1000000))
        TOTAL_TIME=$((TOTAL_TIME + DURATION))

        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "${GREEN}成功${NC} - 响应时间: ${DURATION}ms"
        else
            echo -e "${RED}失败${NC} - HTTP状态码: $HTTP_CODE"
        fi

        # 等待60秒让容器回收
        if [ $i -lt $COUNT ]; then
            echo "等待60秒..."
            sleep 60
        fi
    done

    AVG_TIME=$((TOTAL_TIME / COUNT))
    echo -e "${GREEN}平均冷启动时间: ${AVG_TIME}ms${NC}"
}

# 测试2: 热启动测试
test_warm_start() {
    echo -e "\n${YELLOW}=== 测试2: Lambda热启动时间 ===${NC}"
    echo "测试说明: 连续快速请求，测试容器复用时的响应时间"

    TOTAL_TIME=0
    COUNT=10

    for i in $(seq 1 $COUNT); do
        echo -n "测试 $i/$COUNT: "

        START=$(date +%s%N)
        RESPONSE=$(curl -s -w "\n%{http_code}" "${API_GATEWAY_URL}/status/test-warm-${i}")
        END=$(date +%s%N)

        DURATION=$((($END - $START) / 1000000))
        TOTAL_TIME=$((TOTAL_TIME + DURATION))

        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "${GREEN}成功${NC} - 响应时间: ${DURATION}ms"
        else
            echo -e "${RED}失败${NC} - HTTP状态码: $HTTP_CODE"
        fi

        # 短暂延迟
        sleep 0.5
    done

    AVG_TIME=$((TOTAL_TIME / COUNT))
    echo -e "${GREEN}平均热启动时间: ${AVG_TIME}ms${NC}"
}

# 测试3: API缓存测试
test_api_cache() {
    echo -e "\n${YELLOW}=== 测试3: API Gateway缓存效果 ===${NC}"
    echo "测试说明: 重复请求相同资源，测试缓存命中率"

    TEST_ID="cache-test-$(date +%s)"

    # 第一次请求（缓存未命中）
    echo -n "首次请求（缓存未命中）: "
    START=$(date +%s%N)
    curl -s "${API_GATEWAY_URL}/status/${TEST_ID}" > /dev/null
    END=$(date +%s%N)
    FIRST_DURATION=$((($END - $START) / 1000000))
    echo "${FIRST_DURATION}ms"

    # 等待1秒
    sleep 1

    # 第二次请求（应该缓存命中）
    echo -n "第二次请求（缓存命中）: "
    START=$(date +%s%N)
    curl -s "${API_GATEWAY_URL}/status/${TEST_ID}" > /dev/null
    END=$(date +%s%N)
    SECOND_DURATION=$((($END - $START) / 1000000))
    echo "${SECOND_DURATION}ms"

    # 计算缓存效果
    if [ $SECOND_DURATION -lt $FIRST_DURATION ]; then
        IMPROVEMENT=$(( ($FIRST_DURATION - $SECOND_DURATION) * 100 / $FIRST_DURATION ))
        echo -e "${GREEN}缓存生效！性能提升: ${IMPROVEMENT}%${NC}"
    else
        echo -e "${YELLOW}缓存可能未生效${NC}"
    fi
}

# 测试4: 负载测试
test_load() {
    echo -e "\n${YELLOW}=== 测试4: 负载测试 ===${NC}"
    echo "测试说明: 模拟${CONCURRENT_USERS}个并发用户，持续${TEST_DURATION}秒"

    if ! command -v ab &> /dev/null; then
        echo -e "${YELLOW}跳过: Apache Bench未安装${NC}"
        return
    fi

    # 创建测试数据
    TEST_DATA='{"topic": "Performance Test", "pages": 5}'
    echo "$TEST_DATA" > /tmp/test_data.json

    echo "执行负载测试..."
    ab -n 100 -c $CONCURRENT_USERS -T 'application/json' -p /tmp/test_data.json \
       "${API_GATEWAY_URL}/generate" 2>&1 | grep -E "Requests per second:|Time per request:|Failed requests:|Percentage of the requests"

    # 清理临时文件
    rm -f /tmp/test_data.json
}

# 测试5: PPT生成性能测试
test_ppt_generation() {
    echo -e "\n${YELLOW}=== 测试5: PPT生成性能测试 ===${NC}"
    echo "测试说明: 测试完整的PPT生成流程"

    # 准备测试数据
    TEST_DATA='{
        "topic": "性能测试报告",
        "pages": 5,
        "style": "professional",
        "language": "zh"
    }'

    echo "发送PPT生成请求..."
    START=$(date +%s)

    RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$TEST_DATA" \
        "${API_GATEWAY_URL}/generate")

    # 提取presentation_id
    if command -v jq &> /dev/null; then
        PRESENTATION_ID=$(echo "$RESPONSE" | jq -r '.presentation_id')
    else
        # 简单的字符串提取（不够可靠）
        PRESENTATION_ID=$(echo "$RESPONSE" | grep -o '"presentation_id":"[^"]*' | cut -d'"' -f4)
    fi

    if [ -z "$PRESENTATION_ID" ] || [ "$PRESENTATION_ID" = "null" ]; then
        echo -e "${RED}生成请求失败${NC}"
        echo "响应: $RESPONSE"
        return
    fi

    echo "Presentation ID: $PRESENTATION_ID"
    echo "轮询状态..."

    # 轮询状态直到完成
    MAX_ATTEMPTS=60
    ATTEMPT=0

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        ATTEMPT=$((ATTEMPT + 1))

        STATUS_RESPONSE=$(curl -s "${API_GATEWAY_URL}/status/${PRESENTATION_ID}")

        if command -v jq &> /dev/null; then
            STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status')
        else
            STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
        fi

        echo -n "."

        if [ "$STATUS" = "completed" ]; then
            END=$(date +%s)
            DURATION=$((END - START))
            echo -e "\n${GREEN}PPT生成成功！总耗时: ${DURATION}秒${NC}"

            # 测试下载
            echo "测试下载链接..."
            curl -s -I "${API_GATEWAY_URL}/download/${PRESENTATION_ID}" | head -n1
            break
        elif [ "$STATUS" = "failed" ]; then
            echo -e "\n${RED}PPT生成失败${NC}"
            break
        fi

        sleep 2
    done

    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo -e "\n${YELLOW}超时：PPT生成时间过长${NC}"
    fi
}

# 生成测试报告
generate_report() {
    echo -e "\n${YELLOW}=== 性能测试报告 ===${NC}"
    echo "测试时间: $(date)"
    echo "API Gateway URL: $API_GATEWAY_URL"
    echo "并发用户数: $CONCURRENT_USERS"
    echo "测试持续时间: ${TEST_DURATION}秒"
    echo ""
    echo "建议："
    echo "1. 如果冷启动时间 > 2秒，考虑启用预配置并发"
    echo "2. 如果缓存未生效，检查API Gateway缓存配置"
    echo "3. 如果负载测试失败率高，考虑增加Lambda预留并发"
    echo "4. 如果PPT生成时间 > 60秒，考虑增加Lambda内存配置"
}

# 主函数
main() {
    echo -e "${GREEN}=== Lambda和API Gateway性能测试工具 ===${NC}"
    echo "API Gateway URL: $API_GATEWAY_URL"
    echo ""

    # 检查依赖
    check_dependencies

    # 执行测试
    test_cold_start
    test_warm_start
    test_api_cache
    test_load
    test_ppt_generation

    # 生成报告
    generate_report

    echo -e "\n${GREEN}测试完成！${NC}"
}

# 执行主函数
main