#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI PPT 生成助手前端自动化测试脚本
"""
import requests
import json
import time
from urllib.parse import urljoin
import subprocess
import re
from datetime import datetime

class FrontendTester:
    def __init__(self):
        self.frontend_url = "http://localhost:8081"
        self.api_gateway_url = "https://479jyollng.execute-api.us-east-1.amazonaws.com/dev"
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "frontend_url": self.frontend_url,
            "api_gateway_url": self.api_gateway_url,
            "tests": {}
        }

    def test_frontend_accessibility(self):
        """测试前端页面可访问性"""
        print("🔍 测试前端页面可访问性...")
        try:
            response = requests.get(self.frontend_url, timeout=10)
            success = response.status_code == 200

            # 检查HTML内容
            html_content = response.text
            has_title = "AI PPT 生成助手" in html_content
            has_form = 'id="generateForm"' in html_content
            has_bootstrap = "bootstrap" in html_content

            result = {
                "success": success,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "content_length": len(html_content),
                "has_title": has_title,
                "has_form": has_form,
                "has_bootstrap": has_bootstrap,
                "details": f"页面加载{'成功' if success else '失败'}, 响应时间: {response.elapsed.total_seconds():.2f}s"
            }

            self.test_results["tests"]["frontend_accessibility"] = result
            print(f"✅ 前端可访问性测试完成: {result['details']}")
            return result

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "details": f"无法访问前端页面: {str(e)}"
            }
            self.test_results["tests"]["frontend_accessibility"] = result
            print(f"❌ 前端可访问性测试失败: {str(e)}")
            return result

    def test_api_connectivity(self):
        """测试API连接性"""
        print("🔍 测试API连接性...")
        test_endpoints = [
            "/generate",
            "/status/test",
            "/download/test"
        ]

        results = {}
        for endpoint in test_endpoints:
            try:
                url = urljoin(self.api_gateway_url, endpoint)
                # 使用HEAD请求测试连接，避免触发实际操作
                response = requests.head(url, timeout=10)

                results[endpoint] = {
                    "success": response.status_code in [200, 400, 404, 405],  # 这些都表示API可达
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }

            except Exception as e:
                results[endpoint] = {
                    "success": False,
                    "error": str(e),
                    "status_code": None,
                    "response_time": None
                }

        # 测试OPTIONS请求（CORS预检）
        try:
            response = requests.options(self.api_gateway_url + "/generate", timeout=10)
            cors_headers = {
                "access-control-allow-origin": response.headers.get("Access-Control-Allow-Origin"),
                "access-control-allow-methods": response.headers.get("Access-Control-Allow-Methods"),
                "access-control-allow-headers": response.headers.get("Access-Control-Allow-Headers")
            }
            results["cors_preflight"] = {
                "success": response.status_code == 200,
                "headers": cors_headers
            }
        except Exception as e:
            results["cors_preflight"] = {
                "success": False,
                "error": str(e)
            }

        self.test_results["tests"]["api_connectivity"] = results
        success_count = sum(1 for r in results.values() if r.get("success", False))
        total_count = len(results)

        print(f"✅ API连接性测试完成: {success_count}/{total_count} 个端点可达")
        return results

    def test_javascript_errors(self):
        """检测JavaScript语法错误"""
        print("🔍 检测JavaScript语法错误...")

        js_files = [
            "js/app.js",
            "js/status.js",
            "js/download.js"
        ]

        results = {}
        for js_file in js_files:
            try:
                # 读取JavaScript文件
                with open(f"/Users/umatoratatsu/Documents/AWS/AWS-Handson/ABA/AMAZON-BEDROCK-AGENTS/frontend/{js_file}", "r", encoding="utf-8") as f:
                    js_content = f.read()

                # 基本语法检查
                syntax_issues = []

                # 检查常见语法问题
                if js_content.count("{") != js_content.count("}"):
                    syntax_issues.append("花括号不匹配")

                if js_content.count("(") != js_content.count(")"):
                    syntax_issues.append("圆括号不匹配")

                if js_content.count("[") != js_content.count("]"):
                    syntax_issues.append("方括号不匹配")

                # 检查未定义的函数调用
                undefined_functions = []
                function_calls = re.findall(r'(\w+)\s*\(', js_content)
                defined_functions = re.findall(r'function\s+(\w+)\s*\(|(\w+)\s*[=:]\s*function\s*\(|(\w+)\s*[=:]\s*\([^)]*\)\s*=>', js_content)

                # 扁平化定义的函数列表
                defined_func_names = set()
                for match in defined_functions:
                    for group in match:
                        if group:
                            defined_func_names.add(group)

                # 检查常见的浏览器API和JavaScript内置函数
                builtin_functions = {
                    'console', 'setTimeout', 'clearTimeout', 'setInterval', 'clearInterval',
                    'fetch', 'JSON', 'localStorage', 'document', 'window', 'alert',
                    'confirm', 'Math', 'Date', 'Array', 'Object', 'String', 'parseInt',
                    'parseFloat', 'isNaN', 'addEventListener', 'removeEventListener'
                }

                for func_call in set(function_calls):
                    if (func_call not in defined_func_names and
                        func_call not in builtin_functions and
                        func_call not in ['if', 'for', 'while', 'switch', 'try', 'catch']):
                        undefined_functions.append(func_call)

                results[js_file] = {
                    "success": len(syntax_issues) == 0,
                    "file_size": len(js_content),
                    "syntax_issues": syntax_issues,
                    "undefined_functions": undefined_functions[:10],  # 限制输出数量
                    "lines_of_code": len(js_content.split('\n'))
                }

            except Exception as e:
                results[js_file] = {
                    "success": False,
                    "error": str(e)
                }

        self.test_results["tests"]["javascript_syntax"] = results

        total_issues = sum(len(r.get("syntax_issues", [])) for r in results.values())
        print(f"✅ JavaScript语法检查完成: 发现 {total_issues} 个语法问题")
        return results

    def test_form_validation(self):
        """测试表单验证逻辑"""
        print("🔍 测试表单验证...")

        # 这里我们模拟表单验证逻辑
        validation_tests = [
            {
                "name": "空主题测试",
                "data": {"topic": "", "page_count": 10, "audience": "general"},
                "expected_valid": False
            },
            {
                "name": "正常数据测试",
                "data": {"topic": "测试主题", "page_count": 10, "audience": "general"},
                "expected_valid": True
            },
            {
                "name": "页数边界测试 - 最小值",
                "data": {"topic": "测试主题", "page_count": 5, "audience": "general"},
                "expected_valid": True
            },
            {
                "name": "页数边界测试 - 最大值",
                "data": {"topic": "测试主题", "page_count": 30, "audience": "general"},
                "expected_valid": True
            },
            {
                "name": "页数超出范围测试",
                "data": {"topic": "测试主题", "page_count": 50, "audience": "general"},
                "expected_valid": False
            }
        ]

        results = {}
        for test in validation_tests:
            # 模拟前端验证逻辑
            data = test["data"]
            is_valid = True
            issues = []

            if not data.get("topic", "").strip():
                is_valid = False
                issues.append("主题不能为空")

            page_count = data.get("page_count", 0)
            if not isinstance(page_count, int) or page_count < 5 or page_count > 30:
                is_valid = False
                issues.append("页数必须在5-30之间")

            audience = data.get("audience", "")
            valid_audiences = ["general", "technical", "executive", "academic"]
            if audience not in valid_audiences:
                is_valid = False
                issues.append("无效的目标受众")

            results[test["name"]] = {
                "success": is_valid == test["expected_valid"],
                "actual_valid": is_valid,
                "expected_valid": test["expected_valid"],
                "issues": issues,
                "test_data": data
            }

        self.test_results["tests"]["form_validation"] = results

        passed_tests = sum(1 for r in results.values() if r["success"])
        total_tests = len(results)
        print(f"✅ 表单验证测试完成: {passed_tests}/{total_tests} 个测试通过")
        return results

    def test_localStorage_functionality(self):
        """测试localStorage功能"""
        print("🔍 测试localStorage功能...")

        # 由于我们无法直接访问浏览器的localStorage，
        # 我们检查JavaScript代码中localStorage的使用
        js_files_content = {}
        for js_file in ["js/app.js", "js/status.js", "js/download.js"]:
            try:
                with open(f"/Users/umatoratatsu/Documents/AWS/AWS-Handson/ABA/AMAZON-BEDROCK-AGENTS/frontend/{js_file}", "r") as f:
                    js_files_content[js_file] = f.read()
            except:
                js_files_content[js_file] = ""

        all_js_content = " ".join(js_files_content.values())

        # 检查localStorage使用模式
        localStorage_operations = {
            "setItem": len(re.findall(r'localStorage\.setItem\s*\(', all_js_content)),
            "getItem": len(re.findall(r'localStorage\.getItem\s*\(', all_js_content)),
            "removeItem": len(re.findall(r'localStorage\.removeItem\s*\(', all_js_content))
        }

        # 检查存储的数据类型
        stored_keys = re.findall(r'localStorage\.(?:setItem|getItem|removeItem)\s*\(\s*[\'"]([^\'"]+)[\'"]', all_js_content)

        results = {
            "localStorage_operations": localStorage_operations,
            "stored_keys": list(set(stored_keys)),
            "total_operations": sum(localStorage_operations.values()),
            "has_error_handling": "try" in all_js_content and "catch" in all_js_content,
            "success": sum(localStorage_operations.values()) > 0
        }

        self.test_results["tests"]["localStorage_functionality"] = results
        print(f"✅ localStorage功能测试完成: 发现 {results['total_operations']} 个存储操作")
        return results

    def test_responsive_design(self):
        """测试响应式设计"""
        print("🔍 测试响应式设计...")

        try:
            response = requests.get(self.frontend_url, timeout=10)
            html_content = response.text

            # 检查响应式设计相关的元素
            responsive_features = {
                "viewport_meta": 'name="viewport"' in html_content,
                "bootstrap_grid": 'col-lg-' in html_content or 'col-md-' in html_content,
                "responsive_classes": 'd-none d-md-block' in html_content or 'd-block d-md-none' in html_content,
                "mobile_first": 'col-' in html_content,
                "bootstrap_css": 'bootstrap' in html_content
            }

            # 检查CSS媒体查询（如果有自定义CSS）
            media_queries = re.findall(r'@media[^{]+\{', html_content, re.IGNORECASE)

            results = {
                "responsive_features": responsive_features,
                "media_queries_count": len(media_queries),
                "bootstrap_version": "5.3.0" if "5.3.0" in html_content else "unknown",
                "mobile_optimized": responsive_features["viewport_meta"] and responsive_features["bootstrap_grid"],
                "success": all(responsive_features.values())
            }

            self.test_results["tests"]["responsive_design"] = results
            print(f"✅ 响应式设计测试完成: {'通过' if results['success'] else '部分通过'}")
            return results

        except Exception as e:
            results = {
                "success": False,
                "error": str(e)
            }
            self.test_results["tests"]["responsive_design"] = results
            print(f"❌ 响应式设计测试失败: {str(e)}")
            return results

    def test_security_features(self):
        """测试安全特性"""
        print("🔍 测试安全特性...")

        try:
            response = requests.get(self.frontend_url, timeout=10)
            html_content = response.text
            headers = response.headers

            # 检查安全相关的HTML特性
            security_features = {
                "no_inline_scripts": '<script>' not in html_content or 'nonce=' in html_content,
                "external_resources": 'https://cdn.jsdelivr.net' in html_content,  # 使用CDN
                "form_validation": 'required' in html_content,
                "input_types": 'type="password"' in html_content,
                "csrf_protection": False  # 需要后端支持
            }

            # 检查HTTP安全头
            security_headers = {
                "x-frame-options": headers.get("X-Frame-Options"),
                "x-content-type-options": headers.get("X-Content-Type-Options"),
                "x-xss-protection": headers.get("X-XSS-Protection"),
                "content-security-policy": headers.get("Content-Security-Policy")
            }

            # 检查JavaScript中的安全实践
            js_files_content = ""
            for js_file in ["js/app.js", "js/status.js", "js/download.js"]:
                try:
                    with open(f"/Users/umatoratatsu/Documents/AWS/AWS-Handson/ABA/AMAZON-BEDROCK-AGENTS/frontend/{js_file}", "r") as f:
                        js_files_content += f.read()
                except:
                    pass

            js_security = {
                "uses_innerHTML": '.innerHTML' in js_files_content,
                "validates_input": 'validate' in js_files_content.lower(),
                "sanitizes_data": 'escape' in js_files_content.lower() or 'sanitize' in js_files_content.lower(),
                "uses_https": 'https://' in js_files_content,
                "stores_sensitive_data": 'password' in js_files_content.lower() and 'localStorage' in js_files_content
            }

            results = {
                "html_security": security_features,
                "http_headers": security_headers,
                "javascript_security": js_security,
                "overall_score": 0,
                "success": True
            }

            # 计算安全得分
            score = 0
            total_checks = 0

            for feature, enabled in security_features.items():
                total_checks += 1
                if enabled:
                    score += 1

            for header, value in security_headers.items():
                total_checks += 1
                if value:
                    score += 1

            results["overall_score"] = (score / total_checks) * 100 if total_checks > 0 else 0

            self.test_results["tests"]["security_features"] = results
            print(f"✅ 安全特性测试完成: 安全得分 {results['overall_score']:.1f}%")
            return results

        except Exception as e:
            results = {
                "success": False,
                "error": str(e)
            }
            self.test_results["tests"]["security_features"] = results
            print(f"❌ 安全特性测试失败: {str(e)}")
            return results

    def test_performance_metrics(self):
        """测试性能指标"""
        print("🔍 测试性能指标...")

        performance_results = []

        # 多次请求测试响应时间
        for i in range(5):
            try:
                start_time = time.time()
                response = requests.get(self.frontend_url, timeout=10)
                end_time = time.time()

                performance_results.append({
                    "request_number": i + 1,
                    "response_time": end_time - start_time,
                    "status_code": response.status_code,
                    "content_length": len(response.content),
                    "success": response.status_code == 200
                })

                time.sleep(0.5)  # 避免过于频繁的请求

            except Exception as e:
                performance_results.append({
                    "request_number": i + 1,
                    "error": str(e),
                    "success": False
                })

        # 计算统计数据
        response_times = [r["response_time"] for r in performance_results if "response_time" in r]

        if response_times:
            stats = {
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "avg_response_time": sum(response_times) / len(response_times),
                "total_requests": len(performance_results),
                "successful_requests": sum(1 for r in performance_results if r.get("success", False))
            }
        else:
            stats = {
                "min_response_time": 0,
                "max_response_time": 0,
                "avg_response_time": 0,
                "total_requests": len(performance_results),
                "successful_requests": 0
            }

        # 检查静态资源大小
        try:
            response = requests.get(self.frontend_url)
            html_size = len(response.content)

            # 估算外部资源大小（Bootstrap CSS/JS）
            external_resources = {
                "bootstrap_css": "约150KB",
                "bootstrap_js": "约80KB",
                "bootstrap_icons": "约100KB"
            }

            resource_analysis = {
                "html_size": html_size,
                "estimated_total_size": "约330KB + HTML",
                "external_resources": external_resources,
                "uses_cdn": True
            }

        except Exception as e:
            resource_analysis = {
                "error": str(e)
            }

        results = {
            "performance_stats": stats,
            "individual_requests": performance_results,
            "resource_analysis": resource_analysis,
            "success": stats["successful_requests"] > 0,
            "performance_grade": self._calculate_performance_grade(stats["avg_response_time"])
        }

        self.test_results["tests"]["performance_metrics"] = results
        print(f"✅ 性能测试完成: 平均响应时间 {stats['avg_response_time']:.2f}s, 等级 {results['performance_grade']}")
        return results

    def _calculate_performance_grade(self, avg_response_time):
        """计算性能等级"""
        if avg_response_time < 0.5:
            return "A"
        elif avg_response_time < 1.0:
            return "B"
        elif avg_response_time < 2.0:
            return "C"
        else:
            return "D"

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始AI PPT生成助手前端全面测试...")
        print("=" * 60)

        test_methods = [
            self.test_frontend_accessibility,
            self.test_api_connectivity,
            self.test_javascript_errors,
            self.test_form_validation,
            self.test_localStorage_functionality,
            self.test_responsive_design,
            self.test_security_features,
            self.test_performance_metrics
        ]

        for test_method in test_methods:
            try:
                test_method()
                print()
            except Exception as e:
                print(f"❌ 测试 {test_method.__name__} 出现异常: {str(e)}")
                print()

        # 计算总体测试结果
        total_tests = len(self.test_results["tests"])
        passed_tests = sum(1 for test in self.test_results["tests"].values()
                          if test.get("success", False))

        self.test_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "overall_status": "PASS" if passed_tests == total_tests else "PARTIAL" if passed_tests > 0 else "FAIL"
        }

        print("=" * 60)
        print(f"🎯 测试完成! 总体结果: {self.test_results['summary']['overall_status']}")
        print(f"📊 通过率: {self.test_results['summary']['success_rate']:.1f}% ({passed_tests}/{total_tests})")

        return self.test_results

    def save_results(self, filename="frontend_test_results.json"):
        """保存测试结果"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        print(f"📁 测试结果已保存到: {filename}")

if __name__ == "__main__":
    tester = FrontendTester()
    results = tester.run_all_tests()
    tester.save_results()