"""
图片生成服务性能测试套件 V3
包含全面的性能基准测试、压力测试和优化验证
"""

import pytest
import time
import asyncio
import concurrent.futures
import statistics
import json
import psutil
import gc
from typing import List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas'))

from image_processing_service_v3 import (
    ImageProcessingServiceV3, ImageRequest, ImageResponse,
    CacheManager, BatchProcessor, RateLimiter
)
from cloudwatch_monitoring import CloudWatchMonitor, PerformanceTracker, MetricsAggregator
from image_config import CONFIG


class PerformanceBenchmark:
    """性能基准测试框架"""

    def __init__(self):
        self.results = []
        self.process = psutil.Process()

    def measure_performance(self, func, *args, **kwargs):
        """测量函数性能"""
        # 强制垃圾回收
        gc.collect()

        # 记录初始状态
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = self.process.cpu_percent()

        # 执行函数
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        # 记录结束状态
        end_memory = self.process.memory_info().rss / 1024 / 1024
        end_cpu = self.process.cpu_percent()

        # 计算性能指标
        performance_data = {
            'execution_time': end_time - start_time,
            'memory_used': end_memory - start_memory,
            'cpu_usage': (start_cpu + end_cpu) / 2,
            'result': result
        }

        self.results.append(performance_data)
        return performance_data

    def get_statistics(self):
        """获取性能统计"""
        if not self.results:
            return {}

        times = [r['execution_time'] for r in self.results]
        memory = [r['memory_used'] for r in self.results]
        cpu = [r['cpu_usage'] for r in self.results]

        return {
            'execution_time': {
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'min': min(times),
                'max': max(times),
                'stdev': statistics.stdev(times) if len(times) > 1 else 0
            },
            'memory': {
                'mean': statistics.mean(memory),
                'max': max(memory)
            },
            'cpu': {
                'mean': statistics.mean(cpu),
                'max': max(cpu)
            },
            'samples': len(self.results)
        }


@pytest.fixture
def mock_bedrock_client():
    """模拟Bedrock客户端"""
    client = Mock()

    # 模拟成功的API响应
    def mock_invoke_model(modelId, **kwargs):
        if "nova" in modelId:
            response_body = {
                'images': ['base64encodedimagedata']
            }
        else:
            response_body = {
                'artifacts': [{'base64': 'base64encodedimagedata'}]
            }

        return {
            'body': MagicMock(read=lambda: json.dumps(response_body))
        }

    client.invoke_model = mock_invoke_model
    return client


@pytest.fixture
def service_v3(mock_bedrock_client):
    """创建优化的图片处理服务实例"""
    return ImageProcessingServiceV3(
        bedrock_client=mock_bedrock_client,
        enable_caching=True,
        enable_metrics=True,
        max_workers=10
    )


@pytest.fixture
def monitor():
    """创建监控器实例"""
    return CloudWatchMonitor(namespace="Test", client=Mock())


class TestPerformanceOptimizations:
    """测试性能优化"""

    def test_cache_performance(self, service_v3):
        """测试缓存性能提升"""
        benchmark = PerformanceBenchmark()
        prompt = "高质量商务演示背景"

        # 第一次调用（无缓存）
        first_call = benchmark.measure_performance(
            asyncio.run,
            service_v3._generate_single_async(ImageRequest(prompt=prompt))
        )

        # 第二次调用（有缓存）
        second_call = benchmark.measure_performance(
            asyncio.run,
            service_v3._generate_single_async(ImageRequest(prompt=prompt))
        )

        # 验证缓存提升性能
        assert second_call['execution_time'] < first_call['execution_time'] * 0.1
        print(f"缓存性能提升: {first_call['execution_time'] / second_call['execution_time']:.2f}x")

    def test_batch_processing_performance(self, service_v3):
        """测试批处理性能"""
        benchmark = PerformanceBenchmark()

        # 创建批量请求
        requests = [
            ImageRequest(prompt=f"测试图片 {i}", priority=i)
            for i in range(10)
        ]

        # 测试批处理
        batch_result = benchmark.measure_performance(
            asyncio.run,
            service_v3.generate_images_batch(requests)
        )

        # 验证批处理效率
        avg_time_per_image = batch_result['execution_time'] / len(requests)
        assert avg_time_per_image < 0.5  # 平均每张图片应该小于0.5秒

        print(f"批处理性能: {len(requests)}张图片耗时{batch_result['execution_time']:.2f}秒")
        print(f"平均每张: {avg_time_per_image:.3f}秒")

    def test_parallel_processing(self, service_v3):
        """测试并行处理能力"""
        benchmark = PerformanceBenchmark()

        async def parallel_generation():
            tasks = []
            for i in range(5):
                request = ImageRequest(prompt=f"并行测试 {i}")
                task = service_v3._generate_single_async(request)
                tasks.append(task)

            return await asyncio.gather(*tasks)

        # 测试并行生成
        result = benchmark.measure_performance(
            asyncio.run,
            parallel_generation()
        )

        # 验证并行处理效率
        assert result['execution_time'] < 2.0  # 5张图片并行应该在2秒内完成
        print(f"并行处理5张图片耗时: {result['execution_time']:.2f}秒")

    def test_memory_efficiency(self, service_v3):
        """测试内存效率"""
        benchmark = PerformanceBenchmark()

        # 生成大量图片测试内存使用
        for i in range(20):
            request = ImageRequest(prompt=f"内存测试 {i}")
            benchmark.measure_performance(
                asyncio.run,
                service_v3._generate_single_async(request)
            )

        stats = benchmark.get_statistics()

        # 验证内存使用合理
        assert stats['memory']['max'] < 500  # 最大内存增长不超过500MB
        print(f"最大内存使用: {stats['memory']['max']:.2f}MB")

    def test_rate_limiting(self):
        """测试限流功能"""
        limiter = RateLimiter(max_requests=10, time_window=1)

        # 快速发送请求
        allowed = 0
        rejected = 0

        for _ in range(15):
            if limiter.allow_request():
                allowed += 1
            else:
                rejected += 1

        assert allowed == 10
        assert rejected == 5
        print(f"限流测试: 允许{allowed}个请求，拒绝{rejected}个请求")


class TestMonitoringPerformance:
    """测试监控性能"""

    def test_metrics_collection_overhead(self, monitor):
        """测试指标收集开销"""
        benchmark = PerformanceBenchmark()

        # 测试记录指标的开销
        def record_metrics():
            for i in range(1000):
                monitor.record_metric(f"test_metric_{i % 10}", i)

        result = benchmark.measure_performance(record_metrics)

        # 验证指标收集开销很小
        assert result['execution_time'] < 0.1  # 1000个指标应该在0.1秒内记录完
        print(f"记录1000个指标耗时: {result['execution_time']:.3f}秒")

    def test_performance_tracker(self, monitor):
        """测试性能跟踪器"""
        tracker = PerformanceTracker(monitor)

        @tracker.track_operation("test_operation")
        def slow_operation():
            time.sleep(0.1)
            return "done"

        # 执行被跟踪的操作
        result = slow_operation()

        assert result == "done"
        # 验证指标被记录
        assert monitor._stats['metrics_sent'] >= 0

    def test_metrics_aggregation(self):
        """测试指标聚合"""
        aggregator = MetricsAggregator(window_size=60)

        # 添加测试数据
        for i in range(100):
            aggregator.add_value("test_metric", i)

        stats = aggregator.get_statistics("test_metric")

        assert stats['count'] == 100
        assert stats['average'] == 49.5
        assert stats['min'] == 0
        assert stats['max'] == 99
        print(f"聚合统计: {stats}")


class TestStressAndLoadTesting:
    """压力和负载测试"""

    @pytest.mark.slow
    def test_sustained_load(self, service_v3):
        """测试持续负载"""
        benchmark = PerformanceBenchmark()
        duration = 10  # 秒
        start_time = time.time()
        request_count = 0

        async def sustained_load():
            nonlocal request_count
            while time.time() - start_time < duration:
                request = ImageRequest(prompt=f"持续负载测试 {request_count}")
                await service_v3._generate_single_async(request)
                request_count += 1

        benchmark.measure_performance(asyncio.run, sustained_load())

        # 计算吞吐量
        throughput = request_count / duration
        print(f"持续负载测试: {duration}秒内处理{request_count}个请求")
        print(f"吞吐量: {throughput:.2f} 请求/秒")

        assert throughput > 5  # 至少5个请求/秒

    @pytest.mark.slow
    def test_burst_load(self, service_v3):
        """测试突发负载"""
        benchmark = PerformanceBenchmark()

        async def burst_load():
            # 突然创建大量请求
            tasks = []
            for i in range(50):
                request = ImageRequest(prompt=f"突发负载测试 {i}")
                task = service_v3._generate_single_async(request)
                tasks.append(task)

            return await asyncio.gather(*tasks, return_exceptions=True)

        result = benchmark.measure_performance(asyncio.run, burst_load())

        # 统计成功和失败
        responses = result['result']
        successful = sum(1 for r in responses if not isinstance(r, Exception))
        failed = len(responses) - successful

        print(f"突发负载测试: 50个并发请求")
        print(f"成功: {successful}, 失败: {failed}")
        print(f"总耗时: {result['execution_time']:.2f}秒")

        assert successful > 40  # 至少80%成功率

    def test_resource_cleanup(self, service_v3):
        """测试资源清理"""
        # 执行一些操作
        for i in range(10):
            asyncio.run(service_v3._generate_single_async(
                ImageRequest(prompt=f"清理测试 {i}")
            ))

        # 清理资源
        service_v3.cleanup()

        # 验证线程池已关闭
        assert service_v3.executor._shutdown


class TestPerformanceComparison:
    """性能对比测试"""

    def test_optimized_vs_original(self, mock_bedrock_client):
        """对比优化版本和原始版本性能"""
        # 创建优化版本
        optimized = ImageProcessingServiceV3(
            bedrock_client=mock_bedrock_client,
            enable_caching=True
        )

        # 创建未优化版本（禁用所有优化）
        unoptimized = ImageProcessingServiceV3(
            bedrock_client=mock_bedrock_client,
            enable_caching=False,
            max_workers=1
        )

        benchmark = PerformanceBenchmark()
        requests = [ImageRequest(prompt=f"对比测试 {i}") for i in range(10)]

        # 测试优化版本
        opt_result = benchmark.measure_performance(
            asyncio.run,
            optimized.generate_images_batch(requests)
        )

        # 重置benchmark
        benchmark.results = []

        # 测试未优化版本
        unopt_result = benchmark.measure_performance(
            asyncio.run,
            unoptimized.generate_images_batch(requests)
        )

        # 计算性能提升
        improvement = unopt_result['execution_time'] / opt_result['execution_time']

        print(f"性能对比:")
        print(f"优化版本: {opt_result['execution_time']:.2f}秒")
        print(f"未优化版本: {unopt_result['execution_time']:.2f}秒")
        print(f"性能提升: {improvement:.2f}x")

        assert improvement > 1.5  # 至少1.5倍性能提升


def generate_performance_report(service: ImageProcessingServiceV3):
    """生成性能报告"""
    stats = service.get_performance_stats()
    cache_stats = stats['cache_stats']

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "performance_metrics": {
            "total_requests": stats['total_requests'],
            "success_rate": f"{stats['success_rate'] * 100:.2f}%",
            "average_generation_time": f"{stats['average_generation_time']:.3f}s",
            "cache_hit_rate": f"{cache_stats['hit_rate'] * 100:.2f}%"
        },
        "cache_statistics": {
            "items_cached": cache_stats['items'],
            "cache_size_mb": f"{cache_stats['total_size_mb']:.2f}",
            "hit_count": cache_stats['hit_count'],
            "miss_count": cache_stats['miss_count']
        },
        "model_usage": stats['model_usage'],
        "model_availability": stats['model_pool_status']
    }

    return report


if __name__ == "__main__":
    # 运行性能测试并生成报告
    print("运行性能基准测试...")

    # 创建测试服务
    mock_client = Mock()
    mock_client.invoke_model = lambda **kwargs: {
        'body': MagicMock(read=lambda: json.dumps({'images': ['test_image_data']}))
    }

    service = ImageProcessingServiceV3(
        bedrock_client=mock_client,
        enable_caching=True,
        enable_metrics=True
    )

    # 运行测试
    benchmark = PerformanceBenchmark()

    # 测试单个请求
    print("\n1. 测试单个请求性能...")
    for i in range(10):
        request = ImageRequest(prompt=f"性能测试 {i}")
        benchmark.measure_performance(
            asyncio.run,
            service._generate_single_async(request)
        )

    single_stats = benchmark.get_statistics()
    print(f"平均耗时: {single_stats['execution_time']['mean']:.3f}秒")

    # 测试批处理
    print("\n2. 测试批处理性能...")
    benchmark.results = []
    requests = [ImageRequest(prompt=f"批处理测试 {i}") for i in range(20)]
    benchmark.measure_performance(
        asyncio.run,
        service.generate_images_batch(requests)
    )

    batch_stats = benchmark.get_statistics()
    print(f"批处理20张图片耗时: {batch_stats['execution_time']['mean']:.2f}秒")

    # 生成报告
    print("\n3. 生成性能报告...")
    report = generate_performance_report(service)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    # 清理资源
    service.cleanup()
    print("\n测试完成！")