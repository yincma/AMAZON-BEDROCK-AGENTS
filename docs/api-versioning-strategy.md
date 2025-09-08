# API Version Control Strategy
# AI PPT Assistant - API版本控制策略文档

## 概述

本文档描述了AI PPT Assistant项目的API版本控制策略，包括版本化方案、向后兼容性处理、版本迁移和弃用策略。

## 版本化策略

### 1. 路径版本化（Path Versioning）

我们采用URL路径前缀的版本化方案：

```
# 版本化API端点结构
https://api-gateway-id.execute-api.region.amazonaws.com/{version}/{resource}

# 示例
https://abc123.execute-api.us-east-1.amazonaws.com/v1/presentations
https://abc123.execute-api.us-east-1.amazonaws.com/v2/presentations
```

### 2. 版本生命周期

每个API版本都有明确的生命周期状态：

- **active**: 活跃版本，完全支持
- **deprecated**: 已弃用版本，仍然支持但不推荐使用
- **retired**: 退休版本，不再支持

### 3. 版本配置

```hcl
api_versions = {
  v1 = {
    version_name     = "v1"
    description      = "API Version 1 - Legacy endpoints for backward compatibility"
    stage_name       = "v1"
    is_default       = true
    status          = "active"
    deprecation_date = "2026-12-31"
    lambda_mappings  = {
      "generate_presentation" = "generate_presentation"
      "presentation_status"   = "presentation_status"
      # ... 其他映射
    }
  }
  v2 = {
    version_name     = "v2"
    description      = "API Version 2 - Enhanced endpoints"
    stage_name       = "v2"
    is_default       = false
    status          = "active"
    deprecation_date = ""
    lambda_mappings  = {
      "generate_presentation" = "generate_presentation_v2"  # 可以指向不同的Lambda
      "presentation_status"   = "presentation_status_v2"
      # ... 其他映射
    }
  }
}
```

## API端点映射

### 当前支持的版本化端点

| 功能 | V1 端点 | V2 端点 | 说明 |
|------|---------|---------|------|
| 生成演示文稿 | `POST /v1/presentations` | `POST /v2/presentations` | V2可能包含增强功能 |
| 获取演示状态 | `GET /v1/presentations/{id}` | `GET /v2/presentations/{id}` | V2可能返回更详细信息 |
| 下载演示文稿 | `GET /v1/presentations/{id}/download` | `GET /v2/presentations/{id}/download` | 相同功能 |
| 修改幻灯片 | `PATCH /v1/presentations/{id}/slides/{slideId}` | `PATCH /v2/presentations/{id}/slides/{slideId}` | V2可能支持更多修改类型 |
| 获取任务状态 | `GET /v1/tasks/{task_id}` | `GET /v2/tasks/{task_id}` | V2可能包含更多任务信息 |
| 列出演示文稿 | `GET /v1/presentations` | `GET /v2/presentations` | V2可能支持更多过滤选项 |
| 健康检查 | `GET /v1/health` | `GET /v2/health` | 版本特定的健康状态 |

## Lambda函数映射策略

### 1. 共享Lambda函数
对于功能相同的端点，可以共享同一个Lambda函数：

```hcl
lambda_mappings = {
  "presentation_download" = "presentation_download"  # V1和V2使用相同函数
}
```

### 2. 版本特定Lambda函数
对于功能增强的端点，可以使用不同的Lambda函数：

```hcl
# V1
lambda_mappings = {
  "generate_presentation" = "generate_presentation"
}

# V2
lambda_mappings = {
  "generate_presentation" = "generate_presentation_v2"  # 增强版本
}
```

### 3. Lambda函数内版本检测
在Lambda函数内部通过请求路径检测版本：

```python
def handler(event, context):
    # 从请求路径中提取版本信息
    path = event.get('requestContext', {}).get('resourcePath', '')
    version = 'v1'  # 默认版本
    
    if path.startswith('/v2/'):
        version = 'v2'
    elif path.startswith('/v1/'):
        version = 'v1'
    
    # 根据版本执行不同逻辑
    if version == 'v2':
        return handle_v2_request(event, context)
    else:
        return handle_v1_request(event, context)
```

## 阶段管理（Stage Management）

### 多环境部署

支持多个环境阶段，每个版本都有对应的阶段：

```hcl
api_stages = {
  dev = {
    stage_name           = "dev"
    description          = "Development stage for testing"
    cache_enabled        = false
    throttle_rate_limit  = 50
    throttle_burst_limit = 100
    log_level           = "INFO"
    data_trace_enabled  = true
  }
  staging = {
    stage_name           = "staging"
    description          = "Staging stage for pre-production testing"
    cache_enabled        = true
    throttle_rate_limit  = 100
    throttle_burst_limit = 200
    log_level           = "ERROR"
  }
  prod = {
    stage_name           = "prod"
    description          = "Production stage"
    cache_enabled        = true
    throttle_rate_limit  = 200
    throttle_burst_limit = 400
    log_level           = "ERROR"
  }
}
```

### 环境特定配置

- **开发环境 (dev)**: 启用详细日志和数据跟踪，不启用缓存
- **预生产环境 (staging)**: 启用缓存，中等限流，错误级别日志
- **生产环境 (prod)**: 启用缓存，高限流，仅错误日志

## 向后兼容性处理

### 1. 响应头部版本信息

所有版本化端点都会返回版本相关的响应头：

```http
API-Version: v1
Deprecation-Date: 2026-12-31
```

### 2. 内容协商

支持通过Accept头部指定期望的响应格式：

```http
Accept: application/vnd.ai-ppt-assistant.v1+json
Accept: application/vnd.ai-ppt-assistant.v2+json
```

### 3. 默认版本重定向

为了支持现有客户端，提供根级别API重定向到默认版本：

```http
GET /presentations
# 自动重定向到
GET /v1/presentations
```

### 4. 错误响应兼容性

确保不同版本的错误响应格式保持兼容：

```json
{
  "error": "VALIDATION_ERROR",
  "message": "请求参数验证失败",
  "request_id": "12345",
  "timestamp": "2025-09-07T10:00:00Z",
  "api_version": "v1"
}
```

## 版本迁移策略

### 1. 迁移计划

| 阶段 | 时间线 | 活动 |
|------|--------|------|
| 准备期 | 发布前2个月 | 发布迁移指南，更新文档 |
| 共存期 | 发布后6个月 | V1和V2并行运行 |
| 弃用期 | 发布后12个月 | 标记V1为deprecated |
| 退休期 | 发布后18个月 | 停止支持V1 |

### 2. 客户端迁移支持

#### 2.1 迁移检查工具

创建检查工具帮助客户端识别需要迁移的API调用：

```bash
# 示例：检查API调用日志中的版本使用情况
curl -X GET "https://api.example.com/v1/health" \
  -H "X-Migration-Check: true"
```

#### 2.2 迁移指南

为每个端点提供详细的迁移指南：

```markdown
## 从V1迁移到V2

### 演示文稿生成 API

**V1 请求:**
```json
POST /v1/presentations
{
  "title": "我的演示",
  "topic": "AI技术介绍"
}
```

**V2 请求:**
```json
POST /v2/presentations
{
  "title": "我的演示",
  "topic": "AI技术介绍",
  "template": "technology_showcase",  // 新增：模板选择
  "options": {                       // 新增：更多选项
    "include_animations": true,
    "style_preset": "modern"
  }
}
```
```

#### 2.3 并行测试

提供并行测试功能，允许客户端同时测试V1和V2：

```javascript
// 并行测试示例
const testEndpoint = async (version) => {
  const response = await fetch(`/api/${version}/presentations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Test-Mode': 'parallel'
    },
    body: JSON.stringify(requestData)
  });
  return response.json();
};

// 同时测试两个版本
Promise.all([
  testEndpoint('v1'),
  testEndpoint('v2')
]).then(results => {
  console.log('V1 Result:', results[0]);
  console.log('V2 Result:', results[1]);
});
```

## 版本弃用策略

### 1. 弃用通知

#### 1.1 响应头通知

```http
HTTP/1.1 200 OK
API-Version: v1
Deprecation-Date: 2026-12-31
Link: </docs/migration/v1-to-v2>; rel="migration-guide"
Warning: 299 - "API version v1 is deprecated. Please migrate to v2. Support ends on 2026-12-31"
```

#### 1.2 响应体通知

```json
{
  "data": { ... },
  "_metadata": {
    "api_version": "v1",
    "deprecation": {
      "deprecated": true,
      "sunset_date": "2026-12-31",
      "migration_guide": "https://docs.example.com/migration/v1-to-v2"
    }
  }
}
```

### 2. 弃用时间线

```
发布V2: 2025-09-07
├─ 并行期 (6个月): 2025-09-07 ~ 2026-03-07
│  ├─ V1: active
│  └─ V2: active
├─ 弃用期 (6个月): 2026-03-07 ~ 2026-09-07
│  ├─ V1: deprecated (警告通知)
│  └─ V2: active
├─ 日落期 (3个月): 2026-09-07 ~ 2026-12-07
│  ├─ V1: deprecated (强制通知)
│  └─ V2: active
└─ 退休期: 2026-12-07+
   ├─ V1: retired (停止服务)
   └─ V2: active
```

### 3. 监控和告警

#### 3.1 弃用使用情况监控

```python
# CloudWatch自定义指标
import boto3

def track_deprecated_api_usage(version, endpoint):
    cloudwatch = boto3.client('cloudwatch')
    
    cloudwatch.put_metric_data(
        Namespace='API/Deprecation',
        MetricData=[
            {
                'MetricName': 'DeprecatedAPIUsage',
                'Dimensions': [
                    {'Name': 'Version', 'Value': version},
                    {'Name': 'Endpoint', 'Value': endpoint}
                ],
                'Value': 1,
                'Unit': 'Count'
            }
        ]
    )
```

#### 3.2 弃用告警

```hcl
resource "aws_cloudwatch_metric_alarm" "deprecated_api_usage" {
  alarm_name          = "deprecated-api-high-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DeprecatedAPIUsage"
  namespace           = "API/Deprecation"
  period              = "300"
  statistic           = "Sum"
  threshold           = "100"
  alarm_description   = "This metric monitors deprecated API usage"
  alarm_actions       = [aws_sns_topic.api_alerts.arn]

  dimensions = {
    Version = "v1"
  }
}
```

## 测试策略

### 1. 版本兼容性测试

```bash
# 自动化测试脚本
#!/bin/bash

API_BASE="https://your-api-gateway.amazonaws.com"
API_KEY="your-api-key"

# 测试所有版本的健康检查
for version in v1 v2; do
  echo "Testing $version health endpoint..."
  response=$(curl -s -H "X-API-Key: $API_KEY" "$API_BASE/$version/health")
  echo "Response: $response"
done

# 测试版本特定功能
echo "Testing version-specific features..."

# V1 基础功能测试
curl -X POST "$API_BASE/v1/presentations" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"title":"Test","topic":"Testing"}'

# V2 增强功能测试
curl -X POST "$API_BASE/v2/presentations" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"title":"Test","topic":"Testing","template":"technology_showcase"}'
```

### 2. 性能测试

```yaml
# 使用Apache Bench进行性能测试
test_scenarios:
  - name: "V1 Performance Test"
    endpoint: "/v1/presentations"
    concurrent_users: 10
    total_requests: 100
    
  - name: "V2 Performance Test"
    endpoint: "/v2/presentations"
    concurrent_users: 10
    total_requests: 100
    
  - name: "Mixed Version Load Test"
    scenarios:
      - endpoint: "/v1/presentations"
        weight: 30%
      - endpoint: "/v2/presentations"
        weight: 70%
```

## 监控和观测

### 1. 版本使用情况监控

```hcl
resource "aws_cloudwatch_dashboard" "api_versioning" {
  dashboard_name = "API-Versioning-Dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", "ai-ppt-assistant", "Stage", "v1"],
            ["AWS/ApiGateway", "Count", "ApiName", "ai-ppt-assistant", "Stage", "v2"]
          ]
          period = 300
          stat   = "Sum"
          region = "us-east-1"
          title  = "API Version Usage"
        }
      }
    ]
  })
}
```

### 2. 错误率监控

```hcl
resource "aws_cloudwatch_metric_alarm" "api_version_error_rate" {
  for_each = var.api_versions

  alarm_name          = "api-${each.key}-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Average"
  threshold           = "0.05"  # 5% error rate
  alarm_description   = "This metric monitors API ${each.key} error rate"

  dimensions = {
    ApiName = "ai-ppt-assistant"
    Stage   = each.value.stage_name
  }
}
```

## 最佳实践

### 1. 版本发布最佳实践

- ✅ **语义版本控制**: 使用清晰的版本号 (v1, v2, v3)
- ✅ **向后兼容**: 新版本应尽可能向后兼容
- ✅ **渐进部署**: 使用蓝绿部署或金丝雀发布
- ✅ **文档先行**: 版本发布前更新API文档
- ✅ **测试覆盖**: 确保所有版本都有充分的测试覆盖

### 2. 客户端最佳实践

- ✅ **显式版本**: 客户端应明确指定API版本
- ✅ **错误处理**: 处理版本弃用和迁移通知
- ✅ **监控集成**: 监控API版本使用情况
- ✅ **定期更新**: 定期检查和更新到最新版本

### 3. 运维最佳实践

- ✅ **监控告警**: 设置版本使用和错误监控
- ✅ **容量规划**: 考虑多版本并行运行的资源需求
- ✅ **安全审计**: 定期审计不同版本的安全配置
- ✅ **数据备份**: 确保版本迁移过程中的数据安全

## 故障排除

### 1. 常见问题

#### Q: 客户端收到404错误
**A**: 检查API端点路径是否包含版本号，确保使用正确的版本化URL。

#### Q: Lambda函数权限错误
**A**: 确保为每个版本的API Gateway配置了正确的Lambda权限。

#### Q: CORS问题
**A**: 检查版本化CORS配置，确保包含版本特定的头部。

### 2. 调试步骤

```bash
# 1. 检查API Gateway配置
aws apigateway get-rest-apis --query 'items[?name==`ai-ppt-assistant`]'

# 2. 检查阶段配置
aws apigateway get-stages --rest-api-id <api-id>

# 3. 检查Lambda权限
aws lambda get-policy --function-name generate_presentation

# 4. 测试端点连通性
curl -v -H "X-API-Key: $API_KEY" "$API_BASE/v1/health"
curl -v -H "X-API-Key: $API_KEY" "$API_BASE/v2/health"
```

### 3. 日志分析

```bash
# 查看CloudWatch日志
aws logs filter-log-events \
  --log-group-name "/aws/apigateway/ai-ppt-assistant-dev-v1" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"

# 分析访问模式
aws logs insights start-query \
  --log-group-name "/aws/apigateway/ai-ppt-assistant-dev-v1" \
  --start-time $(date -d '24 hours ago' +%s) \
  --end-time $(date +%s) \
  --query-string "fields @timestamp, @message | filter @message like /v1/ | stats count() by bin(5m)"
```

## 总结

本API版本控制策略提供了：

1. **灵活的版本管理**: 支持多版本并行运行
2. **平滑的迁移路径**: 提供充足的时间和工具支持客户端迁移
3. **完整的监控体系**: 实时监控版本使用情况和性能
4. **自动化的部署**: 通过Terraform实现基础设施即代码
5. **详细的文档**: 为开发者和运维人员提供清晰的指导

通过遵循这个策略，我们可以确保API的演进不会破坏现有的集成，同时为新功能的引入提供清晰的路径。