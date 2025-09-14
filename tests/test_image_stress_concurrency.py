"""
图片生成服务并发和压力测试套件
专注于并发处理能力、压力测试和容错测试
"""

import pytest
import time
import asyncio
import concurrent.futures
import threading
import queue
from unittest.mock import Mock, patch
import sys
import os
import random
from typing import List, Dict, Any, Callable
import statistics

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas'))

from image_processing_service import ImageProcessingService
from image_config import CONFIG
from image_exceptions import ImageProcessingError, NovaServiceError

# 导入测试工具
from test_utils import (
    EnhancedAWSMockHelper, ConcurrencyTester, TestReportGenerator,
    create_test_image_data, performance_test
)


class StressTestConfig:
    """压力测试配置"""

    # 基本压力测试参数
    LIGHT_LOAD_REQUESTS = 50
    MEDIUM_LOAD_REQUESTS = 200
    HEAVY_LOAD_REQUESTS = 500

    # 并发测试参数
    LOW_CONCURRENCY = 5
    MEDIUM_CONCURRENCY = 15
    HIGH_CONCURRENCY = 30

    # 时间限制
    LIGHT_LOAD_TIMEOUT = 60
    MEDIUM_LOAD_TIMEOUT = 180
    HEAVY_LOAD_TIMEOUT = 300

    # 性能阈值
    MIN_SUCCESS_RATE = 0.95
    MAX_AVG_RESPONSE_TIME = 5.0
    MAX_P95_RESPONSE_TIME = 10.0
    MIN_THROUGHPUT = 1.0


class LoadGenerator:
    """负载生成器"""

    def __init__(self, service: ImageProcessingService):
        self.service = service
        self.results = []
        self.errors = []
        self.lock = threading.Lock()

    def single_request_worker(self, request_id: int, delay: float = 0) -> Dict[str, Any]:
        """单个请求工作器"""
        if delay > 0:
            time.sleep(delay)

        start_time = time.perf_counter()
        try:
            prompt = f"压力测试请求 {request_id} 现代商务风格"
            result = self.service.call_image_generation(prompt)
            success = isinstance(result, bytes) and len(result) > 0
            error_msg = None
        except Exception as e:
            success = False
            result = None
            error_msg = str(e)

        end_time = time.perf_counter()
        response_time = end_time - start_time

        result_data = {
            'request_id': request_id,
            'success': success,
            'response_time': response_time,
            'error': error_msg,
            'timestamp': start_time
        }

        with self.lock:
            if success:
                self.results.append(result_data)
            else:
                self.errors.append(result_data)

        return result_data

    def generate_constant_load(self, requests_per_second: float,
                              duration_seconds: int) -> Dict[str, Any]:
        """生成恒定负载"""
        total_requests = int(requests_per_second * duration_seconds)
        request_interval = 1.0 / requests_per_second

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = []

            for i in range(total_requests):
                # 计算延迟以维持恒定速率
                expected_time = start_time + (i * request_interval)
                current_time = time.time()
                delay = max(0, expected_time - current_time)

                future = executor.submit(self.single_request_worker, i, delay)
                futures.append(future)

            # 等待所有请求完成
            concurrent.futures.wait(futures, timeout=duration_seconds + 30)

        total_time = time.time() - start_time

        return self._analyze_results(total_time)

    def generate_burst_load(self, burst_size: int, burst_count: int,
                           interval_seconds: float) -> Dict[str, Any]:
        """生成突发负载"""
        all_results = []

        for burst_num in range(burst_count):
            burst_start = time.time()

            # 并发发送突发请求
            with concurrent.futures.ThreadPoolExecutor(max_workers=burst_size) as executor:
                futures = [
                    executor.submit(self.single_request_worker,
                                  burst_num * burst_size + i)
                    for i in range(burst_size)
                ]

                # 等待突发完成
                concurrent.futures.wait(futures, timeout=30)

            burst_duration = time.time() - burst_start

            # 等待下一个突发
            if burst_num < burst_count - 1:
                time.sleep(interval_seconds)

        return self._analyze_results(time.time() - burst_start)

    def _analyze_results(self, total_time: float) -> Dict[str, Any]:
        """分析测试结果"""
        total_requests = len(self.results) + len(self.errors)
        successful_requests = len(self.results)

        if successful_requests > 0:
            response_times = [r['response_time'] for r in self.results]
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)

            if len(response_times) >= 20:
                p95_response_time = statistics.quantiles(response_times, n=20)[18]
            else:
                p95_response_time = max_response_time

            if len(response_times) >= 100:
                p99_response_time = statistics.quantiles(response_times, n=100)[98]
            else:
                p99_response_time = max_response_time
        else:
            avg_response_time = 0
            min_response_time = 0
            max_response_time = 0
            p95_response_time = 0
            p99_response_time = 0

        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        throughput = successful_requests / total_time if total_time > 0 else 0

        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': len(self.errors),
            'success_rate': success_rate,
            'total_time': total_time,
            'throughput': throughput,
            'avg_response_time': avg_response_time,
            'min_response_time': min_response_time,
            'max_response_time': max_response_time,
            'p95_response_time': p95_response_time,
            'p99_response_time': p99_response_time,
            'errors': self.errors
        }


class TestConcurrencyBasics:
    """基础并发测试"""

    @pytest.fixture
    def mock_service(self):
        """创建Mock服务"""
        mock_client = EnhancedAWSMockHelper.create_bedrock_client_mock(
            response_delay=0.1, failure_rate=0.02
        )
        mock_s3 = EnhancedAWSMockHelper.create_s3_client_mock()

        return ImageProcessingService(
            bedrock_client=mock_client,
            s3_client=mock_s3,
            enable_caching=True
        )

    def test_basic_concurrent_access(self, mock_service):
        """测试基本并发访问"""
        tester = ConcurrencyTester(max_workers=10)

        def generate_image(prompt_suffix):
            prompt = f"并发测试 {prompt_suffix}"
            return mock_service.call_image_generation(prompt)

        test_data = [f"prompt_{i}" for i in range(20)]
        results = tester.run_concurrent_test(generate_image, test_data)

        # 验证并发测试结果
        assert results['success_rate'] >= 0.90
        assert results['avg_response_time'] < 2.0
        assert results['throughput'] > 5.0

        print(f"并发测试结果: 成功率 {results['success_rate']:.2%}, "
              f"平均响应时间 {results['avg_response_time']:.3f}s, "
              f"吞吐量 {results['throughput']:.1f} req/s")

    def test_thread_safety(self, mock_service):
        """测试线程安全性"""
        shared_data = {'counter': 0, 'errors': []}
        lock = threading.Lock()

        def thread_worker(thread_id):
            try:
                for i in range(10):
                    prompt = f"线程安全测试 Thread{thread_id} Iter{i}"
                    result = mock_service.call_image_generation(prompt)

                    with lock:
                        shared_data['counter'] += 1

                    assert isinstance(result, bytes)

            except Exception as e:
                with lock:
                    shared_data['errors'].append(f"Thread {thread_id}: {str(e)}")

        # 启动多个线程
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=thread_worker, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证线程安全
        assert shared_data['counter'] == 50  # 5个线程 × 10次调用
        assert len(shared_data['errors']) == 0

    def test_cache_consistency_under_concurrency(self, mock_service):
        """测试并发情况下的缓存一致性"""
        prompt = "缓存一致性测试"

        def concurrent_cache_test(worker_id):
            results = []
            for i in range(5):
                result = mock_service.call_image_generation(prompt)
                results.append(result)
            return results

        # 并发访问相同提示词
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(concurrent_cache_test, i) for i in range(8)]
            all_results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 验证缓存一致性
        first_result = all_results[0][0]
        for worker_results in all_results:
            for result in worker_results:
                assert result == first_result  # 缓存应该返回相同结果


class TestStressConditions:
    """压力条件测试"""

    @pytest.fixture
    def stress_service(self):
        """创建压力测试服务"""
        mock_client = EnhancedAWSMockHelper.create_bedrock_client_mock(
            response_delay=0.05, failure_rate=0.10  # 更高的失败率
        )
        mock_s3 = EnhancedAWSMockHelper.create_s3_client_mock()

        return ImageProcessingService(
            bedrock_client=mock_client,
            s3_client=mock_s3,
            enable_caching=True
        )

    @pytest.mark.stress
    def test_light_load_stress(self, stress_service):
        """轻负载压力测试"""
        load_generator = LoadGenerator(stress_service)

        # 10 RPS，持续30秒
        results = load_generator.generate_constant_load(
            requests_per_second=10,
            duration_seconds=30
        )

        # 验证轻负载性能
        assert results['success_rate'] >= StressTestConfig.MIN_SUCCESS_RATE
        assert results['avg_response_time'] < StressTestConfig.MAX_AVG_RESPONSE_TIME
        assert results['throughput'] >= StressTestConfig.MIN_THROUGHPUT

        print(f"轻负载测试: {results['total_requests']}个请求, "
              f"成功率 {results['success_rate']:.2%}, "
              f"吞吐量 {results['throughput']:.1f} RPS")

    @pytest.mark.stress
    def test_medium_load_stress(self, stress_service):
        """中负载压力测试"""
        load_generator = LoadGenerator(stress_service)

        # 20 RPS，持续60秒
        results = load_generator.generate_constant_load(
            requests_per_second=20,
            duration_seconds=60
        )

        # 中负载的要求稍微宽松
        assert results['success_rate'] >= 0.90
        assert results['avg_response_time'] < 8.0
        assert results['p95_response_time'] < 15.0

        print(f"中负载测试: {results['total_requests']}个请求, "
              f"成功率 {results['success_rate']:.2%}, "
              f"P95响应时间 {results['p95_response_time']:.2f}s")

    @pytest.mark.stress
    def test_burst_load_stress(self, stress_service):
        """突发负载压力测试"""
        load_generator = LoadGenerator(stress_service)

        # 5次突发，每次30个并发请求，间隔5秒
        results = load_generator.generate_burst_load(
            burst_size=30,
            burst_count=5,
            interval_seconds=5
        )

        # 突发负载测试
        assert results['success_rate'] >= 0.85  # 突发时允许更低成功率
        assert results['avg_response_time'] < 10.0

        print(f"突发负载测试: {results['total_requests']}个请求, "
              f"成功率 {results['success_rate']:.2%}, "
              f"最大响应时间 {results['max_response_time']:.2f}s")

    @pytest.mark.stress
    def test_sustained_high_concurrency(self, stress_service):
        """持续高并发测试"""
        def concurrent_worker(worker_id, duration_seconds):
            start_time = time.time()
            request_count = 0
            errors = 0

            while time.time() - start_time < duration_seconds:
                try:
                    prompt = f"高并发测试 Worker{worker_id} Req{request_count}"
                    result = stress_service.call_image_generation(prompt)
                    if not (isinstance(result, bytes) and len(result) > 0):
                        errors += 1
                    request_count += 1
                except Exception:
                    errors += 1
                    request_count += 1

                # 控制请求频率
                time.sleep(0.1)

            return {
                'worker_id': worker_id,
                'requests': request_count,
                'errors': errors,
                'success_rate': (request_count - errors) / request_count if request_count > 0 else 0
            }

        # 启动20个工作器，持续60秒
        duration = 60
        worker_count = 20

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(concurrent_worker, i, duration)
                for i in range(worker_count)
            ]

            worker_results = [future.result() for future in concurrent.futures.as_completed(futures)]

        total_time = time.time() - start_time

        # 分析结果
        total_requests = sum(r['requests'] for r in worker_results)
        total_errors = sum(r['errors'] for r in worker_results)
        overall_success_rate = (total_requests - total_errors) / total_requests if total_requests > 0 else 0
        overall_throughput = total_requests / total_time

        # 验证高并发性能
        assert overall_success_rate >= 0.80  # 高并发时允许更低成功率
        assert overall_throughput >= 50  # 至少50 RPS的吞吐量

        print(f"高并发测试: {worker_count}个工作器, {total_requests}个请求, "
              f"成功率 {overall_success_rate:.2%}, "
              f"吞吐量 {overall_throughput:.1f} RPS")


class TestFailureRecovery:
    """故障恢复测试"""

    @pytest.fixture
    def unreliable_service(self):
        """创建不可靠的服务"""
        # 高失败率的服务
        mock_client = EnhancedAWSMockHelper.create_bedrock_client_mock(
            response_delay=0.1, failure_rate=0.30
        )
        mock_s3 = EnhancedAWSMockHelper.create_s3_client_mock()

        return ImageProcessingService(
            bedrock_client=mock_client,
            s3_client=mock_s3,
            enable_caching=True
        )

    def test_failure_recovery_under_load(self, unreliable_service):
        """测试负载下的故障恢复"""
        def worker_with_recovery(worker_id):
            success_count = 0
            failure_count = 0
            recovery_count = 0

            for i in range(20):
                try:
                    prompt = f"故障恢复测试 Worker{worker_id} Req{i}"
                    result = unreliable_service.call_image_generation(prompt)

                    if isinstance(result, bytes) and len(result) > 0:
                        success_count += 1
                        if failure_count > 0:  # 从失败中恢复
                            recovery_count += 1
                            failure_count = 0
                    else:
                        failure_count += 1

                except Exception:
                    failure_count += 1

                time.sleep(0.05)  # 控制频率

            return {
                'worker_id': worker_id,
                'success_count': success_count,
                'recovery_count': recovery_count
            }

        # 并发执行故障恢复测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_with_recovery, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 分析恢复能力
        total_successes = sum(r['success_count'] for r in results)
        total_recoveries = sum(r['recovery_count'] for r in results)
        total_attempts = len(results) * 20

        success_rate = total_successes / total_attempts

        # 验证故障恢复
        assert success_rate >= 0.60  # 即使高失败率也要有基本成功率
        assert total_recoveries > 0  # 应该有恢复事件

        print(f"故障恢复测试: 成功率 {success_rate:.2%}, 恢复事件 {total_recoveries}")

    def test_cascading_failure_prevention(self, unreliable_service):
        """测试级联故障预防"""
        failure_tracker = {'consecutive_failures': 0, 'max_consecutive': 0}

        def track_failures(worker_id):
            local_consecutive = 0

            for i in range(30):
                try:
                    prompt = f"级联故障测试 Worker{worker_id} Req{i}"
                    result = unreliable_service.call_image_generation(prompt)

                    if isinstance(result, bytes) and len(result) > 0:
                        local_consecutive = 0
                    else:
                        local_consecutive += 1

                except Exception:
                    local_consecutive += 1

                # 更新全局连续失败计数
                with threading.Lock():
                    failure_tracker['consecutive_failures'] = local_consecutive
                    failure_tracker['max_consecutive'] = max(
                        failure_tracker['max_consecutive'],
                        local_consecutive
                    )

                time.sleep(0.02)

            return local_consecutive

        # 并发测试级联失败
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(track_failures, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 验证级联失败预防
        max_consecutive_failures = failure_tracker['max_consecutive']

        # 连续失败不应该过多（回退机制应该生效）
        assert max_consecutive_failures < 10

        print(f"级联故障测试: 最大连续失败 {max_consecutive_failures}")


class TestResourceManagement:
    """资源管理测试"""

    @pytest.fixture
    def monitored_service(self):
        """创建可监控的服务"""
        mock_client = EnhancedAWSMockHelper.create_bedrock_client_mock(
            response_delay=0.05, failure_rate=0.05
        )
        mock_s3 = EnhancedAWSMockHelper.create_s3_client_mock()

        return ImageProcessingService(
            bedrock_client=mock_client,
            s3_client=mock_s3,
            enable_caching=True
        )

    def test_memory_usage_under_load(self, monitored_service):
        """测试负载下的内存使用"""
        import psutil
        import gc

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        def memory_intensive_worker(worker_id):
            for i in range(50):
                prompt = f"内存测试 Worker{worker_id} Req{i} {' ' * 100}"  # 加长提示词
                result = monitored_service.call_image_generation(prompt)

                # 每10次请求检查内存
                if i % 10 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_increase = current_memory - initial_memory

                    # 内存增长不应该过快
                    if memory_increase > 500:  # 超过500MB
                        return False

            return True

        # 并发执行内存测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(memory_intensive_worker, i) for i in range(8)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 清理并检查最终内存
        monitored_service.clear_cache()
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024
        memory_delta = final_memory - initial_memory

        # 验证内存管理
        assert all(results), "内存使用超出限制"
        assert memory_delta < 200, f"内存增长过多: {memory_delta:.1f}MB"

        print(f"内存使用测试: 初始 {initial_memory:.1f}MB, "
              f"最终 {final_memory:.1f}MB, "
              f"净增长 {memory_delta:.1f}MB")

    def test_connection_pool_management(self, monitored_service):
        """测试连接池管理"""
        connection_stats = {'active_connections': 0, 'max_connections': 0}
        lock = threading.Lock()

        def connection_worker(worker_id):
            with lock:
                connection_stats['active_connections'] += 1
                connection_stats['max_connections'] = max(
                    connection_stats['max_connections'],
                    connection_stats['active_connections']
                )

            try:
                # 模拟长时间连接
                for i in range(10):
                    prompt = f"连接池测试 Worker{worker_id} Req{i}"
                    result = monitored_service.call_image_generation(prompt)
                    time.sleep(0.1)

                return True
            finally:
                with lock:
                    connection_stats['active_connections'] -= 1

        # 启动大量并发连接
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(connection_worker, i) for i in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 验证连接池管理
        assert all(results), "连接池管理出现问题"
        assert connection_stats['max_connections'] <= 25, "并发连接数过高"

        print(f"连接池测试: 最大并发连接 {connection_stats['max_connections']}")


class TestPerformanceDegradation:
    """性能退化测试"""

    def test_gradual_load_increase(self):
        """测试逐步增加负载"""
        mock_client = EnhancedAWSMockHelper.create_bedrock_client_mock(
            response_delay=0.02, failure_rate=0.01
        )
        mock_s3 = EnhancedAWSMockHelper.create_s3_client_mock()

        service = ImageProcessingService(
            bedrock_client=mock_client,
            s3_client=mock_s3,
            enable_caching=True
        )

        load_levels = [1, 5, 10, 20, 30]  # RPS
        performance_data = []

        for rps in load_levels:
            load_generator = LoadGenerator(service)

            # 每个负载级别测试30秒
            results = load_generator.generate_constant_load(
                requests_per_second=rps,
                duration_seconds=30
            )

            performance_data.append({
                'rps': rps,
                'success_rate': results['success_rate'],
                'avg_response_time': results['avg_response_time'],
                'p95_response_time': results['p95_response_time'],
                'actual_throughput': results['throughput']
            })

            # 清理缓存避免影响下一轮测试
            service.clear_cache()
            time.sleep(5)  # 休息5秒

        # 分析性能退化
        print("负载增加性能分析:")
        for data in performance_data:
            print(f"目标RPS: {data['rps']}, "
                  f"实际吞吐量: {data['actual_throughput']:.1f}, "
                  f"成功率: {data['success_rate']:.2%}, "
                  f"P95响应时间: {data['p95_response_time']:.3f}s")

        # 验证性能退化是否可接受
        for i, data in enumerate(performance_data):
            if i > 0:  # 跳过第一个数据点
                prev_data = performance_data[i-1]

                # 成功率不应该大幅下降
                success_rate_drop = prev_data['success_rate'] - data['success_rate']
                assert success_rate_drop < 0.10, f"成功率下降过多: {success_rate_drop:.2%}"

                # 响应时间增长应该可控
                response_time_ratio = data['avg_response_time'] / prev_data['avg_response_time']
                assert response_time_ratio < 3.0, f"响应时间增长过多: {response_time_ratio:.1f}x"


if __name__ == "__main__":
    # 运行压力和并发测试
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "stress",  # 只运行压力测试
        "--durations=10"
    ])