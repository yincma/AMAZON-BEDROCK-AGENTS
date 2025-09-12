#!/usr/bin/env python3
"""
部署后自动验证脚本
验证所有关键组件是否正常工作
"""

import boto3
import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# 配置
REGION = 'us-east-1'
PROJECT = 'ai-ppt-assistant'
ENVIRONMENT = 'dev'

class DeploymentValidator:
    def __init__(self):
        """初始化验证器"""
        self.ssm = boto3.client('ssm', region_name=REGION)
        self.lambda_client = boto3.client('lambda', region_name=REGION)
        self.apigateway = boto3.client('apigateway', region_name=REGION)
        self.dynamodb = boto3.resource('dynamodb', region_name=REGION)
        self.bedrock = boto3.client('bedrock-agent', region_name=REGION)
        
        self.validations = []
        self.api_url = None
        self.api_key = None
        
    def log(self, message: str, status: str = "INFO"):
        """打印日志"""
        symbols = {
            "SUCCESS": "✅",
            "FAIL": "❌",
            "WARNING": "⚠️",
            "INFO": "🔍"
        }
        print(f"{symbols.get(status, '📝')} {message}")
        
    def get_config_from_ssm(self):
        """从SSM获取配置"""
        try:
            # 获取API URL
            response = self.ssm.get_parameter(Name=f'/{PROJECT}/{ENVIRONMENT}/api-gateway-url')
            self.api_url = response['Parameter']['Value']
            
            # 获取API Key
            response = self.ssm.get_parameter(
                Name=f'/{PROJECT}/{ENVIRONMENT}/api-key',
                WithDecryption=True
            )
            self.api_key = response['Parameter']['Value']
            
            self.log(f"API URL: {self.api_url}", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"获取配置失败: {str(e)}", "FAIL")
            return False
    
    def validate_api_health(self):
        """验证API健康检查"""
        self.log("验证API健康检查...", "INFO")
        
        try:
            # 构造健康检查URL
            health_url = f"{self.api_url}/health"
            
            response = requests.get(
                health_url,
                headers={'x-api-key': self.api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                self.validations.append({
                    'test': 'API Health Check',
                    'status': True,
                    'message': f"Status: {response.status_code}"
                })
                self.log("API健康检查通过", "SUCCESS")
                return True
            else:
                self.validations.append({
                    'test': 'API Health Check',
                    'status': False,
                    'message': f"Status: {response.status_code}"
                })
                self.log(f"API健康检查失败: {response.status_code}", "FAIL")
                return False
                
        except Exception as e:
            self.validations.append({
                'test': 'API Health Check',
                'status': False,
                'message': str(e)
            })
            self.log(f"API健康检查异常: {str(e)}", "FAIL")
            return False
    
    def validate_create_presentation(self):
        """验证创建演示文稿API"""
        self.log("测试创建演示文稿API...", "INFO")
        
        try:
            response = requests.post(
                f"{self.api_url}/presentations",
                headers={'x-api-key': self.api_key},
                json={
                    'topic': 'Deployment Test - ' + datetime.now().strftime('%Y%m%d %H:%M:%S'),
                    'slides': 3,
                    'language': 'zh-CN',
                    'test_mode': True  # 测试模式，快速返回
                },
                timeout=30
            )
            
            if response.status_code in [200, 201, 202]:
                data = response.json()
                task_id = data.get('taskId', data.get('task_id'))
                
                self.validations.append({
                    'test': 'Create Presentation API',
                    'status': True,
                    'message': f"Task ID: {task_id}"
                })
                self.log(f"创建演示文稿成功, Task ID: {task_id}", "SUCCESS")
                return task_id
            else:
                self.validations.append({
                    'test': 'Create Presentation API',
                    'status': False,
                    'message': f"Status: {response.status_code}"
                })
                self.log(f"创建演示文稿失败: {response.status_code}", "FAIL")
                return None
                
        except Exception as e:
            self.validations.append({
                'test': 'Create Presentation API',
                'status': False,
                'message': str(e)
            })
            self.log(f"创建演示文稿异常: {str(e)}", "FAIL")
            return None
    
    def validate_lambda_functions(self):
        """验证Lambda函数配置"""
        self.log("验证Lambda函数配置...", "INFO")
        
        critical_functions = [
            'ai-ppt-assistant-api-generate-presentation',
            'ai-ppt-assistant-generate-content',
            'ai-ppt-assistant-generate-image',
            'ai-ppt-assistant-compile-pptx'
        ]
        
        all_configured = True
        
        for func_name in critical_functions:
            try:
                config = self.lambda_client.get_function_configuration(
                    FunctionName=func_name
                )
                
                env_vars = config.get('Environment', {}).get('Variables', {})
                
                # 检查关键配置
                has_ssm_config = 'CONFIG_SOURCE' in env_vars or 'SSM_PREFIX' in env_vars
                has_table_config = 'DYNAMODB_TABLE' in env_vars
                
                is_configured = has_ssm_config or has_table_config
                
                self.validations.append({
                    'test': f'Lambda: {func_name.split("-")[-1]}',
                    'status': is_configured,
                    'message': 'Configured' if is_configured else 'Missing config'
                })
                
                if is_configured:
                    self.log(f"Lambda {func_name.split('-')[-1]} 配置正确", "SUCCESS")
                else:
                    self.log(f"Lambda {func_name.split('-')[-1]} 配置缺失", "FAIL")
                    all_configured = False
                    
            except Exception as e:
                self.validations.append({
                    'test': f'Lambda: {func_name.split("-")[-1]}',
                    'status': False,
                    'message': str(e)
                })
                self.log(f"Lambda {func_name.split('-')[-1]} 验证失败: {str(e)}", "FAIL")
                all_configured = False
        
        return all_configured
    
    def validate_bedrock_agents(self):
        """验证Bedrock Agent配置"""
        self.log("验证Bedrock Agent配置...", "INFO")
        
        agents = {
            'orchestrator': 'Q6RODNGFYR',
            'content': 'L0ZQHJSU4X',
            'visual': 'FO53FNXIRL',
            'compiler': 'B02XIGCUKI'
        }
        
        all_ready = True
        
        for agent_type, agent_id in agents.items():
            try:
                # 检查Agent别名
                response = self.bedrock.list_agent_aliases(agentId=agent_id)
                aliases = response.get('agentAliasSummaries', [])
                
                has_dev_alias = any(
                    a.get('agentAliasName') == 'dev' 
                    for a in aliases
                )
                
                self.validations.append({
                    'test': f'Bedrock Agent: {agent_type}',
                    'status': has_dev_alias,
                    'message': 'Alias configured' if has_dev_alias else 'Missing alias'
                })
                
                if has_dev_alias:
                    self.log(f"Bedrock Agent {agent_type} 别名配置正确", "SUCCESS")
                else:
                    self.log(f"Bedrock Agent {agent_type} 缺少别名", "FAIL")
                    all_ready = False
                    
            except Exception as e:
                self.validations.append({
                    'test': f'Bedrock Agent: {agent_type}',
                    'status': False,
                    'message': str(e)
                })
                self.log(f"Bedrock Agent {agent_type} 验证失败: {str(e)}", "FAIL")
                all_ready = False
        
        return all_ready
    
    def validate_dynamodb_tables(self):
        """验证DynamoDB表"""
        self.log("验证DynamoDB表...", "INFO")
        
        table_name = f'{PROJECT}-{ENVIRONMENT}-sessions'
        
        try:
            table = self.dynamodb.Table(table_name)
            table.load()
            
            # 检查表状态
            is_active = table.table_status == 'ACTIVE'
            
            self.validations.append({
                'test': f'DynamoDB Table: {table_name}',
                'status': is_active,
                'message': f'Status: {table.table_status}'
            })
            
            if is_active:
                self.log(f"DynamoDB表 {table_name} 状态正常", "SUCCESS")
            else:
                self.log(f"DynamoDB表 {table_name} 状态异常: {table.table_status}", "FAIL")
            
            return is_active
            
        except Exception as e:
            self.validations.append({
                'test': f'DynamoDB Table: {table_name}',
                'status': False,
                'message': str(e)
            })
            self.log(f"DynamoDB表验证失败: {str(e)}", "FAIL")
            return False
    
    def generate_report(self):
        """生成验证报告"""
        print("\n" + "="*60)
        print("🎯 部署验证报告")
        print("="*60)
        
        passed = sum(1 for v in self.validations if v['status'])
        total = len(self.validations)
        
        for validation in self.validations:
            status_icon = "✅" if validation['status'] else "❌"
            print(f"{status_icon} {validation['test']}: {validation['message']}")
        
        print("\n" + "-"*60)
        success_rate = (passed/total)*100 if total > 0 else 0
        print(f"📊 结果: {passed}/{total} 通过 ({success_rate:.1f}%)")
        
        # 保存报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'validations': self.validations,
            'summary': {
                'total': total,
                'passed': passed,
                'failed': total - passed,
                'success_rate': f"{success_rate:.1f}%"
            }
        }
        
        report_file = f'deployment_validation_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        return passed == total
    
    def run(self):
        """执行验证流程"""
        print("🚀 开始部署验证...")
        print("="*60)
        
        # 获取配置
        if not self.get_config_from_ssm():
            self.log("无法获取必要配置，验证中止", "FAIL")
            return False
        
        # 执行各项验证
        self.validate_api_health()
        self.validate_create_presentation()
        self.validate_lambda_functions()
        self.validate_bedrock_agents()
        self.validate_dynamodb_tables()
        
        # 生成报告
        all_passed = self.generate_report()
        
        if all_passed:
            print("\n🎉 所有验证通过！部署成功！")
            return 0
        else:
            print("\n⚠️ 部分验证失败，请检查报告")
            return 1

def main():
    """主函数"""
    validator = DeploymentValidator()
    return validator.run()

if __name__ == "__main__":
    sys.exit(main())