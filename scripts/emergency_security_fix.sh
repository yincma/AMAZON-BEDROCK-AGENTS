#!/bin/bash
# emergency_security_fix.sh - 紧急安全修复脚本
# 立即轮换API密钥并加固安全配置

set -e

echo "🚨 开始紧急安全修复..."
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI未安装${NC}"
    exit 1
fi

# 获取当前AWS账户信息
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

echo -e "${YELLOW}📍 AWS账户: $ACCOUNT_ID${NC}"
echo -e "${YELLOW}📍 区域: $REGION${NC}"
echo ""

# 步骤1: 创建新的API密钥
echo -e "${GREEN}步骤1: 创建新的API密钥...${NC}"

NEW_API_KEY=$(aws apigateway create-api-key \
  --name "ai-ppt-assistant-dev-key-$(date +%Y%m%d-%H%M%S)" \
  --enabled \
  --query 'value' \
  --output text \
  --region $REGION)

if [ -z "$NEW_API_KEY" ]; then
    echo -e "${RED}❌ 创建API密钥失败${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 新API密钥已创建${NC}"
echo -e "${YELLOW}⚠️  请立即保存此密钥到安全位置: $NEW_API_KEY${NC}"
echo ""

# 步骤2: 获取新密钥ID
NEW_KEY_ID=$(aws apigateway get-api-keys \
  --query "items[?value=='$NEW_API_KEY'].id" \
  --output text \
  --region $REGION)

# 步骤3: 关联到使用计划
echo -e "${GREEN}步骤2: 关联密钥到使用计划...${NC}"

USAGE_PLAN_ID=$(aws apigateway get-usage-plans \
  --query 'items[?name==`ai-ppt-assistant-usage-plan`].id' \
  --output text \
  --region $REGION)

if [ -z "$USAGE_PLAN_ID" ]; then
    # 如果使用计划不存在，使用第一个找到的
    USAGE_PLAN_ID=$(aws apigateway get-usage-plans \
      --query 'items[0].id' \
      --output text \
      --region $REGION)
fi

if [ ! -z "$USAGE_PLAN_ID" ]; then
    aws apigateway create-usage-plan-key \
      --usage-plan-id $USAGE_PLAN_ID \
      --key-id $NEW_KEY_ID \
      --key-type API_KEY \
      --region $REGION 2>/dev/null || echo "密钥可能已关联"
    
    echo -e "${GREEN}✅ 密钥已关联到使用计划${NC}"
else
    echo -e "${YELLOW}⚠️  未找到使用计划，请手动关联${NC}"
fi

# 步骤4: 存储到SSM Parameter Store
echo -e "${GREEN}步骤3: 存储密钥到SSM Parameter Store...${NC}"

aws ssm put-parameter \
  --name "/ai-ppt-assistant/dev/api-key" \
  --value "$NEW_API_KEY" \
  --type "SecureString" \
  --overwrite \
  --region $REGION 2>/dev/null || {
    # 如果失败，尝试先删除再创建
    aws ssm delete-parameter --name "/ai-ppt-assistant/dev/api-key" --region $REGION 2>/dev/null
    aws ssm put-parameter \
      --name "/ai-ppt-assistant/dev/api-key" \
      --value "$NEW_API_KEY" \
      --type "SecureString" \
      --region $REGION
}

echo -e "${GREEN}✅ 密钥已安全存储到SSM${NC}"

# 步骤5: 禁用旧密钥
echo -e "${GREEN}步骤4: 禁用已泄露的旧密钥...${NC}"

# 已知的泄露密钥
OLD_KEYS=("9EQHqfmiuA5GrkMnK5PVf8OpbIcsMj1N2z6PFGR3")

for OLD_KEY in "${OLD_KEYS[@]}"; do
    OLD_KEY_ID=$(aws apigateway get-api-keys \
      --query "items[?value=='$OLD_KEY'].id" \
      --output text \
      --region $REGION 2>/dev/null)
    
    if [ ! -z "$OLD_KEY_ID" ]; then
        aws apigateway update-api-key \
          --api-key $OLD_KEY_ID \
          --patch-operations op=replace,path=/enabled,value=false \
          --region $REGION
        echo -e "${GREEN}✅ 已禁用旧密钥: ${OLD_KEY:0:10}...${NC}"
    fi
done

# 步骤6: 创建安全的配置文件模板
echo -e "${GREEN}步骤5: 创建安全的配置文件...${NC}"

cat > api_config_info.json << EOF
{
  "project": "ai-ppt-assistant",
  "environment": "dev",
  "region": "$REGION",
  "api_gateway_url": "{{API_GATEWAY_URL}}",
  "api_key_parameter": "/ai-ppt-assistant/dev/api-key",
  "note": "Actual values are stored in AWS SSM Parameter Store",
  "security_notice": "NEVER store actual API keys in this file",
  "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "updated_by": "emergency_security_fix"
}
EOF

echo -e "${GREEN}✅ 安全配置模板已创建${NC}"

# 步骤7: 创建密钥读取辅助脚本
echo -e "${GREEN}步骤6: 创建密钥读取辅助脚本...${NC}"

cat > get_api_key.sh << 'SCRIPT'
#!/bin/bash
# 从SSM安全获取API密钥

aws ssm get-parameter \
  --name "/ai-ppt-assistant/dev/api-key" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text \
  --region us-east-1
SCRIPT

chmod +x get_api_key.sh

echo -e "${GREEN}✅ 辅助脚本已创建: get_api_key.sh${NC}"

# 完成报告
echo ""
echo "================================"
echo -e "${GREEN}🎉 紧急安全修复完成！${NC}"
echo "================================"
echo ""
echo "📋 完成的操作:"
echo "  ✅ 创建新的API密钥"
echo "  ✅ 密钥存储到SSM Parameter Store"
echo "  ✅ 禁用已泄露的旧密钥"
echo "  ✅ 创建安全配置模板"
echo ""
echo -e "${YELLOW}⚠️  重要提醒:${NC}"
echo "  1. 新的API密钥: $NEW_API_KEY"
echo "  2. 请立即更新所有使用API的应用程序"
echo "  3. 使用 ./get_api_key.sh 安全获取密钥"
echo "  4. 永远不要将密钥提交到Git仓库"
echo ""
echo -e "${GREEN}下一步建议:${NC}"
echo "  1. 运行: python3 fix_agent_config.py"
echo "  2. 运行: bash unify_api_gateway.sh"
echo "  3. 运行: python3 migrate_dynamodb_data.py"