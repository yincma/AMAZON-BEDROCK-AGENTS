# AI PPT Assistant - 集成测试自动化指南

## 概述

本指南介绍如何使用 AI PPT Assistant 项目中的集成测试自动化系统。该系统提供了全面的 API 测试、覆盖率报告和 CI/CD 集成。

## 快速开始

### 1. 安装依赖

```bash
pip install -r tests/requirements.txt
```

### 2. 运行集成测试

```bash
# 运行所有集成测试
python scripts/run_integration_tests.py run

# 运行特定类型的测试
python scripts/run_integration_tests.py run --categories api smoke

# 查看可用的测试类别
python scripts/run_integration_tests.py list
```

### 3. 生成覆盖率报告

```bash
# 生成完整的覆盖率报告
python scripts/generate_coverage_report.py --test-type all

# 仅生成 API 测试覆盖率
python scripts/generate_coverage_report.py --test-type api
```

## 测试类别

| 类别 | 描述 | 超时时间 | 标记 |
|------|------|----------|------|
| **API** | API 端点集成测试 | 300s | `integration and api` |
| **Smoke** | 快速验证测试 | 120s | `integration and smoke` |
| **Workflow** | 端到端工作流测试 | 600s | `integration and not slow` |
| **Performance** | 性能和负载测试 | 900s | `integration and slow` |
| **Concurrent** | 并发请求处理测试 | 300s | `integration and concurrent` |
| **Error** | 错误处理和边界测试 | 180s | `integration and error_handling` |

## API 测试覆盖

### 主要端点测试

1. **POST /presentations/generate** - 生成演示文稿
   - 正常流程测试
   - 无效请求处理
   - 重复请求检测
   - 超时处理

2. **GET /presentations/{id}** - 获取演示文稿状态
   - 处理中状态
   - 完成状态
   - 失败状态
   - 不存在的 ID

3. **GET /presentations/{id}/download** - 下载演示文稿
   - 成功下载
   - 文件未准备好
   - 文件不存在

4. **PATCH /presentations/{id}/slides/{slideId}** - 修改幻灯片
   - 成功修改
   - 幻灯片不存在
   - 演示文稿锁定

5. **GET /tasks/{task_id}** - 获取任务状态
   - 已完成任务
   - 运行中任务
   - 任务不存在

6. **GET /health** - 健康检查
   - 系统健康状态

### 测试场景

- **正常流程测试**: 验证 API 的基本功能
- **错误处理测试**: 测试各种错误情况
- **边界条件测试**: 测试极限情况和边界值
- **性能基准测试**: 测量响应时间和吞吐量
- **并发请求测试**: 验证并发处理能力

## GitHub Actions 集成

### 工作流文件

- `.github/workflows/integration-tests.yml`: 主要的集成测试工作流
- `.github/workflows/test.yml`: 综合测试套件（包括单元测试和集成测试）

### 触发条件

- 推送到 `main` 或 `develop` 分支
- 创建到 `main` 分支的 Pull Request
- 每日定时运行（UTC 06:00）
- 手动触发

### 测试矩阵

工作流支持以下测试矩阵：
- **api**: API 端点测试
- **smoke**: 冒烟测试
- **performance**: 性能测试
- **concurrent**: 并发测试

### 环境配置

- **Mocked AWS**: 使用 moto 模拟 AWS 服务（默认）
- **Real AWS**: 使用真实的 AWS 开发环境（需要配置凭据）

## 覆盖率报告

### 生成的报告类型

1. **XML 报告**: `coverage.xml` - 用于 CI/CD 集成
2. **HTML 报告**: `htmlcov/` - 可视化覆盖率报告
3. **JSON 报告**: `coverage.json` - 机器可读的详细数据
4. **Markdown 总结**: `test-results/coverage-summary-*.md`
5. **HTML 仪表板**: `test-results/coverage-dashboard-*.html`

### 覆盖率目标

- **优秀**: ≥ 90%
- **良好**: ≥ 80%
- **可接受**: ≥ 70%
- **需要改进**: < 70%

### 徽章和状态

覆盖率徽章会自动生成并可以嵌入到 README 中：

```markdown
![Coverage](https://img.shields.io/badge/coverage-85.2%25-brightgreen)
```

## 配置文件

### pytest 配置

- `tests/pytest.ini`: 主要 pytest 配置
- `tests/integration/pytest.ini`: 集成测试专用配置
- `tests/conftest.py`: 共享 fixtures 和设置
- `tests/coverage.ini`: 覆盖率配置

### 测试配置

- `tests/integration/test_config.py`: 集成测试配置类
- `.env.test`: 测试环境变量（自动生成）

## 高级用法

### 自定义测试运行

```bash
# 仅运行 API 测试，使用真实 AWS
python scripts/run_integration_tests.py run \
  --categories api \
  --aws-mode real \
  --fail-fast

# 运行性能测试并启用并行执行
python scripts/run_integration_tests.py run \
  --categories performance \
  --parallel
```

### 趋势分析

```bash
# 分析过去7天的测试趋势
python scripts/run_integration_tests.py analyze --days 7
```

### 自定义覆盖率报告

```bash
# 跳过测试执行，仅生成报告
python scripts/generate_coverage_report.py \
  --skip-tests \
  --test-type integration

# 清理旧报告（保留30天）
python scripts/generate_coverage_report.py \
  --cleanup-days 30
```

## 故障排除

### 常见问题

1. **测试超时**
   - 检查 AWS 服务可用性
   - 增加超时设置
   - 检查网络连接

2. **覆盖率低**
   - 查看覆盖率报告中的缺失行
   - 添加针对未覆盖代码的测试
   - 检查测试标记是否正确

3. **AWS 权限错误**
   - 验证 AWS 凭据配置
   - 检查 IAM 权限
   - 切换到 mocked 模式进行本地测试

### 调试技巧

```bash
# 运行详细输出的测试
pytest tests/integration/test_validation.py -v -s

# 运行特定测试类
pytest tests/integration/api_tests.py::TestPresentationGenerationAPI -v

# 使用调试模式
pytest tests/integration/api_tests.py --pdb
```

## 最佳实践

### 编写集成测试

1. **使用适当的标记**: 确保测试有正确的 pytest 标记
2. **模拟外部服务**: 使用 moto 模拟 AWS 服务
3. **独立测试**: 确保测试可以独立运行
4. **清晰的断言**: 使用描述性的断言消息
5. **适当的超时**: 设置合理的测试超时时间

### 维护测试

1. **定期审查**: 定期检查测试覆盖率和质量
2. **更新依赖**: 保持测试依赖项的最新版本
3. **性能监控**: 监控测试执行时间
4. **清理资源**: 确保测试后清理创建的资源

## 参与贡献

### 添加新测试

1. 在 `tests/integration/api_tests.py` 中添加新的测试方法
2. 使用适当的 pytest 标记
3. 更新相关的配置和文档
4. 确保测试通过 CI/CD 检查

### 报告问题

如果发现测试问题，请创建 GitHub issue，包含：
- 详细的错误信息
- 重现步骤
- 环境信息
- 相关的日志文件

---

## 总结

AI PPT Assistant 的集成测试自动化系统提供了：

✅ **全面的 API 测试覆盖**  
✅ **自动化的覆盖率报告**  
✅ **完整的 CI/CD 集成**  
✅ **详细的测试分析和报告**  
✅ **灵活的配置和扩展性**  

通过这个系统，团队可以确保代码质量，快速发现问题，并维持高质量的软件交付。