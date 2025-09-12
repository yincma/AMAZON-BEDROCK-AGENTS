#!/usr/bin/env python3
"""
全面测试所有后端API功能
生成详细的测试报告
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# API配置
API_BASE_URL = "https://t8jhz8li6e.execute-api.us-east-1.amazonaws.com/legacy"
API_KEY = "xRWDKPOB2j58CPOOyteeO3TVJef8tPdd9CC0GMEb"  # 实际的API Key

# 测试结果存储
test_results = {
    "timestamp": datetime.now().isoformat(),
    "api_base_url": API_BASE_URL,
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "errors": [],
    "test_details": []
}

def test_api_endpoint(method: str, endpoint: str, data: dict = None, expected_status: List[int] = [200]) -> Tuple[bool, dict]:
    """测试单个API端点"""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    
    test_info = {
        "endpoint": endpoint,
        "method": method,
        "url": url,
        "request_data": data,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        print(f"\n测试 {method} {endpoint}...")
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"不支持的HTTP方法: {method}")
        
        test_info["status_code"] = response.status_code
        test_info["response_time_ms"] = response.elapsed.total_seconds() * 1000
        
        # 尝试解析JSON响应
        try:
            test_info["response_body"] = response.json()
        except:
            test_info["response_body"] = response.text
        
        # 检查状态码
        if response.status_code in expected_status:
            test_info["result"] = "PASSED"
            print(f"  ✅ 通过 - 状态码: {response.status_code}, 响应时间: {test_info['response_time_ms']:.2f}ms")
            return True, test_info
        else:
            test_info["result"] = "FAILED"
            test_info["error"] = f"期望状态码 {expected_status}, 实际 {response.status_code}"
            print(f"  ❌ 失败 - {test_info['error']}")
            return False, test_info
            
    except requests.exceptions.Timeout:
        test_info["result"] = "ERROR"
        test_info["error"] = "请求超时（30秒）"
        print(f"  ⚠️ 错误 - 请求超时")
        return False, test_info
        
    except Exception as e:
        test_info["result"] = "ERROR"
        test_info["error"] = str(e)
        print(f"  ⚠️ 错误 - {str(e)}")
        return False, test_info

def run_all_tests():
    """运行所有API测试"""
    print("=" * 80)
    print("开始全面API功能测试")
    print(f"API基础URL: {API_BASE_URL}")
    print("=" * 80)
    
    # 定义所有测试用例
    test_cases = [
        # 1. 健康检查
        ("GET", "/health", None, [200, 404]),
        
        # 2. 列出演示文稿
        ("GET", "/presentations", None, [200]),
        
        # 3. 创建新的演示文稿（异步）
        ("POST", "/presentations", {
            "topic": "AI和机器学习的未来",
            "num_slides": 5,
            "style": "professional",
            "language": "zh-CN"
        }, [200, 201, 202]),
        
        # 4. 获取演示文稿状态
        ("GET", "/presentations/test-id-123/status", None, [200, 404]),
        
        # 5. 获取任务状态
        ("GET", "/tasks/test-task-123", None, [200, 404]),
        
        # 6. 修改幻灯片
        ("PUT", "/presentations/test-id-123/slides/1", {
            "title": "更新的标题",
            "content": "更新的内容"
        }, [200, 404]),
        
        # 7. 下载演示文稿
        ("GET", "/presentations/test-id-123/download", None, [200, 404]),
        
        # 8. 创建大纲（直接测试Lambda函数）
        ("POST", "/outline", {
            "topic": "云计算基础",
            "num_slides": 3
        }, [200, 201]),
        
        # 9. 生成内容
        ("POST", "/content", {
            "outline": {
                "slides": [
                    {"title": "介绍", "key_points": ["什么是云计算", "为什么重要"]},
                    {"title": "主要服务", "key_points": ["IaaS", "PaaS", "SaaS"]}
                ]
            }
        }, [200, 201]),
        
        # 10. 生成图片
        ("POST", "/images/generate", {
            "prompt": "未来科技城市",
            "style": "realistic"
        }, [200, 201]),
    ]
    
    # 运行所有测试
    for method, endpoint, data, expected_status in test_cases:
        test_results["total_tests"] += 1
        success, test_info = test_api_endpoint(method, endpoint, data, expected_status)
        
        if success:
            test_results["passed"] += 1
        else:
            test_results["failed"] += 1
            if test_info.get("error"):
                test_results["errors"].append({
                    "endpoint": endpoint,
                    "error": test_info["error"]
                })
        
        test_results["test_details"].append(test_info)
        
        # 避免过快请求
        time.sleep(1)
    
    # 打印测试摘要
    print("\n" + "=" * 80)
    print("测试摘要")
    print("=" * 80)
    print(f"总测试数: {test_results['total_tests']}")
    print(f"通过: {test_results['passed']} ({test_results['passed']/test_results['total_tests']*100:.1f}%)")
    print(f"失败: {test_results['failed']} ({test_results['failed']/test_results['total_tests']*100:.1f}%)")
    
    if test_results["errors"]:
        print("\n错误详情:")
        for error in test_results["errors"]:
            print(f"  - {error['endpoint']}: {error['error']}")
    
    # 性能统计
    response_times = [t["response_time_ms"] for t in test_results["test_details"] if "response_time_ms" in t]
    if response_times:
        print(f"\n性能统计:")
        print(f"  平均响应时间: {sum(response_times)/len(response_times):.2f}ms")
        print(f"  最快响应: {min(response_times):.2f}ms")
        print(f"  最慢响应: {max(response_times):.2f}ms")
    
    return test_results

def save_test_report(results: dict):
    """保存测试报告"""
    # 保存JSON格式报告
    json_file = "/Users/umatoratatsu/Documents/AWS/AWS-Handson/Amazon-Bedrock-Agents/test_results_api.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 测试报告已保存到: {json_file}")
    
    # 生成Markdown报告
    md_file = "/Users/umatoratatsu/Documents/AWS/AWS-Handson/Amazon-Bedrock-Agents/docs/reports/API测试报告.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# API功能测试报告\n\n")
        f.write(f"**测试时间**: {results['timestamp']}\n\n")
        f.write(f"**API基础URL**: {results['api_base_url']}\n\n")
        f.write("## 测试摘要\n\n")
        f.write(f"- **总测试数**: {results['total_tests']}\n")
        f.write(f"- **通过**: {results['passed']} ({results['passed']/results['total_tests']*100:.1f}%)\n")
        f.write(f"- **失败**: {results['failed']} ({results['failed']/results['total_tests']*100:.1f}%)\n\n")
        
        f.write("## 测试详情\n\n")
        f.write("| 端点 | 方法 | 状态码 | 响应时间 | 结果 |\n")
        f.write("|------|------|--------|----------|------|\n")
        
        for test in results["test_details"]:
            status_code = test.get("status_code", "N/A")
            response_time = f"{test.get('response_time_ms', 0):.2f}ms" if "response_time_ms" in test else "N/A"
            result = test.get("result", "UNKNOWN")
            result_icon = "✅" if result == "PASSED" else "❌" if result == "FAILED" else "⚠️"
            
            f.write(f"| {test['endpoint']} | {test['method']} | {status_code} | {response_time} | {result_icon} {result} |\n")
        
        if results["errors"]:
            f.write("\n## 错误详情\n\n")
            for error in results["errors"]:
                f.write(f"- **{error['endpoint']}**: {error['error']}\n")
        
        # 添加性能统计
        response_times = [t["response_time_ms"] for t in results["test_details"] if "response_time_ms" in t]
        if response_times:
            f.write("\n## 性能统计\n\n")
            f.write(f"- **平均响应时间**: {sum(response_times)/len(response_times):.2f}ms\n")
            f.write(f"- **最快响应**: {min(response_times):.2f}ms\n")
            f.write(f"- **最慢响应**: {max(response_times):.2f}ms\n")
    
    print(f"✅ Markdown报告已保存到: {md_file}")

def main():
    """主函数"""
    try:
        results = run_all_tests()
        save_test_report(results)
        
        # 返回状态码
        if results["failed"] == 0:
            print("\n🎉 所有测试通过！")
            return 0
        else:
            print(f"\n⚠️ {results['failed']} 个测试失败")
            return 1
            
    except Exception as e:
        print(f"\n❌ 测试过程出错: {str(e)}")
        return 2

if __name__ == "__main__":
    sys.exit(main())