#!/usr/bin/env python3
"""
性能测试运行脚本
执行全面的性能测试并生成报告
"""

import sys
import os
import time
import json
import asyncio
import argparse
from datetime import datetime
from typing import Dict, Any, List

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tests'))

from lambdas.image_processing_service_v3 import ImageProcessingServiceV3, ImageRequest
from lambdas.cloudwatch_monitoring import CloudWatchMonitor, init_monitoring
from tests.test_performance_v3 import PerformanceBenchmark
import boto3
from botocore.exceptions import ClientError


class PerformanceTestRunner:
    """性能测试运行器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = {}
        self.service = None
        self.monitor = None

    def setup(self):
        """设置测试环境"""
        print("🔧 设置测试环境...")

        # 初始化服务
        if self.config.get('use_real_api'):
            bedrock_client = boto3.client('bedrock-runtime')
            s3_client = boto3.client('s3')
            cloudwatch_client = boto3.client('cloudwatch')
        else:
            # 使用模拟客户端
            from unittest.mock import Mock, MagicMock
            bedrock_client = self._create_mock_bedrock_client()
            s3_client = Mock()
            cloudwatch_client = Mock()

        self.service = ImageProcessingServiceV3(
            bedrock_client=bedrock_client,
            s3_client=s3_client,
            cloudwatch_client=cloudwatch_client,
            enable_caching=self.config.get('enable_cache', True),
            enable_metrics=self.config.get('enable_metrics', True),
            max_workers=self.config.get('max_workers', 10)
        )

        # 初始化监控
        if self.config.get('enable_monitoring'):
            self.monitor = init_monitoring(
                namespace="AI-PPT-Assistant-Test",
                setup_alarms=False
            )

        print("✅ 环境设置完成")

    def _create_mock_bedrock_client(self):
        """创建模拟的Bedrock客户端"""
        from unittest.mock import Mock, MagicMock

        client = Mock()

        def mock_invoke_model(**kwargs):
            # 模拟延迟
            import time
            time.sleep(0.1)

            # 返回模拟响应
            return {
                'body': MagicMock(
                    read=lambda: json.dumps({
                        'images': ['mock_base64_image_data']
                    })
                )
            }

        client.invoke_model = mock_invoke_model
        return client

    async def run_single_request_test(self, iterations: int = 10) -> Dict[str, Any]:
        """运行单请求测试"""
        print(f"\n📊 运行单请求测试 ({iterations} 次迭代)...")

        benchmark = PerformanceBenchmark()
        times = []

        for i in range(iterations):
            request = ImageRequest(
                prompt=f"高质量商务演示背景 测试{i}",
                priority=1
            )

            start = time.perf_counter()
            response = await self.service._generate_single_async(request)
            elapsed = time.perf_counter() - start

            times.append(elapsed)
            print(f"  迭代 {i+1}/{iterations}: {elapsed:.3f}秒")

        # 计算统计
        import statistics
        stats = {
            'test_name': 'single_request',
            'iterations': iterations,
            'mean_time': statistics.mean(times),
            'median_time': statistics.median(times),
            'min_time': min(times),
            'max_time': max(times),
            'std_dev': statistics.stdev(times) if len(times) > 1 else 0
        }

        print(f"✅ 单请求测试完成: 平均 {stats['mean_time']:.3f}秒")
        return stats

    async def run_batch_test(self, batch_size: int = 10) -> Dict[str, Any]:
        """运行批处理测试"""
        print(f"\n📊 运行批处理测试 (批大小: {batch_size})...")

        requests = [
            ImageRequest(
                prompt=f"批处理测试图片 {i}",
                priority=i % 3
            )
            for i in range(batch_size)
        ]

        start = time.perf_counter()
        responses = await self.service.generate_images_batch(requests)
        elapsed = time.perf_counter() - start

        # 统计成功和失败
        successful = sum(1 for r in responses if r.from_cache or r.model_used != "placeholder")

        stats = {
            'test_name': 'batch_processing',
            'batch_size': batch_size,
            'total_time': elapsed,
            'avg_time_per_image': elapsed / batch_size,
            'successful': successful,
            'failed': batch_size - successful,
            'success_rate': successful / batch_size
        }

        print(f"✅ 批处理测试完成: {batch_size}张图片耗时 {elapsed:.2f}秒")
        return stats

    async def run_concurrent_test(self, concurrent_requests: int = 20) -> Dict[str, Any]:
        """运行并发测试"""
        print(f"\n📊 运行并发测试 ({concurrent_requests} 个并发请求)...")

        async def make_request(index: int):
            request = ImageRequest(
                prompt=f"并发测试 {index}",
                priority=index % 5
            )
            start = time.perf_counter()
            try:
                response = await self.service._generate_single_async(request)
                return time.perf_counter() - start, True
            except Exception as e:
                return time.perf_counter() - start, False

        # 创建并发任务
        tasks = [make_request(i) for i in range(concurrent_requests)]

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start

        # 分析结果
        times = [r[0] for r in results]
        successful = sum(1 for r in results if r[1])

        import statistics
        stats = {
            'test_name': 'concurrent_requests',
            'concurrent_count': concurrent_requests,
            'total_time': total_time,
            'mean_response_time': statistics.mean(times),
            'max_response_time': max(times),
            'successful': successful,
            'failed': concurrent_requests - successful,
            'success_rate': successful / concurrent_requests,
            'throughput': concurrent_requests / total_time
        }

        print(f"✅ 并发测试完成: {concurrent_requests}个请求耗时 {total_time:.2f}秒")
        print(f"   吞吐量: {stats['throughput']:.2f} req/s")
        return stats

    async def run_cache_test(self) -> Dict[str, Any]:
        """运行缓存测试"""
        print("\n📊 运行缓存性能测试...")

        # 使用相同的提示词测试缓存
        prompt = "缓存测试专用提示词"
        request = ImageRequest(prompt=prompt)

        # 第一次请求（冷缓存）
        start = time.perf_counter()
        response1 = await self.service._generate_single_async(request)
        cold_time = time.perf_counter() - start

        # 第二次请求（热缓存）
        start = time.perf_counter()
        response2 = await self.service._generate_single_async(request)
        hot_time = time.perf_counter() - start

        # 批量缓存测试
        cache_hits = 0
        for i in range(10):
            response = await self.service._generate_single_async(request)
            if response.from_cache:
                cache_hits += 1

        stats = {
            'test_name': 'cache_performance',
            'cold_cache_time': cold_time,
            'hot_cache_time': hot_time,
            'speedup': cold_time / hot_time if hot_time > 0 else 0,
            'cache_hit_rate': cache_hits / 10,
            'cache_stats': self.service.cache_manager.get_stats()
        }

        print(f"✅ 缓存测试完成:")
        print(f"   冷缓存: {cold_time:.3f}秒")
        print(f"   热缓存: {hot_time:.3f}秒")
        print(f"   加速比: {stats['speedup']:.2f}x")
        print(f"   命中率: {stats['cache_hit_rate']*100:.1f}%")

        return stats

    async def run_stress_test(self, duration: int = 30) -> Dict[str, Any]:
        """运行压力测试"""
        print(f"\n📊 运行压力测试 (持续 {duration} 秒)...")

        start_time = time.time()
        request_count = 0
        successful = 0
        failed = 0
        response_times = []

        while time.time() - start_time < duration:
            request = ImageRequest(
                prompt=f"压力测试 {request_count}",
                priority=request_count % 3
            )

            req_start = time.perf_counter()
            try:
                response = await self.service._generate_single_async(request)
                successful += 1
            except Exception as e:
                failed += 1

            response_times.append(time.perf_counter() - req_start)
            request_count += 1

            # 控制请求速率
            await asyncio.sleep(0.1)

        elapsed = time.time() - start_time

        import statistics
        stats = {
            'test_name': 'stress_test',
            'duration': elapsed,
            'total_requests': request_count,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / request_count if request_count > 0 else 0,
            'throughput': request_count / elapsed,
            'mean_response_time': statistics.mean(response_times),
            'p95_response_time': statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
            'p99_response_time': statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times)
        }

        print(f"✅ 压力测试完成:")
        print(f"   总请求: {request_count}")
        print(f"   成功率: {stats['success_rate']*100:.1f}%")
        print(f"   吞吐量: {stats['throughput']:.2f} req/s")
        print(f"   P95延迟: {stats['p95_response_time']:.3f}秒")

        return stats

    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("\n🚀 开始性能测试套件\n")
        print("=" * 50)

        all_results = {}

        # 单请求测试
        all_results['single_request'] = await self.run_single_request_test(
            iterations=self.config.get('single_iterations', 10)
        )

        # 批处理测试
        all_results['batch_processing'] = await self.run_batch_test(
            batch_size=self.config.get('batch_size', 10)
        )

        # 并发测试
        all_results['concurrent'] = await self.run_concurrent_test(
            concurrent_requests=self.config.get('concurrent_requests', 20)
        )

        # 缓存测试
        all_results['cache'] = await self.run_cache_test()

        # 压力测试（可选）
        if self.config.get('run_stress_test', False):
            all_results['stress'] = await self.run_stress_test(
                duration=self.config.get('stress_duration', 30)
            )

        # 获取服务统计
        all_results['service_stats'] = self.service.get_performance_stats()

        print("\n" + "=" * 50)
        print("✅ 所有测试完成!")

        return all_results

    def generate_report(self, results: Dict[str, Any], output_file: str):
        """生成测试报告"""
        print(f"\n📝 生成测试报告: {output_file}")

        report = {
            'timestamp': datetime.now().isoformat(),
            'config': self.config,
            'results': results,
            'summary': self._generate_summary(results)
        }

        # 保存JSON报告
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # 生成HTML报告
        html_file = output_file.replace('.json', '.html')
        self._generate_html_report(report, html_file)

        print(f"✅ 报告已生成:")
        print(f"   JSON: {output_file}")
        print(f"   HTML: {html_file}")

    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成测试摘要"""
        summary = {
            'overall_performance': 'PASS',
            'key_metrics': {},
            'recommendations': []
        }

        # 分析单请求性能
        if 'single_request' in results:
            avg_time = results['single_request']['mean_time']
            summary['key_metrics']['avg_response_time'] = f"{avg_time:.3f}s"

            if avg_time > 2:
                summary['overall_performance'] = 'NEEDS_IMPROVEMENT'
                summary['recommendations'].append("单请求响应时间超过2秒，建议优化模型调用")

        # 分析缓存性能
        if 'cache' in results:
            hit_rate = results['cache']['cache_hit_rate']
            summary['key_metrics']['cache_hit_rate'] = f"{hit_rate*100:.1f}%"

            if hit_rate < 0.6:
                summary['recommendations'].append("缓存命中率低于60%，建议增加缓存容量或优化缓存键")

        # 分析并发性能
        if 'concurrent' in results:
            throughput = results['concurrent']['throughput']
            summary['key_metrics']['throughput'] = f"{throughput:.2f} req/s"

            if throughput < 10:
                summary['recommendations'].append("吞吐量低于10 req/s，建议增加并发处理能力")

        return summary

    def _generate_html_report(self, report: Dict[str, Any], output_file: str):
        """生成HTML报告"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>性能测试报告 - {report['timestamp']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ background: white; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #3498db; }}
        .metric-label {{ color: #7f8c8d; margin-top: 5px; }}
        .test-result {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .pass {{ color: #27ae60; }}
        .fail {{ color: #e74c3c; }}
        .recommendation {{ background: #fff3cd; padding: 10px; margin: 5px 0; border-left: 4px solid #ffc107; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #ecf0f1; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI-PPT-Assistant 性能测试报告</h1>
        <p>生成时间: {report['timestamp']}</p>
    </div>

    <div class="summary">
        <h2>测试摘要</h2>
        <div>
            <div class="metric">
                <div class="metric-value">{report['summary']['key_metrics'].get('avg_response_time', 'N/A')}</div>
                <div class="metric-label">平均响应时间</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report['summary']['key_metrics'].get('cache_hit_rate', 'N/A')}</div>
                <div class="metric-label">缓存命中率</div>
            </div>
            <div class="metric">
                <div class="metric-value">{report['summary']['key_metrics'].get('throughput', 'N/A')}</div>
                <div class="metric-label">吞吐量</div>
            </div>
        </div>
    </div>

    <div class="summary">
        <h2>测试结果</h2>
        {self._format_test_results_html(report['results'])}
    </div>

    <div class="summary">
        <h2>优化建议</h2>
        {''.join([f'<div class="recommendation">{r}</div>' for r in report['summary']['recommendations']])}
    </div>
</body>
</html>
"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _format_test_results_html(self, results: Dict[str, Any]) -> str:
        """格式化测试结果为HTML"""
        html = ""

        for test_name, test_data in results.items():
            if isinstance(test_data, dict) and 'test_name' in test_data:
                html += f"""
                <div class="test-result">
                    <h3>{test_data['test_name']}</h3>
                    <table>
                """
                for key, value in test_data.items():
                    if key != 'test_name':
                        if isinstance(value, float):
                            value = f"{value:.3f}"
                        html += f"<tr><td>{key}</td><td>{value}</td></tr>"

                html += """
                    </table>
                </div>
                """

        return html

    def cleanup(self):
        """清理资源"""
        if self.service:
            self.service.cleanup()
        if self.monitor:
            self.monitor.shutdown()
        print("✅ 资源清理完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='运行AI-PPT-Assistant性能测试')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--output', type=str, default=f'performance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                       help='输出报告文件')
    parser.add_argument('--use-real-api', action='store_true', help='使用真实API而非模拟')
    parser.add_argument('--run-stress', action='store_true', help='运行压力测试')
    parser.add_argument('--iterations', type=int, default=10, help='单请求测试迭代次数')
    parser.add_argument('--batch-size', type=int, default=10, help='批处理大小')
    parser.add_argument('--concurrent', type=int, default=20, help='并发请求数')

    args = parser.parse_args()

    # 加载或创建配置
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        config = {
            'use_real_api': args.use_real_api,
            'enable_cache': True,
            'enable_metrics': True,
            'enable_monitoring': False,
            'max_workers': 10,
            'single_iterations': args.iterations,
            'batch_size': args.batch_size,
            'concurrent_requests': args.concurrent,
            'run_stress_test': args.run_stress,
            'stress_duration': 30
        }

    # 创建测试运行器
    runner = PerformanceTestRunner(config)

    try:
        # 设置环境
        runner.setup()

        # 运行测试
        results = asyncio.run(runner.run_all_tests())

        # 生成报告
        runner.generate_report(results, args.output)

        # 打印摘要
        print("\n" + "=" * 50)
        print("📊 性能测试摘要")
        print("=" * 50)

        if 'single_request' in results:
            print(f"平均响应时间: {results['single_request']['mean_time']:.3f}秒")

        if 'cache' in results:
            print(f"缓存加速: {results['cache']['speedup']:.2f}x")
            print(f"缓存命中率: {results['cache']['cache_hit_rate']*100:.1f}%")

        if 'concurrent' in results:
            print(f"并发吞吐量: {results['concurrent']['throughput']:.2f} req/s")
            print(f"并发成功率: {results['concurrent']['success_rate']*100:.1f}%")

    finally:
        # 清理资源
        runner.cleanup()


if __name__ == "__main__":
    main()