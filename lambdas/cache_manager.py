"""
缓存管理器 - 多级缓存策略实现
支持内存缓存、Redis缓存和CDN缓存

实现：
- 多级缓存（L1: 内存, L2: Redis, L3: CDN）
- 智能缓存键生成
- TTL管理和失效策略
- 缓存预热机制
- 缓存命中率监控
"""

import os
import json
import time
import hashlib
import logging
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from functools import lru_cache, wraps
import boto3
import redis
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CacheKeyGenerator:
    """智能缓存键生成器"""

    @staticmethod
    def generate_presentation_key(topic: str, page_count: int, template: str, **kwargs) -> str:
        """生成演示文稿缓存键"""
        # 标准化主题（相似主题产生相同的键）
        normalized_topic = CacheKeyGenerator._normalize_topic(topic)

        # 构建基础键
        base_key = f"ppt:{normalized_topic}:{page_count}:{template}"

        # 添加可选参数
        if kwargs.get('with_images'):
            base_key += ":img"
        if kwargs.get('style'):
            base_key += f":{kwargs['style']}"

        # 生成哈希确保键长度合理
        key_hash = hashlib.md5(base_key.encode()).hexdigest()[:8]
        return f"{base_key}:{key_hash}"

    @staticmethod
    def generate_content_key(slide_id: str, content_type: str = "text") -> str:
        """生成幻灯片内容缓存键"""
        return f"content:{slide_id}:{content_type}"

    @staticmethod
    def generate_image_key(prompt: str, style: str = "default") -> str:
        """生成图片缓存键"""
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:12]
        return f"image:{style}:{prompt_hash}"

    @staticmethod
    def _normalize_topic(topic: str) -> str:
        """标准化主题名称（处理相似主题）"""
        # 移除常见后缀
        for suffix in ["基础", "入门", "详解", "技术", "概述", "简介"]:
            topic = topic.replace(suffix, "")

        # 转换为小写并移除空格
        normalized = topic.lower().strip().replace(" ", "_")

        # 映射相似概念
        similar_concepts = {
            "机器学习": "ml",
            "深度学习": "dl",
            "人工智能": "ai",
            "神经网络": "nn",
            "自然语言处理": "nlp"
        }

        for key, value in similar_concepts.items():
            if key in normalized:
                normalized = normalized.replace(key, value)

        return normalized


class MultiLevelCache:
    """多级缓存实现"""

    def __init__(self, redis_endpoint: Optional[str] = None,
                 redis_port: int = 6379,
                 memory_cache_size: int = 128,
                 enable_cdn: bool = True):
        """
        初始化多级缓存

        Args:
            redis_endpoint: Redis集群端点
            redis_port: Redis端口
            memory_cache_size: 内存缓存大小（LRU）
            enable_cdn: 是否启用CDN缓存
        """
        # L1: 内存缓存
        self._memory_cache = {}
        self._memory_cache_size = memory_cache_size
        self._access_times = {}

        # L2: Redis缓存
        self._redis_client = None
        if redis_endpoint:
            try:
                self._redis_client = redis.Redis(
                    host=redis_endpoint,
                    port=redis_port,
                    decode_responses=True,
                    socket_keepalive=True,
                    socket_keepalive_options={
                        1: 1,  # TCP_KEEPIDLE
                        2: 3,  # TCP_KEEPINTVL
                        3: 5   # TCP_KEEPCNT
                    }
                )
                self._redis_client.ping()
                logger.info(f"Connected to Redis at {redis_endpoint}:{redis_port}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self._redis_client = None

        # L3: CDN缓存（通过CloudFront）
        self._enable_cdn = enable_cdn
        if enable_cdn:
            self._cloudfront_client = boto3.client('cloudfront')
            self._s3_client = boto3.client('s3')

        # 缓存统计
        self._stats = {
            'hits': {'l1': 0, 'l2': 0, 'l3': 0},
            'misses': 0,
            'sets': 0,
            'evictions': 0
        }

    def get(self, key: str, cache_level: str = "all") -> Optional[Any]:
        """
        从缓存获取数据

        Args:
            key: 缓存键
            cache_level: 缓存级别 (l1, l2, l3, all)

        Returns:
            缓存的数据或None
        """
        # L1: 检查内存缓存
        if cache_level in ["l1", "all"]:
            if key in self._memory_cache:
                self._stats['hits']['l1'] += 1
                self._access_times[key] = time.time()
                logger.debug(f"L1 cache hit for key: {key}")
                return self._memory_cache[key]['data']

        # L2: 检查Redis缓存
        if cache_level in ["l2", "all"] and self._redis_client:
            try:
                data = self._redis_client.get(key)
                if data:
                    self._stats['hits']['l2'] += 1
                    # 提升到L1缓存
                    self._set_memory_cache(key, json.loads(data))
                    logger.debug(f"L2 cache hit for key: {key}")
                    return json.loads(data)
            except Exception as e:
                logger.error(f"Redis get error: {e}")

        # L3: 检查CDN缓存
        if cache_level in ["l3", "all"] and self._enable_cdn:
            data = self._get_from_cdn(key)
            if data:
                self._stats['hits']['l3'] += 1
                # 提升到L1和L2缓存
                self._set_memory_cache(key, data)
                if self._redis_client:
                    self._set_redis_cache(key, data)
                logger.debug(f"L3 cache hit for key: {key}")
                return data

        self._stats['misses'] += 1
        return None

    def set(self, key: str, value: Any, ttl: int = 3600,
            cache_level: str = "all") -> bool:
        """
        设置缓存数据

        Args:
            key: 缓存键
            value: 要缓存的数据
            ttl: 过期时间（秒）
            cache_level: 缓存级别

        Returns:
            是否成功
        """
        self._stats['sets'] += 1
        success = True

        # L1: 设置内存缓存
        if cache_level in ["l1", "all"]:
            self._set_memory_cache(key, value, ttl)

        # L2: 设置Redis缓存
        if cache_level in ["l2", "all"] and self._redis_client:
            success = success and self._set_redis_cache(key, value, ttl)

        # L3: 设置CDN缓存
        if cache_level in ["l3", "all"] and self._enable_cdn:
            success = success and self._set_cdn_cache(key, value, ttl)

        return success

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        # 从所有级别删除
        if key in self._memory_cache:
            del self._memory_cache[key]

        if self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis delete error: {e}")

        if self._enable_cdn:
            self._invalidate_cdn_cache(key)

        return True

    def invalidate_pattern(self, pattern: str) -> int:
        """
        使匹配模式的缓存失效

        Args:
            pattern: 匹配模式（支持通配符）

        Returns:
            失效的键数量
        """
        count = 0

        # L1: 清理内存缓存
        keys_to_delete = [k for k in self._memory_cache.keys()
                         if self._match_pattern(k, pattern)]
        for key in keys_to_delete:
            del self._memory_cache[key]
            count += 1

        # L2: 清理Redis缓存
        if self._redis_client:
            try:
                for key in self._redis_client.scan_iter(match=pattern):
                    self._redis_client.delete(key)
                    count += 1
            except Exception as e:
                logger.error(f"Redis pattern delete error: {e}")

        logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
        return count

    def _set_memory_cache(self, key: str, value: Any, ttl: int = 3600):
        """设置内存缓存（带LRU逐出）"""
        # 检查容量并逐出最旧的项
        if len(self._memory_cache) >= self._memory_cache_size:
            self._evict_lru()

        self._memory_cache[key] = {
            'data': value,
            'expires_at': time.time() + ttl
        }
        self._access_times[key] = time.time()

    def _evict_lru(self):
        """LRU逐出策略"""
        if not self._access_times:
            return

        # 找到最近最少使用的键
        lru_key = min(self._access_times, key=self._access_times.get)

        # 删除该项
        if lru_key in self._memory_cache:
            del self._memory_cache[lru_key]
            del self._access_times[lru_key]
            self._stats['evictions'] += 1
            logger.debug(f"Evicted LRU key: {lru_key}")

    def _set_redis_cache(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置Redis缓存"""
        try:
            self._redis_client.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def _get_from_cdn(self, key: str) -> Optional[Any]:
        """从CDN获取缓存数据"""
        # CDN通常用于静态资源，这里简化处理
        # 实际实现需要根据CloudFront配置
        return None

    def _set_cdn_cache(self, key: str, value: Any, ttl: int) -> bool:
        """设置CDN缓存"""
        # 对于适合CDN的内容（如生成的PPT文件），上传到S3并通过CloudFront分发
        if isinstance(value, bytes) or key.startswith("ppt_file:"):
            try:
                bucket_name = os.environ.get('CDN_BUCKET_NAME', 'ai-ppt-cdn')
                self._s3_client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=value if isinstance(value, bytes) else json.dumps(value),
                    CacheControl=f'max-age={ttl}'
                )
                return True
            except Exception as e:
                logger.error(f"CDN cache set error: {e}")
        return False

    def _invalidate_cdn_cache(self, key: str):
        """使CDN缓存失效"""
        try:
            distribution_id = os.environ.get('CLOUDFRONT_DISTRIBUTION_ID')
            if distribution_id:
                self._cloudfront_client.create_invalidation(
                    DistributionId=distribution_id,
                    InvalidationBatch={
                        'Paths': {
                            'Quantity': 1,
                            'Items': [f'/{key}']
                        },
                        'CallerReference': str(time.time())
                    }
                )
        except Exception as e:
            logger.error(f"CDN invalidation error: {e}")

    def _match_pattern(self, key: str, pattern: str) -> bool:
        """简单的通配符匹配"""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_hits = sum(self._stats['hits'].values())
        total_requests = total_hits + self._stats['misses']
        hit_rate = total_hits / total_requests if total_requests > 0 else 0

        return {
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'sets': self._stats['sets'],
            'evictions': self._stats['evictions'],
            'hit_rate': hit_rate,
            'memory_cache_size': len(self._memory_cache),
            'memory_cache_capacity': self._memory_cache_size
        }


class CacheWarmer:
    """缓存预热器"""

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache
        self.s3_client = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')

    def warm_popular_content(self, top_n: int = 50):
        """预热热门内容"""
        # 从DynamoDB获取热门PPT主题
        table = self.dynamodb.Table(os.environ.get('PRESENTATIONS_TABLE', 'presentations'))

        try:
            # 查询最近访问的演示文稿
            response = table.scan(
                ProjectionExpression='topic, page_count, template, access_count',
                FilterExpression='access_count > :min_count',
                ExpressionAttributeValues={':min_count': 5}
            )

            # 排序并获取top N
            items = sorted(response['Items'],
                          key=lambda x: x.get('access_count', 0),
                          reverse=True)[:top_n]

            # 预热缓存
            warmed_count = 0
            for item in items:
                key = CacheKeyGenerator.generate_presentation_key(
                    topic=item['topic'],
                    page_count=item['page_count'],
                    template=item['template']
                )

                # 模拟缓存数据（实际应该从S3或生成）
                cache_data = {
                    'topic': item['topic'],
                    'template': item['template'],
                    'prewarmed': True,
                    'timestamp': datetime.now().isoformat()
                }

                self.cache.set(key, cache_data, ttl=7200)  # 2小时TTL
                warmed_count += 1

            logger.info(f"Prewarmed {warmed_count} popular content items")
            return warmed_count

        except Exception as e:
            logger.error(f"Cache warming error: {e}")
            return 0

    def warm_from_s3_batch(self, bucket: str, prefix: str = "cache-warm/"):
        """从S3批量预热缓存"""
        try:
            # 列出S3中的预热数据
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=100
            )

            if 'Contents' not in response:
                return 0

            warmed_count = 0
            for obj in response['Contents']:
                key = obj['Key'].replace(prefix, '')

                # 获取对象内容
                obj_response = self.s3_client.get_object(
                    Bucket=bucket,
                    Key=obj['Key']
                )
                content = json.loads(obj_response['Body'].read())

                # 设置缓存
                self.cache.set(key, content, ttl=3600)
                warmed_count += 1

            logger.info(f"Warmed {warmed_count} items from S3")
            return warmed_count

        except Exception as e:
            logger.error(f"S3 batch warming error: {e}")
            return 0


def cached_function(ttl: int = 300, cache_level: str = "all"):
    """
    装饰器：为函数添加缓存

    Args:
        ttl: 缓存过期时间（秒）
        cache_level: 缓存级别
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()

            # 获取缓存实例
            cache = get_cache_instance()

            # 尝试从缓存获取
            cached_result = cache.get(cache_key, cache_level)
            if cached_result is not None:
                logger.info(f"Cache hit for function: {func.__name__}")
                return cached_result

            # 执行函数
            result = func(*args, **kwargs)

            # 存储到缓存
            cache.set(cache_key, result, ttl, cache_level)

            return result
        return wrapper
    return decorator


# 全局缓存实例
_cache_instance = None


def get_cache_instance() -> MultiLevelCache:
    """获取缓存实例（单例）"""
    global _cache_instance
    if _cache_instance is None:
        redis_endpoint = os.environ.get('REDIS_ENDPOINT')
        _cache_instance = MultiLevelCache(
            redis_endpoint=redis_endpoint,
            memory_cache_size=int(os.environ.get('MEMORY_CACHE_SIZE', '128')),
            enable_cdn=os.environ.get('ENABLE_CDN', 'true').lower() == 'true'
        )
    return _cache_instance


def invalidate_presentation_cache(presentation_id: str):
    """使特定演示文稿的缓存失效"""
    cache = get_cache_instance()
    pattern = f"*{presentation_id}*"
    return cache.invalidate_pattern(pattern)


# Lambda处理器示例
def lambda_handler(event, context):
    """Lambda处理器示例：演示缓存使用"""

    # 初始化缓存
    cache = get_cache_instance()

    # 解析请求
    action = event.get('action', 'get')
    key = event.get('key')

    if action == 'get':
        # 获取缓存
        data = cache.get(key)
        return {
            'statusCode': 200 if data else 404,
            'body': json.dumps(data) if data else json.dumps({'message': 'Cache miss'})
        }

    elif action == 'set':
        # 设置缓存
        value = event.get('value')
        ttl = event.get('ttl', 3600)
        success = cache.set(key, value, ttl)
        return {
            'statusCode': 200 if success else 500,
            'body': json.dumps({'success': success})
        }

    elif action == 'stats':
        # 获取统计信息
        stats = cache.get_stats()
        return {
            'statusCode': 200,
            'body': json.dumps(stats)
        }

    elif action == 'warm':
        # 预热缓存
        warmer = CacheWarmer(cache)
        count = warmer.warm_popular_content()
        return {
            'statusCode': 200,
            'body': json.dumps({'warmed_items': count})
        }

    else:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid action'})
        }