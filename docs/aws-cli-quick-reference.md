# AWS CLI参数获取快速参考

## 🚀 快速命令

### Lambda函数
```bash
# 列出所有Lambda函数及其基本参数
aws lambda list-functions --query 'Functions[*].[FunctionName,Runtime,MemorySize,Timeout]' --output table

# 获取特定函数的详细配置
aws lambda get-function-configuration --function-name <function-name>

# 获取函数的环境变量
aws lambda get-function-configuration --function-name <function-name> --query 'Environment.Variables'

# 获取函数的层信息
aws lambda get-function --function-name <function-name> --query 'Configuration.Layers'

# 获取函数的并发配置
aws lambda get-function-concurrency --function-name <function-name>
```

### API Gateway
```bash
# 列出所有REST API
aws apigateway get-rest-apis --query 'items[*].[name,id,endpointConfiguration.types[0]]' --output table

# 获取API的资源和路径
aws apigateway get-resources --rest-api-id <api-id> --query 'items[*].[path,resourceMethods]' --output table

# 获取API的部署阶段
aws apigateway get-stages --rest-api-id <api-id>

# 获取API的使用计划
aws apigateway get-usage-plans --query 'items[*].[name,throttle,quota]' --output table

# 获取API的自定义域名
aws apigateway get-domain-names
```

### DynamoDB
```bash
# 列出所有表
aws dynamodb list-tables

# 获取表的详细配置
aws dynamodb describe-table --table-name <table-name>

# 获取表的容量和性能指标
aws dynamodb describe-table --table-name <table-name> --query 'Table.[TableStatus,ItemCount,TableSizeBytes,ProvisionedThroughput]'

# 获取表的索引信息
aws dynamodb describe-table --table-name <table-name> --query 'Table.GlobalSecondaryIndexes'

# 获取表的备份设置
aws dynamodb describe-continuous-backups --table-name <table-name>

# 获取表的TTL设置
aws dynamodb describe-time-to-live --table-name <table-name>
```

### S3存储桶
```bash
# 列出所有存储桶
aws s3api list-buckets --query 'Buckets[*].[Name,CreationDate]' --output table

# 获取存储桶的地理位置
aws s3api get-bucket-location --bucket <bucket-name>

# 获取存储桶的版本控制状态
aws s3api get-bucket-versioning --bucket <bucket-name>

# 获取存储桶的加密配置
aws s3api get-bucket-encryption --bucket <bucket-name>

# 获取存储桶的CORS配置
aws s3api get-bucket-cors --bucket <bucket-name>

# 获取存储桶的生命周期策略
aws s3api get-bucket-lifecycle-configuration --bucket <bucket-name>

# 获取存储桶的访问控制列表
aws s3api get-bucket-acl --bucket <bucket-name>
```

### SQS队列
```bash
# 列出所有队列
aws sqs list-queues

# 获取队列的所有属性
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names All

# 获取队列的基本配置
aws sqs get-queue-attributes --queue-url <queue-url> \
  --attribute-names DelaySeconds MessageRetentionPeriod MaximumMessageSize VisibilityTimeout

# 获取死信队列配置
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names RedrivePolicy
```

### VPC和网络
```bash
# 获取VPC信息
aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,CidrBlock,State,Tags[?Key==`Name`].Value|[0]]' --output table

# 获取子网信息
aws ec2 describe-subnets --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,MapPublicIpOnLaunch]' --output table

# 获取安全组规则
aws ec2 describe-security-groups --group-ids <sg-id> --query 'SecurityGroups[*].[GroupName,IpPermissions,IpPermissionsEgress]'

# 获取路由表
aws ec2 describe-route-tables --query 'RouteTables[*].[RouteTableId,Routes]' --output table

# 获取NAT网关
aws ec2 describe-nat-gateways --query 'NatGateways[*].[NatGatewayId,State,SubnetId,ConnectivityType]' --output table
```

### IAM角色和策略
```bash
# 列出所有角色
aws iam list-roles --query 'Roles[*].[RoleName,CreateDate]' --output table

# 获取角色的详细信息
aws iam get-role --role-name <role-name>

# 获取角色的信任策略
aws iam get-role --role-name <role-name> --query 'Role.AssumeRolePolicyDocument'

# 获取角色附加的策略
aws iam list-attached-role-policies --role-name <role-name>

# 获取策略的详细内容
aws iam get-policy-version --policy-arn <policy-arn> --version-id <version-id>
```

### CloudWatch
```bash
# 获取日志组
aws logs describe-log-groups --query 'logGroups[*].[logGroupName,retentionInDays,storedBytes]' --output table

# 获取指标统计
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<function-name> \
  --start-time 2025-09-10T00:00:00Z \
  --end-time 2025-09-11T00:00:00Z \
  --period 3600 \
  --statistics Average,Maximum

# 获取告警配置
aws cloudwatch describe-alarms --query 'MetricAlarms[*].[AlarmName,MetricName,Threshold,ComparisonOperator]' --output table
```

### Bedrock
```bash
# 列出可用的基础模型
aws bedrock list-foundation-models --query 'modelSummaries[*].[modelId,modelName]' --output table

# 获取模型详情
aws bedrock get-foundation-model --model-identifier <model-id>

# 列出代理
aws bedrock-agent list-agents --query 'agentSummaries[*].[agentName,agentId,agentStatus]' --output table

# 获取代理详情
aws bedrock-agent get-agent --agent-id <agent-id>
```

## 💡 实用技巧

### 1. 使用jq处理JSON输出
```bash
# 安装jq
brew install jq  # macOS
sudo apt-get install jq  # Ubuntu/Debian

# 提取特定字段
aws lambda list-functions | jq '.Functions[].FunctionName'

# 过滤和格式化
aws lambda list-functions | jq '.Functions[] | {name: .FunctionName, memory: .MemorySize}'
```

### 2. 导出为不同格式
```bash
# 导出为CSV
aws lambda list-functions --output text --query 'Functions[*].[FunctionName,Runtime,MemorySize]' | tr '\t' ','

# 导出为表格
aws lambda list-functions --output table

# 导出为YAML (需要yq工具)
aws lambda list-functions --output json | yq -y .
```

### 3. 批量处理
```bash
# 批量获取所有Lambda函数的配置
for func in $(aws lambda list-functions --query 'Functions[*].FunctionName' --output text); do
    echo "Processing: $func"
    aws lambda get-function-configuration --function-name $func > "lambda_${func}.json"
done
```

### 4. 使用过滤器
```bash
# 只获取Python Lambda函数
aws lambda list-functions --query "Functions[?Runtime=='python3.12'].[FunctionName,Runtime]"

# 获取大于1GB内存的函数
aws lambda list-functions --query "Functions[?MemorySize>'1024'].[FunctionName,MemorySize]"
```

### 5. 组合命令
```bash
# 获取Lambda函数和其关联的API Gateway
FUNCTION_NAME="your-function"
aws lambda get-function --function-name $FUNCTION_NAME | \
  jq -r '.Configuration.FunctionArn' | \
  xargs -I {} aws apigateway get-rest-apis --query "items[?contains(description, '{}')]" 
```

## 📄 生成文档模板

### Markdown表格生成
```bash
# 生成Lambda函数表格
echo "| Function Name | Runtime | Memory | Timeout |"
echo "|---------------|---------|--------|--------|"
aws lambda list-functions --query 'Functions[*].[FunctionName,Runtime,MemorySize,Timeout]' --output text | \
  while read name runtime memory timeout; do
    echo "| $name | $runtime | $memory MB | $timeout s |"
  done
```

### 导出为Excel可读格式
```bash
# 创建TSV文件（可直接导入Excel）
aws lambda list-functions \
  --query 'Functions[*].[FunctionName,Runtime,MemorySize,Timeout,LastModified]' \
  --output text > lambda_functions.tsv
```

## 🔗 相关资源

- [AWS CLI Command Reference](https://docs.aws.amazon.com/cli/latest/reference/)
- [JQ Manual](https://stedolan.github.io/jq/manual/)
- [AWS CLI Query Tutorial](https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-filter.html)