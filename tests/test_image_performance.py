#!/usr/bin/env python3
"""
图片生成服务性能测试脚本
包含基准测试、负载测试、并发测试等
"""

import asyncio
import json
import time
import statistics
import random
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any, Tuple
import sys
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass, asdict
import boto3
from botocore.exceptions import ClientError

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas'))

from image_processing_service_optimized import (
    ImageProcessingServiceOptimized,
    ImageRequest,
    ImageResponse
)


@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    request_id: str
    prompt: str
    model_used: str
    generation_time: float
    from_cache: bool
    success: bool
    error_message: str = ""
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    cache_hits: int
    min_time: float
    max_time: float
    avg_time: float
    median_time: float
    p95_time: float
    p99_time: float
    throughput: float
    error_rate: float
    cache_hit_rate: float


class ImagePerformanceTester:
    """图片生成服务性能测试器"""

    def __init__(self, service: ImageProcessingServiceOptimized = None):
        """初始化测试器"""
        self.service = service or ImageProcessingServiceOptimized(
            enable_monitoring=True,
            enable_caching=True,
            enable_batching=True
        )
        self.test_results: List[TestResult] = []
        self.test_prompts = self._generate_test_prompts()

    def _generate_test_prompts(self) -> List[str]:
        """生成测试提示词"""
        base_prompts = [
            "专业商务演示背景，现代科技风格，蓝色主题",
            "数据分析仪表板，可视化图表，深色背景",
            "团队协作场景，办公室环境，温暖色调",
            "人工智能概念图，未来科技，抽象艺术",
            "云计算架构图，技术示意，清晰结构",
            "市场营销策略，创意设计，鲜艳色彩",
            "金融数据展示，专业图表，绿色上涨趋势",
            "教育培训场景，互动学习，明亮环境",
            "医疗健康主题，清洁简约，蓝白配色",
            "电子商务平台，购物界面，现代设计"
        ]

        # 生成变体
        prompts = []
        for base in base_prompts:
            prompts.append(base)
            prompts.append(f"{base}，4K高清，专业摄影")
            prompts.append(f"{base}，极简主义，扁平设计")

        return prompts

    async def test_single_request(self, prompt: str, test_name: str = "single") -> TestResult:
        """测试单个请求"""
        request = ImageRequest(
            prompt=prompt,
            request_id=f"test_{test_name}_{int(time.time() * 1000)}",
            priority=5
        )

        start_time = time.time()
        try:
            response = await self.service.generate_image_async(request)
            generation_time = time.time() - start_time

            result = TestResult(
                test_name=test_name,
                request_id=request.request_id,
                prompt=prompt,
                model_used=response.model_used,
                generation_time=generation_time,
                from_cache=response.from_cache,
                success=True
            )

        except Exception as e:
            generation_time = time.time() - start_time
            result = TestResult(
                test_name=test_name,
                request_id=request.request_id,
                prompt=prompt,
                model_used="error",
                generation_time=generation_time,
                from_cache=False,
                success=False,
                error_message=str(e)
            )

        self.test_results.append(result)
        return result

    async def test_concurrent_requests(self, num_requests: int = 10) -> List[TestResult]:
        """测试并发请求"""
        print(f"\n🔄 开始并发测试 ({num_requests} 个请求)...")

        tasks = []
        for i in range(num_requests):
            prompt = random.choice(self.test_prompts)
            task = self.test_single_request(prompt, f"concurrent_{i}")
            tasks.append(task)

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        successful = sum(1 for r in results if r.success)
        print(f"✅ 并发测试完成: {successful}/{num_requests} 成功")
        print(f"⏱️  总耗时: {total_time:.2f}秒")
        print(f"📊 吞吐量: {num_requests / total_time:.2f} 请求/秒")

        return results

    def test_sequential_requests(self, num_requests: int = 10) -> List[TestResult]:
        """测试顺序请求"""
        print(f"\n🔄 开始顺序测试 ({num_requests} 个请求)...")

        results = []
        start_time = time.time()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for i in range(num_requests):
            prompt = random.choice(self.test_prompts)
            result = loop.run_until_complete(
                self.test_single_request(prompt, f"sequential_{i}")
            )
            results.append(result)
            print(f"  请求 {i+1}/{num_requests} 完成 - "
                  f"{'✅ 成功' if result.success else '❌ 失败'} "
                  f"({result.generation_time:.2f}秒)")

        total_time = time.time() - start_time
        loop.close()

        successful = sum(1 for r in results if r.success)
        print(f"✅ 顺序测试完成: {successful}/{num_requests} 成功")
        print(f"⏱️  总耗时: {total_time:.2f}秒")

        return results

    def test_cache_performance(self) -> Dict[str, Any]:
        """测试缓存性能"""
        print("\n🔄 开始缓存性能测试...")

        # 使用相同的提示词测试缓存
        test_prompt = "缓存测试：专业商务演示背景，高质量4K"
        results = []

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 第一次请求（冷缓存）
        print("  测试冷缓存...")
        cold_result = loop.run_until_complete(
            self.test_single_request(test_prompt, "cache_cold")
        )
        results.append(cold_result)

        # 后续请求（热缓存）
        print("  测试热缓存...")
        for i in range(5):
            hot_result = loop.run_until_complete(
                self.test_single_request(test_prompt, f"cache_hot_{i}")
            )
            results.append(hot_result)

        loop.close()

        # 分析结果
        cold_time = cold_result.generation_time
        hot_times = [r.generation_time for r in results[1:]]
        avg_hot_time = statistics.mean(hot_times)

        speedup = cold_time / avg_hot_time if avg_hot_time > 0 else 0
        cache_hits = sum(1 for r in results if r.from_cache)

        print(f"✅ 缓存测试完成:")
        print(f"  冷缓存时间: {cold_time:.2f}秒")
        print(f"  热缓存平均时间: {avg_hot_time:.2f}秒")
        print(f"  加速比: {speedup:.2f}x")
        print(f"  缓存命中: {cache_hits}/{len(results)}")

        return {
            'cold_time': cold_time,
            'avg_hot_time': avg_hot_time,
            'speedup': speedup,
            'cache_hits': cache_hits,
            'total_requests': len(results)
        }

    async def test_load_pattern(self,
                               pattern: str = "steady",
                               duration: int = 60,
                               base_rps: float = 1.0) -> List[TestResult]:
        """
        测试不同负载模式

        Args:
            pattern: 负载模式 (steady, spike, gradual)
            duration: 测试持续时间（秒）
            base_rps: 基础请求速率（请求/秒）
        """
        print(f"\n🔄 开始负载模式测试 (模式: {pattern}, 持续: {duration}秒)...")

        results = []
        start_time = time.time()
        current_time = 0

        while current_time < duration:
            # 根据模式计算当前RPS
            if pattern == "steady":
                current_rps = base_rps
            elif pattern == "spike":
                # 在中间产生尖峰
                if duration * 0.4 < current_time < duration * 0.6:
                    current_rps = base_rps * 5
                else:
                    current_rps = base_rps
            elif pattern == "gradual":
                # 逐渐增加
                current_rps = base_rps * (1 + current_time / duration * 2)
            else:
                current_rps = base_rps

            # 计算这一秒需要发送的请求数
            requests_this_second = int(current_rps)

            # 发送请求
            tasks = []
            for _ in range(requests_this_second):
                prompt = random.choice(self.test_prompts)
                task = self.test_single_request(
                    prompt,
                    f"load_{pattern}_{int(current_time)}"
                )
                tasks.append(task)

            if tasks:
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)

            # 等待到下一秒
            await asyncio.sleep(1)
            current_time = time.time() - start_time

        print(f"✅ 负载测试完成: 共发送 {len(results)} 个请求")
        return results

    def test_model_fallback(self) -> Dict[str, Any]:
        """测试模型故障转移"""
        print("\n🔄 开始模型故障转移测试...")

        # 暂时禁用主模型以测试fallback
        original_models = self.service.model_configs.copy()

        # 模拟Nova模型失败
        if "amazon.nova-canvas-v1:0" in self.service.model_configs:
            self.service.model_configs["amazon.nova-canvas-v1:0"].last_failure_time = datetime.now()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 测试fallback
        result = loop.run_until_complete(
            self.test_single_request(
                "测试故障转移：专业演示背景",
                "model_fallback"
            )
        )

        # 恢复配置
        self.service.model_configs = original_models
        loop.close()

        print(f"✅ 故障转移测试完成:")
        print(f"  使用模型: {result.model_used}")
        print(f"  请求{'成功' if result.success else '失败'}")
        print(f"  耗时: {result.generation_time:.2f}秒")

        return {
            'success': result.success,
            'model_used': result.model_used,
            'generation_time': result.generation_time
        }

    def calculate_metrics(self, results: List[TestResult]) -> PerformanceMetrics:
        """计算性能指标"""
        if not results:
            return None

        successful_results = [r for r in results if r.success]
        times = [r.generation_time for r in successful_results]

        if not times:
            times = [0]

        sorted_times = sorted(times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)

        metrics = PerformanceMetrics(
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(results) - len(successful_results),
            cache_hits=sum(1 for r in results if r.from_cache),
            min_time=min(times) if times else 0,
            max_time=max(times) if times else 0,
            avg_time=statistics.mean(times) if times else 0,
            median_time=statistics.median(times) if times else 0,
            p95_time=sorted_times[p95_index] if p95_index < len(sorted_times) else 0,
            p99_time=sorted_times[p99_index] if p99_index < len(sorted_times) else 0,
            throughput=len(results) / sum(times) if sum(times) > 0 else 0,
            error_rate=(len(results) - len(successful_results)) / len(results) * 100,
            cache_hit_rate=sum(1 for r in results if r.from_cache) / len(results) * 100
        )

        return metrics

    def generate_report(self, output_dir: str = "performance_reports"):
        """生成性能测试报告"""
        os.makedirs(output_dir, exist_ok=True)

        # 计算总体指标
        metrics = self.calculate_metrics(self.test_results)

        # 生成文本报告
        report_path = os.path.join(output_dir, f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("AI-PPT-Assistant 图片生成服务性能测试报告\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总请求数: {metrics.total_requests}\n")
            f.write(f"成功请求: {metrics.successful_requests}\n")
            f.write(f"失败请求: {metrics.failed_requests}\n\n")

            f.write("性能指标:\n")
            f.write(f"  最小响应时间: {metrics.min_time:.3f}秒\n")
            f.write(f"  最大响应时间: {metrics.max_time:.3f}秒\n")
            f.write(f"  平均响应时间: {metrics.avg_time:.3f}秒\n")
            f.write(f"  中位数响应时间: {metrics.median_time:.3f}秒\n")
            f.write(f"  P95响应时间: {metrics.p95_time:.3f}秒\n")
            f.write(f"  P99响应时间: {metrics.p99_time:.3f}秒\n\n")

            f.write(f"吞吐量: {metrics.throughput:.2f} 请求/秒\n")
            f.write(f"错误率: {metrics.error_rate:.2f}%\n")
            f.write(f"缓存命中率: {metrics.cache_hit_rate:.2f}%\n\n")

            # 按测试类型分组统计
            test_types = {}
            for result in self.test_results:
                test_type = result.test_name.split('_')[0]
                if test_type not in test_types:
                    test_types[test_type] = []
                test_types[test_type].append(result)

            f.write("按测试类型统计:\n")
            for test_type, type_results in test_types.items():
                type_metrics = self.calculate_metrics(type_results)
                f.write(f"\n  {test_type}:\n")
                f.write(f"    请求数: {type_metrics.total_requests}\n")
                f.write(f"    成功率: {(type_metrics.successful_requests/type_metrics.total_requests*100):.2f}%\n")
                f.write(f"    平均时间: {type_metrics.avg_time:.3f}秒\n")

        print(f"✅ 文本报告已生成: {report_path}")

        # 生成图表
        self.generate_charts(output_dir, metrics)

        # 生成JSON报告
        json_path = os.path.join(output_dir, f"performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(json_path, 'w') as f:
            json.dump(asdict(metrics), f, indent=2, default=str)

        print(f"✅ JSON报告已生成: {json_path}")

    def generate_charts(self, output_dir: str, metrics: PerformanceMetrics):
        """生成性能图表"""
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))

        # 1. 响应时间分布
        times = [r.generation_time for r in self.test_results if r.success]
        axes[0, 0].hist(times, bins=20, edgecolor='black')
        axes[0, 0].set_title('响应时间分布')
        axes[0, 0].set_xlabel('时间 (秒)')
        axes[0, 0].set_ylabel('频次')
        axes[0, 0].axvline(metrics.avg_time, color='red', linestyle='--', label=f'平均: {metrics.avg_time:.2f}s')
        axes[0, 0].axvline(metrics.p95_time, color='orange', linestyle='--', label=f'P95: {metrics.p95_time:.2f}s')
        axes[0, 0].legend()

        # 2. 时间序列图
        timestamps = [r.timestamp for r in self.test_results]
        response_times = [r.generation_time for r in self.test_results]
        axes[0, 1].plot(timestamps, response_times, 'b-', alpha=0.5)
        axes[0, 1].scatter(timestamps, response_times, c=['green' if r.success else 'red' for r in self.test_results], s=10)
        axes[0, 1].set_title('响应时间趋势')
        axes[0, 1].set_xlabel('时间')
        axes[0, 1].set_ylabel('响应时间 (秒)')
        axes[0, 1].tick_params(axis='x', rotation=45)

        # 3. 成功率饼图
        success_data = [metrics.successful_requests, metrics.failed_requests]
        labels = ['成功', '失败']
        colors = ['#2ecc71', '#e74c3c']
        axes[0, 2].pie(success_data, labels=labels, colors=colors, autopct='%1.1f%%')
        axes[0, 2].set_title('请求成功率')

        # 4. 缓存命中率
        cache_data = [metrics.cache_hits, metrics.total_requests - metrics.cache_hits]
        labels = ['缓存命中', '缓存未命中']
        colors = ['#3498db', '#95a5a6']
        axes[1, 0].pie(cache_data, labels=labels, colors=colors, autopct='%1.1f%%')
        axes[1, 0].set_title('缓存命中率')

        # 5. 模型使用分布
        model_usage = {}
        for r in self.test_results:
            if r.model_used not in model_usage:
                model_usage[r.model_used] = 0
            model_usage[r.model_used] += 1

        axes[1, 1].bar(model_usage.keys(), model_usage.values())
        axes[1, 1].set_title('模型使用分布')
        axes[1, 1].set_xlabel('模型')
        axes[1, 1].set_ylabel('使用次数')
        axes[1, 1].tick_params(axis='x', rotation=45)

        # 6. 性能指标对比
        metrics_data = {
            'Min': metrics.min_time,
            'Avg': metrics.avg_time,
            'Median': metrics.median_time,
            'P95': metrics.p95_time,
            'P99': metrics.p99_time,
            'Max': metrics.max_time
        }
        axes[1, 2].bar(metrics_data.keys(), metrics_data.values(), color='skyblue')
        axes[1, 2].set_title('响应时间指标')
        axes[1, 2].set_xlabel('指标')
        axes[1, 2].set_ylabel('时间 (秒)')

        plt.suptitle('AI-PPT-Assistant 图片生成服务性能分析', fontsize=16)
        plt.tight_layout()

        chart_path = os.path.join(output_dir, f"performance_charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"✅ 性能图表已生成: {chart_path}")


async def run_comprehensive_test():
    """运行全面的性能测试"""
    print("🚀 开始AI-PPT-Assistant图片生成服务性能测试")
    print("=" * 60)

    tester = ImagePerformanceTester()

    # 1. 基准测试
    print("\n📊 1. 基准测试")
    baseline_results = tester.test_sequential_requests(5)

    # 2. 并发测试
    print("\n📊 2. 并发测试")
    concurrent_results = await tester.test_concurrent_requests(20)

    # 3. 缓存测试
    print("\n📊 3. 缓存性能测试")
    cache_results = tester.test_cache_performance()

    # 4. 负载模式测试
    print("\n📊 4. 负载模式测试")
    print("  4.1 稳定负载")
    steady_results = await tester.test_load_pattern("steady", 30, 2.0)

    print("  4.2 尖峰负载")
    spike_results = await tester.test_load_pattern("spike", 30, 1.0)

    print("  4.3 渐进负载")
    gradual_results = await tester.test_load_pattern("gradual", 30, 1.0)

    # 5. 故障转移测试
    print("\n📊 5. 模型故障转移测试")
    fallback_results = tester.test_model_fallback()

    # 生成报告
    print("\n📝 生成测试报告...")
    tester.generate_report()

    # 输出总结
    all_metrics = tester.calculate_metrics(tester.test_results)
    print("\n" + "=" * 60)
    print("🎯 测试总结")
    print("=" * 60)
    print(f"总请求数: {all_metrics.total_requests}")
    print(f"成功率: {(all_metrics.successful_requests/all_metrics.total_requests*100):.2f}%")
    print(f"平均响应时间: {all_metrics.avg_time:.3f}秒")
    print(f"P95响应时间: {all_metrics.p95_time:.3f}秒")
    print(f"吞吐量: {all_metrics.throughput:.2f} 请求/秒")
    print(f"缓存命中率: {all_metrics.cache_hit_rate:.2f}%")

    # 性能建议
    print("\n💡 性能优化建议:")
    if all_metrics.cache_hit_rate < 30:
        print("  ⚠️ 缓存命中率较低，建议优化缓存策略")
    if all_metrics.p95_time > 5:
        print("  ⚠️ P95响应时间较高，建议优化慢请求")
    if all_metrics.error_rate > 5:
        print("  ⚠️ 错误率较高，建议检查服务稳定性")
    if all_metrics.throughput < 1:
        print("  ⚠️ 吞吐量较低，建议增加并发处理能力")

    print("\n✅ 性能测试完成！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-PPT-Assistant图片生成服务性能测试")
    parser.add_argument("--quick", action="store_true", help="运行快速测试")
    parser.add_argument("--concurrent", type=int, help="并发测试请求数")
    parser.add_argument("--duration", type=int, default=60, help="负载测试持续时间")

    args = parser.parse_args()

    if args.quick:
        # 快速测试
        tester = ImagePerformanceTester()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        print("🚀 运行快速性能测试...")
        loop.run_until_complete(tester.test_concurrent_requests(5))
        tester.generate_report()
        loop.close()
    else:
        # 完整测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_comprehensive_test())
        loop.close()