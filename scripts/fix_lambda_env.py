#!/usr/bin/env python3
"""
修复Lambda函数环境变量配置 - 修复Bedrock Agent ID和DynamoDB表配置
"""

import boto3
import json
import sys

# Lambda客户端
lambda_client = boto3.client('lambda', region_name='us-east-1')

# Bedrock Agent配置 - 根据问题修复计划更新
AGENT_CONFIG = {
    'ai-ppt-assistant-api-generate-presentation': {
        'ORCHESTRATOR_AGENT_ID': 'Q6RODNGFYR',
        'ORCHESTRATOR_ALIAS_ID': 'YR5LAKP6SF',
        'DYNAMODB_TABLE': 'ai-ppt-assistant-dev-sessions'
    },
    'ai-ppt-assistant-generate-content': {
        'CONTENT_AGENT_ID': 'L0ZQHJSU4X',
        'DYNAMODB_TABLE': 'ai-ppt-assistant-dev-sessions'
    },
    'ai-ppt-assistant-generate-image': {
        'VISUAL_AGENT_ID': 'FO53FNXIRL',
        'DYNAMODB_TABLE': 'ai-ppt-assistant-dev-sessions'
    },
    'ai-ppt-assistant-compile-pptx': {
        'COMPILER_AGENT_ID': 'B02XIGCUKI',
        'DYNAMODB_TABLE': 'ai-ppt-assistant-dev-sessions'
    },
    'ai-ppt-assistant-api-presentation-status': {
        'DYNAMODB_TABLE': 'ai-ppt-assistant-dev-sessions'
    }
}

def fix_lambda_environment(function_name, env_vars):
    """修复单个Lambda函数的环境变量"""
    try:
        # 获取当前配置
        response = lambda_client.get_function_configuration(
            FunctionName=function_name
        )
        
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # 更新环境变量
        current_env.update(env_vars)
        
        # 更新Lambda配置
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={
                'Variables': current_env
            }
        )
        
        print(f"✅ 成功更新 {function_name} 的环境变量")
        return True
        
    except Exception as e:
        print(f"❌ 更新 {function_name} 失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔧 开始修复Lambda函数环境变量")
    print("修复问题#001: Bedrock Agent ID配置错误")
    print("修复问题#002: DynamoDB表配置不一致")
    print("=" * 60)
    
    success_count = 0
    failure_count = 0
    
    for function_name, env_vars in AGENT_CONFIG.items():
        print(f"\n📋 处理函数: {function_name}")
        print(f"   更新变量: {list(env_vars.keys())}")
        if fix_lambda_environment(function_name, env_vars):
            success_count += 1
        else:
            failure_count += 1
    
    print("\n" + "=" * 60)
    print(f"修复结果: 成功 {success_count}/{len(AGENT_CONFIG)}, 失败 {failure_count}/{len(AGENT_CONFIG)}")
    print("=" * 60)
    
    # 验证修复结果
    print("\n🔍 验证修复结果...")
    print("-" * 60)
    
    validation_passed = True
    for func_name, expected_vars in AGENT_CONFIG.items():
        try:
            response = lambda_client.get_function_configuration(
                FunctionName=func_name
            )
            env_vars = response.get('Environment', {}).get('Variables', {})
            
            # 检查每个期望的变量
            issues = []
            for key, expected_value in expected_vars.items():
                actual_value = env_vars.get(key)
                if actual_value != expected_value:
                    issues.append(f"{key}: 期望'{expected_value}', 实际'{actual_value}'")
            
            if issues:
                print(f"❌ {func_name}:")
                for issue in issues:
                    print(f"   - {issue}")
                validation_passed = False
            else:
                print(f"✅ {func_name}: 所有环境变量已正确设置")
                
        except Exception as e:
            print(f"❌ {func_name}: 无法验证 - {str(e)}")
            validation_passed = False
    
    print("-" * 60)
    
    if validation_passed and failure_count == 0:
        print("\n🎉 修复成功！所有Lambda函数的环境变量已正确更新。")
        print("   - Bedrock Agent ID已更新为正确值")
        print("   - DynamoDB表已统一为ai-ppt-assistant-dev-sessions")
        return 0
    else:
        print("\n⚠️ 修复未完全成功，请检查上述错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())