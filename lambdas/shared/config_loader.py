#!/usr/bin/env python3
"""
统一配置加载器
确保所有Lambda函数使用正确的配置，禁止占位符值
"""

import os
import json
import boto3
from typing import Dict, Any, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """配置验证错误"""
    pass

class ConfigLoader:
    """
    统一的配置加载器
    - 从SSM Parameter Store加载配置
    - 验证配置值，拒绝占位符
    - 提供缓存机制
    - 记录配置审计日志
    """
    
    FORBIDDEN_VALUES = [
        'placeholder',
        'PLACEHOLDER',
        'todo',
        'TODO',
        'xxx',
        'XXX',
        'tbd',
        'TBD'
    ]
    
    def __init__(self, ssm_prefix: str = None):
        """
        初始化配置加载器
        
        Args:
            ssm_prefix: SSM参数前缀，默认从环境变量读取
        """
        self.ssm_client = boto3.client('ssm')
        self.ssm_prefix = ssm_prefix or os.environ.get('SSM_PREFIX', '/ai-ppt-assistant/dev')
        self.cache_ttl = int(os.environ.get('PARAMETER_CACHE_TTL', '60'))
        self._config_cache = {}
        
        logger.info(f"ConfigLoader initialized with prefix: {self.ssm_prefix}")
        
    def _validate_value(self, key: str, value: str) -> None:
        """
        验证配置值，确保没有占位符
        
        Args:
            key: 配置键
            value: 配置值
            
        Raises:
            ConfigValidationError: 如果值包含禁止的占位符
        """
        if not value:
            raise ConfigValidationError(f"配置 '{key}' 值为空")
            
        value_lower = value.lower()
        for forbidden in self.FORBIDDEN_VALUES:
            if forbidden.lower() in value_lower:
                error_msg = f"配置 '{key}' 包含占位符值: '{value}'"
                logger.error(error_msg)
                
                # 发送CloudWatch自定义指标
                cloudwatch = boto3.client('cloudwatch')
                cloudwatch.put_metric_data(
                    Namespace='AI-PPT-Assistant',
                    MetricData=[
                        {
                            'MetricName': 'ConfigValidationError',
                            'Value': 1,
                            'Unit': 'Count',
                            'Dimensions': [
                                {'Name': 'ConfigKey', 'Value': key},
                                {'Name': 'Environment', 'Value': 'dev'}
                            ]
                        }
                    ]
                )
                
                raise ConfigValidationError(error_msg)
                
    @lru_cache(maxsize=128)
    def get_parameter(self, name: str, decrypt: bool = True) -> str:
        """
        从SSM获取单个参数
        
        Args:
            name: 参数名（相对于前缀）
            decrypt: 是否解密SecureString
            
        Returns:
            参数值
            
        Raises:
            ConfigValidationError: 如果参数无效
        """
        full_name = f"{self.ssm_prefix}/{name}" if not name.startswith('/') else name
        
        try:
            response = self.ssm_client.get_parameter(
                Name=full_name,
                WithDecryption=decrypt
            )
            value = response['Parameter']['Value']
            
            # 验证值
            self._validate_value(full_name, value)
            
            logger.info(f"成功加载配置: {full_name}")
            return value
            
        except self.ssm_client.exceptions.ParameterNotFound:
            error_msg = f"配置参数不存在: {full_name}"
            logger.error(error_msg)
            raise ConfigValidationError(error_msg)
        except Exception as e:
            error_msg = f"加载配置失败 {full_name}: {str(e)}"
            logger.error(error_msg)
            raise ConfigValidationError(error_msg)
            
    def get_parameters_by_path(self, path: str = '') -> Dict[str, str]:
        """
        获取路径下的所有参数
        
        Args:
            path: 相对路径
            
        Returns:
            参数字典
        """
        full_path = f"{self.ssm_prefix}/{path}" if path else self.ssm_prefix
        parameters = {}
        
        try:
            paginator = self.ssm_client.get_paginator('get_parameters_by_path')
            page_iterator = paginator.paginate(
                Path=full_path,
                Recursive=True,
                WithDecryption=True
            )
            
            for page in page_iterator:
                for param in page['Parameters']:
                    # 获取相对键名
                    key = param['Name'].replace(f"{self.ssm_prefix}/", '')
                    value = param['Value']
                    
                    # 验证值
                    self._validate_value(key, value)
                    
                    parameters[key] = value
                    
            logger.info(f"成功加载 {len(parameters)} 个配置参数")
            return parameters
            
        except Exception as e:
            error_msg = f"批量加载配置失败: {str(e)}"
            logger.error(error_msg)
            raise ConfigValidationError(error_msg)
            
    def get_bedrock_config(self) -> Dict[str, Any]:
        """
        获取Bedrock Agent配置
        
        Returns:
            Bedrock配置字典
        """
        config = {
            'orchestrator': {
                'id': self.get_parameter('agents/orchestrator/id'),
                'alias_id': self.get_parameter('agents/orchestrator/alias_id'),
                'alias_name': self.get_parameter('agents/orchestrator/alias_name', decrypt=False)
            },
            'compiler': {
                'id': self.get_parameter('agents/compiler/id'),
                'alias_id': self.get_parameter('agents/compiler/alias_id'),
                'alias_name': self.get_parameter('agents/compiler/alias_name', decrypt=False)
            },
            'content': {
                'id': self.get_parameter('agents/content/id'),
                'alias_id': self.get_parameter('agents/content/alias_id'),
                'alias_name': self.get_parameter('agents/content/alias_name', decrypt=False)
            }
        }
        
        logger.info("Bedrock配置加载成功")
        return config
        
    def get_database_config(self) -> Dict[str, str]:
        """
        获取数据库配置
        
        Returns:
            数据库配置字典
        """
        config = {
            'sessions_table': self.get_parameter('dynamodb/sessions-table'),
            'tasks_table': self.get_parameter('dynamodb/tasks-table'),
            'checkpoints_table': self.get_parameter('dynamodb/checkpoints-table')
        }
        
        logger.info("数据库配置加载成功")
        return config
        
    def get_api_config(self) -> Dict[str, str]:
        """
        获取API配置
        
        Returns:
            API配置字典
        """
        config = {
            'api_gateway_id': self.get_parameter('api-gateway-id'),
            'api_gateway_url': self.get_parameter('api-gateway-url'),
            'api_stage': self.get_parameter('api-stage'),
            'api_key': self.get_parameter('api-key', decrypt=True)
        }
        
        logger.info("API配置加载成功")
        return config
        
    def validate_all_configs(self) -> bool:
        """
        验证所有配置
        
        Returns:
            True如果所有配置有效
            
        Raises:
            ConfigValidationError: 如果任何配置无效
        """
        try:
            # 验证Bedrock配置
            bedrock_config = self.get_bedrock_config()
            logger.info(f"Bedrock配置验证通过")
            
            # 验证数据库配置
            db_config = self.get_database_config()
            logger.info(f"数据库配置验证通过")
            
            # 验证API配置
            api_config = self.get_api_config()
            logger.info(f"API配置验证通过")
            
            # 发送成功指标
            cloudwatch = boto3.client('cloudwatch')
            cloudwatch.put_metric_data(
                Namespace='AI-PPT-Assistant',
                MetricData=[
                    {
                        'MetricName': 'ConfigValidationSuccess',
                        'Value': 1,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Environment', 'Value': 'dev'}
                        ]
                    }
                ]
            )
            
            logger.info("所有配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {str(e)}")
            raise

# 全局配置实例
_config_loader = None

def get_config_loader() -> ConfigLoader:
    """
    获取全局配置加载器实例
    
    Returns:
        ConfigLoader实例
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader

def load_config() -> Dict[str, Any]:
    """
    加载并验证所有配置
    
    Returns:
        完整的配置字典
        
    Raises:
        ConfigValidationError: 如果配置无效
    """
    loader = get_config_loader()
    
    # 验证所有配置
    loader.validate_all_configs()
    
    # 返回完整配置
    return {
        'bedrock': loader.get_bedrock_config(),
        'database': loader.get_database_config(),
        'api': loader.get_api_config(),
        'ssm_prefix': loader.ssm_prefix
    }

# Lambda处理器装饰器
def with_validated_config(handler):
    """
    装饰器：确保Lambda处理器使用验证过的配置
    
    Usage:
        @with_validated_config
        def lambda_handler(event, context, config):
            # config参数包含验证过的配置
            pass
    """
    def wrapper(event, context):
        try:
            # 加载并验证配置
            config = load_config()
            
            # 调用原始处理器，传入配置
            return handler(event, context, config)
            
        except ConfigValidationError as e:
            logger.error(f"配置验证失败: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Configuration validation failed',
                    'message': str(e)
                })
            }
        except Exception as e:
            logger.error(f"处理器执行失败: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Internal server error',
                    'message': str(e)
                })
            }
            
    return wrapper