#!/usr/bin/env python3
"""
API 参数验证测试脚本

这个脚本测试 API Gateway 的请求参数验证功能，确保：
1. 有效请求被正确处理
2. 无效请求返回友好的错误消息
3. 所有验证规则按预期工作

运行前需要设置环境变量：
- API_BASE_URL: API Gateway 的基础URL
- API_KEY: API密钥

使用方法:
    python3 scripts/test_api_validation.py
"""

import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

import requests

# 配置
API_BASE_URL = os.environ.get("API_BASE_URL", "https://your-api-id.execute-api.us-east-1.amazonaws.com/dev")
API_KEY = os.environ.get("API_KEY")

if not API_KEY:
    print("❌ 错误: 请设置 API_KEY 环境变量")
    sys.exit(1)

# 通用headers
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
    "User-Agent": "API-Validation-Test/1.0"
}

class ValidationTestSuite:
    """API参数验证测试套件"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0
        
    def run_test(self, test_name: str, test_func) -> bool:
        """运行单个测试"""
        self.total_tests += 1
        print(f"\n🧪 测试: {test_name}")
        
        try:
            result = test_func()
            if result:
                print(f"✅ 通过: {test_name}")
                self.passed_tests += 1
                return True
            else:
                print(f"❌ 失败: {test_name}")
                self.failed_tests += 1
                return False
        except Exception as e:
            print(f"❌ 异常: {test_name} - {str(e)}")
            self.failed_tests += 1
            return False
    
    def print_summary(self):
        """打印测试结果总结"""
        print(f"\n" + "="*50)
        print(f"📊 测试结果总结")
        print(f"总测试数: {self.total_tests}")
        print(f"通过: {self.passed_tests}")
        print(f"失败: {self.failed_tests}")
        print(f"成功率: {self.passed_tests/self.total_tests*100:.1f}%")
        print(f"="*50)
    
    def test_generate_presentation_valid(self) -> bool:
        """测试有效的生成演示文稿请求"""
        url = f"{API_BASE_URL}/presentations"
        payload = {
            "title": "AI技术在企业中的应用",
            "topic": "探讨人工智能技术如何改变现代企业的运营模式",
            "audience": "executive",
            "duration": 30,
            "slide_count": 20,
            "language": "zh",
            "style": "professional",
            "template": "executive_summary",
            "include_speaker_notes": True,
            "include_images": True,
            "session_id": str(uuid.uuid4()),
            "metadata": {
                "presenter": "张三",
                "department": "技术部"
            }
        }
        
        response = requests.post(url, json=payload, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code in [202, 200]:
            print("   ✓ 有效请求被正确接受")
            return True
        else:
            print(f"   ✗ 期望状态码202，实际: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
    
    def test_generate_presentation_missing_required(self) -> bool:
        """测试缺少必需字段的请求"""
        url = f"{API_BASE_URL}/presentations"
        payload = {
            "topic": "缺少标题的请求"
            # 缺少必需的 "title" 字段
        }
        
        response = requests.post(url, json=payload, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 400:
            try:
                error_data = response.json()
                if "VALIDATION_ERROR" in error_data.get("error", ""):
                    print("   ✓ 正确返回验证错误")
                    return True
                else:
                    print(f"   ✗ 错误类型不正确: {error_data.get('error')}")
                    return False
            except:
                print("   ✗ 响应不是有效的JSON")
                return False
        else:
            print(f"   ✗ 期望状态码400，实际: {response.status_code}")
            return False
    
    def test_generate_presentation_invalid_enum(self) -> bool:
        """测试无效枚举值的请求"""
        url = f"{API_BASE_URL}/presentations"
        payload = {
            "title": "测试标题",
            "topic": "测试主题",
            "language": "invalid_language",  # 无效的语言代码
            "style": "invalid_style"  # 无效的风格
        }
        
        response = requests.post(url, json=payload, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 400:
            print("   ✓ 正确拒绝无效枚举值")
            return True
        else:
            print(f"   ✗ 期望状态码400，实际: {response.status_code}")
            return False
    
    def test_generate_presentation_invalid_range(self) -> bool:
        """测试超出范围的数值"""
        url = f"{API_BASE_URL}/presentations"
        payload = {
            "title": "测试标题",
            "topic": "测试主题",
            "duration": 200,  # 超过最大值120
            "slide_count": 150  # 超过最大值100
        }
        
        response = requests.post(url, json=payload, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 400:
            print("   ✓ 正确拒绝超范围数值")
            return True
        else:
            print(f"   ✗ 期望状态码400，实际: {response.status_code}")
            return False
    
    def test_generate_presentation_invalid_string_length(self) -> bool:
        """测试字符串长度验证"""
        url = f"{API_BASE_URL}/presentations"
        payload = {
            "title": "x" * 300,  # 超过最大长度200
            "topic": "测试主题"
        }
        
        response = requests.post(url, json=payload, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 400:
            print("   ✓ 正确拒绝过长字符串")
            return True
        else:
            print(f"   ✗ 期望状态码400，实际: {response.status_code}")
            return False
    
    def test_get_task_valid_uuid(self) -> bool:
        """测试有效UUID格式的任务查询"""
        task_id = str(uuid.uuid4())
        url = f"{API_BASE_URL}/tasks/{task_id}"
        
        response = requests.get(url, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        # 即使任务不存在，UUID格式有效应该通过验证
        if response.status_code in [200, 404]:
            print("   ✓ 有效UUID通过验证")
            return True
        else:
            print(f"   ✗ 期望状态码200或404，实际: {response.status_code}")
            return False
    
    def test_get_task_invalid_uuid(self) -> bool:
        """测试无效UUID格式的任务查询"""
        invalid_task_id = "invalid-uuid-format"
        url = f"{API_BASE_URL}/tasks/{invalid_task_id}"
        
        response = requests.get(url, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 400:
            print("   ✓ 正确拒绝无效UUID")
            return True
        else:
            print(f"   ✗ 期望状态码400，实际: {response.status_code}")
            return False
    
    def test_get_templates_with_valid_params(self) -> bool:
        """测试有效查询参数的模板查询"""
        url = f"{API_BASE_URL}/templates"
        params = {
            "category": "business",
            "limit": 20,
            "offset": 0
        }
        
        response = requests.get(url, params=params, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✓ 有效查询参数通过验证")
            return True
        else:
            print(f"   ✗ 期望状态码200，实际: {response.status_code}")
            return False
    
    def test_get_templates_with_invalid_params(self) -> bool:
        """测试无效查询参数的模板查询"""
        url = f"{API_BASE_URL}/templates"
        params = {
            "limit": 200,  # 超过最大值100
            "offset": -1   # 小于最小值0
        }
        
        response = requests.get(url, params=params, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 400:
            print("   ✓ 正确拒绝无效查询参数")
            return True
        else:
            print(f"   ✗ 期望状态码400，实际: {response.status_code}")
            return False
    
    def test_api_key_missing(self) -> bool:
        """测试缺少API密钥的请求"""
        url = f"{API_BASE_URL}/presentations"
        payload = {
            "title": "测试标题",
            "topic": "测试主题"
        }
        
        headers_without_key = {
            "Content-Type": "application/json",
            "User-Agent": "API-Validation-Test/1.0"
        }
        
        response = requests.post(url, json=payload, headers=headers_without_key)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 403:
            try:
                error_data = response.json()
                if "MISSING_API_KEY" in error_data.get("error", ""):
                    print("   ✓ 正确返回API密钥错误")
                    return True
                else:
                    print(f"   ✗ 错误类型不正确: {error_data.get('error')}")
                    return False
            except:
                print("   ✗ 响应不是有效的JSON")
                return False
        else:
            print(f"   ✗ 期望状态码403，实际: {response.status_code}")
            return False
    
    def test_create_session_valid(self) -> bool:
        """测试有效的创建会话请求"""
        url = f"{API_BASE_URL}/sessions"
        payload = {
            "user_id": "user_12345",
            "session_name": "我的AI演示会话",
            "metadata": {
                "client_version": "1.0.0",
                "platform": "web"
            }
        }
        
        response = requests.post(url, json=payload, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code in [200, 201, 202]:
            print("   ✓ 有效会话创建请求被接受")
            return True
        else:
            print(f"   ✗ 期望状态码200/201/202，实际: {response.status_code}")
            return False
    
    def test_create_session_invalid_user_id(self) -> bool:
        """测试无效用户ID的会话创建"""
        url = f"{API_BASE_URL}/sessions"
        payload = {
            "user_id": "invalid user id with spaces!",  # 包含非法字符
            "session_name": "测试会话"
        }
        
        response = requests.post(url, json=payload, headers=HEADERS)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 400:
            print("   ✓ 正确拒绝无效用户ID")
            return True
        else:
            print(f"   ✗ 期望状态码400，实际: {response.status_code}")
            return False

def main():
    """主测试函数"""
    print("🚀 开始API参数验证测试")
    print(f"📍 API基础URL: {API_BASE_URL}")
    print(f"🔑 使用API密钥: {'是' if API_KEY else '否'}")
    
    suite = ValidationTestSuite()
    
    # 运行所有测试
    suite.run_test("生成演示文稿 - 有效请求", suite.test_generate_presentation_valid)
    suite.run_test("生成演示文稿 - 缺少必需字段", suite.test_generate_presentation_missing_required)
    suite.run_test("生成演示文稿 - 无效枚举值", suite.test_generate_presentation_invalid_enum)
    suite.run_test("生成演示文稿 - 数值超出范围", suite.test_generate_presentation_invalid_range)
    suite.run_test("生成演示文稿 - 字符串过长", suite.test_generate_presentation_invalid_string_length)
    
    suite.run_test("获取任务 - 有效UUID", suite.test_get_task_valid_uuid)
    suite.run_test("获取任务 - 无效UUID", suite.test_get_task_invalid_uuid)
    
    suite.run_test("获取模板 - 有效查询参数", suite.test_get_templates_with_valid_params)
    suite.run_test("获取模板 - 无效查询参数", suite.test_get_templates_with_invalid_params)
    
    suite.run_test("API密钥验证 - 缺少密钥", suite.test_api_key_missing)
    
    suite.run_test("创建会话 - 有效请求", suite.test_create_session_valid)
    suite.run_test("创建会话 - 无效用户ID", suite.test_create_session_invalid_user_id)
    
    # 打印测试总结
    suite.print_summary()
    
    # 如果有测试失败，返回非零退出码
    if suite.failed_tests > 0:
        sys.exit(1)
    else:
        print("🎉 所有测试通过！")
        sys.exit(0)

if __name__ == "__main__":
    main()