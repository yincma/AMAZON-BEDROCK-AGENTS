#!/usr/bin/env python3
"""
fix_agent_config.py - Bedrock Agent配置修复脚本
使用别名替代硬编码ID，确保配置的长期稳定性
"""

import boto3
import json
import sys
from datetime import datetime
from typing import Dict, Optional, List

# 配置
REGION = 'us-east-1'
PROJECT = 'ai-ppt-assistant'
ENVIRONMENT = 'dev'

# Agent配置映射（基于问题报告中的实际Agent ID）
AGENT_CONFIGS = {
    'orchestrator': {
        'agent_id': 'Q6RODNGFYR',
        'alias_name': 'dev',
        'description': 'Orchestrator Agent for PPT generation workflow',
        'functions': ['ai-ppt-assistant-api-generate-presentation', 'ai-ppt-assistant-task-processor']
    },
    'content': {
        'agent_id': 'L0ZQHJSU4X',
        'alias_name': 'dev',
        'description': 'Content Generation Agent',
        'functions': ['ai-ppt-assistant-generate-content', 'ai-ppt-assistant-create-outline']
    },
    'visual': {
        'agent_id': 'FO53FNXIRL',
        'alias_name': 'dev',
        'description': 'Visual Content Agent',
        'functions': ['ai-ppt-assistant-generate-image', 'ai-ppt-assistant-find-image']
    },
    'compiler': {
        'agent_id': 'B02XIGCUKI',
        'alias_name': 'dev',
        'description': 'PPT Compiler Agent',
        'functions': ['ai-ppt-assistant-compile-pptx', 'ai-ppt-assistant-generate-speaker-notes']
    }
}

class AgentConfigFixer:
    def __init__(self):
        """初始化AWS客户端"""
        self.bedrock = boto3.client('bedrock-agent', region_name=REGION)
        self.lambda_client = boto3.client('lambda', region_name=REGION)
        self.ssm = boto3.client('ssm', region_name=REGION)
        self.results = []
        
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }.get(level, "")
        
        print(f"{prefix} [{timestamp}] {message}")
        self.results.append({"time": timestamp, "level": level, "message": message})
    
    def create_or_update_agent_alias(self, agent_id: str, alias_name: str) -> Optional[str]:
        """为Agent创建或更新别名"""
        try:
            # 列出现有别名
            response = self.bedrock.list_agent_aliases(agentId=agent_id)
            existing_aliases = response.get('agentAliasSummaries', [])
            
            # 查找是否存在同名别名
            existing_alias = next(
                (a for a in existing_aliases if a.get('agentAliasName', '') == alias_name),
                None
            )
            
            if existing_alias:
                alias_id = existing_alias['agentAliasId']
                self.log(f"别名 '{alias_name}' 已存在于Agent {agent_id}, ID: {alias_id}", "INFO")
                return alias_id
            else:
                # 创建新别名
                response = self.bedrock.create_agent_alias(
                    agentId=agent_id,
                    agentAliasName=alias_name,
                    description=f"Alias created by fix_agent_config.py at {datetime.now()}"
                )
                alias_id = response['agentAlias']['agentAliasId']
                self.log(f"创建新别名 '{alias_name}' 成功, ID: {alias_id}", "SUCCESS")
                return alias_id
                
        except self.bedrock.exceptions.ResourceNotFoundException:
            self.log(f"Agent {agent_id} 不存在", "ERROR")
            return None
        except Exception as e:
            self.log(f"处理Agent {agent_id} 别名时出错: {str(e)}", "ERROR")
            return None
    
    def store_config_in_ssm(self, agent_type: str, config: Dict) -> bool:
        """将配置存储到SSM Parameter Store"""
        try:
            param_prefix = f"/{PROJECT}/{ENVIRONMENT}/agents/{agent_type}"
            
            # 存储参数
            parameters = {
                f"{param_prefix}/id": config['agent_id'],
                f"{param_prefix}/alias_name": config['alias_name'],
                f"{param_prefix}/alias_id": config.get('alias_id', ''),
                f"{param_prefix}/description": config['description']
            }
            
            for name, value in parameters.items():
                self.ssm.put_parameter(
                    Name=name,
                    Value=value,
                    Type="String",
                    Overwrite=True,
                    Description=f"AI PPT Assistant - {agent_type} Agent configuration"
                )
            
            self.log(f"{agent_type} Agent配置已存储到SSM", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"存储{agent_type}配置到SSM失败: {str(e)}", "ERROR")
            return False
    
    def update_lambda_functions(self, agent_type: str, config: Dict, alias_id: str) -> int:
        """更新Lambda函数环境变量"""
        updated_count = 0
        
        for func_name in config['functions']:
            try:
                # 获取当前配置
                response = self.lambda_client.get_function_configuration(
                    FunctionName=func_name
                )
                
                # 准备新的环境变量
                env_vars = response.get('Environment', {}).get('Variables', {})
                
                # 更新Agent相关配置
                updates = {
                    f'{agent_type.upper()}_AGENT_ID': config['agent_id'],
                    f'{agent_type.upper()}_AGENT_ALIAS': config['alias_name'],
                    f'{agent_type.upper()}_AGENT_ALIAS_ID': alias_id,
                    'CONFIG_SOURCE': 'SSM_PARAMETER_STORE',
                    'SSM_PREFIX': f"/{PROJECT}/{ENVIRONMENT}",
                    'DYNAMODB_TABLE': f'{PROJECT}-{ENVIRONMENT}-sessions'  # 统一使用sessions表
                }
                
                # 对于orchestrator，需要特殊处理
                if agent_type == 'orchestrator':
                    updates['ORCHESTRATOR_ALIAS_ID'] = alias_id
                
                env_vars.update(updates)
                
                # 更新Lambda配置
                self.lambda_client.update_function_configuration(
                    FunctionName=func_name,
                    Environment={'Variables': env_vars},
                    Description=f"Updated by fix_agent_config.py at {datetime.now()}"
                )
                
                self.log(f"更新Lambda函数 {func_name} 成功", "SUCCESS")
                updated_count += 1
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                self.log(f"Lambda函数 {func_name} 不存在", "WARNING")
            except Exception as e:
                self.log(f"更新Lambda函数 {func_name} 失败: {str(e)}", "ERROR")
        
        return updated_count
    
    def verify_configuration(self) -> Dict:
        """验证配置是否正确应用"""
        verification_results = {}
        
        self.log("开始验证配置...", "INFO")
        
        for agent_type, config in AGENT_CONFIGS.items():
            agent_results = {
                'ssm_params': False,
                'lambda_functions': [],
                'alias_exists': False
            }
            
            # 验证SSM参数
            try:
                param_prefix = f"/{PROJECT}/{ENVIRONMENT}/agents/{agent_type}"
                params = self.ssm.get_parameters(
                    Names=[
                        f"{param_prefix}/id",
                        f"{param_prefix}/alias_name",
                        f"{param_prefix}/alias_id"
                    ]
                )
                agent_results['ssm_params'] = len(params['Parameters']) == 3
            except:
                pass
            
            # 验证Lambda函数
            for func_name in config['functions']:
                try:
                    response = self.lambda_client.get_function_configuration(
                        FunctionName=func_name
                    )
                    env_vars = response.get('Environment', {}).get('Variables', {})
                    
                    has_config = (
                        'CONFIG_SOURCE' in env_vars and
                        f'{agent_type.upper()}_AGENT_ALIAS_ID' in env_vars
                    )
                    
                    agent_results['lambda_functions'].append({
                        'name': func_name,
                        'configured': has_config
                    })
                except:
                    agent_results['lambda_functions'].append({
                        'name': func_name,
                        'configured': False
                    })
            
            # 验证别名
            try:
                response = self.bedrock.list_agent_aliases(agentId=config['agent_id'])
                aliases = [a.get('agentAliasName', '') for a in response.get('agentAliasSummaries', [])]
                agent_results['alias_exists'] = config['alias_name'] in aliases
            except:
                pass
            
            verification_results[agent_type] = agent_results
        
        return verification_results
    
    def run(self) -> bool:
        """执行主要修复流程"""
        self.log("=" * 60, "INFO")
        self.log("开始修复Bedrock Agent配置", "INFO")
        self.log("=" * 60, "INFO")
        
        success_count = 0
        total_count = len(AGENT_CONFIGS)
        
        for agent_type, config in AGENT_CONFIGS.items():
            self.log(f"\n处理 {agent_type} Agent...", "INFO")
            
            # 创建或更新别名
            alias_id = self.create_or_update_agent_alias(
                config['agent_id'],
                config['alias_name']
            )
            
            if not alias_id:
                self.log(f"跳过 {agent_type} Agent（别名创建失败）", "WARNING")
                continue
            
            # 更新配置
            config['alias_id'] = alias_id
            
            # 存储到SSM
            if not self.store_config_in_ssm(agent_type, config):
                continue
            
            # 更新Lambda函数
            updated = self.update_lambda_functions(agent_type, config, alias_id)
            self.log(f"更新了 {updated}/{len(config['functions'])} 个Lambda函数", "INFO")
            
            success_count += 1
        
        # 验证配置
        self.log("\n" + "=" * 60, "INFO")
        self.log("验证配置", "INFO")
        self.log("=" * 60, "INFO")
        
        verification = self.verify_configuration()
        
        for agent_type, results in verification.items():
            self.log(f"\n{agent_type} Agent:", "INFO")
            self.log(f"  SSM参数: {'✅' if results['ssm_params'] else '❌'}", "INFO")
            self.log(f"  别名存在: {'✅' if results['alias_exists'] else '❌'}", "INFO")
            
            for func in results['lambda_functions']:
                status = '✅' if func['configured'] else '❌'
                self.log(f"  Lambda {func['name']}: {status}", "INFO")
        
        # 生成报告
        self.generate_report()
        
        # 返回成功状态
        return success_count == total_count
    
    def generate_report(self):
        """生成修复报告"""
        report = {
            'execution_time': datetime.now().isoformat(),
            'region': REGION,
            'project': PROJECT,
            'environment': ENVIRONMENT,
            'agent_configs': AGENT_CONFIGS,
            'results': self.results
        }
        
        # 保存报告
        report_file = f'agent_config_fix_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.log(f"\n报告已保存到: {report_file}", "SUCCESS")
        
        # 打印摘要
        error_count = sum(1 for r in self.results if r['level'] == 'ERROR')
        warning_count = sum(1 for r in self.results if r['level'] == 'WARNING')
        success_count = sum(1 for r in self.results if r['level'] == 'SUCCESS')
        
        print("\n" + "=" * 60)
        print("📊 修复摘要")
        print("=" * 60)
        print(f"✅ 成功: {success_count}")
        print(f"⚠️  警告: {warning_count}")
        print(f"❌ 错误: {error_count}")
        print("=" * 60)

def main():
    """主函数"""
    try:
        fixer = AgentConfigFixer()
        success = fixer.run()
        
        if success:
            print("\n🎉 Agent配置修复成功完成！")
            print("\n下一步:")
            print("1. 运行: bash unify_api_gateway.sh")
            print("2. 运行: python3 migrate_dynamodb_data.py")
            return 0
        else:
            print("\n⚠️ Agent配置修复部分完成，请检查错误日志")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 修复被用户中断")
        return 2
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {str(e)}")
        return 3

if __name__ == "__main__":
    sys.exit(main())