#!/bin/bash

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}清理残留AWS资源${NC}"
echo -e "${GREEN}========================================${NC}"

# 清理DynamoDB表
echo -e "${YELLOW}正在清理DynamoDB表...${NC}"
aws dynamodb delete-table --table-name ai-ppt-assistant-dev-sessions 2>/dev/null || true
aws dynamodb delete-table --table-name ai-ppt-assistant-dev-tasks 2>/dev/null || true
aws dynamodb delete-table --table-name ai-ppt-assistant-dev-checkpoints 2>/dev/null || true

# 等待表删除完成
echo -e "${YELLOW}等待DynamoDB表删除完成...${NC}"
for table in ai-ppt-assistant-dev-sessions ai-ppt-assistant-dev-tasks ai-ppt-assistant-dev-checkpoints; do
    while aws dynamodb describe-table --table-name $table 2>/dev/null; do
        echo "等待 $table 删除..."
        sleep 5
    done
    echo -e "${GREEN}✅ $table 已删除${NC}"
done

# 清理VPC相关资源
echo -e "${YELLOW}正在清理VPC相关资源...${NC}"
VPC_ID="vpc-0727e36c25a57baaf"

# 删除VPC的依赖资源
echo "删除VPC Endpoints..."
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC_ID" --query "VpcEndpoints[].VpcEndpointId" --output text | xargs -I {} aws ec2 delete-vpc-endpoints --vpc-endpoint-ids {} 2>/dev/null || true

echo "删除NAT网关..."
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=$VPC_ID" --query "NatGateways[].NatGatewayId" --output text | xargs -I {} aws ec2 delete-nat-gateway --nat-gateway-id {} 2>/dev/null || true

echo "删除安全组..."
# 先删除非默认安全组
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[?GroupName!='default'].GroupId" --output text | xargs -I {} aws ec2 delete-security-group --group-id {} 2>/dev/null || true

echo "删除子网..."
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[].SubnetId" --output text | xargs -I {} aws ec2 delete-subnet --subnet-id {} 2>/dev/null || true

# 清理IAM角色和策略
echo -e "${YELLOW}正在清理IAM角色和策略...${NC}"
AGENT_TYPES="compiler orchestrator visual content"
for agent in $AGENT_TYPES; do
    # 分离策略
    aws iam detach-role-policy --role-name ai-ppt-assistant-$agent-agent-role --policy-arn arn:aws:iam::375004070918:policy/ai-ppt-assistant-$agent-agent-policy 2>/dev/null || true
    
    # 删除策略
    aws iam delete-policy --policy-arn arn:aws:iam::375004070918:policy/ai-ppt-assistant-$agent-agent-policy 2>/dev/null || true
    
    # 删除角色
    aws iam delete-role --role-name ai-ppt-assistant-$agent-agent-role 2>/dev/null || true
    
    echo -e "${GREEN}✅ 清理 $agent agent 角色和策略${NC}"
done

# 清理KMS别名
echo -e "${YELLOW}正在清理KMS别名...${NC}"
aws kms delete-alias --alias-name alias/ai-ppt-assistant-dev-sns-key 2>/dev/null || true

# 清理CloudWatch日志组
echo -e "${YELLOW}正在清理CloudWatch日志组...${NC}"
aws logs delete-log-group --log-group-name /aws/cloudwatch/insights/ai-ppt-assistant-dev 2>/dev/null || true

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}资源清理完成！${NC}"
echo -e "${GREEN}========================================${NC}"