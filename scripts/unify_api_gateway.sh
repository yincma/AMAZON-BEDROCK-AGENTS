#!/bin/bash
# unify_api_gateway.sh - 统一API Gateway配置
# 只保留一个API和一个Stage，确保配置一致性

set -e

# 配置
REGION="us-east-1"
PROJECT="ai-ppt-assistant"
ENVIRONMENT="dev"
PRIMARY_STAGE="dev"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}API Gateway 统一配置脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI未安装${NC}"
    exit 1
fi

# 获取账户信息
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}📍 AWS账户: $ACCOUNT_ID${NC}"
echo -e "${GREEN}📍 区域: $REGION${NC}"
echo ""

# 步骤1: 分析现有API Gateway
echo -e "${YELLOW}步骤1: 分析现有API Gateway...${NC}"

# 获取所有API
APIS=$(aws apigateway get-rest-apis --region $REGION --query 'items[*].[id,name,createdDate]' --output json)

echo "现有API列表:"
echo "$APIS" | jq -r '.[] | "\(.0)\t\(.1)\t\(.2)"' | column -t -s $'\t'
echo ""

# 查找项目相关的API
PROJECT_APIS=$(aws apigateway get-rest-apis \
  --region $REGION \
  --query "items[?contains(name, '$PROJECT')].[id,name]" \
  --output json)

API_COUNT=$(echo "$PROJECT_APIS" | jq 'length')

if [ "$API_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ 未找到项目相关的API Gateway${NC}"
    exit 1
elif [ "$API_COUNT" -eq 1 ]; then
    PRIMARY_API_ID=$(echo "$PROJECT_APIS" | jq -r '.[0][0]')
    PRIMARY_API_NAME=$(echo "$PROJECT_APIS" | jq -r '.[0][1]')
    echo -e "${GREEN}✅ 找到唯一的项目API: $PRIMARY_API_NAME ($PRIMARY_API_ID)${NC}"
else
    echo -e "${YELLOW}⚠️  找到多个项目API，需要选择主API${NC}"
    
    # 分析哪个API有更多的资源和集成
    for api in $(echo "$PROJECT_APIS" | jq -r '.[][0]'); do
        RESOURCE_COUNT=$(aws apigateway get-resources --rest-api-id $api --region $REGION --query 'items | length' --output text)
        echo "API $api 有 $RESOURCE_COUNT 个资源"
    done
    
    # 默认选择第一个，但可以根据资源数量调整
    PRIMARY_API_ID=$(echo "$PROJECT_APIS" | jq -r '.[0][0]')
    PRIMARY_API_NAME=$(echo "$PROJECT_APIS" | jq -r '.[0][1]')
    echo -e "${YELLOW}选择主API: $PRIMARY_API_NAME ($PRIMARY_API_ID)${NC}"
fi

echo ""

# 步骤2: 检查并清理Stages
echo -e "${YELLOW}步骤2: 检查并清理Stages...${NC}"

# 获取所有stages
STAGES=$(aws apigateway get-stages --rest-api-id $PRIMARY_API_ID --region $REGION --query 'item[*].stageName' --output text)

echo "现有Stages: $STAGES"

# 删除非主要的stages
for stage in $STAGES; do
    if [ "$stage" != "$PRIMARY_STAGE" ]; then
        echo -e "${YELLOW}删除stage: $stage${NC}"
        aws apigateway delete-stage \
          --rest-api-id $PRIMARY_API_ID \
          --stage-name $stage \
          --region $REGION 2>/dev/null || echo "Stage $stage 删除失败或不存在"
    fi
done

# 步骤3: 创建或更新主Stage
echo -e "${YELLOW}步骤3: 创建/更新主Stage...${NC}"

# 创建新部署
DEPLOYMENT_ID=$(aws apigateway create-deployment \
  --rest-api-id $PRIMARY_API_ID \
  --stage-name $PRIMARY_STAGE \
  --description "Unified deployment by unify_api_gateway.sh at $(date)" \
  --region $REGION \
  --query 'id' \
  --output text)

echo -e "${GREEN}✅ 创建部署: $DEPLOYMENT_ID${NC}"

# 更新stage配置
aws apigateway update-stage \
  --rest-api-id $PRIMARY_API_ID \
  --stage-name $PRIMARY_STAGE \
  --patch-operations \
    op=replace,path=/throttle/rateLimit,value=100 \
    op=replace,path=/throttle/burstLimit,value=200 \
  --region $REGION 2>/dev/null || true

echo -e "${GREEN}✅ Stage '$PRIMARY_STAGE' 已更新${NC}"
echo ""

# 步骤4: 统一Usage Plan
echo -e "${YELLOW}步骤4: 统一Usage Plan配置...${NC}"

# 获取所有usage plans
USAGE_PLANS=$(aws apigateway get-usage-plans --region $REGION --query 'items[*].[id,name]' --output json)

if [ "$(echo "$USAGE_PLANS" | jq 'length')" -eq 0 ]; then
    echo "创建新的Usage Plan..."
    
    USAGE_PLAN_ID=$(aws apigateway create-usage-plan \
      --name "$PROJECT-usage-plan" \
      --description "Usage plan for $PROJECT" \
      --api-stages apiId=$PRIMARY_API_ID,stage=$PRIMARY_STAGE \
      --throttle rateLimit=100,burstLimit=200 \
      --region $REGION \
      --query 'id' \
      --output text)
    
    echo -e "${GREEN}✅ 创建Usage Plan: $USAGE_PLAN_ID${NC}"
else
    # 使用第一个usage plan
    USAGE_PLAN_ID=$(echo "$USAGE_PLANS" | jq -r '.[0][0]')
    USAGE_PLAN_NAME=$(echo "$USAGE_PLANS" | jq -r '.[0][1]')
    
    echo "使用现有Usage Plan: $USAGE_PLAN_NAME ($USAGE_PLAN_ID)"
    
    # 获取当前关联的stages
    CURRENT_STAGES=$(aws apigateway get-usage-plan \
      --usage-plan-id $USAGE_PLAN_ID \
      --region $REGION \
      --query 'apiStages' \
      --output json)
    
    echo "当前关联的Stages:"
    echo "$CURRENT_STAGES" | jq -r '.[] | "\(.apiId):\(.stage)"'
    
    # 清理所有现有关联
    echo "清理现有Stage关联..."
    for stage_info in $(echo "$CURRENT_STAGES" | jq -r '.[] | "\(.apiId):\(.stage)"'); do
        aws apigateway update-usage-plan \
          --usage-plan-id $USAGE_PLAN_ID \
          --patch-operations op=remove,path="/apiStages/$stage_info" \
          --region $REGION 2>/dev/null || true
    done
    
    # 添加统一的stage关联
    aws apigateway update-usage-plan \
      --usage-plan-id $USAGE_PLAN_ID \
      --patch-operations \
        op=add,path=/apiStages,value="${PRIMARY_API_ID}:${PRIMARY_STAGE}" \
      --region $REGION
    
    echo -e "${GREEN}✅ Usage Plan已更新${NC}"
fi

echo ""

# 步骤5: 验证API密钥关联
echo -e "${YELLOW}步骤5: 验证API密钥关联...${NC}"

# 获取usage plan关联的密钥
API_KEYS=$(aws apigateway get-usage-plan-keys \
  --usage-plan-id $USAGE_PLAN_ID \
  --region $REGION \
  --query 'items[*].[id,name,value]' \
  --output json)

KEY_COUNT=$(echo "$API_KEYS" | jq 'length')

if [ "$KEY_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ 找到 $KEY_COUNT 个关联的API密钥${NC}"
    
    # 确保至少有一个启用的密钥
    ENABLED_KEYS=$(aws apigateway get-api-keys \
      --region $REGION \
      --query 'items[?enabled==`true`].[id,name]' \
      --output json)
    
    if [ "$(echo "$ENABLED_KEYS" | jq 'length')" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  没有启用的API密钥，请运行 emergency_security_fix.sh${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  没有API密钥关联到Usage Plan${NC}"
    echo "请运行 ./emergency_security_fix.sh 创建新密钥"
fi

echo ""

# 步骤6: 存储配置到SSM
echo -e "${YELLOW}步骤6: 存储配置到SSM Parameter Store...${NC}"

API_GATEWAY_URL="https://${PRIMARY_API_ID}.execute-api.${REGION}.amazonaws.com/${PRIMARY_STAGE}"

# 存储API Gateway URL
aws ssm put-parameter \
  --name "/$PROJECT/$ENVIRONMENT/api-gateway-url" \
  --value "$API_GATEWAY_URL" \
  --type "String" \
  --overwrite \
  --description "API Gateway URL for $PROJECT" \
  --region $REGION

# 存储API ID
aws ssm put-parameter \
  --name "/$PROJECT/$ENVIRONMENT/api-gateway-id" \
  --value "$PRIMARY_API_ID" \
  --type "String" \
  --overwrite \
  --description "API Gateway ID for $PROJECT" \
  --region $REGION

# 存储Stage名称
aws ssm put-parameter \
  --name "/$PROJECT/$ENVIRONMENT/api-stage" \
  --value "$PRIMARY_STAGE" \
  --type "String" \
  --overwrite \
  --description "API Gateway Stage for $PROJECT" \
  --region $REGION

echo -e "${GREEN}✅ 配置已存储到SSM${NC}"
echo ""

# 步骤7: 清理其他未使用的API（可选）
echo -e "${YELLOW}步骤7: 检查其他未使用的API...${NC}"

OTHER_APIS=$(aws apigateway get-rest-apis \
  --region $REGION \
  --query "items[?id!='$PRIMARY_API_ID' && contains(name, '$PROJECT')].[id,name]" \
  --output json)

if [ "$(echo "$OTHER_APIS" | jq 'length')" -gt 0 ]; then
    echo -e "${YELLOW}发现其他项目相关的API:${NC}"
    echo "$OTHER_APIS" | jq -r '.[] | "  - \(.1) (\(.0))"'
    echo ""
    echo "如果确认不需要，可以手动删除："
    echo "$OTHER_APIS" | jq -r '.[] | "aws apigateway delete-rest-api --rest-api-id \(.0) --region '$REGION'"'
else
    echo -e "${GREEN}✅ 没有其他需要清理的API${NC}"
fi

echo ""

# 步骤8: 生成配置摘要
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}配置摘要${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✅ 统一配置完成！${NC}"
echo ""
echo "📋 最终配置:"
echo "  API ID: $PRIMARY_API_ID"
echo "  API Name: $PRIMARY_API_NAME"
echo "  Stage: $PRIMARY_STAGE"
echo "  URL: $API_GATEWAY_URL"
echo "  Usage Plan: $USAGE_PLAN_ID"
echo ""
echo "🔧 SSM参数:"
echo "  /$PROJECT/$ENVIRONMENT/api-gateway-url"
echo "  /$PROJECT/$ENVIRONMENT/api-gateway-id"
echo "  /$PROJECT/$ENVIRONMENT/api-stage"
echo ""

# 创建配置文件
cat > api_gateway_config.json << EOF
{
  "project": "$PROJECT",
  "environment": "$ENVIRONMENT",
  "region": "$REGION",
  "api_id": "$PRIMARY_API_ID",
  "api_name": "$PRIMARY_API_NAME",
  "stage": "$PRIMARY_STAGE",
  "api_url": "$API_GATEWAY_URL",
  "usage_plan_id": "$USAGE_PLAN_ID",
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "updated_by": "unify_api_gateway.sh"
}
EOF

echo -e "${GREEN}配置已保存到: api_gateway_config.json${NC}"
echo ""
echo -e "${GREEN}下一步:${NC}"
echo "  1. 运行: python3 migrate_dynamodb_data.py"
echo "  2. 运行: python3 setup_config_center.py"
echo "  3. 测试API: python3 test_all_backend_apis.py"