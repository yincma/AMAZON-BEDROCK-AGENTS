# 前后端连接使用指南

## 🚀 快速开始

### 1. 环境配置
前端已配置好与后端 AWS API Gateway 的连接：
- **API URL**: https://taett6van5.execute-api.us-east-1.amazonaws.com/v1
- **API Key**: 已在 `.env` 文件中配置

### 2. 启动前端服务
```bash
cd frontend
npm install  # 如果还没有安装依赖
npm run dev
```
访问: http://localhost:5173

### 3. 访问演示文稿生成器
- 直接访问: http://localhost:5173/presentation
- 或通过导航菜单访问 "AI生成" 页面

## 📝 API 使用方法

### 在 React 组件中使用

#### 方法 1: 使用 Hook（推荐）
```typescript
import { usePresentationApi } from '@/hooks/usePresentationApi';

function MyComponent() {
  const {
    createPresentation,
    pollTask,
    listPresentations,
    loading,
    error
  } = usePresentationApi();

  const handleCreate = async () => {
    const task = await createPresentation({
      title: '我的演示文稿',
      topic: '演示文稿内容描述',
      language: 'zh-CN',
      slide_count: 10,
      style: 'modern'
    });

    if (task) {
      // 轮询任务状态
      const result = await pollTask(task.task_id);
      console.log('生成完成:', result);
    }
  };

  return (
    <button onClick={handleCreate} disabled={loading}>
      生成演示文稿
    </button>
  );
}
```

#### 方法 2: 直接使用服务类
```typescript
import { getPresentationApiService } from '@/services/PresentationApiService';

const apiService = getPresentationApiService();

// 创建演示文稿
const response = await apiService.createPresentation({
  title: '测试演示文稿',
  topic: '内容描述',
  language: 'zh-CN',
  slide_count: 10
});

if (response.success) {
  console.log('任务ID:', response.data.task_id);
}
```

## 🧪 测试工具

### 1. HTML 测试页面
打开 `test-api-connection.html` 文件，可以：
- 测试各个 API 端点
- 创建演示文稿
- 查询任务状态

### 2. Node.js 测试脚本
```bash
node test-backend-connection.cjs
```
自动测试所有端点的连接状态

## 📊 API 端点列表

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/health/ready` | GET | 就绪状态 |
| `/presentations` | POST | 创建演示文稿 |
| `/presentations` | GET | 获取演示文稿列表 |
| `/presentations/{id}` | GET | 获取单个演示文稿 |
| `/presentations/{id}` | DELETE | 删除演示文稿 |
| `/presentations/{id}/slides` | PUT | 修改幻灯片 |
| `/presentations/{id}/download` | GET | 下载演示文稿 |
| `/tasks/{taskId}` | GET | 查询任务状态 |
| `/templates` | GET | 获取模板列表 |

## 🔍 调试技巧

### 1. 检查网络请求
在浏览器开发者工具的 Network 标签中查看：
- 请求头是否包含 `x-api-key`
- 响应状态码和错误信息

### 2. 启用调试模式
在 `.env` 文件中设置：
```env
VITE_ENABLE_DEBUG=true
```

### 3. 查看控制台日志
服务类会在控制台输出详细的请求和响应信息

## 🚨 常见问题

### 1. 403 Forbidden 错误
- 检查 API Key 是否正确配置
- 确认 API Key 有访问权限

### 2. 500 Internal Server Error
- 检查 Lambda 函数是否正常部署
- 查看 AWS CloudWatch 日志

### 3. CORS 错误
- 确认 API Gateway 已配置 CORS
- 检查请求头配置

### 4. 任务超时
- 默认轮询时间为 2 分钟
- 可以在 `pollTask` 方法中调整 `maxAttempts` 参数

## 📦 项目结构

```
frontend/
├── src/
│   ├── services/
│   │   ├── AwsApiGatewayService.ts      # AWS API Gateway 基础服务
│   │   ├── PresentationApiService.ts    # 演示文稿 API 服务
│   │   └── index.ts                     # 服务导出
│   ├── hooks/
│   │   └── usePresentationApi.ts        # React Hook
│   ├── components/
│   │   └── PresentationGenerator.tsx    # 演示文稿生成器组件
│   └── router.tsx                       # 路由配置
├── .env                                  # 环境变量配置
├── test-api-connection.html              # HTML 测试页面
└── test-backend-connection.cjs           # Node.js 测试脚本
```

## 🔗 相关资源

- [AWS API Gateway 文档](https://docs.aws.amazon.com/apigateway/)
- [Amazon Bedrock 文档](https://docs.aws.amazon.com/bedrock/)
- [React Query 文档](https://react-query.tanstack.com/)（可选：用于更好的状态管理）

## 📝 后续优化建议

1. **添加缓存机制**: 使用 React Query 或 SWR 管理 API 状态
2. **错误重试**: 实现指数退避的重试机制
3. **离线支持**: 使用 Service Worker 缓存请求
4. **实时更新**: 使用 WebSocket 或 SSE 获取任务状态更新
5. **批量操作**: 支持批量创建和管理演示文稿