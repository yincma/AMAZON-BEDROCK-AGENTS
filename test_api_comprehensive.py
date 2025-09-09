#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI PPT Assistant API 完整功能测试脚本
测试所有API端点的功能和错误处理
"""

import json
import time
import requests
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_test_results.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class APITestSuite:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        # 设置默认请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
        
        self.test_results = []
        self.test_data = {}
        
    def log_test_result(self, test_name: str, success: bool, details: str, response_time: float = 0):
        result = {
            'timestamp': datetime.now().isoformat(),
            'test_name': test_name,
            'success': success,
            'details': details,
            'response_time': response_time
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {details}")
        
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            response = self.session.request(method, url, **kwargs)
            response_time = time.time() - start_time
            
            logger.debug(f"{method} {url} -> {response.status_code} ({response_time:.2f}s)")
            return response
            
        except Exception as e:
            logger.error(f"Request failed: {method} {url} - {str(e)}")
            raise
    
    def test_health_check(self):
        """测试健康检查端点"""
        logger.info("🏥 测试健康检查端点...")
        
        # 测试基本健康检查
        start_time = time.time()
        try:
            response = self.make_request('GET', '/health')
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                self.log_test_result(
                    'health_check_basic',
                    True,
                    f"健康检查返回正常状态: {data.get('status', 'unknown')}",
                    response_time
                )
            else:
                self.log_test_result(
                    'health_check_basic',
                    False,
                    f"健康检查失败，状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test_result('health_check_basic', False, f"健康检查异常: {str(e)}")
        
        # 测试就绪检查
        try:
            response = self.make_request('GET', '/health/ready')
            response_time = time.time() - start_time
            
            if response.status_code in [200, 503]:
                data = response.json()
                self.log_test_result(
                    'readiness_check',
                    True,
                    f"就绪检查完成，状态: {data.get('status', 'unknown')}"
                )
            else:
                self.log_test_result(
                    'readiness_check',
                    False,
                    f"就绪检查返回异常状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test_result('readiness_check', False, f"就绪检查异常: {str(e)}")
    
    def test_presentations_api(self):
        """测试演示文稿相关API"""
        logger.info("📊 测试演示文稿API...")
        
        # 测试创建演示文稿
        presentation_data = {
            "title": "AI技术在教育领域的应用",
            "topic": "介绍人工智能技术在教育领域的具体应用场景，包括个性化学习、智能辅导、教学评估等方面",
            "audience": "technical",
            "duration": 25,
            "slide_count": 15,
            "language": "zh",
            "style": "professional",
            "template": "technology_showcase",
            "include_speaker_notes": True,
            "include_images": True,
            "metadata": {
                "test_run": True,
                "created_by": "api_test_suite"
            }
        }
        
        start_time = time.time()
        try:
            response = self.make_request('POST', '/presentations', json=presentation_data)
            response_time = time.time() - start_time
            
            if response.status_code == 202:
                data = response.json()
                presentation_id = data.get('presentation_id')
                self.test_data['presentation_id'] = presentation_id
                
                self.log_test_result(
                    'create_presentation',
                    True,
                    f"演示文稿创建成功，ID: {presentation_id}",
                    response_time
                )
                
                # 测试获取演示文稿状态
                self.test_presentation_status(presentation_id)
                
            else:
                self.log_test_result(
                    'create_presentation',
                    False,
                    f"演示文稿创建失败，状态码: {response.status_code}, 响应: {response.text}"
                )
        except Exception as e:
            self.log_test_result('create_presentation', False, f"创建演示文稿异常: {str(e)}")
        
        # 测试列出演示文稿
        try:
            response = self.make_request('GET', '/presentations', params={'limit': 10})
            
            if response.status_code == 200:
                data = response.json()
                presentations_count = len(data.get('items', []))
                self.log_test_result(
                    'list_presentations',
                    True,
                    f"获取演示文稿列表成功，找到 {presentations_count} 个演示文稿"
                )
            else:
                self.log_test_result(
                    'list_presentations',
                    False,
                    f"获取演示文稿列表失败，状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test_result('list_presentations', False, f"列出演示文稿异常: {str(e)}")
    
    def test_presentation_status(self, presentation_id: str):
        """测试获取演示文稿状态"""
        max_checks = 5
        check_interval = 10  # 秒
        
        for i in range(max_checks):
            try:
                response = self.make_request('GET', f'/presentations/{presentation_id}')
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    progress = data.get('progress', 0)
                    
                    self.log_test_result(
                        f'get_presentation_status_check_{i+1}',
                        True,
                        f"状态: {status}, 进度: {progress:.1%}"
                    )
                    
                    if status in ['completed', 'failed']:
                        if status == 'completed':
                            # 测试下载演示文稿
                            self.test_download_presentation(presentation_id)
                        break
                        
                elif response.status_code == 404:
                    self.log_test_result(
                        f'get_presentation_status_check_{i+1}',
                        False,
                        f"演示文稿不存在: {presentation_id}"
                    )
                    break
                else:
                    self.log_test_result(
                        f'get_presentation_status_check_{i+1}',
                        False,
                        f"获取状态失败，状态码: {response.status_code}"
                    )
                
                if i < max_checks - 1:
                    logger.info(f"等待 {check_interval} 秒后进行下一次状态检查...")
                    time.sleep(check_interval)
                    
            except Exception as e:
                self.log_test_result(
                    f'get_presentation_status_check_{i+1}',
                    False,
                    f"检查状态异常: {str(e)}"
                )
    
    def test_download_presentation(self, presentation_id: str):
        """测试下载演示文稿"""
        try:
            response = self.make_request('GET', f'/presentations/{presentation_id}/download')
            
            if response.status_code == 200:
                content_length = len(response.content)
                content_type = response.headers.get('Content-Type', 'unknown')
                
                self.log_test_result(
                    'download_presentation',
                    True,
                    f"下载成功，文件大小: {content_length} 字节, 类型: {content_type}"
                )
                
                # 保存文件用于验证
                filename = f"test_presentation_{presentation_id[:8]}.pptx"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                logger.info(f"演示文稿已保存为: {filename}")
                
            elif response.status_code == 409:
                self.log_test_result(
                    'download_presentation',
                    True,
                    "演示文稿尚未完成，无法下载（预期行为）"
                )
            else:
                self.log_test_result(
                    'download_presentation',
                    False,
                    f"下载失败，状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test_result('download_presentation', False, f"下载异常: {str(e)}")
    
    def test_sessions_api(self):
        """测试会话管理API"""
        logger.info("🔄 测试会话管理API...")
        
        # 测试创建会话
        session_data = {
            "user_id": f"test_user_{int(time.time())}",
            "session_name": "API测试会话",
            "metadata": {
                "test_run": True,
                "purpose": "automated_testing"
            }
        }
        
        try:
            response = self.make_request('POST', '/sessions', json=session_data)
            
            if response.status_code == 202:
                data = response.json()
                session_id = data.get('session_id')
                self.test_data['session_id'] = session_id
                
                self.log_test_result(
                    'create_session',
                    True,
                    f"会话创建成功，ID: {session_id}"
                )
                
                # 测试获取会话信息
                self.test_get_session(session_id)
                
            else:
                self.log_test_result(
                    'create_session',
                    False,
                    f"会话创建失败，状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test_result('create_session', False, f"创建会话异常: {str(e)}")
    
    def test_get_session(self, session_id: str):
        """测试获取会话信息"""
        try:
            response = self.make_request('GET', f'/sessions/{session_id}')
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                user_id = data.get('user_id', 'unknown')
                
                self.log_test_result(
                    'get_session',
                    True,
                    f"获取会话信息成功，状态: {status}, 用户: {user_id}"
                )
            else:
                self.log_test_result(
                    'get_session',
                    False,
                    f"获取会话信息失败，状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test_result('get_session', False, f"获取会话信息异常: {str(e)}")
    
    def test_agents_api(self):
        """测试AI代理API"""
        logger.info("🤖 测试AI代理API...")
        
        agent_names = ['orchestrator', 'content', 'visual', 'compiler']
        
        for agent_name in agent_names:
            agent_request = {
                "input": f"测试 {agent_name} 代理的响应能力",
                "session_id": self.test_data.get('session_id'),
                "enable_trace": False,
                "parameters": {
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            }
            
            try:
                response = self.make_request(
                    'POST', 
                    f'/agents/{agent_name}/execute',
                    json=agent_request
                )
                
                if response.status_code == 202:
                    data = response.json()
                    task_id = data.get('task_id')
                    
                    self.log_test_result(
                        f'execute_agent_{agent_name}',
                        True,
                        f"代理 {agent_name} 执行开始，任务ID: {task_id}"
                    )
                    
                    # 测试任务状态查询
                    if task_id:
                        self.test_task_status(task_id, agent_name)
                        
                else:
                    self.log_test_result(
                        f'execute_agent_{agent_name}',
                        False,
                        f"代理 {agent_name} 执行失败，状态码: {response.status_code}"
                    )
            except Exception as e:
                self.log_test_result(
                    f'execute_agent_{agent_name}',
                    False,
                    f"执行代理 {agent_name} 异常: {str(e)}"
                )
    
    def test_task_status(self, task_id: str, agent_name: str):
        """测试任务状态查询"""
        max_checks = 3
        check_interval = 5
        
        for i in range(max_checks):
            try:
                response = self.make_request('GET', f'/tasks/{task_id}')
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    progress = data.get('progress', 0)
                    
                    self.log_test_result(
                        f'get_task_status_{agent_name}_check_{i+1}',
                        True,
                        f"任务状态: {status}, 进度: {progress:.1%}"
                    )
                    
                    if status in ['completed', 'failed']:
                        break
                        
                else:
                    self.log_test_result(
                        f'get_task_status_{agent_name}_check_{i+1}',
                        False,
                        f"获取任务状态失败，状态码: {response.status_code}"
                    )
                
                if i < max_checks - 1:
                    time.sleep(check_interval)
                    
            except Exception as e:
                self.log_test_result(
                    f'get_task_status_{agent_name}_check_{i+1}',
                    False,
                    f"查询任务状态异常: {str(e)}"
                )
    
    def test_templates_api(self):
        """测试模板API"""
        logger.info("📋 测试模板API...")
        
        try:
            response = self.make_request('GET', '/templates', params={'limit': 20})
            
            if response.status_code == 200:
                templates = response.json()
                template_count = len(templates)
                
                self.log_test_result(
                    'get_templates',
                    True,
                    f"获取模板列表成功，找到 {template_count} 个模板"
                )
                
                # 记录可用模板
                if templates:
                    template_names = [t.get('template_id', 'unknown') for t in templates]
                    logger.info(f"可用模板: {', '.join(template_names)}")
                    
            else:
                self.log_test_result(
                    'get_templates',
                    False,
                    f"获取模板列表失败，状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test_result('get_templates', False, f"获取模板异常: {str(e)}")
    
    def test_error_handling(self):
        """测试错误处理"""
        logger.info("⚠️ 测试错误处理...")
        
        # 测试无效的演示文稿ID
        fake_id = str(uuid.uuid4())
        try:
            response = self.make_request('GET', f'/presentations/{fake_id}')
            
            if response.status_code == 404:
                self.log_test_result(
                    'error_invalid_presentation_id',
                    True,
                    "正确返回404错误（无效演示文稿ID）"
                )
            else:
                self.log_test_result(
                    'error_invalid_presentation_id',
                    False,
                    f"未正确处理无效ID，状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test_result('error_invalid_presentation_id', False, f"测试异常: {str(e)}")
        
        # 测试无效的代理名称
        try:
            response = self.make_request(
                'POST',
                '/agents/invalid_agent/execute',
                json={"input": "test"}
            )
            
            if response.status_code == 404:
                self.log_test_result(
                    'error_invalid_agent_name',
                    True,
                    "正确返回404错误（无效代理名称）"
                )
            else:
                self.log_test_result(
                    'error_invalid_agent_name',
                    False,
                    f"未正确处理无效代理名称，状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test_result('error_invalid_agent_name', False, f"测试异常: {str(e)}")
        
        # 测试无效请求数据
        try:
            response = self.make_request('POST', '/presentations', json={"invalid": "data"})
            
            if response.status_code == 400:
                self.log_test_result(
                    'error_invalid_request_data',
                    True,
                    "正确返回400错误（无效请求数据）"
                )
            else:
                self.log_test_result(
                    'error_invalid_request_data',
                    False,
                    f"未正确处理无效请求数据，状态码: {response.status_code}"
                )
        except Exception as e:
            self.log_test_result('error_invalid_request_data', False, f"测试异常: {str(e)}")
    
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始执行完整API功能测试...")
        
        start_time = datetime.now()
        
        # 按依赖顺序执行测试
        self.test_health_check()
        self.test_sessions_api()
        self.test_presentations_api()
        self.test_agents_api()
        self.test_templates_api()
        self.test_error_handling()
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # 生成测试报告
        self.generate_test_report(duration)
    
    def generate_test_report(self, duration):
        """生成测试报告"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': f"{success_rate:.1f}%",
                'duration': str(duration),
                'timestamp': datetime.now().isoformat()
            },
            'test_results': self.test_results,
            'test_data': self.test_data
        }
        
        # 保存详细报告
        with open('api_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印摘要
        logger.info("📊 测试完成，结果摘要:")
        logger.info(f"   总测试数: {total_tests}")
        logger.info(f"   通过数: {passed_tests}")
        logger.info(f"   失败数: {failed_tests}")
        logger.info(f"   成功率: {success_rate:.1f}%")
        logger.info(f"   总耗时: {duration}")
        
        if failed_tests > 0:
            logger.warning("❌ 存在失败的测试，详细信息请查看日志和报告文件")
        else:
            logger.info("✅ 所有测试均通过！")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI PPT Assistant API 完整功能测试')
    parser.add_argument('--url', default='http://localhost:3000', help='API基础URL')
    parser.add_argument('--api-key', help='API密钥（如果需要）')
    
    args = parser.parse_args()
    
    logger.info(f"🔧 测试配置:")
    logger.info(f"   API URL: {args.url}")
    logger.info(f"   API Key: {'已设置' if args.api_key else '未设置'}")
    
    # 创建测试套件并运行
    test_suite = APITestSuite(args.url, args.api_key)
    test_suite.run_all_tests()

if __name__ == '__main__':
    main()