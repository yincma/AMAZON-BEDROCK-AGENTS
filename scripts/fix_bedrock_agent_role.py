#!/usr/bin/env python3
"""
临时脚本：为现有Bedrock Agent创建和关联IAM角色
修复accessDeniedException问题
"""

import json
import boto3
import time

# AWS clients
iam = boto3.client('iam')
bedrock_agent = boto3.client('bedrock-agent')

# Configuration
AGENT_ID = "LA1D127LSK"
REGION = "us-east-1"
ACCOUNT_ID = "375004070918"
ROLE_NAME = "ai-ppt-assistant-orchestrator-agent-role"
POLICY_NAME = "ai-ppt-assistant-orchestrator-agent-policy"

def create_agent_iam_role():
    """创建Bedrock Agent需要的IAM角色"""
    print(f"🔧 创建IAM角色: {ROLE_NAME}")
    
    # 1. 创建IAM角色
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        role_response = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IAM role for AI PPT Assistant Bedrock Orchestrator Agent",
            Tags=[
                {"Key": "Project", "Value": "ai-ppt-assistant"},
                {"Key": "Environment", "Value": "dev"},
                {"Key": "Agent", "Value": "orchestrator"}
            ]
        )
        print(f"✅ IAM角色创建成功")
        role_arn = role_response['Role']['Arn']
    except iam.exceptions.EntityAlreadyExistsException:
        print("⚠️  IAM角色已存在，获取现有角色")
        role_response = iam.get_role(RoleName=ROLE_NAME)
        role_arn = role_response['Role']['Arn']
    
    # 2. 创建IAM策略
    print(f"🔧 创建IAM策略: {POLICY_NAME}")
    
    agent_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BedrockFoundationModelAccess",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{REGION}::foundation-model/*",
                    "arn:aws:bedrock:*:*:inference-profile/*"
                ]
            },
            {
                "Sid": "BedrockInferenceProfileAccess",
                "Effect": "Allow",
                "Action": [
                    "bedrock:GetInferenceProfile",
                    "bedrock:ListInferenceProfiles",
                    "bedrock:UseInferenceProfile"
                ],
                "Resource": "*"
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT_ID}:log-group:/aws/bedrock/*"
            }
        ]
    }
    
    try:
        policy_response = iam.create_policy(
            PolicyName=POLICY_NAME,
            PolicyDocument=json.dumps(agent_policy),
            Description="Policy for AI PPT Assistant Bedrock Orchestrator Agent"
        )
        print(f"✅ IAM策略创建成功")
        policy_arn = policy_response['Policy']['Arn']
    except iam.exceptions.EntityAlreadyExistsException:
        print("⚠️  IAM策略已存在，获取现有策略")
        policy_arn = f"arn:aws:iam::{ACCOUNT_ID}:policy/{POLICY_NAME}"
    
    # 3. 将策略附加到角色
    print("🔗 将策略附加到角色")
    iam.attach_role_policy(
        RoleName=ROLE_NAME,
        PolicyArn=policy_arn
    )
    print("✅ 策略附加成功")
    
    # 等待角色传播
    print("⏱️  等待IAM角色传播...")
    time.sleep(30)
    
    return role_arn

def update_agent_role(role_arn):
    """更新Bedrock Agent的IAM角色"""
    print(f"🔧 更新Agent {AGENT_ID} 的IAM角色")
    
    try:
        # 首先获取现有agent配置
        agent_info = bedrock_agent.get_agent(agentId=AGENT_ID)
        agent = agent_info['agent']
        
        print(f"📋 现有Agent配置: {agent['agentName']}")
        
        # 使用正确的参数更新agent
        response = bedrock_agent.update_agent(
            agentId=AGENT_ID,
            agentName=agent['agentName'],
            agentResourceRoleArn=role_arn,
            foundationModel=agent.get('foundationModel', 'us.anthropic.claude-opus-4-1-20250805-v1:0'),
            instruction=agent.get('instruction', 'You are an AI assistant that helps generate presentations.')
        )
        print("✅ Agent IAM角色更新成功")
        
        # 准备agent以使更改生效
        print("🚀 准备Agent...")
        prepare_response = bedrock_agent.prepare_agent(agentId=AGENT_ID)
        print("✅ Agent准备完成")
        
        return True
    except Exception as e:
        print(f"❌ 更新Agent角色失败: {e}")
        return False

def main():
    print("🚀 开始修复Bedrock Agent IAM角色问题")
    print("=" * 50)
    
    try:
        # 1. 创建IAM角色和策略
        role_arn = create_agent_iam_role()
        
        # 2. 更新Agent
        success = update_agent_role(role_arn)
        
        if success:
            print("\n🎉 Bedrock Agent IAM角色修复完成！")
            print("现在可以重新测试API功能")
        else:
            print("\n❌ Agent角色更新失败")
            
    except Exception as e:
        print(f"\n💥 修复过程异常: {e}")

if __name__ == "__main__":
    main()