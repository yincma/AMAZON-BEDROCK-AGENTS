"""
优化的图片处理服务模块 V3 - 性能优化版本
支持并行处理、批处理、高级缓存策略和性能监控
"""

import logging
import io
import json
import base64
import time
import random
import hashlib
import asyncio
import threading
from typing import Dict, Any, List, Tuple, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache, wraps
from dataclasses import dataclass
from datetime import datetime, timedelta
import queue

from PIL import Image, ImageDraw, ImageFont
import boto3
from botocore.exceptions import ClientError, BotoCoreError

try:
    from .image_config import CONFIG
    from .image_exceptions import ImageProcessingError, NovaServiceError
except ImportError:
    from image_config import CONFIG
    from image_exceptions import ImageProcessingError, NovaServiceError

# 创建一个虚拟的MetricsCollector如果不存在
class MetricsCollector:
    def record_metric(self, *args, **kwargs): pass
    def record_timing(self, *args, **kwargs): pass
    def increment_counter(self, *args, **kwargs): pass

logger = logging.getLogger(__name__)


@dataclass
class ImageRequest:
    """图片请求数据类"""
    prompt: str
    model_preference: Optional[str] = None
    priority: int = 0  # 优先级，数字越大优先级越高
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ImageResponse:
    """图片响应数据类"""
    data: bytes
    model_used: str
    generation_time: float
    from_cache: bool
    request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CacheManager:
    """高级缓存管理器"""

    def __init__(self, max_memory_items: int = 100, ttl_seconds: int = 3600):
        self._memory_cache = {}
        self._cache_metadata = {}
        self._max_items = max_memory_items
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._hit_count = 0
        self._miss_count = 0

    def get(self, key: str) -> Optional[bytes]:
        """获取缓存项"""
        with self._lock:
            if key in self._memory_cache:
                metadata = self._cache_metadata[key]
                # 检查TTL
                if time.time() - metadata['timestamp'] < self._ttl_seconds:
                    metadata['hits'] += 1
                    self._hit_count += 1
                    return self._memory_cache[key]
                else:
                    # 过期，删除
                    del self._memory_cache[key]
                    del self._cache_metadata[key]

            self._miss_count += 1
            return None

    def set(self, key: str, value: bytes) -> None:
        """设置缓存项"""
        with self._lock:
            # LRU淘汰策略
            if len(self._memory_cache) >= self._max_items:
                self._evict_lru()

            self._memory_cache[key] = value
            self._cache_metadata[key] = {
                'timestamp': time.time(),
                'size': len(value),
                'hits': 0
            }

    def _evict_lru(self) -> None:
        """LRU淘汰策略"""
        if not self._cache_metadata:
            return

        # 找出最少使用的项
        lru_key = min(self._cache_metadata.keys(),
                     key=lambda k: self._cache_metadata[k]['hits'])
        del self._memory_cache[lru_key]
        del self._cache_metadata[lru_key]

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_size = sum(meta['size'] for meta in self._cache_metadata.values())
            hit_rate = self._hit_count / (self._hit_count + self._miss_count) if (self._hit_count + self._miss_count) > 0 else 0

            return {
                'items': len(self._memory_cache),
                'total_size_mb': total_size / (1024 * 1024),
                'hit_count': self._hit_count,
                'miss_count': self._miss_count,
                'hit_rate': hit_rate,
                'max_items': self._max_items
            }


class BatchProcessor:
    """批处理处理器"""

    def __init__(self, batch_size: int = 5, batch_timeout: float = 1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._queue = queue.PriorityQueue()
        self._processing = False
        self._lock = threading.Lock()

    def add_request(self, request: ImageRequest) -> asyncio.Future:
        """添加请求到批处理队列"""
        future = asyncio.Future()
        # 使用负优先级以实现高优先级先处理
        self._queue.put((-request.priority, time.time(), request, future))

        # 触发批处理
        if not self._processing:
            threading.Thread(target=self._process_batch, daemon=True).start()

        return future

    def _process_batch(self) -> None:
        """处理批次"""
        with self._lock:
            if self._processing:
                return
            self._processing = True

        try:
            batch = []
            start_time = time.time()

            while len(batch) < self.batch_size:
                try:
                    timeout = self.batch_timeout - (time.time() - start_time)
                    if timeout <= 0:
                        break

                    item = self._queue.get(timeout=timeout)
                    batch.append(item)
                except queue.Empty:
                    break

            if batch:
                self._execute_batch(batch)

        finally:
            self._processing = False

    def _execute_batch(self, batch: List) -> None:
        """执行批处理"""
        # 这里实际执行批处理逻辑
        # 在实际实现中，这里会调用图片生成服务
        pass


class ImageProcessingServiceV3:
    """优化的图片处理服务类 V3 - 高性能版本"""

    def __init__(self, bedrock_client=None, s3_client=None, cloudwatch_client=None,
                 enable_caching=True, enable_metrics=True, max_workers=10):
        """
        初始化优化的图片处理服务

        Args:
            bedrock_client: Bedrock客户端实例
            s3_client: S3客户端实例
            cloudwatch_client: CloudWatch客户端实例
            enable_caching: 是否启用缓存
            enable_metrics: 是否启用指标收集
            max_workers: 最大工作线程数
        """
        self.bedrock_client = bedrock_client or boto3.client('bedrock-runtime')
        self.s3_client = s3_client or boto3.client('s3') if enable_caching else None
        self.cloudwatch_client = cloudwatch_client or boto3.client('cloudwatch') if enable_metrics else None

        # 高级缓存管理
        self.cache_manager = CacheManager(max_memory_items=200, ttl_seconds=7200)
        self.enable_caching = enable_caching

        # 批处理器
        self.batch_processor = BatchProcessor(batch_size=5, batch_timeout=0.5)

        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 指标收集器
        self.metrics = MetricsCollector() if enable_metrics else None

        # 模型池管理
        self.model_pool = {
            "amazon.nova-canvas-v1:0": {"available": True, "failures": 0, "last_success": time.time()},
            "stability.stable-diffusion-xl-v1": {"available": True, "failures": 0, "last_success": time.time()}
        }

        # 性能统计
        self._stats = {
            'total_requests': 0,
            'successful_generations': 0,
            'cache_hits': 0,
            'total_generation_time': 0,
            'model_usage': {}
        }

        # 请求限流
        self._rate_limiter = RateLimiter(max_requests=100, time_window=60)

    async def generate_images_batch(self, requests: List[ImageRequest]) -> List[ImageResponse]:
        """
        批量生成图片（异步）

        Args:
            requests: 图片请求列表

        Returns:
            图片响应列表
        """
        start_time = time.perf_counter()

        # 记录批处理请求
        if self.metrics:
            self.metrics.increment_counter('batch_requests', len(requests))

        # 并行处理请求
        tasks = []
        for request in requests:
            task = asyncio.create_task(self._generate_single_async(request))
            tasks.append(task)

        # 等待所有任务完成
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"批处理中的请求 {i} 失败: {str(response)}")
                # 创建错误响应
                valid_responses.append(ImageResponse(
                    data=self._create_error_placeholder(),
                    model_used="placeholder",
                    generation_time=0,
                    from_cache=False,
                    request_id=requests[i].request_id
                ))
            else:
                valid_responses.append(response)

        # 记录性能指标
        total_time = time.perf_counter() - start_time
        if self.metrics:
            self.metrics.record_timing('batch_generation_time', total_time)
            self.metrics.record_metric('batch_size', len(requests))

        logger.info(f"批量生成 {len(requests)} 张图片，耗时 {total_time:.2f} 秒")

        return valid_responses

    async def _generate_single_async(self, request: ImageRequest) -> ImageResponse:
        """
        异步生成单张图片

        Args:
            request: 图片请求

        Returns:
            图片响应
        """
        start_time = time.perf_counter()

        # 检查限流
        if not self._rate_limiter.allow_request():
            raise ImageProcessingError("请求频率超过限制")

        # 优化提示词
        optimized_prompt = self._optimize_prompt_advanced(request.prompt)

        # 检查缓存
        cache_key = self._get_cache_key(optimized_prompt)
        if self.enable_caching:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                self._stats['cache_hits'] += 1
                if self.metrics:
                    self.metrics.increment_counter('cache_hits')

                return ImageResponse(
                    data=cached_data,
                    model_used="cache",
                    generation_time=time.perf_counter() - start_time,
                    from_cache=True,
                    request_id=request.request_id
                )

        # 选择最佳模型
        best_model = self._select_best_model(request.model_preference)

        try:
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            image_data = await loop.run_in_executor(
                self.executor,
                self._call_bedrock_model_optimized,
                optimized_prompt,
                best_model
            )

            # 缓存结果
            if self.enable_caching:
                self.cache_manager.set(cache_key, image_data)
                # 异步上传到S3
                asyncio.create_task(self._upload_to_s3_async(cache_key, image_data))

            # 更新统计
            generation_time = time.perf_counter() - start_time
            self._update_stats(best_model, generation_time, success=True)

            return ImageResponse(
                data=image_data,
                model_used=best_model,
                generation_time=generation_time,
                from_cache=False,
                request_id=request.request_id
            )

        except Exception as e:
            logger.error(f"图片生成失败: {str(e)}")
            self._update_stats(best_model, 0, success=False)

            # 回退到占位图
            return ImageResponse(
                data=self._create_error_placeholder(),
                model_used="placeholder",
                generation_time=time.perf_counter() - start_time,
                from_cache=False,
                request_id=request.request_id
            )

    def _call_bedrock_model_optimized(self, prompt: str, model_id: str) -> bytes:
        """
        优化的Bedrock模型调用

        Args:
            prompt: 提示词
            model_id: 模型ID

        Returns:
            图片数据
        """
        # 使用连接池和会话复用
        start_time = time.perf_counter()

        try:
            if model_id.startswith("amazon.nova"):
                request_body = self._build_nova_request(prompt)
            else:
                request_body = self._build_stability_request(prompt)

            # 记录API调用开始
            if self.metrics:
                self.metrics.increment_counter(f'api_calls_{model_id}')

            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )

            # 解析响应
            response_body = json.loads(response['body'].read())
            image_data = self._extract_image_data(response_body, model_id)

            # 记录成功
            api_time = time.perf_counter() - start_time
            if self.metrics:
                self.metrics.record_timing(f'api_latency_{model_id}', api_time)

            # 更新模型状态
            self.model_pool[model_id]['last_success'] = time.time()
            self.model_pool[model_id]['failures'] = 0

            return image_data

        except Exception as e:
            # 更新失败计数
            self.model_pool[model_id]['failures'] += 1
            if self.model_pool[model_id]['failures'] >= 3:
                self.model_pool[model_id]['available'] = False
                logger.warning(f"模型 {model_id} 因连续失败被暂时禁用")

            raise

    def _select_best_model(self, preference: Optional[str] = None) -> str:
        """
        智能模型选择

        Args:
            preference: 首选模型

        Returns:
            最佳模型ID
        """
        # 如果有首选且可用，使用首选
        if preference and preference in self.model_pool:
            if self.model_pool[preference]['available']:
                return preference

        # 选择可用且成功率最高的模型
        available_models = [
            model_id for model_id, info in self.model_pool.items()
            if info['available']
        ]

        if not available_models:
            # 重置所有模型状态
            for model_id in self.model_pool:
                self.model_pool[model_id]['available'] = True
                self.model_pool[model_id]['failures'] = 0
            return list(self.model_pool.keys())[0]

        # 基于最近成功时间选择
        return max(available_models,
                  key=lambda m: self.model_pool[m]['last_success'])

    def _optimize_prompt_advanced(self, prompt: str) -> str:
        """
        高级提示词优化

        Args:
            prompt: 原始提示词

        Returns:
            优化后的提示词
        """
        # 基础清理
        optimized = prompt.strip()

        # 智能增强
        enhancements = []

        # 检测语言并添加相应的质量描述
        if any(char >= '\u4e00' and char <= '\u9fff' for char in optimized):
            # 中文提示词
            quality_terms = ["高质量", "4K分辨率", "专业摄影", "细节丰富"]
        else:
            # 英文提示词
            quality_terms = ["high quality", "4K resolution", "professional", "detailed"]

        # 添加未包含的质量描述
        for term in quality_terms:
            if term not in optimized.lower():
                enhancements.append(term)

        # 组合优化后的提示词
        if enhancements:
            optimized = f"{optimized}, {', '.join(enhancements[:2])}"

        # 长度限制
        if len(optimized) > 500:
            optimized = optimized[:497] + "..."

        return optimized

    def _build_nova_request(self, prompt: str) -> Dict[str, Any]:
        """构建Nova请求体"""
        return {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
                "numberOfImages": 1,
                "quality": "premium",
                "width": CONFIG.DEFAULT_IMAGE_WIDTH,
                "height": CONFIG.DEFAULT_IMAGE_HEIGHT,
                "cfgScale": 8.0,
                "seed": None
            }
        }

    def _build_stability_request(self, prompt: str) -> Dict[str, Any]:
        """构建Stability请求体"""
        return {
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": 8,
            "width": CONFIG.DEFAULT_IMAGE_WIDTH,
            "height": CONFIG.DEFAULT_IMAGE_HEIGHT,
            "samples": 1,
            "steps": 50
        }

    def _extract_image_data(self, response_body: Dict, model_id: str) -> bytes:
        """从响应中提取图片数据"""
        if model_id.startswith("amazon.nova"):
            if 'images' in response_body and response_body['images']:
                return base64.b64decode(response_body['images'][0])
        elif model_id.startswith("stability"):
            if 'artifacts' in response_body and response_body['artifacts']:
                return base64.b64decode(response_body['artifacts'][0]['base64'])

        raise NovaServiceError(f"无法从 {model_id} 响应中提取图片数据")

    async def _upload_to_s3_async(self, cache_key: str, image_data: bytes) -> None:
        """异步上传到S3"""
        if not self.s3_client or not CONFIG.DEFAULT_BUCKET:
            return

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._upload_to_s3_sync,
                cache_key,
                image_data
            )
        except Exception as e:
            logger.warning(f"S3上传失败: {str(e)}")

    def _upload_to_s3_sync(self, cache_key: str, image_data: bytes) -> None:
        """同步上传到S3"""
        s3_key = f"image_cache/{cache_key}.png"
        self.s3_client.put_object(
            Bucket=CONFIG.DEFAULT_BUCKET,
            Key=s3_key,
            Body=image_data,
            ContentType='image/png',
            Metadata={
                'cache_key': cache_key[:32],
                'generated_at': str(int(time.time())),
                'size': str(len(image_data))
            }
        )

    def _create_error_placeholder(self) -> bytes:
        """创建错误占位图"""
        image = Image.new('RGB', (CONFIG.DEFAULT_IMAGE_WIDTH, CONFIG.DEFAULT_IMAGE_HEIGHT),
                         color=(200, 200, 200))
        draw = ImageDraw.Draw(image)
        draw.text((50, 50), "Image Generation Failed", fill=(100, 100, 100))

        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()

    def _get_cache_key(self, prompt: str) -> str:
        """生成缓存键"""
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()

    def _update_stats(self, model: str, time_taken: float, success: bool) -> None:
        """更新统计信息"""
        self._stats['total_requests'] += 1

        if success:
            self._stats['successful_generations'] += 1
            self._stats['total_generation_time'] += time_taken

            if model not in self._stats['model_usage']:
                self._stats['model_usage'][model] = 0
            self._stats['model_usage'][model] += 1

        # 发送CloudWatch指标
        if self.metrics and self.cloudwatch_client:
            try:
                self.cloudwatch_client.put_metric_data(
                    Namespace='AI-PPT-Assistant/ImageGeneration',
                    MetricData=[
                        {
                            'MetricName': 'GenerationLatency',
                            'Value': time_taken,
                            'Unit': 'Seconds',
                            'Dimensions': [
                                {'Name': 'Model', 'Value': model},
                                {'Name': 'Status', 'Value': 'Success' if success else 'Failed'}
                            ]
                        }
                    ]
                )
            except Exception as e:
                logger.warning(f"CloudWatch指标发送失败: {str(e)}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        cache_stats = self.cache_manager.get_stats()

        avg_generation_time = (
            self._stats['total_generation_time'] / self._stats['successful_generations']
            if self._stats['successful_generations'] > 0 else 0
        )

        return {
            'total_requests': self._stats['total_requests'],
            'successful_generations': self._stats['successful_generations'],
            'success_rate': (
                self._stats['successful_generations'] / self._stats['total_requests']
                if self._stats['total_requests'] > 0 else 0
            ),
            'average_generation_time': avg_generation_time,
            'cache_stats': cache_stats,
            'model_usage': self._stats['model_usage'],
            'model_pool_status': self.model_pool
        }

    def cleanup(self) -> None:
        """清理资源"""
        self.executor.shutdown(wait=True)
        logger.info("图片处理服务资源已清理")


class RateLimiter:
    """请求限流器"""

    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        """检查是否允许请求"""
        with self._lock:
            now = time.time()
            # 清理过期的请求记录
            self.requests = [t for t in self.requests
                           if now - t < self.time_window]

            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True

            return False