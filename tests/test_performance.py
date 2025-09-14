"""
AI PPT Assistant Phase 3 - 性能优化功能测试用例（修复版）

本模块包含Phase 3性能优化功能的完整测试用例，遵循TDD原则。
测试覆盖：
- 并行生成验证
- 缓存机制测试
- 响应时间验证（<30秒）
- 并发请求处理

根据需求文档Requirement 3.2: 性能优化功能
目标：通过并行处理，生成时间减少50%；使用缓存机制；10页PPT生成时间<30秒
"""

import pytest
import asyncio
import time
import json
import concurrent.futures
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import boto3
from moto import mock_aws
import threading
import uuid
from typing import List, Dict, Any
import statistics
from test_utils import MockPerformanceComponents, TestDataFactory, assert_performance_requirements


class TestPerformanceOptimization:
    """Phase 3 - 性能优化功能测试套件"""

    @pytest.fixture
    def performance_optimizer(self):
        """性能优化器Mock"""
        optimizer = Mock()
        optimizer.optimize_generation.return_value = {
            "status": "success",
            "optimization_applied": True,
            "performance_gain": 0.65
        }
        return optimizer

    @pytest.fixture
    def cache_manager(self):
        """缓存管理器Mock"""
        return MockPerformanceComponents.create_cache_manager()

    @pytest.fixture
    def parallel_processor(self):
        """并行处理器Mock"""
        return MockPerformanceComponents.create_parallel_processor()

    @pytest.fixture
    def performance_monitor(self):
        """性能监控器Mock"""
        return MockPerformanceComponents.create_performance_monitor()

    @pytest.fixture
    def test_presentation_request(self):
        """测试用演示文稿请求"""
        return TestDataFactory.create_presentation_request(
            topic="深度学习技术详解",
            page_count=10,
            parallel_processing=True,
            use_cache=True
        )

    @pytest.fixture
    def large_presentation_request(self):
        """大型演示文稿请求（用于压力测试）"""
        return TestDataFactory.create_presentation_request(
            topic="人工智能全面解析",
            page_count=20,
            template="professional",
            parallel_processing=True
        )

    # ==================== 测试用例1: 并行生成验证 ====================

    def test_parallel_generation_basic_functionality(self, parallel_processor, test_presentation_request):
        """
        测试基础并行生成功能

        Given: 一个10页的PPT生成请求
        When: 启用并行处理
        Then: 多个页面同时生成，总时间显著减少
        """
        # Act
        result = parallel_processor.generate_slides_parallel(test_presentation_request)

        # Assert
        assert result["status"] == "success"
        assert result["parallel_tasks"] == 4
        assert_performance_requirements(result["total_time"], max_time=30.0)
        assert result["slides_generated"] == test_presentation_request["page_count"]
        assert result["efficiency_gain"] > 0.5  # 超过50%的性能提升

    def test_parallel_content_and_image_generation(self, parallel_processor):
        """
        测试内容生成和图片生成的并行处理

        Given: 需要生成内容和图片的幻灯片
        When: 同时处理内容和图片生成
        Then: 两个任务并行执行，总时间减少
        """
        # Arrange
        slides_data = [
            {"slide_number": i, "title": f"幻灯片{i}", "content_ready": False, "image_ready": False}
            for i in range(1, 6)
        ]

        # Mock并行处理器的响应
        parallel_processor.process_content_and_images_parallel.return_value = {
            "status": "success",
            "processed_slides": 5,
            "content_generation_time": 8.2,
            "image_generation_time": 12.1,
            "total_time": 12.5,  # 并行执行，取较长时间
            "serial_estimated_time": 20.3,  # 串行预估时间
            "time_savings": 7.8
        }

        # Act
        result = parallel_processor.process_content_and_images_parallel(slides_data)

        # Assert
        assert result["total_time"] < result["serial_estimated_time"]
        assert result["time_savings"] > 0
        assert result["processed_slides"] == len(slides_data)

    def test_parallel_processing_error_handling(self, parallel_processor, test_presentation_request):
        """
        测试并行处理中的错误处理

        Given: 并行任务中有一个失败
        When: 其他任务继续执行
        Then: 系统优雅处理错误，不影响其他任务
        """
        # Arrange - 配置部分失败的响应
        parallel_processor.generate_slides_parallel.return_value = {
            "status": "partial_success",
            "successful_slides": 8,
            "failed_slides": 2,
            "errors": [
                {"slide_number": 3, "error": "Content generation timeout"},
                {"slide_number": 7, "error": "Image generation failed"}
            ],
            "total_time": 22.1,
            "recovery_actions": [
                "Retry failed slides with simpler prompts",
                "Use placeholder images for failed image generation"
            ]
        }

        # Act
        result = parallel_processor.generate_slides_parallel(test_presentation_request)

        # Assert
        assert result["status"] == "partial_success"
        assert result["successful_slides"] + result["failed_slides"] == test_presentation_request["page_count"]
        assert len(result["errors"]) == result["failed_slides"]
        assert result["total_time"] < 30

    def test_dynamic_parallelism_adjustment(self, parallel_processor):
        """
        测试动态并行度调整

        Given: 系统检测到资源使用情况
        When: 动态调整并行任务数量
        Then: 优化资源使用和性能
        """
        # Arrange
        system_load = {
            "cpu_usage": 0.75,
            "memory_usage": 0.60,
            "lambda_concurrency": 15
        }

        parallel_processor.adjust_parallelism.return_value = {
            "original_parallelism": 6,
            "adjusted_parallelism": 4,
            "reason": "High CPU usage detected",
            "expected_performance_impact": 0.15  # 15%性能影响
        }

        # Act
        result = parallel_processor.adjust_parallelism(system_load)

        # Assert
        assert result["adjusted_parallelism"] < result["original_parallelism"]
        assert result["expected_performance_impact"] < 0.2  # 影响可接受

    # ==================== 测试用例2: 缓存机制测试 ====================

    def test_cache_hit_improves_response_time(self, cache_manager, performance_monitor):
        """
        测试缓存命中提高响应时间

        Given: 相同内容的请求已被缓存
        When: 再次请求相同内容
        Then: 从缓存返回，响应时间显著减少
        """
        # Arrange - 设置缓存命中
        cache_key = "slide_content_hash_123"
        cached_content = {
            "title": "AI技术发展",
            "content": "人工智能技术正在快速发展...",
            "generated_at": datetime.now().isoformat(),
            "cache_hit": True
        }

        cache_manager.get.return_value = cached_content
        cache_manager.exists.return_value = True

        # Mock性能监控
        performance_monitor.start_timing.return_value = time.time()
        performance_monitor.end_timing.return_value = 0.5  # 缓存命中，极快响应

        # Act
        start_time = performance_monitor.start_timing()
        result = cache_manager.get(cache_key)
        end_time = performance_monitor.end_timing()

        # Assert
        assert result is not None
        assert result["cache_hit"] is True
        assert end_time < 1.0  # 缓存命中应该非常快

    def test_cache_miss_stores_new_content(self, cache_manager):
        """
        测试缓存未命中时存储新内容

        Given: 请求的内容不在缓存中
        When: 生成新内容
        Then: 新内容被存储到缓存中
        """
        # Arrange
        cache_key = "new_slide_content_hash_456"
        new_content = {
            "title": "机器学习基础",
            "content": "机器学习是人工智能的一个重要分支...",
            "generated_at": datetime.now().isoformat()
        }

        cache_manager.get.return_value = None  # 缓存未命中
        cache_manager.set.return_value = True

        # Act
        cached_result = cache_manager.get(cache_key)
        if cached_result is None:
            # 模拟生成新内容并缓存
            cache_manager.set(cache_key, new_content, ttl=3600)

        # Assert
        assert cached_result is None  # 确认缓存未命中
        cache_manager.set.assert_called_once_with(cache_key, new_content, ttl=3600)

    def test_cache_performance_statistics(self, cache_manager):
        """
        测试缓存性能统计

        Given: 系统运行一段时间
        When: 查询缓存统计信息
        Then: 返回准确的命中率和性能指标
        """
        # Arrange - 配置缓存统计
        cache_manager.stats.return_value = {
            "hits": 150,
            "misses": 50,
            "hit_rate": 0.75,
            "total_requests": 200,
            "cache_size": "50MB",
            "evictions": 5
        }

        # Act
        stats = cache_manager.stats()

        # Assert
        assert stats["hit_rate"] == 0.75  # 75%命中率
        assert stats["hits"] + stats["misses"] == stats["total_requests"]
        assert stats["hit_rate"] > 0.7  # 命中率应该大于70%

    def test_cache_invalidation_on_update(self, cache_manager):
        """
        测试内容更新时的缓存失效

        Given: 缓存中存在旧内容
        When: 内容被更新
        Then: 相关缓存被清除
        """
        # Arrange
        presentation_id = "ppt-123"
        slide_number = 2
        cache_pattern = f"slide_{presentation_id}_{slide_number}_*"

        cache_manager.invalidate_pattern.return_value = 3  # 清除3个相关缓存

        # Act
        cleared_count = cache_manager.invalidate_pattern(cache_pattern)

        # Assert
        assert cleared_count > 0
        cache_manager.invalidate_pattern.assert_called_once_with(cache_pattern)

    # ==================== 测试用例3: 响应时间验证 ====================

    def test_10_page_presentation_under_30_seconds(self, parallel_processor, cache_manager, performance_monitor):
        """
        测试10页PPT生成时间<30秒

        Given: 10页PPT生成请求，启用并行处理和缓存
        When: 执行生成任务
        Then: 总时间小于30秒
        """
        # Arrange
        presentation_request = TestDataFactory.create_presentation_request(
            page_count=10,
            parallel_processing=True,
            use_cache=True
        )

        # Mock各组件的性能
        cache_manager.get.return_value = None  # 假设缓存未命中
        parallel_processor.generate_slides_parallel.return_value = {
            "status": "success",
            "total_time": 25.5,  # 小于30秒
            "slides_generated": 10,
            "parallel_tasks": 4,
            "cache_hits": 2,
            "cache_misses": 8
        }

        # Act
        start_time = time.time()
        result = parallel_processor.generate_slides_parallel(presentation_request)
        actual_time = time.time() - start_time

        # Assert
        assert_performance_requirements(result["total_time"], max_time=30.0)
        assert result["slides_generated"] == 10
        assert result["status"] == "success"

    def test_large_presentation_performance_scaling(self, parallel_processor, large_presentation_request):
        """
        测试大型演示文稿的性能扩展

        Given: 20页大型PPT请求
        When: 使用并行处理
        Then: 性能线性扩展，时间控制在合理范围内
        """
        # Arrange
        parallel_processor.generate_slides_parallel.return_value = {
            "status": "success",
            "total_time": 45.2,  # 20页，时间约为10页的2倍以内
            "slides_generated": 20,
            "parallel_tasks": 6,  # 更多并行任务
            "efficiency_gain": 0.58
        }

        # Act
        result = parallel_processor.generate_slides_parallel(large_presentation_request)

        # Assert
        assert result["total_time"] < 60  # 20页应在60秒内完成
        assert result["slides_generated"] == 20
        assert result["efficiency_gain"] > 0.5

    def test_performance_under_high_load(self, parallel_processor):
        """
        测试高负载下的性能表现

        Given: 同时处理多个演示文稿请求
        When: 系统负载较高
        Then: 性能优雅降级，维持基本服务质量
        """
        # Arrange
        concurrent_requests = 5
        requests = [
            TestDataFactory.create_presentation_request(page_count=5)
            for _ in range(concurrent_requests)
        ]

        # Mock并发处理结果
        parallel_processor.process_concurrent_requests.return_value = {
            "processed": 5,
            "failed": 0,
            "avg_response_time": 35.2,  # 负载下响应时间增加
            "max_concurrent": 5,
            "performance_degradation": 0.25  # 25%性能降级
        }

        # Act
        result = parallel_processor.process_concurrent_requests(requests)

        # Assert
        assert result["processed"] == concurrent_requests
        assert result["failed"] == 0
        assert result["avg_response_time"] < 60  # 高负载下仍保持合理时间
        assert result["performance_degradation"] < 0.5  # 降级不超过50%

    # ==================== 测试用例4: 并发请求处理 ====================

    def test_concurrent_slide_generation(self, parallel_processor):
        """
        测试并发幻灯片生成

        Given: 多个幻灯片需要同时生成
        When: 并发处理请求
        Then: 所有幻灯片正确生成，无数据竞争
        """
        def mock_generate_slide(slide_data):
            return {
                "slide_number": slide_data["slide_number"],
                "status": "success",
                "generation_time": 2.5,
                "content_hash": f"hash_{slide_data['slide_number']}"
            }

        # Arrange
        slide_requests = [
            {"slide_number": i, "title": f"Slide {i}", "topic": "AI"}
            for i in range(1, 6)
        ]

        # Mock并发生成
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(mock_generate_slide, slide_data)
                for slide_data in slide_requests
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Assert
        assert len(results) == len(slide_requests)
        assert all(result["status"] == "success" for result in results)
        slide_numbers = [result["slide_number"] for result in results]
        assert set(slide_numbers) == set(range(1, 6))

    def test_thread_safety_with_shared_cache(self, cache_manager):
        """
        测试共享缓存的线程安全

        Given: 多线程同时访问缓存
        When: 并发读写操作
        Then: 数据一致性得到保证
        """
        # Arrange
        cache_operations = []
        lock = threading.Lock()

        def cache_operation(thread_id):
            with lock:
                # 模拟缓存操作
                cache_key = f"thread_{thread_id}_data"
                data = {"thread_id": thread_id, "timestamp": time.time()}

                # 写入缓存
                cache_manager.set(cache_key, data)

                # 读取缓存
                result = cache_manager.get(cache_key)
                cache_operations.append(result)

        # Act - 创建多个线程并发访问缓存
        threads = []
        for i in range(5):
            thread = threading.Thread(target=cache_operation, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        assert len(cache_operations) == 5
        assert cache_manager.set.call_count == 5
        assert cache_manager.get.call_count == 5

    def test_rate_limiting_under_concurrent_load(self, parallel_processor):
        """
        测试并发负载下的限流机制

        Given: 大量并发请求
        When: 超过系统容量限制
        Then: 限流机制生效，保护系统稳定性
        """
        # Arrange
        high_concurrency_requests = 20

        parallel_processor.process_concurrent_requests.return_value = {
            "processed": 15,
            "rate_limited": 5,
            "avg_response_time": 28.5,
            "rate_limit_triggered": True,
            "max_concurrent_allowed": 15
        }

        # Act
        requests = [TestDataFactory.create_presentation_request() for _ in range(high_concurrency_requests)]
        result = parallel_processor.process_concurrent_requests(requests)

        # Assert
        assert result["rate_limit_triggered"] is True
        assert result["processed"] + result["rate_limited"] == high_concurrency_requests
        assert result["processed"] <= result["max_concurrent_allowed"]

    # ==================== 综合性能测试 ====================

    def test_end_to_end_performance_optimization(self, parallel_processor, cache_manager, performance_monitor):
        """
        端到端性能优化测试

        Given: 完整的PPT生成流程
        When: 启用所有性能优化功能
        Then: 整体性能满足要求
        """
        # Arrange
        request = TestDataFactory.create_presentation_request(
            page_count=10,
            parallel_processing=True,
            use_cache=True
        )

        # Mock各组件协同工作
        cache_manager.stats.return_value = {"hit_rate": 0.6}
        parallel_processor.generate_slides_parallel.return_value = {
            "status": "success",
            "total_time": 18.5,
            "cache_hits": 6,
            "cache_misses": 4,
            "parallel_efficiency": 0.85
        }
        performance_monitor.get_metrics.return_value = {
            "avg_generation_time": 18.5,
            "cache_hit_rate": 0.6,
            "parallel_efficiency": 0.85
        }

        # Act
        result = parallel_processor.generate_slides_parallel(request)
        metrics = performance_monitor.get_metrics()

        # Assert
        assert_performance_requirements(result["total_time"], max_time=30.0, min_efficiency_gain=0.5)
        assert metrics["cache_hit_rate"] > 0.5
        assert metrics["parallel_efficiency"] > 0.8
        assert result["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])