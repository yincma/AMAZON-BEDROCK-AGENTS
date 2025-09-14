# CORS 问题永久解决方案

## 问题根源分析

### 为什么会出现CORS问题？

1. **初始配置缺失**
   - 原始的Terraform配置只定义了API端点（GET/POST），但没有配置OPTIONS方法
   - API Gateway需要在网关层面处理preflight请求，而不能依赖Lambda函数

2. **浏览器安全机制**
   - 浏览器执行跨域请求前会发送OPTIONS预检请求
   - 如果API Gateway不响应OPTIONS请求，浏览器会阻止实际请求

3. **Lambda层CORS不足**
   - 虽然Lambda函数返回了CORS头，但这只对实际请求有效
   - OPTIONS预检请求到不了Lambda层就被拒绝了

## 已实施的解决方案

### 1. API Gateway层面配置
```hcl
# 为每个端点添加OPTIONS方法
resource "aws_api_gateway_method" "xxx_options" {
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# 使用MOCK集成直接响应
resource "aws_api_gateway_integration" "xxx_options" {
  type = "MOCK"
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}
```

### 2. CORS响应头配置
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`
- `Access-Control-Allow-Methods: GET,POST,OPTIONS`

## 永久性保证

### ✅ 不需要每次部署都修复
CORS配置已经添加到`main.tf`中，属于基础设施代码的一部分：
- 每次运行`terraform apply`都会包含CORS配置
- 配置会被Terraform state跟踪
- 不会因为重新部署而丢失

### ✅ 配置已持久化
当前`main.tf`已包含完整的CORS配置：
- `/generate` - OPTIONS方法（行271-313）
- `/status/{id}` - OPTIONS方法（行358-400）
- `/download/{id}` - OPTIONS方法（行445-487）

## 部署检查清单

### 首次部署后
```bash
# 1. 检查OPTIONS端点
curl -X OPTIONS https://YOUR_API_URL/generate \
  -H "Origin: http://localhost:8080" \
  -H "Access-Control-Request-Method: POST" \
  -i

# 2. 确认返回200和CORS头
# 应该看到：
# - HTTP/2 200
# - access-control-allow-origin: *
# - access-control-allow-methods: GET,POST,OPTIONS
```

### 如果遇到CORS错误
1. **检查部署状态**
   ```bash
   cd infrastructure
   terraform plan
   # 如果显示有changes，说明配置未完全应用
   ```

2. **强制重新部署API Gateway**
   ```bash
   terraform apply -target=aws_api_gateway_deployment.api
   ```

3. **验证配置**
   ```bash
   terraform state show aws_api_gateway_method.generate_options
   ```

## 最佳实践

### 1. 环境特定配置
如果需要限制特定域名访问：
```hcl
# variables.tf
variable "allowed_origins" {
  default = "*"  # 开发环境
  # production = "https://your-domain.com"
}

# main.tf
response_parameters = {
  "method.response.header.Access-Control-Allow-Origin" = "'${var.allowed_origins}'"
}
```

### 2. 自动化测试
创建测试脚本 `test_cors.sh`：
```bash
#!/bin/bash
API_URL="https://479jyollng.execute-api.us-east-1.amazonaws.com/dev"

echo "Testing CORS..."
for endpoint in "generate" "status/test-id" "download/test-id"; do
  echo "Testing /$endpoint"
  curl -s -X OPTIONS "$API_URL/$endpoint" \
    -H "Origin: http://localhost:8080" \
    -o /dev/null -w "%{http_code}\n"
done
```

### 3. 前端备用方案
如果API暂时无法修复，可以使用代理：
```javascript
// 开发环境使用代理绕过CORS
// vite.config.js 或 webpack.config.js
proxy: {
  '/api': {
    target: 'https://YOUR_API_URL',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '')
  }
}
```

## 总结

**问题已永久解决！**
- ✅ CORS配置已添加到Terraform代码
- ✅ 部署后会自动包含CORS支持
- ✅ 不需要每次手动修复
- ✅ 配置会持续存在

**关键点**：
- CORS必须在API Gateway层面配置，不能只依赖Lambda
- OPTIONS方法必须单独定义和配置
- 使用MOCK集成处理OPTIONS请求更高效

最后更新：2025-09-13