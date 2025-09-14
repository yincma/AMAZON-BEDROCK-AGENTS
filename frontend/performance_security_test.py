#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端性能和安全测试
"""
import requests
import time
import concurrent.futures
import re
import subprocess
import json
from datetime import datetime
import statistics
import urllib3
from urllib.parse import urljoin
import ssl
import socket

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PerformanceSecurityTester:
    def __init__(self):
        self.frontend_url = "http://localhost:8081"
        self.api_base_url = "https://479jyollng.execute-api.us-east-1.amazonaws.com/dev"
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "frontend_url": self.frontend_url,
            "api_base_url": self.api_base_url,
            "tests": {}
        }

    def test_load_performance(self):
        """测试负载性能"""
        print("🔍 测试前端负载性能...")

        # 单次加载性能测试
        single_load_times = []
        for i in range(10):
            start_time = time.time()
            try:
                response = requests.get(self.frontend_url, timeout=30)
                end_time = time.time()

                if response.status_code == 200:
                    load_time = end_time - start_time
                    single_load_times.append(load_time)

            except Exception as e:
                print(f"第{i+1}次加载失败: {e}")

            time.sleep(0.5)  # 间隔0.5秒

        # 并发加载测试
        def concurrent_load():
            start_time = time.time()
            try:
                response = requests.get(self.frontend_url, timeout=10)
                end_time = time.time()
                return {
                    "success": response.status_code == 200,
                    "load_time": end_time - start_time,
                    "status_code": response.status_code,
                    "content_length": len(response.content) if response.content else 0
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "load_time": None
                }

        print("   执行并发负载测试 (5个并发用户)...")
        concurrent_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(concurrent_load) for _ in range(5)]
            concurrent_results = [future.result() for future in futures]

        # 分析性能数据
        successful_loads = [r for r in concurrent_results if r["success"]]
        concurrent_load_times = [r["load_time"] for r in successful_loads if r["load_time"]]

        performance_metrics = {
            "single_load_performance": {
                "total_tests": len(single_load_times),
                "successful_loads": len(single_load_times),
                "average_load_time": statistics.mean(single_load_times) if single_load_times else 0,
                "min_load_time": min(single_load_times) if single_load_times else 0,
                "max_load_time": max(single_load_times) if single_load_times else 0,
                "median_load_time": statistics.median(single_load_times) if single_load_times else 0
            },
            "concurrent_load_performance": {
                "total_tests": len(concurrent_results),
                "successful_loads": len(successful_loads),
                "average_load_time": statistics.mean(concurrent_load_times) if concurrent_load_times else 0,
                "min_load_time": min(concurrent_load_times) if concurrent_load_times else 0,
                "max_load_time": max(concurrent_load_times) if concurrent_load_times else 0
            },
            "performance_grade": self._calculate_performance_grade(
                statistics.mean(single_load_times) if single_load_times else float('inf')
            )
        }

        result = {
            "success": len(single_load_times) >= 8,  # 至少80%成功率
            "metrics": performance_metrics,
            "concurrent_results": concurrent_results,
            "details": f"平均加载时间: {performance_metrics['single_load_performance']['average_load_time']:.2f}s, 等级: {performance_metrics['performance_grade']}"
        }

        self.test_results["tests"]["load_performance"] = result
        print(f"✅ 负载性能测试完成: {result['details']}")
        return result

    def test_resource_optimization(self):
        """测试资源优化"""
        print("🔍 测试资源优化...")

        try:
            response = requests.get(self.frontend_url, timeout=15)
            html_content = response.text

            # 分析HTML内容
            resource_analysis = {
                "html_size": len(html_content.encode('utf-8')),
                "external_css_count": len(re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>', html_content)),
                "external_js_count": len(re.findall(r'<script[^>]+src=[^>]*>', html_content)),
                "inline_css_count": len(re.findall(r'<style[^>]*>.*?</style>', html_content, re.DOTALL)),
                "inline_js_count": len(re.findall(r'<script[^>]*>.*?</script>', html_content, re.DOTALL)),
                "image_count": len(re.findall(r'<img[^>]+src=[^>]*>', html_content)),
                "uses_cdn": "cdn.jsdelivr.net" in html_content
            }

            # 检查是否使用了压缩
            compression_headers = {
                "content-encoding": response.headers.get("Content-Encoding", ""),
                "content-length": response.headers.get("Content-Length", ""),
                "cache-control": response.headers.get("Cache-Control", "")
            }

            # 资源优化评分
            optimization_score = 0
            optimization_checks = []

            # CDN使用检查
            if resource_analysis["uses_cdn"]:
                optimization_score += 20
                optimization_checks.append("✅ 使用CDN加载外部资源")
            else:
                optimization_checks.append("❌ 未使用CDN")

            # 外部资源数量检查
            total_external_resources = resource_analysis["external_css_count"] + resource_analysis["external_js_count"]
            if total_external_resources <= 5:
                optimization_score += 20
                optimization_checks.append("✅ 外部资源数量合理")
            else:
                optimization_checks.append(f"⚠️  外部资源较多 ({total_external_resources}个)")

            # HTML大小检查
            if resource_analysis["html_size"] <= 50000:  # 50KB
                optimization_score += 20
                optimization_checks.append("✅ HTML文件大小合理")
            else:
                optimization_checks.append(f"⚠️  HTML文件较大 ({resource_analysis['html_size']/1024:.1f}KB)")

            # 内联资源检查
            if resource_analysis["inline_css_count"] + resource_analysis["inline_js_count"] <= 2:
                optimization_score += 20
                optimization_checks.append("✅ 内联资源使用合理")
            else:
                optimization_checks.append("⚠️  内联资源较多")

            # 图片优化检查
            if resource_analysis["image_count"] <= 5:
                optimization_score += 20
                optimization_checks.append("✅ 图片资源数量合理")
            else:
                optimization_checks.append(f"⚠️  图片资源较多 ({resource_analysis['image_count']}个)")

            result = {
                "success": optimization_score >= 60,
                "optimization_score": optimization_score,
                "resource_analysis": resource_analysis,
                "compression_headers": compression_headers,
                "optimization_checks": optimization_checks,
                "details": f"资源优化得分: {optimization_score}/100"
            }

            self.test_results["tests"]["resource_optimization"] = result
            print(f"{'✅' if result['success'] else '⚠️ '} 资源优化测试完成: {result['details']}")
            return result

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "details": f"资源优化测试异常: {str(e)}"
            }
            self.test_results["tests"]["resource_optimization"] = result
            print(f"❌ 资源优化测试失败: {str(e)}")
            return result

    def test_security_headers(self):
        """测试安全头部"""
        print("🔍 测试HTTP安全头部...")

        try:
            response = requests.get(self.frontend_url, timeout=10)
            headers = response.headers

            security_headers_check = {
                "X-Frame-Options": {
                    "present": "X-Frame-Options" in headers,
                    "value": headers.get("X-Frame-Options", ""),
                    "secure": headers.get("X-Frame-Options", "").upper() in ["DENY", "SAMEORIGIN"]
                },
                "X-Content-Type-Options": {
                    "present": "X-Content-Type-Options" in headers,
                    "value": headers.get("X-Content-Type-Options", ""),
                    "secure": headers.get("X-Content-Type-Options", "").lower() == "nosniff"
                },
                "X-XSS-Protection": {
                    "present": "X-XSS-Protection" in headers,
                    "value": headers.get("X-XSS-Protection", ""),
                    "secure": headers.get("X-XSS-Protection", "").startswith("1")
                },
                "Content-Security-Policy": {
                    "present": "Content-Security-Policy" in headers,
                    "value": headers.get("Content-Security-Policy", ""),
                    "secure": "Content-Security-Policy" in headers
                },
                "Strict-Transport-Security": {
                    "present": "Strict-Transport-Security" in headers,
                    "value": headers.get("Strict-Transport-Security", ""),
                    "secure": "Strict-Transport-Security" in headers
                }
            }

            # 计算安全头部得分
            security_score = 0
            total_headers = len(security_headers_check)

            for header_name, check in security_headers_check.items():
                if check["secure"]:
                    security_score += 1

            security_percentage = (security_score / total_headers) * 100

            result = {
                "success": security_score >= 2,  # 至少2个安全头部
                "security_headers": security_headers_check,
                "security_score": security_score,
                "total_headers": total_headers,
                "security_percentage": security_percentage,
                "details": f"安全头部: {security_score}/{total_headers} ({security_percentage:.1f}%)"
            }

            self.test_results["tests"]["security_headers"] = result
            print(f"{'✅' if result['success'] else '⚠️ '} 安全头部测试完成: {result['details']}")
            return result

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "details": f"安全头部测试异常: {str(e)}"
            }
            self.test_results["tests"]["security_headers"] = result
            print(f"❌ 安全头部测试失败: {str(e)}")
            return result

    def test_xss_injection(self):
        """测试XSS注入防护"""
        print("🔍 测试XSS注入防护...")

        # 常见的XSS攻击向量
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
            "<iframe src=javascript:alert('XSS')></iframe>"
        ]

        xss_test_results = []

        try:
            # 获取原始页面内容
            response = requests.get(self.frontend_url, timeout=10)
            original_content = response.text

            # 检查页面是否已经包含任何可执行的脚本内容
            has_inline_scripts = '<script>' in original_content
            has_event_handlers = re.search(r'on\w+\s*=', original_content, re.IGNORECASE)

            # 模拟通过URL参数注入（如果支持）
            for i, payload in enumerate(xss_payloads):
                test_result = {
                    "payload": payload,
                    "payload_index": i + 1,
                    "reflected": False,
                    "executed": False,
                    "sanitized": True
                }

                try:
                    # 测试URL参数注入
                    test_url = f"{self.frontend_url}?test={payload}"
                    response = requests.get(test_url, timeout=5)

                    # 检查payload是否被反射到响应中
                    if payload in response.text:
                        test_result["reflected"] = True
                        test_result["sanitized"] = False

                    # 检查是否包含可执行的脚本
                    if any(dangerous in response.text.lower() for dangerous in ['<script', 'javascript:', 'onerror=', 'onload=']):
                        test_result["executed"] = True
                        test_result["sanitized"] = False

                except Exception as e:
                    test_result["error"] = str(e)

                xss_test_results.append(test_result)

            # 分析XSS防护效果
            reflected_payloads = [r for r in xss_test_results if r.get("reflected", False)]
            executed_payloads = [r for r in xss_test_results if r.get("executed", False)]

            result = {
                "success": len(executed_payloads) == 0,
                "total_payloads": len(xss_payloads),
                "reflected_payloads": len(reflected_payloads),
                "executed_payloads": len(executed_payloads),
                "xss_test_results": xss_test_results,
                "has_inline_scripts": has_inline_scripts,
                "has_event_handlers": bool(has_event_handlers),
                "protection_level": "高" if len(executed_payloads) == 0 else "中" if len(executed_payloads) <= 2 else "低",
                "details": f"XSS防护: {len(executed_payloads)}/{len(xss_payloads)} 个攻击向量被阻止"
            }

            self.test_results["tests"]["xss_injection"] = result
            print(f"{'✅' if result['success'] else '❌'} XSS注入测试完成: {result['details']}")
            return result

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "details": f"XSS注入测试异常: {str(e)}"
            }
            self.test_results["tests"]["xss_injection"] = result
            print(f"❌ XSS注入测试失败: {str(e)}")
            return result

    def test_ssl_api_security(self):
        """测试API SSL安全配置"""
        print("🔍 测试API SSL安全配置...")

        try:
            # 解析API URL
            from urllib.parse import urlparse
            parsed_url = urlparse(self.api_base_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or 443

            # SSL连接测试
            ssl_info = {}
            try:
                context = ssl.create_default_context()
                with socket.create_connection((hostname, port), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        ssl_info = {
                            "protocol": ssock.version(),
                            "cipher": ssock.cipher(),
                            "server_hostname": ssock.server_hostname,
                            "peer_cert": ssock.getpeercert()
                        }
            except Exception as ssl_error:
                ssl_info = {"error": str(ssl_error)}

            # 测试API端点的SSL配置
            try:
                response = requests.get(self.api_base_url + "/generate",
                                      timeout=10, verify=True)
                ssl_response_info = {
                    "ssl_verify_success": True,
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
            except requests.exceptions.SSLError as e:
                ssl_response_info = {
                    "ssl_verify_success": False,
                    "ssl_error": str(e)
                }
            except Exception as e:
                ssl_response_info = {
                    "ssl_verify_success": True,  # 其他错误不是SSL问题
                    "other_error": str(e)
                }

            # 评估SSL安全性
            ssl_security_score = 0
            ssl_checks = []

            # 检查协议版本
            if ssl_info.get("protocol") in ["TLSv1.2", "TLSv1.3"]:
                ssl_security_score += 25
                ssl_checks.append(f"✅ 使用安全的TLS协议: {ssl_info.get('protocol')}")
            else:
                ssl_checks.append(f"⚠️  TLS协议版本: {ssl_info.get('protocol', 'Unknown')}")

            # 检查证书验证
            if ssl_response_info.get("ssl_verify_success"):
                ssl_security_score += 25
                ssl_checks.append("✅ SSL证书验证通过")
            else:
                ssl_checks.append("❌ SSL证书验证失败")

            # 检查HSTS头部
            hsts_header = ssl_response_info.get("headers", {}).get("Strict-Transport-Security")
            if hsts_header:
                ssl_security_score += 25
                ssl_checks.append("✅ 配置了HSTS头部")
            else:
                ssl_checks.append("⚠️  未配置HSTS头部")

            # 检查是否强制HTTPS
            if self.api_base_url.startswith("https://"):
                ssl_security_score += 25
                ssl_checks.append("✅ 使用HTTPS协议")
            else:
                ssl_checks.append("❌ 未使用HTTPS协议")

            result = {
                "success": ssl_security_score >= 75,
                "ssl_info": ssl_info,
                "ssl_response_info": ssl_response_info,
                "ssl_security_score": ssl_security_score,
                "ssl_checks": ssl_checks,
                "details": f"SSL安全得分: {ssl_security_score}/100"
            }

            self.test_results["tests"]["ssl_api_security"] = result
            print(f"{'✅' if result['success'] else '⚠️ '} API SSL安全测试完成: {result['details']}")
            return result

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "details": f"SSL安全测试异常: {str(e)}"
            }
            self.test_results["tests"]["ssl_api_security"] = result
            print(f"❌ SSL安全测试失败: {str(e)}")
            return result

    def test_browser_compatibility(self):
        """测试浏览器兼容性（通过User-Agent模拟）"""
        print("🔍 测试浏览器兼容性...")

        user_agents = {
            "Chrome": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Edge": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mobile Chrome": "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mobile Safari": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1"
        }

        compatibility_results = {}

        for browser, user_agent in user_agents.items():
            try:
                headers = {"User-Agent": user_agent}
                response = requests.get(self.frontend_url, headers=headers, timeout=10)

                # 基本兼容性检查
                compatibility_check = {
                    "response_successful": response.status_code == 200,
                    "content_length": len(response.content),
                    "has_html5_doctype": response.text.strip().startswith("<!DOCTYPE html>"),
                    "has_viewport_meta": 'name="viewport"' in response.text,
                    "has_bootstrap": "bootstrap" in response.text.lower(),
                    "response_time": response.elapsed.total_seconds()
                }

                # 移动设备特殊检查
                if "Mobile" in browser:
                    compatibility_check["mobile_optimized"] = (
                        compatibility_check["has_viewport_meta"] and
                        "col-" in response.text  # Bootstrap响应式类
                    )

                compatibility_results[browser] = {
                    "success": compatibility_check["response_successful"],
                    "compatibility_check": compatibility_check,
                    "user_agent": user_agent
                }

            except Exception as e:
                compatibility_results[browser] = {
                    "success": False,
                    "error": str(e),
                    "user_agent": user_agent
                }

        # 计算兼容性统计
        successful_browsers = sum(1 for r in compatibility_results.values() if r["success"])
        total_browsers = len(compatibility_results)

        result = {
            "success": successful_browsers >= total_browsers * 0.8,  # 80%兼容率
            "compatibility_results": compatibility_results,
            "successful_browsers": successful_browsers,
            "total_browsers": total_browsers,
            "compatibility_rate": (successful_browsers / total_browsers) * 100,
            "details": f"浏览器兼容性: {successful_browsers}/{total_browsers} ({(successful_browsers/total_browsers)*100:.1f}%)"
        }

        self.test_results["tests"]["browser_compatibility"] = result
        print(f"{'✅' if result['success'] else '⚠️ '} 浏览器兼容性测试完成: {result['details']}")
        return result

    def _calculate_performance_grade(self, avg_time):
        """计算性能等级"""
        if avg_time < 0.5:
            return "A"
        elif avg_time < 1.0:
            return "B"
        elif avg_time < 2.0:
            return "C"
        else:
            return "D"

    def run_all_tests(self):
        """运行所有性能和安全测试"""
        print("🚀 开始性能和安全测试...")
        print("=" * 60)

        test_methods = [
            self.test_load_performance,
            self.test_resource_optimization,
            self.test_security_headers,
            self.test_xss_injection,
            self.test_ssl_api_security,
            self.test_browser_compatibility
        ]

        for test_method in test_methods:
            try:
                test_method()
                print()
            except Exception as e:
                print(f"❌ 测试 {test_method.__name__} 出现异常: {str(e)}")
                print()

        # 计算总体结果
        passed_tests = sum(1 for test in self.test_results["tests"].values()
                          if test.get("success", False))
        total_tests = len(self.test_results["tests"])

        self.test_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "overall_status": "PASS" if passed_tests == total_tests else "PARTIAL" if passed_tests > 0 else "FAIL"
        }

        print("=" * 60)
        print(f"🎯 性能和安全测试完成! 总体结果: {self.test_results['summary']['overall_status']}")
        print(f"📊 通过率: {self.test_results['summary']['success_rate']:.1f}% ({passed_tests}/{total_tests})")

        return self.test_results

    def save_results(self, filename="performance_security_test_results.json"):
        """保存测试结果"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        print(f"📁 性能和安全测试结果已保存到: {filename}")

if __name__ == "__main__":
    tester = PerformanceSecurityTester()
    results = tester.run_all_tests()
    tester.save_results()