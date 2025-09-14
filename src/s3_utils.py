"""
S3工具类 - 提供S3操作的辅助功能
"""

import boto3
import json
import logging
from typing import Dict, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class S3Helper:
    """S3操作辅助类"""

    def __init__(self, bucket_name: str, region_name: str = 'us-east-1'):
        """
        初始化S3Helper

        Args:
            bucket_name: S3存储桶名称
            region_name: AWS区域名称
        """
        self.bucket_name = bucket_name
        self.region_name = region_name

        try:
            self.s3_client = boto3.client('s3', region_name=region_name)
            logger.info(f"Initialized S3Helper for bucket: {bucket_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise

    def read_json(self, key: str) -> Dict[str, Any]:
        """
        从S3读取JSON文件

        Args:
            key: S3对象键

        Returns:
            Dict: 解析后的JSON数据

        Raises:
            ClientError: S3操作失败
            json.JSONDecodeError: JSON解析失败
        """
        try:
            logger.info(f"Reading JSON from S3: s3://{self.bucket_name}/{key}")

            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )

            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)

            logger.info(f"Successfully read JSON from S3: {key}")
            return data

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.error(f"S3 object not found: {key}")
            elif error_code == 'NoSuchBucket':
                logger.error(f"S3 bucket not found: {self.bucket_name}")
            else:
                logger.error(f"S3 client error reading {key}: {e}")
            raise

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {key}: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error reading {key}: {e}")
            raise

    def write_json(self, key: str, data: Dict[str, Any]) -> bool:
        """
        写入JSON数据到S3

        Args:
            key: S3对象键
            data: 要写入的数据

        Returns:
            bool: 写入是否成功
        """
        try:
            json_content = json.dumps(data, ensure_ascii=False, indent=2)

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_content.encode('utf-8'),
                ContentType='application/json'
            )

            logger.info(f"Successfully wrote JSON to S3: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to write JSON to S3 {key}: {e}")
            return False

    def upload_file(self, file_path: str, key: str, content_type: Optional[str] = None) -> bool:
        """
        上传文件到S3

        Args:
            file_path: 本地文件路径
            key: S3对象键
            content_type: MIME类型

        Returns:
            bool: 上传是否成功
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )

            logger.info(f"Successfully uploaded file to S3: {file_path} -> s3://{self.bucket_name}/{key}")
            return True

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return False

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            return False

    def upload_bytes(self, data: bytes, key: str, content_type: str) -> bool:
        """
        上传字节数据到S3

        Args:
            data: 字节数据
            key: S3对象键
            content_type: MIME类型

        Returns:
            bool: 上传是否成功
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type
            )

            logger.info(f"Successfully uploaded {len(data)} bytes to S3: s3://{self.bucket_name}/{key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to upload bytes to S3: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error uploading bytes: {e}")
            return False

    def generate_presigned_url(self, key: str, expires_in: int = 3600, method: str = 'get_object') -> Optional[str]:
        """
        生成预签名URL

        Args:
            key: S3对象键
            expires_in: URL有效期（秒）
            method: HTTP方法 ('get_object' 或 'put_object')

        Returns:
            Optional[str]: 预签名URL，失败时返回None
        """
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )

            logger.info(f"Generated presigned URL for {key}, expires in {expires_in} seconds")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            return None

    def object_exists(self, key: str) -> bool:
        """
        检查S3对象是否存在

        Args:
            key: S3对象键

        Returns:
            bool: 对象是否存在
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            else:
                logger.error(f"Error checking object existence {key}: {e}")
                return False

        except Exception as e:
            logger.error(f"Unexpected error checking object {key}: {e}")
            return False

    def delete_object(self, key: str) -> bool:
        """
        删除S3对象

        Args:
            key: S3对象键

        Returns:
            bool: 删除是否成功
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Successfully deleted S3 object: {key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete S3 object {key}: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error deleting object {key}: {e}")
            return False

    def get_object_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取S3对象元数据

        Args:
            key: S3对象键

        Returns:
            Optional[Dict]: 对象元数据，失败时返回None
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)

            metadata = {
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType', ''),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {})
            }

            return metadata

        except ClientError as e:
            logger.error(f"Failed to get metadata for {key}: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error getting metadata for {key}: {e}")
            return None

    def list_objects(self, prefix: str = '', max_keys: int = 1000) -> list:
        """
        列出S3对象

        Args:
            prefix: 对象键前缀
            max_keys: 最大返回数量

        Returns:
            list: 对象列表
        """
        try:
            objects = []
            paginator = self.s3_client.get_paginator('list_objects_v2')

            for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            ):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'etag': obj['ETag'].strip('"')
                        })

            logger.info(f"Listed {len(objects)} objects with prefix: {prefix}")
            return objects

        except ClientError as e:
            logger.error(f"Failed to list objects with prefix {prefix}: {e}")
            return []

        except Exception as e:
            logger.error(f"Unexpected error listing objects: {e}")
            return []

    def copy_object(self, source_key: str, dest_key: str) -> bool:
        """
        复制S3对象

        Args:
            source_key: 源对象键
            dest_key: 目标对象键

        Returns:
            bool: 复制是否成功
        """
        try:
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': source_key
            }

            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_key
            )

            logger.info(f"Successfully copied S3 object: {source_key} -> {dest_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to copy S3 object {source_key} to {dest_key}: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error copying object: {e}")
            return False


class S3PresignedUrlManager:
    """S3预签名URL管理器"""

    def __init__(self, s3_helper: S3Helper):
        self.s3_helper = s3_helper

    def create_download_url(self, key: str, filename: Optional[str] = None, expires_in: int = 3600) -> Optional[str]:
        """
        创建下载URL

        Args:
            key: S3对象键
            filename: 下载时的文件名
            expires_in: URL有效期

        Returns:
            Optional[str]: 下载URL
        """
        params = {'Bucket': self.s3_helper.bucket_name, 'Key': key}

        if filename:
            params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'

        try:
            url = self.s3_helper.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires_in
            )

            logger.info(f"Created download URL for {key}")
            return url

        except Exception as e:
            logger.error(f"Failed to create download URL for {key}: {e}")
            return None

    def create_upload_url(self, key: str, content_type: str, expires_in: int = 3600) -> Optional[str]:
        """
        创建上传URL

        Args:
            key: S3对象键
            content_type: 内容类型
            expires_in: URL有效期

        Returns:
            Optional[str]: 上传URL
        """
        try:
            url = self.s3_helper.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.s3_helper.bucket_name,
                    'Key': key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )

            logger.info(f"Created upload URL for {key}")
            return url

        except Exception as e:
            logger.error(f"Failed to create upload URL for {key}: {e}")
            return None