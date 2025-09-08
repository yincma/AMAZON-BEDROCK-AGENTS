# API参数验证配置指南

本指南介绍AI PPT Assistant API Gateway的请求参数验证功能，包括配置、使用和测试方法。

## 概述

API Gateway现在配置了完整的请求参数验证，包括：

- ✅ JSON Schema验证
- ✅ 路径参数验证  
- ✅ 查询参数验证
- ✅ 自定义错误响应
- ✅ API密钥验证

## 验证配置详情

### 1. JSON Schema模型

#### 生成演示文稿请求 (`GeneratePresentationRequest`)
```json
{
  "title": "字符串，1-200字符，必需",
  "topic": "字符串，1-1000字符，必需", 
  "audience": "枚举：general|technical|executive|academic|student",
  "duration": "整数，5-120，默认20",
  "slide_count": "整数，5-100，默认15",
  "language": "枚举：en|ja|zh|es|fr|de|pt|ko，默认en",
  "style": "枚举：professional|creative|minimalist|technical|academic",
  "template": "枚举：default|executive_summary|technology_showcase|sales_pitch|educational",
  "include_speaker_notes": "布尔值，默认true",
  "include_images": "布尔值，默认true",
  "session_id": "UUID格式字符串，可选",
  "metadata": "对象，可选",
  "preferences": "对象，可选"
}
```

#### 创建会话请求 (`CreateSessionRequest`)
```json
{
  "user_id": "字符串，1-50字符，字母数字下划线连字符，必需",
  "session_name": "字符串，1-100字符，可选",
  "metadata": "对象，可选"
}
```

#### 执行代理请求 (`ExecuteAgentRequest`)
```json
{
  "input": "字符串，1-2000字符，必需",
  "session_id": "UUID格式字符串，可选",
  "enable_trace": "布尔值，默认false",
  "parameters": "对象，可选"
}
```

### 2. 请求验证器

- **validate_all**: 验证请求体和参数
- **validate_body**: 仅验证请求体
- **validate_parameters**: 仅验证参数

### 3. 错误响应配置

| 错误类型 | HTTP状态码 | 错误代码 | 描述 |
|---------|-----------|---------|------|
| BAD_REQUEST_BODY | 400 | VALIDATION_ERROR | 请求体验证失败 |
| BAD_REQUEST_PARAMETERS | 400 | PARAMETER_ERROR | 参数格式错误 |
| MISSING_AUTHENTICATION_TOKEN | 403 | MISSING_API_KEY | 缺少或无效API密钥 |
| THROTTLED | 429 | RATE_LIMIT_EXCEEDED | 请求频率超限 |
| DEFAULT_5XX | 500 | INTERNAL_ERROR | 服务器内部错误 |

### 4. 端点验证配置

| 端点 | 验证类型 | Schema模型 |
|------|---------|-----------|
| POST /presentations | Body + Headers | GeneratePresentationRequest |
| GET /presentations/{id} | Path Parameters | UUID验证 |
| GET /presentations | Query Parameters | 分页参数验证 |
| POST /sessions | Body + Headers | CreateSessionRequest |
| GET /sessions/{id} | Path Parameters | UUID验证 |
| POST /agents/{name}/execute | Body + Path + Headers | ExecuteAgentRequest |
| GET /tasks/{task_id} | Path Parameters | UUID验证 |
| GET /templates | Query Parameters | 分页和过滤参数验证 |

## 使用示例

### 有效的请求示例

```bash
# 生成演示文稿
curl -X POST "https://your-api.amazonaws.com/dev/presentations" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "title": "AI技术在企业中的应用",
    "topic": "探讨人工智能技术如何改变现代企业运营",
    "audience": "executive",
    "duration": 30,
    "slide_count": 20,
    "language": "zh",
    "style": "professional"
  }'
```

### 错误响应示例

```json
{
  "error": "VALIDATION_ERROR",
  "message": "请求参数验证失败",
  "details": "Invalid input: title is required",
  "request_id": "12345678-1234-1234-1234-123456789012",
  "timestamp": "2025-01-01T12:00:00Z"
}
```

## 测试验证功能

### 运行自动化测试

```bash
# 设置环境变量
export API_BASE_URL="https://your-api.amazonaws.com/dev"
export API_KEY="your-api-key"

# 运行验证测试
./scripts/run_validation_tests.sh
```

### 手动测试场景

1. **测试必需字段验证**
```bash
curl -X POST "$API_BASE_URL/presentations" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"topic": "缺少标题"}' 
# 期望: 400错误，VALIDATION_ERROR
```

2. **测试数值范围验证**
```bash
curl -X POST "$API_BASE_URL/presentations" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "测试", "topic": "测试", "duration": 200}'
# 期望: 400错误，duration超出范围
```

3. **测试UUID格式验证**
```bash
curl -X GET "$API_BASE_URL/tasks/invalid-uuid" \
  -H "X-API-Key: $API_KEY"
# 期望: 400错误，UUID格式无效
```

4. **测试API密钥验证**
```bash
curl -X POST "$API_BASE_URL/presentations" \
  -H "Content-Type: application/json" \
  -d '{"title": "测试", "topic": "测试"}'
# 期望: 403错误，MISSING_API_KEY
```

## 监控和维护

### CloudWatch指标

监控以下指标：
- 4XXError - 客户端错误（验证失败）
- 5XXError - 服务器错误  
- IntegrationLatency - 验证对延迟的影响
- Count - 总请求数

### 日志分析

在CloudWatch Logs中查看：
- 验证失败的详细信息
- 常见的验证错误模式
- 客户端行为分析

### 告警配置

建议为以下场景配置告警：
- 4XX错误率超过10%
- 验证错误激增
- 特定客户端反复验证失败

## 开发建议

### 客户端最佳实践

1. **预验证**: 在客户端进行基本验证
2. **错误处理**: 优雅处理验证错误
3. **重试机制**: 对临时错误实现重试
4. **用户友好**: 将技术错误转换为用户友好的消息

### API文档更新

确保API文档包含：
- 完整的Schema定义
- 验证规则说明
- 错误响应格式
- 示例请求和响应

## 故障排除

### 常见问题

1. **Schema验证总是失败**
   - 检查Content-Type头是否为application/json
   - 验证JSON格式是否正确
   - 确认字段名称和类型匹配

2. **路径参数验证失败**  
   - 确认UUID格式正确
   - 检查路径模板配置

3. **API密钥验证失败**
   - 确认X-API-Key头存在
   - 检查密钥是否有效
   - 验证使用计划配置

### 调试步骤

1. 检查CloudWatch日志
2. 使用API Gateway测试功能
3. 验证Terraform配置
4. 运行自动化测试套件

## 更新历史

- **v1.0**: 初始验证配置
  - JSON Schema模型
  - 请求验证器
  - 错误响应格式化
  - 自动化测试套件