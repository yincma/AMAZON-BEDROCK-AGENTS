#!/usr/bin/env python3
"""
部署验证脚本
检查关键配置是否正确设置
"""

import boto3
import sys
import json
from datetime import datetime

def check_lambda_configuration():
    """检查Lambda函数配置"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # 检查关键Lambda函数
    key_functions = [
        'ai-ppt-assistant-api-generate-presentation',
        'ai-ppt-assistant-api-presentation-status',
        'ai-ppt-assistant-api-task-processor'
    ]
    
    issues = []
    
    for func_name in key_functions:
        try:
            response = lambda_client.get_function_configuration(FunctionName=func_name)
            env_vars = response.get('Environment', {}).get('Variables', {})
            
            # 检查关键环境变量
            critical_vars = {
                'ORCHESTRATOR_AGENT_ID': 'Bedrock Agent ID',
                'ORCHESTRATOR_ALIAS_ID': 'Bedrock Agent Alias ID',
                'DYNAMODB_TABLE': 'DynamoDB Table Name'
            }
            
            for var, description in critical_vars.items():
                value = env_vars.get(var, '')
                
                # 检查无效值
                if not value or value == 'None' or 'placeholder' in value.lower():
                    issues.append(f"❌ {func_name}: {var} is invalid ({value})")
                elif var == 'DYNAMODB_TABLE' and value != 'ai-ppt-assistant-dev-sessions':
                    issues.append(f"⚠️ {func_name}: {var} might be incorrect ({value})")
                    
        except Exception as e:
            issues.append(f"❌ Failed to check {func_name}: {str(e)}")
    
    return issues

def check_api_gateway():
    """检查API Gateway配置"""
    api_client = boto3.client('apigateway', region_name='us-east-1')
    
    try:
        # 获取API列表
        apis = api_client.get_rest_apis()
        
        # 查找我们的API
        our_api = None
        for api in apis.get('items', []):
            if 'ai-ppt-assistant' in api.get('name', '').lower():
                our_api = api
                break
        
        if our_api:
            print(f"✅ API Gateway found: {our_api['id']}")
            
            # 检查API密钥
            api_keys = api_client.get_api_keys()
            if api_keys.get('items'):
                print(f"✅ API Keys configured: {len(api_keys['items'])} key(s)")
            else:
                return ["❌ No API keys found"]
        else:
            return ["❌ API Gateway not found"]
            
    except Exception as e:
        return [f"❌ Failed to check API Gateway: {str(e)}"]
    
    return []

def check_dynamodb_tables():
    """检查DynamoDB表"""
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    
    required_tables = [
        'ai-ppt-assistant-dev-sessions',
        'ai-ppt-assistant-dev-tasks',
        'ai-ppt-assistant-dev-checkpoints'
    ]
    
    issues = []
    
    for table_name in required_tables:
        try:
            response = dynamodb.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            
            if status != 'ACTIVE':
                issues.append(f"⚠️ Table {table_name} is not active (status: {status})")
            else:
                print(f"✅ DynamoDB table {table_name} is active")
                
        except dynamodb.exceptions.ResourceNotFoundException:
            issues.append(f"❌ DynamoDB table {table_name} not found")
        except Exception as e:
            issues.append(f"❌ Failed to check table {table_name}: {str(e)}")
    
    return issues

def check_bedrock_agents():
    """检查Bedrock Agents是否存在"""
    bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')
    
    try:
        response = bedrock_agent.list_agents()
        agents = response.get('agentSummaries', [])
        
        expected_agents = ['orchestrator', 'compiler', 'content', 'visual']
        found_agents = []
        
        for agent in agents:
            agent_name = agent.get('agentName', '')
            for expected in expected_agents:
                if expected in agent_name.lower():
                    found_agents.append(expected)
                    print(f"✅ Bedrock Agent found: {agent_name} (ID: {agent['agentId']})")
        
        missing = set(expected_agents) - set(found_agents)
        if missing:
            return [f"⚠️ Missing Bedrock Agents: {', '.join(missing)}"]
            
    except Exception as e:
        return [f"⚠️ Could not check Bedrock Agents: {str(e)}"]
    
    return []

def main():
    """主验证流程"""
    print("\n" + "="*60)
    print("🔍 AI PPT Assistant Deployment Verification")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    all_issues = []
    
    # 1. 检查Lambda配置
    print("Checking Lambda functions...")
    issues = check_lambda_configuration()
    all_issues.extend(issues)
    
    # 2. 检查API Gateway
    print("\nChecking API Gateway...")
    issues = check_api_gateway()
    all_issues.extend(issues)
    
    # 3. 检查DynamoDB表
    print("\nChecking DynamoDB tables...")
    issues = check_dynamodb_tables()
    all_issues.extend(issues)
    
    # 4. 检查Bedrock Agents
    print("\nChecking Bedrock Agents...")
    issues = check_bedrock_agents()
    all_issues.extend(issues)
    
    # 结果总结
    print("\n" + "="*60)
    if all_issues:
        print("⚠️ VERIFICATION FAILED - Issues found:")
        for issue in all_issues:
            print(f"  {issue}")
        print("\n💡 To fix these issues, run:")
        print("  ./scripts/sync_bedrock_config.sh")
        print("  python3 fix_data_issue.py")
        sys.exit(1)
    else:
        print("✅ VERIFICATION PASSED - All checks successful!")
        print("\n🎉 Your deployment is ready to use!")
        print("\nTest your API with:")
        print("  python3 test_all_backend_apis.py")
        sys.exit(0)

if __name__ == "__main__":
    main()