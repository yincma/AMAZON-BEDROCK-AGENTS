#!/usr/bin/env python3
"""快速验证P0级问题是否修复"""

import boto3
import requests
import json
import sys
from datetime import datetime

def validate_lambda_env():
    """验证Lambda环境变量配置"""
    print("\n📋 验证Lambda环境变量配置...")
    print("-" * 60)
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    functions_to_check = {
        'ai-ppt-assistant-api-generate-presentation': ['ORCHESTRATOR_AGENT_ID', 'DYNAMODB_TABLE'],
        'ai-ppt-assistant-generate-content': ['CONTENT_AGENT_ID', 'DYNAMODB_TABLE'],
        'ai-ppt-assistant-generate-image': ['VISUAL_AGENT_ID', 'DYNAMODB_TABLE'],
        'ai-ppt-assistant-compile-pptx': ['COMPILER_AGENT_ID', 'DYNAMODB_TABLE'],
        'ai-ppt-assistant-api-presentation-status': ['DYNAMODB_TABLE']
    }
    
    all_valid = True
    for func_name, required_vars in functions_to_check.items():
        try:
            response = lambda_client.get_function_configuration(FunctionName=func_name)
            env_vars = response.get('Environment', {}).get('Variables', {})
            
            issues = []
            for var in required_vars:
                if var not in env_vars:
                    issues.append(f"{var} 缺失")
                elif 'placeholder' in str(env_vars.get(var, '')).lower():
                    issues.append(f"{var} 仍是占位符")
                elif var == 'DYNAMODB_TABLE' and env_vars.get(var) != 'ai-ppt-assistant-dev-sessions':
                    issues.append(f"DYNAMODB_TABLE 不正确: {env_vars.get(var)}")
            
            if issues:
                print(f"❌ {func_name}: {', '.join(issues)}")
                all_valid = False
            else:
                print(f"✅ {func_name}: 配置正确")
                
        except Exception as e:
            print(f"❌ {func_name}: 检查失败 - {str(e)}")
            all_valid = False
    
    return all_valid

def validate_api_gateway():
    """验证API Gateway配置"""
    print("\n🌐 验证API Gateway配置...")
    print("-" * 60)
    
    api_url = "https://otmr3noxg5.execute-api.us-east-1.amazonaws.com/dev"
    api_key = "9EQHqfmiuA5GrkMnK5PVf8OpbIcsMj1N2z6PFGR3"
    
    headers = {'x-api-key': api_key}
    
    # 测试health端点
    try:
        response = requests.get(f"{api_url}/health", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"✅ Health端点: 状态码 {response.status_code}")
            return True
        else:
            print(f"❌ Health端点: 状态码 {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API Gateway测试失败: {str(e)}")
        return False

def validate_dynamodb():
    """验证DynamoDB表存在"""
    print("\n💾 验证DynamoDB表配置...")
    print("-" * 60)
    
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    
    required_tables = [
        'ai-ppt-assistant-dev-sessions',
        'ai-ppt-assistant-dev-tasks',
        'ai-ppt-assistant-dev-checkpoints'
    ]
    
    all_valid = True
    for table_name in required_tables:
        try:
            response = dynamodb.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            if status == 'ACTIVE':
                print(f"✅ {table_name}: 状态 {status}")
            else:
                print(f"⚠️ {table_name}: 状态 {status}")
                all_valid = False
        except Exception as e:
            print(f"❌ {table_name}: 不存在或无法访问 - {str(e)}")
            all_valid = False
    
    return all_valid

def validate_json_config():
    """验证JSON配置文件"""
    print("\n📄 验证JSON配置文件...")
    print("-" * 60)
    
    try:
        with open('api_config_info.json', 'r') as f:
            config = json.load(f)
        
        required_fields = ['api_gateway_url', 'api_key', 'region', 'environment']
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            print(f"❌ 缺少必要字段: {', '.join(missing_fields)}")
            return False
        
        # 验证值是否正确
        issues = []
        if config.get('api_gateway_url') != 'https://otmr3noxg5.execute-api.us-east-1.amazonaws.com/dev':
            issues.append(f"API URL不正确: {config.get('api_gateway_url')}")
        if config.get('api_key') != '9EQHqfmiuA5GrkMnK5PVf8OpbIcsMj1N2z6PFGR3':
            issues.append(f"API Key不匹配")
        
        if issues:
            print(f"❌ 配置问题: {', '.join(issues)}")
            return False
        else:
            print(f"✅ JSON配置文件格式正确且值匹配")
            return True
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON格式错误: {str(e)}")
        return False
    except FileNotFoundError:
        print(f"❌ 配置文件不存在")
        return False
    except Exception as e:
        print(f"❌ 读取配置失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 P0级问题修复验证")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = {
        "Lambda环境变量": validate_lambda_env(),
        "API Gateway": validate_api_gateway(),
        "DynamoDB表": validate_dynamodb(),
        "JSON配置": validate_json_config()
    }
    
    print("\n" + "=" * 60)
    print("📊 验证结果汇总")
    print("=" * 60)
    
    for component, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component}: {'通过' if status else '失败'}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有P0级问题已成功修复！")
        print("系统核心功能已恢复正常。")
        return 0
    else:
        print("⚠️ 仍有问题需要修复")
        print("请检查上述失败的组件。")
        return 1

if __name__ == "__main__":
    sys.exit(main())