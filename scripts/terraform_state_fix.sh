#!/bin/bash

# Terraform 状态修复脚本
# 解决资源已存在但不在 Terraform 状态中的问题

set -e

echo "======================================================================="
echo "🔧 Terraform 状态同步修复脚本"
echo "======================================================================="

cd /Users/umatoratatsu/Documents/AWS/AWS-Handson/Amazon-Bedrock-Agents/infrastructure

# 1. 初始化 Terraform
echo -e "\n[INFO] 初始化 Terraform..."
terraform init -upgrade

# 2. 刷新状态
echo -e "\n[INFO] 刷新 Terraform 状态..."
terraform refresh

# 3. 导入已存在的 IAM 角色
echo -e "\n[INFO] 导入已存在的 IAM 角色到 Terraform 状态..."
IAM_ROLES=(
    "module.bedrock.aws_iam_role.bedrock_agent_role[\"compiler\"]|ai-ppt-assistant-compiler-agent-role"
    "module.bedrock.aws_iam_role.bedrock_agent_role[\"orchestrator\"]|ai-ppt-assistant-orchestrator-agent-role"
    "module.bedrock.aws_iam_role.bedrock_agent_role[\"visual\"]|ai-ppt-assistant-visual-agent-role"
    "module.bedrock.aws_iam_role.bedrock_agent_role[\"content\"]|ai-ppt-assistant-content-agent-role"
)

for role_spec in "${IAM_ROLES[@]}"; do
    IFS='|' read -r resource role_name <<< "$role_spec"
    if ! terraform state show "$resource" &>/dev/null; then
        echo "  导入: $role_name"
        terraform import "$resource" "$role_name" || echo "  跳过: $role_name (可能已导入或不存在)"
    fi
done

# 4. 导入已存在的 IAM 策略
echo -e "\n[INFO] 导入已存在的 IAM 策略到 Terraform 状态..."
IAM_POLICIES=(
    "module.bedrock.aws_iam_policy.bedrock_agent_policy[\"compiler\"]|arn:aws:iam::375004070918:policy/ai-ppt-assistant-compiler-agent-policy"
    "module.bedrock.aws_iam_policy.bedrock_agent_policy[\"orchestrator\"]|arn:aws:iam::375004070918:policy/ai-ppt-assistant-orchestrator-agent-policy"
    "module.bedrock.aws_iam_policy.bedrock_agent_policy[\"visual\"]|arn:aws:iam::375004070918:policy/ai-ppt-assistant-visual-agent-policy"
    "module.bedrock.aws_iam_policy.bedrock_agent_policy[\"content\"]|arn:aws:iam::375004070918:policy/ai-ppt-assistant-content-agent-policy"
)

for policy_spec in "${IAM_POLICIES[@]}"; do
    IFS='|' read -r resource policy_arn <<< "$policy_spec"
    if ! terraform state show "$resource" &>/dev/null; then
        echo "  导入: $policy_arn"
        terraform import "$resource" "$policy_arn" || echo "  跳过: $policy_arn (可能已导入或不存在)"
    fi
done

# 5. 导入已存在的 DynamoDB 表
echo -e "\n[INFO] 导入已存在的 DynamoDB 表到 Terraform 状态..."
DYNAMODB_TABLES=(
    "module.dynamodb.aws_dynamodb_table.sessions|ai-ppt-assistant-dev-sessions"
    "module.dynamodb.aws_dynamodb_table.tasks[0]|ai-ppt-assistant-dev-tasks"
    "module.dynamodb.aws_dynamodb_table.checkpoints|ai-ppt-assistant-dev-checkpoints"
)

for table_spec in "${DYNAMODB_TABLES[@]}"; do
    IFS='|' read -r resource table_name <<< "$table_spec"
    if ! terraform state show "$resource" &>/dev/null; then
        # 检查表是否存在
        if aws dynamodb describe-table --table-name "$table_name" &>/dev/null; then
            echo "  导入: $table_name"
            terraform import "$resource" "$table_name" || echo "  跳过: $table_name (可能已导入)"
        else
            echo "  表不存在: $table_name"
        fi
    fi
done

# 6. 导入 KMS 别名
echo -e "\n[INFO] 导入 KMS 别名..."
if ! terraform state show "module.monitoring[0].aws_kms_alias.sns_key_alias" &>/dev/null; then
    terraform import "module.monitoring[0].aws_kms_alias.sns_key_alias" "alias/ai-ppt-assistant-dev-sns-key" || echo "  跳过 KMS 别名"
fi

# 7. 导入 CloudWatch 日志组
echo -e "\n[INFO] 导入 CloudWatch 日志组..."
if ! terraform state show "module.monitoring[0].aws_cloudwatch_log_group.insights_queries" &>/dev/null; then
    terraform import "module.monitoring[0].aws_cloudwatch_log_group.insights_queries" "/aws/cloudwatch/insights/ai-ppt-assistant-dev" || echo "  跳过日志组"
fi

# 8. 导入 VPC 安全组
echo -e "\n[INFO] 导入 VPC 安全组..."
VPC_ID="vpc-0727e36c25a57baaf"
SG_NAME="ai-ppt-assistant-dev-vpc-endpoints-sg"

# 查找安全组 ID
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=$SG_NAME" \
    --query "SecurityGroups[0].GroupId" \
    --output text 2>/dev/null || echo "")

if [ ! -z "$SG_ID" ] && [ "$SG_ID" != "None" ]; then
    if ! terraform state show "module.vpc.aws_security_group.vpc_endpoints" &>/dev/null; then
        echo "  导入安全组: $SG_ID"
        terraform import "module.vpc.aws_security_group.vpc_endpoints" "$SG_ID" || echo "  跳过安全组"
    fi
fi

# 9. 导入 VPC 子网
echo -e "\n[INFO] 检查并导入 VPC 子网..."
SUBNETS=(
    "module.vpc.aws_subnet.public[0]|10.0.0.0/24"
    "module.vpc.aws_subnet.public[1]|10.0.1.0/24"
)

for subnet_spec in "${SUBNETS[@]}"; do
    IFS='|' read -r resource cidr <<< "$subnet_spec"
    # 查找子网 ID
    SUBNET_ID=$(aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$VPC_ID" "Name=cidr-block,Values=$cidr" \
        --query "Subnets[0].SubnetId" \
        --output text 2>/dev/null || echo "")
    
    if [ ! -z "$SUBNET_ID" ] && [ "$SUBNET_ID" != "None" ]; then
        if ! terraform state show "$resource" &>/dev/null; then
            echo "  导入子网: $SUBNET_ID ($cidr)"
            terraform import "$resource" "$SUBNET_ID" || echo "  跳过子网: $cidr"
        fi
    fi
done

# 10. 再次刷新状态
echo -e "\n[INFO] 最终状态刷新..."
terraform refresh

# 11. 计划部署
echo -e "\n[INFO] 生成部署计划..."
terraform plan -out=tfplan

echo -e "\n[SUCCESS] Terraform 状态修复完成！"
echo "现在可以运行: terraform apply tfplan"