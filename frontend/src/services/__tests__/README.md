# 服务单元测试文档

## 概述

本目录包含了前端服务层的完整单元测试套件，使用Jest测试框架和TypeScript。测试覆盖了以下四个核心服务：

## 测试文件

### 1. ApiService.test.ts
**测试范围**: HTTP API客户端服务
- ✅ HTTP方法（GET、POST、PUT、DELETE、PATCH）
- ✅ 错误处理和重试逻辑
- ✅ 请求/响应拦截器
- ✅ 超时处理
- ✅ 请求取消
- ✅ 健康检查
- ✅ API密钥管理
- ✅ 响应元数据处理

**关键测试点**:
- 成功请求处理
- 网络错误处理
- HTTP错误响应处理
- 自动重试机制（503、502等状态码）
- 请求配置更新
- AbortController集成

### 2. PptService.test.ts
**测试范围**: PPT生成服务
- ✅ 会话管理（创建、获取、设置）
- ✅ 事件监听系统
- ✅ 大纲操作（创建、更新）
- ✅ 内容增强（单个、批量）
- ✅ PPT生成和进度跟踪
- ✅ 文件下载
- ✅ 资源清理

**关键测试点**:
- 会话自动创建
- 事件发射和监听
- 进度轮询机制
- 错误处理和重试
- 异步操作管理
- 内存泄漏防护

### 3. StorageService.test.ts
**测试范围**: 本地存储服务
- ✅ 项目CRUD操作
- ✅ 用户偏好管理
- ✅ API配置存储
- ✅ 缓存机制（TTL支持）
- ✅ 数据导入/导出
- ✅ 搜索和过滤
- ✅ 存储信息统计
- ✅ 最近项目管理

**关键测试点**:
- LocalForage集成
- 数据一致性
- 缓存过期处理
- 批量导入逻辑
- 存储空间管理
- 备份和恢复

### 4. ImageService.test.ts
**测试范围**: 图片搜索服务
- ✅ 图片搜索和过滤
- ✅ 批量搜索（速率限制）
- ✅ 缓存机制（内存+持久化）
- ✅ 搜索历史管理
- ✅ 图片建议生成
- ✅ 热门搜索统计
- ✅ 图片下载和元数据获取
- ✅ URL验证

**关键测试点**:
- 多层缓存策略
- 关键词提取算法
- 搜索历史限制
- 速率限制实现
- 图片格式验证
- 错误恢复机制

## 测试配置

### Jest配置 (jest.config.cjs)
```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/vite-env.d.ts',
    '!src/main.tsx'
  ],
  coverageDirectory: 'coverage',
  testTimeout: 10000
};
```

### 测试设置 (setupTests.ts)
- Mock localStorage
- Mock fetch API
- Mock URL构造函数
- Mock import.meta.env
- 自动清理模拟数据

## 模拟策略

### 外部依赖模拟
- **axios**: 完整模拟HTTP客户端
- **localforage**: 模拟IndexedDB存储
- **定时器**: 使用jest.useFakeTimers()
- **网络请求**: 模拟API响应

### 测试工具
- **jest.fn()**: 函数模拟
- **jest.spyOn()**: 方法监听
- **jest.clearAllMocks()**: 清理模拟状态
- **假定时器**: 测试异步操作

## 运行测试

### 基本测试命令
```bash
# 运行所有测试
npm test

# 监听模式
npm run test:watch

# 生成覆盖率报告
npm run test:coverage

# CI环境测试
npm run test:ci
```

### 测试覆盖目标
- **行覆盖率**: >80%
- **函数覆盖率**: >80%
- **分支覆盖率**: >75%
- **语句覆盖率**: >80%

## 测试数据

### 模拟数据示例
```typescript
const mockProject: Project = {
  id: 'project-123',
  title: 'Test Project',
  description: 'A test project',
  topic: 'AI Technology',
  settings: {
    slidesCount: 10,
    theme: 'professional',
    includeImages: true,
    language: 'en',
    tone: 'professional'
  },
  status: ProjectStatus.DRAFT,
  createdAt: new Date('2023-01-01T00:00:00Z'),
  updatedAt: new Date('2023-01-01T12:00:00Z')
};
```

## 质量保证

### 测试原则
1. **独立性**: 每个测试独立运行，不依赖其他测试
2. **可重复性**: 测试结果应该是确定性的
3. **快速反馈**: 测试应该快速执行并提供明确的错误信息
4. **边界测试**: 测试正常情况、边界情况和错误情况
5. **实际使用场景**: 测试应该反映真实的使用模式

### 错误处理测试
- 网络错误
- 服务器错误（4xx, 5xx）
- 超时错误
- 解析错误
- 存储错误
- 验证错误

### 异步操作测试
- Promise处理
- 事件发射
- 定时器操作
- 进度更新
- 取消操作
- 并发控制

## 维护指南

### 添加新测试
1. 创建测试文件: `ServiceName.test.ts`
2. 导入必要的依赖和模拟
3. 设置beforeEach/afterEach钩子
4. 编写描述性的测试用例
5. 确保测试覆盖率达标

### 更新现有测试
1. 当服务接口改变时更新测试
2. 添加新功能的测试用例
3. 维护模拟数据的一致性
4. 更新文档和注释

## 问题排查

### 常见问题
1. **模块解析错误**: 检查导入路径和Jest配置
2. **异步测试超时**: 增加testTimeout或使用done回调
3. **模拟未生效**: 确保模拟在测试运行前设置
4. **内存泄漏**: 确保在afterEach中清理资源

### 调试技巧
- 使用`console.log`输出调试信息
- 使用Jest的`--verbose`标志查看详细输出
- 使用`--detectOpenHandles`检测资源泄漏
- 单独运行失败的测试用例

## 总结

本测试套件提供了全面的服务层测试覆盖，确保了：
- 🎯 **高质量**: 严格的测试标准和边界用例覆盖
- 🚀 **可维护性**: 清晰的测试结构和模拟策略
- 🔒 **可靠性**: 全面的错误处理和异常情况测试
- ⚡ **性能**: 快速执行和准确的反馈

测试套件为前端应用提供了坚实的质量保障基础。