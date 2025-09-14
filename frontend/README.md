# AI PPT 生成助手 - 前端界面

## 简介

这是一个轻量级的单页应用，用于快速验证 AI PPT 生成系统的 API 功能。无需构建工具，直接在浏览器中运行。

## 特性

- 🚀 **零依赖构建** - 纯 HTML/CSS/JavaScript，无需 npm install
- 🎨 **响应式设计** - 使用 Bootstrap 5，支持移动端
- 💾 **本地存储** - 历史记录和配置保存在 localStorage
- 🔄 **实时进度** - 自动轮询显示生成进度
- 📥 **一键下载** - 生成完成后直接下载 PPT
- 📝 **历史记录** - 查看和重新下载之前生成的文件

## 快速开始

### 1. 启动本地服务器

```bash
# 方式1：使用 Python 3
cd frontend
python3 -m http.server 8080

# 方式2：使用 Node.js
npx serve .

# 方式3：使用 VS Code
# 安装 Live Server 扩展，右键 index.html 选择 "Open with Live Server"
```

### 2. 访问应用

打开浏览器访问: http://localhost:8080

### 3. 配置 API

1. 输入 API Gateway URL（例如：https://xxx.execute-api.us-east-1.amazonaws.com/prod）
2. 输入 API Key
3. 配置会自动保存到浏览器本地存储

### 4. 生成 PPT

1. 输入演示主题
2. 选择页数和目标受众
3. 点击"开始生成"
4. 等待进度条完成
5. 点击"下载 PPT"

## 文件结构

```
frontend/
├── index.html          # 主页面
├── js/
│   ├── app.js         # 主应用逻辑
│   ├── status.js      # 状态轮询管理
│   └── download.js    # 下载管理
└── README.md          # 本文档
```

## 功能说明

### API 配置
- 支持配置 API Gateway URL 和 API Key
- 配置自动保存，下次打开无需重新输入

### PPT 生成
- 支持自定义主题、页数（5-30页）、目标受众
- 实时显示生成进度和当前处理阶段
- 生成失败自动显示错误信息

### 历史记录
- 自动保存最近 10 条生成记录
- 显示生成时间、状态和基本信息
- 点击已完成的记录可重新下载
- 支持一键清除所有历史

### 下载管理
- 自动获取预签名 URL
- 显示文件大小（如果可用）
- 下载成功显示提示
- 支持重新下载

## API 端点

应用使用以下 API 端点：

- `POST /presentations/generate` - 创建新的演示文稿
- `GET /presentations/{id}/status` - 查询生成状态
- `GET /presentations/{id}/download` - 获取下载链接

## 本地存储

应用使用 localStorage 存储以下数据：

- `apiEndpoint` - API Gateway URL
- `apiKey` - API 密钥
- `pptHistory` - 生成历史记录
- `downloadStats` - 下载统计

## 故障排除

### CORS 错误
如果遇到 CORS 错误，确保：
1. API Gateway 已配置 CORS 头
2. 允许的源包含 `http://localhost:8080`

### 网络超时
- 默认轮询超时为 5 分钟
- 可在 `status.js` 中调整 `maxRetries` 值

### 下载失败
- 检查预签名 URL 是否有效（默认 1 小时）
- 确保 S3 bucket 策略允许公开访问

## 开发提示

### 调试模式
打开浏览器控制台查看详细日志：
```javascript
// 在控制台执行
localStorage.setItem('debug', 'true');
```

### 模拟数据
测试时可以使用模拟数据：
```javascript
// 模拟成功响应
window.mockResponse = {
    presentation_id: 'test-123',
    status: 'completed'
};
```

### 自定义样式
可以在 `index.html` 的 `<style>` 标签中添加自定义 CSS

## 浏览器兼容性

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 安全注意事项

⚠️ **注意**：这是一个演示应用，不适合生产环境使用。

- API Key 存储在浏览器本地，可能被恶意脚本访问
- 建议仅在内部网络或开发环境使用
- 生产环境应实现proper的身份验证机制

## 扩展功能

可以轻松添加以下功能：

- 🎨 主题切换（深色/浅色模式）
- 🌍 多语言支持
- 📊 生成统计图表
- 🔐 OAuth 2.0 认证
- 📤 分享功能
- 💾 云端同步历史记录

## 许可证

MIT