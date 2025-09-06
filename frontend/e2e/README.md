# E2E测试文档

本项目使用 Playwright 进行端到端测试，覆盖了 AI PPT 生成器的关键业务流程。

## 🚀 快速开始

### 1. 安装浏览器

```bash
npm run test:e2e:install
```

### 2. 运行所有测试

```bash
npm run test:e2e
```

### 3. 运行特定浏览器测试

```bash
# Chrome
npm run test:e2e:chromium

# Firefox
npm run test:e2e:firefox

# Safari
npm run test:e2e:webkit

# 移动端
npm run test:e2e:mobile
```

## 📋 测试套件概览

### 1. 首次用户体验 (`01-first-time-user.spec.ts`)
- ✅ 欢迎界面显示
- ✅ API配置引导
- ✅ 首个项目创建
- ✅ 用户偏好记忆
- ✅ 移动端适配

### 2. PPT创建流程 (`02-ppt-creation-flow.spec.ts`)
- ✅ 完整创建工作流
- ✅ 大纲生成和验证
- ✅ 内容增强功能
- ✅ 图片搜索和选择
- ✅ PPT生成和下载
- ✅ 进度跟踪
- ✅ 工作保存

### 3. 项目管理 (`03-project-management.spec.ts`)
- ✅ 多项目创建
- ✅ 项目加载和切换
- ✅ 项目编辑和删除
- ✅ 项目复制
- ✅ 导入/导出功能
- ✅ 项目搜索过滤
- ✅ 项目统计信息

### 4. 错误处理和边界情况 (`04-error-handling.spec.ts`)
- ✅ API配置错误
- ✅ 网络连接问题
- ✅ 输入验证错误
- ✅ 存储空间限制
- ✅ 并发操作处理
- ✅ 数据恢复机制

### 5. 性能和可访问性 (`05-performance-accessibility.spec.ts`)
- ✅ 页面加载性能
- ✅ API响应时间
- ✅ 内存使用优化
- ✅ 键盘导航支持
- ✅ 屏幕阅读器兼容
- ✅ 响应式设计

## 🔧 高级用法

### 调试模式
```bash
npm run test:e2e:debug
```

### UI模式（可视化测试运行）
```bash
npm run test:e2e:ui
```

### 有头模式（显示浏览器）
```bash
npm run test:e2e:headed
```

### 查看测试报告
```bash
npm run test:e2e:report
```

## 📊 测试配置

### 浏览器支持
- ✅ Chromium (Chrome/Edge)
- ✅ Firefox
- ✅ WebKit (Safari)
- ✅ 移动端 Chrome
- ✅ 移动端 Safari

### 视口尺寸
- 📱 移动端: 375×667
- 📱 平板: 768×1024  
- 💻 桌面: 1280×720
- 🖥️ 宽屏: 1920×1080

### 性能阈值
- 📈 页面加载: <3秒
- 📈 API响应: <5秒
- 📈 图片加载: <2秒
- 📈 导航时间: <1秒

## 📁 文件结构

```
e2e/
├── fixtures/
│   └── test-data.ts          # 测试数据
├── tests/
│   ├── 01-first-time-user.spec.ts
│   ├── 02-ppt-creation-flow.spec.ts
│   ├── 03-project-management.spec.ts
│   ├── 04-error-handling.spec.ts
│   └── 05-performance-accessibility.spec.ts
├── utils/
│   └── test-helpers.ts       # 页面对象模型和工具函数
├── global-setup.ts          # 全局设置
├── global-teardown.ts       # 全局清理
└── README.md               # 本文档
```

## 🎯 测试数据管理

测试使用固定的测试数据，避免依赖外部API：

```typescript
export const API_CONFIG = {
  valid: {
    apiKey: 'test-api-key-12345',
    endpoint: 'https://api.test.com',
    model: 'claude-3-sonnet',
  }
};

export const PROJECT_DATA = {
  simple: {
    title: 'Test Project',
    description: 'A simple test project',
    topic: 'Software Testing',
  }
};
```

## 📝 页面对象模型

使用页面对象模式提高测试可维护性：

```typescript
class AppPage {
  constructor(public page: Page) {}

  async createNewProject(projectData) {
    // 封装复杂的用户交互
  }

  async expectProjectToBeLoaded(projectName) {
    // 封装断言逻辑
  }
}
```

## 🚨 错误场景测试

模拟各种错误情况：

```typescript
class ErrorScenarios {
  async simulateNetworkFailure() {
    await this.page.context().setOffline(true);
  }

  async simulateAPIError(statusCode = 500) {
    await this.page.context().route('**/api/**', route => {
      route.fulfill({ status: statusCode });
    });
  }
}
```

## 📊 性能监控

集成性能监控功能：

```typescript
class PerformanceMonitor {
  async getPerformanceMetrics() {
    return await this.page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0];
      return {
        loadTime: navigation.loadEventEnd - navigation.navigationStart,
        // ... 其他指标
      };
    });
  }
}
```

## 🔄 CI/CD集成

在CI环境中运行测试：

```bash
# 无头模式，适合CI
npm run test:e2e

# 生成JUnit报告
PLAYWRIGHT_JUNIT_OUTPUT_FILE=test-results/junit.xml npm run test:e2e

# 上传测试报告
npm run test:e2e:report
```

## 📚 最佳实践

### 1. 测试数据隔离
- 每个测试使用独立的测试数据
- beforeEach中清理应用状态

### 2. 等待策略
- 使用显式等待而不是固定延时
- 等待网络空闲状态

### 3. 错误处理
- 测试各种错误场景
- 验证错误消息和恢复机制

### 4. 性能测试
- 设置合理的性能阈值
- 监控关键性能指标

### 5. 可访问性
- 测试键盘导航
- 验证屏幕阅读器支持

## 🐛 故障排除

### 常见问题

#### 测试超时
```bash
# 增加超时时间
npx playwright test --timeout=60000
```

#### 浏览器未安装
```bash
# 重新安装浏览器
npm run test:e2e:install --force
```

#### 端口冲突
确保开发服务器在正确端口(5173)运行：
```bash
npm run dev
```

### 调试技巧

1. **启用调试模式**
```bash
npm run test:e2e:debug
```

2. **查看浏览器操作**
```bash
npm run test:e2e:headed
```

3. **截图和视频**
测试失败时会自动生成截图和视频，位于 `test-results/` 目录

4. **追踪文件**
使用 `--trace on` 选项生成详细的执行追踪

## 📞 支持

如有问题请检查：
1. Playwright版本兼容性
2. 浏览器版本要求
3. Node.js版本支持
4. 测试环境配置

测试报告和日志保存在 `test-results/` 目录中，便于问题诊断和分析。