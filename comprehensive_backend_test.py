#!/usr/bin/env python3
"""
AI PPT Assistant 综合后台功能测试
深入测试业务逻辑和数据处理流程
"""

import requests
import json
import time
import uuid
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import threading
import concurrent.futures

# 配置信息
API_BASE_URL = "https://5vkle9t89e.execute-api.us-east-1.amazonaws.com/legacy"
API_KEY = "JVuEiLVBtlaXN8ctsNIJIaPi3eROzEgc6Y3lb4gM"
REGION = "us-east-1"

# API请求头
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# AWS客户端
try:
    dynamodb = boto3.client('dynamodb', region_name=REGION)
    s3 = boto3.client('s3', region_name=REGION) 
    sqs = boto3.client('sqs', region_name=REGION)
    lambda_client = boto3.client('lambda', region_name=REGION)
    cloudwatch = boto3.client('cloudwatch', region_name=REGION)
except Exception as e:
    print(f"⚠️ AWS客户端初始化警告: {e}")
    dynamodb = s3 = sqs = lambda_client = cloudwatch = None

class BackendTester:
    def __init__(self):
        self.test_results = []
        self.test_session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        self.test_presentation_ids = []
        self.test_task_ids = []
        self.created_resources = []
        
    def log_test(self, test_name: str, status: str, details: str = "", data: Any = None):
        """记录测试结果"""
        timestamp = datetime.now().isoformat()
        result = {
            "timestamp": timestamp,
            "test_name": test_name,
            "status": status,
            "details": details,
            "data": data
        }
        self.test_results.append(result)
        
        status_icon = {
            "PASS": "✅",
            "FAIL": "❌", 
            "WARNING": "⚠️",
            "INFO": "ℹ️"
        }.get(status, "❓")
        
        print(f"{status_icon} {test_name}: {details}")
        
    def cleanup_test_resources(self):
        """清理测试创建的资源"""
        print("\n🧹 开始清理测试资源...")
        
        if dynamodb:
            try:
                # 清理测试会话
                dynamodb.delete_item(
                    TableName="ai-ppt-assistant-dev-sessions",
                    Key={"session_id": {"S": self.test_session_id}}
                )
                self.log_test("清理会话", "INFO", f"已删除会话: {self.test_session_id}")
            except Exception as e:
                self.log_test("清理会话", "WARNING", f"清理会话失败: {str(e)}")
                
            # 清理测试任务
            for task_id in self.test_task_ids:
                try:
                    dynamodb.delete_item(
                        TableName="ai-ppt-assistant-dev-tasks",
                        Key={"task_id": {"S": task_id}}
                    )
                except Exception:
                    pass
                    
        print("✅ 测试资源清理完成")
        
    def test_presentation_workflow(self) -> Dict[str, Any]:
        """测试完整的演示文稿生成工作流程"""
        print("\n" + "="*60)
        print("🎯 测试演示文稿生成完整工作流程")
        print("="*60)
        
        workflow_results = {}
        
        # 第1步：创建演示文稿请求
        print("\n📝 步骤1: 创建演示文稿请求")
        presentation_payload = {
            "title": f"后台测试演示文稿 - {datetime.now().strftime('%H:%M:%S')}",
            "topic": "深度学习在计算机视觉中的应用，包括CNN、YOLO、Transformer架构的比较分析",
            "audience": "technical",
            "duration": 15,
            "slide_count": 8,
            "language": "zh",
            "style": "professional"
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/presentations",
                headers=HEADERS,
                json=presentation_payload,
                timeout=30
            )
            
            if response.status_code == 202:
                response_data = response.json()
                
                # 解析直接的API响应格式（OpenAPI标准）
                presentation_id = response_data.get("presentation_id")
                
                if presentation_id:
                    # API返回presentation_id，将其用作task_id追踪
                    task_id = presentation_id
                    self.test_presentation_ids.append(presentation_id)
                    self.test_task_ids.append(task_id)
                    workflow_results["presentation_created"] = True
                    workflow_results["presentation_id"] = presentation_id
                    workflow_results["task_id"] = task_id
                    
                    status = response_data.get('status', 'unknown')
                    progress = response_data.get('progress', 0)
                    title = response_data.get('title', 'unknown')
                    
                    self.log_test("创建演示文稿", "PASS", 
                                f"演示文稿ID: {presentation_id}, 状态: {status}, 进度: {progress}%, 标题: {title}")
                else:
                    self.log_test("创建演示文稿", "FAIL", f"响应数据中缺少presentation_id: {response_data}")
                    return workflow_results
            else:
                self.log_test("创建演示文稿", "FAIL", 
                            f"HTTP {response.status_code}: {response.text}")
                return workflow_results
                
        except Exception as e:
            self.log_test("创建演示文稿", "FAIL", f"请求异常: {str(e)}")
            return workflow_results
        
        # 第2步：监控任务进度
        print("\n⏳ 步骤2: 监控任务处理进度")
        task_status = self._monitor_task_progress(task_id, max_wait_time=300)
        workflow_results["task_monitoring"] = task_status
        
        # 第3步：验证数据库状态
        print("\n🗄️ 步骤3: 验证数据库状态")
        db_status = self._verify_database_state(presentation_id, task_id)
        workflow_results["database_verification"] = db_status
        
        # 第4步：测试文件生成
        print("\n📄 步骤4: 测试文件生成")
        file_status = self._test_file_generation(presentation_id)
        workflow_results["file_generation"] = file_status
        
        return workflow_results
    
    def _monitor_task_progress(self, task_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """监控任务处理进度"""
        start_time = time.time()
        status_changes = []
        
        while time.time() - start_time < max_wait_time:
            try:
                # 通过API检查任务状态
                response = requests.get(
                    f"{API_BASE_URL}/tasks/{task_id}",
                    headers=HEADERS,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # 直接从API响应获取任务状态信息（OpenAPI标准格式）
                    current_status = data.get("status", "unknown")
                    current_step = data.get("current_step", "unknown") 
                    progress = data.get("progress", 0)
                    
                    status_info = {
                        "timestamp": datetime.now().isoformat(),
                        "status": current_status,
                        "step": current_step, 
                        "progress": progress
                    }
                    
                    if not status_changes or status_changes[-1]["status"] != current_status:
                        status_changes.append(status_info)
                        self.log_test("任务状态变化", "INFO", 
                                    f"状态: {current_status}, 步骤: {current_step}, 进度: {progress}%")
                    
                    # 检查是否完成或失败
                    if current_status in ["completed", "failed", "error"]:
                        result = {
                            "final_status": current_status,
                            "processing_time": time.time() - start_time,
                            "status_changes": status_changes,
                            "success": current_status == "completed"
                        }
                        
                        if current_status == "completed":
                            self.log_test("任务监控", "PASS", 
                                        f"任务完成，用时: {result['processing_time']:.1f}秒")
                        else:
                            self.log_test("任务监控", "FAIL", 
                                        f"任务失败，状态: {current_status}")
                        
                        return result
                
                # 等待5秒再次检查
                time.sleep(5)
                
            except Exception as e:
                self.log_test("任务监控", "WARNING", f"监控异常: {str(e)}")
                time.sleep(5)
        
        # 超时
        self.log_test("任务监控", "FAIL", f"任务监控超时 ({max_wait_time}秒)")
        return {
            "final_status": "timeout",
            "processing_time": max_wait_time,
            "status_changes": status_changes,
            "success": False
        }
    
    def _verify_database_state(self, presentation_id: str, task_id: str) -> Dict[str, Any]:
        """验证数据库中的数据状态"""
        verification_results = {}
        
        if not dynamodb:
            self.log_test("数据库验证", "WARNING", "DynamoDB客户端不可用")
            return {"error": "DynamoDB客户端不可用"}
        
        try:
            # 检查任务表
            task_response = dynamodb.get_item(
                TableName="ai-ppt-assistant-dev-tasks",
                Key={"task_id": {"S": task_id}}
            )
            
            if "Item" in task_response:
                task_item = task_response["Item"]
                verification_results["task_exists"] = True
                verification_results["task_status"] = task_item.get("status", {}).get("S", "unknown")
                verification_results["task_data"] = self._format_dynamodb_item(task_item)
                
                self.log_test("任务数据验证", "PASS", 
                            f"任务存在，状态: {verification_results['task_status']}")
            else:
                verification_results["task_exists"] = False
                self.log_test("任务数据验证", "FAIL", "任务在数据库中不存在")
        
        except Exception as e:
            self.log_test("任务数据验证", "FAIL", f"查询任务失败: {str(e)}")
            verification_results["task_error"] = str(e)
        
        try:
            # 检查会话表
            session_response = dynamodb.get_item(
                TableName="ai-ppt-assistant-dev-sessions",
                Key={"session_id": {"S": self.test_session_id}}
            )
            
            if "Item" in session_response:
                verification_results["session_exists"] = True
                session_item = session_response["Item"]
                verification_results["session_data"] = self._format_dynamodb_item(session_item)
                
                self.log_test("会话数据验证", "PASS", "会话数据存在")
            else:
                verification_results["session_exists"] = False
                self.log_test("会话数据验证", "INFO", "会话数据不存在（可能正常）")
        
        except Exception as e:
            self.log_test("会话数据验证", "FAIL", f"查询会话失败: {str(e)}")
            verification_results["session_error"] = str(e)
        
        return verification_results
    
    def _format_dynamodb_item(self, item: Dict) -> Dict:
        """格式化DynamoDB项目数据"""
        formatted = {}
        for key, value in item.items():
            if "S" in value:
                formatted[key] = value["S"]
            elif "N" in value:
                formatted[key] = float(value["N"])
            elif "BOOL" in value:
                formatted[key] = value["BOOL"]
            elif "L" in value:
                formatted[key] = [self._format_dynamodb_item({"item": v})["item"] for v in value["L"]]
            elif "M" in value:
                formatted[key] = self._format_dynamodb_item(value["M"])
            else:
                formatted[key] = value
        return formatted
    
    def _test_file_generation(self, presentation_id: str) -> Dict[str, Any]:
        """测试文件生成功能"""
        file_results = {}
        
        try:
            # 尝试下载演示文稿
            response = requests.get(
                f"{API_BASE_URL}/presentations/{presentation_id}/download",
                headers=HEADERS,
                timeout=30
            )
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                content_length = len(response.content)
                
                file_results["download_success"] = True
                file_results["content_type"] = content_type
                file_results["file_size"] = content_length
                
                if "application/json" in content_type:
                    # 返回下载URL
                    data = response.json()
                    download_url = data.get("download_url")
                    file_results["download_url"] = download_url
                    
                    self.log_test("文件下载", "PASS", 
                                f"获得下载URL: {download_url[:50]}...")
                else:
                    # 直接返回文件内容
                    file_results["direct_content"] = True
                    
                    self.log_test("文件下载", "PASS", 
                                f"直接下载文件，大小: {content_length} bytes")
            else:
                file_results["download_success"] = False
                file_results["error_code"] = response.status_code
                file_results["error_message"] = response.text
                
                self.log_test("文件下载", "FAIL", 
                            f"下载失败: HTTP {response.status_code}")
                
        except Exception as e:
            file_results["download_success"] = False
            file_results["exception"] = str(e)
            
            self.log_test("文件下载", "FAIL", f"下载异常: {str(e)}")
        
        return file_results
    
    def test_lambda_functions(self) -> Dict[str, Any]:
        """测试Lambda函数调用"""
        print("\n" + "="*60)
        print("⚡ 测试Lambda函数直接调用")
        print("="*60)
        
        lambda_results = {}
        
        if not lambda_client:
            self.log_test("Lambda测试", "WARNING", "Lambda客户端不可用")
            return {"error": "Lambda客户端不可用"}
        
        # 测试简单的Lambda函数
        test_functions = [
            {
                "name": "ai-ppt-assistant-list-presentations",
                "payload": {}
            },
            {
                "name": "ai-ppt-assistant-get-task", 
                "payload": {"task_id": "test-task-id"}
            }
        ]
        
        for func_test in test_functions:
            try:
                response = lambda_client.invoke(
                    FunctionName=func_test["name"],
                    InvocationType='RequestResponse',
                    Payload=json.dumps(func_test["payload"])
                )
                
                status_code = response['StatusCode']
                payload_response = json.loads(response['Payload'].read().decode())
                
                lambda_results[func_test["name"]] = {
                    "status_code": status_code,
                    "response": payload_response,
                    "success": status_code == 200
                }
                
                if status_code == 200:
                    self.log_test(f"Lambda调用", "PASS", 
                                f"{func_test['name']} 调用成功")
                else:
                    self.log_test(f"Lambda调用", "FAIL", 
                                f"{func_test['name']} 调用失败: {status_code}")
                    
            except Exception as e:
                lambda_results[func_test["name"]] = {
                    "error": str(e),
                    "success": False
                }
                self.log_test(f"Lambda调用", "FAIL", 
                            f"{func_test['name']} 异常: {str(e)}")
        
        return lambda_results
    
    def test_concurrent_requests(self) -> Dict[str, Any]:
        """测试并发请求处理能力"""
        print("\n" + "="*60)
        print("🔄 测试并发请求处理")
        print("="*60)
        
        concurrent_results = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0,
            "max_response_time": 0,
            "min_response_time": float('inf'),
            "results": []
        }
        
        def make_request(request_id: int) -> Dict[str, Any]:
            """发起单个请求"""
            start_time = time.time()
            
            try:
                response = requests.get(
                    f"{API_BASE_URL}/presentations",
                    headers=HEADERS,
                    timeout=30
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                return {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "success": response.status_code == 200,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                end_time = time.time()
                response_time = end_time - start_time
                
                return {
                    "request_id": request_id,
                    "error": str(e),
                    "response_time": response_time,
                    "success": False,
                    "timestamp": datetime.now().isoformat()
                }
        
        # 使用线程池发起10个并发请求
        num_requests = 10
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                concurrent_results["results"].append(result)
                
                concurrent_results["total_requests"] += 1
                
                if result["success"]:
                    concurrent_results["successful_requests"] += 1
                else:
                    concurrent_results["failed_requests"] += 1
                
                response_time = result["response_time"]
                concurrent_results["max_response_time"] = max(
                    concurrent_results["max_response_time"], response_time
                )
                concurrent_results["min_response_time"] = min(
                    concurrent_results["min_response_time"], response_time
                )
        
        # 计算平均响应时间
        total_time = sum(r["response_time"] for r in concurrent_results["results"])
        concurrent_results["average_response_time"] = total_time / num_requests
        
        success_rate = (concurrent_results["successful_requests"] / num_requests) * 100
        
        self.log_test("并发请求测试", "PASS" if success_rate >= 80 else "FAIL",
                    f"成功率: {success_rate:.1f}% ({concurrent_results['successful_requests']}/{num_requests})")
        
        self.log_test("响应时间统计", "INFO",
                    f"平均: {concurrent_results['average_response_time']:.2f}s, "
                    f"最大: {concurrent_results['max_response_time']:.2f}s, "
                    f"最小: {concurrent_results['min_response_time']:.2f}s")
        
        return concurrent_results
    
    def generate_test_report(self) -> Dict[str, Any]:
        """生成综合测试报告"""
        print("\n" + "="*60)
        print("📊 生成综合后台功能测试报告")
        print("="*60)
        
        # 统计测试结果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed_tests = sum(1 for r in self.test_results if r["status"] == "FAIL")
        warnings = sum(1 for r in self.test_results if r["status"] == "WARNING")
        
        report = {
            "test_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "warnings": warnings,
                "success_rate": f"{(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%"
            },
            "detailed_results": self.test_results,
            "test_resources": {
                "session_id": self.test_session_id,
                "presentation_ids": self.test_presentation_ids,
                "task_ids": self.test_task_ids
            }
        }
        
        # 保存报告到文件
        with open("backend_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📈 测试统计:")
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"警告: {warnings}")
        print(f"成功率: {report['test_summary']['success_rate']}")
        
        if failed_tests > 0:
            print(f"\n❌ 失败的测试:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test_name']}: {result['details']}")
        
        print(f"\n💾 详细报告已保存到: backend_test_report.json")
        
        return report
    
    def run_comprehensive_tests(self):
        """运行综合后台功能测试"""
        print("🚀 开始后台功能深度测试...")
        print(f"🕒 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🆔 测试会话ID: {self.test_session_id}")
        
        try:
            # 1. 测试完整的演示文稿工作流程
            workflow_results = self.test_presentation_workflow()
            
            # 2. 测试Lambda函数直接调用
            lambda_results = self.test_lambda_functions()
            
            # 3. 测试并发处理能力
            concurrent_results = self.test_concurrent_requests()
            
            # 4. 生成综合报告
            report = self.generate_test_report()
            
            return report
            
        except KeyboardInterrupt:
            print("\n⚠️ 测试被用户中断")
            return None
        except Exception as e:
            print(f"\n❌ 测试过程中发生错误: {str(e)}")
            return None
        finally:
            # 总是执行清理
            self.cleanup_test_resources()


def main():
    """主函数"""
    tester = BackendTester()
    
    try:
        report = tester.run_comprehensive_tests()
        if report:
            success_rate = float(report["test_summary"]["success_rate"].rstrip("%"))
            
            if success_rate >= 90:
                print("\n🎉 后台功能测试完成 - 优秀！")
            elif success_rate >= 70:
                print("\n✅ 后台功能测试完成 - 良好")
            else:
                print("\n⚠️ 后台功能测试完成 - 需要改进")
                
            return 0 if success_rate >= 70 else 1
        else:
            return 1
            
    except Exception as e:
        print(f"\n❌ 测试执行失败: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())