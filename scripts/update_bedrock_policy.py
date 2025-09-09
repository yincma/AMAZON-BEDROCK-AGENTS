#!/usr/bin/env python3
"""
更新Bedrock Agent的IAM策略，添加inference profile权限
"""

import json
import boto3

# AWS clients
iam = boto3.client('iam')

# Configuration
ROLE_NAME = "ai-ppt-assistant-bedrock-agent-role"
POLICY_NAME = "BedrockAgentPermissions"

def update_bedrock_agent_policy():
    """更新Bedrock Agent的IAM内联策略"""
    print(f"🔧 更新IAM内联策略: {POLICY_NAME}")
    
    # 新的策略文档，包含所有必需权限
    policy_document = {
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
                    "arn:aws:bedrock:us-east-1::foundation-model/*",
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
                "Sid": "S3Access",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::ai-ppt-assistant-dev-presentations-375004070918",
                    "arn:aws:s3:::ai-ppt-assistant-dev-presentations-375004070918/*"
                ]
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow", 
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:us-east-1:375004070918:log-group:/aws/bedrock/*"
            }
        ]
    }
    
    try:
        # 更新内联策略
        response = iam.put_role_policy(
            RoleName=ROLE_NAME,
            PolicyName=POLICY_NAME,
            PolicyDocument=json.dumps(policy_document, indent=2)
        )
        
        print("✅ IAM策略更新成功")
        print("📋 新增权限:")
        print("   - bedrock:GetInferenceProfile")
        print("   - bedrock:ListInferenceProfiles") 
        print("   - bedrock:UseInferenceProfile")
        print("   - inference-profile资源的InvokeModel权限")
        
        return True
        
    except Exception as e:
        print(f"❌ 策略更新失败: {e}")
        return False

def main():
    print("🚀 开始修复Bedrock Agent权限策略")
    print("=" * 50)
    
    success = update_bedrock_agent_policy()
    
    if success:
        print("\n🎉 Bedrock Agent权限策略修复完成！")
        print("💡 建议等待30-60秒让权限传播生效")
        print("🧪 然后重新测试API调用")
    else:
        print("\n❌ 权限策略修复失败")

if __name__ == "__main__":
    main()