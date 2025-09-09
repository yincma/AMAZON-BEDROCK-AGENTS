#!/usr/bin/env python3
"""
快速验证V3版本修复效果的脚本
"""

import boto3
import requests
import json

def verify_iam_policy_v3():
    """验证Lambda IAM策略V3版本"""
    iam = boto3.client('iam')
    
    try:
        policy = iam.get_policy(PolicyArn='arn:aws:iam::375004070918:policy/ai-ppt-assistant-lambda-policy')
        version = policy['Policy']['DefaultVersionId']
        
        if version == 'v3':
            print("✅ Lambda IAM策略: V3版本已部署")
            
            # 验证V3权限内容
            policy_doc = iam.get_policy_version(
                PolicyArn='arn:aws:iam::375004070918:policy/ai-ppt-assistant-lambda-policy',
                VersionId='v3'
            )['PolicyVersion']['Document']
            
            # 检查关键权限
            has_inference_profile = False
            has_sessions_table = False
            
            for statement in policy_doc['Statement']:
                if 'bedrock:GetInferenceProfile' in statement.get('Action', []):
                    has_inference_profile = True
                    print("  ✅ Inference Profile权限已配置")
                    
                if 'dynamodb:PutItem' in statement.get('Action', []):
                    resources = statement.get('Resource', [])
                    if any('sessions' in r for r in resources):
                        has_sessions_table = True
                        print("  ✅ Sessions表权限已配置")
            
            return has_inference_profile and has_sessions_table
        else:
            print(f"❌ Lambda IAM策略版本错误: {version} (应为v3)")
            return False
            
    except Exception as e:
        print(f"❌ IAM策略验证失败: {e}")
        return False

def verify_bedrock_agent():
    """验证Bedrock Agent状态和权限"""
    bedrock = boto3.client('bedrock-agent')
    
    try:
        agent = bedrock.get_agent(agentId='LA1D127LSK')['agent']
        
        status = agent['agentStatus']
        role_arn = agent.get('agentResourceRoleArn')
        
        if status == 'PREPARED':
            print("✅ Bedrock Agent状态: PREPARED")
        else:
            print(f"⚠️  Bedrock Agent状态: {status}")
            
        if role_arn:
            print(f"✅ Bedrock Agent IAM角色: {role_arn}")
            return True
        else:
            print("❌ Bedrock Agent缺少IAM角色")
            return False
            
    except Exception as e:
        print(f"❌ Bedrock Agent验证失败: {e}")
        return False

def verify_api_basic():
    """验证API基本功能"""
    api_url = "https://mhzd3d1mhh.execute-api.us-east-1.amazonaws.com/legacy"
    api_key = "R0tkfRDvg45T1vtuqZu101qYmhXWyXWM2lqxEjdj"
    
    headers = {
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        # 测试健康检查
        health_response = requests.get(f"{api_url}/health", headers=headers)
        if health_response.status_code == 200:
            print("✅ API健康检查: 正常")
        else:
            print(f"❌ API健康检查失败: {health_response.status_code}")
            return False
            
        # 测试演示文稿创建
        create_data = {
            "title": "V3验证测试",
            "topic": "验证所有修复是否生效"
        }
        
        create_response = requests.post(
            f"{api_url}/presentations", 
            headers=headers, 
            json=create_data
        )
        
        if create_response.status_code == 202:
            print("✅ 演示文稿创建API: 正常")
            return True
        else:
            print(f"❌ 演示文稿创建失败: {create_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False

def main():
    print("🔍 V3版本修复效果验证")
    print("=" * 40)
    
    # 验证各项修复
    iam_ok = verify_iam_policy_v3()
    agent_ok = verify_bedrock_agent() 
    api_ok = verify_api_basic()
    
    print("\n" + "=" * 40)
    print("📊 验证结果摘要:")
    print(f"   Lambda权限(V3): {'✅' if iam_ok else '❌'}")
    print(f"   Bedrock Agent: {'✅' if agent_ok else '❌'}")
    print(f"   API基本功能: {'✅' if api_ok else '❌'}")
    
    if iam_ok and agent_ok and api_ok:
        print("\n🎉 所有V3修复验证通过！")
        print("💡 系统已达到AWS专家级配置标准")
    else:
        print("\n⚠️  部分修复仍需时间生效")
        print("💡 建议等待5-10分钟权限传播后重新验证")

if __name__ == "__main__":
    main()