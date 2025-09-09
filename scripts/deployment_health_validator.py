#!/usr/bin/env python3
"""
AI PPT Assistant - 部署健康验证脚本
==================================

自动化验证脚本，防止未来部署时出现类似问题：
1. Lambda权限验证
2. Bedrock Agent ID配置验证  
3. Lambda依赖打包验证
4. 系统健康检查

使用方法：
python scripts/deployment_health_validator.py [--fix]

作者：AWS Expert & Claude Code
日期：2025-09-09
"""

import json
import os
import subprocess
import sys
import zipfile
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import boto3
from botocore.exceptions import ClientError


class DeploymentHealthValidator:
    """部署健康验证器"""
    
    def __init__(self, region: str = "us-east-1", project_name: str = "ai-ppt-assistant"):
        self.region = region
        self.project_name = project_name
        self.dev_env = f"{project_name}-dev"
        
        # AWS客户端
        self.iam = boto3.client('iam', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=region)
        
        self.issues = []
        self.fixes_applied = []
        
    def log_info(self, message: str):
        """记录信息"""
        print(f"[INFO] {message}")
        
    def log_warning(self, message: str):
        """记录警告"""
        print(f"[WARNING] {message}")
        
    def log_error(self, message: str):
        """记录错误"""
        print(f"[ERROR] {message}")
        self.issues.append(message)
        
    def log_success(self, message: str):
        """记录成功"""
        print(f"[SUCCESS] {message}")

    def validate_lambda_permissions(self) -> bool:
        """验证Lambda函数权限配置"""
        self.log_info("验证Lambda函数权限配置...")
        
        try:
            role_name = f"{self.project_name}-lambda-execution-role"
            
            # 获取IAM角色
            role = self.iam.get_role(RoleName=role_name)
            role_arn = role['Role']['Arn']
            
            # 检查附加的策略
            policies = self.iam.list_attached_role_policies(RoleName=role_name)
            attached_policies = [p['PolicyName'] for p in policies['AttachedPolicies']]
            
            required_policies = [
                f"{self.project_name}-lambda-policy",
                "AWSLambdaBasicExecutionRole"
            ]
            
            missing_policies = [p for p in required_policies if p not in attached_policies]
            
            if missing_policies:
                self.log_error(f"Lambda角色缺少策略: {missing_policies}")
                return False
            
            # 检查自定义策略内容
            custom_policy_arn = f"arn:aws:iam::{self._get_account_id()}:policy/{self.project_name}-lambda-policy"
            policy_version = self.iam.get_policy_version(
                PolicyArn=custom_policy_arn,
                VersionId=self.iam.get_policy(PolicyArn=custom_policy_arn)['Policy']['DefaultVersionId']
            )
            
            policy_doc = policy_version['PolicyVersion']['Document']
            
            # 检查关键权限
            required_actions = {
                'bedrock:InvokeAgent',
                'bedrock:InvokeModel', 
                'dynamodb:PutItem',
                'dynamodb:GetItem',
                'dynamodb:Query',
                'dynamodb:UpdateItem'
            }
            
            granted_actions = set()
            for statement in policy_doc['Statement']:
                if statement.get('Effect') == 'Allow':
                    actions = statement.get('Action', [])
                    if isinstance(actions, str):
                        actions = [actions]
                    granted_actions.update(actions)
            
            missing_actions = required_actions - granted_actions
            if missing_actions:
                self.log_error(f"Lambda策略缺少权限: {missing_actions}")
                return False
                
            self.log_success("Lambda权限配置验证通过")
            return True
            
        except Exception as e:
            self.log_error(f"Lambda权限验证失败: {str(e)}")
            return False

    def validate_bedrock_agent_configuration(self) -> bool:
        """验证Bedrock Agent配置"""
        self.log_info("验证Bedrock Agent配置...")
        
        try:
            # 获取实际部署的Agents
            agents_response = self.bedrock_agent.list_agents()
            deployed_agents = {
                agent['agentName']: {
                    'id': agent['agentId'],
                    'status': agent['agentStatus']
                }
                for agent in agents_response['agentSummaries']
                if agent['agentName'].startswith(self.project_name)
            }
            
            if not deployed_agents:
                self.log_error("没有找到已部署的Bedrock Agents")
                return False
            
            # 检查Agent状态
            for agent_name, agent_info in deployed_agents.items():
                if agent_info['status'] != 'PREPARED':
                    self.log_error(f"Agent {agent_name} 状态不正确: {agent_info['status']}")
                    return False
                
                # 获取Alias信息
                aliases = self.bedrock_agent.list_agent_aliases(agentId=agent_info['id'])
                if not aliases['agentAliasSummaries']:
                    self.log_error(f"Agent {agent_name} 没有Alias配置")
                    return False
            
            # 检查Lambda环境变量中的Agent ID配置
            agent_functions = [
                f"{self.project_name}-api-generate-presentation",
                f"{self.project_name}-api-modify-slide", 
                f"{self.project_name}-api-task-processor"
            ]
            
            for func_name in agent_functions:
                try:
                    func_config = self.lambda_client.get_function_configuration(FunctionName=func_name)
                    env_vars = func_config.get('Environment', {}).get('Variables', {})
                    
                    # 检查Orchestrator Agent ID
                    if 'ORCHESTRATOR_AGENT_ID' in env_vars:
                        orchestrator_id = env_vars['ORCHESTRATOR_AGENT_ID']
                        orchestrator_agent = next(
                            (a for name, a in deployed_agents.items() if 'orchestrator' in name.lower()),
                            None
                        )
                        if orchestrator_agent and orchestrator_id != orchestrator_agent['id']:
                            self.log_error(f"函数 {func_name} 的ORCHESTRATOR_AGENT_ID不匹配: {orchestrator_id} != {orchestrator_agent['id']}")
                            return False
                            
                except Exception as e:
                    self.log_warning(f"无法检查函数 {func_name}: {str(e)}")
            
            self.log_success("Bedrock Agent配置验证通过")
            return True
            
        except Exception as e:
            self.log_error(f"Bedrock Agent配置验证失败: {str(e)}")
            return False

    def validate_lambda_dependencies(self) -> bool:
        """验证Lambda依赖打包"""
        self.log_info("验证Lambda依赖打包...")
        
        lambda_dirs = ['api', 'controllers']
        success = True
        
        for lambda_dir in lambda_dirs:
            lambda_path = f"lambdas/{lambda_dir}"
            if not os.path.exists(lambda_path):
                continue
                
            # 检查zip文件
            for py_file in os.listdir(lambda_path):
                if py_file.endswith('.py'):
                    zip_file = py_file.replace('.py', '.zip')
                    zip_path = os.path.join(lambda_path, zip_file)
                    
                    if not os.path.exists(zip_path):
                        self.log_warning(f"缺少zip文件: {zip_path}")
                        continue
                    
                    # 检查zip文件内容
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zf:
                            file_list = zf.namelist()
                            
                            # 检查utils模块
                            utils_files = [f for f in file_list if f.startswith('utils/')]
                            if not utils_files:
                                self.log_error(f"Lambda包 {zip_file} 缺少utils模块")
                                success = False
                            
                            # 检查关键utils文件
                            required_utils = ['utils/api_utils.py', 'utils/__init__.py']
                            for required_file in required_utils:
                                if required_file not in file_list:
                                    self.log_error(f"Lambda包 {zip_file} 缺少 {required_file}")
                                    success = False
                                    
                    except Exception as e:
                        self.log_error(f"无法检查Lambda包 {zip_file}: {str(e)}")
                        success = False
        
        # 检查Lambda Layers
        layer_path = "lambdas/layers/dist"
        if os.path.exists(layer_path):
            for layer_file in os.listdir(layer_path):
                if layer_file.endswith('.zip'):
                    layer_zip = os.path.join(layer_path, layer_file)
                    try:
                        with zipfile.ZipFile(layer_zip, 'r') as zf:
                            file_list = zf.namelist()
                            
                            # 检查aws_lambda_powertools
                            powertools_files = [f for f in file_list if 'aws_lambda_powertools' in f]
                            if not powertools_files:
                                self.log_error(f"Layer {layer_file} 缺少aws_lambda_powertools")
                                success = False
                                
                    except Exception as e:
                        self.log_error(f"无法检查Layer {layer_file}: {str(e)}")
                        success = False
        
        if success:
            self.log_success("Lambda依赖打包验证通过")
        
        return success

    def validate_system_health(self) -> bool:
        """验证系统健康状态"""
        self.log_info("验证系统健康状态...")
        
        try:
            # 检查Lambda函数状态
            lambda_functions = [
                f"{self.project_name}-api-generate-presentation",
                f"{self.project_name}-api-presentation-status",
                f"{self.project_name}-api-presentation-download",
                f"{self.project_name}-api-modify-slide",
                f"{self.project_name}-api-task-processor"
            ]
            
            for func_name in lambda_functions:
                try:
                    func_config = self.lambda_client.get_function_configuration(FunctionName=func_name)
                    if func_config['State'] != 'Active':
                        self.log_error(f"Lambda函数 {func_name} 状态不正常: {func_config['State']}")
                        return False
                except Exception as e:
                    self.log_error(f"无法检查Lambda函数 {func_name}: {str(e)}")
                    return False
            
            self.log_success("系统健康状态验证通过")
            return True
            
        except Exception as e:
            self.log_error(f"系统健康验证失败: {str(e)}")
            return False

    def _get_account_id(self) -> str:
        """获取AWS账户ID"""
        try:
            return boto3.client('sts').get_caller_identity()['Account']
        except Exception:
            return "UNKNOWN"

    def generate_agent_id_update_script(self) -> str:
        """生成Agent ID更新脚本"""
        self.log_info("生成Agent ID同步脚本...")
        
        try:
            # 获取实际的Agent IDs和Alias IDs
            agents_response = self.bedrock_agent.list_agents()
            agent_mapping = {}
            
            for agent in agents_response['agentSummaries']:
                if agent['agentName'].startswith(self.project_name):
                    agent_type = agent['agentName'].replace(f"{self.project_name}-", "").replace("-agent", "")
                    
                    # 获取Alias
                    aliases = self.bedrock_agent.list_agent_aliases(agentId=agent['agentId'])
                    alias_id = aliases['agentAliasSummaries'][0]['agentAliasId'] if aliases['agentAliasSummaries'] else None
                    
                    agent_mapping[agent_type] = {
                        'agent_id': agent['agentId'],
                        'alias_id': alias_id
                    }
            
            # 生成更新脚本
            script_content = f"""#!/bin/bash
# Agent ID同步脚本 - 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 将实际部署的Agent IDs更新到Terraform配置

echo "开始同步Bedrock Agent IDs到Terraform配置..."

# 备份原始配置
cp infrastructure/main.tf infrastructure/main.tf.backup.$(date +%Y%m%d_%H%M%S)

# 更新Agent IDs
"""
            
            for agent_type, ids in agent_mapping.items():
                script_content += f"""
# 更新{agent_type} Agent配置
sed -i 's/{agent_type}_agent_id.*=.*/{agent_type}_agent_id = "{ids["agent_id"]}"  # {agent_type.title()} Agent ID/' infrastructure/main.tf
sed -i 's/{agent_type}_alias_id.*=.*/{agent_type}_alias_id = "{ids["alias_id"]}"  # {agent_type.title()} Alias ID/' infrastructure/main.tf
"""
            
            script_content += """
echo "Agent IDs已更新到Terraform配置"
echo "请运行 'terraform apply -target=module.lambda' 来应用更新"
"""
            
            script_path = "scripts/sync_agent_ids.sh"
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            os.chmod(script_path, 0o755)
            self.log_success(f"Agent ID同步脚本已生成: {script_path}")
            
            return script_path
            
        except Exception as e:
            self.log_error(f"生成Agent ID更新脚本失败: {str(e)}")
            return ""

    def run_validation(self, auto_fix: bool = False) -> bool:
        """运行完整验证"""
        self.log_info("开始部署健康验证...")
        self.log_info(f"项目: {self.project_name}")
        self.log_info(f"区域: {self.region}")
        self.log_info("=" * 50)
        
        all_passed = True
        
        # 1. Lambda权限验证
        if not self.validate_lambda_permissions():
            all_passed = False
            
        # 2. Bedrock Agent配置验证
        if not self.validate_bedrock_agent_configuration():
            all_passed = False
            if auto_fix:
                self.generate_agent_id_update_script()
                self.fixes_applied.append("生成了Agent ID同步脚本")
        
        # 3. Lambda依赖验证
        if not self.validate_lambda_dependencies():
            all_passed = False
            
        # 4. 系统健康检查
        if not self.validate_system_health():
            all_passed = False
        
        # 输出结果
        self.log_info("=" * 50)
        if all_passed:
            self.log_success("✅ 所有验证通过！部署状态健康。")
        else:
            self.log_error(f"❌ 发现 {len(self.issues)} 个问题需要修复")
            for issue in self.issues:
                print(f"  - {issue}")
                
        if self.fixes_applied:
            self.log_info("🔧 已应用的修复:")
            for fix in self.fixes_applied:
                print(f"  - {fix}")
        
        return all_passed


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI PPT Assistant 部署健康验证")
    parser.add_argument("--fix", action="store_true", help="自动应用可用的修复")
    parser.add_argument("--region", default="us-east-1", help="AWS区域")
    parser.add_argument("--project", default="ai-ppt-assistant", help="项目名称")
    
    args = parser.parse_args()
    
    validator = DeploymentHealthValidator(region=args.region, project_name=args.project)
    success = validator.run_validation(auto_fix=args.fix)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()