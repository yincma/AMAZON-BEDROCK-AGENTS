#!/usr/bin/env python3
"""
部署验证脚本 - 全面检查AI PPT Assistant部署状态
"""
import boto3
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple

class DeploymentValidator:
    def __init__(self):
        self.ssm = boto3.client('ssm', region_name='us-east-1')
        self.lambda_client = boto3.client('lambda', region_name='us-east-1')
        self.apigateway = boto3.client('apigateway', region_name='us-east-1')
        self.dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        self.bedrock = boto3.client('bedrock-agent', region_name='us-east-1')
        
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        
    def check_api_keys_security(self) -> bool:
        """验证API密钥安全配置"""
        print("🔒 检查API密钥安全...")
        
        try:
            # 检查SSM中的密钥
            param = self.ssm.get_parameter(
                Name='/ai-ppt-assistant/dev/api-key',
                WithDecryption=True
            )
            
            if param['Parameter']['Value']:
                self.results['passed'].append("API密钥已存储在SSM Parameter Store")
                
                # 检查是否还有泄露的密钥活跃
                leaked_key = "9EQHqfmiuA5GrkMnK5PVf8OpbIcsMj1N2z6PFGR3"
                api_keys = self.apigateway.get_api_keys()
                
                for key in api_keys['items']:
                    if key.get('value') == leaked_key and key.get('enabled'):
                        self.results['failed'].append("泄露的API密钥仍然启用")
                        return False
                        
                return True
            else:
                self.results['failed'].append("SSM中未找到API密钥")
                return False
                
        except Exception as e:
            self.results['failed'].append(f"API密钥检查失败: {str(e)}")
            return False
            
    def check_agent_aliases(self) -> bool:
        """验证Bedrock Agent别名配置"""
        print("🤖 检查Bedrock Agent别名...")
        
        agent_ids = {
            'compiler': 'B02XIGCUKI',
            'content': 'L0ZQHJSU4X',
            'orchestrator': 'Q6RODNGFYR',
            'visual': 'FO53FNXIRL'
        }
        
        all_good = True
        for agent_type, agent_id in agent_ids.items():
            try:
                aliases = self.bedrock.list_agent_aliases(agentId=agent_id)
                
                has_dev_alias = any(
                    alias['aliasName'] == 'dev' 
                    for alias in aliases.get('agentAliasSummaries', [])
                )
                
                if has_dev_alias:
                    self.results['passed'].append(f"{agent_type} Agent有dev别名")
                else:
                    self.results['warnings'].append(f"{agent_type} Agent缺少dev别名")
                    all_good = False
                    
            except Exception as e:
                self.results['failed'].append(f"{agent_type} Agent检查失败: {str(e)}")
                all_good = False
                
        return all_good
        
    def check_api_gateway_unity(self) -> bool:
        """验证API Gateway统一配置"""
        print("🌐 检查API Gateway配置...")
        
        try:
            apis = self.apigateway.get_rest_apis()
            api_count = len(apis['items'])
            
            if api_count == 1:
                api = apis['items'][0]
                api_id = api['id']
                
                # 检查stages
                stages = self.apigateway.get_stages(restApiId=api_id)
                stage_names = [s['stageName'] for s in stages['item']]
                
                if 'legacy' in stage_names:
                    self.results['warnings'].append("存在legacy stage，应该删除")
                    
                if 'dev' in stage_names:
                    self.results['passed'].append("API Gateway配置正确（有dev stage）")
                    return True
                else:
                    self.results['failed'].append("缺少dev stage")
                    return False
                    
            else:
                self.results['failed'].append(f"存在{api_count}个API Gateway（应该只有1个）")
                return False
                
        except Exception as e:
            self.results['failed'].append(f"API Gateway检查失败: {str(e)}")
            return False
            
    def check_dynamodb_tables(self) -> bool:
        """验证DynamoDB表配置"""
        print("💾 检查DynamoDB表...")
        
        expected_tables = [
            'ai-ppt-assistant-dev-sessions',
            'ai-ppt-assistant-dev-tasks',
            'ai-ppt-assistant-dev-checkpoints'
        ]
        
        try:
            tables = self.dynamodb.list_tables()
            existing_tables = tables['TableNames']
            
            all_exist = all(table in existing_tables for table in expected_tables)
            
            if all_exist:
                self.results['passed'].append("所有DynamoDB表都存在")
                return True
            else:
                missing = [t for t in expected_tables if t not in existing_tables]
                self.results['failed'].append(f"缺少DynamoDB表: {missing}")
                return False
                
        except Exception as e:
            self.results['failed'].append(f"DynamoDB检查失败: {str(e)}")
            return False
            
    def check_lambda_configurations(self) -> bool:
        """验证Lambda函数配置"""
        print("⚡ 检查Lambda函数配置...")
        
        critical_functions = [
            'ai-ppt-assistant-api-generate-presentation',
            'ai-ppt-assistant-generate-content',
            'ai-ppt-assistant-generate-image',
            'ai-ppt-assistant-compile-pptx'
        ]
        
        all_good = True
        for func_name in critical_functions:
            try:
                config = self.lambda_client.get_function_configuration(
                    FunctionName=func_name
                )
                
                env_vars = config.get('Environment', {}).get('Variables', {})
                
                # 检查关键环境变量
                if 'placeholder' in str(env_vars).lower():
                    self.results['failed'].append(f"{func_name} 使用占位符配置")
                    all_good = False
                    
                if env_vars.get('DYNAMODB_TABLE') == 'ai-ppt-assistant-dev-tasks':
                    self.results['warnings'].append(f"{func_name} 使用tasks表而非sessions表")
                    
                if 'CONFIG_SOURCE' not in env_vars:
                    self.results['warnings'].append(f"{func_name} 未配置CONFIG_SOURCE")
                    
            except Exception as e:
                self.results['failed'].append(f"{func_name} 检查失败: {str(e)}")
                all_good = False
                
        if all_good:
            self.results['passed'].append("Lambda函数基本配置正确")
            
        return all_good
        
    def check_ssm_parameters(self) -> bool:
        """验证SSM Parameter Store配置"""
        print("🔧 检查SSM配置中心...")
        
        try:
            params = self.ssm.get_parameters_by_path(
                Path='/ai-ppt-assistant/dev/',
                Recursive=True
            )
            
            param_count = len(params['Parameters'])
            
            if param_count >= 30:
                self.results['passed'].append(f"SSM配置完整（{param_count}个参数）")
                return True
            else:
                self.results['warnings'].append(f"SSM参数较少（{param_count}个）")
                return True
                
        except Exception as e:
            self.results['failed'].append(f"SSM检查失败: {str(e)}")
            return False
            
    def generate_report(self) -> Dict:
        """生成验证报告"""
        total_checks = len(self.results['passed']) + len(self.results['failed']) + len(self.results['warnings'])
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_checks': total_checks,
                'passed': len(self.results['passed']),
                'failed': len(self.results['failed']),
                'warnings': len(self.results['warnings']),
                'health_score': (len(self.results['passed']) / total_checks * 100) if total_checks > 0 else 0
            },
            'details': self.results,
            'recommendations': []
        }
        
        # 添加建议
        if self.results['failed']:
            report['recommendations'].append("🔴 立即修复失败项以确保系统正常运行")
            
        if self.results['warnings']:
            report['recommendations'].append("🟡 尽快处理警告项以避免潜在问题")
            
        if report['summary']['health_score'] < 80:
            report['recommendations'].append("⚠️ 系统健康度较低，建议执行完整的修复计划")
            
        return report
        
    def run_validation(self) -> int:
        """执行完整验证"""
        print("\n" + "="*60)
        print("🚀 AI PPT Assistant 部署验证")
        print("="*60 + "\n")
        
        # 执行各项检查
        checks = [
            ("API密钥安全", self.check_api_keys_security),
            ("Agent别名", self.check_agent_aliases),
            ("API Gateway", self.check_api_gateway_unity),
            ("DynamoDB表", self.check_dynamodb_tables),
            ("Lambda配置", self.check_lambda_configurations),
            ("SSM参数", self.check_ssm_parameters)
        ]
        
        for check_name, check_func in checks:
            try:
                check_func()
            except Exception as e:
                self.results['failed'].append(f"{check_name}检查异常: {str(e)}")
                
        # 生成报告
        report = self.generate_report()
        
        # 显示结果
        print("\n" + "="*60)
        print("📊 验证结果")
        print("="*60)
        
        print(f"\n✅ 通过项 ({len(self.results['passed'])}个):")
        for item in self.results['passed']:
            print(f"  • {item}")
            
        if self.results['warnings']:
            print(f"\n⚠️ 警告项 ({len(self.results['warnings'])}个):")
            for item in self.results['warnings']:
                print(f"  • {item}")
                
        if self.results['failed']:
            print(f"\n❌ 失败项 ({len(self.results['failed'])}个):")
            for item in self.results['failed']:
                print(f"  • {item}")
                
        print(f"\n📈 系统健康度: {report['summary']['health_score']:.1f}%")
        
        if report['recommendations']:
            print("\n💡 建议:")
            for rec in report['recommendations']:
                print(f"  {rec}")
                
        # 保存报告
        with open('deployment_validation_report.json', 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"\n📁 详细报告已保存到: deployment_validation_report.json")
        
        # 返回状态码
        if self.results['failed']:
            return 1  # 有失败项
        elif self.results['warnings']:
            return 2  # 有警告项
        else:
            return 0  # 全部通过
            
if __name__ == "__main__":
    validator = DeploymentValidator()
    exit_code = validator.run_validation()
    sys.exit(exit_code)