"""
图片缓存服务 - 管理图片生成结果的缓存
"""

import json
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ImageCacheService:
    """图片缓存服务 - 使用DynamoDB和S3实现两级缓存"""

    def __init__(
        self,
        dynamodb_table: str = "ai-ppt-image-cache",
        s3_bucket: str = "ai-ppt-image-cache",
        cache_ttl_hours: int = 24 * 7  # 默认缓存7天
    ):
        """
        初始化缓存服务

        Args:
            dynamodb_table: DynamoDB表名
            s3_bucket: S3桶名
            cache_ttl_hours: 缓存过期时间（小时）
        """
        self.dynamodb = boto3.resource('dynamodb')
        self.s3_client = boto3.client('s3')
        self.table = self.dynamodb.Table(dynamodb_table)
        self.s3_bucket = s3_bucket
        self.cache_ttl_hours = cache_ttl_hours

    def generate_cache_key(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 768,
        style: str = "default",
        model: Optional[str] = None
    ) -> str:
        """
        生成缓存键

        Args:
            prompt: 提示词
            width: 宽度
            height: 高度
            style: 风格
            model: 模型名称

        Returns:
            缓存键
        """
        # 标准化提示词（去除多余空格、转小写）
        normalized_prompt = ' '.join(prompt.lower().split())

        # 生成键
        key_components = [
            normalized_prompt,
            str(width),
            str(height),
            style,
            model or "default"
        ]

        key_string = "|".join(key_components)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get_cached_image(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        从缓存获取图片

        Args:
            cache_key: 缓存键

        Returns:
            缓存的图片数据，如果不存在或过期则返回None
        """
        try:
            # 从DynamoDB获取元数据
            response = self.table.get_item(Key={'cache_key': cache_key})

            if 'Item' not in response:
                logger.debug(f"Cache miss: {cache_key}")
                return None

            item = response['Item']

            # 检查是否过期
            cached_at = datetime.fromisoformat(item['cached_at'])
            if self._is_expired(cached_at):
                logger.info(f"Cache expired: {cache_key}")
                self._delete_cache_entry(cache_key, item.get('s3_key'))
                return None

            # 从S3获取图片数据
            s3_key = item['s3_key']
            image_data = self._get_from_s3(s3_key)

            if not image_data:
                logger.warning(f"S3 data missing for cache key: {cache_key}")
                self._delete_cache_entry(cache_key, None)
                return None

            # 更新访问计数和时间
            self._update_access_stats(cache_key)

            return {
                'image_data': image_data,
                'metadata': {
                    'prompt': item.get('prompt'),
                    'model': item.get('model'),
                    'width': item.get('width'),
                    'height': item.get('height'),
                    'cached_at': item.get('cached_at'),
                    'hit_count': item.get('hit_count', 0) + 1
                }
            }

        except ClientError as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def save_to_cache(
        self,
        cache_key: str,
        image_data: bytes,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        保存图片到缓存

        Args:
            cache_key: 缓存键
            image_data: 图片数据
            metadata: 元数据

        Returns:
            是否保存成功
        """
        try:
            # 保存图片到S3
            s3_key = f"cache/{cache_key[:2]}/{cache_key}.png"
            if not self._save_to_s3(s3_key, image_data):
                return False

            # 保存元数据到DynamoDB
            item = {
                'cache_key': cache_key,
                's3_key': s3_key,
                'prompt': metadata.get('prompt', ''),
                'model': metadata.get('model', 'unknown'),
                'width': metadata.get('width', 1024),
                'height': metadata.get('height', 768),
                'style': metadata.get('style', 'default'),
                'cached_at': datetime.now(timezone.utc).isoformat(),
                'expires_at': (
                    datetime.now(timezone.utc) + timedelta(hours=self.cache_ttl_hours)
                ).isoformat(),
                'hit_count': 0,
                'file_size': len(image_data)
            }

            # 转换数值类型为Decimal（DynamoDB要求）
            item = self._convert_to_decimal(item)

            self.table.put_item(Item=item)

            logger.info(f"Cached image: {cache_key}")
            return True

        except ClientError as e:
            logger.error(f"Error saving to cache: {e}")
            return False

    def find_similar_cached_images(
        self,
        prompt: str,
        threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        查找相似的缓存图片（基于提示词相似度）

        Args:
            prompt: 提示词
            threshold: 相似度阈值

        Returns:
            相似图片列表
        """
        try:
            # 使用GSI查询相似提示词
            # 这需要在DynamoDB表上创建合适的GSI
            # 简化版：返回空列表
            return []

        except Exception as e:
            logger.error(f"Error finding similar images: {e}")
            return []

    def cleanup_expired_cache(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的条目数量
        """
        try:
            # 扫描过期条目
            now = datetime.now(timezone.utc).isoformat()
            response = self.table.scan(
                FilterExpression='expires_at < :now',
                ExpressionAttributeValues={':now': now}
            )

            expired_items = response.get('Items', [])
            deleted_count = 0

            for item in expired_items:
                cache_key = item['cache_key']
                s3_key = item.get('s3_key')

                if self._delete_cache_entry(cache_key, s3_key):
                    deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} expired cache entries")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计
        """
        try:
            # 扫描表获取统计（实际应用中应使用CloudWatch指标）
            response = self.table.scan(
                Select='COUNT'
            )

            total_items = response.get('Count', 0)

            # 获取更多统计信息需要额外查询
            return {
                'total_cached_images': total_items,
                'cache_ttl_hours': self.cache_ttl_hours,
                'bucket': self.s3_bucket,
                'table': self.table.table_name
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    def _is_expired(self, cached_at: datetime) -> bool:
        """检查缓存是否过期"""
        age = datetime.now(timezone.utc) - cached_at.replace(tzinfo=timezone.utc)
        return age.total_seconds() > self.cache_ttl_hours * 3600

    def _get_from_s3(self, s3_key: str) -> Optional[bytes]:
        """从S3获取数据"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=s3_key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug(f"S3 key not found: {s3_key}")
            else:
                logger.error(f"Error getting from S3: {e}")
            return None

    def _save_to_s3(self, s3_key: str, data: bytes) -> bool:
        """保存数据到S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=data,
                ContentType='image/png',
                StorageClass='INTELLIGENT_TIERING'  # 自动优化存储成本
            )
            return True
        except ClientError as e:
            logger.error(f"Error saving to S3: {e}")
            return False

    def _delete_cache_entry(
        self,
        cache_key: str,
        s3_key: Optional[str]
    ) -> bool:
        """删除缓存条目"""
        try:
            # 删除DynamoDB条目
            self.table.delete_item(Key={'cache_key': cache_key})

            # 删除S3对象
            if s3_key:
                self.s3_client.delete_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key
                )

            return True
        except Exception as e:
            logger.error(f"Error deleting cache entry: {e}")
            return False

    def _update_access_stats(self, cache_key: str) -> None:
        """更新访问统计"""
        try:
            self.table.update_item(
                Key={'cache_key': cache_key},
                UpdateExpression='SET hit_count = hit_count + :inc, last_accessed = :now',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':now': datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update access stats: {e}")

    def _convert_to_decimal(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """转换数值为Decimal类型（DynamoDB要求）"""
        for key, value in item.items():
            if isinstance(value, (int, float)):
                item[key] = Decimal(str(value))
        return item