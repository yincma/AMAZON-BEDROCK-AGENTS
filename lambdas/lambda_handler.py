"""
Lambda函数入口点 - PPT生成服务
"""

import json
import boto3
import uuid
from datetime import datetime
from image_processing_service import ImageProcessingService

def lambda_handler(event, context):
    """
    Lambda函数主处理器

    支持的操作:
    - generate_ppt: 生成新的PPT
    - generate_image: 生成单张图片
    - status: 查询生成状态
    - test: 测试连接
    """

    print(f"收到请求: {json.dumps(event)}")

    # 获取操作类型
    action = event.get('action', 'generate_ppt')

    try:
        if action == 'test':
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Lambda函数运行正常',
                    'timestamp': datetime.now().isoformat(),
                    'version': '2.0'
                })
            }

        elif action == 'generate_image':
            # 生成单张图片
            slide_content = event.get('slide_content', {
                'title': 'AI技术',
                'content': ['人工智能', '机器学习', '深度学习']
            })

            image_service = ImageProcessingService()
            prompt = image_service.generate_prompt(slide_content)

            try:
                image_data = image_service.call_image_generation(prompt)

                # 保存到S3
                s3_client = boto3.client('s3')
                bucket = os.environ.get('S3_BUCKET', 'ai-ppt-presentations-dev')
                key = f"images/{uuid.uuid4()}.png"

                s3_client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=image_data,
                    ContentType='image/png'
                )

                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'success',
                        'image_url': f"s3://{bucket}/{key}",
                        'size': len(image_data)
                    })
                }
            except Exception as e:
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'status': 'error',
                        'message': str(e)
                    })
                }

        elif action == 'generate_ppt':
            # 生成完整PPT
            topic = event.get('topic', 'AI技术演示')
            slides_count = event.get('slides_count', 5)

            # TODO: 实现完整的PPT生成逻辑
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'processing',
                    'presentation_id': str(uuid.uuid4()),
                    'message': f'正在生成{slides_count}页关于"{topic}"的PPT'
                })
            }

        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'不支持的操作: {action}'
                })
            }

    except Exception as e:
        print(f"错误: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

import os