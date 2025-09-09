#!/usr/bin/env python3
"""
直接测试 Bedrock Agent 调用
用于诊断权限问题的根本原因
"""

import boto3
import json
from datetime import datetime

def test_bedrock_agent_call():
    """直接测试 Bedrock Agent 调用"""
    
    # 配置信息
    agent_id = "LA1D127LSK" 
    alias_id = "PSQBDUP6KR"
    region = "us-east-1"
    session_id = f"test-session-{int(datetime.now().timestamp())}"
    
    print(f"🔍 测试 Bedrock Agent 调用:")
    print(f"   Agent ID: {agent_id}")
    print(f"   Alias ID: {alias_id}")
    print(f"   Region: {region}")
    print(f"   Session ID: {session_id}")
    
    try:
        # 创建 Bedrock Agent Runtime 客户端
        bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=region)
        
        print("\n✅ Bedrock Agent Runtime 客户端创建成功")
        
        # 测试调用
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText="Hello, this is a test message. Can you help me create a simple presentation outline about AWS Lambda?"
        )
        
        print("✅ Agent 调用成功!")
        print(f"Response Keys: {list(response.keys())}")
        
        # 尝试读取响应流
        if 'completion' in response:
            completion = response['completion']
            if hasattr(completion, 'read'):
                content = completion.read().decode('utf-8')
                print(f"Response Content: {content[:200]}...")
            else:
                print(f"Completion: {completion}")
                
        return True
        
    except Exception as e:
        print(f"❌ Agent 调用失败: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        
        # 详细错误分析
        if hasattr(e, 'response'):
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', 'Unknown')
            print(f"AWS 错误代码: {error_code}")
            print(f"AWS 错误消息: {error_message}")
        
        return False

def test_bedrock_runtime_basic():
    """测试基础的 bedrock runtime 访问"""
    try:
        bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")
        
        # 测试基础模型调用
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            contentType="application/json",
            accept="application/json", 
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Say hello"}]
            })
        )
        
        print("✅ Bedrock Runtime 基础调用成功")
        return True
        
    except Exception as e:
        print(f"❌ Bedrock Runtime 基础调用失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Bedrock 权限诊断开始...")
    print("=" * 60)
    
    # 1. 测试基础 bedrock runtime
    print("\n1. 测试 Bedrock Runtime 基础访问:")
    basic_ok = test_bedrock_runtime_basic()
    
    # 2. 测试 Agent 调用
    print("\n2. 测试 Bedrock Agent 调用:")
    agent_ok = test_bedrock_agent_call()
    
    print("\n" + "=" * 60)
    print("🎯 诊断结果:")
    print(f"   Bedrock Runtime: {'✅ 正常' if basic_ok else '❌ 失败'}")
    print(f"   Bedrock Agent: {'✅ 正常' if agent_ok else '❌ 失败'}")
    
    if not agent_ok and basic_ok:
        print("\n💡 分析: Bedrock Runtime 正常，但 Agent 调用失败")
        print("   可能原因:")
        print("   1. Agent 不存在或状态错误")
        print("   2. Agent 的 IAM 角色权限问题")
        print("   3. Agent 到 Foundation Model 的权限链断裂")
        print("   4. Region 或账户权限问题")
    elif not basic_ok:
        print("\n💡 分析: Bedrock 基础权限问题")
        print("   检查 AWS 凭证和区域配置")