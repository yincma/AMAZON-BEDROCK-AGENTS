#!/usr/bin/env python3
"""
VERIFY阶段测试执行器 - 运行所有测试并生成覆盖率报告
"""
import sys
import os
import subprocess
import json
import time
from datetime import datetime
import yaml

def setup_environment():
    """设置测试环境"""
    # 设置环境变量
    os.environ.update({
        'AWS_ACCESS_KEY_ID': 'testing',
        'AWS_SECRET_ACCESS_KEY': 'testing',
        'AWS_DEFAULT_REGION': 'us-east-1',
        'S3_BUCKET': 'ai-ppt-presentations-test',
        'PYTHONPATH': os.getcwd()
    })

def run_test_suite(test_module, verbose=True):
    """运行特定测试套件"""
    print(f"\n{'='*60}")
    print(f"运行测试套件: {test_module}")
    print(f"{'='*60}")

    cmd = [
        'python', '-m', 'pytest',
        f'tests/{test_module}',
        '-v' if verbose else '',
        '--tb=short',
        '--disable-warnings',
        '-x',  # 第一个失败时停止
        '--cov=src',
        '--cov=lambdas',
        '--cov-report=term-missing',
        '--maxfail=5'
    ]

    cmd = [c for c in cmd if c]  # 移除空字符串

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            env=os.environ
        )
        end_time = time.time()
        duration = end_time - start_time

        return {
            'module': test_module,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'duration': duration,
            'passed': result.returncode == 0
        }
    except Exception as e:
        return {
            'module': test_module,
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
            'duration': 0,
            'passed': False
        }

def generate_test_report(results):
    """生成测试报告"""
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['passed'])
    failed_tests = total_tests - passed_tests
    total_duration = sum(r['duration'] for r in results)

    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_suites': total_tests,
            'passed_suites': passed_tests,
            'failed_suites': failed_tests,
            'total_duration': round(total_duration, 2),
            'success_rate': round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0
        },
        'detailed_results': results
    }

    return report

def update_tdd_state(test_passed=True):
    """更新TDD状态文件"""
    state_file = '.tdd-state/current-cycle.yaml'
    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            state = yaml.safe_load(f)

        # 更新VERIFY阶段状态
        state['phases']['VERIFY'] = {
            'status': 'completed' if test_passed else 'failed',
            'description': 'VERIFY阶段 - 执行测试验证实现',
            'timestamp': datetime.now().isoformat(),
            'test_passed': test_passed
        }

        if test_passed:
            state['cycle_status'] = 'completed'
            state['completed_at'] = datetime.now().isoformat()
        else:
            state['cycle_status'] = 'failed'
            state['current_phase'] = 'GREEN'  # 回到GREEN阶段修复

        with open(state_file, 'w', encoding='utf-8') as f:
            yaml.dump(state, f, default_flow_style=False, allow_unicode=True)

def main():
    """主执行函数"""
    print("🚀 启动VERIFY阶段测试执行...")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 设置环境
    setup_environment()

    # 测试套件列表
    test_suites = [
        'test_content_generator.py',
        'test_ppt_compiler.py',
        'test_api.py',
        'test_integration.py',
        'test_infrastructure.py'
    ]

    all_results = []

    for suite in test_suites:
        print(f"\n📋 执行测试套件: {suite}")
        result = run_test_suite(suite)
        all_results.append(result)

        if result['passed']:
            print(f"✅ {suite} - 通过 ({result['duration']:.2f}s)")
        else:
            print(f"❌ {suite} - 失败 ({result['duration']:.2f}s)")
            print(f"错误信息: {result['stderr'][:200]}...")

    # 生成报告
    report = generate_test_report(all_results)

    # 保存报告
    with open('test_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 更新TDD状态
    all_passed = all(r['passed'] for r in all_results)
    update_tdd_state(all_passed)

    # 打印总结
    print(f"\n{'='*60}")
    print("🎯 测试执行总结")
    print(f"{'='*60}")
    print(f"总测试套件: {report['summary']['total_suites']}")
    print(f"通过套件: {report['summary']['passed_suites']}")
    print(f"失败套件: {report['summary']['failed_suites']}")
    print(f"成功率: {report['summary']['success_rate']:.1f}%")
    print(f"总耗时: {report['summary']['total_duration']:.2f}s")

    if all_passed:
        print("\n🎉 所有测试通过！VERIFY阶段完成！")
        return 0
    else:
        print("\n⚠️  存在测试失败，需要回到GREEN阶段修复代码")
        return 1

if __name__ == '__main__':
    sys.exit(main())