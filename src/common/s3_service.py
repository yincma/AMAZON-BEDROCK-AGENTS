"""
S3服务类 - 统一S3操作，提供类型安全的接口
"""
import json
import logging
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError, BotoCoreError

from ..constants import Config

logger = logging.getLogger(__name__)

class S3ServiceError(Exception):
    """S3服务异常"""
    pass

class S3Service:
    """S3服务封装类，提供类型安全的S3操作"""

    def __init__(self, bucket_name: str, s3_client=None, region_name: str = None):
        """初始化S3服务

        Args:
            bucket_name: S3存储桶名称
            s3_client: S3客户端实例（可选，用于测试）
            region_name: AWS区域名称（可选）
        """
        self.bucket_name = bucket_name
        self.s3_client = s3_client or boto3.client(
            's3',
            region_name=region_name or Config.Env.DEFAULT_REGION
        )

    def upload_json(self, key: str, data: Dict[str, Any],
                   content_type: str = None) -> str:
        """上传JSON数据到S3

        Args:
            key: S3对象键
            data: 要上传的JSON数据
            content_type: 内容类型（可选）

        Returns:
            S3对象键

        Raises:
            S3ServiceError: 上传失败时抛出
        """
        try:
            json_data = json.dumps(data, ensure_ascii=False, indent=2)

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_data.encode('utf-8'),
                ContentType=content_type or Config.API.CONTENT_TYPE_JSON
            )

            logger.info(f"JSON数据已上传到S3: s3://{self.bucket_name}/{key}")
            return key

        except (ClientError, BotoCoreError) as e:
            error_msg = f"上传JSON到S3失败: {str(e)}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg) from e

    def download_json(self, key: str) -> Dict[str, Any]:
        """从S3下载JSON数据

        Args:
            key: S3对象键

        Returns:
            解析后的JSON数据

        Raises:
            S3ServiceError: 下载或解析失败时抛出
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )

            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)

            logger.debug(f"从S3下载JSON数据: s3://{self.bucket_name}/{key}")
            return data

        except (ClientError, BotoCoreError) as e:
            error_msg = f"从S3下载JSON失败: {str(e)}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg) from e
        except json.JSONDecodeError as e:
            error_msg = f"解析S3中的JSON数据失败: {str(e)}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg) from e

    def upload_bytes(self, key: str, data: bytes,
                    content_type: str) -> str:
        """上传字节数据到S3

        Args:
            key: S3对象键
            data: 要上传的字节数据
            content_type: 内容类型

        Returns:
            S3对象键

        Raises:
            S3ServiceError: 上传失败时抛出
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type
            )

            logger.info(f"字节数据已上传到S3: s3://{self.bucket_name}/{key}")
            return key

        except (ClientError, BotoCoreError) as e:
            error_msg = f"上传字节数据到S3失败: {str(e)}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg) from e

    def object_exists(self, key: str) -> bool:
        """检查S3对象是否存在

        Args:
            key: S3对象键

        Returns:
            对象是否存在
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                # 其他错误重新抛出
                raise S3ServiceError(f"检查S3对象存在性失败: {str(e)}") from e

    def generate_presigned_url(self, key: str,
                              expires_in: int = None,
                              method: str = 'get_object') -> str:
        """生成预签名URL

        Args:
            key: S3对象键
            expires_in: URL有效期（秒），默认使用配置值
            method: HTTP方法，默认为get_object

        Returns:
            预签名URL

        Raises:
            S3ServiceError: 生成URL失败时抛出
        """
        try:
            expires_in = expires_in or Config.S3.DEFAULT_URL_EXPIRY

            url = self.s3_client.generate_presigned_url(
                method,
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )

            logger.debug(f"生成预签名URL: {key}")
            return url

        except (ClientError, BotoCoreError) as e:
            error_msg = f"生成预签名URL失败: {str(e)}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg) from e

    def delete_object(self, key: str) -> None:
        """删除S3对象

        Args:
            key: S3对象键

        Raises:
            S3ServiceError: 删除失败时抛出
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            logger.info(f"已删除S3对象: s3://{self.bucket_name}/{key}")

        except (ClientError, BotoCoreError) as e:
            error_msg = f"删除S3对象失败: {str(e)}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg) from e

    def delete_objects_by_prefix(self, prefix: str) -> int:
        """根据前缀批量删除S3对象

        Args:
            prefix: 对象前缀

        Returns:
            删除的对象数量

        Raises:
            S3ServiceError: 删除失败时抛出
        """
        try:
            # 列出所有匹配前缀的对象
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            objects = response.get('Contents', [])
            if not objects:
                logger.info(f"没有找到匹配前缀的对象: {prefix}")
                return 0

            # 批量删除对象
            delete_keys = [{'Key': obj['Key']} for obj in objects]

            # S3批量删除限制
            deleted_count = 0
            for i in range(0, len(delete_keys), Config.S3.MAX_DELETE_OBJECTS):
                batch = delete_keys[i:i + Config.S3.MAX_DELETE_OBJECTS]

                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': batch}
                )
                deleted_count += len(batch)

            logger.info(f"批量删除S3对象完成: {deleted_count}个对象，前缀: {prefix}")
            return deleted_count

        except (ClientError, BotoCoreError) as e:
            error_msg = f"批量删除S3对象失败: {str(e)}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg) from e

    def list_objects_by_prefix(self, prefix: str,
                              max_keys: int = 1000) -> List[Dict[str, Any]]:
        """根据前缀列出S3对象

        Args:
            prefix: 对象前缀
            max_keys: 最大返回数量

        Returns:
            对象信息列表

        Raises:
            S3ServiceError: 列出对象失败时抛出
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            objects = response.get('Contents', [])
            logger.debug(f"列出S3对象: {len(objects)}个对象，前缀: {prefix}")

            return objects

        except (ClientError, BotoCoreError) as e:
            error_msg = f"列出S3对象失败: {str(e)}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg) from e

    def get_object_metadata(self, key: str) -> Dict[str, Any]:
        """获取S3对象元数据

        Args:
            key: S3对象键

        Returns:
            对象元数据

        Raises:
            S3ServiceError: 获取元数据失败时抛出
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )

            metadata = {
                'ContentLength': response.get('ContentLength'),
                'ContentType': response.get('ContentType'),
                'LastModified': response.get('LastModified'),
                'ETag': response.get('ETag'),
                'Metadata': response.get('Metadata', {})
            }

            logger.debug(f"获取S3对象元数据: s3://{self.bucket_name}/{key}")
            return metadata

        except (ClientError, BotoCoreError) as e:
            error_msg = f"获取S3对象元数据失败: {str(e)}"
            logger.error(error_msg)
            raise S3ServiceError(error_msg) from e

# 便捷函数
def create_s3_service(bucket_name: str = None, **kwargs) -> S3Service:
    """创建S3服务实例

    Args:
        bucket_name: 存储桶名称，默认从环境变量获取
        **kwargs: 其他初始化参数

    Returns:
        S3Service实例
    """
    import os
    bucket_name = bucket_name or os.environ.get(
        Config.Env.S3_BUCKET,
        Config.Env.DEFAULT_BUCKET
    )
    return S3Service(bucket_name, **kwargs)