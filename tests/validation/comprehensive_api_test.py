#!/usr/bin/env python3
"""
AI PPT Assistant - 综合API测试脚本
验证所有修复后的API端点功能
"""

import requests
import json
import time
import sys
from datetime import datetime

# 配置
API_BASE_URL = "https://1gq0gwsq3d.execute-api.us-east-1.amazonaws.com/legacy"
API_KEY = "DYXsvhgHzI60RWguXUukX4L7eFfA6X5A3jhtAC81"  # 从问题报告获取

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def test_endpoint(method, endpoint, data=None, expected_status=None):
    """测试单个API端点"""
    url = f"{API_BASE_URL}{endpoint}"
    
    print(f"\n🧪 测试 {method} {endpoint}")
    print(f"📡 URL: {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=HEADERS, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=HEADERS, json=data, timeout=30)
        else:
            print(f"❌ 不支持的HTTP方法: {method}")
            return False
            
        print(f"📊 状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 成功响应")
            try:
                response_data = response.json()
                print(f"📋 响应内容: {json.dumps(response_data, indent=2, ensure_ascii=False)[:500]}")
            except:
                print(f"📋 响应内容: {response.text[:500]}")
            return True
        elif response.status_code == 202:
            print("✅ 接受处理 (异步)")
            try:
                response_data = response.json()
                print(f"📋 响应内容: {json.dumps(response_data, indent=2, ensure_ascii=False)[:500]}")
            except:
                print(f"📋 响应内容: {response.text[:500]}")
            return True
        else:
            print(f"⚠️  非预期状态码: {response.status_code}")
            print(f"📋 错误内容: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ 请求超时")
        return False
    except requests.exceptions.ConnectionError:
        print("🔌 连接错误")
        return False
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 AI PPT Assistant - 综合API测试")
    print("=" * 60)
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API基础URL: {API_BASE_URL}")
    print("=" * 60)
    
    test_results = []
    
    # 1. 健康检查端点
    print("\n📋 1. 基础健康检查")
    success = test_endpoint("GET", "/health")
    test_results.append(("健康检查", success))
    
    success = test_endpoint("GET", "/health/ready")
    test_results.append(("就绪检查", success))
    
    # 2. 演示文稿相关API
    print("\n📋 2. 演示文稿相关API")
    
    # 列出演示文稿
    success = test_endpoint("GET", "/presentations")
    test_results.append(("列出演示文稿", success))
    
    # 创建演示文稿
    presentation_data = {
        "title": "测试演示文稿",
        "topic": "AI和机器学习的未来发展趋势",
        "audience": "technical",
        "duration": 15,
        "slide_count": 10,
        "language": "zh",
        "style": "professional"
    }
    
    success = test_endpoint("POST", "/presentations", presentation_data)
    test_results.append(("创建演示文稿", success))
    
    # 3. 会话相关API  
    print("\n📋 3. 会话相关API")
    
    session_data = {
        "user_id": "test_user_001",
        "session_name": "测试会话"
    }
    
    success = test_endpoint("POST", "/sessions", session_data)
    test_results.append(("创建会话", success))
    
    # 4. 代理执行API
    print("\n📋 4. 代理执行API")
    
    agent_data = {
        "input": "请帮我创建一个关于人工智能的演示文稿大纲",
        "enable_trace": False
    }
    
    success = test_endpoint("POST", "/agents/orchestrator/execute", agent_data)
    test_results.append(("代理执行", success))
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, success in test_results if success)
    
    for test_name, success in test_results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print("-" * 40)
    print(f"总测试数量: {total_tests}")
    print(f"通过数量: {passed_tests}")
    print(f"失败数量: {total_tests - passed_tests}")
    print(f"成功率: {(passed_tests/total_tests*100):.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！API部署修复成功！")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} 个测试失败，需要进一步检查")
        return 1

if __name__ == "__main__":
    sys.exit(main())