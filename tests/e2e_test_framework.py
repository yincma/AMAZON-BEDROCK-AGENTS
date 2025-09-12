#!/usr/bin/env python3
"""
端到端自动化测试框架
测试完整的PPT生成流程，确保系统正常工作
"""

import json
import time
import boto3
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import sys
import os

# 添加共享模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambdas', 'shared'))
from config_loader import ConfigLoader, ConfigValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class E2ETestFramework:
    """
    端到端测试框架
    自动测试整个PPT生成流程
    """
    
    def __init__(self):
        """初始化测试框架"""
        self.config_loader = ConfigLoader()
        self.test_results = []
        self.cloudwatch = boto3.client('cloudwatch')
        self.dynamodb = boto3.client('dynamodb')
        self.s3 = boto3.client('s3')
        
        # 加载配置
        self.api_config = self.config_loader.get_api_config()
        self.db_config = self.config_loader.get_database_config()
        self.bedrock_config = self.config_loader.get_bedrock_config()
        
    def _record_test_result(self, test_name: str, status: str, details: Dict = None):
        """
        记录测试结果
        
        Args:
            test_name: 测试名称
            status: 测试状态 (PASS/FAIL/SKIP)
            details: 详细信息
        """
        result = {
            'test_name': test_name,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.test_results.append(result)
        
        # 发送CloudWatch指标
        self.cloudwatch.put_metric_data(
            Namespace='AI-PPT-Assistant/E2E-Tests',
            MetricData=[
                {
                    'MetricName': 'TestResult',
                    'Value': 1 if status == 'PASS' else 0,
                    'Unit': 'None',
                    'Dimensions': [
                        {'Name': 'TestName', 'Value': test_name},
                        {'Name': 'Status', 'Value': status}
                    ]
                }
            ]
        )
        
        logger.info(f"Test '{test_name}': {status}")
        if details:
            logger.debug(f"Details: {json.dumps(details, indent=2)}")
            
    def test_config_validation(self) -> bool:
        """
        测试1: 配置验证
        确保所有配置都有效且不包含占位符
        """
        test_name = "ConfigValidation"
        
        try:
            # 验证所有配置
            self.config_loader.validate_all_configs()
            
            # 检查具体的Bedrock配置
            for agent_type, config in self.bedrock_config.items():
                if 'placeholder' in config['id'].lower():
                    self._record_test_result(
                        test_name, 
                        'FAIL', 
                        {'error': f"{agent_type} agent ID contains placeholder"}
                    )
                    return False
                    
            self._record_test_result(test_name, 'PASS', {'message': '所有配置验证通过'})
            return True
            
        except ConfigValidationError as e:
            self._record_test_result(test_name, 'FAIL', {'error': str(e)})
            return False
        except Exception as e:
            self._record_test_result(test_name, 'FAIL', {'error': f"Unexpected error: {str(e)}"})
            return False
            
    def test_api_connectivity(self) -> bool:
        """
        测试2: API连接性
        测试API Gateway是否可访问
        """
        test_name = "APIConnectivity"
        
        try:
            # 测试健康检查端点
            url = f"{self.api_config['api_gateway_url']}/health"
            headers = {'x-api-key': self.api_config['api_key']}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self._record_test_result(test_name, 'PASS', {'status_code': response.status_code})
                return True
            else:
                self._record_test_result(
                    test_name, 
                    'FAIL', 
                    {'status_code': response.status_code, 'response': response.text}
                )
                return False
                
        except Exception as e:
            self._record_test_result(test_name, 'FAIL', {'error': str(e)})
            return False
            
    def test_create_presentation(self) -> Optional[str]:
        """
        测试3: 创建演示文稿
        测试完整的PPT创建流程
        
        Returns:
            presentation_id 如果成功，否则None
        """
        test_name = "CreatePresentation"
        
        try:
            url = f"{self.api_config['api_gateway_url']}/presentations"
            headers = {
                'x-api-key': self.api_config['api_key'],
                'Content-Type': 'application/json'
            }
            
            # 测试数据
            payload = {
                'title': f'E2E Test Presentation {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'topic': 'End-to-end testing of PPT generation system',
                'slide_count': 3,
                'language': 'en',
                'style': 'professional'
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201, 202]:
                data = response.json()
                presentation_id = data.get('presentation_id')
                
                self._record_test_result(
                    test_name, 
                    'PASS', 
                    {'presentation_id': presentation_id, 'status_code': response.status_code}
                )
                return presentation_id
            else:
                self._record_test_result(
                    test_name, 
                    'FAIL', 
                    {'status_code': response.status_code, 'response': response.text}
                )
                return None
                
        except Exception as e:
            self._record_test_result(test_name, 'FAIL', {'error': str(e)})
            return None
            
    def test_check_presentation_status(self, presentation_id: str) -> bool:
        """
        测试4: 检查演示文稿状态
        验证任务处理流程
        
        Args:
            presentation_id: 演示文稿ID
            
        Returns:
            True如果状态检查成功
        """
        test_name = "CheckPresentationStatus"
        
        if not presentation_id:
            self._record_test_result(test_name, 'SKIP', {'reason': 'No presentation_id available'})
            return False
            
        try:
            url = f"{self.api_config['api_gateway_url']}/presentations/{presentation_id}"
            headers = {'x-api-key': self.api_config['api_key']}
            
            # 最多等待5分钟
            max_wait = 300
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    
                    if status == 'completed':
                        self._record_test_result(
                            test_name, 
                            'PASS', 
                            {'status': status, 'presentation_id': presentation_id}
                        )
                        return True
                    elif status == 'failed':
                        self._record_test_result(
                            test_name, 
                            'FAIL', 
                            {'status': status, 'error': data.get('error', 'Unknown error')}
                        )
                        return False
                    else:
                        # 仍在处理中
                        logger.info(f"Presentation status: {status}, waiting...")
                        time.sleep(10)
                elif response.status_code == 404:
                    # 检查DynamoDB中的任务状态
                    task_status = self._check_task_in_dynamodb(presentation_id)
                    self._record_test_result(
                        test_name, 
                        'FAIL', 
                        {
                            'error': 'Presentation not found in API',
                            'dynamodb_status': task_status
                        }
                    )
                    return False
                else:
                    self._record_test_result(
                        test_name, 
                        'FAIL', 
                        {'status_code': response.status_code, 'response': response.text}
                    )
                    return False
                    
            # 超时
            self._record_test_result(
                test_name, 
                'FAIL', 
                {'error': f'Timeout after {max_wait} seconds'}
            )
            return False
            
        except Exception as e:
            self._record_test_result(test_name, 'FAIL', {'error': str(e)})
            return False
            
    def _check_task_in_dynamodb(self, task_id: str) -> Dict:
        """
        在DynamoDB中检查任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        try:
            response = self.dynamodb.get_item(
                TableName=self.db_config['tasks_table'],
                Key={'task_id': {'S': task_id}}
            )
            
            if 'Item' in response:
                item = response['Item']
                return {
                    'found': True,
                    'status': item.get('status', {}).get('S', 'unknown'),
                    'error': item.get('error', {}).get('S', None),
                    'progress': item.get('progress', {}).get('N', '0')
                }
            else:
                return {'found': False}
                
        except Exception as e:
            logger.error(f"Error checking DynamoDB: {str(e)}")
            return {'error': str(e)}
            
    def test_lambda_functions(self) -> bool:
        """
        测试5: Lambda函数健康检查
        验证所有Lambda函数都正常运行
        """
        test_name = "LambdaFunctions"
        lambda_client = boto3.client('lambda')
        
        try:
            # 列出所有PPT相关的Lambda函数
            response = lambda_client.list_functions(
                FunctionVersion='ALL',
                MaxItems=50
            )
            
            ppt_functions = [
                f for f in response['Functions'] 
                if 'ai-ppt-assistant' in f['FunctionName']
            ]
            
            all_healthy = True
            failed_functions = []
            
            for func in ppt_functions:
                # 检查函数配置
                config = lambda_client.get_function_configuration(
                    FunctionName=func['FunctionName']
                )
                
                # 检查环境变量
                env_vars = config.get('Environment', {}).get('Variables', {})
                
                # 验证关键环境变量
                if 'CONFIG_SOURCE' not in env_vars:
                    failed_functions.append({
                        'name': func['FunctionName'],
                        'issue': 'Missing CONFIG_SOURCE'
                    })
                    all_healthy = False
                elif env_vars.get('CONFIG_SOURCE') != 'SSM_PARAMETER_STORE':
                    failed_functions.append({
                        'name': func['FunctionName'],
                        'issue': f"CONFIG_SOURCE is {env_vars.get('CONFIG_SOURCE')}"
                    })
                    all_healthy = False
                    
            if all_healthy:
                self._record_test_result(
                    test_name, 
                    'PASS', 
                    {'total_functions': len(ppt_functions)}
                )
            else:
                self._record_test_result(
                    test_name, 
                    'FAIL', 
                    {'failed_functions': failed_functions}
                )
                
            return all_healthy
            
        except Exception as e:
            self._record_test_result(test_name, 'FAIL', {'error': str(e)})
            return False
            
    def run_all_tests(self) -> Dict[str, Any]:
        """
        运行所有端到端测试
        
        Returns:
            测试结果汇总
        """
        logger.info("="*60)
        logger.info("开始端到端测试")
        logger.info("="*60)
        
        # 测试执行顺序
        test_sequence = [
            ('配置验证', self.test_config_validation),
            ('API连接性', self.test_api_connectivity),
            ('Lambda函数健康检查', self.test_lambda_functions),
        ]
        
        # 执行基础测试
        for test_name, test_func in test_sequence:
            logger.info(f"\n执行测试: {test_name}")
            test_func()
            
        # 执行PPT生成流程测试
        logger.info("\n执行测试: PPT生成流程")
        presentation_id = self.test_create_presentation()
        if presentation_id:
            self.test_check_presentation_status(presentation_id)
            
        # 生成测试报告
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        skipped = sum(1 for r in self.test_results if r['status'] == 'SKIP')
        
        success_rate = (passed / len(self.test_results) * 100) if self.test_results else 0
        
        report = {
            'test_time': datetime.now().isoformat(),
            'summary': {
                'total_tests': len(self.test_results),
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'success_rate': f"{success_rate:.1f}%"
            },
            'test_results': self.test_results,
            'conclusion': 'ALL_TESTS_PASSED' if failed == 0 else 'TESTS_FAILED'
        }
        
        # 保存报告
        report_file = f"e2e_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        # 发送汇总指标到CloudWatch
        self.cloudwatch.put_metric_data(
            Namespace='AI-PPT-Assistant/E2E-Tests',
            MetricData=[
                {
                    'MetricName': 'TestSuccessRate',
                    'Value': success_rate,
                    'Unit': 'Percent',
                    'Dimensions': [
                        {'Name': 'Environment', 'Value': 'dev'}
                    ]
                }
            ]
        )
        
        logger.info("\n" + "="*60)
        logger.info("测试结果汇总")
        logger.info("="*60)
        logger.info(f"总测试数: {len(self.test_results)}")
        logger.info(f"通过: {passed}")
        logger.info(f"失败: {failed}")
        logger.info(f"跳过: {skipped}")
        logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"报告已保存到: {report_file}")
        
        return report

def main():
    """主函数"""
    framework = E2ETestFramework()
    report = framework.run_all_tests()
    
    # 根据测试结果决定退出码
    if report['conclusion'] == 'ALL_TESTS_PASSED':
        logger.info("\n✅ 所有测试通过！")
        sys.exit(0)
    else:
        logger.error("\n❌ 测试失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()