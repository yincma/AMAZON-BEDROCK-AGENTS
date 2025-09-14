"""
AI PPT Assistant Phase 3 - 内容更新器

提供单页内容更新功能，支持乐观锁、版本控制和一致性保持。

功能特性：
- 单页内容更新
- ETag乐观锁机制
- 版本控制
- 数据验证
- 错误处理和恢复
"""

import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ContentUpdateError(Exception):
    """内容更新异常基类"""

    def __init__(self, message: str, error_code: str = "CONTENT_UPDATE_ERROR", details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ValidationError(ContentUpdateError):
    """数据验证错误"""

    def __init__(self, message: str, field_name: str = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field_name})
        self.field_name = field_name


class VersionConflictError(ContentUpdateError):
    """版本冲突错误"""

    def __init__(self, message: str, current_version: str, provided_version: str):
        super().__init__(message, "VERSION_CONFLICT", {
            "current_version": current_version,
            "provided_version": provided_version
        })


class PresentationNotFoundError(ContentUpdateError):
    """演示文稿未找到错误"""

    def __init__(self, presentation_id: str):
        super().__init__(f"Presentation {presentation_id} not found",
                         "PRESENTATION_NOT_FOUND", {"presentation_id": presentation_id})


class ContentUpdater:
    """内容更新器 - 负责单页内容更新逻辑

    功能：
    - 单页内容更新
    - 版本控制
    - 数据验证
    - 并发控制
    """

    def __init__(self, dynamodb_client=None, s3_client=None, bucket_name: str = None):
        """
        初始化内容更新器

        Args:
            dynamodb_client: DynamoDB客户端
            s3_client: S3客户端
            bucket_name: S3存储桶名称
        """
        self.dynamodb = dynamodb_client or boto3.client('dynamodb')
        self.s3_client = s3_client or boto3.client('s3')
        self.bucket_name = bucket_name or "ai-ppt-presentations"
        self.table_name = "ai-ppt-presentations"

        logger.info(f"ContentUpdater初始化完成，使用存储桶: {self.bucket_name}")

    def update_slide(self, presentation_id: str, slide_update: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新单页幻灯片内容

        Args:
            presentation_id: 演示文稿ID
            slide_update: 更新数据

        Returns:
            更新结果

        Raises:
            ValidationError: 数据验证错误
            PresentationNotFoundError: 演示文稿不存在
            VersionConflictError: 版本冲突
        """
        # 验证输入参数
        self._validate_update_request(slide_update)

        try:
            # 获取当前演示文稿数据
            presentation_data = self._get_presentation(presentation_id)

            # 验证幻灯片编号
            slide_number = slide_update["slide_number"]
            if slide_number <= 0 or slide_number > len(presentation_data["slides"]):
                raise ValidationError(f"Slide number {slide_number} does not exist")

            # 检查版本冲突
            if "version" in slide_update:
                self._check_version_conflict(presentation_data, slide_update["version"])

            # 执行更新
            updated_slide = self._perform_slide_update(presentation_data, slide_update)

            # 生成新的ETag
            etag = self._generate_etag(presentation_data)
            presentation_data["etag"] = etag
            presentation_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # 保存到存储
            self._save_presentation(presentation_data)

            logger.info(f"成功更新演示文稿 {presentation_id} 第 {slide_number} 页")

            return {
                "status": "success",
                "updated_slide": updated_slide,
                "presentation_id": presentation_id,
                "etag": etag,
                "updated_at": presentation_data["updated_at"]
            }

        except (ValidationError, PresentationNotFoundError, VersionConflictError):
            raise
        except Exception as e:
            logger.error(f"更新幻灯片时发生错误: {str(e)}")
            raise ContentUpdateError(f"Failed to update slide: {str(e)}") from e

    def _validate_update_request(self, slide_update: Dict[str, Any]) -> None:
        """验证更新请求"""
        if not isinstance(slide_update, dict):
            raise ValidationError("Update request must be a dictionary")

        if "slide_number" not in slide_update:
            raise ValidationError("Missing required field: slide_number", "slide_number")

        if not isinstance(slide_update["slide_number"], int):
            raise ValidationError("slide_number must be an integer", "slide_number")

        # 验证内容不为空（如果提供）
        if "content" in slide_update and not slide_update["content"]:
            raise ValidationError("Content cannot be empty", "content")

        # 验证内容长度
        if "content" in slide_update:
            content = slide_update["content"]
            if isinstance(content, list):
                total_length = sum(len(str(item)) for item in content)
                if total_length > 2000:  # 内容过长限制
                    raise ValidationError("Content too long for slide format", "content")
            elif isinstance(content, str) and len(content) > 2000:
                raise ValidationError("Content too long for slide format", "content")

    def _get_presentation(self, presentation_id: str) -> Dict[str, Any]:
        """从存储中获取演示文稿数据"""
        try:
            # 先尝试从DynamoDB获取
            response = self.dynamodb.get_item(
                TableName=self.table_name,
                Key={'presentation_id': {'S': presentation_id}}
            )

            if 'Item' in response:
                return self._deserialize_dynamodb_item(response['Item'])

            # 如果DynamoDB没有，尝试从S3获取
            try:
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=f"presentations/{presentation_id}.json"
                )
                data = json.loads(response['Body'].read().decode('utf-8'))
                return data
            except ClientError as s3_error:
                if s3_error.response['Error']['Code'] == 'NoSuchKey':
                    raise PresentationNotFoundError(presentation_id)
                raise

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise PresentationNotFoundError(presentation_id)
            raise ContentUpdateError(f"Failed to retrieve presentation: {str(e)}")

    def _check_version_conflict(self, presentation_data: Dict[str, Any], provided_version: str) -> None:
        """检查版本冲突"""
        current_version = presentation_data.get("version", "1.0")
        if current_version != provided_version:
            raise VersionConflictError(
                f"Version conflict detected. Current version is {current_version}, provided version is {provided_version}",
                current_version,
                provided_version
            )

    def _perform_slide_update(self, presentation_data: Dict[str, Any], slide_update: Dict[str, Any]) -> Dict[str, Any]:
        """执行幻灯片更新"""
        slide_number = slide_update["slide_number"]
        slide_index = slide_number - 1

        # 获取当前幻灯片数据
        current_slide = presentation_data["slides"][slide_index].copy()

        # 更新字段
        for field in ["title", "content", "speaker_notes", "layout"]:
            if field in slide_update:
                current_slide[field] = slide_update[field]

        # 保持其他字段不变（如image_url等）
        current_slide["slide_number"] = slide_number
        current_slide["updated_at"] = datetime.now(timezone.utc).isoformat()

        # 更新演示文稿数据中的幻灯片
        presentation_data["slides"][slide_index] = current_slide

        return current_slide

    def _generate_etag(self, presentation_data: Dict[str, Any]) -> str:
        """生成ETag用于乐观锁"""
        # 使用演示文稿ID和更新时间生成ETag
        content = f"{presentation_data.get('presentation_id', '')}-{datetime.now(timezone.utc).isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()

    def _save_presentation(self, presentation_data: Dict[str, Any]) -> None:
        """保存演示文稿到存储"""
        presentation_id = presentation_data["presentation_id"]

        try:
            # 保存到S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"presentations/{presentation_id}.json",
                Body=json.dumps(presentation_data, ensure_ascii=False, indent=2),
                ContentType="application/json"
            )

            # 同时更新DynamoDB记录（如果存在的话）
            try:
                self._update_dynamodb_record(presentation_data)
            except Exception as e:
                logger.warning(f"更新DynamoDB记录失败，但S3更新成功: {str(e)}")

        except ClientError as e:
            logger.error(f"保存演示文稿失败: {str(e)}")
            raise ContentUpdateError("S3 storage unavailable") from e

    def _update_dynamodb_record(self, presentation_data: Dict[str, Any]) -> None:
        """更新DynamoDB记录"""
        try:
            self.dynamodb.put_item(
                TableName=self.table_name,
                Item=self._serialize_for_dynamodb(presentation_data)
            )
        except Exception as e:
            logger.warning(f"DynamoDB更新失败: {str(e)}")

    def _serialize_for_dynamodb(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """序列化数据用于DynamoDB存储"""
        def serialize_value(value):
            if isinstance(value, str):
                return {'S': value}
            elif isinstance(value, (int, float)):
                return {'N': str(value)}
            elif isinstance(value, bool):
                return {'BOOL': value}
            elif isinstance(value, list):
                return {'L': [serialize_value(item) for item in value]}
            elif isinstance(value, dict):
                return {'M': {k: serialize_value(v) for k, v in value.items()}}
            else:
                return {'S': str(value)}

        return {key: serialize_value(value) for key, value in data.items()}

    def _deserialize_dynamodb_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """反序列化DynamoDB项"""
        def deserialize_value(value):
            if 'S' in value:
                return value['S']
            elif 'N' in value:
                return float(value['N']) if '.' in value['N'] else int(value['N'])
            elif 'BOOL' in value:
                return value['BOOL']
            elif 'L' in value:
                return [deserialize_value(item) for item in value['L']]
            elif 'M' in value:
                return {k: deserialize_value(v) for k, v in value['M'].items()}
            else:
                return str(value)

        return {key: deserialize_value(value) for key, value in item.items()}


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda处理函数

    Args:
        event: Lambda事件数据
        context: Lambda上下文

    Returns:
        API Gateway响应
    """
    try:
        # 解析请求
        presentation_id = event['pathParameters']['presentation_id']
        slide_number = int(event['pathParameters']['slide_number'])

        # 解析请求体
        body = json.loads(event.get('body', '{}'))
        body['slide_number'] = slide_number

        # 处理If-Match头（ETag）
        headers = event.get('headers', {})
        if 'If-Match' in headers:
            body['version'] = headers['If-Match']

        # 创建更新器并执行更新
        updater = ContentUpdater()
        result = updater.update_slide(presentation_id, body)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'ETag': result['etag']
            },
            'body': json.dumps(result, ensure_ascii=False)
        }

    except ValidationError as e:
        logger.error(f"验证错误: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': e.error_code,
                'message': str(e),
                'details': e.details
            }, ensure_ascii=False)
        }

    except VersionConflictError as e:
        logger.error(f"版本冲突: {str(e)}")
        return {
            'statusCode': 412,  # Precondition Failed
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': e.error_code,
                'message': str(e),
                'details': e.details
            }, ensure_ascii=False)
        }

    except PresentationNotFoundError as e:
        logger.error(f"演示文稿未找到: {str(e)}")
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': e.error_code,
                'message': str(e),
                'details': e.details
            }, ensure_ascii=False)
        }

    except TimeoutError as e:
        logger.error(f"操作超时: {str(e)}")
        return {
            'statusCode': 408,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'TIMEOUT_ERROR',
                'message': 'Update operation timed out after 30 seconds'
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"未预期错误: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred'
            }, ensure_ascii=False)
        }


if __name__ == "__main__":
    # 本地测试代码
    test_presentation_data = {
        "presentation_id": "test-ppt-123",
        "topic": "AI技术发展趋势",
        "status": "completed",
        "slides": [
            {
                "slide_number": 1,
                "title": "AI技术概述",
                "content": ["人工智能定义", "发展历程", "核心技术"],
                "image_url": "s3://bucket/images/slide1.jpg",
                "speaker_notes": "这是第一页的演讲备注"
            },
            {
                "slide_number": 2,
                "title": "机器学习",
                "content": ["监督学习", "无监督学习", "强化学习"],
                "image_url": "s3://bucket/images/slide2.jpg",
                "speaker_notes": "这是第二页的演讲备注"
            }
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    print("测试内容更新器:")

    # 模拟更新请求
    update_request = {
        "slide_number": 2,
        "title": "深度学习技术",
        "content": ["神经网络", "卷积网络", "循环网络", "Transformer"]
    }

    try:
        updater = ContentUpdater()

        # 模拟保存测试数据到文件
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(test_presentation_data, f, ensure_ascii=False, indent=2)
            test_file = f.name

        print(f"创建测试文件: {test_file}")
        print(f"更新请求: {update_request}")

    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")