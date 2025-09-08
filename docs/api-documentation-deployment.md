# API文档自动生成部署指南

## 概述

AI PPT Assistant项目包含了完整的API文档自动生成和托管解决方案，支持OpenAPI 3.0规范、Swagger UI界面、Postman集合等多种文档格式。

## 功能特性

### 🚀 自动化文档生成
- **OpenAPI 3.0规范**：从API Gateway自动导出并增强的完整API规范
- **Swagger UI界面**：交互式API文档，支持在线测试API端点
- **Postman集合**：预配置的API请求集合，便于开发和测试
- **API Gateway文档**：内置的API Gateway文档版本控制

### 📦 托管解决方案
- **S3静态网站**：文档文件的可靠托管
- **CloudFront CDN**：全球加速访问（可选）
- **自动部署**：API变更时自动更新文档
- **版本控制**：文档版本追踪和管理

### 🔧 开发者友好
- **一键访问**：通过URL直接访问各种文档格式
- **预配置变量**：Postman集合包含环境变量配置
- **自动测试脚本**：内置的API测试脚本
- **错误处理**：完善的错误响应文档

## 部署配置

### 必需的Terraform变量

在`terraform.tfvars`文件中添加或修改以下配置：

```hcl
# API文档配置
enable_api_documentation = true
enable_documentation_cdn = true
documentation_retention_days = 30
documentation_lambda_memory = 512
documentation_lambda_timeout = 300
documentation_price_class = "PriceClass_100"
```

### 变量说明

| 变量名 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `enable_api_documentation` | bool | `true` | 启用API文档功能 |
| `enable_documentation_cdn` | bool | `true` | 启用CloudFront CDN |
| `documentation_retention_days` | number | `30` | 文档日志保留天数 |
| `documentation_lambda_memory` | number | `512` | Lambda函数内存大小(MB) |
| `documentation_lambda_timeout` | number | `300` | Lambda函数超时时间(秒) |
| `documentation_price_class` | string | `"PriceClass_100"` | CloudFront价格类别 |

## 部署步骤

### 1. 检查前置条件

确保已完成基础设施部署：
```bash
# 验证配置
terraform validate

# 检查计划
terraform plan
```

### 2. 部署文档基础设施

```bash
# 应用配置
terraform apply

# 确认部署
terraform show | grep -A 5 "api_documentation"
```

### 3. 验证部署结果

部署完成后，Terraform将输出以下URL：

```bash
# 获取文档URLs
terraform output api_documentation_url
terraform output swagger_ui_url
terraform output openapi_spec_url
terraform output postman_collection_url
```

## 访问方式

### 🌐 主文档页面
访问主文档页面获取所有文档资源的链接：
```
https://<cloudfront-domain>/
```

### 📋 Swagger UI
交互式API文档界面：
```
https://<cloudfront-domain>/swagger-ui/
```

### 📄 OpenAPI规范
完整的OpenAPI 3.0规范文件：
```
https://<cloudfront-domain>/openapi.yaml
```

### 📮 Postman集合
可直接导入Postman的API集合：
```
https://<cloudfront-domain>/postman-collection.json
```

## 使用指南

### Swagger UI使用方法

1. **访问界面**：打开Swagger UI URL
2. **API密钥配置**：点击"Authorize"按钮，输入API密钥
3. **测试端点**：展开API端点，点击"Try it out"
4. **查看响应**：执行请求并查看响应结果

### Postman集合使用方法

1. **下载集合**：从Postman集合URL下载JSON文件
2. **导入Postman**：在Postman中选择"Import" > "Upload Files"
3. **配置环境变量**：
   - `base_url`：设置为您的API Gateway URL
   - `api_key`：设置为您的API密钥
4. **执行请求**：选择请求并发送

### 环境变量配置

Postman集合包含以下预配置变量：

| 变量名 | 描述 | 示例值 |
|-------|------|--------|
| `base_url` | API基础URL | `https://your-api.execute-api.us-east-1.amazonaws.com/v1` |
| `api_key` | API密钥 | `YOUR_API_KEY_HERE` |
| `presentation_id` | 演示文稿ID | 自动从响应中设置 |
| `session_id` | 会话ID | 自动从响应中设置 |
| `task_id` | 任务ID | 自动从响应中设置 |

## 文档更新机制

### 自动更新
- **API变更检测**：当API Gateway部署更新时自动触发
- **文档重新生成**：Lambda函数自动生成最新文档
- **内容更新**：S3中的文档文件实时更新
- **CDN刷新**：CloudFront缓存自动更新

### 手动更新
如需手动触发文档更新：

```bash
# 获取Lambda函数名称
FUNCTION_NAME=$(terraform output -raw documentation_lambda_function)

# 手动调用Lambda函数
aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --payload '{}' \
  response.json

# 查看结果
cat response.json
```

## 监控和故障排除

### 查看Lambda日志
```bash
# 获取日志组名称
LOG_GROUP="/aws/lambda/$(terraform output -raw documentation_lambda_function)"

# 查看最近的日志
aws logs describe-log-streams \
  --log-group-name $LOG_GROUP \
  --order-by LastEventTime \
  --descending
```

### 常见问题

#### 1. 文档无法访问
**问题**：访问文档URL返回404错误
**解决**：
1. 检查S3存储桶是否已创建
2. 验证Lambda函数是否成功执行
3. 确认CloudFront分发是否正常

#### 2. Swagger UI无法加载API规范
**问题**：Swagger UI界面无法显示API端点
**解决**：
1. 检查OpenAPI规范文件是否存在
2. 验证CORS配置是否正确
3. 确认API Gateway文档是否生成

#### 3. Lambda函数执行失败
**问题**：文档生成Lambda函数报错
**解决**：
1. 检查IAM权限配置
2. 验证环境变量设置
3. 查看CloudWatch日志详细错误

## 安全考虑

### 访问控制
- **公共访问**：文档默认为公共访问
- **API密钥**：实际API调用需要有效的API密钥
- **CORS设置**：适当配置CORS以限制跨域访问

### 敏感信息保护
- **API密钥隐藏**：文档中不包含实际的API密钥
- **示例数据**：使用虚拟数据作为示例
- **环境隔离**：不同环境使用不同的文档URL

## 成本优化

### CloudFront配置
- **价格类别**：使用`PriceClass_100`降低成本
- **缓存策略**：合理设置缓存时间
- **地域限制**：根据需要设置地域访问限制

### Lambda优化
- **内存配置**：根据实际需要调整内存大小
- **超时设置**：避免不必要的长时间等待
- **调用频率**：避免频繁的手动触发

## 维护建议

### 定期检查
- **文档准确性**：定期验证文档与实际API的一致性
- **链接有效性**：检查所有文档链接是否有效
- **性能监控**：关注文档访问性能

### 版本管理
- **文档版本**：为重大API变更创建文档版本
- **变更记录**：维护API变更历史记录
- **回滚机制**：在必要时能够回滚到前一版本

---

通过以上配置和指南，您可以成功部署和使用AI PPT Assistant的API文档自动生成功能，为开发者提供完整、准确、易用的API文档体验。