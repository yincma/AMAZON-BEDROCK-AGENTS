#!/bin/bash

# 智能Bedrock配置同步脚本
# 自动处理Agent不存在的情况，创建占位Agent或使用模拟模式

set -e

echo "🤖 智能Bedrock Agent配置同步..."

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 配置模式：real（真实Agent）或 mock（模拟模式）
CONFIG_MODE="real"

# 检查是否存在Bedrock Agents
echo "📋 检查Bedrock Agents..."
ORCHESTRATOR_ID=$(aws bedrock-agent list-agents --query "agentSummaries[?agentName=='ai-ppt-assistant-orchestrator-agent'].agentId | [0]" --output text 2>/dev/null || echo "")
COMPILER_ID=$(aws bedrock-agent list-agents --query "agentSummaries[?agentName=='ai-ppt-assistant-compiler-agent'].agentId | [0]" --output text 2>/dev/null || echo "")
CONTENT_ID=$(aws bedrock-agent list-agents --query "agentSummaries[?agentName=='ai-ppt-assistant-content-agent'].agentId | [0]" --output text 2>/dev/null || echo "")

# 如果没有找到Agent，使用模拟模式
if [ -z "$ORCHESTRATOR_ID" ] || [ "$ORCHESTRATOR_ID" == "None" ]; then
    echo -e "${YELLOW}⚠️ 未找到Bedrock Agents，启用模拟模式${NC}"
    CONFIG_MODE="mock"
    
    # 使用固定的模拟ID（这些ID会在Lambda中被识别为模拟模式）
    ORCHESTRATOR_ID="MOCK-ORCHESTRATOR-001"
    COMPILER_ID="MOCK-COMPILER-001"
    CONTENT_ID="MOCK-CONTENT-001"
    ORCHESTRATOR_ALIAS="MOCK-ALIAS"
    COMPILER_ALIAS="MOCK-ALIAS"
    CONTENT_ALIAS="MOCK-ALIAS"
else
    echo -e "${GREEN}✅ 找到真实Bedrock Agents${NC}"
    
    # 获取真实的Alias IDs
    ORCHESTRATOR_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$ORCHESTRATOR_ID" --query "agentAliasSummaries[0].agentAliasId" --output text 2>/dev/null || echo "TSTALIASID")
    COMPILER_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$COMPILER_ID" --query "agentAliasSummaries[0].agentAliasId" --output text 2>/dev/null || echo "TSTALIASID")
    CONTENT_ALIAS=$(aws bedrock-agent list-agent-aliases --agent-id "$CONTENT_ID" --query "agentAliasSummaries[0].agentAliasId" --output text 2>/dev/null || echo "TSTALIASID")
fi

echo "📊 当前配置模式: $CONFIG_MODE"
echo "  Orchestrator: $ORCHESTRATOR_ID (Alias: $ORCHESTRATOR_ALIAS)"
echo "  Compiler: $COMPILER_ID (Alias: $COMPILER_ALIAS)"
echo "  Content: $CONTENT_ID (Alias: $CONTENT_ALIAS)"

# 更新SSM参数
echo ""
echo "📝 更新SSM参数..."
aws ssm put-parameter --name "/ai-ppt-assistant/dev/config-mode" --value "$CONFIG_MODE" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/orchestrator/id" --value "$ORCHESTRATOR_ID" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/orchestrator/alias_id" --value "$ORCHESTRATOR_ALIAS" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/compiler/id" --value "$COMPILER_ID" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/compiler/alias_id" --value "$COMPILER_ALIAS" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/content/id" --value "$CONTENT_ID" --type "String" --overwrite 2>/dev/null || true
aws ssm put-parameter --name "/ai-ppt-assistant/dev/agents/content/alias_id" --value "$CONTENT_ALIAS" --type "String" --overwrite 2>/dev/null || true

# 获取基础设施配置
echo ""
echo "📋 获取基础设施配置..."
if [ -d "infrastructure" ]; then
    cd infrastructure
    API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
    API_KEY=$(terraform output -raw api_gateway_api_key 2>/dev/null || echo "")
    cd ..
fi

# 更新Lambda函数环境变量
echo ""
echo "🔧 更新Lambda函数环境变量..."
LAMBDA_FUNCTIONS=$(aws lambda list-functions --query 'Functions[?contains(FunctionName, `ai-ppt-assistant`)].FunctionName' --output text)

for func in $LAMBDA_FUNCTIONS; do
    echo "  更新: $func"
    aws lambda update-function-configuration \
        --function-name "$func" \
        --environment "Variables={
            CONFIG_MODE=$CONFIG_MODE,
            BEDROCK_AGENT_ID=$ORCHESTRATOR_ID,
            BEDROCK_AGENT_ALIAS_ID=$ORCHESTRATOR_ALIAS,
            ORCHESTRATOR_AGENT_ID=$ORCHESTRATOR_ID,
            ORCHESTRATOR_ALIAS_ID=$ORCHESTRATOR_ALIAS,
            COMPILER_AGENT_ID=$COMPILER_ID,
            COMPILER_ALIAS_ID=$COMPILER_ALIAS,
            CONTENT_AGENT_ID=$CONTENT_ID,
            CONTENT_ALIAS_ID=$CONTENT_ALIAS,
            DYNAMODB_TABLE=ai-ppt-assistant-dev-sessions,
            DYNAMODB_TABLE_NAME=ai-ppt-assistant-dev-sessions,
            DYNAMODB_SESSIONS_TABLE=ai-ppt-assistant-dev-sessions,
            DYNAMODB_TASKS_TABLE=ai-ppt-assistant-dev-tasks,
            DYNAMODB_CHECKPOINTS_TABLE=ai-ppt-assistant-dev-checkpoints,
            SSM_PREFIX=/ai-ppt-assistant/dev
        }" \
        --output text --query 'LastUpdateStatus' 2>/dev/null || true
done

# 如果是模拟模式，创建Lambda函数的模拟处理器
if [ "$CONFIG_MODE" == "mock" ]; then
    echo ""
    echo -e "${YELLOW}📝 配置模拟模式处理...${NC}"
    
    # 创建模拟响应配置
    cat > /tmp/mock_config.json <<EOF
{
    "mode": "mock",
    "message": "System running in mock mode - Bedrock Agents not configured",
    "mock_responses": {
        "create_outline": {
            "slides": [
                {"title": "Introduction", "content": "Mock introduction content"},
                {"title": "Main Topic", "content": "Mock main content"},
                {"title": "Conclusion", "content": "Mock conclusion"}
            ]
        },
        "generate_content": {
            "content": "This is mock generated content for testing purposes."
        }
    }
}
EOF
    
    # 上传模拟配置到S3
    aws s3 cp /tmp/mock_config.json s3://ai-ppt-assistant-dev-resources/config/mock_config.json 2>/dev/null || true
    rm /tmp/mock_config.json
    
    echo -e "${YELLOW}⚠️ 系统配置为模拟模式 - PPT生成将使用模拟数据${NC}"
    echo -e "${YELLOW}💡 要使用真实功能，请在AWS Bedrock控制台创建所需的Agents${NC}"
fi

echo ""
if [ "$CONFIG_MODE" == "real" ]; then
    echo -e "${GREEN}✅ 配置同步成功！系统使用真实Bedrock Agents${NC}"
else
    echo -e "${YELLOW}✅ 配置同步成功！系统运行在模拟模式${NC}"
    echo ""
    echo "要启用真实功能，请："
    echo "1. 在AWS Bedrock控制台创建以下Agents："
    echo "   - ai-ppt-assistant-orchestrator-agent"
    echo "   - ai-ppt-assistant-compiler-agent"
    echo "   - ai-ppt-assistant-content-agent"
    echo "2. 重新运行: make sync-config"
fi

# 创建配置状态文件
cat > .bedrock_config_status <<EOF
CONFIG_MODE=$CONFIG_MODE
LAST_SYNC=$(date +"%Y-%m-%d %H:%M:%S")
ORCHESTRATOR_ID=$ORCHESTRATOR_ID
COMPILER_ID=$COMPILER_ID
CONTENT_ID=$CONTENT_ID
EOF

echo ""
echo "📊 配置状态已保存到 .bedrock_config_status"