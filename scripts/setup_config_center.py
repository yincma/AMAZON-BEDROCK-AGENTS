#!/usr/bin/env python3
"""
setup_config_center.py - 配置中心化设置脚本
建立SSM Parameter Store作为单一真相源
"""

import boto3
import json
import sys
from datetime import datetime
from typing import Dict, Any, List

# 配置
REGION = 'us-east-1'
PROJECT = 'ai-ppt-assistant'
ENVIRONMENT = 'dev'

class ConfigCenterSetup:
    def __init__(self):
        """初始化AWS客户端"""
        self.ssm = boto3.client('ssm', region_name=REGION)
        self.lambda_client = boto3.client('lambda', region_name=REGION)
        self.apigateway = boto3.client('apigateway', region_name=REGION)
        self.dynamodb = boto3.client('dynamodb', region_name=REGION)
        self.s3 = boto3.client('s3', region_name=REGION)
        self.sts = boto3.client('sts', region_name=REGION)
        
        # 获取账户信息
        self.account_id = self.sts.get_caller_identity()['Account']
        self.parameter_prefix = f"/{PROJECT}/{ENVIRONMENT}"
        
        self.created_params = []
        self.updated_params = []
        self.failed_params = []
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CONFIG": "🔧"
        }.get(level, "")
        
        print(f"{prefix} [{timestamp}] {message}")
    
    def discover_resources(self) -> Dict[str, Any]:
        """自动发现AWS资源"""
        self.log("自动发现AWS资源...", "INFO")
        
        resources = {
            'api_gateway': {},
            'dynamodb_tables': [],
            's3_buckets': [],
            'lambda_functions': []
        }
        
        # 发现API Gateway
        try:
            apis = self.apigateway.get_rest_apis()
            for api in apis['items']:
                if PROJECT in api['name']:
                    resources['api_gateway'] = {
                        'id': api['id'],
                        'name': api['name'],
                        'created_date': str(api.get('createdDate', ''))
                    }
                    self.log(f"发现API Gateway: {api['name']}", "CONFIG")
                    break
        except Exception as e:
            self.log(f"发现API Gateway失败: {str(e)}", "WARNING")
        
        # 发现DynamoDB表
        try:
            tables = self.dynamodb.list_tables()
            for table_name in tables['TableNames']:
                if PROJECT in table_name:
                    resources['dynamodb_tables'].append(table_name)
                    self.log(f"发现DynamoDB表: {table_name}", "CONFIG")
        except Exception as e:
            self.log(f"发现DynamoDB表失败: {str(e)}", "WARNING")
        
        # 发现S3桶
        try:
            buckets = self.s3.list_buckets()
            for bucket in buckets['Buckets']:
                if PROJECT in bucket['Name']:
                    resources['s3_buckets'].append(bucket['Name'])
                    self.log(f"发现S3桶: {bucket['Name']}", "CONFIG")
        except Exception as e:
            self.log(f"发现S3桶失败: {str(e)}", "WARNING")
        
        # 发现Lambda函数
        try:
            functions = self.lambda_client.list_functions()
            for func in functions['Functions']:
                if PROJECT in func['FunctionName']:
                    resources['lambda_functions'].append(func['FunctionName'])
            self.log(f"发现 {len(resources['lambda_functions'])} 个Lambda函数", "CONFIG")
        except Exception as e:
            self.log(f"发现Lambda函数失败: {str(e)}", "WARNING")
        
        return resources
    
    def create_or_update_parameter(self, name: str, value: str, 
                                  param_type: str = "String", 
                                  description: str = "", 
                                  secure: bool = False) -> bool:
        """创建或更新SSM参数"""
        try:
            # 检查参数是否存在
            try:
                existing = self.ssm.get_parameter(Name=name)
                action = "update"
            except self.ssm.exceptions.ParameterNotFound:
                action = "create"
            
            # 创建或更新参数
            if action == "update":
                # 更新现有参数（不能使用Tags）
                self.ssm.put_parameter(
                    Name=name,
                    Value=value,
                    Type="SecureString" if secure else param_type,
                    Overwrite=True,
                    Description=description or f"Configuration for {PROJECT}"
                )
            else:
                # 创建新参数（可以使用Tags）
                self.ssm.put_parameter(
                    Name=name,
                    Value=value,
                    Type="SecureString" if secure else param_type,
                    Description=description or f"Configuration for {PROJECT}",
                    Tags=[
                        {'Key': 'Project', 'Value': PROJECT},
                        {'Key': 'Environment', 'Value': ENVIRONMENT},
                        {'Key': 'ManagedBy', 'Value': 'setup_config_center.py'}
                    ]
                )
            
            if action == "create":
                self.created_params.append(name)
                self.log(f"创建参数: {name}", "SUCCESS")
            else:
                self.updated_params.append(name)
                self.log(f"更新参数: {name}", "SUCCESS")
            
            return True
            
        except Exception as e:
            self.log(f"处理参数 {name} 失败: {str(e)}", "ERROR")
            self.failed_params.append(name)
            return False
    
    def setup_core_parameters(self, resources: Dict[str, Any]):
        """设置核心配置参数"""
        self.log("\n设置核心配置参数...", "INFO")
        
        # API Gateway配置
        if resources['api_gateway']:
            api_id = resources['api_gateway']['id']
            api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/{ENVIRONMENT}"
            
            self.create_or_update_parameter(
                f"{self.parameter_prefix}/api-gateway-id",
                api_id,
                description="API Gateway ID"
            )
            
            self.create_or_update_parameter(
                f"{self.parameter_prefix}/api-gateway-url",
                api_url,
                description="API Gateway base URL"
            )
            
            self.create_or_update_parameter(
                f"{self.parameter_prefix}/api-stage",
                ENVIRONMENT,
                description="API Gateway stage name"
            )
        
        # DynamoDB配置
        primary_table = f"{PROJECT}-{ENVIRONMENT}-sessions"
        self.create_or_update_parameter(
            f"{self.parameter_prefix}/dynamodb-table",
            primary_table,
            description="Primary DynamoDB table"
        )
        
        self.create_or_update_parameter(
            f"{self.parameter_prefix}/dynamodb-region",
            REGION,
            description="DynamoDB region"
        )
        
        # S3配置
        if resources['s3_buckets']:
            primary_bucket = resources['s3_buckets'][0]
            self.create_or_update_parameter(
                f"{self.parameter_prefix}/s3-bucket",
                primary_bucket,
                description="Primary S3 bucket for storage"
            )
        
        # 环境配置
        self.create_or_update_parameter(
            f"{self.parameter_prefix}/environment",
            ENVIRONMENT,
            description="Environment name"
        )
        
        self.create_or_update_parameter(
            f"{self.parameter_prefix}/region",
            REGION,
            description="AWS region"
        )
        
        self.create_or_update_parameter(
            f"{self.parameter_prefix}/account-id",
            self.account_id,
            description="AWS account ID"
        )
        
        # 应用配置
        self.create_or_update_parameter(
            f"{self.parameter_prefix}/log-level",
            "INFO",
            description="Application log level"
        )
        
        self.create_or_update_parameter(
            f"{self.parameter_prefix}/version",
            "2.0.0",
            description="Application version"
        )
        
        self.create_or_update_parameter(
            f"{self.parameter_prefix}/deployment-date",
            datetime.now().isoformat(),
            description="Last deployment date"
        )
    
    def setup_agent_parameters(self):
        """设置Bedrock Agent参数"""
        self.log("\n设置Bedrock Agent参数...", "INFO")
        
        # Agent配置（基于实际的Agent ID）
        agents = {
            'orchestrator': {
                'id': 'Q6RODNGFYR',
                'alias': 'dev',
                'description': 'Orchestrator Agent'
            },
            'content': {
                'id': 'L0ZQHJSU4X',
                'alias': 'dev',
                'description': 'Content Generation Agent'
            },
            'visual': {
                'id': 'FO53FNXIRL',
                'alias': 'dev',
                'description': 'Visual Content Agent'
            },
            'compiler': {
                'id': 'B02XIGCUKI',
                'alias': 'dev',
                'description': 'PPT Compiler Agent'
            }
        }
        
        for agent_type, config in agents.items():
            prefix = f"{self.parameter_prefix}/agents/{agent_type}"
            
            self.create_or_update_parameter(
                f"{prefix}/id",
                config['id'],
                description=f"{config['description']} ID"
            )
            
            self.create_or_update_parameter(
                f"{prefix}/alias",
                config['alias'],
                description=f"{config['description']} alias name"
            )
            
            self.create_or_update_parameter(
                f"{prefix}/description",
                config['description'],
                description=f"Description for {agent_type} agent"
            )
    
    def setup_service_limits(self):
        """设置服务限制参数"""
        self.log("\n设置服务限制参数...", "INFO")
        
        limits = {
            'lambda-concurrent-executions': '100',
            'api-rate-limit': '100',
            'api-burst-limit': '200',
            's3-retention-days': '30',
            'dynamodb-read-capacity': '5',
            'dynamodb-write-capacity': '5'
        }
        
        for limit_name, limit_value in limits.items():
            self.create_or_update_parameter(
                f"{self.parameter_prefix}/limits/{limit_name}",
                limit_value,
                description=f"Service limit for {limit_name}"
            )
    
    def create_lambda_helper(self):
        """创建Lambda辅助函数用于读取配置"""
        self.log("\n创建Lambda配置辅助函数...", "INFO")
        
        helper_code = '''import boto3
import os
from functools import lru_cache
from typing import Dict, Any

# 初始化SSM客户端
ssm = boto3.client('ssm', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# 配置前缀
PARAMETER_PREFIX = os.environ.get('SSM_PREFIX', '/ai-ppt-assistant/dev')

@lru_cache(maxsize=128)
def get_parameter(name: str, decrypt: bool = False) -> str:
    """从SSM Parameter Store获取单个参数"""
    try:
        # 如果name不以/开头，添加前缀
        if not name.startswith('/'):
            name = f"{PARAMETER_PREFIX}/{name}"
        
        response = ssm.get_parameter(
            Name=name,
            WithDecryption=decrypt
        )
        return response['Parameter']['Value']
        
    except ssm.exceptions.ParameterNotFound:
        # 降级到环境变量
        env_key = name.split('/')[-1].upper().replace('-', '_')
        return os.environ.get(env_key, '')
    except Exception as e:
        print(f"Error getting parameter {name}: {str(e)}")
        return ''

def get_parameters_by_path(path: str) -> Dict[str, str]:
    """获取路径下的所有参数"""
    parameters = {}
    
    try:
        # 确保路径格式正确
        if not path.startswith('/'):
            path = f"{PARAMETER_PREFIX}/{path}"
        
        paginator = ssm.get_paginator('get_parameters_by_path')
        
        for page in paginator.paginate(
            Path=path,
            Recursive=True,
            WithDecryption=True
        ):
            for param in page['Parameters']:
                # 提取参数名（去掉路径前缀）
                key = param['Name'].replace(path + '/', '')
                parameters[key] = param['Value']
        
    except Exception as e:
        print(f"Error getting parameters by path {path}: {str(e)}")
    
    return parameters

def get_config() -> Dict[str, Any]:
    """获取完整配置"""
    config = {
        # 基础配置
        'api_gateway_url': get_parameter('api-gateway-url'),
        'api_key': get_parameter('api-key', decrypt=True),
        'dynamodb_table': get_parameter('dynamodb-table'),
        's3_bucket': get_parameter('s3-bucket'),
        'environment': get_parameter('environment'),
        'region': get_parameter('region'),
        
        # Agent配置
        'agents': get_parameters_by_path(f'{PARAMETER_PREFIX}/agents'),
        
        # 限制配置
        'limits': get_parameters_by_path(f'{PARAMETER_PREFIX}/limits')
    }
    
    return config

# 导出配置（在Lambda函数启动时加载）
CONFIG = get_config()

# 使用示例
if __name__ == "__main__":
    print("Configuration loaded:")
    print(json.dumps(CONFIG, indent=2))
'''
        
        # 保存辅助代码
        with open('lambda_config_helper.py', 'w') as f:
            f.write(helper_code)
        
        self.log("Lambda配置辅助函数已创建: lambda_config_helper.py", "SUCCESS")
    
    def update_lambda_functions(self, resources: Dict[str, Any]):
        """更新Lambda函数以使用SSM参数"""
        self.log("\n更新Lambda函数配置...", "INFO")
        
        updated_count = 0
        
        for func_name in resources['lambda_functions']:
            try:
                # 获取当前配置
                response = self.lambda_client.get_function_configuration(
                    FunctionName=func_name
                )
                
                env_vars = response.get('Environment', {}).get('Variables', {})
                
                # 添加SSM配置
                env_vars.update({
                    'SSM_PREFIX': self.parameter_prefix,
                    'CONFIG_SOURCE': 'SSM_PARAMETER_STORE',
                    'PARAMETER_CACHE_TTL': '300'  # 5分钟缓存
                })
                
                # 更新函数配置
                self.lambda_client.update_function_configuration(
                    FunctionName=func_name,
                    Environment={'Variables': env_vars}
                )
                
                self.log(f"更新Lambda函数: {func_name}", "SUCCESS")
                updated_count += 1
                
            except Exception as e:
                self.log(f"更新Lambda函数 {func_name} 失败: {str(e)}", "ERROR")
        
        return updated_count
    
    def generate_report(self):
        """生成配置报告"""
        report = {
            'setup_time': datetime.now().isoformat(),
            'region': REGION,
            'project': PROJECT,
            'environment': ENVIRONMENT,
            'parameter_prefix': self.parameter_prefix,
            'statistics': {
                'created': len(self.created_params),
                'updated': len(self.updated_params),
                'failed': len(self.failed_params)
            },
            'parameters': {
                'created': self.created_params,
                'updated': self.updated_params,
                'failed': self.failed_params
            }
        }
        
        # 保存报告
        report_file = f'config_center_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"\n报告已保存到: {report_file}", "SUCCESS")
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("📊 配置中心设置摘要")
        print("=" * 60)
        print(f"✅ 创建参数: {len(self.created_params)}")
        print(f"🔄 更新参数: {len(self.updated_params)}")
        print(f"❌ 失败: {len(self.failed_params)}")
        print(f"\n参数前缀: {self.parameter_prefix}")
        print("=" * 60)
    
    def validate_setup(self) -> bool:
        """验证配置中心设置"""
        self.log("\n验证配置中心...", "INFO")
        
        critical_params = [
            f"{self.parameter_prefix}/api-gateway-url",
            f"{self.parameter_prefix}/dynamodb-table",
            f"{self.parameter_prefix}/environment"
        ]
        
        all_valid = True
        
        for param in critical_params:
            try:
                self.ssm.get_parameter(Name=param)
                self.log(f"✅ 参数存在: {param}", "SUCCESS")
            except:
                self.log(f"❌ 参数缺失: {param}", "ERROR")
                all_valid = False
        
        return all_valid
    
    def run(self) -> bool:
        """执行配置中心设置"""
        self.log("=" * 60, "INFO")
        self.log("开始设置配置中心", "INFO")
        self.log("=" * 60, "INFO")
        
        try:
            # 步骤1: 发现资源
            resources = self.discover_resources()
            
            # 步骤2: 设置核心参数
            self.setup_core_parameters(resources)
            
            # 步骤3: 设置Agent参数
            self.setup_agent_parameters()
            
            # 步骤4: 设置服务限制
            self.setup_service_limits()
            
            # 步骤5: 创建Lambda辅助函数
            self.create_lambda_helper()
            
            # 步骤6: 更新Lambda函数
            lambda_updated = self.update_lambda_functions(resources)
            self.log(f"更新了 {lambda_updated} 个Lambda函数", "INFO")
            
            # 步骤7: 验证设置
            is_valid = self.validate_setup()
            
            # 步骤8: 生成报告
            self.generate_report()
            
            return is_valid
            
        except Exception as e:
            self.log(f"设置过程出现异常: {str(e)}", "ERROR")
            return False

def main():
    """主函数"""
    print("🔧 SSM Parameter Store 配置中心设置")
    print("=" * 60)
    print(f"项目: {PROJECT}")
    print(f"环境: {ENVIRONMENT}")
    print(f"区域: {REGION}")
    print("=" * 60)
    
    setup = ConfigCenterSetup()
    
    if setup.run():
        print("\n🎉 配置中心设置成功！")
        print("\n使用方法:")
        print("1. 在Lambda函数中导入: from lambda_config_helper import CONFIG")
        print("2. 使用配置: table_name = CONFIG['dynamodb_table']")
        print("\n下一步:")
        print("1. 运行: python3 test_all_backend_apis.py")
        print("2. 验证所有服务正常工作")
        return 0
    else:
        print("\n❌ 配置中心设置失败，请检查错误")
        return 1

if __name__ == "__main__":
    sys.exit(main())