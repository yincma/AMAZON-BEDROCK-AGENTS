# AI PPT Assistant Frontend

AI驱动的PowerPoint生成器前端应用，提供直观的用户界面来创建、管理和生成专业的演示文稿。

## 🌟 特性

- 🤖 **AI驱动**: 智能生成PPT大纲和内容
- 📝 **富文本编辑**: 强大的内容编辑功能
- 🖼️ **智能图片搜索**: 自动匹配相关图片
- 💾 **本地存储**: 自动保存和项目管理
- 🎨 **多种模板**: 丰富的PPT模板选择
- 📱 **响应式设计**: 支持多设备访问
- 🚀 **高性能**: 优化的加载和渲染

## 📋 系统要求

- Node.js 18.0.0 或更高版本
- npm 9.0.0 或更高版本
- 现代浏览器 (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-org/ppt-assistant-frontend.git
cd ppt-assistant-frontend/frontend
```

### 2. 安装依赖

```bash
npm install
```

**注意**: 如果遇到依赖问题，请确保安装了以下关键依赖：
```bash
npm install @heroicons/react react-router-dom @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities @tailwindcss/postcss
```

### 3. 配置环境变量

复制环境变量模板并配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的API配置：

```env
VITE_API_BASE_URL=https://your-api-gateway.amazonaws.com/prod
VITE_API_KEY=your-api-key-here
```

### 4. 启动开发服务器

```bash
npm run dev
```

应用将在 `http://localhost:5173` 启动。

## 📁 项目结构

```
frontend/
├── src/
│   ├── components/        # React组件
│   │   ├── common/       # 通用组件
│   │   ├── editor/       # 编辑器组件
│   │   ├── layout/       # 布局组件
│   │   ├── media/        # 媒体组件
│   │   ├── preview/      # 预览组件
│   │   ├── project/      # 项目管理组件
│   │   └── settings/     # 设置组件
│   ├── services/         # API服务层
│   ├── store/           # Zustand状态管理
│   ├── hooks/           # 自定义Hooks
│   ├── utils/           # 工具函数
│   ├── types/           # TypeScript类型
│   ├── styles/          # 全局样式
│   └── pages/           # 页面组件
├── public/              # 静态资源
├── e2e/                 # 端到端测试
├── docs/                # 文档
└── tests/               # 测试文件

```

## 🛠️ 开发命令

```bash
# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview

# 运行类型检查
npm run type-check

# 运行代码检查
npm run lint

# 格式化代码
npm run format

# 运行单元测试
npm test

# 运行测试覆盖率
npm run test:coverage

# 运行端到端测试
npm run test:e2e

# 运行所有测试
npm run test:all
```

## 🧪 测试

### 单元测试

使用 Jest 和 React Testing Library：

```bash
npm test
npm run test:watch  # 监听模式
npm run test:coverage  # 生成覆盖率报告
```

### 端到端测试

使用 Playwright：

```bash
npm run test:e2e
npm run test:e2e:headed  # 有界面模式
npm run test:e2e:debug   # 调试模式
```

## 🏗️ 构建和部署

### 生产构建

```bash
npm run build
```

构建文件将生成在 `dist/` 目录。

### 部署选项

#### 1. 静态托管 (推荐)

将 `dist/` 目录部署到任何静态托管服务：
- AWS S3 + CloudFront
- Vercel
- Netlify
- GitHub Pages

#### 2. Docker

```bash
docker build -t ppt-assistant-frontend .
docker run -p 80:80 ppt-assistant-frontend
```

#### 3. Node.js 服务器

```bash
npm run build
npm run serve
```

## 🔧 配置说明

### 环境变量

查看 `.env.example` 文件了解所有可配置项。

关键配置：
- `VITE_API_BASE_URL`: 后端API地址
- `VITE_API_KEY`: API密钥
- `VITE_API_TIMEOUT`: 请求超时时间
- `VITE_ENABLE_OFFLINE_MODE`: 离线模式开关

### API集成

应用需要连接到后端API服务。确保：
1. API Gateway已配置CORS
2. Lambda函数已部署
3. DynamoDB表已创建
4. S3存储桶已配置

## 📚 技术栈

- **框架**: React 19 + TypeScript 5
- **构建工具**: Vite 7
- **路由**: React Router v7
- **状态管理**: Zustand
- **样式**: Tailwind CSS v4
- **拖拽功能**: @dnd-kit
- **HTTP客户端**: Axios
- **图标**: Lucide React + Heroicons
- **测试**: Jest + Playwright
- **本地存储**: LocalForage

## 🤝 贡献指南

### 开发流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 代码规范

- 遵循 ESLint 配置
- 使用 Prettier 格式化
- 编写单元测试
- 更新文档

### 提交规范

使用语义化提交信息：
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具

## 🔍 故障排除

### 常见问题

#### 1. 端口被占用
如果看到 `Port 5173 is in use` 错误：
```bash
# 查找占用端口的进程
lsof -i :5173
# 终止进程
kill -9 <PID>
```

#### 2. Tailwind CSS 错误
如果遇到 Tailwind CSS 相关错误：
- 确保安装了 `@tailwindcss/postcss` 包
- 检查 `postcss.config.js` 配置是否正确
- 清除缓存后重启：`rm -rf node_modules/.vite && npm run dev`

#### 3. 组件导入错误
如果看到 `Failed to resolve import` 错误：
- 检查组件是否使用了正确的导出方式（named export vs default export）
- 确认所有依赖都已正确安装
- 运行 `npm install` 重新安装依赖

#### 4. React Router 错误
确保已安装 `react-router-dom`：
```bash
npm install react-router-dom
```

#### 5. 拖拽功能不工作
确保安装了 DnD Kit 相关包：
```bash
npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities
```

## 🐛 问题反馈

发现bug或有建议？请创建 [Issue](https://github.com/your-org/ppt-assistant-frontend/issues)。

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 👥 团队

- 产品设计：Product Team
- 前端开发：Frontend Team
- 后端开发：Backend Team
- 测试：QA Team

## 🔗 相关链接

- [用户文档](./docs/USER_GUIDE.md)
- [API文档](https://api-docs.ppt-assistant.com)
- [后端仓库](https://github.com/your-org/ppt-assistant-backend)
- [设计规范](./docs/DESIGN_GUIDE.md)

## 📈 项目状态

- 版本：1.0.0
- 状态：开发中
- 最后更新：2024年12月

---

Made with ❤️ by AI PPT Assistant Team