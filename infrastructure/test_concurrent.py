#!/usr/bin/env python3
"""
AI PPT API并发和负载测试套件
专注于测试API在高并发情况下的性能和稳定性
"""

import asyncio
import aiohttp
import time
import json
import statistics
import argparse
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import uuid
import concurrent.futures
import threading
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ConcurrentTestResult:
    """并发测试单次结果"""
    request_id: str
    start_time: float
    end_time: float
    status_code: int
    response_time_ms: int
    success: bool
    error_message: Optional[str] = None
    response_size: int = 0

@dataclass
class LoadTestSummary:
    """负载测试摘要"""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    total_duration_seconds: float
    requests_per_second: float
    avg_response_time_ms: float
    min_response_time_ms: int
    max_response_time_ms: int
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    error_distribution: Dict[str, int]

class ConcurrentAPITester:
    """并发API测试器"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.results: List[ConcurrentTestResult] = []

    async def make_request(self, session: aiohttp.ClientSession, method: str,
                          endpoint: str, data: Optional[Dict] = None,
                          request_id: str = None) -> ConcurrentTestResult:
        """执行单个异步HTTP请求"""
        if request_id is None:
            request_id = f"{method}-{endpoint.replace('/', '_')}-{uuid.uuid4().hex[:8]}"

        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'AI-PPT-Concurrent-Tester/1.0'
            }

            if method.upper() == 'GET':
                async with session.get(url, headers=headers, timeout=self.timeout) as response:
                    response_text = await response.text()
                    end_time = time.time()

                    return ConcurrentTestResult(
                        request_id=request_id,
                        start_time=start_time,
                        end_time=end_time,
                        status_code=response.status,
                        response_time_ms=int((end_time - start_time) * 1000),
                        success=200 <= response.status < 500,  # 客户端错误也算预期行为
                        response_size=len(response_text.encode('utf-8'))
                    )

            elif method.upper() == 'POST':
                async with session.post(url, json=data, headers=headers,
                                      timeout=self.timeout) as response:
                    response_text = await response.text()
                    end_time = time.time()

                    return ConcurrentTestResult(
                        request_id=request_id,
                        start_time=start_time,
                        end_time=end_time,
                        status_code=response.status,
                        response_time_ms=int((end_time - start_time) * 1000),
                        success=200 <= response.status < 500,
                        response_size=len(response_text.encode('utf-8'))
                    )

            elif method.upper() == 'OPTIONS':
                headers.update({
                    'Origin': 'https://example.com',
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'Content-Type'
                })
                async with session.options(url, headers=headers,
                                         timeout=self.timeout) as response:
                    response_text = await response.text()
                    end_time = time.time()

                    return ConcurrentTestResult(
                        request_id=request_id,
                        start_time=start_time,
                        end_time=end_time,
                        status_code=response.status,
                        response_time_ms=int((end_time - start_time) * 1000),
                        success=response.status in [200, 204],
                        response_size=len(response_text.encode('utf-8'))
                    )

        except asyncio.TimeoutError:
            end_time = time.time()
            return ConcurrentTestResult(
                request_id=request_id,
                start_time=start_time,
                end_time=end_time,
                status_code=0,
                response_time_ms=int((end_time - start_time) * 1000),
                success=False,
                error_message="Request timeout"
            )

        except Exception as e:
            end_time = time.time()
            return ConcurrentTestResult(
                request_id=request_id,
                start_time=start_time,
                end_time=end_time,
                status_code=0,
                response_time_ms=int((end_time - start_time) * 1000),
                success=False,
                error_message=str(e)
            )

    async def run_concurrent_requests(self, requests_config: List[Dict[str, Any]],
                                    max_concurrent: int = 10) -> List[ConcurrentTestResult]:
        """运行并发请求"""
        connector = aiohttp.TCPConnector(limit=max_concurrent, limit_per_host=max_concurrent)
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []

            for i, config in enumerate(requests_config):
                task = self.make_request(
                    session=session,
                    method=config['method'],
                    endpoint=config['endpoint'],
                    data=config.get('data'),
                    request_id=config.get('request_id', f"req-{i}")
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(ConcurrentTestResult(
                        request_id=f"req-{i}",
                        start_time=time.time(),
                        end_time=time.time(),
                        status_code=0,
                        response_time_ms=0,
                        success=False,
                        error_message=str(result)
                    ))
                else:
                    processed_results.append(result)

            return processed_results

    def analyze_results(self, results: List[ConcurrentTestResult],
                       test_name: str) -> LoadTestSummary:
        """分析测试结果"""
        if not results:
            return LoadTestSummary(
                test_name=test_name,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                success_rate=0.0,
                total_duration_seconds=0.0,
                requests_per_second=0.0,
                avg_response_time_ms=0.0,
                min_response_time_ms=0,
                max_response_time_ms=0,
                median_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                error_distribution={}
            )

        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        response_times = [r.response_time_ms for r in successful_results if r.response_time_ms > 0]

        # 时间统计
        if results:
            start_time = min(r.start_time for r in results)
            end_time = max(r.end_time for r in results)
            total_duration = end_time - start_time
        else:
            total_duration = 0

        # 响应时间统计
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            median_response_time = statistics.median(response_times)

            # 计算百分位数
            sorted_times = sorted(response_times)
            p95_index = int(len(sorted_times) * 0.95)
            p99_index = int(len(sorted_times) * 0.99)
            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_response_time
            p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_response_time
        else:
            avg_response_time = 0
            min_response_time = 0
            max_response_time = 0
            median_response_time = 0
            p95_response_time = 0
            p99_response_time = 0

        # 错误分布
        error_distribution = {}
        for result in failed_results:
            if result.error_message:
                error_key = result.error_message
            elif result.status_code > 0:
                error_key = f"HTTP {result.status_code}"
            else:
                error_key = "Unknown error"

            error_distribution[error_key] = error_distribution.get(error_key, 0) + 1

        return LoadTestSummary(
            test_name=test_name,
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            success_rate=(len(successful_results) / len(results)) * 100 if results else 0,
            total_duration_seconds=total_duration,
            requests_per_second=len(results) / total_duration if total_duration > 0 else 0,
            avg_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            median_response_time_ms=median_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            error_distribution=error_distribution
        )

    def generate_test_requests(self, endpoint: str, method: str,
                             count: int, data_template: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """生成测试请求配置"""
        requests = []

        for i in range(count):
            config = {
                'method': method,
                'endpoint': endpoint,
                'request_id': f"{method.lower()}-{endpoint.replace('/', '_')}-{i}"
            }

            if data_template and method.upper() == 'POST':
                # 为每个请求创建略有不同的数据
                data = data_template.copy()
                if 'topic' in data:
                    data['topic'] = f"{data['topic']} - 测试 {i}"
                config['data'] = data

            elif endpoint.startswith('/status/') or endpoint.startswith('/download/'):
                # 为状态和下载请求生成唯一ID
                config['endpoint'] = endpoint.replace('test-id', f'test-id-{i}-{uuid.uuid4().hex[:8]}')

            requests.append(config)

        return requests

    async def test_concurrent_status_requests(self, concurrent_count: int = 20) -> LoadTestSummary:
        """测试并发状态查询"""
        logger.info(f"开始并发状态查询测试 ({concurrent_count}个并发请求)")

        requests_config = self.generate_test_requests('/status/test-id', 'GET', concurrent_count)
        results = await self.run_concurrent_requests(requests_config, concurrent_count)

        return self.analyze_results(results, f"并发状态查询 ({concurrent_count}个并发)")

    async def test_concurrent_options_requests(self, concurrent_count: int = 15) -> LoadTestSummary:
        """测试并发OPTIONS预检请求"""
        logger.info(f"开始并发OPTIONS预检测试 ({concurrent_count}个并发请求)")

        requests_config = self.generate_test_requests('/generate', 'OPTIONS', concurrent_count)
        results = await self.run_concurrent_requests(requests_config, concurrent_count)

        return self.analyze_results(results, f"并发OPTIONS预检 ({concurrent_count}个并发)")

    async def test_concurrent_download_requests(self, concurrent_count: int = 10) -> LoadTestSummary:
        """测试并发下载请求"""
        logger.info(f"开始并发下载请求测试 ({concurrent_count}个并发请求)")

        requests_config = self.generate_test_requests('/download/test-id', 'GET', concurrent_count)
        results = await self.run_concurrent_requests(requests_config, concurrent_count)

        return self.analyze_results(results, f"并发下载请求 ({concurrent_count}个并发)")

    async def test_mixed_concurrent_requests(self, total_requests: int = 30) -> LoadTestSummary:
        """测试混合并发请求"""
        logger.info(f"开始混合并发请求测试 ({total_requests}个请求)")

        # 创建混合请求
        requests_config = []

        # 状态查询请求 (40%)
        status_count = int(total_requests * 0.4)
        requests_config.extend(self.generate_test_requests('/status/test-id', 'GET', status_count))

        # OPTIONS预检请求 (30%)
        options_count = int(total_requests * 0.3)
        requests_config.extend(self.generate_test_requests('/generate', 'OPTIONS', options_count))

        # 下载请求 (20%)
        download_count = int(total_requests * 0.2)
        requests_config.extend(self.generate_test_requests('/download/test-id', 'GET', download_count))

        # PPT生成请求 (10%)
        generate_count = total_requests - status_count - options_count - download_count
        generate_data = {
            "topic": "并发测试主题",
            "page_count": 5,
            "style": "professional"
        }
        requests_config.extend(self.generate_test_requests('/generate', 'POST', generate_count, generate_data))

        # 随机打乱请求顺序
        random.shuffle(requests_config)

        results = await self.run_concurrent_requests(requests_config, min(20, total_requests))

        return self.analyze_results(results, f"混合并发请求 ({total_requests}个请求)")

    async def test_load_with_ramp_up(self, max_concurrent: int = 50,
                                   ramp_up_duration: int = 30) -> List[LoadTestSummary]:
        """负载递增测试"""
        logger.info(f"开始负载递增测试 (最大{max_concurrent}并发，递增时间{ramp_up_duration}秒)")

        summaries = []
        step_count = 5
        step_duration = ramp_up_duration // step_count

        for step in range(1, step_count + 1):
            concurrent_count = int((step / step_count) * max_concurrent)
            concurrent_count = max(1, concurrent_count)

            logger.info(f"负载步骤 {step}/{step_count}: {concurrent_count}个并发请求")

            # 创建状态查询请求
            requests_config = self.generate_test_requests('/status/test-id', 'GET', concurrent_count)
            results = await self.run_concurrent_requests(requests_config, concurrent_count)

            summary = self.analyze_results(results, f"负载步骤{step} ({concurrent_count}并发)")
            summaries.append(summary)

            logger.info(f"步骤{step}结果: 成功率{summary.success_rate:.1f}%, "
                       f"平均响应时间{summary.avg_response_time_ms:.0f}ms")

            # 步骤间延迟
            if step < step_count:
                await asyncio.sleep(step_duration)

        return summaries

    async def test_sustained_load(self, concurrent_count: int = 20,
                                 duration_seconds: int = 60) -> List[LoadTestSummary]:
        """持续负载测试"""
        logger.info(f"开始持续负载测试 ({concurrent_count}并发，持续{duration_seconds}秒)")

        summaries = []
        start_time = time.time()
        round_number = 1

        while time.time() - start_time < duration_seconds:
            remaining_time = duration_seconds - (time.time() - start_time)
            current_requests = min(concurrent_count, max(1, int(remaining_time / 2)))

            logger.info(f"持续负载轮次{round_number}: {current_requests}个请求")

            requests_config = self.generate_test_requests('/status/test-id', 'GET', current_requests)
            results = await self.run_concurrent_requests(requests_config, current_requests)

            summary = self.analyze_results(results, f"持续负载轮次{round_number} ({current_requests}请求)")
            summaries.append(summary)

            logger.info(f"轮次{round_number}结果: 成功率{summary.success_rate:.1f}%, "
                       f"RPS{summary.requests_per_second:.1f}")

            round_number += 1

            # 短暂延迟
            await asyncio.sleep(1)

        return summaries

    def save_results(self, summaries: List[LoadTestSummary],
                    filename: str = None) -> str:
        """保存测试结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"concurrent_test_results_{timestamp}.json"

        report_data = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'api_endpoint': self.base_url,
                'total_test_scenarios': len(summaries)
            },
            'test_summaries': [asdict(summary) for summary in summaries],
            'overall_analysis': self._analyze_overall_performance(summaries)
        }

        import os
        os.makedirs("test_results", exist_ok=True)
        filepath = os.path.join("test_results", filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"测试结果已保存到: {filepath}")
        return filepath

    def _analyze_overall_performance(self, summaries: List[LoadTestSummary]) -> Dict[str, Any]:
        """分析整体性能"""
        if not summaries:
            return {}

        total_requests = sum(s.total_requests for s in summaries)
        total_successful = sum(s.successful_requests for s in summaries)
        overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0

        avg_response_times = [s.avg_response_time_ms for s in summaries if s.avg_response_time_ms > 0]
        overall_avg_response_time = statistics.mean(avg_response_times) if avg_response_times else 0

        max_rps = max(s.requests_per_second for s in summaries) if summaries else 0

        # 性能评级
        performance_grade = "A"
        issues = []

        if overall_success_rate < 95:
            performance_grade = "C"
            issues.append(f"成功率较低: {overall_success_rate:.1f}%")

        if overall_avg_response_time > 5000:
            performance_grade = "D" if performance_grade in ["A", "B"] else performance_grade
            issues.append(f"平均响应时间过长: {overall_avg_response_time:.0f}ms")
        elif overall_avg_response_time > 2000:
            performance_grade = "B" if performance_grade == "A" else performance_grade
            issues.append(f"响应时间较长: {overall_avg_response_time:.0f}ms")

        recommendations = []

        if overall_success_rate < 99:
            recommendations.append("调查请求失败原因，检查错误日志")

        if overall_avg_response_time > 1000:
            recommendations.append("考虑性能优化，如添加缓存、数据库优化等")

        if max_rps < 10:
            recommendations.append("API吞吐量较低，考虑扩展服务器资源")

        recommendations.extend([
            "监控生产环境中的实际负载模式",
            "设置性能告警阈值",
            "定期进行负载测试以发现性能回归"
        ])

        return {
            'overall_success_rate': overall_success_rate,
            'overall_avg_response_time_ms': overall_avg_response_time,
            'max_requests_per_second': max_rps,
            'performance_grade': performance_grade,
            'identified_issues': issues,
            'recommendations': recommendations
        }

async def main():
    parser = argparse.ArgumentParser(description='AI PPT API 并发负载测试')
    parser.add_argument('--url', default='https://fe2kf91287.execute-api.us-east-1.amazonaws.com/dev',
                       help='API基础URL')
    parser.add_argument('--timeout', type=int, default=30, help='请求超时时间（秒）')
    parser.add_argument('--concurrent-basic', type=int, default=20, help='基本并发测试数量')
    parser.add_argument('--concurrent-mixed', type=int, default=30, help='混合并发测试数量')
    parser.add_argument('--load-max', type=int, default=50, help='负载递增测试最大并发数')
    parser.add_argument('--sustained-concurrent', type=int, default=20, help='持续负载测试并发数')
    parser.add_argument('--sustained-duration', type=int, default=60, help='持续负载测试时长（秒）')
    parser.add_argument('--skip-sustained', action='store_true', help='跳过持续负载测试')
    parser.add_argument('--output', help='结果输出文件名')

    args = parser.parse_args()

    tester = ConcurrentAPITester(args.url, args.timeout)

    try:
        all_summaries = []

        # 基本并发测试
        logger.info("=" * 60)
        logger.info("开始基本并发测试")
        logger.info("=" * 60)

        # 状态查询并发测试
        summary = await tester.test_concurrent_status_requests(args.concurrent_basic)
        all_summaries.append(summary)

        # OPTIONS预检并发测试
        summary = await tester.test_concurrent_options_requests(15)
        all_summaries.append(summary)

        # 下载请求并发测试
        summary = await tester.test_concurrent_download_requests(10)
        all_summaries.append(summary)

        # 混合并发测试
        logger.info("=" * 60)
        logger.info("开始混合并发测试")
        logger.info("=" * 60)

        summary = await tester.test_mixed_concurrent_requests(args.concurrent_mixed)
        all_summaries.append(summary)

        # 负载递增测试
        logger.info("=" * 60)
        logger.info("开始负载递增测试")
        logger.info("=" * 60)

        ramp_summaries = await tester.test_load_with_ramp_up(args.load_max, 30)
        all_summaries.extend(ramp_summaries)

        # 持续负载测试（可选）
        if not args.skip_sustained:
            logger.info("=" * 60)
            logger.info("开始持续负载测试")
            logger.info("=" * 60)

            sustained_summaries = await tester.test_sustained_load(
                args.sustained_concurrent, args.sustained_duration
            )
            all_summaries.extend(sustained_summaries)

        # 保存结果
        result_file = tester.save_results(all_summaries, args.output)

        # 输出摘要
        logger.info("=" * 60)
        logger.info("并发负载测试完成")
        logger.info("=" * 60)

        for summary in all_summaries[-3:]:  # 显示最后几个测试的结果
            print(f"\n{summary.test_name}:")
            print(f"  总请求数: {summary.total_requests}")
            print(f"  成功率: {summary.success_rate:.1f}%")
            print(f"  平均响应时间: {summary.avg_response_time_ms:.0f}ms")
            print(f"  RPS: {summary.requests_per_second:.1f}")

        print(f"\n详细结果已保存到: {result_file}")

    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"测试运行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())