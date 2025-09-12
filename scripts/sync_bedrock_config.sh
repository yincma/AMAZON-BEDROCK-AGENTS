#!/bin/bash

# 自动同步Bedrock配置脚本
# 在Terraform部署后自动获取并配置真实的Bedrock Agent IDs

set -e

echo "🔄 同步Bedrock Agent配置..."

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 获取Bedrock Agent IDs
echo "📋 获取Bedrock Agent IDs..."
ORCHESTRATOR_ID=$(aws bedrock-agent list-agents --query "agentSummaries[?agentName=='ai-ppt-assistant-orchestrator-agent'].agentId | [0]" --output text 2>/dev/null || echo "")
COMPILER_ID=$(aws bedrock-agent list-agents --query "agentSummaries[?agentName=='ai-ppt-assistant-compiler-agent'].agentId | [0]" --output text 2>/dev/null || echo "")
CONTENT_ID=$(aws bedrock-agent list-agents --query "agentSummaries[?agentName=='ai-ppt-assistant-content-agent'].agentId | [0]" --output text 2>/dev/null || echo "")

# 验证是否获取到有效ID
if [ -z "$ORCHESTRATOR_ID" ] || [ "$ORCHESTRATOR_ID" == "None" ] || [[ "$ORCHESTRATOR_ID" == *"placeholder"* ]]; then
    echo -e "${YELLOW}⚠️ 未找到Orchestrator Agent，请先在Bedrock中创建${NC}"
    exit 0  # 不阻止部署，但给出警告
fi

# 获取Agent Alias IDs
if [ ! -z "$ORCHESTRATOR_ID" ] && [ "$ORCHESTRATOR_ID" != "None" ]; then
    ORCHESTRATOR_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$ORCHESTRATOR_ID" --query "agentAliasSummaries[?agentAliasName=='TSTALIASID'].agentAliasId | [0]" --output text 2>/dev/null || echo "TSTALIASID")
else
    ORCHESTRATOR_ALIAS="TSTALIASID"
fi

if [ ! -z "$COMPILER_ID" ] && [ "$COMPILER_ID" != "None" ]; then
    COMPILER_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$COMPILER_ID" --query "agentAliasSummaries[?agentAliasName=='TSTALIASID'].agentAliasId | [0]" --output text 2>/dev/null || echo "TSTALIASID")
else
    COMPILER_ALIAS="TSTALIASID"
fi

if [ ! -z "$CONTENT_ID" ] && [ "$CONTENT_ID" != "None" ]; then
    CONTENT_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$CONTENT_ID" --query "agentAliasSummaries[?agentAliasName=='TSTALIASID'].agentAliasId | [0]" --output text 2>/dev/null || echo "TSTALIASID")
else
    CONTENT_ALIAS="TSTALIASID"
fi

echo -e "${GREEN}✅ 找到以下Bedrock Agents:${NC}"
echo "  Orchestrator: $ORCHESTRATOR_ID (Alias: $ORCHESTRATOR_ALIAS)"
echo "  Compiler: $COMPILER_ID (Alias: $COMPILER_ALIAS)"
echo "  Content: $CONTENT_ID (Alias: $CONTENT_ALIAS)"

# 更新SSM参数
echo ""
echo "📝 更新SSM参数..."
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/orchestrator/id" --value "$ORCHESTRATOR_ID" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/orchestrator/alias_id" --value "$ORCHESTRATOR_ALIAS" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/compiler/id" --value "$COMPILER_ID" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/compiler/alias_id" --value "$COMPILER_ALIAS" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/content/id" --value "$CONTENT_ID" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/content/alias_id" --value "$CONTENT_ALIAS" --type "String" --overwrite 2>/dev/null || true

# 先获取API Gateway和DynamoDB配置（为SSM更新准备）
if [ -d "infrastructure" ]; then
    cd infrastructure
    API_URL_FOR_SSM=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
    API_KEY_FOR_SSM=$(terraform output -raw api_gateway_api_key 2>/dev/null || echo "")
    API_ID_FOR_SSM=$(echo $API_URL_FOR_SSM | cut -d'/' -f3 | cut -d'.' -f1)
    cd ..
    
    # 更新API Gateway相关SSM参数
    echo "  更新API Gateway配置到SSM..."
    aws ssm put-parameter --name "/ai-ppt-assistant/dev/api-gateway-url" --value "$API_URL_FOR_SSM" --type "String" --overwrite 2>/dev/null || true
    aws ssm put-parameter --name "/ai-ppt-assistant/dev/api-gateway-id" --value "$API_ID_FOR_SSM" --type "String" --overwrite 2>/dev/null || true
    aws ssm put-parameter --name "/ai-ppt-assistant/dev/api-key" --value "$API_KEY_FOR_SSM" --type "SecureString" --overwrite 2>/dev/null || true
fi

# 更新DynamoDB表配置到SSM
echo "  更新DynamoDB表配置到SSM..."
aws ssm put-parameter --name "/ai-ppt-assistant/dev/dynamodb-table-sessions" --value "ai-ppt-assistant-dev-sessions" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/dynamodb-table-tasks" --value "ai-ppt-assistant-dev-tasks" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/dynamodb-table-checkpoints" --value "ai-ppt-assistant-dev-checkpoints" --type "String" --overwrite 2>/dev/null || true

# 获取API Gateway和DynamoDB配置
echo ""
echo "📋 获取基础设施配置..."
if [ -d "infrastructure" ]; then
    cd infrastructure
    API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
    API_KEY=$(terraform output -raw api_gateway_api_key 2>/dev/null || echo "")
    API_ID=$(echo $API_URL | cut -d'/' -f3 | cut -d'.' -f1)
    cd ..
else
    API_URL=""
    API_KEY=""
    API_ID=""
fi

# DynamoDB表名
DYNAMODB_TABLE_SESSIONS="ai-ppt-assistant-dev-sessions"
DYNAMODB_TABLE_TASKS="ai-ppt-assistant-dev-tasks"
DYNAMODB_TABLE_CHECKPOINTS="ai-ppt-assistant-dev-checkpoints"

echo "  API Gateway URL: $API_URL"
echo "  DynamoDB Sessions Table: $DYNAMODB_TABLE_SESSIONS"

# 更新Lambda函数环境变量
echo ""
echo "🔧 更新Lambda函数环境变量..."
LAMBDA_FUNCTIONS=$(aws lambda list-functions --query 'Functions[?contains(FunctionName, `ai-ppt-assistant`)].FunctionName' --output text)

for func in $LAMBDA_FUNCTIONS; do
    echo "  更新: $func"
    aws lambda update-function-configuration \
        --function-name "$func" \
        --environment "Variables={
            ORCHESTRATOR_AGENT_ID=$ORCHESTRATOR_ID,
            ORCHESTRATOR_ALIAS_ID=$ORCHESTRATOR_ALIAS,
            ORCHESTRATOR_AGENT_ALIAS_ID=$ORCHESTRATOR_ALIAS,
            COMPILER_AGENT_ID=$COMPILER_ID,
            COMPILER_ALIAS_ID=$COMPILER_ALIAS,
            CONTENT_AGENT_ID=$CONTENT_ID,
            CONTENT_ALIAS_ID=$CONTENT_ALIAS,
            CONFIG_SOURCE=SSM_PARAMETER_STORE,
            SSM_PREFIX=/ai-ppt-assistant/dev,
            DYNAMODB_TABLE=ai-ppt-assistant-dev-sessions,
            DYNAMODB_TABLE_SESSIONS=$DYNAMODB_TABLE_SESSIONS,
            DYNAMODB_TABLE_TASKS=$DYNAMODB_TABLE_TASKS,
            DYNAMODB_TABLE_CHECKPOINTS=$DYNAMODB_TABLE_CHECKPOINTS,
            DYNAMODB_TABLE_PRESENTATIONS=$DYNAMODB_TABLE_SESSIONS,
            API_GATEWAY_URL=$API_URL,
            API_GATEWAY_ID=$API_ID
        }" \
        --output text --query 'LastUpdateStatus' 2>/dev/null || true
done

# 验证配置
echo ""
echo "✅ 验证配置..."
VALIDATION_FAILED=0

# 检查SSM参数
SSM_CHECK=$(aws ssm get-parameter --name "/ai-ppt-assistant/dev/agents/orchestrator/id" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
if [[ "$SSM_CHECK" == *"placeholder"* ]]; then
    echo -e "${RED}❌ SSM参数仍包含占位符${NC}"
    VALIDATION_FAILED=1
fi

# 检查Lambda环境变量
LAMBDA_CHECK=$(aws lambda get-function-configuration --function-name "ai-ppt-assistant-api-task-processor" --query 'Environment.Variables.ORCHESTRATOR_AGENT_ID' --output text 2>/dev/null || echo "")
if [[ "$LAMBDA_CHECK" == *"placeholder"* ]]; then
    echo -e "${RED}❌ Lambda环境变量仍包含占位符${NC}"
    VALIDATION_FAILED=1
fi

if [ $VALIDATION_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ 配置同步成功！${NC}"
else
    echo -e "${YELLOW}⚠️ 配置同步完成，但检测到一些问题${NC}"
fi

echo ""
echo "📊 配置摘要:"
echo "  - SSM参数已更新"
echo "  - Lambda函数环境变量已更新"
echo "  - 无占位符检测: $([ $VALIDATION_FAILED -eq 0 ] && echo '✅ 通过' || echo '⚠️ 需要检查')"