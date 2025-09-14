"""
图片生成服务性能基准测试套件
专注于性能测试、基准测试和资源使用监控
"""

import pytest
import time
import asyncio
import concurrent.futures
import threading
import statistics
import psutil
import gc
import json
from unittest.mock import Mock, patch
from typing import List, Dict, Any
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas'))

from image_processing_service import ImageProcessingService
from image_config import CONFIG


class PerformanceMonitor:
    """性能监控工具"""

    def __init__(self):
        self.process = psutil.Process()
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None
        self.measurements = []

    def start_monitoring(self):
        """开始监控"""
        self.start_time = time.perf_counter()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = self.process.cpu_percent()
        self.measurements = []

    def record_measurement(self, label: str):
        """记录一个测量点"""
        current_time = time.perf_counter()
        current_memory = self.process.memory_info().rss / 1024 / 1024
        current_cpu = self.process.cpu_percent()

        measurement = {
            'label': label,
            'elapsed_time': current_time - self.start_time,
            'memory_mb': current_memory,
            'memory_delta': current_memory - self.start_memory,
            'cpu_percent': current_cpu
        }
        self.measurements.append(measurement)
        return measurement

    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.measurements:
            return {}

        total_time = self.measurements[-1]['elapsed_time']
        max_memory = max(m['memory_mb'] for m in self.measurements)
        max_memory_delta = max(m['memory_delta'] for m in self.measurements)
        avg_cpu = statistics.mean(m['cpu_percent'] for m in self.measurements)

        return {
            'total_time': total_time,
            'max_memory_mb': max_memory,
            'max_memory_delta_mb': max_memory_delta,
            'avg_cpu_percent': avg_cpu,
            'measurement_count': len(self.measurements)
        }


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self, iterations: int = 10):
        self.iterations = iterations
        self.results = []

    def run_benchmark(self, test_func, *args, **kwargs):
        """运行基准测试"""
        times = []
        for i in range(self.iterations):
            start_time = time.perf_counter()
            result = test_func(*args, **kwargs)
            end_time = time.perf_counter()

            execution_time = end_time - start_time
            times.append(execution_time)

            self.results.append({
                'iteration': i,
                'time': execution_time,
                'result': result
            })

        return self._analyze_results(times)

    def _analyze_results(self, times: List[float]) -> Dict[str, float]:
        """分析基准测试结果"""
        return {
            'min_time': min(times),
            'max_time': max(times),
            'avg_time': statistics.mean(times),
            'median_time': statistics.median(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
            'p95_time': statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
            'p99_time': statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times)
        }


@pytest.fixture
def performance_monitor():
    """性能监控fixture"""
    return PerformanceMonitor()


@pytest.fixture
def benchmark_runner():
    """基准测试运行器fixture"""
    return BenchmarkRunner(iterations=20)


@pytest.fixture
def optimized_mock_bedrock():
    """优化的Mock Bedrock客户端，模拟真实延迟"""
    client = Mock()

    def realistic_invoke_model(**kwargs):
        # 模拟真实API延迟
        time.sleep(0.1 + 0.05 * (1 if 'nova' in kwargs.get('modelId', '') else 0.5))

        # 返回标准响应
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "images": ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hRqYEAAAAABJRU5ErkJggg=="]
        }).encode()

        return {'body': mock_response, 'ResponseMetadata': {'HTTPStatusCode': 200}}

    client.invoke_model.side_effect = realistic_invoke_model
    return client


class TestPerformanceBaselines:
    """性能基线测试"""

    def test_prompt_generation_baseline(self, benchmark_runner, performance_monitor):
        """测试提示词生成性能基线"""
        service = ImageProcessingService(enable_caching=False)

        test_content = {
            "title": "AI技术在金融行业的应用与发展前景",
            "content": [
                "智能风控系统的构建与优化",
                "算法交易与量化投资策略",
                "客户服务智能化解决方案",
                "区块链与AI的融合创新",
                "监管科技的技术实现路径"
            ]
        }

        performance_monitor.start_monitoring()

        # 运行基准测试
        def generate_prompt():
            return service.generate_prompt(test_content, "business")

        results = benchmark_runner.run_benchmark(generate_prompt)

        performance_monitor.record_measurement("prompt_generation_complete")
        summary = performance_monitor.get_summary()

        # 性能断言
        assert results['avg_time'] < 0.050  # 平均50ms以内
        assert results['p95_time'] < 0.100  # 95%在100ms以内
        assert results['max_time'] < 0.200  # 最大200ms以内

        # 内存使用断言
        assert summary['max_memory_delta_mb'] < 10  # 内存增长不超过10MB

        print(f"提示词生成性能基线:")
        print(f"平均时间: {results['avg_time']:.4f}s")
        print(f"P95时间: {results['p95_time']:.4f}s")
        print(f"最大时间: {results['max_time']:.4f}s")
        print(f"标准差: {results['std_dev']:.4f}s")

    def test_image_validation_baseline(self, benchmark_runner):
        """测试图片验证性能基线"""
        service = ImageProcessingService(enable_caching=False)

        # 创建测试图片数据
        from PIL import Image
        import io
        image = Image.new('RGB', (800, 600), color='blue')
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        test_image_data = img_bytes.getvalue()

        def validate_image():
            return service.validate_image_format(test_image_data, 'PNG')

        results = benchmark_runner.run_benchmark(validate_image)

        # 性能断言
        assert results['avg_time'] < 0.010  # 平均10ms以内
        assert results['p95_time'] < 0.020  # 95%在20ms以内
        assert all(r['result'] is True for r in benchmark_runner.results)

        print(f"图片验证性能基线:")
        print(f"平均时间: {results['avg_time']:.4f}s")
        print(f"P95时间: {results['p95_time']:.4f}s")

    def test_cache_performance_baseline(self, optimized_mock_bedrock, benchmark_runner, performance_monitor):
        """测试缓存性能基线"""
        service = ImageProcessingService(
            bedrock_client=optimized_mock_bedrock,
            enable_caching=True
        )

        test_prompt = "缓存性能基线测试，现代商务风格"

        performance_monitor.start_monitoring()

        # 第一次调用（缓存未命中）
        first_call_time = time.perf_counter()
        service.call_image_generation(test_prompt)
        first_call_duration = time.perf_counter() - first_call_time

        performance_monitor.record_measurement("first_call_complete")

        # 后续调用（缓存命中）
        def cached_call():
            return service.call_image_generation(test_prompt)

        results = benchmark_runner.run_benchmark(cached_call)

        performance_monitor.record_measurement("cached_calls_complete")
        summary = performance_monitor.get_summary()

        # 性能断言
        assert results['avg_time'] < 0.001  # 缓存命中应该在1ms以内
        assert results['avg_time'] < first_call_duration * 0.01  # 至少快100倍

        print(f"缓存性能基线:")
        print(f"首次调用时间: {first_call_duration:.4f}s")
        print(f"缓存命中平均时间: {results['avg_time']:.4f}s")
        print(f"性能提升倍数: {first_call_duration / results['avg_time']:.1f}x")

    def test_concurrent_baseline(self, optimized_mock_bedrock, performance_monitor):
        """测试并发性能基线"""
        service = ImageProcessingService(
            bedrock_client=optimized_mock_bedrock,
            enable_caching=True
        )

        performance_monitor.start_monitoring()

        def concurrent_worker(worker_id: int) -> Dict[str, Any]:
            worker_start = time.perf_counter()
            prompt = f"并发基线测试 Worker {worker_id}"

            try:
                result = service.call_image_generation(prompt)
                success = isinstance(result, bytes) and len(result) > 0
            except Exception as e:
                success = False

            worker_end = time.perf_counter()

            return {
                'worker_id': worker_id,
                'duration': worker_end - worker_start,
                'success': success
            }

        # 测试不同并发级别
        concurrency_levels = [1, 2, 4, 8, 16]
        results = {}

        for concurrency in concurrency_levels:
            start_time = time.perf_counter()

            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(concurrent_worker, i) for i in range(concurrency)]
                worker_results = [future.result() for future in concurrent.futures.as_completed(futures)]

            total_time = time.perf_counter() - start_time

            # 分析结果
            successful_workers = [r for r in worker_results if r['success']]
            success_rate = len(successful_workers) / len(worker_results)

            worker_times = [r['duration'] for r in successful_workers]
            avg_worker_time = statistics.mean(worker_times) if worker_times else 0

            throughput = len(successful_workers) / total_time

            results[concurrency] = {
                'total_time': total_time,
                'success_rate': success_rate,
                'avg_worker_time': avg_worker_time,
                'throughput': throughput
            }

            # 性能断言
            assert success_rate >= 0.90  # 至少90%成功率
            assert throughput > 0  # 有效吞吐量

            performance_monitor.record_measurement(f"concurrency_{concurrency}")

        summary = performance_monitor.get_summary()

        print(f"并发性能基线结果:")
        for concurrency, result in results.items():
            print(f"并发度 {concurrency}: 成功率 {result['success_rate']:.2%}, "
                  f"吞吐量 {result['throughput']:.1f} ops/s, "
                  f"平均延迟 {result['avg_worker_time']:.3f}s")

        # 验证扩展性
        best_throughput = max(results.values(), key=lambda x: x['throughput'])['throughput']
        single_throughput = results[1]['throughput']
        scalability_factor = best_throughput / single_throughput

        assert scalability_factor >= 2.0  # 至少2倍扩展性

    def test_memory_efficiency_baseline(self, optimized_mock_bedrock, performance_monitor):
        """测试内存效率基线"""
        import gc

        performance_monitor.start_monitoring()

        # 禁用垃圾回收以准确测量
        gc.disable()

        try:
            service = ImageProcessingService(
                bedrock_client=optimized_mock_bedrock,
                enable_caching=True
            )

            performance_monitor.record_measurement("service_created")

            # 生成大量图片
            batch_sizes = [10, 50, 100, 200]
            memory_usage = {}

            for batch_size in batch_sizes:
                # 清理之前的缓存
                service.clear_cache()
                gc.collect()

                start_memory = performance_monitor.process.memory_info().rss / 1024 / 1024

                # 批量生成
                for i in range(batch_size):
                    prompt = f"内存效率测试 batch{batch_size} item{i}"
                    service.call_image_generation(prompt)

                end_memory = performance_monitor.process.memory_info().rss / 1024 / 1024
                memory_delta = end_memory - start_memory
                memory_per_image = memory_delta / batch_size

                memory_usage[batch_size] = {
                    'total_memory_mb': memory_delta,
                    'memory_per_image_mb': memory_per_image
                }

                performance_monitor.record_measurement(f"batch_{batch_size}_complete")

                # 内存效率断言
                assert memory_per_image < 5.0  # 每张图片不超过5MB内存
                assert memory_delta < batch_size * 10  # 总内存合理

        finally:
            gc.enable()

        summary = performance_monitor.get_summary()

        print(f"内存效率基线:")
        for batch_size, usage in memory_usage.items():
            print(f"批次大小 {batch_size}: 总内存 {usage['total_memory_mb']:.1f}MB, "
                  f"单图内存 {usage['memory_per_image_mb']:.2f}MB")

        # 验证内存线性增长
        memory_per_image_values = [usage['memory_per_image_mb'] for usage in memory_usage.values()]
        memory_std = statistics.stdev(memory_per_image_values)
        assert memory_std < 1.0  # 内存使用应该相对稳定


class TestLoadTesting:
    """负载测试"""

    @pytest.mark.load
    def test_sustained_load(self, optimized_mock_bedrock, performance_monitor):
        """测试持续负载"""
        service = ImageProcessingService(
            bedrock_client=optimized_mock_bedrock,
            enable_caching=True
        )

        performance_monitor.start_monitoring()

        # 持续负载参数
        duration_minutes = 5
        target_rps = 10  # 每秒请求数
        total_requests = int(duration_minutes * 60 * target_rps)

        successful_requests = 0
        failed_requests = 0
        response_times = []

        start_time = time.time()

        for i in range(total_requests):
            request_start = time.perf_counter()

            try:
                prompt = f"持续负载测试 请求{i}"
                result = service.call_image_generation(prompt)

                if isinstance(result, bytes) and len(result) > 0:
                    successful_requests += 1
                else:
                    failed_requests += 1

            except Exception:
                failed_requests += 1

            request_end = time.perf_counter()
            response_time = request_end - request_start
            response_times.append(response_time)

            # 控制请求速率
            elapsed = time.time() - start_time
            expected_requests = elapsed * target_rps
            if i + 1 > expected_requests:
                sleep_time = (i + 1) / target_rps - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            # 记录进度
            if (i + 1) % 100 == 0:
                performance_monitor.record_measurement(f"request_{i+1}")

        total_time = time.time() - start_time
        actual_rps = total_requests / total_time
        success_rate = successful_requests / total_requests

        # 性能指标
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]
        p99_response_time = statistics.quantiles(response_times, n=100)[98]

        # 负载测试断言
        assert success_rate >= 0.95  # 95%成功率
        assert actual_rps >= target_rps * 0.9  # 实际RPS接近目标
        assert p95_response_time < 1.0  # P95响应时间小于1秒
        assert p99_response_time < 2.0  # P99响应时间小于2秒

        summary = performance_monitor.get_summary()

        print(f"持续负载测试结果:")
        print(f"总请求数: {total_requests}")
        print(f"成功请求: {successful_requests}")
        print(f"失败请求: {failed_requests}")
        print(f"成功率: {success_rate:.2%}")
        print(f"目标RPS: {target_rps}")
        print(f"实际RPS: {actual_rps:.1f}")
        print(f"平均响应时间: {avg_response_time:.3f}s")
        print(f"P95响应时间: {p95_response_time:.3f}s")
        print(f"P99响应时间: {p99_response_time:.3f}s")
        print(f"最大内存使用: {summary['max_memory_delta_mb']:.1f}MB")

    @pytest.mark.load
    def test_burst_load(self, optimized_mock_bedrock, performance_monitor):
        """测试突发负载"""
        service = ImageProcessingService(
            bedrock_client=optimized_mock_bedrock,
            enable_caching=True
        )

        performance_monitor.start_monitoring()

        # 突发负载参数
        burst_size = 50
        burst_interval = 2  # 每2秒一次突发
        num_bursts = 10

        all_results = []

        for burst_num in range(num_bursts):
            burst_start = time.time()

            # 并发发送突发请求
            def burst_worker(request_id):
                worker_start = time.perf_counter()
                try:
                    prompt = f"突发负载测试 Burst{burst_num} Req{request_id}"
                    result = service.call_image_generation(prompt)
                    success = isinstance(result, bytes) and len(result) > 0
                except Exception:
                    success = False

                worker_end = time.perf_counter()
                return {
                    'burst_num': burst_num,
                    'request_id': request_id,
                    'duration': worker_end - worker_start,
                    'success': success
                }

            with concurrent.futures.ThreadPoolExecutor(max_workers=burst_size) as executor:
                futures = [executor.submit(burst_worker, i) for i in range(burst_size)]
                burst_results = [future.result() for future in concurrent.futures.as_completed(futures)]

            burst_end = time.time()
            burst_duration = burst_end - burst_start

            # 分析突发结果
            successful_in_burst = sum(1 for r in burst_results if r['success'])
            success_rate_burst = successful_in_burst / burst_size
            avg_duration_burst = statistics.mean(r['duration'] for r in burst_results)

            all_results.extend(burst_results)

            performance_monitor.record_measurement(f"burst_{burst_num}")

            print(f"突发 {burst_num}: 成功率 {success_rate_burst:.2%}, "
                  f"突发耗时 {burst_duration:.2f}s, "
                  f"平均请求耗时 {avg_duration_burst:.3f}s")

            # 等待下一次突发
            if burst_num < num_bursts - 1:
                time.sleep(burst_interval)

        # 总体分析
        total_requests = len(all_results)
        total_successful = sum(1 for r in all_results if r['success'])
        overall_success_rate = total_successful / total_requests

        response_times = [r['duration'] for r in all_results if r['success']]
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]
        else:
            avg_response_time = 0
            p95_response_time = 0

        # 突发负载断言
        assert overall_success_rate >= 0.90  # 90%成功率（突发负载要求稍低）
        assert avg_response_time < 2.0  # 平均响应时间小于2秒
        assert p95_response_time < 5.0  # P95响应时间小于5秒

        summary = performance_monitor.get_summary()

        print(f"突发负载测试总结:")
        print(f"突发次数: {num_bursts}")
        print(f"每次突发大小: {burst_size}")
        print(f"总请求数: {total_requests}")
        print(f"总体成功率: {overall_success_rate:.2%}")
        print(f"平均响应时间: {avg_response_time:.3f}s")
        print(f"P95响应时间: {p95_response_time:.3f}s")


class TestScalabilityAnalysis:
    """扩展性分析测试"""

    @pytest.mark.scalability
    def test_horizontal_scalability(self, optimized_mock_bedrock, performance_monitor):
        """测试水平扩展性"""
        performance_monitor.start_monitoring()

        # 模拟多个服务实例
        num_instances = [1, 2, 4, 8]
        results = {}

        for instances in num_instances:
            # 创建多个服务实例
            services = [
                ImageProcessingService(
                    bedrock_client=optimized_mock_bedrock,
                    enable_caching=True
                )
                for _ in range(instances)
            ]

            # 负载测试
            requests_per_instance = 20
            total_requests = instances * requests_per_instance

            def instance_worker(instance_id, service_instance):
                instance_results = []
                for i in range(requests_per_instance):
                    start_time = time.perf_counter()
                    try:
                        prompt = f"扩展性测试 Instance{instance_id} Req{i}"
                        result = service_instance.call_image_generation(prompt)
                        success = isinstance(result, bytes) and len(result) > 0
                    except Exception:
                        success = False

                    end_time = time.perf_counter()
                    instance_results.append({
                        'instance_id': instance_id,
                        'success': success,
                        'duration': end_time - start_time
                    })
                return instance_results

            # 并发执行所有实例
            start_time = time.time()

            with concurrent.futures.ThreadPoolExecutor(max_workers=instances) as executor:
                futures = [
                    executor.submit(instance_worker, i, services[i])
                    for i in range(instances)
                ]
                all_instance_results = []
                for future in concurrent.futures.as_completed(futures):
                    all_instance_results.extend(future.result())

            total_time = time.time() - start_time

            # 分析结果
            successful_requests = sum(1 for r in all_instance_results if r['success'])
            success_rate = successful_requests / total_requests
            throughput = successful_requests / total_time

            response_times = [r['duration'] for r in all_instance_results if r['success']]
            avg_response_time = statistics.mean(response_times) if response_times else 0

            results[instances] = {
                'throughput': throughput,
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'total_time': total_time
            }

            performance_monitor.record_measurement(f"instances_{instances}")

        # 扩展性分析
        single_instance_throughput = results[1]['throughput']
        scalability_analysis = {}

        for instances in num_instances[1:]:  # 跳过单实例
            actual_throughput = results[instances]['throughput']
            theoretical_throughput = single_instance_throughput * instances
            scalability_efficiency = actual_throughput / theoretical_throughput

            scalability_analysis[instances] = {
                'efficiency': scalability_efficiency,
                'speedup': actual_throughput / single_instance_throughput
            }

            # 扩展性断言
            assert scalability_efficiency >= 0.7  # 至少70%扩展效率

        print(f"水平扩展性分析:")
        for instances, result in results.items():
            print(f"{instances}实例: 吞吐量 {result['throughput']:.1f} ops/s, "
                  f"成功率 {result['success_rate']:.2%}, "
                  f"平均响应时间 {result['avg_response_time']:.3f}s")

        for instances, analysis in scalability_analysis.items():
            print(f"{instances}实例扩展: 效率 {analysis['efficiency']:.2%}, "
                  f"加速比 {analysis['speedup']:.1f}x")


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "not (load or scalability)",  # 默认跳过长时间测试
        "--durations=10"  # 显示最慢的10个测试
    ])