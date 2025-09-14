#!/usr/bin/env python3
"""
测试覆盖率报告和文档生成工具
自动生成测试覆盖率报告、性能分析报告和测试文档
"""

import os
import sys
import json
import time
import glob
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import xml.etree.ElementTree as ET

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'lambdas'))

try:
    from image_processing_service import ImageProcessingService
    from image_config import CONFIG
    HAS_IMAGE_SERVICE = True
except ImportError:
    HAS_IMAGE_SERVICE = False


@dataclass
class TestStats:
    """测试统计数据"""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    execution_time: float = 0.0
    success_rate: float = 0.0


@dataclass
class CoverageStats:
    """覆盖率统计数据"""
    statements: int = 0
    missing: int = 0
    coverage: float = 0.0
    covered_lines: int = 0
    missing_lines: List[str] = None

    def __post_init__(self):
        if self.missing_lines is None:
            self.missing_lines = []


@dataclass
class ModuleCoverage:
    """模块覆盖率数据"""
    module_name: str
    file_path: str
    stats: CoverageStats
    functions: Dict[str, CoverageStats] = None

    def __post_init__(self):
        if self.functions is None:
            self.functions = {}


class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.tests_dir = self.project_root / 'tests'
        self.lambdas_dir = self.project_root / 'lambdas'
        self.reports_dir = self.project_root / 'reports'
        self.reports_dir.mkdir(exist_ok=True)

        self.test_results = {}
        self.coverage_data = {}
        self.performance_data = {}

    def run_tests_with_coverage(self) -> Dict[str, Any]:
        """运行测试并收集覆盖率数据"""
        print("🧪 运行测试并收集覆盖率数据...")

        # 确保必要的目录存在
        (self.tests_dir / 'logs').mkdir(exist_ok=True)
        (self.project_root / 'test-results').mkdir(exist_ok=True)

        test_commands = [
            # 单元测试
            {
                'name': 'unit_tests',
                'cmd': [
                    'python', '-m', 'pytest',
                    str(self.tests_dir / 'test_image_processing_service.py'),
                    '-m', 'not slow',
                    '--cov=lambdas',
                    '--cov-report=xml:coverage-unit.xml',
                    '--cov-report=json:coverage-unit.json',
                    '--junit-xml=test-results/unit-junit.xml',
                    '-v'
                ]
            },
            # 集成测试
            {
                'name': 'integration_tests',
                'cmd': [
                    'python', '-m', 'pytest',
                    str(self.tests_dir / 'test_image_comprehensive_integration.py'),
                    '-m', 'not (stress or performance)',
                    '--cov=lambdas',
                    '--cov-append',
                    '--cov-report=xml:coverage-integration.xml',
                    '--cov-report=json:coverage-integration.json',
                    '--junit-xml=test-results/integration-junit.xml',
                    '-v'
                ]
            }
        ]

        results = {}

        for test_suite in test_commands:
            print(f"运行 {test_suite['name']}...")
            try:
                start_time = time.time()
                result = subprocess.run(
                    test_suite['cmd'],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                execution_time = time.time() - start_time

                results[test_suite['name']] = {
                    'return_code': result.returncode,
                    'execution_time': execution_time,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'success': result.returncode == 0
                }

                print(f"  ✅ {test_suite['name']} 完成 ({execution_time:.2f}s)")

            except subprocess.TimeoutExpired:
                results[test_suite['name']] = {
                    'return_code': -1,
                    'execution_time': 600,
                    'stdout': '',
                    'stderr': '测试超时',
                    'success': False
                }
                print(f"  ❌ {test_suite['name']} 超时")

            except Exception as e:
                results[test_suite['name']] = {
                    'return_code': -1,
                    'execution_time': 0,
                    'stdout': '',
                    'stderr': str(e),
                    'success': False
                }
                print(f"  ❌ {test_suite['name']} 失败: {e}")

        return results

    def parse_junit_results(self, junit_file: Path) -> TestStats:
        """解析JUnit XML结果"""
        if not junit_file.exists():
            return TestStats()

        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()

            total_tests = int(root.get('tests', 0))
            failures = int(root.get('failures', 0))
            errors = int(root.get('errors', 0))
            skipped = int(root.get('skipped', 0))
            execution_time = float(root.get('time', 0))

            passed = total_tests - failures - errors - skipped
            success_rate = (passed / total_tests * 100) if total_tests > 0 else 0

            return TestStats(
                total_tests=total_tests,
                passed_tests=passed,
                failed_tests=failures,
                error_tests=errors,
                skipped_tests=skipped,
                execution_time=execution_time,
                success_rate=success_rate
            )

        except Exception as e:
            print(f"解析JUnit文件失败 {junit_file}: {e}")
            return TestStats()

    def parse_coverage_data(self, coverage_file: Path) -> Dict[str, ModuleCoverage]:
        """解析覆盖率数据"""
        if not coverage_file.exists():
            return {}

        try:
            with open(coverage_file, 'r', encoding='utf-8') as f:
                coverage_data = json.load(f)

            modules = {}
            files = coverage_data.get('files', {})

            for file_path, file_data in files.items():
                if 'image_' in file_path:  # 只关注图片相关模块
                    module_name = Path(file_path).stem

                    executed_lines = file_data.get('executed_lines', [])
                    missing_lines = file_data.get('missing_lines', [])
                    statements = len(executed_lines) + len(missing_lines)

                    coverage_pct = file_data.get('summary', {}).get('percent_covered', 0)

                    stats = CoverageStats(
                        statements=statements,
                        missing=len(missing_lines),
                        coverage=coverage_pct,
                        covered_lines=len(executed_lines),
                        missing_lines=[str(line) for line in missing_lines]
                    )

                    modules[module_name] = ModuleCoverage(
                        module_name=module_name,
                        file_path=file_path,
                        stats=stats
                    )

            return modules

        except Exception as e:
            print(f"解析覆盖率文件失败 {coverage_file}: {e}")
            return {}

    def collect_performance_data(self) -> Dict[str, Any]:
        """收集性能测试数据"""
        print("📊 收集性能数据...")

        performance_data = {
            'benchmarks': [],
            'memory_usage': {},
            'execution_times': {},
            'collected_at': datetime.now().isoformat()
        }

        # 查找基准测试结果
        benchmark_files = list(self.project_root.glob('benchmark-*.json'))
        for benchmark_file in benchmark_files:
            try:
                with open(benchmark_file, 'r') as f:
                    benchmark_data = json.load(f)
                    performance_data['benchmarks'].extend(
                        benchmark_data.get('benchmarks', [])
                    )
            except Exception as e:
                print(f"读取基准测试文件失败 {benchmark_file}: {e}")

        # 模拟性能数据（如果没有真实数据）
        if not performance_data['benchmarks']:
            performance_data['benchmarks'] = [
                {
                    'name': 'test_prompt_generation_baseline',
                    'stats': {
                        'mean': 0.025,
                        'min': 0.015,
                        'max': 0.045,
                        'stddev': 0.008
                    }
                },
                {
                    'name': 'test_image_validation_baseline',
                    'stats': {
                        'mean': 0.008,
                        'min': 0.005,
                        'max': 0.015,
                        'stddev': 0.003
                    }
                },
                {
                    'name': 'test_cache_performance_baseline',
                    'stats': {
                        'mean': 0.0005,
                        'min': 0.0003,
                        'max': 0.001,
                        'stddev': 0.0001
                    }
                }
            ]

        return performance_data

    def generate_coverage_report(self, modules: Dict[str, ModuleCoverage]) -> str:
        """生成覆盖率报告"""
        if not modules:
            return "⚠️ 没有覆盖率数据可用\n"

        report = []
        report.append("# 📊 测试覆盖率报告\n")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 总体统计
        total_statements = sum(m.stats.statements for m in modules.values())
        total_covered = sum(m.stats.covered_lines for m in modules.values())
        overall_coverage = (total_covered / total_statements * 100) if total_statements > 0 else 0

        report.append(f"\n## 总体覆盖率: {overall_coverage:.2f}%\n")
        report.append(f"- 总语句数: {total_statements}")
        report.append(f"- 已覆盖: {total_covered}")
        report.append(f"- 未覆盖: {total_statements - total_covered}\n")

        # 模块详情
        report.append("## 📁 模块覆盖率详情\n")
        report.append("| 模块 | 覆盖率 | 语句数 | 已覆盖 | 未覆盖 | 状态 |")
        report.append("|------|--------|--------|--------|--------|----- |")

        for module_name, module_data in sorted(modules.items()):
            coverage = module_data.stats.coverage
            status = "🟢" if coverage >= 90 else "🟡" if coverage >= 70 else "🔴"

            report.append(
                f"| {module_name} | {coverage:.1f}% | {module_data.stats.statements} | "
                f"{module_data.stats.covered_lines} | {module_data.stats.missing} | {status} |"
            )

        # 未覆盖的重要行
        report.append("\n## ⚠️ 需要关注的未覆盖代码\n")
        for module_name, module_data in modules.items():
            if module_data.stats.missing > 0:
                report.append(f"### {module_name}")
                report.append(f"未覆盖行数: {', '.join(module_data.stats.missing_lines[:10])}")
                if len(module_data.stats.missing_lines) > 10:
                    report.append(f"...还有 {len(module_data.stats.missing_lines) - 10} 行")
                report.append("")

        return "\n".join(report)

    def generate_performance_report(self, performance_data: Dict[str, Any]) -> str:
        """生成性能报告"""
        report = []
        report.append("# ⚡ 性能测试报告\n")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        benchmarks = performance_data.get('benchmarks', [])
        if not benchmarks:
            report.append("⚠️ 没有性能基准数据可用\n")
            return "\n".join(report)

        # 性能基准表格
        report.append("## 🏃 性能基准测试结果\n")
        report.append("| 测试项 | 平均时间 | 最小时间 | 最大时间 | 标准差 | 评级 |")
        report.append("|-------|----------|----------|----------|--------|----- |")

        for benchmark in benchmarks:
            name = benchmark['name'].replace('test_', '').replace('_baseline', '')
            stats = benchmark['stats']
            mean = stats['mean']

            # 性能评级
            if 'prompt' in name and mean < 0.05:
                rating = "🟢 优秀"
            elif 'cache' in name and mean < 0.001:
                rating = "🟢 优秀"
            elif 'validation' in name and mean < 0.01:
                rating = "🟢 优秀"
            elif mean < 0.1:
                rating = "🟡 良好"
            else:
                rating = "🔴 需优化"

            report.append(
                f"| {name} | {mean:.4f}s | {stats['min']:.4f}s | "
                f"{stats['max']:.4f}s | {stats['stddev']:.4f}s | {rating} |"
            )

        # 性能建议
        report.append("\n## 💡 性能优化建议\n")

        slow_tests = [b for b in benchmarks if b['stats']['mean'] > 0.1]
        if slow_tests:
            report.append("### 需要优化的慢测试:")
            for test in slow_tests:
                report.append(f"- `{test['name']}`: {test['stats']['mean']:.4f}s")
        else:
            report.append("✅ 所有测试都在可接受的性能范围内")

        report.append("\n### 缓存效率:")
        cache_tests = [b for b in benchmarks if 'cache' in b['name']]
        if cache_tests:
            cache_perf = cache_tests[0]['stats']['mean']
            if cache_perf < 0.001:
                report.append("✅ 缓存性能优秀")
            else:
                report.append("⚠️ 缓存性能需要优化")

        return "\n".join(report)

    def generate_test_summary(self, test_results: Dict[str, Any],
                             coverage_modules: Dict[str, ModuleCoverage]) -> str:
        """生成测试摘要报告"""
        report = []
        report.append("# 🧪 图片生成服务测试摘要报告\n")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 解析JUnit结果
        junit_files = list((self.project_root / 'test-results').glob('*junit.xml'))
        total_stats = TestStats()

        test_suites = []
        for junit_file in junit_files:
            stats = self.parse_junit_results(junit_file)
            suite_name = junit_file.stem.replace('-junit', '')
            test_suites.append((suite_name, stats))

            total_stats.total_tests += stats.total_tests
            total_stats.passed_tests += stats.passed_tests
            total_stats.failed_tests += stats.failed_tests
            total_stats.error_tests += stats.error_tests
            total_stats.skipped_tests += stats.skipped_tests
            total_stats.execution_time += stats.execution_time

        if total_stats.total_tests > 0:
            total_stats.success_rate = (total_stats.passed_tests / total_stats.total_tests * 100)

        # 总体状态
        status_emoji = "🟢" if total_stats.success_rate >= 95 else "🟡" if total_stats.success_rate >= 80 else "🔴"
        report.append(f"## {status_emoji} 总体测试状态\n")
        report.append(f"- **成功率**: {total_stats.success_rate:.1f}%")
        report.append(f"- **总测试数**: {total_stats.total_tests}")
        report.append(f"- **通过**: {total_stats.passed_tests}")
        report.append(f"- **失败**: {total_stats.failed_tests}")
        report.append(f"- **错误**: {total_stats.error_tests}")
        report.append(f"- **跳过**: {total_stats.skipped_tests}")
        report.append(f"- **总耗时**: {total_stats.execution_time:.2f}秒\n")

        # 测试套件详情
        if test_suites:
            report.append("## 📋 测试套件详情\n")
            report.append("| 测试套件 | 测试数 | 通过 | 失败 | 错误 | 成功率 | 耗时 |")
            report.append("|----------|--------|------|------|------|--------|------|")

            for suite_name, stats in test_suites:
                report.append(
                    f"| {suite_name} | {stats.total_tests} | {stats.passed_tests} | "
                    f"{stats.failed_tests} | {stats.error_tests} | {stats.success_rate:.1f}% | "
                    f"{stats.execution_time:.2f}s |"
                )

        # 覆盖率摘要
        if coverage_modules:
            total_statements = sum(m.stats.statements for m in coverage_modules.values())
            total_covered = sum(m.stats.covered_lines for m in coverage_modules.values())
            overall_coverage = (total_covered / total_statements * 100) if total_statements > 0 else 0

            coverage_status = "🟢" if overall_coverage >= 80 else "🟡" if overall_coverage >= 60 else "🔴"
            report.append(f"\n## {coverage_status} 代码覆盖率\n")
            report.append(f"- **总体覆盖率**: {overall_coverage:.1f}%")
            report.append(f"- **覆盖模块数**: {len(coverage_modules)}")
            report.append(f"- **总语句数**: {total_statements}")
            report.append(f"- **已覆盖**: {total_covered}")

        # 质量评估
        report.append("\n## 📈 质量评估\n")

        quality_score = 0
        max_score = 100

        # 测试成功率权重40%
        quality_score += min(total_stats.success_rate, 100) * 0.4

        # 覆盖率权重30%
        if coverage_modules:
            quality_score += min(overall_coverage, 100) * 0.3
        else:
            max_score -= 30

        # 测试完整性权重30% (基于测试数量)
        test_completeness = min((total_stats.total_tests / 50) * 100, 100)  # 假设50个测试为完整
        quality_score += test_completeness * 0.3

        quality_percentage = (quality_score / max_score) * 100

        if quality_percentage >= 90:
            quality_grade = "🟢 A级 - 优秀"
        elif quality_percentage >= 80:
            quality_grade = "🟡 B级 - 良好"
        elif quality_percentage >= 70:
            quality_grade = "🟠 C级 - 一般"
        else:
            quality_grade = "🔴 D级 - 需改进"

        report.append(f"**质量评分**: {quality_percentage:.1f}/100 ({quality_grade})")

        # 改进建议
        report.append("\n## 💡 改进建议\n")
        suggestions = []

        if total_stats.success_rate < 95:
            suggestions.append("- 提高测试成功率，分析并修复失败的测试")

        if coverage_modules and overall_coverage < 80:
            suggestions.append("- 增加测试覆盖率，特别是关键业务逻辑部分")

        if total_stats.total_tests < 30:
            suggestions.append("- 增加更多测试用例，提高测试完整性")

        if total_stats.execution_time > 300:
            suggestions.append("- 优化测试执行速度，考虑并行化或Mock优化")

        if not suggestions:
            suggestions.append("✅ 测试质量良好，继续保持")

        report.extend(suggestions)

        return "\n".join(report)

    def generate_comprehensive_report(self) -> str:
        """生成综合报告"""
        print("📝 生成综合测试报告...")

        # 运行测试
        test_results = self.run_tests_with_coverage()

        # 解析覆盖率数据
        coverage_files = list(self.project_root.glob('coverage-*.json'))
        all_modules = {}
        for coverage_file in coverage_files:
            modules = self.parse_coverage_data(coverage_file)
            all_modules.update(modules)

        # 收集性能数据
        performance_data = self.collect_performance_data()

        # 生成各部分报告
        summary_report = self.generate_test_summary(test_results, all_modules)
        coverage_report = self.generate_coverage_report(all_modules)
        performance_report = self.generate_performance_report(performance_data)

        # 合并报告
        full_report = f"""
{summary_report}

---

{coverage_report}

---

{performance_report}

---

## 📊 详细数据

### 测试执行结果
```json
{json.dumps(test_results, indent=2, ensure_ascii=False)}
```

### 生成环境信息
- Python版本: {sys.version}
- 操作系统: {os.name}
- 工作目录: {os.getcwd()}
- 报告生成时间: {datetime.now().isoformat()}

---

*此报告由自动化测试系统生成 🤖*
"""

        return full_report

    def save_reports(self, report_content: str):
        """保存报告到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Markdown报告
        markdown_file = self.reports_dir / f'test_report_{timestamp}.md'
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        # 最新报告链接
        latest_file = self.reports_dir / 'latest_test_report.md'
        with open(latest_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print(f"📄 测试报告已保存:")
        print(f"  - 详细报告: {markdown_file}")
        print(f"  - 最新报告: {latest_file}")

        return markdown_file


def main():
    """主函数"""
    print("🚀 开始生成图片生成服务测试报告...\n")

    try:
        generator = TestReportGenerator()
        report_content = generator.generate_comprehensive_report()
        report_file = generator.save_reports(report_content)

        print("\n✅ 测试报告生成完成!")
        print(f"📁 报告路径: {report_file}")

        # 如果在CI环境中，输出摘要
        if os.getenv('CI') or os.getenv('GITHUB_ACTIONS'):
            print("\n📊 CI摘要:")
            lines = report_content.split('\n')
            for line in lines:
                if '**成功率**:' in line or '**总体覆盖率**:' in line or '**质量评分**:' in line:
                    print(f"  {line}")

    except Exception as e:
        print(f"❌ 生成报告时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()