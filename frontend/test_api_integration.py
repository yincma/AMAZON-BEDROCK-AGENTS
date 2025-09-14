#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端API集成测试
"""
import requests
import json
import time
from datetime import datetime

class APIIntegrationTester:
    def __init__(self):
        self.api_base_url = "https://479jyollng.execute-api.us-east-1.amazonaws.com/dev"
        self.test_presentation_id = None
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "api_base_url": self.api_base_url,
            "tests": {}
        }

    def test_generate_presentation(self):
        """测试生成演示文稿API"""
        print("🔍 测试生成演示文稿API...")

        test_data = {
            "topic": "人工智能在前端测试中的应用",
            "page_count": 5,
            "audience": "technical"
        }

        try:
            response = requests.post(
                f"{self.api_base_url}/generate",
                json=test_data,
                headers={
                    "Content-Type": "application/json"
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                self.test_presentation_id = data.get("presentation_id")

                result = {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "presentation_id": self.test_presentation_id,
                    "response_data": data,
                    "details": "生成请求成功提交"
                }
            else:
                result = {
                    "success": False,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "error": response.text,
                    "details": f"生成请求失败，状态码: {response.status_code}"
                }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "details": f"API调用异常: {str(e)}"
            }

        self.test_results["tests"]["generate_presentation"] = result
        print(f"{'✅' if result['success'] else '❌'} 生成API测试: {result['details']}")
        return result

    def test_status_polling(self):
        """测试状态轮询API"""
        print("🔍 测试状态轮询API...")

        if not self.test_presentation_id:
            result = {
                "success": False,
                "details": "无法测试状态API，因为没有有效的presentation_id"
            }
            self.test_results["tests"]["status_polling"] = result
            print(f"❌ 状态API测试: {result['details']}")
            return result

        try:
            # 轮询几次状态
            status_responses = []
            for i in range(3):
                response = requests.get(
                    f"{self.api_base_url}/status/{self.test_presentation_id}",
                    timeout=15
                )

                status_data = {
                    "attempt": i + 1,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }

                if response.status_code == 200:
                    data = response.json()
                    status_data.update({
                        "status": data.get("status"),
                        "progress": data.get("progress"),
                        "message": data.get("message")
                    })

                status_responses.append(status_data)
                time.sleep(2)  # 等待2秒

            # 分析状态响应
            successful_requests = [r for r in status_responses if r["status_code"] == 200]

            result = {
                "success": len(successful_requests) > 0,
                "total_requests": len(status_responses),
                "successful_requests": len(successful_requests),
                "status_responses": status_responses,
                "details": f"状态轮询: {len(successful_requests)}/{len(status_responses)} 次成功"
            }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "details": f"状态轮询异常: {str(e)}"
            }

        self.test_results["tests"]["status_polling"] = result
        print(f"{'✅' if result['success'] else '❌'} 状态API测试: {result['details']}")
        return result

    def test_download_api(self):
        """测试下载API"""
        print("🔍 测试下载API...")

        if not self.test_presentation_id:
            result = {
                "success": False,
                "details": "无法测试下载API，因为没有有效的presentation_id"
            }
            self.test_results["tests"]["download_api"] = result
            print(f"❌ 下载API测试: {result['details']}")
            return result

        try:
            response = requests.get(
                f"{self.api_base_url}/download/{self.test_presentation_id}",
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                result = {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "download_url": data.get("download_url"),
                    "details": "下载链接获取成功"
                }
            else:
                result = {
                    "success": False,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "error": response.text,
                    "details": f"下载API失败，状态码: {response.status_code}"
                }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "details": f"下载API异常: {str(e)}"
            }

        self.test_results["tests"]["download_api"] = result
        print(f"{'✅' if result['success'] else '❌'} 下载API测试: {result['details']}")
        return result

    def test_cors_headers(self):
        """测试CORS头部"""
        print("🔍 测试CORS配置...")

        try:
            # 发送OPTIONS预检请求
            response = requests.options(
                f"{self.api_base_url}/generate",
                headers={
                    "Origin": "http://localhost:8081",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                },
                timeout=10
            )

            cors_headers = {
                "access-control-allow-origin": response.headers.get("Access-Control-Allow-Origin", ""),
                "access-control-allow-methods": response.headers.get("Access-Control-Allow-Methods", ""),
                "access-control-allow-headers": response.headers.get("Access-Control-Allow-Headers", ""),
                "access-control-max-age": response.headers.get("Access-Control-Max-Age", "")
            }

            # 检查CORS配置是否正确
            cors_issues = []
            if not cors_headers["access-control-allow-origin"]:
                cors_issues.append("缺少 Access-Control-Allow-Origin 头部")
            elif cors_headers["access-control-allow-origin"] not in ["*", "http://localhost:8081"]:
                cors_issues.append("Origin不被允许")

            if "POST" not in cors_headers.get("access-control-allow-methods", ""):
                cors_issues.append("POST方法不被允许")

            if "Content-Type" not in cors_headers.get("access-control-allow-headers", ""):
                cors_issues.append("Content-Type头部不被允许")

            result = {
                "success": len(cors_issues) == 0,
                "status_code": response.status_code,
                "cors_headers": cors_headers,
                "cors_issues": cors_issues,
                "details": f"CORS配置{'正确' if len(cors_issues) == 0 else '存在问题'}"
            }

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "details": f"CORS测试异常: {str(e)}"
            }

        self.test_results["tests"]["cors_headers"] = result
        print(f"{'✅' if result['success'] else '❌'} CORS测试: {result['details']}")
        return result

    def test_error_handling(self):
        """测试错误处理"""
        print("🔍 测试API错误处理...")

        error_tests = [
            {
                "name": "无效的JSON数据",
                "url": f"{self.api_base_url}/generate",
                "method": "POST",
                "data": "invalid json",
                "headers": {"Content-Type": "application/json"}
            },
            {
                "name": "缺少必需字段",
                "url": f"{self.api_base_url}/generate",
                "method": "POST",
                "data": json.dumps({"page_count": 10}),
                "headers": {"Content-Type": "application/json"}
            },
            {
                "name": "无效的presentation_id",
                "url": f"{self.api_base_url}/status/invalid-id",
                "method": "GET",
                "data": None,
                "headers": {}
            }
        ]

        results = {}
        for test in error_tests:
            try:
                if test["method"] == "POST":
                    response = requests.post(
                        test["url"],
                        data=test["data"],
                        headers=test["headers"],
                        timeout=10
                    )
                else:
                    response = requests.get(
                        test["url"],
                        headers=test["headers"],
                        timeout=10
                    )

                # 错误处理测试应该返回适当的错误状态码
                expected_error_codes = [400, 404, 422, 500]
                is_proper_error = response.status_code in expected_error_codes

                results[test["name"]] = {
                    "success": is_proper_error,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds(),
                    "response_text": response.text[:200] if response.text else "",
                    "details": f"返回状态码 {response.status_code}"
                }

            except Exception as e:
                results[test["name"]] = {
                    "success": False,
                    "error": str(e),
                    "details": f"请求异常: {str(e)}"
                }

        overall_success = sum(1 for r in results.values() if r.get("success", False))
        total_tests = len(results)

        self.test_results["tests"]["error_handling"] = {
            "overall_success": overall_success == total_tests,
            "passed_tests": overall_success,
            "total_tests": total_tests,
            "individual_results": results,
            "details": f"错误处理测试: {overall_success}/{total_tests} 通过"
        }

        print(f"{'✅' if overall_success == total_tests else '❌'} 错误处理测试: {overall_success}/{total_tests} 通过")
        return self.test_results["tests"]["error_handling"]

    def run_all_tests(self):
        """运行所有API集成测试"""
        print("🚀 开始API集成测试...")
        print("=" * 60)

        test_methods = [
            self.test_generate_presentation,
            self.test_status_polling,
            self.test_download_api,
            self.test_cors_headers,
            self.test_error_handling
        ]

        for test_method in test_methods:
            try:
                test_method()
                print()
            except Exception as e:
                print(f"❌ 测试 {test_method.__name__} 出现异常: {str(e)}")
                print()

        # 计算总体结果
        passed_tests = 0
        total_tests = 0

        for test_name, test_result in self.test_results["tests"].items():
            total_tests += 1
            if test_result.get("success", False) or test_result.get("overall_success", False):
                passed_tests += 1

        self.test_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "overall_status": "PASS" if passed_tests == total_tests else "PARTIAL" if passed_tests > 0 else "FAIL"
        }

        print("=" * 60)
        print(f"🎯 API集成测试完成! 总体结果: {self.test_results['summary']['overall_status']}")
        print(f"📊 通过率: {self.test_results['summary']['success_rate']:.1f}% ({passed_tests}/{total_tests})")

        return self.test_results

    def save_results(self, filename="api_integration_test_results.json"):
        """保存测试结果"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        print(f"📁 API测试结果已保存到: {filename}")

if __name__ == "__main__":
    tester = APIIntegrationTester()
    results = tester.run_all_tests()
    tester.save_results()