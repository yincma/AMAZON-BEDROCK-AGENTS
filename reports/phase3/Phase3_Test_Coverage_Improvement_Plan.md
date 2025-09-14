# Phase 3 测试覆盖率改进计划

## 当前状态总结
- **总体覆盖率**: 0% (0/5,289行)
- **测试通过率**: 83.5% (71/85)
- **主要问题**: 全部使用Mock测试，未执行实际代码

## 覆盖率提升路线图

### 阶段1: 基础单元测试 (目标覆盖率: 40%)
**预计工作量**: 2-3天
**目标**: 为核心组件添加真实的单元测试

#### 1.1 API处理器测试
```python
# tests/unit/test_api_handler_unit.py
import pytest
from lambdas.api_handler import APIHandler

class TestAPIHandlerUnit:
    def test_validate_request_structure(self):
        handler = APIHandler()
        valid_request = {
            "presentation_id": "test-123",
            "slide_number": 1,
            "title": "Test Title"
        }
        result = handler.validate_request(valid_request)
        assert result.is_valid is True

    def test_sanitize_user_input(self):
        handler = APIHandler()
        dirty_input = "<script>alert('xss')</script>Normal Text"
        clean_input = handler.sanitize_input(dirty_input)
        assert "<script>" not in clean_input
        assert "Normal Text" in clean_input
```

#### 1.2 内容生成器测试
```python
# tests/unit/test_content_generator_unit.py
from src.content_generator import ContentGenerator

class TestContentGeneratorUnit:
    def test_generate_slide_outline(self):
        generator = ContentGenerator()
        result = generator.generate_outline("人工智能", 5)
        assert len(result["slides"]) == 5
        assert all("title" in slide for slide in result["slides"])

    def test_content_length_validation(self):
        generator = ContentGenerator()
        long_topic = "A" * 1000  # 超长主题
        with pytest.raises(ValueError, match="Topic too long"):
            generator.generate_outline(long_topic, 5)
```

#### 1.3 PPT编译器测试
```python
# tests/unit/test_ppt_compiler_unit.py
from src.ppt_compiler import PPTCompiler
import tempfile
import os

class TestPPTCompilerUnit:
    def test_create_empty_presentation(self):
        compiler = PPTCompiler()
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp:
            compiler.create_empty_presentation(tmp.name)
            assert os.path.exists(tmp.name)
            assert os.path.getsize(tmp.name) > 0
            os.unlink(tmp.name)

    def test_add_slide_with_content(self):
        compiler = PPTCompiler()
        slide_data = {
            "title": "Test Slide",
            "content": ["Point 1", "Point 2"],
            "layout": "title_content"
        }
        result = compiler.add_slide(slide_data)
        assert result["slide_added"] is True
```

#### 1.4 验证器测试
```python
# tests/unit/test_validators_unit.py
from src.validators import PresentationValidator

class TestValidatorsUnit:
    def test_validate_slide_content_format(self):
        validator = PresentationValidator()
        valid_slide = {
            "slide_number": 1,
            "title": "Valid Title",
            "content": ["Valid content point"]
        }
        result = validator.validate_slide(valid_slide)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_detect_invalid_slide_number(self):
        validator = PresentationValidator()
        invalid_slide = {
            "slide_number": -1,  # 无效编号
            "title": "Title",
            "content": []
        }
        result = validator.validate_slide(invalid_slide)
        assert result.is_valid is False
        assert "Invalid slide number" in str(result.errors)
```

### 阶段2: 集成测试 (目标覆盖率: 65%)
**预计工作量**: 3-4天
**目标**: 测试组件间交互和工作流

#### 2.1 PPT生成工作流测试
```python
# tests/integration/test_ppt_workflow_integration.py
import pytest
from unittest.mock import patch
from lambdas.workflow_orchestrator import WorkflowOrchestrator

@pytest.mark.integration
class TestPPTWorkflowIntegration:
    @patch('boto3.client')
    def test_complete_ppt_generation_workflow(self, mock_boto):
        # 模拟AWS服务但使用真实业务逻辑
        orchestrator = WorkflowOrchestrator()
        request = {
            "topic": "机器学习基础",
            "page_count": 5,
            "style": "modern"
        }

        result = orchestrator.generate_presentation(request)

        assert result["status"] == "success"
        assert result["presentation_id"] is not None
        assert len(result["slides"]) == 5

    def test_error_handling_in_workflow(self):
        orchestrator = WorkflowOrchestrator()
        # 测试各种错误情况的处理
        invalid_request = {"page_count": -1}

        with pytest.raises(ValueError):
            orchestrator.generate_presentation(invalid_request)
```

#### 2.2 缓存机制集成测试
```python
# tests/integration/test_cache_integration.py
from lambdas.cache_manager import CacheManager
import tempfile
import json

class TestCacheIntegration:
    def test_cache_store_and_retrieve(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheManager(cache_dir=temp_dir)

            test_data = {"topic": "AI", "content": "Generated content"}
            cache_key = "test_key"

            # 存储
            cache.store(cache_key, test_data)

            # 检索
            retrieved = cache.get(cache_key)
            assert retrieved == test_data

    def test_cache_expiration(self):
        cache = CacheManager(ttl_seconds=1)  # 1秒过期
        cache.store("expire_test", {"data": "test"})

        import time
        time.sleep(2)  # 等待过期

        result = cache.get("expire_test")
        assert result is None
```

### 阶段3: 性能和端到端测试 (目标覆盖率: 85%)
**预计工作量**: 4-5天
**目标**: 真实性能测试和完整流程验证

#### 3.1 真实性能测试
```python
# tests/performance/test_actual_performance.py
import time
import pytest
from lambdas.performance_optimizer import PerformanceOptimizer

@pytest.mark.performance
class TestActualPerformance:
    def test_10_slide_generation_time(self):
        optimizer = PerformanceOptimizer()

        start_time = time.time()
        result = optimizer.generate_presentation_optimized({
            "topic": "性能测试主题",
            "page_count": 10,
            "enable_parallel": True
        })
        end_time = time.time()

        actual_time = end_time - start_time
        assert actual_time < 30.0  # 30秒要求
        assert result["status"] == "success"

    def test_memory_usage_monitoring(self):
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        optimizer = PerformanceOptimizer()
        optimizer.generate_large_presentation({"page_count": 20})

        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory

        assert memory_increase < 500  # 不超过500MB增长
```

#### 3.2 AWS服务集成测试
```python
# tests/integration/test_aws_services_integration.py
import pytest
import boto3
from moto import mock_s3, mock_dynamodb

@pytest.mark.aws
class TestAWSServicesIntegration:
    @mock_s3
    @mock_dynamodb
    def test_s3_and_dynamodb_integration(self):
        # 创建模拟的AWS资源
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-ppt-bucket')

        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='PresentationStatus',
            KeySchema=[{'AttributeName': 'presentation_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'presentation_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # 测试实际的AWS交互逻辑
        from lambdas.workflow_orchestrator import WorkflowOrchestrator
        orchestrator = WorkflowOrchestrator()

        result = orchestrator.generate_and_store({
            "presentation_id": "aws-test-123",
            "topic": "AWS集成测试"
        })

        assert result["s3_uploaded"] is True
        assert result["status_saved"] is True
```

## 测试文件结构规划

```
tests/
├── unit/                           # 单元测试 (40个测试)
│   ├── test_api_handler_unit.py           # API处理器 (8测试)
│   ├── test_content_generator_unit.py     # 内容生成 (8测试)
│   ├── test_ppt_compiler_unit.py          # PPT编译 (6测试)
│   ├── test_validators_unit.py            # 验证器 (8测试)
│   ├── test_image_processor_unit.py       # 图片处理 (6测试)
│   └── test_utils_unit.py                 # 工具函数 (4测试)
├── integration/                    # 集成测试 (25个测试)
│   ├── test_ppt_workflow_integration.py   # 工作流集成 (8测试)
│   ├── test_cache_integration.py          # 缓存集成 (5测试)
│   ├── test_aws_services_integration.py   # AWS集成 (7测试)
│   └── test_error_handling_integration.py # 错误处理 (5测试)
├── performance/                    # 性能测试 (15个测试)
│   ├── test_actual_performance.py         # 真实性能 (8测试)
│   ├── test_load_testing.py              # 负载测试 (4测试)
│   └── test_memory_profiling.py          # 内存分析 (3测试)
└── e2e/                           # 端到端测试 (10个测试)
    ├── test_complete_user_journey.py     # 完整用户流程 (5测试)
    └── test_api_endpoints_e2e.py         # API端到端 (5测试)
```

## 实施时间表

### 第1周: 基础设施搭建
- **第1-2天**: 设置测试环境和工具配置
- **第3天**: 创建基础测试文件结构
- **第4-5天**: 实现核心单元测试 (API处理器、内容生成器)

### 第2周: 单元测试完成
- **第6-7天**: PPT编译器和验证器单元测试
- **第8-9天**: 图片处理和工具函数测试
- **第10天**: 单元测试覆盖率验证 (目标40%)

### 第3周: 集成测试
- **第11-12天**: PPT工作流集成测试
- **第13-14天**: AWS服务和缓存集成测试
- **第15天**: 集成测试覆盖率验证 (目标65%)

### 第4周: 性能和E2E测试
- **第16-17天**: 真实性能测试实现
- **第18-19天**: 端到端测试和负载测试
- **第20天**: 最终覆盖率验证 (目标85%)

## 预期效果

### 覆盖率提升预期
1. **阶段1完成**: 40%覆盖率
   - 核心业务逻辑全覆盖
   - 基础错误处理验证

2. **阶段2完成**: 65%覆盖率
   - 组件交互全覆盖
   - 主要工作流验证

3. **阶段3完成**: 85%覆盖率
   - 性能要求验证
   - 完整用户场景覆盖

### 测试质量改进
- **可靠性**: 从Mock测试转向真实代码测试
- **有效性**: 能够发现实际的代码缺陷
- **维护性**: 测试与代码实现紧密关联

## 资源需求

### 开发资源
- **主要开发者**: 1人全时
- **测试支持**: 1人兼职
- **预计总工时**: 80-100小时

### 基础设施
- **测试环境**: AWS测试账户
- **CI/CD集成**: GitHub Actions配置
- **监控工具**: 代码覆盖率仪表板

## 风险和缓解措施

### 主要风险
1. **时间超支**: 复杂业务逻辑测试可能比预期耗时更长
   - **缓解**: 优先实现核心路径，逐步完善

2. **AWS服务依赖**: 真实AWS服务可能不稳定或产生费用
   - **缓解**: 使用moto库模拟，最小化真实服务使用

3. **测试环境问题**: 测试环境可能与生产环境不一致
   - **缓解**: 使用容器化测试环境，确保一致性

## 成功标准

### 定量指标
- ✅ 代码覆盖率 ≥ 85%
- ✅ 测试通过率 ≥ 95%
- ✅ 性能测试通过率 100%
- ✅ 集成测试通过率 ≥ 90%

### 定性指标
- ✅ 能够发现实际的代码缺陷
- ✅ 测试执行稳定可靠
- ✅ 测试维护成本可接受
- ✅ 支持持续集成流水线

这个改进计划将系统性地提升Phase 3的测试覆盖率，从当前的0%提升到85%以上，同时确保测试的实用性和可维护性。