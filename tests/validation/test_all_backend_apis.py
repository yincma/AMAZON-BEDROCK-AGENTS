#!/usr/bin/env python3
"""
AI PPT Assistant API 综合测试脚本
测试所有后端API端点功能
"""

import json
import time
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# API配置
API_BASE_URL = "https://k4ona7g2x3.execute-api.us-east-1.amazonaws.com/legacy"
API_KEY = "UCNx4NTHHk54TjO6KdfZV176vqJb7cWZ56HdI7tV"

# 请求头
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

class APITester:
    def __init__(self):
        self.results = []
        self.presentation_id = None
        self.test_start_time = datetime.now()
        
    def log_result(self, test_name: str, status: str, message: str, details: Optional[Dict] = None):
        """记录测试结果"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "status": status,
            "message": message,
            "details": details or {}
        }
        self.results.append(result)
        
        # 实时打印结果
        status_emoji = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⚠️"
        print(f"{status_emoji} [{test_name}] {status}: {message}")
        if details and status == "FAILED":
            print(f"   详细信息: {json.dumps(details, ensure_ascii=False, indent=2)}")
    
    def test_create_presentation(self) -> bool:
        """测试创建演示文稿"""
        test_name = "创建演示文稿"
        
        try:
            # 准备测试数据
            payload = {
                "title": "AI技术测试演示",
                "topic": "这是一个用于测试API功能的演示文稿，介绍人工智能的基本概念",
                "audience": "general",
                "duration": 10,
                "slide_count": 5,
                "language": "zh",
                "style": "professional",
                "template": "default",
                "include_speaker_notes": True,
                "include_images": True
            }
            
            # 发送请求
            response = requests.post(
                f"{API_BASE_URL}/presentations",
                headers=HEADERS,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 202:
                response_data = response.json()
                # API返回的是task_id，presentation_id与task_id相同
                if "data" in response_data and "task_id" in response_data["data"]:
                    self.presentation_id = response_data["data"]["task_id"]
                else:
                    self.presentation_id = response_data.get("presentation_id") or response_data.get("task_id")
                
                self.log_result(
                    test_name,
                    "SUCCESS",
                    f"成功创建演示文稿，ID: {self.presentation_id}",
                    response_data
                )
                return True
            else:
                self.log_result(
                    test_name,
                    "FAILED",
                    f"HTTP {response.status_code}",
                    {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                )
                return False
                
        except Exception as e:
            self.log_result(
                test_name,
                "FAILED",
                f"请求异常: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_get_presentation_status(self) -> bool:
        """测试获取演示文稿状态"""
        test_name = "获取演示文稿状态"
        
        if not self.presentation_id:
            self.log_result(test_name, "SKIPPED", "没有可用的演示文稿ID")
            return False
        
        try:
            # 尝试多次获取状态，等待处理完成
            max_attempts = 30
            for attempt in range(max_attempts):
                response = requests.get(
                    f"{API_BASE_URL}/presentations/{self.presentation_id}",
                    headers=HEADERS,
                    timeout=30
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    status = response_data.get("status", "unknown")
                    progress = response_data.get("progress", 0)
                    
                    print(f"   状态检查 {attempt + 1}/{max_attempts}: {status} (进度: {progress * 100:.1f}%)")
                    
                    if status == "completed":
                        self.log_result(
                            test_name,
                            "SUCCESS",
                            f"演示文稿已完成，共 {response_data.get('slide_count', 0)} 页",
                            response_data
                        )
                        return True
                    elif status == "failed":
                        self.log_result(
                            test_name,
                            "FAILED",
                            "演示文稿生成失败",
                            response_data
                        )
                        return False
                    
                    # 等待后继续检查
                    time.sleep(5)
                else:
                    self.log_result(
                        test_name,
                        "FAILED",
                        f"HTTP {response.status_code}",
                        {
                            "status_code": response.status_code,
                            "response": response.text
                        }
                    )
                    return False
            
            # 超时
            self.log_result(
                test_name,
                "WARNING",
                f"演示文稿生成超时（{max_attempts * 5}秒）",
                {"last_status": status, "last_progress": progress}
            )
            return False
            
        except Exception as e:
            self.log_result(
                test_name,
                "FAILED",
                f"请求异常: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_list_presentations(self) -> bool:
        """测试列出演示文稿"""
        test_name = "列出演示文稿"
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/presentations",
                headers=HEADERS,
                params={"limit": 10, "offset": 0},
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                items = response_data.get("items", [])
                total = response_data.get("total", 0)
                
                self.log_result(
                    test_name,
                    "SUCCESS",
                    f"成功获取演示文稿列表，共 {total} 个，当前页 {len(items)} 个",
                    {
                        "total": total,
                        "items_count": len(items),
                        "first_item": items[0] if items else None
                    }
                )
                return True
            else:
                self.log_result(
                    test_name,
                    "FAILED",
                    f"HTTP {response.status_code}",
                    {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                )
                return False
                
        except Exception as e:
            self.log_result(
                test_name,
                "FAILED",
                f"请求异常: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_download_presentation(self) -> bool:
        """测试下载演示文稿"""
        test_name = "下载演示文稿"
        
        if not self.presentation_id:
            self.log_result(test_name, "SKIPPED", "没有可用的演示文稿ID")
            return False
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/presentations/{self.presentation_id}/download",
                headers=HEADERS,
                timeout=60
            )
            
            if response.status_code == 200:
                # 保存文件
                filename = f"test_presentation_{self.presentation_id}.pptx"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                self.log_result(
                    test_name,
                    "SUCCESS",
                    f"成功下载演示文稿，文件大小: {file_size / 1024:.2f} KB",
                    {
                        "filename": filename,
                        "size_bytes": file_size,
                        "content_type": response.headers.get("Content-Type")
                    }
                )
                return True
            elif response.status_code == 409:
                self.log_result(
                    test_name,
                    "WARNING",
                    "演示文稿尚未准备好",
                    {"status_code": response.status_code}
                )
                return False
            else:
                self.log_result(
                    test_name,
                    "FAILED",
                    f"HTTP {response.status_code}",
                    {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                )
                return False
                
        except Exception as e:
            self.log_result(
                test_name,
                "FAILED",
                f"请求异常: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_invalid_api_key(self) -> bool:
        """测试无效API密钥"""
        test_name = "无效API密钥测试"
        
        try:
            invalid_headers = {
                "x-api-key": "invalid_key_123",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{API_BASE_URL}/presentations",
                headers=invalid_headers,
                timeout=30
            )
            
            if response.status_code == 401 or response.status_code == 403:
                self.log_result(
                    test_name,
                    "SUCCESS",
                    f"正确拒绝无效密钥 (HTTP {response.status_code})",
                    {"status_code": response.status_code}
                )
                return True
            else:
                self.log_result(
                    test_name,
                    "FAILED",
                    f"未正确处理无效密钥，返回 HTTP {response.status_code}",
                    {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                )
                return False
                
        except Exception as e:
            self.log_result(
                test_name,
                "FAILED",
                f"请求异常: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def test_invalid_presentation_id(self) -> bool:
        """测试无效的演示文稿ID"""
        test_name = "无效演示文稿ID测试"
        
        try:
            invalid_id = "invalid-id-12345"
            response = requests.get(
                f"{API_BASE_URL}/presentations/{invalid_id}",
                headers=HEADERS,
                timeout=30
            )
            
            if response.status_code == 404 or response.status_code == 400:
                self.log_result(
                    test_name,
                    "SUCCESS",
                    f"正确处理无效ID (HTTP {response.status_code})",
                    {"status_code": response.status_code}
                )
                return True
            else:
                self.log_result(
                    test_name,
                    "FAILED",
                    f"未正确处理无效ID，返回 HTTP {response.status_code}",
                    {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                )
                return False
                
        except Exception as e:
            self.log_result(
                test_name,
                "FAILED",
                f"请求异常: {str(e)}",
                {"error": str(e)}
            )
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("开始 AI PPT Assistant API 测试")
        print("="*60)
        print(f"API URL: {API_BASE_URL}")
        print(f"测试时间: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
        # 执行测试
        tests = [
            self.test_invalid_api_key,  # 先测试认证
            self.test_create_presentation,
            self.test_get_presentation_status,
            self.test_list_presentations,
            self.test_download_presentation,
            self.test_invalid_presentation_id
        ]
        
        success_count = 0
        failed_count = 0
        warning_count = 0
        skipped_count = 0
        
        for test in tests:
            result = test()
            # 统计结果
            last_result = self.results[-1]
            if last_result["status"] == "SUCCESS":
                success_count += 1
            elif last_result["status"] == "FAILED":
                failed_count += 1
            elif last_result["status"] == "WARNING":
                warning_count += 1
            elif last_result["status"] == "SKIPPED":
                skipped_count += 1
        
        # 生成测试报告
        print("\n" + "="*60)
        print("测试结果汇总")
        print("="*60)
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {failed_count}")
        print(f"⚠️  警告: {warning_count}")
        print(f"⏭️  跳过: {skipped_count}")
        print(f"总计: {len(self.results)} 个测试")
        
        # 计算总耗时
        total_time = (datetime.now() - self.test_start_time).total_seconds()
        print(f"\n总耗时: {total_time:.2f} 秒")
        
        # 保存详细报告
        report_filename = f"api_test_report_{self.test_start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total_tests": len(self.results),
                    "success": success_count,
                    "failed": failed_count,
                    "warning": warning_count,
                    "skipped": skipped_count,
                    "duration_seconds": total_time,
                    "api_url": API_BASE_URL,
                    "test_time": self.test_start_time.isoformat()
                },
                "results": self.results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细报告已保存到: {report_filename}")
        
        # 返回是否所有测试都通过
        return failed_count == 0

if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all_tests()
    
    # 退出码
    exit(0 if success else 1)