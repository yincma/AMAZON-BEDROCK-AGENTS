#!/usr/bin/env python3
"""
更新Lambda函数环境变量以支持图片生成服务
"""

import boto3
import json
import sys
from typing import Dict, Any

def get_lambda_functions(project_name: str = "ai-ppt-assistant") -> list:
    """获取项目相关的Lambda函数"""
    lambda_client = boto3.client('lambda')

    try:
        response = lambda_client.list_functions()
        functions = response.get('Functions', [])

        # 过滤项目相关函数
        project_functions = [
            f for f in functions
            if project_name in f['FunctionName'].lower()
        ]

        return project_functions
    except Exception as e:
        print(f"Error listing functions: {e}")
        return []

def update_lambda_environment(function_name: str, env_vars: Dict[str, str]) -> bool:
    """更新Lambda函数环境变量"""
    lambda_client = boto3.client('lambda')

    try:
        # 获取当前配置
        response = lambda_client.get_function_configuration(
            FunctionName=function_name
        )

        current_env = response.get('Environment', {}).get('Variables', {})

        # 合并新的环境变量
        updated_env = {**current_env, **env_vars}

        # 更新函数配置
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={
                'Variables': updated_env
            }
        )

        print(f"✅ Updated environment for {function_name}")
        return True

    except Exception as e:
        print(f"❌ Error updating {function_name}: {e}")
        return False

def main():
    """主函数"""

    # 获取AWS账号信息
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = boto3.Session().region_name

    # 图片生成服务需要的环境变量
    image_env_vars = {
        # Bedrock模型配置
        'NOVA_MODEL_ID': 'amazon.nova-canvas-v1:0',
        'STABILITY_MODEL_ID': 'stability.stable-diffusion-xl-v1',
        'TITAN_MODEL_ID': 'amazon.titan-image-generator-v2:0',

        # 缓存配置
        'IMAGE_CACHE_TABLE': 'ai-ppt-assistant-image-cache',
        'IMAGE_CACHE_BUCKET': f'ai-ppt-assistant-image-cache-dev-{account_id}',
        'CACHE_TTL_HOURS': '168',  # 7天

        # 图片配置
        'DEFAULT_IMAGE_WIDTH': '1024',
        'DEFAULT_IMAGE_HEIGHT': '768',
        'IMAGE_QUALITY': 'premium',

        # 性能配置
        'MAX_RETRY_ATTEMPTS': '3',
        'RETRY_DELAY_SECONDS': '2',
        'BATCH_TIMEOUT_SECONDS': '60',

        # 功能开关
        'ENABLE_IMAGE_CACHE': 'true',
        'ENABLE_FALLBACK': 'true',
        'ENABLE_PARALLEL_GENERATION': 'true',

        # 监控配置
        'ENABLE_XRAY': 'true',
        'LOG_LEVEL': 'INFO'
    }

    print(f"🚀 Updating Lambda functions in account {account_id}, region {region}")
    print(f"📦 Environment variables to add/update:")
    for key, value in image_env_vars.items():
        print(f"   {key}: {value}")

    # 获取需要更新的Lambda函数
    functions = get_lambda_functions()

    if not functions:
        print("⚠️ No Lambda functions found")
        return

    print(f"\n📋 Found {len(functions)} Lambda functions")

    # 特定函数需要更新
    target_functions = [
        'generate_ppt',
        'compile_ppt',
        'image_generator',
        'api_handler'
    ]

    success_count = 0
    for func in functions:
        func_name = func['FunctionName']

        # 检查是否需要更新
        should_update = any(
            target in func_name.lower()
            for target in target_functions
        )

        if should_update:
            print(f"\n🔧 Updating: {func_name}")
            if update_lambda_environment(func_name, image_env_vars):
                success_count += 1
        else:
            print(f"⏭️ Skipping: {func_name}")

    print(f"\n✨ Updated {success_count} Lambda functions successfully")

    # 输出验证命令
    print("\n📝 To verify the updates, run:")
    print(f"aws lambda get-function-configuration --function-name ai-ppt-assistant-generate-ppt --query 'Environment.Variables' --output json")

if __name__ == "__main__":
    main()