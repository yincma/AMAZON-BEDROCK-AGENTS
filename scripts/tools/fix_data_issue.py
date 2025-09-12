#!/usr/bin/env python3
"""
临时修复脚本：将sessions表中的数据复制到tasks表
使presentation-status函数能够正确查询
"""

import boto3
import json
from datetime import datetime

# 创建DynamoDB客户端
dynamodb = boto3.client('dynamodb', region_name='us-east-1')

def copy_session_to_task(presentation_id):
    """将sessions表中的数据复制到tasks表"""
    
    # 1. 从sessions表扫描获取数据
    print(f"📋 扫描sessions表查找: {presentation_id}")
    response = dynamodb.scan(
        TableName='ai-ppt-assistant-dev-sessions',
        FilterExpression='presentation_id = :pid',
        ExpressionAttributeValues={
            ':pid': {'S': presentation_id}
        }
    )
    
    if not response.get('Items'):
        print(f"❌ 未找到presentation_id: {presentation_id}")
        return False
    
    item = response['Items'][0]
    print(f"✅ 找到数据，session_id: {item['session_id']['S']}")
    
    # 2. 转换数据格式并写入tasks表
    task_item = {
        'task_id': {'S': presentation_id},
        'presentation_id': {'S': presentation_id},
        'session_id': item['session_id'],
        'status': item['status'],
        'title': item['title'],
        'topic': item['topic'],
        'created_at': item['created_at'],
        'updated_at': item['updated_at'],
        'progress': item.get('progress', {'N': '0'}),
        'ttl': item.get('ttl', {'N': str(int(datetime.now().timestamp()) + 86400)})
    }
    
    # 复制其他所有字段
    for key in ['slide_count', 'language', 'style', 'audience', 'duration', 
                'template', 'include_speaker_notes', 'include_images']:
        if key in item:
            task_item[key] = item[key]
    
    print(f"📝 写入tasks表...")
    dynamodb.put_item(
        TableName='ai-ppt-assistant-dev-tasks',
        Item=task_item
    )
    
    print(f"✅ 成功复制到tasks表")
    return True

def fix_all_presentations():
    """修复所有现有的演示文稿数据"""
    
    print("🔧 开始修复数据问题...")
    
    # 扫描sessions表获取所有演示文稿
    response = dynamodb.scan(
        TableName='ai-ppt-assistant-dev-sessions'
    )
    
    presentations = response.get('Items', [])
    print(f"📊 找到 {len(presentations)} 个演示文稿")
    
    fixed_count = 0
    for item in presentations:
        if 'presentation_id' in item:
            pid = item['presentation_id']['S']
            print(f"\n处理: {pid}")
            if copy_session_to_task(pid):
                fixed_count += 1
    
    print(f"\n✅ 修复完成！成功处理 {fixed_count}/{len(presentations)} 个演示文稿")

if __name__ == "__main__":
    # 修复特定的测试演示文稿
    test_ids = [
        'dbd40880-8548-4150-acc1-759a1fe1de3e',
        'b9680f52-c80a-4bb3-ae95-2e5e1db19888'
    ]
    
    print("🔧 修复测试演示文稿...")
    for pid in test_ids:
        copy_session_to_task(pid)
    
    print("\n" + "="*50)
    print("修复所有演示文稿...")
    fix_all_presentations()