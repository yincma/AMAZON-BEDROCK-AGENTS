"""
图片生成服务综合集成测试套件
测试覆盖正常流程、异常流程、性能、并发、缓存等各种场景
"""

import pytest
import asyncio
import time
import json
import concurrent.futures
import threading
from unittest.mock import Mock, patch, MagicMock, call
import io
from PIL import Image
import hashlib
import base64
import boto3
from botocore.exceptions import ClientError, BotoCoreError
import statistics

# 导入被测试的模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas'))

from image_processing_service import ImageProcessingService
from image_config import CONFIG
from image_exceptions import (
    ImageProcessingError, NovaServiceError, S3OperationError,
    ValidationError, ConfigurationError
)


class TestImageProcessingServiceIntegration:
    """图片处理服务集成测试"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.test_prompt = "专业商务演示图片，现代简洁风格，高质量4K分辨率"
        self.test_slide_content = {
            "title": "人工智能的未来发展",
            "content": [
                "机器学习算法的突破",
                "深度学习的广泛应用",
                "AI对各行业的影响"
            ]
        }

    @pytest.fixture
    def mock_bedrock_client(self):
        """模拟Bedrock客户端"""
        client = Mock()

        # 模拟Nova Canvas成功响应
        nova_response_body = {
            "images": ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hRqYEAAAAABJRU5ErkJggg=="]
        }

        # 模拟Stability AI成功响应
        stability_response_body = {
            "artifacts": [{
                "base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hRqYEAAAAABJRU5ErkJggg=="
            }]
        }

        def mock_invoke_model(**kwargs):
            model_id = kwargs.get('modelId', '')
            body = json.loads(kwargs.get('body', '{}'))

            if 'nova' in model_id:
                response_body = nova_response_body
            elif 'stability' in model_id:
                response_body = stability_response_body
            else:
                response_body = {"error": "Unsupported model"}

            mock_response = Mock()
            mock_response.read.return_value = json.dumps(response_body).encode('utf-8')

            return {
                'body': mock_response,
                'ResponseMetadata': {'HTTPStatusCode': 200}
            }

        client.invoke_model.side_effect = mock_invoke_model
        return client

    @pytest.fixture
    def mock_s3_client(self):
        """模拟S3客户端"""
        client = Mock()

        # 模拟get_object - 缓存未命中
        client.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}}, 'GetObject'
        )

        # 模拟put_object - 缓存保存成功
        client.put_object.return_value = {'ETag': 'test-etag'}

        return client

    def test_complete_image_generation_workflow(self, mock_bedrock_client, mock_s3_client):
        """测试完整的图片生成工作流"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        # 测试生成提示词
        prompt = service.generate_prompt(self.test_slide_content)
        assert isinstance(prompt, str)
        assert len(prompt) > 20
        assert "人工智能" in prompt or "AI" in prompt

        # 测试图片生成
        image_data = service.call_image_generation(prompt)
        assert isinstance(image_data, bytes)
        assert len(image_data) > 0

        # 验证图片格式
        assert service.validate_image_format(image_data, 'PNG')

        # 测试图片优化
        optimized_data = service.optimize_image_size(image_data)
        assert isinstance(optimized_data, bytes)

    def test_fallback_mechanism_all_models(self, mock_s3_client):
        """测试多模型fallback机制"""
        # 创建一个会让所有模型都失败的客户端
        failing_client = Mock()
        failing_client.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException'}}, 'InvokeModel'
        )

        service = ImageProcessingService(
            bedrock_client=failing_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        # 应该回退到占位图
        image_data = service.call_image_generation(self.test_prompt)
        assert isinstance(image_data, bytes)
        assert len(image_data) > 0

        # 验证是占位图（PNG格式）
        assert service.validate_image_format(image_data, 'PNG')

    def test_caching_system_comprehensive(self, mock_bedrock_client, mock_s3_client):
        """测试缓存系统的完整功能"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        # 第一次调用 - 应该调用Bedrock
        prompt = "测试缓存功能"
        image_data_1 = service.call_image_generation(prompt)
        assert mock_bedrock_client.invoke_model.call_count == 1

        # 第二次调用相同提示词 - 应该从内存缓存返回
        image_data_2 = service.call_image_generation(prompt)
        assert mock_bedrock_client.invoke_model.call_count == 1  # 不应该增加
        assert image_data_1 == image_data_2

        # 测试缓存统计
        stats = service.get_cache_stats()
        assert stats['memory_cache_size'] == 1
        assert stats['cache_enabled'] is True
        assert stats['s3_cache_enabled'] is True

        # 清除缓存
        service.clear_cache()
        stats = service.get_cache_stats()
        assert stats['memory_cache_size'] == 0

    def test_s3_cache_integration(self, mock_bedrock_client):
        """测试S3缓存集成"""
        # 模拟S3缓存命中
        cached_image_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hRqYEAAAAABJRU5ErkJggg=="
        )

        mock_s3_client = Mock()
        mock_response = Mock()
        mock_response.read.return_value = cached_image_data
        mock_s3_client.get_object.return_value = {'Body': mock_response}

        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        prompt = "S3缓存测试"
        image_data = service.call_image_generation(prompt)

        # 应该从S3缓存返回，不调用Bedrock
        assert mock_bedrock_client.invoke_model.call_count == 0
        assert image_data == cached_image_data

    def test_error_handling_comprehensive(self, mock_s3_client):
        """测试全面的错误处理"""

        # 测试1: Bedrock服务临时不可用
        failing_client = Mock()
        failing_client.invoke_model.side_effect = [
            ClientError({'Error': {'Code': 'ThrottlingException'}}, 'InvokeModel'),
            ClientError({'Error': {'Code': 'ThrottlingException'}}, 'InvokeModel'),
            # 第三次成功
            Mock(body=Mock(read=Mock(return_value=json.dumps({
                "images": ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hRqYEAAAAABJRU5ErkJggg=="]
            }).encode())))
        ]

        service = ImageProcessingService(
            bedrock_client=failing_client,
            s3_client=mock_s3_client
        )

        # 应该重试后成功
        with patch('time.sleep'):  # 跳过实际的sleep
            image_data = service.call_image_generation(self.test_prompt)

        assert isinstance(image_data, bytes)
        assert failing_client.invoke_model.call_count >= 2

    def test_concurrent_generation_safety(self, mock_bedrock_client, mock_s3_client):
        """测试并发图片生成的安全性"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        def generate_image(prompt_suffix):
            prompt = f"并发测试 {prompt_suffix}"
            return service.call_image_generation(prompt)

        # 并发生成多个图片
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(generate_image, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 所有结果都应该成功
        assert len(results) == 10
        for result in results:
            assert isinstance(result, bytes)
            assert len(result) > 0

    def test_model_priority_and_preference(self, mock_s3_client):
        """测试模型优先级和偏好设置"""
        mock_client = Mock()

        def mock_invoke_with_tracking(**kwargs):
            model_id = kwargs.get('modelId', '')
            # 记录调用的模型
            if not hasattr(mock_invoke_with_tracking, 'called_models'):
                mock_invoke_with_tracking.called_models = []
            mock_invoke_with_tracking.called_models.append(model_id)

            # 模拟成功响应
            mock_response = Mock()
            mock_response.read.return_value = json.dumps({
                "images": ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hRqYEAAAAABJRU5ErkJggg=="]
            }).encode()

            return {'body': mock_response}

        mock_client.invoke_model.side_effect = mock_invoke_with_tracking

        service = ImageProcessingService(
            bedrock_client=mock_client,
            s3_client=mock_s3_client
        )

        # 测试指定首选模型
        service.call_image_generation(
            self.test_prompt,
            model_preference="stability.stable-diffusion-xl-v1"
        )

        # 验证首选模型被首先调用
        called_models = mock_invoke_with_tracking.called_models
        assert len(called_models) == 1
        assert "stability" in called_models[0]

    def test_prompt_optimization_effectiveness(self, mock_bedrock_client, mock_s3_client):
        """测试提示词优化的有效性"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client
        )

        # 测试不同类型的内容优化
        test_cases = [
            {
                "content": {"title": "AI技术", "content": ["机器学习", "深度学习"]},
                "audience": "business",
                "expected_keywords": ["科技", "商务", "专业"]
            },
            {
                "content": {"title": "教育培训", "content": ["课程设计", "学习方法"]},
                "audience": "academic",
                "expected_keywords": ["教育", "学术", "知识"]
            },
            {
                "content": {"title": "创意设计", "content": ["视觉艺术", "创新思维"]},
                "audience": "creative",
                "expected_keywords": ["创意", "艺术", "设计"]
            }
        ]

        for case in test_cases:
            prompt = service.generate_prompt(case["content"], case["audience"])

            # 验证提示词包含预期关键词
            assert any(keyword in prompt for keyword in case["expected_keywords"])

            # 验证提示词质量
            assert "高质量" in prompt or "4K" in prompt
            assert len(prompt) > 30
            assert len(prompt) < 600  # 不应过长

    def test_image_validation_comprehensive(self, mock_bedrock_client, mock_s3_client):
        """测试图片验证的全面功能"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client
        )

        # 创建不同格式的测试图片
        def create_test_image(format='PNG', size=(800, 600)):
            image = Image.new('RGB', size, color='blue')
            img_bytes = io.BytesIO()
            image.save(img_bytes, format=format)
            return img_bytes.getvalue()

        # 测试PNG格式验证
        png_data = create_test_image('PNG')
        assert service.validate_image_format(png_data, 'PNG') is True
        assert service.validate_image_format(png_data, 'JPEG') is False

        # 测试JPEG格式验证
        jpg_data = create_test_image('JPEG')
        assert service.validate_image_format(jpg_data, 'JPEG') is True
        assert service.validate_image_format(jpg_data, 'PNG') is False

        # 测试无效数据
        invalid_data = b"这不是图片数据"
        assert service.validate_image_format(invalid_data, 'PNG') is False

    def test_image_optimization_performance(self, mock_bedrock_client, mock_s3_client):
        """测试图片优化性能"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client
        )

        # 创建大尺寸测试图片
        def create_large_image():
            image = Image.new('RGB', (2000, 1500), color='red')
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            return img_bytes.getvalue()

        large_image_data = create_large_image()
        original_size = len(large_image_data)

        # 测试尺寸优化
        start_time = time.time()
        optimized_data = service.optimize_image_size(large_image_data, 800, 600)
        optimization_time = time.time() - start_time

        # 验证优化效果
        optimized_size = len(optimized_data)

        # 优化应该在合理时间内完成
        assert optimization_time < 2.0

        # 验证优化后的图片尺寸
        optimized_image = Image.open(io.BytesIO(optimized_data))
        assert optimized_image.width <= 800
        assert optimized_image.height <= 600

    def test_placeholder_image_creation(self, mock_bedrock_client, mock_s3_client):
        """测试占位图创建的各种场景"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client
        )

        # 测试默认占位图
        placeholder_data = service.create_placeholder_image()
        assert isinstance(placeholder_data, bytes)
        assert service.validate_image_format(placeholder_data, 'PNG')

        # 测试自定义尺寸占位图
        custom_placeholder = service.create_placeholder_image(400, 300, "自定义文本")
        assert isinstance(custom_placeholder, bytes)

        # 验证尺寸
        custom_image = Image.open(io.BytesIO(custom_placeholder))
        assert custom_image.width == 400
        assert custom_image.height == 300

        # 测试长文本处理
        long_text = "这是一个很长的文本" * 10
        long_text_placeholder = service.create_placeholder_image(text=long_text)
        assert isinstance(long_text_placeholder, bytes)

    def test_edge_cases_and_boundary_conditions(self, mock_bedrock_client, mock_s3_client):
        """测试边界条件和极端情况"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client
        )

        # 测试空内容
        empty_content = {"title": "", "content": []}
        prompt = service.generate_prompt(empty_content)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # 测试只有标题的内容
        title_only = {"title": "仅标题测试", "content": []}
        prompt = service.generate_prompt(title_only)
        assert "仅标题测试" in prompt

        # 测试只有内容的情况
        content_only = {"title": "", "content": ["内容1", "内容2"]}
        prompt = service.generate_prompt(content_only)
        assert "内容1" in prompt or "内容2" in prompt

        # 测试特殊字符处理
        special_chars = {
            "title": "标题@#$%^&*()",
            "content": ["内容包含emoji 🚀", "数字123", "符号!@#$%"]
        }
        prompt = service.generate_prompt(special_chars)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

        # 测试非常长的内容
        long_content = {
            "title": "超长标题" * 20,
            "content": ["超长内容项目" * 50 for _ in range(10)]
        }
        prompt = service.generate_prompt(long_content)
        assert isinstance(prompt, str)
        assert len(prompt) < 600  # 应该被优化截断

    def test_memory_management_and_cleanup(self, mock_bedrock_client, mock_s3_client):
        """测试内存管理和清理"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        # 生成大量图片以填充缓存
        for i in range(20):
            prompt = f"内存测试 {i}"
            service.call_image_generation(prompt)

        # 检查缓存大小
        stats_before = service.get_cache_stats()
        assert stats_before['memory_cache_size'] == 20

        # 清除缓存
        service.clear_cache()

        # 验证清理效果
        stats_after = service.get_cache_stats()
        assert stats_after['memory_cache_size'] == 0

    def test_configuration_flexibility(self):
        """测试配置的灵活性"""
        # 测试不同配置的服务创建

        # 禁用缓存的服务
        service_no_cache = ImageProcessingService(enable_caching=False)
        assert service_no_cache.enable_caching is False
        assert service_no_cache.s3_client is None

        # 自定义模型列表
        service_custom = ImageProcessingService()
        original_models = service_custom.supported_models.copy()

        # 验证支持的模型
        assert "amazon.nova-canvas-v1:0" in service_custom.supported_models
        assert "stability.stable-diffusion-xl-v1" in service_custom.supported_models

    def test_exception_handling_specificity(self, mock_s3_client):
        """测试具体异常的处理"""

        # 测试NovaServiceError
        failing_client = Mock()
        failing_client.invoke_model.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': '模型不存在'}},
            'InvokeModel'
        )

        service = ImageProcessingService(
            bedrock_client=failing_client,
            s3_client=mock_s3_client
        )

        # 应该处理异常并回退到占位图
        image_data = service.call_image_generation(self.test_prompt)
        assert isinstance(image_data, bytes)

        # 验证是占位图
        assert service.validate_image_format(image_data, 'PNG')

    def test_integration_with_real_aws_format(self, mock_bedrock_client, mock_s3_client):
        """测试与真实AWS响应格式的集成"""
        # 模拟真实的AWS Bedrock响应格式
        realistic_nova_response = {
            "images": [
                # 这是一个1x1像素的PNG图片的base64
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw0AcxV9TpSItDnYQcchQnSyIijhKFYtgobQVWnUwufQLmjQkKS6OgmvBwY/FqoOLs64OroIg+AHi5uak6CIl/i8ptIjx4Lgf7+497t4BQqPCVLNrAlA1y0jFY2I2tyoGXuHHCPogICgxU5+TkiS085jT3S936p1lW5mf+5OC3TGbAXpEOsb0LYvwOvn0ZFXOeY89wsoSySDOnHhU0A9Jlwy4hvAeY7SYN4gni09FLpk8QixKdBSzmFE5ocWyLisyauUs8QiPptBDki/JrhQyLnfcayWdqt37c3wjVyxkKg3l4piAOcEJZKhGDWE0sJKokMFIhngn1j8s68eRLBVZAwXQAAdKWIUEMmf9i3Wt8y6LuYtKdDOQfrDbQMTn6Iysk30YxXo2yL8fQ2N/cj5SYLwbaH5zjLs6CPA2cHjDp1P2u6Dqe5+F4V1oJgCJCNgdAGFuJiD2BPp5qe35J4lIkFXG7qILMfFh6PggYNaVN8I"
            ],
            "seed": 12345,
            "finishReason": "SUCCESS"
        }

        mock_bedrock_client.invoke_model.return_value = {
            'body': Mock(read=Mock(return_value=json.dumps(realistic_nova_response).encode())),
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }

        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client
        )

        image_data = service.call_image_generation(self.test_prompt)
        assert isinstance(image_data, bytes)
        assert len(image_data) > 0


class TestPerformanceBenchmarks:
    """性能基准测试"""

    def setup_method(self):
        """性能测试设置"""
        self.performance_thresholds = {
            "single_generation_max_time": 5.0,  # 单次生成最大时间（秒）
            "batch_generation_max_time": 30.0,  # 批量生成最大时间（秒）
            "prompt_generation_max_time": 0.1,  # 提示词生成最大时间（秒）
            "cache_lookup_max_time": 0.01,     # 缓存查找最大时间（秒）
            "concurrent_max_time": 10.0,       # 并发处理最大时间（秒）
        }

    @pytest.mark.performance
    def test_single_image_generation_performance(self, mock_bedrock_client, mock_s3_client):
        """测试单张图片生成性能"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client
        )

        prompt = "性能测试用提示词，现代商务风格"

        # 预热
        service.call_image_generation(prompt)

        # 性能测试
        start_time = time.time()
        image_data = service.call_image_generation(prompt)
        end_time = time.time()

        generation_time = end_time - start_time

        # 验证性能
        assert generation_time < self.performance_thresholds["single_generation_max_time"]
        assert isinstance(image_data, bytes)
        assert len(image_data) > 0

    @pytest.mark.performance
    def test_prompt_generation_performance(self):
        """测试提示词生成性能"""
        service = ImageProcessingService()

        test_content = {
            "title": "AI技术发展趋势分析报告",
            "content": [
                "深度学习技术的突破与创新",
                "自然语言处理的商业化应用",
                "计算机视觉在各行业的落地实践",
                "机器学习算法的优化与改进",
                "人工智能伦理与可持续发展"
            ]
        }

        # 批量性能测试
        times = []
        for _ in range(100):
            start_time = time.perf_counter()
            prompt = service.generate_prompt(test_content)
            end_time = time.perf_counter()

            times.append(end_time - start_time)
            assert isinstance(prompt, str)
            assert len(prompt) > 0

        # 性能分析
        avg_time = statistics.mean(times)
        max_time = max(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile

        assert avg_time < self.performance_thresholds["prompt_generation_max_time"]
        assert max_time < self.performance_thresholds["prompt_generation_max_time"] * 2

        print(f"提示词生成性能统计:")
        print(f"平均时间: {avg_time:.4f}s")
        print(f"最大时间: {max_time:.4f}s")
        print(f"P95时间: {p95_time:.4f}s")

    @pytest.mark.performance
    def test_cache_performance(self, mock_bedrock_client, mock_s3_client):
        """测试缓存性能"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        prompt = "缓存性能测试"

        # 第一次生成（缓存未命中）
        start_time = time.perf_counter()
        service.call_image_generation(prompt)
        first_time = time.perf_counter() - start_time

        # 第二次生成（缓存命中）
        start_time = time.perf_counter()
        service.call_image_generation(prompt)
        cached_time = time.perf_counter() - start_time

        # 缓存查找应该非常快
        assert cached_time < self.performance_thresholds["cache_lookup_max_time"]

        # 缓存命中应该比首次生成快很多
        assert cached_time < first_time * 0.1

        print(f"缓存性能对比:")
        print(f"首次生成: {first_time:.4f}s")
        print(f"缓存命中: {cached_time:.4f}s")
        print(f"性能提升: {first_time/cached_time:.1f}x")

    @pytest.mark.performance
    def test_concurrent_generation_performance(self, mock_bedrock_client, mock_s3_client):
        """测试并发生成性能"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        def generate_single(index):
            prompt = f"并发性能测试 {index}"
            start_time = time.perf_counter()
            result = service.call_image_generation(prompt)
            end_time = time.perf_counter()
            return {
                'index': index,
                'time': end_time - start_time,
                'success': isinstance(result, bytes) and len(result) > 0
            }

        # 并发执行
        concurrent_count = 8
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(generate_single, i) for i in range(concurrent_count)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        total_time = time.time() - start_time

        # 性能验证
        assert total_time < self.performance_thresholds["concurrent_max_time"]
        assert len(results) == concurrent_count
        assert all(r['success'] for r in results)

        # 统计分析
        individual_times = [r['time'] for r in results]
        avg_individual_time = statistics.mean(individual_times)

        print(f"并发性能统计:")
        print(f"总时间: {total_time:.2f}s")
        print(f"平均单次时间: {avg_individual_time:.4f}s")
        print(f"并发效率: {(avg_individual_time * concurrent_count) / total_time:.1f}x")

    @pytest.mark.performance
    def test_memory_usage_optimization(self, mock_bedrock_client, mock_s3_client):
        """测试内存使用优化"""
        import psutil
        import gc

        process = psutil.Process()

        # 记录初始内存使用
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        # 生成大量图片
        for i in range(50):
            prompt = f"内存测试 {i}"
            service.call_image_generation(prompt)

            # 每10次检查内存
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory

                # 内存增长应该控制在合理范围
                assert memory_increase < 200  # 不超过200MB

        # 清理缓存
        service.clear_cache()
        gc.collect()

        # 检查内存释放
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_after_cleanup = final_memory - initial_memory

        print(f"内存使用统计:")
        print(f"初始内存: {initial_memory:.1f}MB")
        print(f"最终内存: {final_memory:.1f}MB")
        print(f"净增长: {memory_after_cleanup:.1f}MB")


class TestStressTesting:
    """压力测试"""

    @pytest.mark.stress
    def test_high_volume_generation(self, mock_bedrock_client, mock_s3_client):
        """测试高容量图片生成"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        # 大批量生成测试
        batch_size = 100
        success_count = 0
        error_count = 0

        start_time = time.time()

        for i in range(batch_size):
            try:
                prompt = f"压力测试批次 {i}"
                result = service.call_image_generation(prompt)
                if isinstance(result, bytes) and len(result) > 0:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                print(f"第{i}次生成失败: {str(e)}")

        total_time = time.time() - start_time

        # 验证压力测试结果
        success_rate = success_count / batch_size
        assert success_rate >= 0.95  # 95%成功率
        assert total_time < 120  # 2分钟内完成

        print(f"压力测试结果:")
        print(f"总数: {batch_size}")
        print(f"成功: {success_count}")
        print(f"失败: {error_count}")
        print(f"成功率: {success_rate:.2%}")
        print(f"总时间: {total_time:.1f}s")
        print(f"平均每次: {total_time/batch_size:.3f}s")

    @pytest.mark.stress
    def test_memory_stress(self, mock_bedrock_client, mock_s3_client):
        """测试内存压力"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        # 生成大量不同的图片以测试内存管理
        large_batch = 200

        for i in range(large_batch):
            # 创建不同的提示词以避免缓存
            prompt = f"内存压力测试 {i} {time.time()}"

            try:
                result = service.call_image_generation(prompt)
                assert isinstance(result, bytes)

                # 周期性清理缓存
                if i % 50 == 0:
                    service.clear_cache()

            except Exception as e:
                pytest.fail(f"内存压力测试在第{i}次失败: {str(e)}")

    @pytest.mark.stress
    def test_concurrent_stress(self, mock_bedrock_client, mock_s3_client):
        """测试并发压力"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        def stress_worker(worker_id, iterations):
            results = []
            for i in range(iterations):
                try:
                    prompt = f"并发压力测试 Worker{worker_id} Iter{i}"
                    result = service.call_image_generation(prompt)
                    results.append(True if isinstance(result, bytes) else False)
                except Exception as e:
                    results.append(False)
                    print(f"Worker {worker_id} Iteration {i} 失败: {str(e)}")
            return results

        # 启动多个工作线程
        workers = 10
        iterations_per_worker = 20

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(stress_worker, worker_id, iterations_per_worker)
                for worker_id in range(workers)
            ]

            all_results = []
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())

        total_time = time.time() - start_time

        # 分析结果
        total_operations = workers * iterations_per_worker
        successful_operations = sum(all_results)
        success_rate = successful_operations / total_operations

        # 验证并发压力测试
        assert success_rate >= 0.90  # 90%成功率
        assert total_time < 60  # 1分钟内完成

        print(f"并发压力测试结果:")
        print(f"工作线程: {workers}")
        print(f"每线程迭代: {iterations_per_worker}")
        print(f"总操作数: {total_operations}")
        print(f"成功操作: {successful_operations}")
        print(f"成功率: {success_rate:.2%}")
        print(f"总时间: {total_time:.1f}s")
        print(f"吞吐量: {total_operations/total_time:.1f} ops/s")


class TestErrorRecoveryAndResilience:
    """错误恢复和弹性测试"""

    def test_service_degradation_graceful_handling(self, mock_s3_client):
        """测试服务降级的优雅处理"""
        # 创建逐步失败的客户端
        call_count = 0

        def failing_invoke_model(**kwargs):
            nonlocal call_count
            call_count += 1

            # 前3次调用失败，第4次成功
            if call_count <= 3:
                raise ClientError(
                    {'Error': {'Code': 'ThrottlingException', 'Message': '服务忙'}},
                    'InvokeModel'
                )
            else:
                # 成功响应
                mock_response = Mock()
                mock_response.read.return_value = json.dumps({
                    "images": ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hRqYEAAAAABJRU5ErkJggg=="]
                }).encode()
                return {'body': mock_response}

        mock_client = Mock()
        mock_client.invoke_model.side_effect = failing_invoke_model

        service = ImageProcessingService(
            bedrock_client=mock_client,
            s3_client=mock_s3_client
        )

        # 测试重试机制
        with patch('time.sleep'):  # 跳过实际sleep
            result = service.call_image_generation("恢复测试")

        # 应该最终成功
        assert isinstance(result, bytes)
        assert call_count >= 3  # 验证重试发生

    def test_partial_failure_recovery(self, mock_bedrock_client, mock_s3_client):
        """测试部分失败的恢复"""
        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client,
            enable_caching=True
        )

        # 模拟部分操作成功，部分失败的场景
        success_prompts = ["成功1", "成功2", "成功3"]
        mixed_results = []

        for prompt in success_prompts:
            try:
                result = service.call_image_generation(prompt)
                mixed_results.append({
                    'prompt': prompt,
                    'success': True,
                    'result': result
                })
            except Exception as e:
                mixed_results.append({
                    'prompt': prompt,
                    'success': False,
                    'error': str(e)
                })

        # 验证部分成功
        successful_results = [r for r in mixed_results if r['success']]
        assert len(successful_results) >= 1  # 至少有一个成功

    def test_configuration_error_handling(self):
        """测试配置错误处理"""
        # 测试无效的Bedrock客户端
        invalid_client = None

        service = ImageProcessingService(bedrock_client=invalid_client, enable_caching=False)

        # 应该创建默认客户端
        assert service.bedrock_client is not None

    def test_data_corruption_handling(self, mock_bedrock_client, mock_s3_client):
        """测试数据损坏处理"""
        # 模拟返回损坏数据的客户端
        mock_bedrock_client.invoke_model.return_value = {
            'body': Mock(read=Mock(return_value=b'invalid json'))
        }

        service = ImageProcessingService(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client
        )

        # 应该处理损坏数据并回退到占位图
        result = service.call_image_generation("数据损坏测试")
        assert isinstance(result, bytes)
        assert service.validate_image_format(result, 'PNG')  # 占位图


if __name__ == "__main__":
    # 运行测试时的配置
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--strict-markers",
        "-m", "not (stress or performance)"  # 默认跳过压力和性能测试
    ])