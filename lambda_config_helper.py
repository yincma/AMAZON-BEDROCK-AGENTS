import boto3
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
