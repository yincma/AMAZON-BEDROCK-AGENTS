#!/bin/bash

# AWS参数收集脚本 - 用于详细设计书
# 使用方法: ./get_aws_parameters.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 输出目录
OUTPUT_DIR="aws_parameters_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo -e "${GREEN}=== AWS服务参数收集工具 ===${NC}"
echo -e "输出目录: ${YELLOW}$OUTPUT_DIR${NC}"

# 1. Lambda函数参数
echo -e "\n${YELLOW}[1/8] 收集Lambda函数参数...${NC}"
aws lambda list-functions \
    --query 'Functions[*].{FunctionName:FunctionName,Runtime:Runtime,MemorySize:MemorySize,Timeout:Timeout,Handler:Handler,Environment:Environment}' \
    --output json > "$OUTPUT_DIR/lambda_functions.json"

# 获取每个Lambda函数的详细配置
for func in $(aws lambda list-functions --query 'Functions[*].FunctionName' --output text); do
    echo "  - 获取函数详情: $func"
    aws lambda get-function-configuration --function-name "$func" \
        --output json > "$OUTPUT_DIR/lambda_${func}_config.json"
done

# 2. API Gateway参数
echo -e "\n${YELLOW}[2/8] 收集API Gateway参数...${NC}"
for api_id in $(aws apigateway get-rest-apis --query 'items[*].id' --output text); do
    api_name=$(aws apigateway get-rest-api --rest-api-id "$api_id" --query 'name' --output text)
    echo "  - 获取API配置: $api_name ($api_id)"
    
    # 获取API详情
    aws apigateway get-rest-api --rest-api-id "$api_id" \
        --output json > "$OUTPUT_DIR/api_${api_name}_details.json"
    
    # 获取资源和方法
    aws apigateway get-resources --rest-api-id "$api_id" \
        --output json > "$OUTPUT_DIR/api_${api_name}_resources.json"
    
    # 获取部署阶段
    aws apigateway get-stages --rest-api-id "$api_id" \
        --output json > "$OUTPUT_DIR/api_${api_name}_stages.json" 2>/dev/null || true
done

# 3. DynamoDB表参数
echo -e "\n${YELLOW}[3/8] 收集DynamoDB表参数...${NC}"
for table in $(aws dynamodb list-tables --query 'TableNames[*]' --output text); do
    echo "  - 获取表配置: $table"
    aws dynamodb describe-table --table-name "$table" \
        --output json > "$OUTPUT_DIR/dynamodb_${table}.json"
done

# 4. S3存储桶参数
echo -e "\n${YELLOW}[4/8] 收集S3存储桶参数...${NC}"
for bucket in $(aws s3api list-buckets --query 'Buckets[*].Name' --output text); do
    echo "  - 获取存储桶配置: $bucket"
    
    # 基本配置
    aws s3api get-bucket-location --bucket "$bucket" \
        --output json > "$OUTPUT_DIR/s3_${bucket}_location.json" 2>/dev/null || true
    
    # 版本控制
    aws s3api get-bucket-versioning --bucket "$bucket" \
        --output json > "$OUTPUT_DIR/s3_${bucket}_versioning.json" 2>/dev/null || true
    
    # 加密配置
    aws s3api get-bucket-encryption --bucket "$bucket" \
        --output json > "$OUTPUT_DIR/s3_${bucket}_encryption.json" 2>/dev/null || true
    
    # 生命周期策略
    aws s3api get-bucket-lifecycle-configuration --bucket "$bucket" \
        --output json > "$OUTPUT_DIR/s3_${bucket}_lifecycle.json" 2>/dev/null || true
done

# 5. SQS队列参数
echo -e "\n${YELLOW}[5/8] 收集SQS队列参数...${NC}"
for queue_url in $(aws sqs list-queues --query 'QueueUrls[*]' --output text); do
    queue_name=$(echo "$queue_url" | rev | cut -d'/' -f1 | rev)
    echo "  - 获取队列配置: $queue_name"
    aws sqs get-queue-attributes --queue-url "$queue_url" \
        --attribute-names All \
        --output json > "$OUTPUT_DIR/sqs_${queue_name}.json"
done

# 6. VPC和网络参数
echo -e "\n${YELLOW}[6/8] 收集VPC和网络参数...${NC}"
# VPC
aws ec2 describe-vpcs --output json > "$OUTPUT_DIR/vpc_all.json"
# 子网
aws ec2 describe-subnets --output json > "$OUTPUT_DIR/subnets_all.json"
# 安全组
aws ec2 describe-security-groups --output json > "$OUTPUT_DIR/security_groups_all.json"
# NAT网关
aws ec2 describe-nat-gateways --output json > "$OUTPUT_DIR/nat_gateways_all.json"
# Internet网关
aws ec2 describe-internet-gateways --output json > "$OUTPUT_DIR/internet_gateways_all.json"

# 7. IAM角色和策略
echo -e "\n${YELLOW}[7/8] 收集IAM角色和策略参数...${NC}"
# 列出Lambda相关的角色
for role in $(aws iam list-roles --query "Roles[?contains(RoleName, 'lambda') || contains(RoleName, 'Lambda')].RoleName" --output text); do
    echo "  - 获取角色配置: $role"
    aws iam get-role --role-name "$role" \
        --output json > "$OUTPUT_DIR/iam_role_${role}.json"
    
    # 获取附加的策略
    aws iam list-attached-role-policies --role-name "$role" \
        --output json > "$OUTPUT_DIR/iam_role_${role}_policies.json"
done

# 8. CloudWatch日志组
echo -e "\n${YELLOW}[8/8] 收集CloudWatch日志组参数...${NC}"
aws logs describe-log-groups \
    --query 'logGroups[*].{LogGroupName:logGroupName,RetentionInDays:retentionInDays,StoredBytes:storedBytes}' \
    --output json > "$OUTPUT_DIR/cloudwatch_log_groups.json"

# 生成汇总报告
echo -e "\n${GREEN}生成汇总报告...${NC}"
cat > "$OUTPUT_DIR/summary.md" << EOF
# AWS服务参数汇总报告

生成时间: $(date '+%Y-%m-%d %H:%M:%S')

## 收集的服务

1. **Lambda函数**
   - 文件: lambda_*.json
   - 包含: 函数配置、环境变量、超时设置、内存配置

2. **API Gateway**
   - 文件: api_*.json
   - 包含: API定义、资源路径、集成配置、部署阶段

3. **DynamoDB**
   - 文件: dynamodb_*.json
   - 包含: 表结构、索引、容量设置、流配置

4. **S3存储桶**
   - 文件: s3_*.json
   - 包含: 位置、版本控制、加密、生命周期策略

5. **SQS队列**
   - 文件: sqs_*.json
   - 包含: 队列属性、消息保留、死信队列配置

6. **VPC和网络**
   - 文件: vpc_*.json, subnets_*.json, security_groups_*.json
   - 包含: VPC配置、子网、安全组规则、网关

7. **IAM角色和策略**
   - 文件: iam_*.json
   - 包含: 角色定义、信任关系、附加策略

8. **CloudWatch日志**
   - 文件: cloudwatch_*.json
   - 包含: 日志组、保留期、存储大小

## 使用说明

1. 所有参数以JSON格式保存，便于程序化处理
2. 可使用jq工具查询特定参数：
   \`\`\`bash
   jq '.FunctionConfiguration.MemorySize' lambda_*_config.json
   \`\`\`
3. 可以导入到Excel或其他工具中进行分析

EOF

echo -e "\n${GREEN}✅ 参数收集完成！${NC}"
echo -e "输出目录: ${YELLOW}$OUTPUT_DIR${NC}"
echo -e "查看汇总: ${YELLOW}cat $OUTPUT_DIR/summary.md${NC}"
echo -e "\n提示: 使用 'jq' 工具可以更好地处理JSON文件"
echo -e "示例: jq '.Functions[0]' $OUTPUT_DIR/lambda_functions.json"