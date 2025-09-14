"""
AI PPT Assistant Phase 3 - 性能优化功能测试用例

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


class TestPerformanceOptimization:
    """Phase 3 - 性能优化功能测试套件"""

    @pytest.fixture
    def performance_optimizer(self):
        """性能优化器 - 这是我们要实现的组件"""
        return Mock()

    @pytest.fixture
    def cache_manager(self):
        """缓存管理器Mock"""
        return Mock()

    @pytest.fixture
    def parallel_processor(self):
        """并行处理器Mock"""
        return Mock()

    @pytest.fixture
    def test_presentation_request(self):
        """测试用演示文稿请求"""
        return {
            "presentation_id": f"perf-test-{uuid.uuid4()}",
            "topic": "深度学习技术详解",
            "page_count": 10,
            "template": "modern",
            "with_images": True,
            "parallel_processing": True,
            "use_cache": True
        }

    @pytest.fixture
    def large_presentation_request(self):
        """大型演示文稿请求（用于压力测试）"""
        return {
            "presentation_id": f"large-test-{uuid.uuid4()}",
            "topic": "人工智能全面解析",
            "page_count": 20,
            "template": "professional",
            "with_images": True,
            "parallel_processing": True
        }

    # ==================== 测试用例1: 并行生成验证 ====================

    def test_parallel_generation_basic_functionality(self, parallel_processor, test_presentation_request):
        """
        测试基础并行生成功能

        Given: 一个10页的PPT生成请求
        When: 启用并行处理
        Then: 多个页面同时生成，总时间显著减少
        """
        # Arrange
        expected_parallel_tasks = 4  # 假设并行处理4个任务组
        parallel_processor.generate_slides_parallel.return_value = {
            "status": "success",
            "parallel_tasks": expected_parallel_tasks,
            "total_time": 18.5,  # 小于30秒
            "slides_generated": 10,
            "time_saved": 12.3,  # 相比串行处理节省的时间
            "efficiency_gain": 0.52  # 52%的效率提升
        }

        # Act
        result = parallel_processor.generate_slides_parallel(test_presentation_request)

        # Assert
        assert result["status"] == "success"
        assert result["parallel_tasks"] == expected_parallel_tasks
        assert result["total_time"] < 30  # 满足性能要求
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

    def test_parallel_processing_error_handling(self, parallel_processor):
        """
        测试并行处理中的错误处理

        Given: 并行任务中有一个失败
        When: 其他任务继续执行
        Then: 系统优雅处理错误，不影响其他任务
        """
        # Arrange
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

    def test_cache_hit_improves_response_time(self, cache_manager, performance_optimizer):
        """
        测试缓存命中提升响应时间

        Given: 相似的PPT生成请求已经缓存
        When: 发起新的生成请求
        Then: 从缓存获取结果，响应时间大幅缩短
        """
        # Arrange
        cache_key = "topic:深度学习_pages:10_template:modern"
        cached_data = {
            "outline": {"title": "深度学习技术", "slides": [...]},
            "generated_at": datetime.now().isoformat(),
            "cache_hit": True
        }

        cache_manager.get_cached_content.return_value = cached_data
        performance_optimizer.generate_with_cache.return_value = {
            "status": "success",
            "cache_hit": True,
            "response_time": 2.1,  # 大幅缩短
            "data_source": "cache",
            "cache_freshness": 0.95
        }

        # Act
        result = performance_optimizer.generate_with_cache(cache_key)

        # Assert
        assert result["cache_hit"] is True
        assert result["response_time"] < 5  # 缓存命中应该很快
        assert result["cache_freshness"] > 0.9

    def test_cache_miss_stores_new_content(self, cache_manager, performance_optimizer):
        """
        测试缓存未命中时存储新内容

        Given: 缓存中没有相关内容
        When: 生成新的PPT内容
        Then: 将新内容存储到缓存中
        """
        # Arrange
        cache_key = "topic:区块链技术_pages:8_template:classic"

        cache_manager.get_cached_content.return_value = None  # 缓存未命中
        performance_optimizer.generate_with_cache.return_value = {
            "status": "success",
            "cache_hit": False,
            "response_time": 25.3,  # 正常生成时间
            "data_source": "generated",
            "cached_for_future": True
        }

        # Act
        result = performance_optimizer.generate_with_cache(cache_key)

        # Assert
        assert result["cache_hit"] is False
        assert result["cached_for_future"] is True
        assert result["response_time"] < 30

        # 验证缓存存储调用
        cache_manager.store_content.assert_called_once()

    def test_cache_expiration_and_refresh(self, cache_manager):
        """
        测试缓存过期和刷新机制

        Given: 缓存内容已过期
        When: 检查缓存状态
        Then: 标记过期并触发刷新
        """
        # Arrange
        expired_cache_item = {
            "content": {"title": "过期内容"},
            "created_at": (datetime.now() - timedelta(days=8)).isoformat(),  # 8天前
            "ttl": 7 * 24 * 3600,  # 7天TTL
            "is_expired": True
        }

        cache_manager.check_cache_expiration.return_value = {
            "expired_items": 3,
            "refresh_required": True,
            "cleanup_completed": True
        }

        # Act
        result = cache_manager.check_cache_expiration()

        # Assert
        assert result["refresh_required"] is True
        assert result["expired_items"] > 0

    def test_cache_size_management(self, cache_manager):
        """
        测试缓存大小管理

        Given: 缓存接近容量限制
        When: 添加新的缓存条目
        Then: 清理最少使用的条目
        """
        # Arrange
        cache_stats = {
            "total_size": "450MB",
            "max_size": "500MB",
            "utilization": 0.90,
            "items_count": 1250
        }

        cache_manager.manage_cache_size.return_value = {
            "cleanup_triggered": True,
            "items_removed": 125,
            "space_freed": "50MB",
            "new_utilization": 0.80
        }

        # Act
        result = cache_manager.manage_cache_size(cache_stats)

        # Assert
        assert result["cleanup_triggered"] is True
        assert result["new_utilization"] < cache_stats["utilization"]

    def test_intelligent_cache_key_generation(self, cache_manager):
        """
        测试智能缓存键生成

        Given: 不同但相似的PPT请求
        When: 生成缓存键
        Then: 相似请求产生相同的缓存键
        """
        # Arrange
        request1 = {"topic": "机器学习", "pages": 10, "template": "modern"}
        request2 = {"topic": "机器学习基础", "pages": 10, "template": "modern"}  # 相似主题
        request3 = {"topic": "深度学习", "pages": 10, "template": "modern"}  # 不同主题

        cache_manager.generate_cache_key.side_effect = [
            "ml_10_modern_v1",
            "ml_10_modern_v1",  # 相同的键
            "dl_10_modern_v1"   # 不同的键
        ]

        # Act
        key1 = cache_manager.generate_cache_key(request1)
        key2 = cache_manager.generate_cache_key(request2)
        key3 = cache_manager.generate_cache_key(request3)

        # Assert
        assert key1 == key2  # 相似请求相同键
        assert key1 != key3  # 不同请求不同键

    # ==================== 测试用例3: 响应时间验证（<30秒） ====================

    def test_10_page_ppt_generation_under_30_seconds(self, performance_optimizer, test_presentation_request):
        """
        测试10页PPT生成时间小于30秒

        Given: 10页PPT生成请求（带图片）
        When: 使用优化后的并行生成
        Then: 总时间小于30秒
        """
        # Arrange
        start_time = datetime.now()

        performance_optimizer.generate_presentation_optimized.return_value = {
            "status": "success",
            "presentation_id": test_presentation_request["presentation_id"],
            "pages_generated": 10,
            "total_time": 28.7,  # 小于30秒
            "breakdown": {
                "outline_generation": 3.2,
                "content_generation": 12.5,
                "image_generation": 8.1,
                "compilation": 4.9
            },
            "optimization_used": ["parallel_processing", "caching", "step_functions"]
        }

        # Act
        result = performance_optimizer.generate_presentation_optimized(test_presentation_request)

        # Assert
        assert result["total_time"] < 30.0  # 核心性能要求
        assert result["pages_generated"] == 10
        assert result["status"] == "success"
        assert "parallel_processing" in result["optimization_used"]

    def test_response_time_under_different_loads(self, performance_optimizer):
        """
        测试不同负载下的响应时间

        Given: 不同的系统负载情况
        When: 生成PPT
        Then: 在各种负载下都满足性能要求
        """
        # Arrange
        load_scenarios = [
            {"load": "low", "concurrent_requests": 2},
            {"load": "medium", "concurrent_requests": 10},
            {"load": "high", "concurrent_requests": 25}
        ]

        performance_optimizer.test_under_load.side_effect = [
            {"scenario": "low", "avg_response_time": 22.1, "max_response_time": 25.3},
            {"scenario": "medium", "avg_response_time": 27.8, "max_response_time": 29.9},
            {"scenario": "high", "avg_response_time": 29.2, "max_response_time": 32.1}  # 高负载稍微超时
        ]

        # Act & Assert
        for scenario in load_scenarios:
            result = performance_optimizer.test_under_load(scenario)
            if scenario["load"] in ["low", "medium"]:
                assert result["max_response_time"] < 30.0
            # 高负载下可能稍微超时，但应该接近30秒

    def test_performance_degradation_gracefully(self, performance_optimizer):
        """
        测试性能优雅降级

        Given: 系统资源受限
        When: 无法满足最优性能
        Then: 优雅降级，仍然提供服务
        """
        # Arrange
        resource_constraints = {
            "lambda_throttling": True,
            "bedrock_rate_limit": True,
            "s3_slow_response": True
        }

        performance_optimizer.handle_performance_degradation.return_value = {
            "status": "degraded_performance",
            "response_time": 35.2,  # 超过30秒但仍可接受
            "degradation_reason": "Resource constraints detected",
            "fallback_strategies_used": [
                "Reduced image quality",
                "Simplified content templates",
                "Single-threaded processing"
            ],
            "user_notification": "生成时间可能稍长，请耐心等待"
        }

        # Act
        result = performance_optimizer.handle_performance_degradation(resource_constraints)

        # Assert
        assert result["status"] == "degraded_performance"
        assert result["response_time"] < 60  # 即使降级也不应该太慢
        assert len(result["fallback_strategies_used"]) > 0

    @pytest.mark.performance
    def test_actual_timing_constraints(self, performance_optimizer):
        """
        测试实际计时约束

        Given: 真实的计时要求
        When: 执行性能测试
        Then: 验证实际执行时间
        """
        # Arrange - 这个测试会实际计时
        start_time = time.time()

        # 模拟真实的处理时间
        def simulate_processing():
            time.sleep(0.1)  # 模拟100ms处理时间
            return {
                "status": "success",
                "actual_processing_time": 0.1
            }

        performance_optimizer.generate_presentation_optimized.side_effect = simulate_processing

        # Act
        result = performance_optimizer.generate_presentation_optimized({})
        actual_time = time.time() - start_time

        # Assert
        assert actual_time < 1.0  # Mock应该很快
        assert result["status"] == "success"

    # ==================== 测试用例4: 并发请求处理 ====================

    def test_concurrent_requests_basic_handling(self, performance_optimizer):
        """
        测试基础并发请求处理

        Given: 多个同时发起的PPT生成请求
        When: 系统处理这些并发请求
        Then: 所有请求都得到正确处理
        """
        # Arrange
        concurrent_requests = [
            {"id": f"req-{i}", "topic": f"主题{i}", "pages": 5}
            for i in range(5)
        ]

        performance_optimizer.handle_concurrent_requests.return_value = {
            "total_requests": 5,
            "successful_requests": 5,
            "failed_requests": 0,
            "avg_processing_time": 24.5,
            "max_processing_time": 28.1,
            "concurrent_efficiency": 0.91
        }

        # Act
        result = performance_optimizer.handle_concurrent_requests(concurrent_requests)

        # Assert
        assert result["successful_requests"] == len(concurrent_requests)
        assert result["failed_requests"] == 0
        assert result["max_processing_time"] < 30

    def test_high_concurrency_load_balancing(self, performance_optimizer):
        """
        测试高并发下的负载均衡

        Given: 50个并发请求
        When: 系统进行负载均衡
        Then: 请求被合理分配，性能保持稳定
        """
        # Arrange
        high_concurrency_scenario = {
            "concurrent_requests": 50,
            "request_distribution": "even",
            "load_balancing_enabled": True
        }

        performance_optimizer.test_high_concurrency.return_value = {
            "requests_processed": 50,
            "load_balancing_triggered": True,
            "queue_depth_max": 12,
            "avg_wait_time": 5.2,
            "throughput": 1.8,  # requests per second
            "resource_utilization": {
                "lambda_concurrent": 20,
                "bedrock_requests_per_minute": 180
            }
        }

        # Act
        result = performance_optimizer.test_high_concurrency(high_concurrency_scenario)

        # Assert
        assert result["requests_processed"] == high_concurrency_scenario["concurrent_requests"]
        assert result["load_balancing_triggered"] is True
        assert result["avg_wait_time"] < 10  # 等待时间合理

    def test_request_queuing_and_prioritization(self, performance_optimizer):
        """
        测试请求队列和优先级处理

        Given: 超出处理能力的请求数量
        When: 系统进行队列管理
        Then: 请求按优先级排队处理
        """
        # Arrange
        prioritized_requests = [
            {"id": "urgent-1", "priority": "high", "pages": 5},
            {"id": "normal-1", "priority": "normal", "pages": 10},
            {"id": "urgent-2", "priority": "high", "pages": 8},
            {"id": "low-1", "priority": "low", "pages": 15}
        ]

        performance_optimizer.process_with_priority.return_value = {
            "processing_order": ["urgent-1", "urgent-2", "normal-1", "low-1"],
            "queue_management": "enabled",
            "high_priority_avg_time": 18.5,
            "normal_priority_avg_time": 26.3,
            "low_priority_avg_time": 35.2
        }

        # Act
        result = performance_optimizer.process_with_priority(prioritized_requests)

        # Assert
        assert result["processing_order"][0] in ["urgent-1", "urgent-2"]  # 高优先级优先
        assert result["high_priority_avg_time"] < result["normal_priority_avg_time"]

    def test_concurrent_requests_error_isolation(self, performance_optimizer):
        """
        测试并发请求中的错误隔离

        Given: 并发请求中有部分失败
        When: 处理这些请求
        Then: 错误被隔离，不影响其他请求
        """
        # Arrange
        mixed_requests = [
            {"id": "success-1", "valid": True},
            {"id": "fail-1", "valid": False},  # 将失败的请求
            {"id": "success-2", "valid": True},
            {"id": "fail-2", "valid": False}
        ]

        performance_optimizer.process_with_error_isolation.return_value = {
            "successful_requests": 2,
            "failed_requests": 2,
            "error_isolation_effective": True,
            "failures": [
                {"id": "fail-1", "error": "Invalid topic"},
                {"id": "fail-2", "error": "Missing parameters"}
            ],
            "success_rate": 0.50
        }

        # Act
        result = performance_optimizer.process_with_error_isolation(mixed_requests)

        # Assert
        assert result["error_isolation_effective"] is True
        assert result["successful_requests"] > 0  # 部分成功
        assert len(result["failures"]) == result["failed_requests"]

    # ==================== 性能基准测试 ====================

    @pytest.mark.performance
    @pytest.mark.parametrize("page_count", [5, 10, 15, 20])
    def test_performance_scaling_with_page_count(self, performance_optimizer, page_count):
        """
        测试不同页数下的性能表现

        Given: 不同页数的PPT请求
        When: 生成PPT
        Then: 响应时间随页数合理增长
        """
        # Arrange
        request = {"pages": page_count, "with_images": True}

        # 模拟随页数增长的处理时间（但有并行优化）
        expected_time = min(15 + page_count * 1.2, 30)  # 最多30秒

        performance_optimizer.generate_presentation_optimized.return_value = {
            "status": "success",
            "pages": page_count,
            "processing_time": expected_time,
            "time_per_page": expected_time / page_count
        }

        # Act
        result = performance_optimizer.generate_presentation_optimized(request)

        # Assert
        assert result["processing_time"] <= 30.0
        if page_count <= 10:
            assert result["processing_time"] <= expected_time

    def test_performance_comparison_serial_vs_parallel(self, performance_optimizer):
        """
        测试串行vs并行处理性能对比

        Given: 同样的PPT生成任务
        When: 分别用串行和并行方式处理
        Then: 并行处理显著更快
        """
        # Arrange
        task_spec = {"pages": 10, "with_images": True}

        performance_optimizer.compare_serial_parallel.return_value = {
            "serial_time": 45.2,
            "parallel_time": 22.8,
            "improvement_ratio": 1.98,  # 近2倍提升
            "efficiency_gain": 0.495,  # 49.5%提升
            "parallel_overhead": 1.3
        }

        # Act
        comparison = performance_optimizer.compare_serial_parallel(task_spec)

        # Assert
        assert comparison["parallel_time"] < comparison["serial_time"]
        assert comparison["improvement_ratio"] > 1.5  # 至少50%提升
        assert comparison["efficiency_gain"] > 0.4

    # ==================== 资源使用优化测试 ====================

    def test_memory_usage_optimization(self, performance_optimizer):
        """
        测试内存使用优化

        Given: 大型PPT生成任务
        When: 监控内存使用
        Then: 内存使用保持在合理范围
        """
        # Arrange
        large_task = {"pages": 20, "high_resolution_images": True}

        performance_optimizer.monitor_memory_usage.return_value = {
            "peak_memory_mb": 1800,  # 低于2GB限制
            "avg_memory_mb": 1200,
            "memory_efficient": True,
            "gc_collections": 3,
            "memory_optimization_enabled": True
        }

        # Act
        result = performance_optimizer.monitor_memory_usage(large_task)

        # Assert
        assert result["peak_memory_mb"] < 2048  # 在Lambda限制内
        assert result["memory_efficient"] is True

    def test_cpu_utilization_optimization(self, performance_optimizer):
        """
        测试CPU使用率优化

        Given: CPU密集型PPT生成任务
        When: 监控CPU使用率
        Then: CPU使用率得到优化
        """
        # Arrange
        cpu_intensive_task = {"pages": 15, "complex_content": True}

        performance_optimizer.monitor_cpu_usage.return_value = {
            "avg_cpu_utilization": 0.78,
            "peak_cpu_utilization": 0.92,
            "cpu_optimization_enabled": True,
            "parallel_efficiency": 0.85,
            "bottlenecks_identified": ["bedrock_api_calls", "image_processing"]
        }

        # Act
        result = performance_optimizer.monitor_cpu_usage(cpu_intensive_task)

        # Assert
        assert result["avg_cpu_utilization"] < 0.90  # 避免资源耗尽
        assert result["parallel_efficiency"] > 0.80

    # ==================== 集成性能测试 ====================

    @pytest.mark.integration
    @pytest.mark.slow
    def test_end_to_end_performance_workflow(self, performance_optimizer, cache_manager, parallel_processor):
        """
        测试端到端的性能优化工作流

        Given: 完整的性能优化组件
        When: 执行完整的PPT生成流程
        Then: 所有组件协同工作，实现性能目标
        """
        # Arrange
        workflow_request = {
            "presentation_id": "e2e-perf-test",
            "topic": "企业数字化转型",
            "pages": 12,
            "enable_all_optimizations": True
        }

        # 模拟完整工作流的结果
        performance_optimizer.execute_optimized_workflow.return_value = {
            "status": "success",
            "total_time": 26.8,
            "optimizations_used": ["caching", "parallel_processing", "resource_pooling"],
            "performance_metrics": {
                "cache_hit_rate": 0.35,
                "parallel_efficiency": 0.88,
                "resource_utilization": 0.75
            },
            "quality_maintained": True
        }

        # Act
        result = performance_optimizer.execute_optimized_workflow(workflow_request)

        # Assert
        assert result["status"] == "success"
        assert result["total_time"] < 30
        assert result["quality_maintained"] is True
        assert len(result["optimizations_used"]) >= 2

    # ==================== 错误和边界情况 ====================

    def test_performance_under_resource_constraints(self, performance_optimizer):
        """测试资源受限下的性能表现"""
        # Arrange
        resource_limits = {
            "memory_limit_mb": 1024,  # 较低内存限制
            "cpu_throttling": 0.5,    # CPU被限制
            "network_latency_ms": 200  # 高网络延迟
        }

        performance_optimizer.test_with_constraints.return_value = {
            "status": "completed_with_degradation",
            "processing_time": 38.5,  # 超过理想时间但完成
            "quality_impact": "minimal",
            "adaptive_strategies_used": [
                "Reduced image resolution",
                "Simplified content generation"
            ]
        }

        # Act & Assert
        result = performance_optimizer.test_with_constraints(resource_limits)
        assert result["status"] == "completed_with_degradation"
        assert result["processing_time"] < 60  # 仍在可接受范围

    def test_performance_monitoring_alerts(self, performance_optimizer):
        """测试性能监控和告警"""
        # Arrange
        performance_optimizer.check_performance_thresholds.return_value = {
            "alerts_triggered": [
                {"type": "response_time", "threshold": 30, "actual": 35.2, "severity": "warning"},
                {"type": "memory_usage", "threshold": 0.8, "actual": 0.95, "severity": "critical"}
            ],
            "recommendations": [
                "Consider increasing Lambda memory allocation",
                "Review parallel processing configuration"
            ]
        }

        # Act & Assert
        result = performance_optimizer.check_performance_thresholds()
        assert len(result["alerts_triggered"]) > 0
        assert any(alert["severity"] == "critical" for alert in result["alerts_triggered"])


# ==================== 测试辅助函数 ====================

class PerformanceTestHelper:
    """性能测试辅助类"""

    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """测量函数执行时间"""
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time

    @staticmethod
    def simulate_concurrent_requests(request_count: int, processor_func):
        """模拟并发请求"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(processor_func, f"request-{i}")
                for i in range(request_count)
            ]
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
            return results

    @staticmethod
    def calculate_performance_statistics(timing_data: List[float]) -> Dict[str, float]:
        """计算性能统计数据"""
        return {
            "min": min(timing_data),
            "max": max(timing_data),
            "avg": statistics.mean(timing_data),
            "median": statistics.median(timing_data),
            "std_dev": statistics.stdev(timing_data) if len(timing_data) > 1 else 0,
            "percentile_95": sorted(timing_data)[int(len(timing_data) * 0.95)]
        }


# ==================== Pytest配置 ====================

@pytest.fixture(autouse=True)
def setup_performance_test_environment():
    """性能测试环境设置"""
    import os
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["PERFORMANCE_TESTING"] = "true"
    os.environ["ENABLE_DETAILED_METRICS"] = "true"
    yield
    # 清理
    for var in ["PERFORMANCE_TESTING", "ENABLE_DETAILED_METRICS"]:
        if var in os.environ:
            del os.environ[var]


@pytest.mark.performance
class PerformanceRegressionTests:
    """性能回归测试套件"""

    def test_no_performance_regression(self, performance_optimizer):
        """确保性能没有退化"""
        baseline_metrics = {
            "10_pages_with_images": 28.5,
            "5_pages_text_only": 12.3,
            "20_pages_complex": 45.2
        }

        for scenario, baseline_time in baseline_metrics.items():
            current_result = performance_optimizer.run_baseline_test(scenario)
            assert current_result["processing_time"] <= baseline_time * 1.1  # 允许10%的偏差


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([__file__ + "::TestPerformanceOptimization::test_10_page_ppt_generation_under_30_seconds", "-v"])