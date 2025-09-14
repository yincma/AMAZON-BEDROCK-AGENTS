#!/usr/bin/env python3
"""
图片生成服务测试执行脚本
提供便捷的测试执行命令和选项
"""

import os
import sys
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any


class TestRunner:
    """测试执行器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.tests_dir = self.project_root / 'tests'

        # 确保环境变量设置
        self.setup_environment()

    def setup_environment(self):
        """设置测试环境变量"""
        env_vars = {
            'PYTHONPATH': str(self.project_root / 'lambdas'),
            'AWS_ACCESS_KEY_ID': 'testing',
            'AWS_SECRET_ACCESS_KEY': 'testing',
            'AWS_SECURITY_TOKEN': 'testing',
            'AWS_SESSION_TOKEN': 'testing',
            'AWS_DEFAULT_REGION': 'us-east-1',
            'ENVIRONMENT': 'test',
            'DEBUG': 'true',
            'CACHE_ENABLED': 'true',
            'PARALLEL_PROCESSING': 'true'
        }

        for key, value in env_vars.items():
            if key not in os.environ:
                os.environ[key] = value

    def run_command(self, command: List[str], description: str = "") -> Dict[str, Any]:
        """执行命令并返回结果"""
        if description:
            print(f"🚀 {description}")

        print(f"执行命令: {' '.join(command)}")

        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False
            )
            execution_time = time.time() - start_time

            success = result.returncode == 0
            status_icon = "✅" if success else "❌"

            print(f"{status_icon} 完成 ({execution_time:.2f}s)")

            if not success and result.stderr:
                print(f"错误输出:\n{result.stderr}")

            return {
                'success': success,
                'returncode': result.returncode,
                'execution_time': execution_time,
                'stdout': result.stdout,
                'stderr': result.stderr
            }

        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ 执行失败: {e}")
            return {
                'success': False,
                'returncode': -1,
                'execution_time': execution_time,
                'stdout': '',
                'stderr': str(e)
            }

    def run_unit_tests(self, verbose: bool = True, coverage: bool = True) -> Dict[str, Any]:
        """运行单元测试"""
        command = ['python', '-m', 'pytest', 'tests/test_image_processing_service.py']

        if verbose:
            command.append('-v')

        if coverage:
            command.extend([
                '--cov=lambdas',
                '--cov-report=term-missing',
                '--cov-report=html:htmlcov'
            ])

        command.extend([
            '-m', 'not slow',
            '--junit-xml=test-results/unit-junit.xml'
        ])

        return self.run_command(command, "运行单元测试")

    def run_integration_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """运行集成测试"""
        command = [
            'python', '-m', 'pytest',
            'tests/test_image_comprehensive_integration.py',
            '-m', 'not (stress or performance)',
            '--junit-xml=test-results/integration-junit.xml'
        ]

        if verbose:
            command.append('-v')

        return self.run_command(command, "运行集成测试")

    def run_performance_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """运行性能测试"""
        command = [
            'python', '-m', 'pytest',
            'tests/test_image_performance_benchmarks.py',
            '-m', 'performance',
            '--benchmark-json=benchmark-results.json',
            '--junit-xml=test-results/performance-junit.xml'
        ]

        if verbose:
            command.append('-v')

        return self.run_command(command, "运行性能基准测试")

    def run_stress_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """运行压力测试"""
        command = [
            'python', '-m', 'pytest',
            'tests/test_image_stress_concurrency.py',
            '-m', 'stress',
            '--junit-xml=test-results/stress-junit.xml',
            '--maxfail=3'
        ]

        if verbose:
            command.append('-v')

        return self.run_command(command, "运行压力测试")

    def run_all_tests(self, skip_slow: bool = True) -> Dict[str, Any]:
        """运行所有测试"""
        command = ['python', '-m', 'pytest', 'tests/']

        if skip_slow:
            command.extend(['-m', 'not (slow or stress or load)'])

        command.extend([
            '--cov=lambdas',
            '--cov-report=html:htmlcov',
            '--cov-report=xml',
            '--junit-xml=test-results/all-junit.xml',
            '-v'
        ])

        return self.run_command(command, "运行完整测试套件")

    def run_specific_test(self, test_path: str, verbose: bool = True) -> Dict[str, Any]:
        """运行特定测试"""
        command = ['python', '-m', 'pytest', test_path]

        if verbose:
            command.append('-v')

        return self.run_command(command, f"运行特定测试: {test_path}")

    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        command = ['python', 'tests/generate_test_report.py']
        return self.run_command(command, "生成测试报告")

    def check_dependencies(self) -> bool:
        """检查测试依赖"""
        print("🔍 检查测试依赖...")

        required_packages = [
            'pytest', 'pytest-cov', 'pytest-xdist', 'pytest-benchmark',
            'moto', 'boto3', 'pillow', 'responses'
        ]

        missing_packages = []

        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
            print(f"请运行: pip install {' '.join(missing_packages)}")
            return False

        print("✅ 所有依赖包已安装")
        return True

    def setup_directories(self):
        """设置必要的目录"""
        directories = [
            'test-results',
            'tests/logs',
            'htmlcov',
            'reports'
        ]

        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 创建目录: {dir_path}")

    def clean_test_artifacts(self):
        """清理测试产物"""
        print("🧹 清理测试产物...")

        patterns = [
            'test-results/*',
            'htmlcov/*',
            '.coverage*',
            '**/__pycache__',
            '**/*.pyc',
            '.pytest_cache',
            'benchmark-*.json'
        ]

        import glob
        import shutil

        for pattern in patterns:
            for path in glob.glob(str(self.project_root / pattern), recursive=True):
                path_obj = Path(path)
                try:
                    if path_obj.is_dir():
                        shutil.rmtree(path_obj)
                    else:
                        path_obj.unlink()
                    print(f"  删除: {path_obj}")
                except Exception as e:
                    print(f"  警告: 无法删除 {path_obj}: {e}")

        print("✅ 清理完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="图片生成服务测试执行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python scripts/run_image_tests.py --unit                # 运行单元测试
  python scripts/run_image_tests.py --integration         # 运行集成测试
  python scripts/run_image_tests.py --performance         # 运行性能测试
  python scripts/run_image_tests.py --stress              # 运行压力测试
  python scripts/run_image_tests.py --all                 # 运行所有测试
  python scripts/run_image_tests.py --test path/to/test   # 运行特定测试
  python scripts/run_image_tests.py --report              # 生成测试报告
  python scripts/run_image_tests.py --clean               # 清理测试产物
        """
    )

    # 测试类型选项
    parser.add_argument('--unit', action='store_true', help='运行单元测试')
    parser.add_argument('--integration', action='store_true', help='运行集成测试')
    parser.add_argument('--performance', action='store_true', help='运行性能测试')
    parser.add_argument('--stress', action='store_true', help='运行压力测试')
    parser.add_argument('--all', action='store_true', help='运行所有测试')

    # 特定测试
    parser.add_argument('--test', type=str, help='运行特定测试文件或函数')

    # 报告和工具
    parser.add_argument('--report', action='store_true', help='生成测试报告')
    parser.add_argument('--clean', action='store_true', help='清理测试产物')
    parser.add_argument('--setup', action='store_true', help='设置测试环境')

    # 选项
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式')
    parser.add_argument('--no-coverage', action='store_true', help='禁用覆盖率收集')
    parser.add_argument('--include-slow', action='store_true', help='包含慢测试')

    args = parser.parse_args()

    # 创建测试运行器
    runner = TestRunner()

    # 检查是否需要帮助
    if len(sys.argv) == 1:
        parser.print_help()
        return

    # 执行对应操作
    results = []
    verbose = not args.quiet

    try:
        if args.clean:
            runner.clean_test_artifacts()
            return

        if args.setup:
            if not runner.check_dependencies():
                sys.exit(1)
            runner.setup_directories()
            print("✅ 测试环境设置完成")
            return

        if args.report:
            result = runner.generate_report()
            results.append(('测试报告生成', result))

        elif args.unit:
            result = runner.run_unit_tests(
                verbose=verbose,
                coverage=not args.no_coverage
            )
            results.append(('单元测试', result))

        elif args.integration:
            result = runner.run_integration_tests(verbose=verbose)
            results.append(('集成测试', result))

        elif args.performance:
            result = runner.run_performance_tests(verbose=verbose)
            results.append(('性能测试', result))

        elif args.stress:
            result = runner.run_stress_tests(verbose=verbose)
            results.append(('压力测试', result))

        elif args.all:
            result = runner.run_all_tests(skip_slow=not args.include_slow)
            results.append(('完整测试套件', result))

        elif args.test:
            result = runner.run_specific_test(args.test, verbose=verbose)
            results.append(('特定测试', result))

        else:
            print("❌ 请指定要执行的测试类型")
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        sys.exit(130)

    except Exception as e:
        print(f"❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 输出结果摘要
    if results:
        print("\n" + "="*60)
        print("📊 测试执行摘要")
        print("="*60)

        total_time = 0
        all_success = True

        for test_name, result in results:
            status = "✅ 成功" if result['success'] else "❌ 失败"
            total_time += result['execution_time']
            if not result['success']:
                all_success = False

            print(f"{test_name}: {status} ({result['execution_time']:.2f}s)")

        print(f"\n总耗时: {total_time:.2f}s")

        if all_success:
            print("🎉 所有测试执行成功!")
        else:
            print("⚠️ 部分测试执行失败，请检查详细输出")
            sys.exit(1)


if __name__ == "__main__":
    main()