#!/bin/bash

# 完整配置修复脚本 - 解决所有配置问题
# 包括：DynamoDB表名、API Gateway URL、Bedrock Agent IDs

set -e

echo "🔧 开始完整配置修复..."
echo "================================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置参数
PROJECT_NAME="ai-ppt-assistant"
ENVIRONMENT="dev"
REGION="us-east-1"
SSM_PREFIX="/ai-ppt-assistant/dev"

echo -e "${BLUE}📊 步骤 1/5: 获取当前部署的资源信息${NC}"
echo "----------------------------------------"

# 获取API Gateway信息
cd infrastructure
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
API_KEY=$(terraform output -raw api_gateway_api_key 2>/dev/null || echo "")
API_ID=$(echo $API_URL | cut -d'/' -f3 | cut -d'.' -f1)
cd ..

echo "  API Gateway URL: $API_URL"
echo "  API Gateway ID: $API_ID"
echo "  API Key: ${API_KEY:0:10}..."

# DynamoDB表名
DYNAMODB_TABLE_SESSIONS="${PROJECT_NAME}-${ENVIRONMENT}-sessions"
DYNAMODB_TABLE_TASKS="${PROJECT_NAME}-${ENVIRONMENT}-tasks"
DYNAMODB_TABLE_CHECKPOINTS="${PROJECT_NAME}-${ENVIRONMENT}-checkpoints"

echo "  DynamoDB Tables:"
echo "    - Sessions: $DYNAMODB_TABLE_SESSIONS"
echo "    - Tasks: $DYNAMODB_TABLE_TASKS"
echo "    - Checkpoints: $DYNAMODB_TABLE_CHECKPOINTS"

echo -e "${BLUE}📊 步骤 2/5: 获取Bedrock Agent IDs${NC}"
echo "----------------------------------------"

# 获取Bedrock Agent IDs
ORCHESTRATOR_ID=$(aws bedrock-agent list-agents --query "agentSummaries[?agentName=='${PROJECT_NAME}-orchestrator-agent'].agentId | [0]" --output text 2>/dev/null || echo "")
COMPILER_ID=$(aws bedrock-agent list-agents --query "agentSummaries[?agentName=='${PROJECT_NAME}-compiler-agent'].agentId | [0]" --output text 2>/dev/null || echo "")
CONTENT_ID=$(aws bedrock-agent list-agents --query "agentSummaries[?agentName=='${PROJECT_NAME}-content-agent'].agentId | [0]" --output text 2>/dev/null || echo "")
VISUAL_ID=$(aws bedrock-agent list-agents --query "agentSummaries[?agentName=='${PROJECT_NAME}-visual-agent'].agentId | [0]" --output text 2>/dev/null || echo "")

echo "  Orchestrator Agent: $ORCHESTRATOR_ID"
echo "  Compiler Agent: $COMPILER_ID"
echo "  Content Agent: $CONTENT_ID"
echo "  Visual Agent: $VISUAL_ID"

echo -e "${BLUE}📊 步骤 3/5: 更新SSM参数存储${NC}"
echo "----------------------------------------"

# 更新API Gateway配置
echo "  更新API Gateway URL..."
aws ssm put-parameter \
    --name "${SSM_PREFIX}/api-gateway-url" \
    --value "$API_URL" \
    --type "String" \
    --overwrite \
    --region $REGION >/dev/null 2>&1 || true

echo "  更新API Gateway ID..."
aws ssm put-parameter \
    --name "${SSM_PREFIX}/api-gateway-id" \
    --value "$API_ID" \
    --type "String" \
    --overwrite \
    --region $REGION >/dev/null 2>&1 || true

echo "  更新API Key..."
aws ssm put-parameter \
    --name "${SSM_PREFIX}/api-key" \
    --value "$API_KEY" \
    --type "SecureString" \
    --overwrite \
    --region $REGION >/dev/null 2>&1 || true

# 更新DynamoDB表配置
echo "  更新DynamoDB表配置..."
aws ssm put-parameter \
    --name "${SSM_PREFIX}/dynamodb-table-sessions" \
    --value "$DYNAMODB_TABLE_SESSIONS" \
    --type "String" \
    --overwrite \
    --region $REGION >/dev/null 2>&1 || true

aws ssm put-parameter \
    --name "${SSM_PREFIX}/dynamodb-table-tasks" \
    --value "$DYNAMODB_TABLE_TASKS" \
    --type "String" \
    --overwrite \
    --region $REGION >/dev/null 2>&1 || true

aws ssm put-parameter \
    --name "${SSM_PREFIX}/dynamodb-table-checkpoints" \
    --value "$DYNAMODB_TABLE_CHECKPOINTS" \
    --type "String" \
    --overwrite \
    --region $REGION >/dev/null 2>&1 || true

# 更新Bedrock Agent IDs
if [ ! -z "$ORCHESTRATOR_ID" ] && [ "$ORCHESTRATOR_ID" != "None" ]; then
    echo "  更新Orchestrator Agent ID..."
    aws ssm put-parameter \
        --name "${SSM_PREFIX}/agents/orchestrator/id" \
        --value "$ORCHESTRATOR_ID" \
        --type "String" \
        --overwrite \
        --region $REGION >/dev/null 2>&1 || true
fi

if [ ! -z "$COMPILER_ID" ] && [ "$COMPILER_ID" != "None" ]; then
    echo "  更新Compiler Agent ID..."
    aws ssm put-parameter \
        --name "${SSM_PREFIX}/agents/compiler/id" \
        --value "$COMPILER_ID" \
        --type "String" \
        --overwrite \
        --region $REGION >/dev/null 2>&1 || true
fi

if [ ! -z "$CONTENT_ID" ] && [ "$CONTENT_ID" != "None" ]; then
    echo "  更新Content Agent ID..."
    aws ssm put-parameter \
        --name "${SSM_PREFIX}/agents/content/id" \
        --value "$CONTENT_ID" \
        --type "String" \
        --overwrite \
        --region $REGION >/dev/null 2>&1 || true
fi

echo -e "${GREEN}✅ SSM参数更新完成${NC}"

echo -e "${BLUE}📊 步骤 4/5: 更新Lambda函数环境变量${NC}"
echo "----------------------------------------"

# 获取所有Lambda函数
LAMBDA_FUNCTIONS=$(aws lambda list-functions --query "Functions[?starts_with(FunctionName, '${PROJECT_NAME}')].FunctionName" --output text)

# 更新每个Lambda函数的环境变量
for FUNC in $LAMBDA_FUNCTIONS; do
    echo "  更新函数: $FUNC"
    
    # 获取现有环境变量
    EXISTING_VARS=$(aws lambda get-function-configuration \
        --function-name "$FUNC" \
        --query 'Environment.Variables' \
        --output json 2>/dev/null || echo '{}')
    
    # 构建新的环境变量JSON
    NEW_VARS=$(echo $EXISTING_VARS | python3 -c "
import sys, json
vars = json.load(sys.stdin)

# 添加/更新DynamoDB表名
vars['DYNAMODB_TABLE_SESSIONS'] = '$DYNAMODB_TABLE_SESSIONS'
vars['DYNAMODB_TABLE_TASKS'] = '$DYNAMODB_TABLE_TASKS'
vars['DYNAMODB_TABLE_CHECKPOINTS'] = '$DYNAMODB_TABLE_CHECKPOINTS'
vars['DYNAMODB_TABLE_PRESENTATIONS'] = '$DYNAMODB_TABLE_SESSIONS'  # 兼容旧代码

# 添加/更新API Gateway配置
vars['API_GATEWAY_URL'] = '$API_URL'
vars['API_GATEWAY_ID'] = '$API_ID'

# 添加/更新Bedrock Agent IDs
if '$ORCHESTRATOR_ID' and '$ORCHESTRATOR_ID' != 'None':
    vars['ORCHESTRATOR_AGENT_ID'] = '$ORCHESTRATOR_ID'
if '$COMPILER_ID' and '$COMPILER_ID' != 'None':
    vars['COMPILER_AGENT_ID'] = '$COMPILER_ID'
if '$CONTENT_ID' and '$CONTENT_ID' != 'None':
    vars['CONTENT_AGENT_ID'] = '$CONTENT_ID'

# 添加配置源
vars['CONFIG_SOURCE'] = 'SSM_PARAMETER_STORE'
vars['SSM_PREFIX'] = '$SSM_PREFIX'

# 移除占位符值
keys_to_check = list(vars.keys())
for key in keys_to_check:
    if 'placeholder' in str(vars[key]).lower():
        del vars[key]

print(json.dumps(vars))
")
    
    # 更新Lambda函数配置
    aws lambda update-function-configuration \
        --function-name "$FUNC" \
        --environment "Variables=$NEW_VARS" \
        --region $REGION >/dev/null 2>&1
    
    echo -e "    ${GREEN}✓${NC} $FUNC 更新完成"
done

echo -e "${GREEN}✅ Lambda函数环境变量更新完成${NC}"

echo -e "${BLUE}📊 步骤 5/5: 验证配置${NC}"
echo "----------------------------------------"

# 验证Lambda函数配置
echo "  验证Lambda函数配置..."
VALIDATION_FAILED=0

for FUNC in $LAMBDA_FUNCTIONS; do
    ENV_VARS=$(aws lambda get-function-configuration \
        --function-name "$FUNC" \
        --query 'Environment.Variables' \
        --output json 2>/dev/null || echo '{}')
    
    # 检查是否包含DynamoDB表名
    if ! echo "$ENV_VARS" | grep -q "DYNAMODB_TABLE_SESSIONS"; then
        echo -e "    ${YELLOW}⚠️${NC} $FUNC 缺少DynamoDB表名配置"
        VALIDATION_FAILED=1
    fi
    
    # 检查是否包含占位符
    if echo "$ENV_VARS" | grep -qi "placeholder"; then
        echo -e "    ${RED}❌${NC} $FUNC 包含占位符值"
        VALIDATION_FAILED=1
    fi
done

# 验证SSM参数
echo "  验证SSM参数..."
SSM_API_URL=$(aws ssm get-parameter --name "${SSM_PREFIX}/api-gateway-url" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
if [ "$SSM_API_URL" != "$API_URL" ]; then
    echo -e "    ${RED}❌${NC} SSM中的API URL不匹配"
    VALIDATION_FAILED=1
fi

echo ""
echo "================================"
if [ $VALIDATION_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ 配置修复成功完成！${NC}"
    echo ""
    echo "📋 修复摘要："
    echo "  • 更新了SSM参数中的API Gateway配置"
    echo "  • 添加了DynamoDB表名到所有Lambda函数"
    echo "  • 同步了Bedrock Agent IDs"
    echo "  • 移除了所有占位符值"
else
    echo -e "${YELLOW}⚠️ 配置修复完成，但有一些警告${NC}"
    echo "  请检查上述警告信息"
fi

echo ""
echo "🔍 下一步："
echo "  1. 运行 'python3 test_all_backend_apis.py' 测试API功能"
echo "  2. 如果仍有问题，检查Lambda函数日志"
echo ""
echo "📌 提示："
echo "  • API URL: $API_URL"
echo "  • API Key: $API_KEY"
echo ""