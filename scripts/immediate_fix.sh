#!/bin/bash

# AI PPT Assistant - 立即修复脚本
# 用途：快速执行第一阶段修复计划
# 创建时间：2025-09-11

set -e  # 遇到错误立即停止

echo "========================================"
echo "AI PPT Assistant 第一阶段修复脚本"
echo "========================================"
echo ""
echo "⚠️ 警告：此脚本将执行以下操作："
echo "1. 轮换API密钥"
echo "2. 配置Bedrock Agent别名"
echo "3. 统一API Gateway"
echo "4. 迁移DynamoDB数据"
echo "5. 创建SSM配置中心"
echo ""
read -p "确认执行？(y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

# 设置变量
export AWS_REGION=us-east-1
export PROJECT_NAME=ai-ppt-assistant
export ENVIRONMENT=dev

echo ""
echo "🔐 步骤1: API密钥轮换"
echo "========================================"

# 创建新的API密钥
NEW_API_KEY=$(aws apigateway create-api-key \
  --name "${PROJECT_NAME}-${ENVIRONMENT}-key-$(date +%Y%m%d%H%M)" \
  --enabled \
  --query 'value' \
  --output text \
  --region ${AWS_REGION})

echo "✅ 新API密钥已创建"

# 获取使用计划ID
USAGE_PLAN_ID=$(aws apigateway get-usage-plans \
  --query 'items[?name==`ai-ppt-assistant-usage-plan`].id' \
  --output text \
  --region ${AWS_REGION})

if [ ! -z "$USAGE_PLAN_ID" ]; then
  # 关联到使用计划
  NEW_KEY_ID=$(aws apigateway get-api-keys --query "items[?value=='$NEW_API_KEY'].id" --output text --region ${AWS_REGION})
  aws apigateway create-usage-plan-key \
    --usage-plan-id $USAGE_PLAN_ID \
    --key-id $NEW_KEY_ID \
    --key-type API_KEY \
    --region ${AWS_REGION} 2>/dev/null || true
  echo "✅ API密钥已关联到使用计划"
fi

# 存储到SSM
aws ssm put-parameter \
  --name "/${PROJECT_NAME}/${ENVIRONMENT}/api-key" \
  --value "$NEW_API_KEY" \
  --type "SecureString" \
  --overwrite \
  --region ${AWS_REGION} 2>/dev/null || true

echo "✅ API密钥已存储到SSM Parameter Store"

# 禁用旧密钥
OLD_KEY_IDS=$(aws apigateway get-api-keys \
  --query "items[?name=='${PROJECT_NAME}-${ENVIRONMENT}-api-key'].id" \
  --output text \
  --region ${AWS_REGION})

for KEY_ID in $OLD_KEY_IDS; do
  aws apigateway update-api-key \
    --api-key $KEY_ID \
    --patch-operations op=replace,path=/enabled,value=false \
    --region ${AWS_REGION} 2>/dev/null || true
  echo "✅ 禁用旧密钥: $KEY_ID"
done

echo ""
echo "🤖 步骤2: 配置Bedrock Agent别名"
echo "========================================"

# Agent配置
declare -A AGENTS
AGENTS["orchestrator"]="Q6RODNGFYR"
AGENTS["content"]="L0ZQHJSU4X"
AGENTS["visual"]="FO53FNXIRL"
AGENTS["compiler"]="B02XIGCUKI"

for AGENT_TYPE in "${!AGENTS[@]}"; do
  AGENT_ID="${AGENTS[$AGENT_TYPE]}"
  
  # 检查别名是否存在
  EXISTING_ALIAS=$(aws bedrock-agent list-agent-aliases \
    --agent-id $AGENT_ID \
    --query "agentAliasSummaries[?agentAliasName=='dev'].agentAliasId" \
    --output text \
    --region ${AWS_REGION} 2>/dev/null || echo "")
  
  if [ -z "$EXISTING_ALIAS" ]; then
    # 创建别名
    ALIAS_ID=$(aws bedrock-agent create-agent-alias \
      --agent-id $AGENT_ID \
      --agent-alias-name dev \
      --description "Development alias created $(date)" \
      --query 'agentAlias.agentAliasId' \
      --output text \
      --region ${AWS_REGION} 2>/dev/null || echo "")
    
    if [ ! -z "$ALIAS_ID" ]; then
      echo "✅ 创建${AGENT_TYPE} Agent别名: $ALIAS_ID"
      
      # 存储到SSM
      aws ssm put-parameter \
        --name "/${PROJECT_NAME}/${ENVIRONMENT}/agents/${AGENT_TYPE}/alias_id" \
        --value "$ALIAS_ID" \
        --type "String" \
        --overwrite \
        --region ${AWS_REGION} 2>/dev/null || true
    fi
  else
    echo "✓ ${AGENT_TYPE} Agent别名已存在: $EXISTING_ALIAS"
    
    # 存储到SSM
    aws ssm put-parameter \
      --name "/${PROJECT_NAME}/${ENVIRONMENT}/agents/${AGENT_TYPE}/alias_id" \
      --value "$EXISTING_ALIAS" \
      --type "String" \
      --overwrite \
      --region ${AWS_REGION} 2>/dev/null || true
  fi
done

echo ""
echo "🌐 步骤3: 统一API Gateway"
echo "========================================"

API_ID="otmr3noxg5"

# 删除legacy stage
aws apigateway delete-stage \
  --rest-api-id $API_ID \
  --stage-name legacy \
  --region ${AWS_REGION} 2>/dev/null || echo "✓ legacy stage不存在或已删除"

# 部署到dev stage
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name dev \
  --description "Unified deployment $(date +%Y%m%d-%H%M%S)" \
  --region ${AWS_REGION} 2>/dev/null || true

echo "✅ API Gateway已统一到dev stage"

# 存储URL到SSM
aws ssm put-parameter \
  --name "/${PROJECT_NAME}/${ENVIRONMENT}/api-gateway-url" \
  --value "https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/dev" \
  --type "String" \
  --overwrite \
  --region ${AWS_REGION} 2>/dev/null || true

echo ""
echo "💾 步骤4: DynamoDB数据迁移"
echo "========================================"

# 创建Python脚本进行数据迁移
cat > /tmp/migrate_dynamodb.py << 'EOF'
import boto3
import json
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def migrate_data():
    tasks_table = dynamodb.Table('ai-ppt-assistant-dev-tasks')
    sessions_table = dynamodb.Table('ai-ppt-assistant-dev-sessions')
    
    # 扫描tasks表
    try:
        response = tasks_table.scan()
        items = response.get('Items', [])
        print(f"找到 {len(items)} 条记录需要迁移")
        
        migrated = 0
        for item in items:
            try:
                # 检查是否已存在
                existing = sessions_table.get_item(
                    Key={'taskId': item.get('taskId')}
                )
                
                if 'Item' not in existing:
                    sessions_table.put_item(Item=item)
                    migrated += 1
                    print(f"✓ 迁移: {item.get('taskId')}")
            except Exception as e:
                print(f"❌ 迁移失败: {item.get('taskId')} - {e}")
        
        print(f"✅ 成功迁移 {migrated} 条记录")
        
    except Exception as e:
        print(f"❌ 数据迁移失败: {e}")

if __name__ == "__main__":
    migrate_data()
EOF

python3 /tmp/migrate_dynamodb.py

# 更新Lambda函数环境变量
FUNCTIONS=(
  "ai-ppt-assistant-api-generate-presentation"
  "ai-ppt-assistant-api-presentation-status"
  "ai-ppt-assistant-api-list-presentations"
  "ai-ppt-assistant-api-get-task"
)

for FUNC in "${FUNCTIONS[@]}"; do
  aws lambda update-function-configuration \
    --function-name $FUNC \
    --environment "Variables={DYNAMODB_TABLE=ai-ppt-assistant-dev-sessions,CONFIG_SOURCE=SSM_PARAMETER_STORE}" \
    --region ${AWS_REGION} 2>/dev/null || echo "⚠️ 无法更新函数: $FUNC"
done

echo "✅ Lambda函数已更新为使用sessions表"

echo ""
echo "🔧 步骤5: 创建SSM配置中心"
echo "========================================"

# 创建核心配置参数
PARAMETERS=(
  "api-stage:dev"
  "dynamodb-table:ai-ppt-assistant-dev-sessions"
  "dynamodb-region:us-east-1"
  "s3-bucket:ai-ppt-assistant-dev-presentations-375004070918"
  "sqs-queue:ai-ppt-assistant-dev-tasks"
  "environment:development"
  "log-level:INFO"
  "version:2.0.0"
)

for PARAM in "${PARAMETERS[@]}"; do
  KEY="${PARAM%%:*}"
  VALUE="${PARAM#*:}"
  
  aws ssm put-parameter \
    --name "/${PROJECT_NAME}/${ENVIRONMENT}/${KEY}" \
    --value "$VALUE" \
    --type "String" \
    --overwrite \
    --region ${AWS_REGION} 2>/dev/null || true
  
  echo "✓ 创建参数: /${PROJECT_NAME}/${ENVIRONMENT}/${KEY}"
done

echo "✅ SSM配置中心已创建"

echo ""
echo "========================================"
echo "🎉 第一阶段修复完成！"
echo "========================================"
echo ""
echo "新API密钥: $NEW_API_KEY"
echo ""
echo "请保存此密钥并更新您的客户端配置。"
echo ""
echo "下一步："
echo "1. 运行验证: make validate-fixes"
echo "2. 执行部署: make deploy-safe"
echo ""
echo "如有问题，请查看: docs/reports/第一阶段修复验证报告.md"

# 清理临时文件
rm -f /tmp/migrate_dynamodb.py