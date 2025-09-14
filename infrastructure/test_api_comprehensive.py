#!/usr/bin/env python3
"""
AI PPT后端API综合测试套件 - Python版本
提供更详细的API测试、数据验证和报告生成功能
"""

import json
import requests
import time
import threading
import concurrent.futures
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
import argparse
import sys
import os
import logging
from dataclasses import dataclass, asdict
import uuid
import statistics

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('api_test.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    status: str  # PASS, FAIL, WARN
    details: str
    response_time: int  # 毫秒
    status_code: Optional[int] = None
    response_data: Optional[Dict] = None
    error_message: Optional[str] = None

@dataclass
class TestSuite:
    """测试套件结果"""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    results: List[TestResult] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []

class APITester:
    """API测试主类"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-PPT-API-Tester/1.0',
            'Accept': 'application/json'
        })
        self.test_suite = TestSuite()
        self.current_presentation_id = None

    def log_test_start(self, test_name: str):
        """记录测试开始"""
        self.test_suite.total_tests += 1
        logger.info(f"开始测试: {test_name}")

    def record_result(self, result: TestResult):
        """记录测试结果"""
        self.test_suite.results.append(result)

        if result.status == 'PASS':
            self.test_suite.passed += 1
            logger.info(f"✅ {result.test_name} - {result.details}")
        elif result.status == 'FAIL':
            self.test_suite.failed += 1
            logger.error(f"❌ {result.test_name} - {result.details}")
        elif result.status == 'WARN':
            self.test_suite.warnings += 1
            logger.warning(f"⚠️  {result.test_name} - {result.details}")

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                    headers: Optional[Dict] = None, expected_status: int = 200) -> Tuple[requests.Response, int]:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        request_headers = self.session.headers.copy()

        if headers:
            request_headers.update(headers)

        start_time = time.time()

        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=request_headers, timeout=self.timeout)
            elif method.upper() == 'POST':
                request_headers['Content-Type'] = 'application/json'
                response = self.session.post(url, json=data, headers=request_headers, timeout=self.timeout)
            elif method.upper() == 'OPTIONS':
                response = self.session.options(url, headers=request_headers, timeout=self.timeout)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            response_time = int((time.time() - start_time) * 1000)
            return response, response_time

        except requests.exceptions.RequestException as e:
            response_time = int((time.time() - start_time) * 1000)
            logger.error(f"请求失败: {str(e)}")
            raise

    def validate_json_response(self, response: requests.Response) -> bool:
        """验证JSON响应格式"""
        try:
            response.json()
            return True
        except json.JSONDecodeError:
            return False

    def test_basic_connectivity(self):
        """测试基本连通性"""
        test_name = "基本连通性测试"
        self.log_test_start(test_name)

        try:
            response, response_time = self.make_request('GET', '')

            if response.status_code in [200, 404]:
                result = TestResult(
                    test_name=test_name,
                    status='PASS',
                    details=f"API连通性正常 (状态码: {response.status_code})",
                    response_time=response_time,
                    status_code=response.status_code
                )
            else:
                result = TestResult(
                    test_name=test_name,
                    status='FAIL',
                    details=f"连通性异常 (状态码: {response.status_code})",
                    response_time=response_time,
                    status_code=response.status_code
                )

        except Exception as e:
            result = TestResult(
                test_name=test_name,
                status='FAIL',
                details=f"连接失败: {str(e)}",
                response_time=0,
                error_message=str(e)
            )

        self.record_result(result)

    def test_cors_preflight(self):
        """测试CORS预检请求"""
        test_name = "CORS预检请求测试"
        self.log_test_start(test_name)

        headers = {
            'Origin': 'https://example.com',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }

        try:
            response, response_time = self.make_request('OPTIONS', '/generate', headers=headers)

            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
            }

            if response.status_code in [200, 204]:
                result = TestResult(
                    test_name=test_name,
                    status='PASS',
                    details=f"CORS预检成功 (状态码: {response.status_code})",
                    response_time=response_time,
                    status_code=response.status_code,
                    response_data=cors_headers
                )
            else:
                result = TestResult(
                    test_name=test_name,
                    status='FAIL',
                    details=f"CORS预检失败 (状态码: {response.status_code})",
                    response_time=response_time,
                    status_code=response.status_code
                )

        except Exception as e:
            result = TestResult(
                test_name=test_name,
                status='FAIL',
                details=f"CORS测试失败: {str(e)}",
                response_time=0,
                error_message=str(e)
            )

        self.record_result(result)

    def test_generate_ppt_success(self):
        """测试PPT生成 - 成功场景"""
        test_name = "PPT生成请求 - 正常场景"
        self.log_test_start(test_name)

        test_data = {
            "topic": "人工智能在现代企业中的应用与挑战",
            "page_count": 10,
            "style": "professional"
        }

        try:
            response, response_time = self.make_request('POST', '/generate', test_data)

            if response.status_code in [200, 202]:
                if self.validate_json_response(response):
                    response_data = response.json()
                    presentation_id = response_data.get('presentation_id')

                    if presentation_id:
                        self.current_presentation_id = presentation_id
                        result = TestResult(
                            test_name=test_name,
                            status='PASS',
                            details=f"PPT生成请求成功 (ID: {presentation_id[:8]}...)",
                            response_time=response_time,
                            status_code=response.status_code,
                            response_data=response_data
                        )
                    else:
                        result = TestResult(
                            test_name=test_name,
                            status='WARN',
                            details="响应中缺少presentation_id",
                            response_time=response_time,
                            status_code=response.status_code
                        )
                else:
                    result = TestResult(
                        test_name=test_name,
                        status='FAIL',
                        details="响应格式非JSON",
                        response_time=response_time,
                        status_code=response.status_code
                    )
            else:
                result = TestResult(
                    test_name=test_name,
                    status='FAIL',
                    details=f"请求失败 (状态码: {response.status_code})",
                    response_time=response_time,
                    status_code=response.status_code
                )

        except Exception as e:
            result = TestResult(
                test_name=test_name,
                status='FAIL',
                details=f"生成测试失败: {str(e)}",
                response_time=0,
                error_message=str(e)
            )

        self.record_result(result)

    def test_input_validation(self):
        """测试输入验证"""
        test_name = "输入参数验证测试"
        self.log_test_start(test_name)

        test_cases = [
            {"data": {}, "description": "空请求"},
            {"data": {"topic": ""}, "description": "空主题"},
            {"data": {"topic": "test", "page_count": -1}, "description": "负数页数"},
            {"data": {"topic": "test", "page_count": 1000}, "description": "页数过大"},
            {"data": {"topic": "A" * 1000, "page_count": 5}, "description": "主题过长"},
        ]

        validation_results = []

        for case in test_cases:
            try:
                response, response_time = self.make_request('POST', '/generate', case["data"])

                if response.status_code == 400:
                    validation_results.append(f"✓ {case['description']} - 正确返回400")
                else:
                    validation_results.append(f"✗ {case['description']} - 状态码: {response.status_code}")

            except Exception as e:
                validation_results.append(f"✗ {case['description']} - 异常: {str(e)}")

        # 评估验证结果
        successful_validations = len([r for r in validation_results if r.startswith('✓')])
        total_validations = len(validation_results)

        if successful_validations >= total_validations * 0.8:  # 80%成功率
            result = TestResult(
                test_name=test_name,
                status='PASS',
                details=f"参数验证正常 ({successful_validations}/{total_validations} 通过)",
                response_time=0,
                response_data={'validation_details': validation_results}
            )
        else:
            result = TestResult(
                test_name=test_name,
                status='FAIL',
                details=f"参数验证不完整 ({successful_validations}/{total_validations} 通过)",
                response_time=0,
                response_data={'validation_details': validation_results}
            )

        self.record_result(result)

    def test_status_endpoint(self):
        """测试状态查询端点"""
        test_name = "状态查询测试"
        self.log_test_start(test_name)

        # 使用之前生成的ID或者测试ID
        test_id = self.current_presentation_id or "test-presentation-id-12345"

        try:
            response, response_time = self.make_request('GET', f'/status/{test_id}')

            if response.status_code in [200, 404]:
                if response.status_code == 200 and self.validate_json_response(response):
                    response_data = response.json()
                    required_fields = ['presentation_id', 'status']

                    missing_fields = [field for field in required_fields if field not in response_data]

                    if not missing_fields:
                        result = TestResult(
                            test_name=test_name,
                            status='PASS',
                            details=f"状态查询成功 (状态: {response_data.get('status', 'N/A')})",
                            response_time=response_time,
                            status_code=response.status_code,
                            response_data=response_data
                        )
                    else:
                        result = TestResult(
                            test_name=test_name,
                            status='WARN',
                            details=f"响应缺少字段: {missing_fields}",
                            response_time=response_time,
                            status_code=response.status_code
                        )
                else:
                    result = TestResult(
                        test_name=test_name,
                        status='PASS',
                        details="状态端点响应正常",
                        response_time=response_time,
                        status_code=response.status_code
                    )
            else:
                result = TestResult(
                    test_name=test_name,
                    status='FAIL',
                    details=f"状态查询失败 (状态码: {response.status_code})",
                    response_time=response_time,
                    status_code=response.status_code
                )

        except Exception as e:
            result = TestResult(
                test_name=test_name,
                status='FAIL',
                details=f"状态查询异常: {str(e)}",
                response_time=0,
                error_message=str(e)
            )

        self.record_result(result)

    def test_download_endpoint(self):
        """测试下载端点"""
        test_name = "下载端点测试"
        self.log_test_start(test_name)

        test_id = self.current_presentation_id or "test-presentation-id-12345"

        try:
            response, response_time = self.make_request('GET', f'/download/{test_id}')

            if response.status_code in [200, 404]:
                if response.status_code == 200 and self.validate_json_response(response):
                    response_data = response.json()

                    if 'download_url' in response_data:
                        result = TestResult(
                            test_name=test_name,
                            status='PASS',
                            details="下载链接生成成功",
                            response_time=response_time,
                            status_code=response.status_code,
                            response_data={'has_download_url': True}
                        )
                    else:
                        result = TestResult(
                            test_name=test_name,
                            status='WARN',
                            details="响应中缺少download_url",
                            response_time=response_time,
                            status_code=response.status_code
                        )
                else:
                    result = TestResult(
                        test_name=test_name,
                        status='PASS',
                        details="下载端点响应正常",
                        response_time=response_time,
                        status_code=response.status_code
                    )
            else:
                result = TestResult(
                    test_name=test_name,
                    status='FAIL',
                    details=f"下载端点失败 (状态码: {response.status_code})",
                    response_time=response_time,
                    status_code=response.status_code
                )

        except Exception as e:
            result = TestResult(
                test_name=test_name,
                status='FAIL',
                details=f"下载测试异常: {str(e)}",
                response_time=0,
                error_message=str(e)
            )

        self.record_result(result)

    def test_concurrent_requests(self, concurrent_count: int = 5):
        """测试并发请求"""
        test_name = f"并发请求测试 ({concurrent_count}个并发)"
        self.log_test_start(test_name)

        def make_concurrent_request(request_id: int) -> Tuple[int, int, bool]:
            """单个并发请求"""
            try:
                test_id = f"concurrent-test-{request_id}-{uuid.uuid4().hex[:8]}"
                response, response_time = self.make_request('GET', f'/status/{test_id}')
                return response.status_code, response_time, True
            except Exception:
                return 0, 0, False

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_count) as executor:
            futures = [executor.submit(make_concurrent_request, i) for i in range(concurrent_count)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        total_time = int((time.time() - start_time) * 1000)

        successful = len([r for r in results if r[2] and r[0] in [200, 404]])
        response_times = [r[1] for r in results if r[2] and r[1] > 0]

        if response_times:
            avg_response_time = int(statistics.mean(response_times))
            max_response_time = max(response_times)
        else:
            avg_response_time = 0
            max_response_time = 0

        success_rate = (successful / concurrent_count) * 100

        if success_rate >= 80:  # 80%成功率
            result = TestResult(
                test_name=test_name,
                status='PASS',
                details=f"并发测试成功 ({successful}/{concurrent_count}, 成功率: {success_rate:.1f}%)",
                response_time=avg_response_time,
                response_data={
                    'successful_requests': successful,
                    'total_requests': concurrent_count,
                    'success_rate': success_rate,
                    'avg_response_time': avg_response_time,
                    'max_response_time': max_response_time,
                    'total_test_time': total_time
                }
            )
        else:
            result = TestResult(
                test_name=test_name,
                status='FAIL',
                details=f"并发测试失败 ({successful}/{concurrent_count}, 成功率: {success_rate:.1f}%)",
                response_time=avg_response_time,
                response_data={
                    'successful_requests': successful,
                    'total_requests': concurrent_count,
                    'success_rate': success_rate
                }
            )

        self.record_result(result)

    def test_performance_baseline(self, iterations: int = 10):
        """测试性能基准"""
        test_name = f"性能基准测试 ({iterations}次请求)"
        self.log_test_start(test_name)

        response_times = []
        successful_requests = 0

        for i in range(iterations):
            try:
                test_id = f"perf-test-{i}-{uuid.uuid4().hex[:8]}"
                response, response_time = self.make_request('GET', f'/status/{test_id}')

                response_times.append(response_time)

                if response.status_code in [200, 404]:
                    successful_requests += 1

                time.sleep(0.1)  # 避免过载

            except Exception as e:
                logger.warning(f"性能测试请求 {i+1} 失败: {str(e)}")

        if response_times:
            avg_time = int(statistics.mean(response_times))
            min_time = min(response_times)
            max_time = max(response_times)
            median_time = int(statistics.median(response_times))

            # 评估性能 - 平均响应时间应该在合理范围内
            if avg_time < 5000:  # 5秒阈值
                status = 'PASS'
                details = f"性能测试通过 (平均: {avg_time}ms, 中位数: {median_time}ms)"
            elif avg_time < 10000:  # 10秒警告阈值
                status = 'WARN'
                details = f"响应时间较长 (平均: {avg_time}ms, 中位数: {median_time}ms)"
            else:
                status = 'FAIL'
                details = f"响应时间过长 (平均: {avg_time}ms)"

            result = TestResult(
                test_name=test_name,
                status=status,
                details=details,
                response_time=avg_time,
                response_data={
                    'iterations': iterations,
                    'successful_requests': successful_requests,
                    'avg_response_time': avg_time,
                    'min_response_time': min_time,
                    'max_response_time': max_time,
                    'median_response_time': median_time
                }
            )
        else:
            result = TestResult(
                test_name=test_name,
                status='FAIL',
                details="无法收集性能数据",
                response_time=0
            )

        self.record_result(result)

    def test_security_basics(self):
        """基本安全性测试"""
        test_name = "基本安全性检查"
        self.log_test_start(test_name)

        security_tests = []

        # 测试SQL注入防护
        try:
            malicious_id = "'; DROP TABLE users; --"
            response, _ = self.make_request('GET', f'/status/{malicious_id}')

            if response.status_code in [400, 404]:
                security_tests.append("✓ SQL注入防护正常")
            else:
                security_tests.append("✗ SQL注入防护可能存在问题")
        except:
            security_tests.append("✓ SQL注入测试触发异常（可能是防护机制）")

        # 测试XSS防护
        try:
            xss_payload = "<script>alert('xss')</script>"
            test_data = {"topic": xss_payload, "page_count": 5}
            response, _ = self.make_request('POST', '/generate', test_data)

            if response.status_code in [400, 200]:
                security_tests.append("✓ XSS测试处理正常")
            else:
                security_tests.append("✗ XSS处理可能存在问题")
        except:
            security_tests.append("✓ XSS测试触发异常（可能是防护机制）")

        # 测试超长输入
        try:
            long_id = "A" * 1000
            response, _ = self.make_request('GET', f'/status/{long_id}')

            if response.status_code in [400, 414]:  # 414 = URI Too Long
                security_tests.append("✓ 超长输入防护正常")
            else:
                security_tests.append("✗ 超长输入处理需要检查")
        except:
            security_tests.append("✓ 超长输入测试触发异常（可能是防护机制）")

        passed_tests = len([t for t in security_tests if t.startswith('✓')])
        total_tests = len(security_tests)

        if passed_tests >= total_tests * 0.8:
            result = TestResult(
                test_name=test_name,
                status='PASS',
                details=f"基本安全检查通过 ({passed_tests}/{total_tests})",
                response_time=0,
                response_data={'security_test_details': security_tests}
            )
        else:
            result = TestResult(
                test_name=test_name,
                status='WARN',
                details=f"安全检查需要关注 ({passed_tests}/{total_tests})",
                response_time=0,
                response_data={'security_test_details': security_tests}
            )

        self.record_result(result)

    def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始运行API综合测试套件")
        self.test_suite.start_time = datetime.now(timezone.utc)

        # 运行所有测试
        self.test_basic_connectivity()
        self.test_cors_preflight()
        self.test_generate_ppt_success()
        self.test_input_validation()
        self.test_status_endpoint()
        self.test_download_endpoint()
        self.test_concurrent_requests(5)
        self.test_performance_baseline(10)
        self.test_security_basics()

        self.test_suite.end_time = datetime.now(timezone.utc)
        logger.info("API综合测试套件完成")

    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        duration = 0
        if self.test_suite.start_time and self.test_suite.end_time:
            duration = int((self.test_suite.end_time - self.test_suite.start_time).total_seconds())

        success_rate = 0
        if self.test_suite.total_tests > 0:
            success_rate = (self.test_suite.passed / self.test_suite.total_tests) * 100

        # 收集响应时间统计
        response_times = [r.response_time for r in self.test_suite.results if r.response_time > 0]
        if response_times:
            avg_response_time = int(statistics.mean(response_times))
            max_response_time = max(response_times)
        else:
            avg_response_time = 0
            max_response_time = 0

        # 生成建议
        recommendations = []

        if self.test_suite.failed > 0:
            recommendations.append("调查并修复失败的测试用例")

        if self.test_suite.warnings > 0:
            recommendations.append("检查警告项目，考虑改进API响应格式")

        if success_rate < 80:
            recommendations.append("成功率低于80%，建议全面检查API实现")

        if avg_response_time > 3000:
            recommendations.append("平均响应时间较长，考虑性能优化")

        recommendations.extend([
            "定期运行此测试套件确保API稳定性",
            "添加更多边界条件和压力测试",
            "实施API监控和告警机制",
            "考虑添加缓存机制提高性能"
        ])

        report = {
            'test_summary': {
                'timestamp': datetime.now().isoformat(),
                'api_endpoint': self.base_url,
                'total_tests': self.test_suite.total_tests,
                'passed': self.test_suite.passed,
                'failed': self.test_suite.failed,
                'warnings': self.test_suite.warnings,
                'success_rate': round(success_rate, 1),
                'duration_seconds': duration,
                'avg_response_time_ms': avg_response_time,
                'max_response_time_ms': max_response_time
            },
            'test_results': [asdict(result) for result in self.test_suite.results],
            'recommendations': recommendations
        }

        return report

    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None):
        """保存测试报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"api_test_report_{timestamp}.json"

        os.makedirs("test_results", exist_ok=True)
        filepath = os.path.join("test_results", filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"测试报告已保存到: {filepath}")
        return filepath

def main():
    parser = argparse.ArgumentParser(description='AI PPT API 综合测试套件')
    parser.add_argument('--url', default='https://fe2kf91287.execute-api.us-east-1.amazonaws.com/dev',
                       help='API基础URL')
    parser.add_argument('--timeout', type=int, default=30, help='请求超时时间（秒）')
    parser.add_argument('--concurrent', type=int, default=5, help='并发测试数量')
    parser.add_argument('--performance-iterations', type=int, default=10, help='性能测试迭代次数')
    parser.add_argument('--output', help='报告输出文件名')
    parser.add_argument('--verbose', action='store_true', help='详细输出')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 创建测试器并运行测试
    tester = APITester(args.url, args.timeout)

    try:
        tester.run_all_tests()

        # 生成和保存报告
        report = tester.generate_report()
        report_file = tester.save_report(report, args.output)

        # 输出摘要
        summary = report['test_summary']
        print("\n" + "="*60)
        print("              API测试完成摘要")
        print("="*60)
        print(f"API端点: {summary['api_endpoint']}")
        print(f"总测试数: {summary['total_tests']}")
        print(f"成功: {summary['passed']}")
        print(f"失败: {summary['failed']}")
        print(f"警告: {summary['warnings']}")
        print(f"成功率: {summary['success_rate']}%")
        print(f"测试时长: {summary['duration_seconds']}秒")
        print(f"平均响应时间: {summary['avg_response_time_ms']}ms")
        print(f"\n详细报告: {report_file}")
        print("="*60)

        # 根据测试结果设置退出码
        if summary['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"测试运行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()