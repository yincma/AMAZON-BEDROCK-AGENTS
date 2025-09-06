# AWS API Gateway 连接指南

## 问题诊断

您的AWS API Gateway endpoint `https://byih5fsutb.execute-api.us-east-1.amazonaws.com/dev` 返回了 `Missing Authentication Token` 错误，这是因为API Gateway需要认证。

## 解决方案

### 1. 获取API密钥

从AWS控制台获取您的API密钥：

1. 登录 [AWS Console](https://console.aws.amazon.com/)
2. 导航到 **API Gateway** 服务
3. 选择您的API（byih5fsutb）
4. 在左侧菜单中点击 **API Keys**
5. 创建或选择一个现有的API密钥
6. 复制密钥值

### 2. 在前端配置API

1. 打开前端应用：http://localhost:5173
2. 导航到设置页面：http://localhost:5173/settings/api
3. 配置以下内容：
   - **API地址**: `https://byih5fsutb.execute-api.us-east-1.amazonaws.com/dev`
   - **API密钥**: 粘贴您从AWS控制台复制的密钥
4. 点击"测试API连接"按钮
5. 如果连接成功，点击"保存配置"

### 3. API Gateway配置检查

确保您的API Gateway已正确配置：

#### CORS配置
在API Gateway控制台中，确保已启用CORS：

```json
{
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
  "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
}
```

#### API密钥使用计划
1. 在API Gateway控制台中，创建使用计划
2. 将API密钥关联到使用计划
3. 将使用计划关联到您的API阶段（dev）

### 4. 测试API连接

使用curl测试您的API（替换YOUR_API_KEY为实际密钥）：

```bash
# 测试健康检查端点
curl -H "x-api-key: YOUR_API_KEY" \
  https://byih5fsutb.execute-api.us-east-1.amazonaws.com/dev/health

# 测试其他端点
curl -H "x-api-key: YOUR_API_KEY" \
  https://byih5fsutb.execute-api.us-east-1.amazonaws.com/dev/
```

### 5. 前端集成已优化

前端已经为AWS API Gateway进行了以下优化：

- ✅ 自动检测AWS API Gateway URL
- ✅ 使用正确的`x-api-key`请求头
- ✅ 智能健康检查，尝试多个端点
- ✅ 详细的错误提示和指导
- ✅ 支持保存配置到本地存储

## 常见问题

### Q: 仍然收到403错误？
**A:** 检查以下内容：
- API密钥是否正确
- API密钥是否已启用
- API密钥是否关联到正确的使用计划
- 使用计划是否关联到dev阶段

### Q: 收到CORS错误？
**A:** 需要在API Gateway中配置CORS：
1. 在API Gateway控制台中，选择您的资源
2. 点击Actions → Enable CORS
3. 配置允许的源和头部
4. 部署API到dev阶段

### Q: 如何查看具体的API端点？
**A:** 在API Gateway控制台中：
1. 选择您的API
2. 点击Stages → dev
3. 查看Invoke URL和可用的资源路径

## 后端要求

确保您的Lambda函数或后端服务：
- 正确处理OPTIONS请求（CORS预检）
- 返回适当的响应头
- 处理认证令牌验证

## 需要帮助？

如果问题仍然存在，请检查：
1. CloudWatch日志查看详细错误
2. API Gateway的执行日志
3. Lambda函数日志（如果使用Lambda）

## 测试成功标志

当您看到以下情况时，说明连接成功：
- 测试按钮显示"连接成功"
- 状态指示灯变为绿色
- 显示响应时间

---

**注意**: 请妥善保管您的API密钥，不要将其提交到版本控制系统中。