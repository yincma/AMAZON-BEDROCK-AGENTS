# 🚨 AI PPT Assistant 故障排查指南

## 📋 更新记录
**最后更新**: 2024-09-14
**版本**: 1.0

## 快速诊断清单

### ✅ 已解决的常见问题

#### 1. Lambda Handler 错误
**症状**: CloudWatch日志显示 "Unable to import module 'lambda_function'"

**根本原因**: Handler配置不正确

**解决方案**:
```hcl
# 错误配置
handler = "handler"  # ❌

# 正确配置
handler = "lambda_function.lambda_handler"  # ✅
```

**验证方法**:
```bash
# 检查Lambda函数配置
aws lambda get-function-configuration --function-name ai-ppt-generate | grep Handler

# 应该返回: "Handler": "lambda_function.lambda_handler"
```

#### 2. CORS 跨域访问错误
**症状**: 浏览器控制台显示 "Access-Control-Allow-Origin" 错误

**根本原因**: Lambda响应缺少CORS头

**解决方案**:
```python
def lambda_handler(event, context):
    # 处理预检请求
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': ''
        }

    # 正常请求处理
    try:
        result = process_request(event)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps(result)
        }
    except Exception as e:
        return error_response(500, str(e))
```

#### 3. IAM 权限不足
**症状**: Lambda无法访问S3或Bedrock服务

**根本原因**: IAM角色权限配置不完整

**解决方案**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::ai-ppt-storage-*/*",
        "arn:aws:s3:::ai-ppt-storage-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## 常见错误代码及解决方案

### HTTP 错误代码

| 错误代码 | 含义 | 可能原因 | 解决方案 |
|---------|------|---------|---------|
| 400 | Bad Request | 请求参数错误 | 检查请求格式和必填字段 |
| 401 | Unauthorized | 认证失败 | 检查API密钥或认证令牌 |
| 403 | Forbidden | 权限不足 | 检查IAM角色权限 |
| 404 | Not Found | 资源不存在 | 验证presentation_id是否正确 |
| 429 | Too Many Requests | 请求过多 | 实施重试逻辑，增加延迟 |
| 500 | Internal Server Error | 服务器错误 | 查看CloudWatch日志 |
| 502 | Bad Gateway | API Gateway错误 | 检查Lambda函数是否正常运行 |
| 503 | Service Unavailable | 服务不可用 | 检查AWS服务状态 |
| 504 | Gateway Timeout | 超时 | 增加Lambda超时时间 |

### Lambda 错误类型

#### 1. 初始化错误
```python
# 错误示例
INIT_START Runtime Version: python:3.9.v16
[ERROR] Runtime.ImportModuleError: Unable to import module 'lambda_function'

# 解决方案
1. 确保文件名为 lambda_function.py
2. 确保函数名为 lambda_handler
3. 检查依赖包是否正确安装
```

#### 2. 运行时错误
```python
# 错误示例
[ERROR] KeyError: 'body'
Traceback (most recent call last):
  File "/var/task/lambda_function.py", line 10, in lambda_handler
    body = json.loads(event['body'])

# 解决方案
def lambda_handler(event, context):
    # 安全地获取body
    body = event.get('body', '{}')
    if isinstance(body, str):
        body = json.loads(body)
```

#### 3. 超时错误
```python
# 错误示例
Task timed out after 30.03 seconds

# 解决方案
1. 增加Lambda超时时间（最大15分钟）
2. 优化代码性能
3. 使用异步处理模式
```

## 性能问题诊断

### 1. 冷启动延迟
**症状**: 首次请求响应时间长（>3秒）

**诊断命令**:
```bash
# 查看冷启动指标
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=ai-ppt-generate \
  --start-time 2024-09-14T00:00:00Z \
  --end-time 2024-09-14T23:59:59Z \
  --period 3600 \
  --statistics Maximum \
  --query 'Datapoints[?Maximum > `3000`]'
```

**解决方案**:
1. 启用预留并发
2. 使用预配置并发
3. 减少依赖包大小
4. 使用Lambda Layers

### 2. 内存不足
**症状**: Lambda执行缓慢或失败

**诊断命令**:
```bash
# 查看内存使用情况
aws logs filter-log-events \
  --log-group-name /aws/lambda/ai-ppt-generate \
  --filter-pattern '"Memory Used"'
```

**解决方案**:
```hcl
# 增加内存配置
memory_size = 3008  # 获得2个vCPU
```

### 3. 并发限制
**症状**: 部分请求失败，返回429错误

**诊断命令**:
```bash
# 查看并发执行数
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=ai-ppt-generate \
  --start-time 2024-09-14T00:00:00Z \
  --end-time 2024-09-14T23:59:59Z \
  --period 300 \
  --statistics Maximum
```

**解决方案**:
1. 增加预留并发数
2. 实施请求队列
3. 使用SQS进行异步处理

## 日志查询技巧

### CloudWatch Insights 查询示例

#### 1. 查找所有错误
```sql
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

#### 2. 分析请求延迟
```sql
fields @timestamp, @duration
| filter @type = "REPORT"
| stats avg(@duration), max(@duration), min(@duration) by bin(5m)
```

#### 3. 查找特定请求
```sql
fields @timestamp, @message
| filter @message like /presentation_id: "ppt-123456"/
| sort @timestamp asc
```

#### 4. 统计错误类型
```sql
fields @message
| filter @message like /ERROR/
| parse @message /(?<error_type>[\w\.]+Error)/
| stats count() by error_type
```

## 监控和告警设置

### 关键指标监控

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

# 创建告警
def create_alarm(function_name):
    cloudwatch.put_metric_alarm(
        AlarmName=f'{function_name}-error-rate',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=2,
        MetricName='Errors',
        Namespace='AWS/Lambda',
        Period=300,
        Statistic='Sum',
        Threshold=10.0,
        ActionsEnabled=True,
        AlarmActions=['arn:aws:sns:region:account:topic'],
        AlarmDescription='Lambda函数错误率过高',
        Dimensions=[
            {
                'Name': 'FunctionName',
                'Value': function_name
            }
        ]
    )
```

### X-Ray 追踪分析

```bash
# 启用X-Ray追踪
aws lambda update-function-configuration \
  --function-name ai-ppt-generate \
  --tracing-config Mode=Active

# 查看追踪信息
aws xray get-trace-summaries \
  --time-range-type LastHour \
  --query 'TraceSummaries[?Duration > `1`]'
```

## 应急响应流程

### 1. 服务完全不可用
```bash
# 步骤1: 检查AWS服务状态
curl https://status.aws.amazon.com/

# 步骤2: 查看错误日志
aws logs tail /aws/lambda/ai-ppt-generate --follow

# 步骤3: 检查IAM权限
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::account:role/lambda-role \
  --action-names s3:GetObject bedrock:InvokeModel

# 步骤4: 重新部署
cd infrastructure/
terraform plan
terraform apply
```

### 2. 性能严重下降
```bash
# 步骤1: 检查并发执行数
aws lambda get-function-concurrency --function-name ai-ppt-generate

# 步骤2: 增加内存和超时
aws lambda update-function-configuration \
  --function-name ai-ppt-generate \
  --memory-size 3008 \
  --timeout 900

# 步骤3: 清理旧的执行环境
aws lambda update-function-configuration \
  --function-name ai-ppt-generate \
  --environment Variables={FORCE_REFRESH=true}
```

### 3. 大量错误
```bash
# 步骤1: 启用详细日志
aws lambda update-function-configuration \
  --function-name ai-ppt-generate \
  --environment Variables={LOG_LEVEL=DEBUG}

# 步骤2: 查看最近的错误
aws logs filter-log-events \
  --log-group-name /aws/lambda/ai-ppt-generate \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern ERROR

# 步骤3: 回滚到上一个版本
aws lambda update-function-code \
  --function-name ai-ppt-generate \
  --s3-bucket deployment-bucket \
  --s3-key previous-version.zip
```

## 预防措施

### 1. 代码部署前检查
```bash
#!/bin/bash
# pre-deploy-check.sh

# 检查Python语法
python -m py_compile lambda_function.py

# 运行单元测试
pytest tests/

# 检查依赖包
pip check

# 验证Handler配置
grep -q "def lambda_handler" lambda_function.py || echo "Warning: lambda_handler not found"
```

### 2. 健康检查端点
```python
def lambda_handler(event, context):
    # 健康检查
    if event.get('path') == '/health':
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat()
            })
        }
```

### 3. 自动恢复机制
```python
import time
from functools import wraps

def retry_on_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

@retry_on_error(max_retries=3)
def call_bedrock(prompt):
    # Bedrock调用逻辑
    pass
```

## 联系支持

### 内部支持
- **Slack频道**: #ai-ppt-support
- **邮件**: ai-ppt-team@company.com
- **值班电话**: +1-xxx-xxx-xxxx

### AWS支持
- **AWS Support Center**: https://console.aws.amazon.com/support/
- **AWS Service Health Dashboard**: https://status.aws.amazon.com/

### 文档和资源
- **项目Wiki**: [内部链接]
- **API文档**: /docs/api/
- **架构图**: /docs/architecture/
- **运维手册**: /docs/operations/

## 附录：常用命令速查

```bash
# Lambda函数操作
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `ai-ppt`)]'
aws lambda get-function --function-name ai-ppt-generate
aws lambda invoke --function-name ai-ppt-generate output.json

# 日志查询
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/ai-ppt
aws logs tail /aws/lambda/ai-ppt-generate --follow
aws logs get-log-events --log-group-name /aws/lambda/ai-ppt-generate --log-stream-name 'latest'

# S3操作
aws s3 ls s3://ai-ppt-storage-account-id/
aws s3 cp test.pptx s3://ai-ppt-storage-account-id/presentations/
aws s3 presign s3://ai-ppt-storage-account-id/presentations/test.pptx

# API Gateway
aws apigateway get-rest-apis
aws apigateway get-stages --rest-api-id api-id
aws apigateway get-deployment --rest-api-id api-id --deployment-id deployment-id

# CloudWatch指标
aws cloudwatch list-metrics --namespace AWS/Lambda
aws cloudwatch get-metric-data --metric-data-queries file://queries.json
```

---

**文档版本**: 1.0
**最后更新**: 2024-09-14
**维护团队**: AI PPT Development Team