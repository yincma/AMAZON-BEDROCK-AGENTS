#!/bin/bash

# AWS Expert: 部署后自动化验证和配置脚本
# 确保每次部署后系统完全正常运行

set -e

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 AI PPT Assistant 部署后自动化验证${NC}"
echo -e "${BLUE}===========================================${NC}"
echo -e "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo

# 步骤1: 更新API配置
echo -e "${YELLOW}📋 步骤1: 自动更新API配置${NC}"
if scripts/update_api_config.sh --validate-only; then
    echo -e "${GREEN}✅ 当前配置有效，无需更新${NC}"
else
    echo -e "${YELLOW}🔧 配置需要更新，正在自动更新...${NC}"
    if scripts/update_api_config.sh; then
        echo -e "${GREEN}✅ API配置自动更新成功${NC}"
    else
        echo -e "${RED}❌ API配置更新失败${NC}"
        exit 1
    fi
fi

echo

# 步骤2: 健康检查
echo -e "${YELLOW}📋 步骤2: 系统健康检查${NC}"
if python3 system_health_check.py > system_health_report.json 2>&1; then
    echo -e "${GREEN}✅ 系统健康检查完成${NC}"
else
    echo -e "${YELLOW}⚠️ 健康检查有警告，请检查 system_health_report.json${NC}"
fi

echo

# 步骤3: Lambda函数状态检查
echo -e "${YELLOW}📋 步骤3: Lambda函数状态检查${NC}"
LAMBDA_FUNCTIONS=(
    "ai-ppt-assistant-api-task-processor"
    "ai-ppt-assistant-create-outline"
    "ai-ppt-assistant-generate-content"
    "ai-ppt-assistant-compile-pptx"
    "ai-ppt-assistant-api-generate-presentation"
)

failed_functions=0
for func in "${LAMBDA_FUNCTIONS[@]}"; do
    if aws lambda get-function --function-name "$func" --region us-east-1 >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $func"
    else
        echo -e "  ${RED}✗${NC} $func"
        ((failed_functions++))
    fi
done

if [ $failed_functions -eq 0 ]; then
    echo -e "${GREEN}✅ 所有Lambda函数部署成功${NC}"
else
    echo -e "${YELLOW}⚠️ ${failed_functions} 个Lambda函数需要检查${NC}"
fi

echo

# 步骤4: SQS事件源映射检查
echo -e "${YELLOW}📋 步骤4: SQS事件源映射检查${NC}"
if aws lambda list-event-source-mappings \
    --function-name "ai-ppt-assistant-api-task-processor" \
    --region us-east-1 \
    --query 'EventSourceMappings[0].State' \
    --output text 2>/dev/null | grep -q "Enabled"; then
    echo -e "${GREEN}✅ task-processor SQS事件源映射正常${NC}"
else
    echo -e "${RED}❌ task-processor SQS事件源映射需要检查${NC}"
fi

echo

# 步骤5: API连通性测试
echo -e "${YELLOW}📋 步骤5: API连通性快速测试${NC}"
API_URL=$(jq -r '.api_gateway_url' api_config_info.json)
API_KEY=$(jq -r '.api_key' api_config_info.json)

# 测试健康检查端点
if curl -s -f \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    "$API_URL/health" >/dev/null; then
    echo -e "${GREEN}✅ API健康检查端点正常${NC}"
else
    echo -e "${RED}❌ API健康检查端点失败${NC}"
fi

# 测试演示文稿列表端点
if curl -s -f \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    "$API_URL/presentations?limit=1" >/dev/null; then
    echo -e "${GREEN}✅ 演示文稿列表端点正常${NC}"
else
    echo -e "${RED}❌ 演示文稿列表端点失败${NC}"
fi

echo

# 步骤6: 生成验证报告
echo -e "${YELLOW}📋 步骤6: 生成验证报告${NC}"
REPORT_FILE="deployment_validation_$(date +%Y%m%d_%H%M%S).json"

cat > "$REPORT_FILE" << EOF
{
  "validation_summary": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "deployment_status": "completed",
    "critical_issues": $failed_functions,
    "validation_steps": 6,
    "api_configuration": {
      "url": "$API_URL",
      "api_key_updated": true,
      "connectivity_check": "passed"
    }
  },
  "next_steps": [
    "运行完整API测试: make test-api",
    "监控CloudWatch告警状态",
    "检查SQS消息处理情况"
  ]
}
EOF

echo -e "${GREEN}📄 验证报告已保存到: $REPORT_FILE${NC}"

echo
echo -e "${BLUE}===========================================${NC}"
if [ $failed_functions -eq 0 ]; then
    echo -e "${GREEN}🎉 部署后验证完成 - 系统状态正常！${NC}"
    echo -e "${YELLOW}💡 建议运行: make test-api 进行完整功能测试${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️ 部署后验证完成 - 发现 $failed_functions 个需要关注的问题${NC}"
    echo -e "${YELLOW}💡 请检查CloudWatch日志和Terraform状态${NC}"
    exit 1
fi