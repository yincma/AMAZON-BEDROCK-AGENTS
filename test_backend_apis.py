#!/usr/bin/env python3
"""
后端API功能测试脚本
测试所有API端点的功能性和响应状态
"""

import json
import requests
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# API配置
API_BASE_URL = "https://2xbqtuq2t4.execute-api.us-east-1.amazonaws.com/legacy"
API_KEY = "287KGlpdeG5vUdxWxJxAq4pv9Y5iQmbZ1IVNrsV5"

# 测试结果追踪
test_results = {
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "errors": [],
    "test_details": []
}


def make_api_request(method: str, endpoint: str, data: Optional[Dict] = None, 
                     headers: Optional[Dict] = None) -> tuple:
    """
    发送API请求的通用函数
    """
    url = f"{API_BASE_URL}{endpoint}"
    
    # 默认headers
    default_headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=default_headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=default_headers, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=default_headers, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=default_headers, timeout=30)
        else:
            return False, f"Unsupported method: {method}"
        
        return response.status_code, response.text
    except requests.exceptions.Timeout:
        return False, "Request timeout"
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def test_endpoint(test_name: str, method: str, endpoint: str, 
                  data: Optional[Dict] = None, expected_status: int = 200) -> bool:
    """
    测试单个API端点
    """
    global test_results
    test_results["total_tests"] += 1
    
    print(f"\n{'='*60}")
    print(f"测试: {test_name}")
    print(f"方法: {method} {endpoint}")
    if data:
        print(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    status, response = make_api_request(method, endpoint, data)
    
    # 记录详细信息
    test_detail = {
        "test_name": test_name,
        "endpoint": endpoint,
        "method": method,
        "timestamp": datetime.now().isoformat()
    }
    
    if status is False:
        print(f"❌ 失败: {response}")
        test_results["failed"] += 1
        test_results["errors"].append({
            "test": test_name,
            "error": response
        })
        test_detail["status"] = "FAILED"
        test_detail["error"] = response
        test_results["test_details"].append(test_detail)
        return False
    
    print(f"响应状态码: {status}")
    
    # 尝试解析JSON响应
    try:
        response_json = json.loads(response) if response else {}
        print(f"响应内容: {json.dumps(response_json, ensure_ascii=False, indent=2)}")
        test_detail["response"] = response_json
    except:
        print(f"响应内容 (非JSON): {response[:500]}")
        test_detail["response"] = response[:500]
    
    test_detail["status_code"] = status
    
    # 验证状态码
    if status == expected_status or (expected_status == 200 and 200 <= status < 300):
        print(f"✅ 通过")
        test_results["passed"] += 1
        test_detail["status"] = "PASSED"
        test_results["test_details"].append(test_detail)
        return True
    else:
        print(f"❌ 失败: 期望状态码 {expected_status}, 实际 {status}")
        test_results["failed"] += 1
        test_results["errors"].append({
            "test": test_name,
            "error": f"Expected status {expected_status}, got {status}"
        })
        test_detail["status"] = "FAILED"
        test_detail["error"] = f"Expected status {expected_status}"
        test_results["test_details"].append(test_detail)
        return False


def run_all_tests():
    """
    执行所有API测试
    """
    print("\n" + "="*60)
    print("开始执行后端API功能测试")
    print(f"API基础URL: {API_BASE_URL}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 存储测试中生成的数据
    test_data = {}
    
    # 1. 测试健康检查端点
    test_endpoint("健康检查", "GET", "/health")
    
    # 2. 测试列出演示文稿
    test_endpoint("列出演示文稿", "GET", "/presentations")
    
    # 3. 测试创建演示文稿
    presentation_data = {
        "topic": "人工智能在医疗领域的应用",
        "pages": 5,
        "style": "professional",
        "language": "zh-CN",
        "audience": "医疗专业人士"
    }
    
    if test_endpoint("创建演示文稿", "POST", "/presentations", presentation_data):
        # 获取任务ID用于后续测试
        status, response = make_api_request("POST", "/presentations", presentation_data)
        try:
            response_json = json.loads(response)
            if "taskId" in response_json:
                test_data["task_id"] = response_json["taskId"]
                print(f"\n📝 获取到任务ID: {test_data['task_id']}")
            elif "task_id" in response_json:
                test_data["task_id"] = response_json["task_id"]
                print(f"\n📝 获取到任务ID: {test_data['task_id']}")
        except:
            print("\n⚠️ 无法从响应中提取任务ID")
    
    # 4. 测试获取任务状态
    if test_data.get("task_id"):
        test_endpoint(
            "获取任务状态", 
            "GET", 
            f"/tasks/{test_data['task_id']}"
        )
        
        # 等待一下让任务有时间处理
        print("\n⏳ 等待3秒让任务处理...")
        time.sleep(3)
        
        # 再次检查状态
        test_endpoint(
            "再次获取任务状态", 
            "GET", 
            f"/tasks/{test_data['task_id']}"
        )
    
    # 5. 测试获取演示文稿状态
    if test_data.get("task_id"):
        test_endpoint(
            "获取演示文稿状态",
            "GET",
            f"/presentations/{test_data['task_id']}/status"
        )
    
    # 6. 测试修改幻灯片
    if test_data.get("task_id"):
        modify_data = {
            "slideNumber": 2,
            "content": "更新后的内容：AI在诊断中的应用",
            "notes": "演讲者备注：强调准确性的提升"
        }
        test_endpoint(
            "修改幻灯片",
            "PUT",
            f"/presentations/{test_data['task_id']}/slides/2",
            modify_data
        )
    
    # 7. 测试创建大纲
    outline_data = {
        "topic": "区块链技术入门",
        "pages": 8,
        "audience": "初学者",
        "style": "educational"
    }
    test_endpoint("创建大纲", "POST", "/outline", outline_data)
    
    # 8. 测试生成内容
    content_data = {
        "outline": {
            "title": "云计算基础",
            "slides": [
                {"title": "什么是云计算", "points": ["定义", "特点", "优势"]},
                {"title": "云服务模型", "points": ["IaaS", "PaaS", "SaaS"]}
            ]
        },
        "style": "technical"
    }
    test_endpoint("生成内容", "POST", "/content", content_data)
    
    # 9. 测试图片搜索
    image_search_data = {
        "query": "artificial intelligence",
        "count": 5
    }
    test_endpoint("搜索图片", "POST", "/images/search", image_search_data)
    
    # 10. 测试生成图片
    image_generate_data = {
        "prompt": "futuristic AI robot helping doctor",
        "style": "photorealistic",
        "size": "1024x1024"
    }
    test_endpoint("生成图片", "POST", "/images/generate", image_generate_data)
    
    # 11. 测试下载演示文稿
    if test_data.get("task_id"):
        test_endpoint(
            "下载演示文稿",
            "GET",
            f"/presentations/{test_data['task_id']}/download"
        )
    
    # 12. 测试错误处理 - 无效的任务ID
    test_endpoint(
        "错误处理 - 无效任务ID",
        "GET",
        "/tasks/invalid-task-id-12345",
        expected_status=404
    )
    
    # 13. 测试错误处理 - 缺少必要参数
    test_endpoint(
        "错误处理 - 缺少参数",
        "POST",
        "/presentations",
        {},
        expected_status=400
    )
    
    # 14. 测试OPTIONS请求 (CORS)
    test_endpoint(
        "CORS预检请求",
        "OPTIONS",
        "/presentations",
        expected_status=200
    )
    
    return test_data


def print_summary():
    """
    打印测试摘要
    """
    print("\n" + "="*60)
    print("测试摘要")
    print("="*60)
    print(f"总测试数: {test_results['total_tests']}")
    print(f"✅ 通过: {test_results['passed']}")
    print(f"❌ 失败: {test_results['failed']}")
    print(f"成功率: {(test_results['passed']/test_results['total_tests']*100):.1f}%")
    
    if test_results["errors"]:
        print("\n错误详情:")
        for error in test_results["errors"]:
            print(f"  - {error['test']}: {error['error']}")
    
    # 保存详细报告
    report_file = f"api_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    print(f"\n📄 详细报告已保存到: {report_file}")
    
    return test_results["failed"] == 0


if __name__ == "__main__":
    try:
        # 运行所有测试
        test_data = run_all_tests()
        
        # 打印摘要
        success = print_summary()
        
        # 退出码
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        print_summary()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {str(e)}")
        print_summary()
        sys.exit(1)