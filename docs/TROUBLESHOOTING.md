# 🔍 故障排除指南 - AI PPT Assistant

本文档包含常见问题的诊断和解决方案。

## 📋 目录

- [部署相关问题](#部署相关问题)
- [API Gateway问题](#api-gateway问题)
- [Lambda函数问题](#lambda函数问题)
- [配置和环境问题](#配置和环境问题)
- [Bedrock服务问题](#bedrock服务问题)
- [性能问题](#性能问题)
- [调试工具](#调试工具)

## 🚀 部署相关问题

### Terraform部署失败

#### 问题: `Error: Cycle in module dependencies`

**症状**:
```bash
Error: Cycle in module dependencies
Module [A] depends on [B], which depends on [A]
```

**解决方案**:
```bash
# 1. 检查循环依赖
terraform graph > dependency_graph.dot
dot -Tpng dependency_graph.dot -o dependency_graph.png

# 2. 使用重构后的配置
cp infrastructure/main_refactored.tf infrastructure/main.tf

# 3. 重新初始化
terraform init -reconfigure
terraform plan
```

#### 问题: `Resource already exists`

**症状**:
```bash
Error: Resource "aws_s3_bucket.presentations" already exists
```

**解决方案**:
```bash
# 1. 导入已存在的资源
terraform import aws_s3_bucket.presentations bucket-name

# 2. 或删除冲突资源并重新创建
aws s3 rm s3://bucket-name --recursive
aws s3api delete-bucket --bucket bucket-name
terraform apply
```

### Lambda部署失败

#### 问题: `Invalid handler specified`

**症状**:
```bash
Error: Invalid handler specified: handler.lambda_handler
```

**解决方案**:
```bash
# 1. 检查handler文件结构
ls -la lambdas/session_manager/
# 应该包含: handler.py, requirements.txt

# 2. 验证handler函数
grep -n "lambda_handler" lambdas/session_manager/handler.py

# 3. 使用自动部署脚本
python deploy_lambda_functions.py
```

#### 问题: `Package too large`

**症状**:
```bash
Error: Unzipped size must be smaller than 262144000 bytes
```

**解决方案**:
```bash
# 1. 检查包大小
cd lambdas/session_manager
du -sh .

# 2. 排除不必要文件
echo "__pycache__/" >> .lambdaignore
echo "*.pyc" >> .lambdaignore
echo "tests/" >> .lambdaignore

# 3. 使用Lambda层
python deploy_lambda_functions.py --use-layers
```

## 🌐 API Gateway问题

### CORS错误

#### 问题: `Access-Control-Allow-Origin header is missing`

**症状**:
浏览器控制台显示CORS错误

**解决方案**:
```bash
# 1. 重新配置API Gateway CORS
python configure_api_gateway.py --enable-cors

# 2. 手动验证CORS配置
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/sessions
```

### API路由错误

#### 问题: `Missing Authentication Token`

**症状**:
```json
{
  "message": "Missing Authentication Token"
}
```

**解决方案**:
```bash
# 1. 检查API配置
aws apigateway get-rest-apis

# 2. 验证路由配置
python -c "
import json
with open('api_gateway_configuration.json', 'r') as f:
    config = json.load(f)
    print('Configured endpoints:')
    for endpoint in config.get('endpoints', []):
        print(f'  {endpoint[\"method\"]} {endpoint[\"resource_path\"]}')
"

# 3. 重新部署API
python configure_api_gateway.py --redeploy
```

## 🔧 Lambda函数问题

### 运行时错误

#### 问题: `Module not found`

**症状**:
```
[ERROR] Runtime.ImportModuleError: Unable to import module 'handler': No module named 'enhanced_config_manager'
```

**解决方案**:
```bash
# 1. 验证Lambda层
aws lambda list-layers

# 2. 检查依赖打包
cd lambdas/layers/shared/python
python -c "import enhanced_config_manager; print('Import successful')"

# 3. 重新部署层
python deploy_lambda_functions.py --update-layers
```

#### 问题: `Task timed out`

**症状**:
```
[ERROR] Task timed out after 30.00 seconds
```

**解决方案**:
```bash
# 1. 增加超时时间
aws lambda update-function-configuration \
    --function-name session_manager \
    --timeout 60

# 2. 检查函数性能
python -c "
import boto3
client = boto3.client('cloudwatch')
response = client.get_metric_statistics(
    Namespace='AWS/Lambda',
    MetricName='Duration',
    Dimensions=[{'Name': 'FunctionName', 'Value': 'session_manager'}],
    StartTime='2025-09-05T00:00:00Z',
    EndTime='2025-09-05T23:59:59Z',
    Period=300,
    Statistics=['Average', 'Maximum']
)
for point in response['Datapoints']:
    print(f'{point[\"Timestamp\"]}: {point[\"Average\"]:.2f}ms')
"

# 3. 优化代码性能
# 参考performance_optimization.md
```

### 权限问题

#### 问题: `Access denied`

**症状**:
```
[ERROR] botocore.exceptions.ClientError: An error occurred (AccessDenied) when calling the PutItem operation
```

**解决方案**:
```bash
# 1. 检查IAM角色
aws iam get-role --role-name lambda-execution-role

# 2. 添加必要权限
aws iam attach-role-policy \
    --role-name lambda-execution-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# 3. 验证资源策略
aws dynamodb describe-table --table-name ai-ppt-assistant-dev-sessions
```

## ⚙️ 配置和环境问题

### 配置加载失败

#### 问题: `Configuration key not found`

**症状**:
```
[ERROR] KeyError: 'BUCKET_NAME'
```

**解决方案**:
```bash
# 1. 验证配置文件
python -c "
from lambdas.layers.shared.python.enhanced_config_manager import EnhancedConfigManager
config = EnhancedConfigManager('dev')
print('Available configs:')
validation = config.validate_config()
for key, status in validation.items():
    print(f'  {key}: {\"✅\" if status else \"❌\"}')
"

# 2. 检查环境变量
env | grep -E "(BUCKET_NAME|TABLE_NAME|REGION)"

# 3. 更新配置
python -c "
import yaml
with open('config/environments/dev.yaml', 'r') as f:
    config = yaml.safe_load(f)
print('Current config:', config)
"
```

### 环境变量问题

#### 问题: `AWS region not configured`

**症状**:
```
[ERROR] You must specify a region
```

**解决方案**:
```bash
# 1. 设置AWS区域
export AWS_DEFAULT_REGION=us-east-1
export BEDROCK_REGION=us-east-1

# 2. 验证AWS配置
aws configure list

# 3. 更新Lambda环境变量
aws lambda update-function-configuration \
    --function-name session_manager \
    --environment Variables='{\"BEDROCK_REGION\":\"us-east-1\"}'
```

## 🤖 Bedrock服务问题

### 模型访问问题

#### 问题: `Model access denied`

**症状**:
```
[ERROR] botocore.exceptions.ClientError: An error occurred (AccessDeniedException) when calling the InvokeModel operation: Your account is not authorized to invoke this model.
```

**解决方案**:
```bash
# 1. 检查模型访问权限
aws bedrock list-foundation-models --region us-east-1

# 2. 申请模型访问权限
# 登录AWS控制台 → Bedrock → Model access → Request access

# 3. 验证权限状态
python -c "
import boto3
client = boto3.client('bedrock', region_name='us-east-1')
try:
    response = client.list_foundation_models()
    accessible_models = [m['modelId'] for m in response['modelSummaries']]
    print('Accessible models:')
    for model in accessible_models:
        print(f'  {model}')
except Exception as e:
    print(f'Error: {e}')
"
```

### 调用限制问题

#### 问题: `Throttling exception`

**症状**:
```
[ERROR] ThrottlingException: Request was throttled due to request rate
```

**解决方案**:
```python
# 在Lambda函数中添加重试逻辑
import time
import boto3
from botocore.exceptions import ClientError

def invoke_bedrock_with_retry(client, **kwargs):
    max_retries = 3
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            return client.invoke_model(**kwargs)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
            raise e
```

## 📈 性能问题

### Lambda冷启动

#### 问题: 函数冷启动时间过长

**解决方案**:
```python
# 1. 预热函数
import boto3

def warm_up_functions():
    """预热所有Lambda函数"""
    lambda_client = boto3.client('lambda')
    functions = [
        'session_manager',
        'ppt_generator',
        'content_enhancer'
    ]
    
    for func in functions:
        try:
            lambda_client.invoke(
                FunctionName=func,
                InvocationType='RequestResponse',
                Payload='{"warmup": true}'
            )
        except Exception as e:
            print(f"预热{func}失败: {e}")
```

### DynamoDB性能

#### 问题: 读写操作延迟过高

**解决方案**:
```bash
# 1. 检查DynamoDB指标
aws cloudwatch get-metric-statistics \
    --namespace AWS/DynamoDB \
    --metric-name SuccessfulRequestLatency \
    --dimensions Name=TableName,Value=ai-ppt-assistant-dev-sessions \
    --start-time 2025-09-05T00:00:00Z \
    --end-time 2025-09-05T23:59:59Z \
    --period 300 \
    --statistics Average

# 2. 优化DynamoDB配置
aws dynamodb update-table \
    --table-name ai-ppt-assistant-dev-sessions \
    --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10

# 3. 添加DAX缓存(可选)
# 参考deployment指南中的DAX配置
```

## 🔧 调试工具

### 日志查看

```bash
# 查看Lambda函数日志
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/"

# 实时查看日志
aws logs tail /aws/lambda/session_manager --follow

# 过滤错误日志
aws logs filter-log-events \
    --log-group-name "/aws/lambda/session_manager" \
    --filter-pattern "ERROR"
```

### 性能监控

```python
# CloudWatch自定义指标
import boto3
from datetime import datetime

def put_custom_metric(metric_name, value, unit='Count'):
    """发送自定义指标到CloudWatch"""
    cloudwatch = boto3.client('cloudwatch')
    
    cloudwatch.put_metric_data(
        Namespace='AI-PPT-Assistant',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
        ]
    )

# 使用示例
put_custom_metric('SessionCreated', 1)
put_custom_metric('ResponseTime', 150, 'Milliseconds')
```

### 本地测试

```bash
# 1. 设置本地环境
export AWS_PROFILE=your-profile
export ENVIRONMENT=dev

# 2. 本地测试Lambda函数
cd lambdas/session_manager
python -c "
import json
from handler import lambda_handler

event = {
    'httpMethod': 'POST',
    'body': json.dumps({
        'user_id': 'test_user',
        'project_name': 'test_project'
    })
}

result = lambda_handler(event, {})
print(json.dumps(result, indent=2))
"

# 3. API测试
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/sessions \
     -H "Content-Type: application/json" \
     -d '{"user_id": "test_user", "project_name": "test_project"}'
```

## 🚨 紧急问题处理

### 服务完全无响应

```bash
# 1. 快速健康检查
python -c "
import boto3
import json

# 检查关键服务状态
services = {
    'lambda': boto3.client('lambda'),
    'apigateway': boto3.client('apigateway'),
    'dynamodb': boto3.client('dynamodb')
}

for service, client in services.items():
    try:
        if service == 'lambda':
            response = client.list_functions(MaxItems=1)
        elif service == 'apigateway':
            response = client.get_rest_apis(limit=1)
        elif service == 'dynamodb':
            response = client.list_tables(Limit=1)
        print(f'✅ {service}: 正常')
    except Exception as e:
        print(f'❌ {service}: {e}')
"

# 2. 回滚到稳定版本
git checkout main
python deploy_lambda_functions.py --force-update

# 3. 启用详细日志
aws logs put-retention-policy \
    --log-group-name "/aws/lambda/session_manager" \
    --retention-in-days 7
```

## 📞 获取帮助

如果上述解决方案无法解决您的问题：

1. **检查日志**: 详细查看CloudWatch日志
2. **查看监控**: 检查CloudWatch指标和报警
3. **测试隔离**: 逐个组件测试定位问题
4. **联系支持**: 创建GitHub Issue并附上详细日志

---

📅 **最后更新**: 2025-09-05 | ✅ **文档状态**: 生产就绪