"""
Lambda处理器 - PPT生成API入口
"""
import json
import os
import sys
import uuid
from datetime import datetime
import logging

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.content_generator import ContentGenerator
from src.content_validator import validate_complete_presentation
from src.config import DEFAULT_PAGE_COUNT, MIN_PAGE_COUNT, MAX_PAGE_COUNT

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """Lambda处理函数

    Args:
        event: API Gateway事件
        context: Lambda上下文

    Returns:
        API响应
    """
    try:
        # 1. 解析请求
        if isinstance(event.get('body'), str):
            body = json.loads(event.get('body', '{}'))
        else:
            body = event.get('body', {})

        topic = body.get('topic')
        page_count = body.get('page_count', DEFAULT_PAGE_COUNT)

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

        # 验证页数
        if not isinstance(page_count, int) or page_count < MIN_PAGE_COUNT or page_count > MAX_PAGE_COUNT:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f'页数必须在{MIN_PAGE_COUNT}-{MAX_PAGE_COUNT}之间'
                })
            }

        # 2. 生成presentation_id
        presentation_id = str(uuid.uuid4())
        logger.info(f"开始生成PPT: {presentation_id}, 主题: {topic}, 页数: {page_count}")

        # 3. 初始化生成器
        generator = ContentGenerator()

        # 4. 生成大纲
        logger.info("生成大纲...")
        outline = generator.generate_outline(topic, page_count)

        # 5. 生成详细内容
        logger.info("生成详细内容...")
        slides = generator.generate_slide_content(outline)

        # 6. 构建完整内容
        content = {
            'presentation_id': presentation_id,
            'topic': topic,
            'title': outline.get('title', topic),
            'slides': slides,
            'metadata': {
                'total_slides': page_count,
                'created_at': datetime.now().isoformat(),
                'status': 'completed'
            }
        }

        # 7. 验证内容
        validation_result = validate_complete_presentation(outline, {'slides': slides})
        if not validation_result['is_valid']:
            logger.warning(f"内容验证失败: {validation_result['errors']}")

        # 8. 保存到S3
        logger.info("保存到S3...")
        s3_path = generator.save_to_s3(presentation_id, content)

        # 9. 返回响应
        response = {
            'presentation_id': presentation_id,
            'status': 'completed',
            'message': 'PPT生成成功',
            's3_path': s3_path,
            'total_slides': page_count,
            'validation': validation_result
        }

        logger.info(f"PPT生成完成: {presentation_id}")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response)
        }

    except ValueError as e:
        logger.error(f"参数错误: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }

    except Exception as e:
        logger.error(f"处理请求时出错: {str(e)}", exc_info=True)
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

# 本地测试
if __name__ == "__main__":
    # 测试事件
    test_event = {
        'body': json.dumps({
            'topic': '人工智能的未来',
            'page_count': 5
        })
    }

    # 测试上下文
    test_context = {}

    # 调用处理器
    result = handler(test_event, test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))