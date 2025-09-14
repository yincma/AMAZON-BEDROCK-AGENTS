"""
Lambda函数: 更新单页幻灯片内容
API: PATCH /presentations/{id}/slides/{n}
"""

import json
import boto3
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

# AWS服务客户端
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Presentations')

# 配置
S3_BUCKET = 'ai-ppt-presentations'
LOCK_TIMEOUT = 30  # 秒


class ValidationError(Exception):
    """验证错误"""
    pass


class ConflictError(Exception):
    """资源冲突错误"""
    pass


class PreconditionFailedError(Exception):
    """前置条件失败错误"""
    pass


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda入口函数
    """
    try:
        # 解析路径参数
        presentation_id = event['pathParameters']['presentationId']
        slide_number = int(event['pathParameters']['slideNumber'])

        # 解析请求体
        body = json.loads(event.get('body', '{}'))

        # 获取ETag（如果提供）
        etag = event['headers'].get('If-Match')

        # 验证输入
        validate_input(presentation_id, slide_number, body)

        # 获取并验证演示文稿
        presentation = get_presentation(presentation_id)
        validate_presentation_state(presentation, slide_number)

        # 检查并发控制
        if etag and presentation.get('etag') != etag:
            raise PreconditionFailedError(
                f"ETag mismatch. Current: {presentation.get('etag')}"
            )

        # 获取锁
        lock_token = acquire_lock(presentation_id)

        try:
            # 更新幻灯片
            updated_presentation = update_slide_content(
                presentation,
                slide_number,
                body
            )

            # 保存更新
            new_etag = save_presentation(updated_presentation)

            # 生成预览URL
            preview_url = generate_preview_url(presentation_id, slide_number)

            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'ETag': new_etag,
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'presentation_id': presentation_id,
                    'slide_number': slide_number,
                    'updated_at': datetime.utcnow().isoformat(),
                    'etag': new_etag,
                    'preview_url': preview_url
                })
            }

        finally:
            # 释放锁
            release_lock(presentation_id, lock_token)

    except ValidationError as e:
        return error_response(400, 'VALIDATION_ERROR', str(e))
    except PreconditionFailedError as e:
        return error_response(412, 'PRECONDITION_FAILED', str(e))
    except ConflictError as e:
        return error_response(409, 'CONFLICT', str(e))
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return error_response(404, 'NOT_FOUND', 'Presentation not found')
        return error_response(500, 'INTERNAL_ERROR', str(e))
    except Exception as e:
        print(f"Unexpected error: {e}")
        return error_response(500, 'INTERNAL_ERROR', 'An unexpected error occurred')


def validate_input(presentation_id: str, slide_number: int, body: Dict[str, Any]):
    """
    验证输入参数
    """
    # 验证UUID格式
    try:
        uuid.UUID(presentation_id)
    except ValueError:
        raise ValidationError('Invalid presentation ID format')

    # 验证幻灯片编号
    if slide_number < 1 or slide_number > 100:
        raise ValidationError('Slide number must be between 1 and 100')

    # 验证请求体
    if not body:
        raise ValidationError('Request body cannot be empty')

    # 验证字段长度
    if 'title' in body and len(body['title']) > 100:
        raise ValidationError('Title exceeds maximum length of 100 characters')

    if 'content' in body and len(body['content']) > 2000:
        raise ValidationError('Content exceeds maximum length of 2000 characters')

    if 'speaker_notes' in body and len(body['speaker_notes']) > 1000:
        raise ValidationError('Speaker notes exceed maximum length of 1000 characters')

    # 验证布局类型
    valid_layouts = ['title', 'content', 'two_column', 'image_left', 'image_right', 'comparison']
    if 'layout' in body and body['layout'] not in valid_layouts:
        raise ValidationError(f'Invalid layout. Must be one of: {valid_layouts}')

    # 验证样式覆盖
    if 'style_overrides' in body:
        validate_style_overrides(body['style_overrides'])


def validate_style_overrides(style_overrides: Dict[str, Any]):
    """
    验证样式覆盖参数
    """
    if 'background_color' in style_overrides:
        color = style_overrides['background_color']
        if not isinstance(color, str) or not color.startswith('#') or len(color) != 7:
            raise ValidationError('Invalid background color format. Use #RRGGBB')

    if 'font_size' in style_overrides:
        size = style_overrides['font_size']
        if not isinstance(size, int) or size < 8 or size > 72:
            raise ValidationError('Font size must be between 8 and 72')


def get_presentation(presentation_id: str) -> Dict[str, Any]:
    """
    从DynamoDB获取演示文稿元数据
    """
    response = table.get_item(
        Key={'presentation_id': presentation_id}
    )

    if 'Item' not in response:
        raise ValidationError('Presentation not found')

    return response['Item']


def validate_presentation_state(presentation: Dict[str, Any], slide_number: int):
    """
    验证演示文稿状态
    """
    # 检查状态
    if presentation['status'] != 'completed':
        raise ConflictError(f"Cannot update presentation in {presentation['status']} state")

    # 检查幻灯片是否存在
    if slide_number > presentation.get('page_count', 0):
        raise ValidationError(f"Slide {slide_number} does not exist")

    # 检查锁状态
    if presentation.get('lock_token'):
        lock_expires = presentation.get('lock_expires', 0)
        if lock_expires > datetime.utcnow().timestamp():
            raise ConflictError('Presentation is locked by another operation')


def acquire_lock(presentation_id: str) -> str:
    """
    获取分布式锁
    """
    lock_token = str(uuid.uuid4())
    lock_expires = datetime.utcnow().timestamp() + LOCK_TIMEOUT

    try:
        table.update_item(
            Key={'presentation_id': presentation_id},
            UpdateExpression='SET lock_token = :token, lock_expires = :expires',
            ConditionExpression='attribute_not_exists(lock_token) OR lock_expires < :now',
            ExpressionAttributeValues={
                ':token': lock_token,
                ':expires': lock_expires,
                ':now': datetime.utcnow().timestamp()
            }
        )
        return lock_token
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            raise ConflictError('Failed to acquire lock')
        raise


def release_lock(presentation_id: str, lock_token: str):
    """
    释放分布式锁
    """
    try:
        table.update_item(
            Key={'presentation_id': presentation_id},
            UpdateExpression='REMOVE lock_token, lock_expires',
            ConditionExpression='lock_token = :token',
            ExpressionAttributeValues={':token': lock_token}
        )
    except ClientError:
        # 锁可能已过期或被其他进程释放
        pass


def update_slide_content(
    presentation: Dict[str, Any],
    slide_number: int,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    更新幻灯片内容
    """
    # 从S3下载当前PPTX文件
    pptx_key = f"presentations/{presentation['presentation_id']}/v{presentation.get('version', 1)}/presentation.pptx"

    # 这里应该实际下载和修改PPTX文件
    # 为演示目的，我们只更新元数据

    # 更新幻灯片元数据
    slides = presentation.get('slides', [])

    # 确保slides列表足够长
    while len(slides) < slide_number:
        slides.append({})

    # 更新指定幻灯片
    slide = slides[slide_number - 1]

    if 'title' in updates:
        slide['title'] = updates['title']
    if 'content' in updates:
        slide['content'] = updates['content']
    if 'speaker_notes' in updates:
        slide['speaker_notes'] = updates['speaker_notes']
    if 'layout' in updates:
        slide['layout'] = updates['layout']
    if 'style_overrides' in updates:
        slide['style_overrides'] = updates['style_overrides']

    slide['updated_at'] = datetime.utcnow().isoformat()

    presentation['slides'] = slides
    presentation['updated_at'] = datetime.utcnow().isoformat()
    presentation['version'] = presentation.get('version', 1) + 1

    return presentation


def save_presentation(presentation: Dict[str, Any]) -> str:
    """
    保存演示文稿到DynamoDB并返回新的ETag
    """
    # 生成新的ETag
    etag = generate_etag(presentation)
    presentation['etag'] = etag

    # 保存到DynamoDB
    table.put_item(Item=presentation)

    # 这里应该也上传更新后的PPTX到S3

    return etag


def generate_etag(data: Dict[str, Any]) -> str:
    """
    生成ETag
    """
    # 使用关键字段生成哈希
    key_fields = [
        str(data.get('presentation_id')),
        str(data.get('version', 1)),
        str(data.get('updated_at'))
    ]
    content = ''.join(key_fields)
    return hashlib.md5(content.encode()).hexdigest()


def generate_preview_url(presentation_id: str, slide_number: int) -> str:
    """
    生成幻灯片预览URL
    """
    # 生成预签名URL
    preview_key = f"presentations/{presentation_id}/previews/slide_{slide_number}.png"

    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': preview_key
            },
            ExpiresIn=3600
        )
        return url
    except:
        # 如果预览不存在，返回占位符
        return f"https://{S3_BUCKET}.s3.amazonaws.com/placeholder.png"


def error_response(status_code: int, error_code: str, message: str) -> Dict[str, Any]:
    """
    生成错误响应
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': error_code,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'request_id': str(uuid.uuid4())
        })
    }