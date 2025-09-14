"""
下载处理Lambda函数 - 处理PPT文件下载请求（简化版）
"""
import json
import boto3
import logging
from botocore.exceptions import ClientError
import os

s3 = boto3.client('s3')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """下载处理Lambda函数"""
    try:
        logger.info("开始处理下载请求")

        # 获取环境变量
        bucket_name = os.environ.get('S3_BUCKET', 'ai-ppt-presentations-dev')

        # 提取presentation_id
        path_params = event.get('pathParameters', {})
        presentation_id = path_params.get('id') if path_params else None

        # 如果没有从pathParameters获取到，尝试从path中解析
        if not presentation_id:
            path = event.get('path', '')
            if '/download/' in path:
                parts = path.split('/download/')
                if len(parts) > 1:
                    presentation_id = parts[1].split('/')[0]

        if not presentation_id:
            logger.error("未提供presentation_id")
            return error_response(400, 'Presentation ID required')

        logger.info(f"处理下载请求，presentation_id: {presentation_id}")

        # 初始化S3客户端
        s3_client = boto3.client('s3')

        # 构建文件路径
        pptx_key = f"presentations/{presentation_id}/output/presentation.pptx"

        # 检查文件是否存在
        try:
            response = s3_client.head_object(Bucket=bucket_name, Key=pptx_key)
            file_size = response['ContentLength']
            last_modified = response['LastModified']

            logger.info(f"找到文件: {pptx_key}, 大小: {file_size} bytes")

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.warning(f"文件不存在: {pptx_key}")
                return error_response(404, 'Presentation file not found')
            else:
                logger.error(f"检查文件时出错: {str(e)}")
                return error_response(500, 'Error checking file availability')

        # 检查查询参数以确定返回类型
        query_params = event.get('queryStringParameters') or {}
        return_type = query_params.get('type', 'url')  # 默认返回URL
        expires_in = int(query_params.get('expires', 3600))  # 默认1小时

        # 限制过期时间（最大7天）
        expires_in = min(expires_in, 7 * 24 * 3600)

        if return_type == 'direct':
            # 直接返回文件内容（适用于小文件）
            try:
                if file_size > 10 * 1024 * 1024:  # 10MB限制
                    logger.warning(f"文件过大，不支持直接下载: {file_size} bytes")
                    return error_response(413, 'File too large for direct download')

                # 获取文件内容
                obj = s3_client.get_object(Bucket=bucket_name, Key=pptx_key)
                file_content = obj['Body'].read()

                # 返回二进制内容
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                        'Content-Disposition': f'attachment; filename="presentation_{presentation_id}.pptx"',
                        'Content-Length': str(len(file_content)),
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': file_content,
                    'isBase64Encoded': True
                }

            except Exception as e:
                logger.error(f"获取文件内容失败: {str(e)}")
                return error_response(500, 'Error retrieving file content')

        else:
            # 生成预签名下载URL（默认方式）
            try:
                download_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': bucket_name,
                        'Key': pptx_key,
                        'ResponseContentDisposition': f'attachment; filename="presentation_{presentation_id}.pptx"'
                    },
                    ExpiresIn=expires_in
                )

                logger.info(f"成功生成下载链接，有效期: {expires_in} 秒")

                # 获取状态信息（如果存在）
                status_info = {}
                try:
                    from src.status_manager import StatusManager
                    status_manager = StatusManager(bucket_name)
                    status = status_manager.get_status(presentation_id)
                    if status:
                        status_info = {
                            'topic': status.get('topic', ''),
                            'page_count': status.get('page_count', 0),
                            'created_at': status.get('created_at'),
                            'completion_time': status.get('updated_at')
                        }
                except Exception as e:
                    logger.warning(f"获取状态信息失败: {str(e)}")

                # 构建响应数据
                response_data = {
                    'presentation_id': presentation_id,
                    'download_url': download_url,
                    'expires_in': expires_in,
                    'expires_at': (last_modified.timestamp() + expires_in) if last_modified else None,
                    'file_size': file_size,
                    'file_type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    'filename': f'presentation_{presentation_id}.pptx'
                }

                # 添加状态信息
                if status_info:
                    response_data.update(status_info)

                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                    },
                    'body': json.dumps(response_data, ensure_ascii=False)
                }

            except Exception as e:
                logger.error(f"生成预签名URL失败: {str(e)}")
                return error_response(500, 'Error generating download URL')

    except Exception as e:
        logger.error(f"下载请求处理失败: {str(e)}")
        return error_response(500, 'Internal server error')


def error_response(status_code: int, message: str) -> dict:
    """构建错误响应"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps({'error': message})
    }


# 测试用的便利函数
def generate_download_url(presentation_id: str, s3_client=None, bucket_name: str = None,
                         expires_in: int = 3600) -> str:
    """生成下载URL（测试用）"""
    if not s3_client:
        s3_client = boto3.client('s3')

    if not bucket_name:
        bucket_name = 'ai-ppt-presentations-dev'

    pptx_key = f"presentations/{presentation_id}/output/presentation.pptx"

    return s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': bucket_name,
            'Key': pptx_key,
            'ResponseContentDisposition': f'attachment; filename="presentation_{presentation_id}.pptx"'
        },
        ExpiresIn=expires_in
    )


def handle_download_request(presentation_id: str, s3_client=None, bucket_name: str = None) -> dict:
    """处理下载请求（测试用）"""
    event = {
        'pathParameters': {'id': presentation_id},
        'httpMethod': 'GET'
    }

    if bucket_name:
        os.environ['S3_BUCKET'] = bucket_name

    return handler(event, None)


def generate_presigned_download_url(presentation_id: str, s3_client=None, bucket_name: str = None,
                                  expires_in: int = 3600) -> str:
    """生成预签名下载URL（测试兼容）"""
    return generate_download_url(presentation_id, s3_client, bucket_name, expires_in)


def check_file_availability(presentation_id: str, s3_client=None, bucket_name: str = None) -> dict:
    """检查文件可用性（测试用）"""
    if not s3_client:
        s3_client = boto3.client('s3')

    if not bucket_name:
        bucket_name = 'ai-ppt-presentations-dev'

    pptx_key = f"presentations/{presentation_id}/output/presentation.pptx"

    try:
        response = s3_client.head_object(Bucket=bucket_name, Key=pptx_key)
        return {
            'available': True,
            'file_size': response['ContentLength'],
            'last_modified': response['LastModified'].isoformat(),
            'content_type': response.get('ContentType', 'application/octet-stream')
        }
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return {'available': False, 'error': 'File not found'}
        else:
            return {'available': False, 'error': str(e)}
    except Exception as e:
        return {'available': False, 'error': str(e)}


def download_file_content(presentation_id: str, s3_client=None, bucket_name: str = None) -> bytes:
    """下载文件内容（测试用）"""
    if not s3_client:
        s3_client = boto3.client('s3')

    if not bucket_name:
        bucket_name = 'ai-ppt-presentations-dev'

    pptx_key = f"presentations/{presentation_id}/output/presentation.pptx"

    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=pptx_key)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"下载文件内容失败: {str(e)}")
        raise


def get_download_info(presentation_id: str, s3_client=None, bucket_name: str = None) -> dict:
    """获取下载信息（测试用）"""
    try:
        # 检查文件可用性
        file_info = check_file_availability(presentation_id, s3_client, bucket_name)

        if not file_info['available']:
            return {'error': file_info['error']}

        # 生成下载URL
        download_url = generate_download_url(presentation_id, s3_client, bucket_name)

        return {
            'presentation_id': presentation_id,
            'download_url': download_url,
            'file_size': file_info['file_size'],
            'last_modified': file_info['last_modified'],
            'content_type': file_info['content_type']
        }

    except Exception as e:
        return {'error': str(e)}


def batch_generate_download_urls(presentation_ids: list, s3_client=None,
                                bucket_name: str = None, expires_in: int = 3600) -> dict:
    """批量生成下载URL（测试用）"""
    results = {}
    errors = {}

    for presentation_id in presentation_ids:
        try:
            url = generate_download_url(presentation_id, s3_client, bucket_name, expires_in)
            results[presentation_id] = url
        except Exception as e:
            errors[presentation_id] = str(e)

    return {
        'successful': results,
        'failed': errors,
        'total_requested': len(presentation_ids),
        'successful_count': len(results),
        'failed_count': len(errors)
    }