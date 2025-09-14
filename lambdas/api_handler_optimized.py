"""
优化后的统一API处理器
处理所有PPT生成相关的API请求
"""

import json
import uuid
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 导入基础模块
from utils.api_base import (
    APIHandler as BaseAPIHandler,
    RequestValidator,
    ResponseBuilder,
    ValidationError,
    ResourceNotFoundError,
    HttpStatus,
    ErrorCode,
    validate_request,
    with_error_handling
)
from services.s3_service import S3Service, S3ServiceError
from services.dynamodb_service import DynamoDBService, DynamoDBServiceError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class PPTConfig:
    """PPT生成配置"""
    MIN_PAGE_COUNT = 3
    MAX_PAGE_COUNT = 20
    DEFAULT_PAGE_COUNT = 10
    MIN_TOPIC_LENGTH = 3
    MAX_TOPIC_LENGTH = 200
    DOWNLOAD_URL_EXPIRY = 3600  # 1小时

    # S3路径模板
    STATUS_FILE_TEMPLATE = "presentations/{presentation_id}/status.json"
    CONTENT_FILE_TEMPLATE = "presentations/{presentation_id}/content.json"
    PPTX_FILE_TEMPLATE = "presentations/{presentation_id}/output/presentation.pptx"

    # 状态值
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"


class PPTAPIHandler(BaseAPIHandler):
    """PPT生成API处理器"""

    def __init__(self):
        super().__init__()
        self.bucket_name = os.environ.get('S3_BUCKET', 'ai-ppt-presentations-dev')
        self.table_name = os.environ.get('DYNAMODB_TABLE', 'ai-ppt-presentations')

        self.s3_service = S3Service(self.bucket_name)
        self.dynamodb_service = DynamoDBService(self.table_name)

    def _route_request(self, event: Dict, context: Any) -> Dict:
        """路由请求到对应的处理方法"""
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')

        # 定义路由映射
        routes = {
            ('POST', '/generate'): self.handle_generate,
            ('GET', '/status'): self.handle_status,
            ('GET', '/download'): self.handle_download,
            ('DELETE', '/presentations'): self.handle_delete,
            ('GET', '/presentations'): self.handle_list,
            ('PUT', '/presentations'): self.handle_update
        }

        # 处理带路径参数的路由
        if path.startswith('/status/'):
            return self.handle_status(event)
        elif path.startswith('/download/'):
            return self.handle_download(event)
        elif path.startswith('/presentations/') and http_method == 'DELETE':
            return self.handle_delete(event)
        elif path.startswith('/presentations/') and http_method == 'PUT':
            return self.handle_update(event)

        # 查找精确匹配的路由
        handler = routes.get((http_method, path))
        if handler:
            return handler(event)

        # 未找到路由
        return self.response_builder.error_response(
            HttpStatus.NOT_FOUND.value,
            ErrorCode.RESOURCE_NOT_FOUND.value,
            f"Endpoint not found: {http_method} {path}"
        )

    @validate_request(
        body_required=True,
        required_fields=['topic']
    )
    def handle_generate(self, event: Dict) -> Dict:
        """
        处理PPT生成请求
        POST /generate
        """
        body = event['parsed_body']
        topic = body['topic']
        page_count = body.get('page_count', PPTConfig.DEFAULT_PAGE_COUNT)
        style = body.get('style', 'professional')
        language = body.get('language', 'zh')

        # 验证参数
        self.validator.validate_string_length(topic, 'topic', PPTConfig.MIN_TOPIC_LENGTH, PPTConfig.MAX_TOPIC_LENGTH)
        self.validator.validate_number_range(page_count, 'page_count', PPTConfig.MIN_PAGE_COUNT, PPTConfig.MAX_PAGE_COUNT)
        self.validator.validate_enum_value(style, 'style', ['professional', 'creative', 'minimal', 'consultant'])
        self.validator.validate_enum_value(language, 'language', ['zh', 'en', 'ja', 'ko'])

        # 生成唯一ID
        presentation_id = str(uuid.uuid4())

        # 创建初始记录
        initial_data = {
            'presentation_id': presentation_id,
            'topic': topic,
            'page_count': page_count,
            'style': style,
            'language': language,
            'status': PPTConfig.STATUS_PENDING,
            'progress': 0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'user_id': event.get('requestContext', {}).get('identity', {}).get('userArn', 'anonymous')
        }

        try:
            # 保存到DynamoDB
            self.dynamodb_service.put_item(initial_data)

            # 保存状态到S3
            status_key = PPTConfig.STATUS_FILE_TEMPLATE.format(presentation_id=presentation_id)
            self.s3_service.upload_json(status_key, initial_data)

            # TODO: 触发异步处理（Step Functions或SQS）
            # self._trigger_async_processing(presentation_id, initial_data)

            return self.response_builder.success_response(
                HttpStatus.ACCEPTED.value,
                {
                    'presentation_id': presentation_id,
                    'status': PPTConfig.STATUS_PENDING,
                    'topic': topic,
                    'page_count': page_count,
                    'estimated_completion_time': page_count * 3  # 估算每页3秒
                },
                "PPT generation started successfully"
            )

        except (DynamoDBServiceError, S3ServiceError) as e:
            self.logger.error(f"Failed to save initial data: {str(e)}")
            raise

    @validate_request(
        path_params={'id': {'type': 'uuid'}}
    )
    def handle_status(self, event: Dict) -> Dict:
        """
        处理状态查询请求
        GET /status/{id}
        """
        presentation_id = event.get('pathParameters', {}).get('id')

        if not presentation_id:
            # 尝试从路径中解析
            path = event.get('path', '')
            if '/status/' in path:
                presentation_id = path.split('/status/')[1].split('/')[0]

        if not presentation_id:
            raise ValidationError("Presentation ID is required", "id")

        # 优先从DynamoDB查询
        try:
            item = self.dynamodb_service.get_item({'presentation_id': presentation_id})
            if item:
                return self.response_builder.success_response(
                    HttpStatus.OK.value,
                    self._format_status_response(item)
                )
        except DynamoDBServiceError as e:
            self.logger.warning(f"Failed to query DynamoDB: {str(e)}")

        # 备选：从S3查询
        try:
            status_key = PPTConfig.STATUS_FILE_TEMPLATE.format(presentation_id=presentation_id)
            status_data = self.s3_service.download_json(status_key)
            return self.response_builder.success_response(
                HttpStatus.OK.value,
                self._format_status_response(status_data)
            )
        except S3ServiceError as e:
            if e.error_code == 'NOT_FOUND':
                raise ResourceNotFoundError("Presentation", presentation_id)
            raise

    @validate_request(
        path_params={'id': {'type': 'uuid'}},
        query_params={
            'format': {'enum': ['url', 'direct'], 'required': False},
            'expires': {'type': 'int', 'required': False}
        }
    )
    def handle_download(self, event: Dict) -> Dict:
        """
        处理下载请求
        GET /download/{id}
        """
        presentation_id = event.get('pathParameters', {}).get('id')

        if not presentation_id:
            # 尝试从路径中解析
            path = event.get('path', '')
            if '/download/' in path:
                presentation_id = path.split('/download/')[1].split('/')[0]

        if not presentation_id:
            raise ValidationError("Presentation ID is required", "id")

        query_params = event.get('queryStringParameters', {}) or {}
        format_type = query_params.get('format', 'url')
        expires_in = min(int(query_params.get('expires', PPTConfig.DOWNLOAD_URL_EXPIRY)), 7 * 24 * 3600)

        # 检查文件是否存在
        pptx_key = PPTConfig.PPTX_FILE_TEMPLATE.format(presentation_id=presentation_id)

        if not self.s3_service.object_exists(pptx_key):
            # 检查presentation是否存在
            status_key = PPTConfig.STATUS_FILE_TEMPLATE.format(presentation_id=presentation_id)
            if not self.s3_service.object_exists(status_key):
                raise ResourceNotFoundError("Presentation", presentation_id)
            else:
                return self.response_builder.error_response(
                    HttpStatus.UNPROCESSABLE_ENTITY.value,
                    "FILE_NOT_READY",
                    "Presentation file is not ready yet",
                    {'presentation_id': presentation_id, 'status': 'processing'}
                )

        if format_type == 'url':
            # 生成预签名URL
            download_url = self.s3_service.generate_presigned_url(pptx_key, expires_in)

            return self.response_builder.success_response(
                HttpStatus.OK.value,
                {
                    'presentation_id': presentation_id,
                    'download_url': download_url,
                    'expires_in': expires_in,
                    'file_name': f"presentation_{presentation_id}.pptx"
                }
            )
        else:
            # 直接返回文件内容（仅适用于小文件）
            metadata = self.s3_service.get_object_metadata(pptx_key)
            if metadata['content_length'] > 10 * 1024 * 1024:  # 10MB限制
                return self.response_builder.error_response(
                    HttpStatus.PAYLOAD_TOO_LARGE.value,
                    "FILE_TOO_LARGE",
                    "File is too large for direct download. Please use URL format.",
                    {'file_size': metadata['content_length'], 'max_size': 10 * 1024 * 1024}
                )

            # TODO: 实现直接文件下载
            return self.response_builder.error_response(
                HttpStatus.NOT_IMPLEMENTED.value,
                "NOT_IMPLEMENTED",
                "Direct download not implemented yet"
            )

    @validate_request(
        path_params={'id': {'type': 'uuid'}},
        query_params={'force': {'type': 'bool', 'required': False}}
    )
    def handle_delete(self, event: Dict) -> Dict:
        """
        处理删除请求
        DELETE /presentations/{id}
        """
        presentation_id = event.get('pathParameters', {}).get('id')

        if not presentation_id:
            # 尝试从路径中解析
            path = event.get('path', '')
            if '/presentations/' in path:
                presentation_id = path.split('/presentations/')[1].split('/')[0]

        if not presentation_id:
            raise ValidationError("Presentation ID is required", "id")

        query_params = event.get('queryStringParameters', {}) or {}
        force_delete = query_params.get('force', False)

        try:
            # 获取presentation信息
            item = self.dynamodb_service.get_item({'presentation_id': presentation_id})
            if not item:
                raise ResourceNotFoundError("Presentation", presentation_id)

            # 检查是否可以删除
            if not force_delete and item.get('status') == PPTConfig.STATUS_PROCESSING:
                return self.response_builder.error_response(
                    HttpStatus.CONFLICT.value,
                    ErrorCode.OPERATION_NOT_ALLOWED.value,
                    "Cannot delete presentation while it's being processed",
                    {'presentation_id': presentation_id, 'status': item['status']}
                )

            # 删除S3对象
            s3_keys = [
                PPTConfig.STATUS_FILE_TEMPLATE.format(presentation_id=presentation_id),
                PPTConfig.CONTENT_FILE_TEMPLATE.format(presentation_id=presentation_id),
                PPTConfig.PPTX_FILE_TEMPLATE.format(presentation_id=presentation_id)
            ]

            delete_results = self.s3_service.batch_delete_objects(s3_keys)

            # 删除DynamoDB记录
            self.dynamodb_service.delete_item({'presentation_id': presentation_id})

            return self.response_builder.success_response(
                HttpStatus.NO_CONTENT.value,
                None,
                "Presentation deleted successfully"
            )

        except (DynamoDBServiceError, S3ServiceError) as e:
            self.logger.error(f"Failed to delete presentation: {str(e)}")
            raise

    def handle_list(self, event: Dict) -> Dict:
        """
        处理列表查询请求
        GET /presentations
        """
        query_params = event.get('queryStringParameters', {}) or {}
        limit = min(int(query_params.get('limit', 20)), 100)
        status_filter = query_params.get('status')

        try:
            if status_filter:
                # 使用过滤条件扫描
                items = self.dynamodb_service.scan(
                    filter_expression='#status = :status',
                    expression_attribute_values={':status': status_filter},
                    limit=limit
                )
            else:
                # 扫描所有项目
                items = self.dynamodb_service.scan(limit=limit)

            # 格式化响应
            presentations = [self._format_list_item(item) for item in items]

            return self.response_builder.success_response(
                HttpStatus.OK.value,
                {
                    'presentations': presentations,
                    'count': len(presentations),
                    'limit': limit
                }
            )

        except DynamoDBServiceError as e:
            self.logger.error(f"Failed to list presentations: {str(e)}")
            raise

    @validate_request(
        path_params={'id': {'type': 'uuid'}},
        body_required=True
    )
    def handle_update(self, event: Dict) -> Dict:
        """
        处理更新请求
        PUT /presentations/{id}
        """
        presentation_id = event.get('pathParameters', {}).get('id')
        body = event['parsed_body']

        # 只允许更新特定字段
        allowed_updates = ['topic', 'style', 'language']
        updates = {k: v for k, v in body.items() if k in allowed_updates}

        if not updates:
            raise ValidationError("No valid fields to update", "body")

        try:
            # 更新DynamoDB记录
            updated_item = self.dynamodb_service.update_item(
                {'presentation_id': presentation_id},
                updates
            )

            # 同步更新S3状态文件
            status_key = PPTConfig.STATUS_FILE_TEMPLATE.format(presentation_id=presentation_id)
            self.s3_service.upload_json(status_key, updated_item)

            return self.response_builder.success_response(
                HttpStatus.OK.value,
                self._format_status_response(updated_item),
                "Presentation updated successfully"
            )

        except DynamoDBServiceError as e:
            if e.error_code == 'NOT_FOUND':
                raise ResourceNotFoundError("Presentation", presentation_id)
            raise

    def _format_status_response(self, item: Dict) -> Dict:
        """格式化状态响应"""
        return {
            'presentation_id': item['presentation_id'],
            'topic': item.get('topic'),
            'status': item.get('status'),
            'progress': item.get('progress', 0),
            'page_count': item.get('page_count'),
            'style': item.get('style'),
            'language': item.get('language'),
            'created_at': item.get('created_at'),
            'updated_at': item.get('updated_at'),
            'download_ready': item.get('status') == PPTConfig.STATUS_COMPLETED,
            'error_message': item.get('error_message')
        }

    def _format_list_item(self, item: Dict) -> Dict:
        """格式化列表项"""
        return {
            'presentation_id': item['presentation_id'],
            'topic': item.get('topic'),
            'status': item.get('status'),
            'page_count': item.get('page_count'),
            'created_at': item.get('created_at')
        }


def lambda_handler(event, context):
    """Lambda入口函数"""
    handler = PPTAPIHandler()
    return handler.handle_request(event, context)


# 用于本地测试的辅助函数
if __name__ == "__main__":
    # 测试生成请求
    test_event = {
        'httpMethod': 'POST',
        'path': '/generate',
        'body': json.dumps({
            'topic': '人工智能在医疗领域的应用',
            'page_count': 10,
            'style': 'professional',
            'language': 'zh'
        })
    }

    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2, ensure_ascii=False))