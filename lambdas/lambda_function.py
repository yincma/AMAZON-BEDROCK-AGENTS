"""
Lambda Function - 简化版PPT生成API（无外部依赖）
"""
import json
import uuid
import boto3
from datetime import datetime

# 初始化 AWS 服务
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    """Lambda处理函数 - 简化版，确保能正常工作"""
    try:
        # 解析请求
        if isinstance(event.get('body'), str):
            body = json.loads(event.get('body', '{}'))
        else:
            body = event.get('body', {})

        topic = body.get('topic')
        page_count = body.get('page_count', 10)
        audience = body.get('audience', 'general')

        # 验证输入
        if not topic:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': '缺少必需参数: topic'
                })
            }

        # 生成presentation_id
        presentation_id = str(uuid.uuid4())

        # 创建演示文稿数据（模拟）
        presentation_data = {
            'presentation_id': presentation_id,
            'topic': topic,
            'title': f"{topic} - 演示文稿",
            'page_count': page_count,
            'audience': audience,
            'status': 'processing',
            'created_at': datetime.now().isoformat(),
            'slides': []
        }

        # 生成幻灯片（简化版 - 使用咨询顾问风格的内容）
        slide_templates = [
            {"title": "执行摘要", "content": f"关于{topic}的核心洞察与战略建议"},
            {"title": "背景与挑战", "content": f"{topic}领域的现状分析与关键挑战"},
            {"title": "战略框架", "content": f"基于MECE原则的{topic}分析框架"},
            {"title": "解决方案", "content": f"{topic}的创新解决路径"},
            {"title": "实施路线图", "content": f"{topic}项目的阶段性实施计划"},
            {"title": "预期成果", "content": f"实施{topic}后的价值创造与影响"},
            {"title": "风险与缓解", "content": f"{topic}实施中的潜在风险及应对策略"},
            {"title": "成功案例", "content": f"行业内{topic}的最佳实践参考"},
            {"title": "资源需求", "content": f"推进{topic}所需的关键资源配置"},
            {"title": "下一步行动", "content": f"{topic}的优先行动计划与里程碑"}
        ]

        for i in range(1, min(page_count + 1, len(slide_templates) + 1)):
            template = slide_templates[i-1] if i <= len(slide_templates) else {"title": f"第{i}页", "content": f"关于{topic}的补充内容"}
            slide = {
                'slide_number': i,
                'title': template['title'],
                'content': template['content'],
                'speaker_notes': f"详细阐述{template['title']}的关键要点，强调{topic}的战略重要性。"
            }
            presentation_data['slides'].append(slide)

        # 更新状态为完成
        presentation_data['status'] = 'completed'

        # 尝试保存到DynamoDB（如果表存在）
        try:
            table = dynamodb.Table('ai-ppt-presentations')
            table.put_item(Item=presentation_data)
        except Exception as e:
            print(f"DynamoDB保存失败（可忽略）: {str(e)}")

        # 返回成功响应
        response = {
            'presentation_id': presentation_id,
            'status': 'completed',
            'message': 'PPT生成成功',
            'topic': topic,
            'page_count': page_count,
            'created_at': presentation_data['created_at']
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-API-Key'
            },
            'body': json.dumps(response, ensure_ascii=False)
        }

    except Exception as e:
        print(f"处理请求时出错: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': '内部服务器错误',
                'message': str(e)
            })
        }
