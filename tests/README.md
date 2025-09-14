# 图片生成服务集成测试套件

这是一个为图片生成服务设计的综合测试套件，提供了完整的测试覆盖，包括单元测试、集成测试、性能测试和压力测试。

## 🚀 快速开始

### 安装依赖
```bash
pip install -r tests/requirements.txt
```

### 运行基础测试
```bash
# 使用便捷脚本
python scripts/run_image_tests.py --unit

# 或直接使用pytest
pytest tests/test_image_processing_service.py -v
```

## 📁 测试文件结构

```
tests/
├── conftest.py                              # 全局fixtures和配置
├── test_utils.py                           # 测试工具和Mock助手
├── test_image_processing_service.py        # 单元测试
├── test_image_generator.py                # TDD测试用例
├── test_image_comprehensive_integration.py # 🔧 综合集成测试
├── test_image_performance_benchmarks.py   # ⚡ 性能基准测试
├── test_image_stress_concurrency.py       # 💪 压力和并发测试
├── generate_test_report.py                # 📊 测试报告生成器
└── run_image_tests.py                     # 🎯 便捷执行脚本
```

## 🧪 测试类型

### 单元测试 (Unit Tests)
- ✅ 提示词生成逻辑
- ✅ 图片格式验证
- ✅ 缓存机制
- ✅ 错误处理
- ✅ 配置管理

### 集成测试 (Integration Tests)
- ✅ 完整的图片生成流程
- ✅ 多模型fallback机制
- ✅ 缓存系统集成
- ✅ AWS服务集成
- ✅ 错误恢复机制

### 性能测试 (Performance Tests)
- ⚡ 提示词生成: < 50ms
- ⚡ 缓存查找: < 1ms
- ⚡ 图片验证: < 10ms
- ⚡ 并发处理能力
- ⚡ 内存使用效率

### 压力测试 (Stress Tests)
- 💪 高并发请求处理
- 💪 持续负载测试
- 💪 突发流量处理
- 💪 内存压力测试
- 💪 故障恢复能力

## 🛠️ 使用方法

### 基本命令
```bash
# 运行单元测试
python scripts/run_image_tests.py --unit

# 运行集成测试
python scripts/run_image_tests.py --integration

# 运行性能测试
python scripts/run_image_tests.py --performance

# 运行压力测试
python scripts/run_image_tests.py --stress

# 运行所有测试
python scripts/run_image_tests.py --all

# 生成测试报告
python scripts/run_image_tests.py --report
```

### pytest直接使用
```bash
# 按标记运行
pytest -m "unit" -v
pytest -m "integration" -v
pytest -m "performance" -v
pytest -m "stress" -v

# 带覆盖率
pytest --cov=lambdas --cov-report=html

# 并行执行
pytest -n auto

# 性能基准
pytest --benchmark-only
```

## 📊 关键特性

### 🎯 智能Mock系统
- **真实AWS响应**: 模拟真实的Bedrock和S3响应格式
- **故障注入**: 可配置的失败率和延迟
- **渐进式复杂度**: 从简单Mock到智能Mock

### ⚡ 性能监控
- **基准测试**: 自动化性能基准建立和跟踪
- **资源监控**: 内存、CPU使用率实时监控
- **性能分析**: 详细的性能指标和瓶颈分析

### 💪 并发测试
- **线程安全**: 验证服务的线程安全性
- **负载测试**: 多级负载测试支持
- **故障恢复**: 验证在高负载下的错误恢复能力

### 📈 自动化报告
- **测试覆盖率**: 详细的代码覆盖率分析
- **性能趋势**: 性能指标历史趋势跟踪
- **质量评分**: 基于多指标的自动质量评分

## 🔧 配置选项

### pytest.ini配置
```ini
[tool:pytest]
markers =
    unit: 单元测试
    integration: 集成测试
    performance: 性能测试
    stress: 压力测试
    slow: 运行时间较长的测试

# 覆盖率要求
addopts = --cov=lambdas --cov-fail-under=80
```

### 环境变量
```bash
export ENVIRONMENT=test
export AWS_ACCESS_KEY_ID=testing
export AWS_SECRET_ACCESS_KEY=testing
export AWS_DEFAULT_REGION=us-east-1
export DEBUG=true
export CACHE_ENABLED=true
```

## 🚀 CI/CD集成

### GitHub Actions
项目包含完整的GitHub Actions工作流:
- ✅ 多Python版本测试 (3.11, 3.12, 3.13)
- ✅ 分层测试执行
- ✅ 自动覆盖率报告
- ✅ 性能基准跟踪
- ✅ 质量门禁检查

### 触发条件
- 推送到main/dev分支
- Pull Request
- 每日定时执行
- 手动触发

## 📊 性能基准

| 测试项 | 目标时间 | 优秀 | 良好 | 需优化 |
|--------|----------|------|------|---------|
| 提示词生成 | < 50ms | < 25ms | < 50ms | > 50ms |
| 缓存查找 | < 1ms | < 0.5ms | < 1ms | > 1ms |
| 图片验证 | < 10ms | < 5ms | < 10ms | > 10ms |
| 完整生成流程 | < 5s | < 2s | < 5s | > 5s |

## 🛡️ 质量门禁

- **基础测试成功率**: > 95%
- **集成测试成功率**: > 90%
- **代码覆盖率**: > 80%
- **性能基准**: 满足预设阈值

## 📚 详细文档

- 📖 [完整测试指南](../docs/testing/IMAGE_SERVICE_TESTING_GUIDE.md)
- 🔧 [配置文档](pytest.ini)
- 🚀 [CI/CD配置](../.github/workflows/image-service-tests.yml)

## 🤝 贡献指南

1. 添加新功能时，请确保包含相应的测试
2. 保持测试覆盖率在80%以上
3. 性能测试应满足基准要求
4. 所有测试应通过质量门禁

## 🐛 故障排除

### 常见问题
```bash
# 测试超时
pytest --timeout=600

# 内存不足
pytest --maxfail=1

# Mock失效
# 检查Mock配置和断言

# 并发测试不稳定
# 增加重试机制或调整并发参数
```

### 调试技巧
```bash
# 详细日志
pytest -s --log-cli-level=DEBUG

# 交互式调试
import pdb; pdb.set_trace()

# 单独运行
pytest tests/test_specific.py::test_function -v
```

## ✨ 主要优势

- 🎯 **全面覆盖**: 从单元到端到端的完整测试
- 🚀 **高度自动化**: CI/CD集成和自动化报告
- 💡 **智能Mock**: 真实的AWS服务模拟
- 📊 **性能监控**: 持续的性能基准跟踪
- 🔧 **易于扩展**: 模块化设计，易于添加新测试
- 📈 **质量保证**: 多维度的质量评估和改进建议

---

🤖 *这个测试套件为图片生成服务提供了企业级的质量保证，确保代码的可靠性、性能和可维护性。*