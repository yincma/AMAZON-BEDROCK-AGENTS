#!/usr/bin/env python3
"""
Bedrock权限测试脚本
直接测试Lambda函数是否能成功调用Bedrock Agent
"""

import json
import boto3
import sys
from datetime import datetime

def test_bedrock_agent_invocation():
    """测试Bedrock Agent调用"""
    print("🤖 测试Bedrock Agent调用权限")
    print("=" * 60)
    
    bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    
    # 测试配置
    test_agents = [
        {
            'name': 'Orchestrator Agent',
            'agent_id': 'LA1D127LSK',
            'alias_id': 'TSTALIASID',
            'session_id': f'test-session-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'input_text': 'Generate a simple presentation outline about AWS'
        },
        {
            'name': 'Content Agent',
            'agent_id': 'KXWM8D0L7J',
            'alias_id': 'TSTALIASID',
            'session_id': f'test-session-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'input_text': 'Create content for a slide about cloud computing'
        },
        {
            'name': 'Visual Agent',
            'agent_id': 'SXISBNLYOZ',
            'alias_id': 'TSTALIASID',
            'session_id': f'test-session-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'input_text': 'Find images related to technology'
        },
        {
            'name': 'Compiler Agent',
            'agent_id': 'WJCMF1L8VG',
            'alias_id': 'TSTALIASID',
            'session_id': f'test-session-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'input_text': 'Compile a presentation'
        }
    ]
    
    results = []
    
    for agent_config in test_agents:
        print(f"\n📍 测试 {agent_config['name']}:")
        print(f"   Agent ID: {agent_config['agent_id']}")
        print(f"   Alias ID: {agent_config['alias_id']}")
        
        try:
            # 尝试调用Agent
            response = bedrock_agent.invoke_agent(
                agentId=agent_config['agent_id'],
                agentAliasId=agent_config['alias_id'],
                sessionId=agent_config['session_id'],
                inputText=agent_config['input_text'],
                enableTrace=False
            )
            
            # 检查响应
            if response.get('completion'):
                print(f"   ✅ 成功调用Agent")
                results.append((agent_config['name'], True, None))
            else:
                print(f"   ⚠️  调用返回但无响应内容")
                results.append((agent_config['name'], False, "No response content"))
                
        except Exception as e:
            error_msg = str(e)
            if 'AccessDeniedException' in error_msg:
                print(f"   ❌ 权限被拒绝: {error_msg[:100]}")
                results.append((agent_config['name'], False, "AccessDeniedException"))
            elif 'ResourceNotFoundException' in error_msg:
                print(f"   ❌ Agent未找到: {error_msg[:100]}")
                results.append((agent_config['name'], False, "ResourceNotFoundException"))
            else:
                print(f"   ❌ 其他错误: {error_msg[:100]}")
                results.append((agent_config['name'], False, error_msg[:100]))
    
    return results

def test_lambda_invocation():
    """通过Lambda测试Bedrock权限"""
    print("\n🔧 通过Lambda函数测试Bedrock权限")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # 测试generate_presentation Lambda函数
    test_payload = {
        "body": json.dumps({
            "topic": "Test AWS Permissions",
            "user_id": "test-user",
            "num_slides": 3
        })
    }
    
    try:
        print("\n📍 测试 generate_presentation Lambda函数:")
        response = lambda_client.invoke(
            FunctionName='ai-ppt-assistant-api-generate-presentation',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        status_code = response_payload.get('statusCode', 0)
        
        if status_code == 200:
            print("   ✅ Lambda函数成功执行")
            body = json.loads(response_payload.get('body', '{}'))
            if body.get('data', {}).get('task_id'):
                print(f"   ✅ 成功创建任务: {body['data']['task_id']}")
                return True, body['data']['task_id']
        else:
            print(f"   ❌ Lambda返回错误: {status_code}")
            print(f"   错误信息: {response_payload.get('body', '')[:200]}")
            return False, None
            
    except Exception as e:
        print(f"   ❌ Lambda调用失败: {str(e)[:200]}")
        return False, None

def test_agent_status():
    """检查Agent状态"""
    print("\n📊 检查Bedrock Agent状态")
    print("=" * 60)
    
    bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')
    
    agent_ids = [
        ('Orchestrator', 'LA1D127LSK'),
        ('Content', 'KXWM8D0L7J'),
        ('Visual', 'SXISBNLYOZ'),
        ('Compiler', 'WJCMF1L8VG')
    ]
    
    for agent_name, agent_id in agent_ids:
        try:
            response = bedrock_agent.get_agent(agentId=agent_id)
            agent = response['agent']
            status = agent.get('agentStatus', 'UNKNOWN')
            
            status_icon = "✅" if status == "PREPARED" else "⚠️"
            print(f"{status_icon} {agent_name} Agent ({agent_id}): {status}")
            
            if status != "PREPARED":
                print(f"   ⚠️  Agent需要准备: 运行 prepare_agent 操作")
                
        except Exception as e:
            print(f"❌ 无法获取 {agent_name} Agent状态: {str(e)[:100]}")

def main():
    """主函数"""
    print("🚀 AI PPT Assistant - Bedrock权限测试")
    print("=" * 60)
    print("测试时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # 1. 检查Agent状态
    test_agent_status()
    
    # 2. 测试直接调用Bedrock Agent
    agent_results = test_bedrock_agent_invocation()
    
    # 3. 通过Lambda测试
    lambda_success, task_id = test_lambda_invocation()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试总结:")
    print("=" * 60)
    
    # Agent测试结果
    agent_passed = sum(1 for _, success, _ in agent_results if success)
    agent_failed = len(agent_results) - agent_passed
    
    print(f"\nBedrock Agent直接调用:")
    print(f"  ✅ 成功: {agent_passed}/{len(agent_results)}")
    print(f"  ❌ 失败: {agent_failed}/{len(agent_results)}")
    
    if agent_failed > 0:
        print("\n失败的Agent:")
        for name, success, error in agent_results:
            if not success:
                print(f"  - {name}: {error}")
    
    # Lambda测试结果
    print(f"\nLambda函数调用:")
    if lambda_success:
        print(f"  ✅ 成功创建任务: {task_id}")
    else:
        print(f"  ❌ Lambda调用失败")
    
    # 建议
    if agent_failed > 0 or not lambda_success:
        print("\n💡 建议操作:")
        print("1. 检查Lambda函数的IAM角色是否包含bedrock:InvokeAgent权限")
        print("2. 确保所有Bedrock Agent处于PREPARED状态")
        print("3. 验证Agent ID和Alias ID是否正确")
        print("4. 运行 'python scripts/validate_iam_permissions.py' 验证权限配置")
        print("5. 查看CloudWatch日志获取详细错误信息")
        return 1
    else:
        print("\n✨ 所有Bedrock权限测试通过!")
        return 0

if __name__ == "__main__":
    sys.exit(main())