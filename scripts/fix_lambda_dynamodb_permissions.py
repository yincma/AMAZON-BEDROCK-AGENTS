#!/usr/bin/env python3
"""
快速修复Lambda DynamoDB权限，添加sessions表访问权限
"""

import json
import boto3

# AWS clients  
iam = boto3.client('iam')

# Configuration
POLICY_ARN = "arn:aws:iam::375004070918:policy/ai-ppt-assistant-lambda-policy"

def update_lambda_policy():
    """更新Lambda IAM策略添加sessions表权限"""
    print("🔧 更新Lambda IAM策略...")
    
    try:
        # 获取当前策略版本
        current_version = iam.get_policy(PolicyArn=POLICY_ARN)['Policy']['DefaultVersionId']
        current_policy = iam.get_policy_version(PolicyArn=POLICY_ARN, VersionId=current_version)
        
        # 修改策略文档
        policy_doc = current_policy['PolicyVersion']['Document']
        
        # 找到DynamoDB权限语句并添加sessions表
        for statement in policy_doc['Statement']:
            if 'dynamodb:PutItem' in statement.get('Action', []):
                # 添加sessions表ARN
                sessions_table_arn = "arn:aws:dynamodb:us-east-1:375004070918:table/ai-ppt-assistant-dev-sessions"
                if sessions_table_arn not in statement['Resource']:
                    statement['Resource'].append(sessions_table_arn)
                    print(f"✅ 添加sessions表权限: {sessions_table_arn}")
        
        # 创建新版本
        new_version_response = iam.create_policy_version(
            PolicyArn=POLICY_ARN,
            PolicyDocument=json.dumps(policy_doc, indent=2),
            SetAsDefault=True
        )
        
        print(f"✅ 策略版本 {new_version_response['PolicyVersion']['VersionId']} 创建并设为默认")
        return True
        
    except Exception as e:
        print(f"❌ 策略更新失败: {e}")
        return False

def main():
    print("🚀 修复Lambda DynamoDB权限")
    print("=" * 40)
    
    success = update_lambda_policy()
    
    if success:
        print("\n🎉 Lambda权限修复完成！")
        print("💡 等待30秒让权限生效，然后重新测试")
    else:
        print("\n❌ 权限修复失败")

if __name__ == "__main__":
    main()