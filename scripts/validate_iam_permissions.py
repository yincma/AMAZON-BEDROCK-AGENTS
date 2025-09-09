#!/usr/bin/env python3
"""
IAM权限验证脚本
验证Lambda函数是否具有正确的Bedrock权限
"""

import json
import boto3
import sys
from typing import Dict, List, Tuple

def get_lambda_role(function_name: str) -> str:
    """获取Lambda函数的IAM角色ARN"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        return response['Configuration']['Role']
    except Exception as e:
        print(f"❌ 无法获取函数 {function_name} 的角色: {e}")
        return None

def get_role_policies(role_arn: str) -> List[Dict]:
    """获取角色的所有策略"""
    iam = boto3.client('iam')
    role_name = role_arn.split('/')[-1]
    policies = []
    
    try:
        # 获取内联策略
        inline_policies = iam.list_role_policies(RoleName=role_name)
        for policy_name in inline_policies.get('PolicyNames', []):
            policy_doc = iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            policies.append({
                'PolicyName': policy_name,
                'PolicyType': 'Inline',
                'PolicyDocument': json.loads(policy_doc['PolicyDocument']) if isinstance(policy_doc['PolicyDocument'], str) else policy_doc['PolicyDocument']
            })
        
        # 获取托管策略
        attached_policies = iam.list_attached_role_policies(RoleName=role_name)
        for policy in attached_policies.get('AttachedPolicies', []):
            policy_version = iam.get_policy(PolicyArn=policy['PolicyArn'])
            version_id = policy_version['Policy']['DefaultVersionId']
            policy_doc = iam.get_policy_version(PolicyArn=policy['PolicyArn'], VersionId=version_id)
            policies.append({
                'PolicyName': policy['PolicyName'],
                'PolicyType': 'Managed',
                'PolicyDocument': policy_doc['PolicyVersion']['Document']
            })
    except Exception as e:
        print(f"❌ 无法获取角色 {role_name} 的策略: {e}")
    
    return policies

def check_bedrock_permissions(policies: List[Dict]) -> Tuple[bool, List[str], List[str]]:
    """检查是否包含必需的Bedrock权限"""
    required_actions = [
        'bedrock:InvokeAgent',
        'bedrock:GetAgent',
        'bedrock:GetFoundationModelAvailability',
        'bedrock:ListFoundationModels',
        'bedrock:InvokeModel'
    ]
    
    found_actions = set()
    missing_actions = set(required_actions)
    
    for policy in policies:
        policy_doc = policy.get('PolicyDocument', {})
        for statement in policy_doc.get('Statement', []):
            if statement.get('Effect') == 'Allow':
                actions = statement.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                
                for action in actions:
                    # 检查通配符
                    if action == 'bedrock:*':
                        found_actions.update(required_actions)
                        missing_actions.clear()
                    elif action.startswith('bedrock:'):
                        if action in required_actions:
                            found_actions.add(action)
                            missing_actions.discard(action)
    
    return len(missing_actions) == 0, list(found_actions), list(missing_actions)

def check_dynamodb_permissions(policies: List[Dict]) -> Tuple[bool, List[str]]:
    """检查DynamoDB权限"""
    required_actions = [
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:Query',
        'dynamodb:Scan'
    ]
    
    found_actions = set()
    
    for policy in policies:
        policy_doc = policy.get('PolicyDocument', {})
        for statement in policy_doc.get('Statement', []):
            if statement.get('Effect') == 'Allow':
                actions = statement.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                
                for action in actions:
                    if action == 'dynamodb:*':
                        found_actions.update(required_actions)
                    elif action in required_actions:
                        found_actions.add(action)
    
    return len(found_actions) >= len(required_actions), list(found_actions)

def check_s3_permissions(policies: List[Dict]) -> Tuple[bool, List[str]]:
    """检查S3权限"""
    required_actions = [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket'
    ]
    
    found_actions = set()
    
    for policy in policies:
        policy_doc = policy.get('PolicyDocument', {})
        for statement in policy_doc.get('Statement', []):
            if statement.get('Effect') == 'Allow':
                actions = statement.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                
                for action in actions:
                    if action == 's3:*':
                        found_actions.update(required_actions)
                    elif action in required_actions:
                        found_actions.add(action)
    
    return len(found_actions) >= len(required_actions), list(found_actions)

def validate_lambda_permissions(function_name: str) -> bool:
    """验证单个Lambda函数的权限"""
    print(f"\n🔍 检查Lambda函数: {function_name}")
    print("=" * 60)
    
    # 获取Lambda角色
    role_arn = get_lambda_role(function_name)
    if not role_arn:
        return False
    
    print(f"📋 IAM角色: {role_arn.split('/')[-1]}")
    
    # 获取角色策略
    policies = get_role_policies(role_arn)
    print(f"📑 找到 {len(policies)} 个策略")
    
    all_valid = True
    
    # 检查Bedrock权限
    print("\n🤖 Bedrock权限检查:")
    has_bedrock, found_bedrock, missing_bedrock = check_bedrock_permissions(policies)
    if has_bedrock:
        print("  ✅ 所有必需的Bedrock权限都已配置")
        for action in found_bedrock:
            print(f"    ✓ {action}")
    else:
        print("  ❌ 缺少Bedrock权限:")
        for action in missing_bedrock:
            print(f"    ✗ {action}")
        all_valid = False
    
    # 检查DynamoDB权限
    print("\n💾 DynamoDB权限检查:")
    has_dynamodb, found_dynamodb = check_dynamodb_permissions(policies)
    if has_dynamodb:
        print("  ✅ DynamoDB权限已配置")
    else:
        print("  ⚠️  部分DynamoDB权限可能缺失")
    
    # 检查S3权限
    print("\n📦 S3权限检查:")
    has_s3, found_s3 = check_s3_permissions(policies)
    if has_s3:
        print("  ✅ S3权限已配置")
    else:
        print("  ⚠️  部分S3权限可能缺失")
    
    return all_valid

def main():
    """主函数"""
    print("🚀 AI PPT Assistant - IAM权限验证")
    print("=" * 60)
    
    # 需要检查的Lambda函数列表
    lambda_functions = [
        'ai-ppt-assistant-create-outline',
        'ai-ppt-assistant-generate-content',
        'ai-ppt-assistant-generate-image',
        'ai-ppt-assistant-find-image',
        'ai-ppt-assistant-generate-speaker-notes',
        'ai-ppt-assistant-compile-pptx',
        'ai-ppt-assistant-api-generate-presentation',
        'ai-ppt-assistant-api-presentation-status',
        'ai-ppt-assistant-api-presentation-download',
        'ai-ppt-assistant-api-modify-slide',
        'ai-ppt-assistant-api-list-presentations'
    ]
    
    all_valid = True
    validation_results = {}
    
    for function_name in lambda_functions:
        try:
            is_valid = validate_lambda_permissions(function_name)
            validation_results[function_name] = is_valid
            if not is_valid:
                all_valid = False
        except Exception as e:
            print(f"❌ 验证函数 {function_name} 时出错: {e}")
            validation_results[function_name] = False
            all_valid = False
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 验证总结:")
    print("=" * 60)
    
    passed = sum(1 for v in validation_results.values() if v)
    failed = len(validation_results) - passed
    
    print(f"✅ 通过: {passed}/{len(validation_results)}")
    print(f"❌ 失败: {failed}/{len(validation_results)}")
    
    if failed > 0:
        print("\n❌ 失败的函数:")
        for func_name, is_valid in validation_results.items():
            if not is_valid:
                print(f"  - {func_name}")
    
    if all_valid:
        print("\n✨ 所有Lambda函数的IAM权限配置正确!")
        return 0
    else:
        print("\n⚠️  部分Lambda函数缺少必需的权限，请修复后再部署")
        print("\n建议操作:")
        print("1. 运行 'terraform plan' 检查配置")
        print("2. 运行 'terraform apply' 应用权限更新")
        print("3. 重新运行此脚本验证权限")
        return 1

if __name__ == "__main__":
    sys.exit(main())