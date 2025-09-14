"""
Lambda函数: 删除演示文稿
API: DELETE /presentations/{id}
"""

import json
import boto3
import uuid
from datetime import datetime
from typing import Dict, Any
from botocore.exceptions import ClientError

# AWS服务客户端
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
cloudwatch = boto3.client('logs')

# 配置
PRESENTATIONS_TABLE = 'Presentations'
TASKS_TABLE = 'Tasks'
S3_BUCKET = 'ai-ppt-presentations'
CLEANUP_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/xxx/cleanup-queue'


class ValidationError(Exception):
    """验证错误"""
    pass


class ConflictError(Exception):
    """资源冲突错误"""
    pass


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda入口函数
    """
    try:
        # 解析路径参数
        presentation_id = event['pathParameters']['presentationId']

        # 解析查询参数
        query_params = event.get('queryStringParameters', {}) or {}
        force_delete = query_params.get('force', 'false').lower() == 'true'

        # 验证输入
        validate_presentation_id(presentation_id)

        # 获取演示文稿信息
        presentation = get_presentation(presentation_id)

        # 检查是否可以删除
        if not force_delete:
            check_deletion_allowed(presentation)

        # 标记为删除中
        mark_as_deleting(presentation_id)

        # 创建异步清理任务
        cleanup_task_id = create_cleanup_task(presentation_id, presentation)

        # 返回成功响应
        return {
            'statusCode': 204,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'X-Cleanup-Task-Id': cleanup_task_id
            }
        }

    except ValidationError as e:
        return error_response(400, 'VALIDATION_ERROR', str(e))
    except ConflictError as e:
        return error_response(409, 'CONFLICT', str(e))
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return error_response(404, 'NOT_FOUND', 'Presentation not found')
        return error_response(500, 'INTERNAL_ERROR', str(e))
    except Exception as e:
        print(f"Unexpected error: {e}")
        return error_response(500, 'INTERNAL_ERROR', 'An unexpected error occurred')


def validate_presentation_id(presentation_id: str):
    """
    验证演示文稿ID格式
    """
    try:
        uuid.UUID(presentation_id)
    except ValueError:
        raise ValidationError('Invalid presentation ID format')


def get_presentation(presentation_id: str) -> Dict[str, Any]:
    """
    获取演示文稿信息
    """
    table = dynamodb.Table(PRESENTATIONS_TABLE)
    response = table.get_item(
        Key={'presentation_id': presentation_id}
    )

    if 'Item' not in response:
        raise ValidationError('Presentation not found')

    return response['Item']


def check_deletion_allowed(presentation: Dict[str, Any]):
    """
    检查是否允许删除
    """
    status = presentation.get('status')

    # 检查状态
    if status in ['processing', 'compiling']:
        raise ConflictError(
            f"Cannot delete presentation in {status} state. "
            "Use force=true to override."
        )

    # 检查锁状态
    if presentation.get('lock_token'):
        lock_expires = presentation.get('lock_expires', 0)
        if lock_expires > datetime.utcnow().timestamp():
            raise ConflictError(
                'Presentation is locked by another operation. '
                'Use force=true to override.'
            )


def mark_as_deleting(presentation_id: str):
    """
    标记演示文稿为删除中状态
    """
    table = dynamodb.Table(PRESENTATIONS_TABLE)

    try:
        table.update_item(
            Key={'presentation_id': presentation_id},
            UpdateExpression='SET #status = :status, deleted_at = :deleted_at',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'deleting',
                ':deleted_at': datetime.utcnow().isoformat()
            }
        )
    except ClientError as e:
        print(f"Error marking presentation as deleting: {e}")
        # 继续删除流程


def create_cleanup_task(presentation_id: str, presentation: Dict[str, Any]) -> str:
    """
    创建异步清理任务
    """
    task_id = str(uuid.uuid4())

    # 准备清理任务
    cleanup_task = {
        'task_id': task_id,
        'task_type': 'DELETE_PRESENTATION',
        'presentation_id': presentation_id,
        'created_at': datetime.utcnow().isoformat(),
        'resources': {
            's3_prefix': f"presentations/{presentation_id}/",
            'dynamodb_keys': [
                {'table': PRESENTATIONS_TABLE, 'key': {'presentation_id': presentation_id}}
            ],
            'related_tasks': get_related_tasks(presentation_id),
            'log_groups': [
                f"/aws/lambda/generate-ppt-{presentation_id}",
                f"/aws/lambda/compile-ppt-{presentation_id}"
            ]
        }
    }

    # 发送到SQS队列
    try:
        sqs.send_message(
            QueueUrl=CLEANUP_QUEUE_URL,
            MessageBody=json.dumps(cleanup_task),
            MessageAttributes={
                'task_type': {
                    'StringValue': 'DELETE_PRESENTATION',
                    'DataType': 'String'
                },
                'priority': {
                    'StringValue': 'low',
                    'DataType': 'String'
                }
            }
        )
    except ClientError as e:
        print(f"Error sending cleanup task to SQS: {e}")
        # 同步清理作为后备方案
        sync_cleanup(presentation_id)

    return task_id


def get_related_tasks(presentation_id: str) -> list:
    """
    获取相关任务ID
    """
    table = dynamodb.Table(TASKS_TABLE)

    try:
        response = table.query(
            IndexName='PresentationIndex',
            KeyConditionExpression='presentation_id = :pid',
            ExpressionAttributeValues={
                ':pid': presentation_id
            }
        )
        return [item['task_id'] for item in response.get('Items', [])]
    except:
        return []


def sync_cleanup(presentation_id: str):
    """
    同步清理资源（后备方案）
    """
    errors = []

    # 清理S3文件
    try:
        delete_s3_files(presentation_id)
    except Exception as e:
        errors.append(f"S3 cleanup error: {e}")

    # 清理DynamoDB记录
    try:
        delete_dynamodb_records(presentation_id)
    except Exception as e:
        errors.append(f"DynamoDB cleanup error: {e}")

    # 清理CloudWatch日志
    try:
        delete_cloudwatch_logs(presentation_id)
    except Exception as e:
        errors.append(f"CloudWatch cleanup error: {e}")

    if errors:
        print(f"Cleanup errors for {presentation_id}: {errors}")


def delete_s3_files(presentation_id: str):
    """
    删除S3中的文件
    """
    prefix = f"presentations/{presentation_id}/"

    # 列出所有对象
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)

    delete_keys = []
    for page in pages:
        for obj in page.get('Contents', []):
            delete_keys.append({'Key': obj['Key']})

            # 批量删除（每批最多1000个）
            if len(delete_keys) >= 1000:
                s3.delete_objects(
                    Bucket=S3_BUCKET,
                    Delete={'Objects': delete_keys}
                )
                delete_keys = []

    # 删除剩余的对象
    if delete_keys:
        s3.delete_objects(
            Bucket=S3_BUCKET,
            Delete={'Objects': delete_keys}
        )


def delete_dynamodb_records(presentation_id: str):
    """
    删除DynamoDB记录
    """
    # 删除主表记录
    presentations_table = dynamodb.Table(PRESENTATIONS_TABLE)
    presentations_table.delete_item(
        Key={'presentation_id': presentation_id}
    )

    # 删除相关任务记录
    tasks_table = dynamodb.Table(TASKS_TABLE)
    tasks = get_related_tasks(presentation_id)

    for task_id in tasks:
        try:
            tasks_table.delete_item(
                Key={'task_id': task_id}
            )
        except:
            pass


def delete_cloudwatch_logs(presentation_id: str):
    """
    删除CloudWatch日志
    """
    log_groups = [
        f"/aws/lambda/generate-ppt-{presentation_id}",
        f"/aws/lambda/compile-ppt-{presentation_id}",
        f"/aws/lambda/status-check-{presentation_id}"
    ]

    for log_group in log_groups:
        try:
            cloudwatch.delete_log_group(logGroupName=log_group)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                print(f"Error deleting log group {log_group}: {e}")


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