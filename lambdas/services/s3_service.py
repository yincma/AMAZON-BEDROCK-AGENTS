"""
统一的S3服务模块
提供S3操作的标准化接口
"""

import json
import boto3
import logging
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError
import mimetypes

logger = logging.getLogger(__name__)


class S3ServiceError(Exception):
    """S3服务错误"""
    def __init__(self, message: str, error_code: str = None, details: Any = None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class S3Service:
    """S3服务封装类"""

    def __init__(self, bucket_name: str, s3_client=None):
        """
        初始化S3服务

        Args:
            bucket_name: S3存储桶名称
            s3_client: 可选的S3客户端实例
        """
        self.bucket_name = bucket_name
        self.s3_client = s3_client or boto3.client('s3')
        self.logger = logging.getLogger(self.__class__.__name__)

    def upload_json(self, key: str, data: Dict, metadata: Dict = None) -> str:
        """
        上传JSON数据到S3

        Args:
            key: S3对象键
            data: 要上传的数据字典
            metadata: 可选的元数据

        Returns:
            S3对象的ETag

        Raises:
            S3ServiceError: 上传失败时抛出
        """
        try:
            json_data = json.dumps(data, ensure_ascii=False, default=str)

            put_kwargs = {
                'Bucket': self.bucket_name,
                'Key': key,
                'Body': json_data,
                'ContentType': 'application/json'
            }

            if metadata:
                put_kwargs['Metadata'] = {k: str(v) for k, v in metadata.items()}

            response = self.s3_client.put_object(**put_kwargs)
            self.logger.info(f"Successfully uploaded JSON to s3://{self.bucket_name}/{key}")
            return response['ETag']

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to upload JSON to S3: {error_code} - {error_message}")
            raise S3ServiceError(f"Failed to upload JSON: {error_message}", error_code, {'key': key})

    def download_json(self, key: str) -> Dict:
        """
        从S3下载JSON数据

        Args:
            key: S3对象键

        Returns:
            解析后的JSON数据

        Raises:
            S3ServiceError: 下载失败时抛出
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8')
            self.logger.info(f"Successfully downloaded JSON from s3://{self.bucket_name}/{key}")
            return json.loads(content)

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                self.logger.warning(f"Object not found: s3://{self.bucket_name}/{key}")
                raise S3ServiceError(f"Object not found: {key}", 'NOT_FOUND', {'key': key})
            else:
                error_message = e.response['Error']['Message']
                self.logger.error(f"Failed to download JSON from S3: {error_code} - {error_message}")
                raise S3ServiceError(f"Failed to download JSON: {error_message}", error_code, {'key': key})

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from s3://{self.bucket_name}/{key}: {str(e)}")
            raise S3ServiceError(f"Invalid JSON content in object: {key}", 'INVALID_JSON', {'key': key})

    def upload_file(self, key: str, file_path: str, content_type: str = None, metadata: Dict = None) -> str:
        """
        上传文件到S3

        Args:
            key: S3对象键
            file_path: 本地文件路径
            content_type: 内容类型（可选，自动检测）
            metadata: 可选的元数据

        Returns:
            S3对象的ETag

        Raises:
            S3ServiceError: 上传失败时抛出
        """
        try:
            # 自动检测内容类型
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_path)
                content_type = content_type or 'application/octet-stream'

            extra_args = {'ContentType': content_type}
            if metadata:
                extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}

            self.s3_client.upload_file(file_path, self.bucket_name, key, ExtraArgs=extra_args)
            self.logger.info(f"Successfully uploaded file to s3://{self.bucket_name}/{key}")

            # 获取ETag
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return response['ETag']

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to upload file to S3: {error_code} - {error_message}")
            raise S3ServiceError(f"Failed to upload file: {error_message}", error_code, {'key': key, 'file_path': file_path})

        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            raise S3ServiceError(f"File not found: {file_path}", 'FILE_NOT_FOUND', {'file_path': file_path})

    def download_file(self, key: str, file_path: str) -> None:
        """
        从S3下载文件

        Args:
            key: S3对象键
            file_path: 本地文件保存路径

        Raises:
            S3ServiceError: 下载失败时抛出
        """
        try:
            self.s3_client.download_file(self.bucket_name, key, file_path)
            self.logger.info(f"Successfully downloaded file from s3://{self.bucket_name}/{key} to {file_path}")

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                self.logger.warning(f"Object not found: s3://{self.bucket_name}/{key}")
                raise S3ServiceError(f"Object not found: {key}", 'NOT_FOUND', {'key': key})
            else:
                error_message = e.response['Error']['Message']
                self.logger.error(f"Failed to download file from S3: {error_code} - {error_message}")
                raise S3ServiceError(f"Failed to download file: {error_message}", error_code, {'key': key})

    def object_exists(self, key: str) -> bool:
        """
        检查S3对象是否存在

        Args:
            key: S3对象键

        Returns:
            True如果对象存在，否则False
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                self.logger.error(f"Error checking object existence: {str(e)}")
                raise S3ServiceError(f"Failed to check object existence: {str(e)}", 'CHECK_FAILED', {'key': key})

    def generate_presigned_url(self, key: str, expiration: int = 3600, http_method: str = 'GET') -> str:
        """
        生成预签名URL

        Args:
            key: S3对象键
            expiration: URL过期时间（秒）
            http_method: HTTP方法（GET或PUT）

        Returns:
            预签名URL

        Raises:
            S3ServiceError: 生成失败时抛出
        """
        try:
            client_method = 'get_object' if http_method == 'GET' else 'put_object'
            url = self.s3_client.generate_presigned_url(
                ClientMethod=client_method,
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            self.logger.info(f"Generated presigned URL for s3://{self.bucket_name}/{key} (expires in {expiration}s)")
            return url

        except ClientError as e:
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to generate presigned URL: {error_message}")
            raise S3ServiceError(f"Failed to generate presigned URL: {error_message}", 'URL_GENERATION_FAILED', {'key': key})

    def delete_object(self, key: str) -> None:
        """
        删除S3对象

        Args:
            key: S3对象键

        Raises:
            S3ServiceError: 删除失败时抛出
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            self.logger.info(f"Successfully deleted s3://{self.bucket_name}/{key}")

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to delete object: {error_code} - {error_message}")
            raise S3ServiceError(f"Failed to delete object: {error_message}", error_code, {'key': key})

    def list_objects(self, prefix: str = '', max_keys: int = 1000) -> List[Dict]:
        """
        列出S3对象

        Args:
            prefix: 对象键前缀
            max_keys: 最大返回数量

        Returns:
            对象列表

        Raises:
            S3ServiceError: 列出失败时抛出
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                PaginationConfig={'MaxItems': max_keys}
            )

            objects = []
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'etag': obj['ETag']
                        })

            self.logger.info(f"Listed {len(objects)} objects with prefix '{prefix}'")
            return objects

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to list objects: {error_code} - {error_message}")
            raise S3ServiceError(f"Failed to list objects: {error_message}", error_code, {'prefix': prefix})

    def copy_object(self, source_key: str, dest_key: str, source_bucket: str = None) -> str:
        """
        复制S3对象

        Args:
            source_key: 源对象键
            dest_key: 目标对象键
            source_bucket: 源存储桶（可选，默认使用当前存储桶）

        Returns:
            新对象的ETag

        Raises:
            S3ServiceError: 复制失败时抛出
        """
        try:
            source_bucket = source_bucket or self.bucket_name
            copy_source = {'Bucket': source_bucket, 'Key': source_key}

            response = self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_key
            )

            self.logger.info(f"Successfully copied s3://{source_bucket}/{source_key} to s3://{self.bucket_name}/{dest_key}")
            return response['CopyObjectResult']['ETag']

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                self.logger.warning(f"Source object not found: s3://{source_bucket}/{source_key}")
                raise S3ServiceError(f"Source object not found: {source_key}", 'NOT_FOUND', {'key': source_key})
            else:
                error_message = e.response['Error']['Message']
                self.logger.error(f"Failed to copy object: {error_code} - {error_message}")
                raise S3ServiceError(f"Failed to copy object: {error_message}", error_code, {
                    'source_key': source_key,
                    'dest_key': dest_key
                })

    def get_object_metadata(self, key: str) -> Dict:
        """
        获取对象元数据

        Args:
            key: S3对象键

        Returns:
            对象元数据字典

        Raises:
            S3ServiceError: 获取失败时抛出
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)

            metadata = {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified').isoformat() if response.get('LastModified') else None,
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {})
            }

            self.logger.info(f"Retrieved metadata for s3://{self.bucket_name}/{key}")
            return metadata

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                self.logger.warning(f"Object not found: s3://{self.bucket_name}/{key}")
                raise S3ServiceError(f"Object not found: {key}", 'NOT_FOUND', {'key': key})
            else:
                error_message = e.response['Error']['Message']
                self.logger.error(f"Failed to get object metadata: {error_code} - {error_message}")
                raise S3ServiceError(f"Failed to get object metadata: {error_message}", error_code, {'key': key})

    def batch_delete_objects(self, keys: List[str]) -> Dict:
        """
        批量删除S3对象

        Args:
            keys: 要删除的对象键列表

        Returns:
            删除结果字典

        Raises:
            S3ServiceError: 删除失败时抛出
        """
        if not keys:
            return {'deleted': [], 'errors': []}

        try:
            delete_objects = [{'Key': key} for key in keys]

            response = self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': delete_objects}
            )

            result = {
                'deleted': [d['Key'] for d in response.get('Deleted', [])],
                'errors': [{'key': e['Key'], 'code': e['Code'], 'message': e['Message']}
                          for e in response.get('Errors', [])]
            }

            self.logger.info(f"Batch deleted {len(result['deleted'])} objects, {len(result['errors'])} errors")
            return result

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            self.logger.error(f"Failed to batch delete objects: {error_code} - {error_message}")
            raise S3ServiceError(f"Failed to batch delete objects: {error_message}", error_code, {'keys': keys})