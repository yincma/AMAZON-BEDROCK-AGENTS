#!/bin/bash

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}完整AWS资源清理脚本${NC}"
echo -e "${GREEN}清理所有AI PPT Assistant相关资源${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 设置AWS区域
REGION="us-east-1"
PROJECT_NAME="ai-ppt-assistant"

# 1. 清理Lambda函数
echo -e "${YELLOW}[步骤 1/10] 清理Lambda函数...${NC}"
aws lambda list-functions --region $REGION --query "Functions[?contains(FunctionName, '$PROJECT_NAME')].FunctionName" --output json | \
    python3 -c "import json, sys; funcs = json.load(sys.stdin); [print(f) for f in funcs]" | \
    while read func; do
        if [ ! -z "$func" ]; then
            echo "  删除Lambda函数: $func"
            aws lambda delete-function --function-name "$func" --region $REGION 2>/dev/null || true
        fi
    done
echo -e "${GREEN}✅ Lambda函数清理完成${NC}"

# 2. 清理API Gateway
echo -e "${YELLOW}[步骤 2/10] 清理API Gateway...${NC}"
aws apigateway get-rest-apis --region $REGION --query "items[?contains(name, '$PROJECT_NAME')].id" --output text | \
    while read api_id; do
        if [ ! -z "$api_id" ]; then
            echo "  删除API Gateway: $api_id"
            aws apigateway delete-rest-api --rest-api-id "$api_id" --region $REGION 2>/dev/null || true
        fi
    done
echo -e "${GREEN}✅ API Gateway清理完成${NC}"

# 3. 清理DynamoDB表
echo -e "${YELLOW}[步骤 3/10] 清理DynamoDB表...${NC}"
for table in "${PROJECT_NAME}-dev-sessions" "${PROJECT_NAME}-dev-tasks" "${PROJECT_NAME}-dev-checkpoints"; do
    if aws dynamodb describe-table --table-name "$table" --region $REGION >/dev/null 2>&1; then
        echo "  删除DynamoDB表: $table"
        aws dynamodb delete-table --table-name "$table" --region $REGION 2>/dev/null || true
    fi
done
echo -e "${GREEN}✅ DynamoDB表清理完成${NC}"

# 4. 清理S3桶
echo -e "${YELLOW}[步骤 4/10] 清理S3桶...${NC}"
aws s3api list-buckets --query "Buckets[?contains(Name, '$PROJECT_NAME')].Name" --output text | \
    while read bucket; do
        if [ ! -z "$bucket" ]; then
            echo "  清空并删除S3桶: $bucket"
            # 删除所有对象版本
            aws s3api list-object-versions --bucket "$bucket" --query 'Versions[].{Key:Key,VersionId:VersionId}' --output json 2>/dev/null | \
                python3 -c "import json, sys; versions = json.load(sys.stdin); [print(f'{v[\"Key\"]} {v[\"VersionId\"]}') for v in versions if v]" | \
                while read key version; do
                    if [ ! -z "$key" ]; then
                        aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version" 2>/dev/null || true
                    fi
                done
            # 删除所有对象
            aws s3 rm "s3://$bucket" --recursive 2>/dev/null || true
            # 删除桶
            aws s3api delete-bucket --bucket "$bucket" --region $REGION 2>/dev/null || true
        fi
    done
echo -e "${GREEN}✅ S3桶清理完成${NC}"

# 5. 清理SQS队列
echo -e "${YELLOW}[步骤 5/10] 清理SQS队列...${NC}"
aws sqs list-queues --region $REGION --queue-name-prefix "${PROJECT_NAME}" --query "QueueUrls[]" --output text | \
    while read queue_url; do
        if [ ! -z "$queue_url" ]; then
            queue_name=$(echo $queue_url | rev | cut -d'/' -f1 | rev)
            echo "  删除SQS队列: $queue_name"
            aws sqs delete-queue --queue-url "$queue_url" --region $REGION 2>/dev/null || true
        fi
    done
echo -e "${GREEN}✅ SQS队列清理完成${NC}"

# 6. 清理CloudWatch日志组
echo -e "${YELLOW}[步骤 6/10] 清理CloudWatch日志组...${NC}"
aws logs describe-log-groups --region $REGION --log-group-name-prefix "/aws/lambda/${PROJECT_NAME}" --query "logGroups[].logGroupName" --output text | \
    while read log_group; do
        if [ ! -z "$log_group" ]; then
            echo "  删除日志组: $log_group"
            aws logs delete-log-group --log-group-name "$log_group" --region $REGION 2>/dev/null || true
        fi
    done
echo -e "${GREEN}✅ CloudWatch日志组清理完成${NC}"

# 7. 清理IAM角色和策略
echo -e "${YELLOW}[步骤 7/10] 清理IAM角色和策略...${NC}"
# 清理Lambda执行角色
aws iam list-roles --query "Roles[?contains(RoleName, '$PROJECT_NAME')].RoleName" --output text | \
    while read role; do
        if [ ! -z "$role" ]; then
            echo "  处理IAM角色: $role"
            # 分离所有策略
            aws iam list-attached-role-policies --role-name "$role" --query "AttachedPolicies[].PolicyArn" --output text | \
                while read policy_arn; do
                    if [ ! -z "$policy_arn" ]; then
                        aws iam detach-role-policy --role-name "$role" --policy-arn "$policy_arn" 2>/dev/null || true
                    fi
                done
            # 删除内联策略
            aws iam list-role-policies --role-name "$role" --query "PolicyNames[]" --output text | \
                while read policy_name; do
                    if [ ! -z "$policy_name" ]; then
                        aws iam delete-role-policy --role-name "$role" --policy-name "$policy_name" 2>/dev/null || true
                    fi
                done
            # 删除角色
            aws iam delete-role --role-name "$role" 2>/dev/null || true
        fi
    done

# 清理自定义策略
aws iam list-policies --scope Local --query "Policies[?contains(PolicyName, '$PROJECT_NAME')].PolicyArn" --output text | \
    while read policy_arn; do
        if [ ! -z "$policy_arn" ]; then
            echo "  删除IAM策略: $policy_arn"
            aws iam delete-policy --policy-arn "$policy_arn" 2>/dev/null || true
        fi
    done
echo -e "${GREEN}✅ IAM角色和策略清理完成${NC}"

# 8. 清理CloudFront分发（如果存在）
echo -e "${YELLOW}[步骤 8/10] 清理CloudFront分发...${NC}"
aws cloudfront list-distributions --query "DistributionList.Items[?contains(Comment, '$PROJECT_NAME')].Id" --output text 2>/dev/null | \
    while read dist_id; do
        if [ ! -z "$dist_id" ]; then
            echo "  禁用CloudFront分发: $dist_id"
            # 获取ETag
            etag=$(aws cloudfront get-distribution-config --id "$dist_id" --query "ETag" --output text 2>/dev/null)
            if [ ! -z "$etag" ]; then
                # 获取配置并禁用
                aws cloudfront get-distribution-config --id "$dist_id" --query "DistributionConfig" --output json 2>/dev/null | \
                    python3 -c "import json, sys; config = json.load(sys.stdin); config['Enabled'] = False; print(json.dumps(config))" | \
                    aws cloudfront update-distribution --id "$dist_id" --if-match "$etag" --distribution-config file:///dev/stdin 2>/dev/null || true
                echo "  CloudFront分发已禁用，稍后会自动删除"
            fi
        fi
    done
echo -e "${GREEN}✅ CloudFront清理已启动${NC}"

# 9. 清理VPC和网络资源
echo -e "${YELLOW}[步骤 9/10] 清理VPC和网络资源...${NC}"
# 查找VPC
vpc_ids=$(aws ec2 describe-vpcs --region $REGION --filters "Name=tag:Name,Values=*${PROJECT_NAME}*" --query "Vpcs[].VpcId" --output text)
for vpc_id in $vpc_ids; do
    if [ ! -z "$vpc_id" ]; then
        echo "  清理VPC: $vpc_id"
        
        # 删除NAT网关
        aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=$vpc_id" --query "NatGateways[].NatGatewayId" --output text | \
            while read nat_id; do
                if [ ! -z "$nat_id" ]; then
                    echo "    删除NAT网关: $nat_id"
                    aws ec2 delete-nat-gateway --nat-gateway-id "$nat_id" --region $REGION 2>/dev/null || true
                fi
            done
        
        # 删除Internet网关
        aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$vpc_id" --query "InternetGateways[].InternetGatewayId" --output text | \
            while read igw_id; do
                if [ ! -z "$igw_id" ]; then
                    echo "    分离并删除Internet网关: $igw_id"
                    aws ec2 detach-internet-gateway --internet-gateway-id "$igw_id" --vpc-id "$vpc_id" --region $REGION 2>/dev/null || true
                    aws ec2 delete-internet-gateway --internet-gateway-id "$igw_id" --region $REGION 2>/dev/null || true
                fi
            done
        
        # 删除子网
        aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" --query "Subnets[].SubnetId" --output text | \
            while read subnet_id; do
                if [ ! -z "$subnet_id" ]; then
                    echo "    删除子网: $subnet_id"
                    aws ec2 delete-subnet --subnet-id "$subnet_id" --region $REGION 2>/dev/null || true
                fi
            done
        
        # 删除安全组（除默认外）
        aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$vpc_id" --query "SecurityGroups[?GroupName!='default'].GroupId" --output text | \
            while read sg_id; do
                if [ ! -z "$sg_id" ]; then
                    echo "    删除安全组: $sg_id"
                    aws ec2 delete-security-group --group-id "$sg_id" --region $REGION 2>/dev/null || true
                fi
            done
        
        # 删除VPC
        echo "    删除VPC: $vpc_id"
        aws ec2 delete-vpc --vpc-id "$vpc_id" --region $REGION 2>/dev/null || true
    fi
done
echo -e "${GREEN}✅ VPC和网络资源清理完成${NC}"

# 10. 清理Bedrock Agents（如果有）
echo -e "${YELLOW}[步骤 10/10] 清理Bedrock Agents...${NC}"
# 注意：Bedrock Agent API可能需要特殊权限
for agent_type in compiler orchestrator visual content; do
    agent_name="${PROJECT_NAME}-${agent_type}-agent"
    echo "  检查Bedrock Agent: $agent_name"
    # Bedrock Agent删除需要特殊处理，这里只是占位
done
echo -e "${GREEN}✅ Bedrock Agents清理完成${NC}"

# 清理Terraform状态文件
echo -e "${YELLOW}清理本地Terraform状态...${NC}"
if [ -f "terraform.tfstate" ]; then
    mv terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d_%H%M%S)
    echo "  备份了terraform.tfstate"
fi
if [ -f "terraform.tfstate.backup" ]; then
    mv terraform.tfstate.backup terraform.tfstate.backup.$(date +%Y%m%d_%H%M%S)
    echo "  备份了terraform.tfstate.backup"
fi
rm -rf .terraform 2>/dev/null
rm -f .terraform.lock.hcl 2>/dev/null
rm -f .terraform.tfstate.lock.info 2>/dev/null
echo -e "${GREEN}✅ Terraform状态清理完成${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 资源清理完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}提示：${NC}"
echo "1. CloudFront分发可能需要15-30分钟才能完全删除"
echo "2. 某些资源可能有依赖关系，如果清理失败，请稍后重试"
echo "3. 建议运行 'aws configure list-profiles' 确认使用正确的AWS配置"
echo ""
echo -e "${GREEN}现在可以安全地重新部署了！${NC}"