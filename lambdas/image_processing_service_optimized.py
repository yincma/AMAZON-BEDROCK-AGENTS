"""
高性能图片处理服务模块 - 包含全面的性能优化和监控
"""

import logging
import io
import json
import base64
import time
import random
import hashlib
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from collections import OrderedDict, deque
import threading
from enum import Enum

from PIL import Image, ImageDraw, ImageFont
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

try:
    from .image_config import CONFIG
    from .image_exceptions import ImageProcessingError, NovaServiceError
    from .metrics_collector import MetricsCollector
    from .cache_manager import DistributedCacheManager
except ImportError:
    from image_config import CONFIG
    from image_exceptions import ImageProcessingError, NovaServiceError
    # 如果导入失败，创建模拟类
    class MetricsCollector:
        def record_metric(self, *args, **kwargs): pass
        def start_timer(self, *args, **kwargs):
            class Timer:
                def stop(self): pass
            return Timer()

    class DistributedCacheManager:
        def __init__(self, *args, **kwargs): pass
        def get(self, key): return None
        def set(self, key, value, ttl=None): pass
        def clear(self): pass

logger = logging.getLogger(__name__)


class ModelPriority(Enum):
    """模型优先级枚举"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


@dataclass
class ModelConfig:
    """模型配置数据类"""
    model_id: str
    priority: ModelPriority
    timeout: int
    max_retries: int
    cost_per_request: float
    quality_score: float
    avg_response_time: float
    success_rate: float = 1.0
    last_failure_time: Optional[datetime] = None
    failure_count: int = 0


@dataclass
class ImageRequest:
    """图片请求数据类"""
    prompt: str
    request_id: str
    width: int = CONFIG.DEFAULT_IMAGE_WIDTH
    height: int = CONFIG.DEFAULT_IMAGE_HEIGHT
    quality: str = "premium"
    model_preference: Optional[str] = None
    priority: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageResponse:
    """图片响应数据类"""
    request_id: str
    image_data: bytes
    model_used: str
    generation_time: float
    from_cache: bool
    cost: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConnectionPool:
    """连接池管理器"""

    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self._pools = {}
        self._lock = threading.Lock()

    def get_client(self, service_name: str, **kwargs):
        """获取或创建客户端连接"""
        with self._lock:
            if service_name not in self._pools:
                config = Config(
                    max_pool_connections=self.max_connections,
                    retries={'max_attempts': 3, 'mode': 'adaptive'},
                    connect_timeout=5,
                    read_timeout=30
                )
                self._pools[service_name] = boto3.client(
                    service_name,
                    config=config,
                    **kwargs
                )
            return self._pools[service_name]


class RequestBatcher:
    """请求批处理器"""

    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.5):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._batch = deque()
        self._lock = threading.Lock()
        self._timer = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

    def add_request(self, request: ImageRequest) -> concurrent.futures.Future:
        """添加请求到批处理队列"""
        future = concurrent.futures.Future()

        with self._lock:
            self._batch.append((request, future))

            if len(self._batch) >= self.batch_size:
                self._process_batch()
            elif not self._timer:
                self._timer = threading.Timer(self.batch_timeout, self._process_batch)
                self._timer.start()

        return future

    def _process_batch(self):
        """处理批量请求"""
        with self._lock:
            if not self._batch:
                return

            batch = list(self._batch)
            self._batch.clear()

            if self._timer:
                self._timer.cancel()
                self._timer = None

        # 在后台处理批量请求
        self._executor.submit(self._execute_batch, batch)

    def _execute_batch(self, batch):
        """执行批量请求"""
        # 这里实现实际的批处理逻辑
        for request, future in batch:
            try:
                # 处理单个请求
                result = self._process_single_request(request)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

    def _process_single_request(self, request: ImageRequest):
        """处理单个请求的占位方法"""
        return ImageResponse(
            request_id=request.request_id,
            image_data=b"",
            model_used="placeholder",
            generation_time=0.0,
            from_cache=False,
            cost=0.0
        )


class LRUImageCache:
    """LRU图片缓存实现"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
        self._timestamps = {}
        self._lock = threading.Lock()
        self._hit_count = 0
        self._miss_count = 0

    def get(self, key: str) -> Optional[bytes]:
        """获取缓存项"""
        with self._lock:
            if key in self._cache:
                # 检查TTL
                if time.time() - self._timestamps[key] > self.ttl_seconds:
                    del self._cache[key]
                    del self._timestamps[key]
                    self._miss_count += 1
                    return None

                # 移动到末尾（最近使用）
                self._cache.move_to_end(key)
                self._hit_count += 1
                return self._cache[key]

            self._miss_count += 1
            return None

    def set(self, key: str, value: bytes):
        """设置缓存项"""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.max_size:
                    # 删除最老的项
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    del self._timestamps[oldest_key]

            self._cache[key] = value
            self._timestamps[key] = time.time()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total_requests = self._hit_count + self._miss_count
            hit_rate = self._hit_count / total_requests if total_requests > 0 else 0

            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_count': self._hit_count,
                'miss_count': self._miss_count,
                'hit_rate': hit_rate,
                'ttl_seconds': self.ttl_seconds
            }


class ImageProcessingServiceOptimized:
    """高性能图片处理服务类 - 包含全面的性能优化"""

    def __init__(self,
                 enable_caching: bool = True,
                 enable_monitoring: bool = True,
                 enable_batching: bool = True,
                 enable_preloading: bool = True):
        """
        初始化优化的图片处理服务

        Args:
            enable_caching: 是否启用缓存
            enable_monitoring: 是否启用监控
            enable_batching: 是否启用批处理
            enable_preloading: 是否启用预加载
        """
        # 连接池管理
        self.connection_pool = ConnectionPool(max_connections=50)
        self.bedrock_client = self.connection_pool.get_client('bedrock-runtime')
        self.s3_client = self.connection_pool.get_client('s3')
        self.cloudwatch_client = self.connection_pool.get_client('cloudwatch')

        # 缓存管理
        self.enable_caching = enable_caching
        self.lru_cache = LRUImageCache(max_size=200, ttl_seconds=3600)
        self.distributed_cache = DistributedCacheManager() if enable_caching else None

        # 批处理管理
        self.enable_batching = enable_batching
        self.request_batcher = RequestBatcher() if enable_batching else None

        # 监控管理
        self.enable_monitoring = enable_monitoring
        self.metrics_collector = MetricsCollector() if enable_monitoring else None

        # 模型配置
        self.model_configs = self._initialize_model_configs()

        # 并发控制
        self.semaphore = asyncio.Semaphore(10)  # 最大并发数
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)

        # 预加载管理
        self.enable_preloading = enable_preloading
        self.preload_queue = deque(maxlen=50)

        # 性能统计
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'total_generation_time': 0,
            'total_cost': 0
        }

        # Lambda冷启动优化
        self._warm_up()

    def _initialize_model_configs(self) -> Dict[str, ModelConfig]:
        """初始化模型配置"""
        return {
            "amazon.nova-canvas-v1:0": ModelConfig(
                model_id="amazon.nova-canvas-v1:0",
                priority=ModelPriority.HIGH,
                timeout=30,
                max_retries=3,
                cost_per_request=0.01,
                quality_score=0.95,
                avg_response_time=2.5
            ),
            "stability.stable-diffusion-xl-v1": ModelConfig(
                model_id="stability.stable-diffusion-xl-v1",
                priority=ModelPriority.MEDIUM,
                timeout=25,
                max_retries=2,
                cost_per_request=0.008,
                quality_score=0.90,
                avg_response_time=3.0
            )
        }

    def _warm_up(self):
        """Lambda冷启动预热"""
        try:
            # 预热Bedrock连接
            self.bedrock_client.list_foundation_models(maxResults=1)

            # 预热S3连接
            if self.s3_client and CONFIG.DEFAULT_BUCKET:
                self.s3_client.head_bucket(Bucket=CONFIG.DEFAULT_BUCKET)

            logger.info("服务预热完成")
        except Exception as e:
            logger.warning(f"服务预热失败: {str(e)}")

    async def generate_image_async(self, request: ImageRequest) -> ImageResponse:
        """
        异步生成图片

        Args:
            request: 图片请求对象

        Returns:
            图片响应对象
        """
        start_time = time.time()

        # 记录请求指标
        if self.enable_monitoring:
            self.metrics_collector.record_metric('ImageGenerationRequested', 1)

        try:
            # 检查多级缓存
            cached_image = await self._check_multi_level_cache(request)
            if cached_image:
                return ImageResponse(
                    request_id=request.request_id,
                    image_data=cached_image,
                    model_used="cache",
                    generation_time=time.time() - start_time,
                    from_cache=True,
                    cost=0.0
                )

            # 使用信号量控制并发
            async with self.semaphore:
                # 智能模型选择
                model_config = self._select_optimal_model(request)

                # 生成图片
                image_data = await self._generate_with_model_async(
                    request,
                    model_config
                )

                # 异步缓存结果
                asyncio.create_task(self._cache_image_async(request, image_data))

                # 预加载相关图片
                if self.enable_preloading:
                    asyncio.create_task(self._preload_related_images(request))

                generation_time = time.time() - start_time

                # 更新性能统计
                self._update_performance_stats(
                    model_config,
                    generation_time,
                    success=True
                )

                return ImageResponse(
                    request_id=request.request_id,
                    image_data=image_data,
                    model_used=model_config.model_id,
                    generation_time=generation_time,
                    from_cache=False,
                    cost=model_config.cost_per_request
                )

        except Exception as e:
            logger.error(f"图片生成失败: {str(e)}")

            if self.enable_monitoring:
                self.metrics_collector.record_metric('ImageGenerationFailed', 1)

            # 返回优化的占位图
            return ImageResponse(
                request_id=request.request_id,
                image_data=self._create_optimized_placeholder(request),
                model_used="placeholder",
                generation_time=time.time() - start_time,
                from_cache=False,
                cost=0.0
            )

    def generate_image_batch(self, requests: List[ImageRequest]) -> List[ImageResponse]:
        """
        批量生成图片

        Args:
            requests: 图片请求列表

        Returns:
            图片响应列表
        """
        # 使用线程池并行处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # 创建异步任务
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            tasks = [
                loop.create_task(self.generate_image_async(request))
                for request in requests
            ]

            # 等待所有任务完成
            responses = loop.run_until_complete(asyncio.gather(*tasks))
            loop.close()

            return responses

    async def _check_multi_level_cache(self, request: ImageRequest) -> Optional[bytes]:
        """
        检查多级缓存

        Args:
            request: 图片请求

        Returns:
            缓存的图片数据，如果没有则返回None
        """
        cache_key = self._generate_cache_key(request)

        # L1: 内存LRU缓存
        cached = self.lru_cache.get(cache_key)
        if cached:
            logger.debug("L1缓存命中")
            self.performance_stats['cache_hits'] += 1
            return cached

        # L2: 分布式缓存（Redis/ElastiCache）
        if self.distributed_cache:
            cached = self.distributed_cache.get(cache_key)
            if cached:
                logger.debug("L2缓存命中")
                # 更新L1缓存
                self.lru_cache.set(cache_key, cached)
                self.performance_stats['cache_hits'] += 1
                return cached

        # L3: S3缓存
        if self.s3_client and CONFIG.DEFAULT_BUCKET:
            try:
                s3_key = f"image_cache/{cache_key}.png"
                response = await self._s3_get_object_async(
                    CONFIG.DEFAULT_BUCKET,
                    s3_key
                )

                if response:
                    image_data = response['Body'].read()
                    logger.debug("L3缓存命中")

                    # 更新L1和L2缓存
                    self.lru_cache.set(cache_key, image_data)
                    if self.distributed_cache:
                        self.distributed_cache.set(cache_key, image_data, ttl=3600)

                    self.performance_stats['cache_hits'] += 1
                    return image_data

            except ClientError:
                pass

        return None

    async def _cache_image_async(self, request: ImageRequest, image_data: bytes):
        """
        异步缓存图片到多级缓存

        Args:
            request: 图片请求
            image_data: 图片数据
        """
        cache_key = self._generate_cache_key(request)

        # L1: 内存缓存
        self.lru_cache.set(cache_key, image_data)

        # L2: 分布式缓存
        if self.distributed_cache:
            self.distributed_cache.set(cache_key, image_data, ttl=3600)

        # L3: S3缓存（异步）
        if self.s3_client and CONFIG.DEFAULT_BUCKET:
            asyncio.create_task(
                self._s3_put_object_async(
                    CONFIG.DEFAULT_BUCKET,
                    f"image_cache/{cache_key}.png",
                    image_data
                )
            )

    def _select_optimal_model(self, request: ImageRequest) -> ModelConfig:
        """
        智能选择最优模型

        Args:
            request: 图片请求

        Returns:
            最优模型配置
        """
        available_models = []

        for model_id, config in self.model_configs.items():
            # 跳过最近失败的模型
            if config.last_failure_time:
                time_since_failure = datetime.now() - config.last_failure_time
                if time_since_failure < timedelta(minutes=5):
                    continue

            # 计算模型分数
            score = self._calculate_model_score(config, request)
            available_models.append((score, config))

        # 按分数排序
        available_models.sort(key=lambda x: x[0], reverse=True)

        if not available_models:
            # 如果所有模型都不可用，选择默认模型
            return self.model_configs["amazon.nova-canvas-v1:0"]

        return available_models[0][1]

    def _calculate_model_score(self, config: ModelConfig, request: ImageRequest) -> float:
        """
        计算模型分数

        Args:
            config: 模型配置
            request: 图片请求

        Returns:
            模型分数
        """
        # 基础分数
        score = config.quality_score * 100

        # 根据请求优先级调整
        if request.priority > 5:
            # 高优先级请求，更看重质量
            score *= 1.2
        else:
            # 低优先级请求，更看重速度和成本
            score *= (1.0 / config.avg_response_time)
            score *= (1.0 / config.cost_per_request)

        # 根据成功率调整
        score *= config.success_rate

        # 根据失败次数惩罚
        if config.failure_count > 0:
            score *= (1.0 / (1 + config.failure_count * 0.1))

        return score

    async def _generate_with_model_async(self,
                                        request: ImageRequest,
                                        model_config: ModelConfig) -> bytes:
        """
        使用指定模型异步生成图片

        Args:
            request: 图片请求
            model_config: 模型配置

        Returns:
            生成的图片数据
        """
        # 优化提示词
        optimized_prompt = self._optimize_prompt_advanced(request.prompt)

        # 使用线程池执行同步API调用
        loop = asyncio.get_event_loop()

        try:
            image_data = await loop.run_in_executor(
                self.executor,
                self._call_bedrock_model_with_timeout,
                optimized_prompt,
                model_config
            )

            # 图片后处理优化
            optimized_image = await self._post_process_image_async(image_data)

            return optimized_image

        except Exception as e:
            # 更新模型失败信息
            model_config.failure_count += 1
            model_config.last_failure_time = datetime.now()
            model_config.success_rate *= 0.9

            raise e

    def _call_bedrock_model_with_timeout(self,
                                        prompt: str,
                                        model_config: ModelConfig) -> bytes:
        """
        调用Bedrock模型（带超时控制）

        Args:
            prompt: 优化后的提示词
            model_config: 模型配置

        Returns:
            生成的图片数据
        """
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"模型调用超时: {model_config.model_id}")

        # 设置超时
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(model_config.timeout)

        try:
            if model_config.model_id.startswith("amazon.nova"):
                return self._call_nova_optimized(prompt, model_config)
            elif model_config.model_id.startswith("stability."):
                return self._call_stability_optimized(prompt, model_config)
            else:
                raise ValueError(f"不支持的模型: {model_config.model_id}")
        finally:
            signal.alarm(0)  # 取消超时

    def _call_nova_optimized(self, prompt: str, model_config: ModelConfig) -> bytes:
        """优化的Nova API调用"""
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
                "numberOfImages": 1,
                "quality": "premium",
                "width": CONFIG.DEFAULT_IMAGE_WIDTH,
                "height": CONFIG.DEFAULT_IMAGE_HEIGHT,
                "cfgScale": 8.0,
                "seed": random.randint(0, 2147483647)  # 随机种子提高多样性
            }
        }

        # 使用流式响应减少延迟
        response = self.bedrock_client.invoke_model_with_response_stream(
            modelId=model_config.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        # 处理流式响应
        response_body = b""
        for event in response['body']:
            response_body += event['chunk']['bytes']

        result = json.loads(response_body)

        if 'images' in result and result['images']:
            return base64.b64decode(result['images'][0])

        raise NovaServiceError("Nova API响应中没有图片数据")

    def _call_stability_optimized(self, prompt: str, model_config: ModelConfig) -> bytes:
        """优化的Stability API调用"""
        request_body = {
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": 8,
            "width": CONFIG.DEFAULT_IMAGE_WIDTH,
            "height": CONFIG.DEFAULT_IMAGE_HEIGHT,
            "samples": 1,
            "steps": 30  # 减少步数以提高速度
        }

        response = self.bedrock_client.invoke_model(
            modelId=model_config.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        result = json.loads(response['body'].read())

        if 'artifacts' in result and result['artifacts']:
            return base64.b64decode(result['artifacts'][0]['base64'])

        raise NovaServiceError("Stability API响应中没有图片数据")

    async def _post_process_image_async(self, image_data: bytes) -> bytes:
        """
        异步图片后处理

        Args:
            image_data: 原始图片数据

        Returns:
            处理后的图片数据
        """
        loop = asyncio.get_event_loop()

        # 在线程池中执行CPU密集型操作
        return await loop.run_in_executor(
            self.executor,
            self._optimize_image_quality,
            image_data
        )

    def _optimize_image_quality(self, image_data: bytes) -> bytes:
        """
        优化图片质量和大小

        Args:
            image_data: 原始图片数据

        Returns:
            优化后的图片数据
        """
        try:
            with io.BytesIO(image_data) as img_buffer:
                image = Image.open(img_buffer)

                # 转换为RGB（如果需要）
                if image.mode != 'RGB':
                    image = image.convert('RGB')

                # 优化大小
                if image.width > CONFIG.DEFAULT_IMAGE_WIDTH or \
                   image.height > CONFIG.DEFAULT_IMAGE_HEIGHT:
                    image.thumbnail(
                        (CONFIG.DEFAULT_IMAGE_WIDTH, CONFIG.DEFAULT_IMAGE_HEIGHT),
                        Image.Resampling.LANCZOS
                    )

                # 保存优化后的图片
                output_buffer = io.BytesIO()
                image.save(
                    output_buffer,
                    format='PNG',
                    optimize=True,
                    quality=85  # 平衡质量和大小
                )

                return output_buffer.getvalue()

        except Exception as e:
            logger.warning(f"图片优化失败: {str(e)}")
            return image_data

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

        # 检测并增强风格
        if "商务" in optimized or "business" in optimized.lower():
            enhancements.append("professional corporate style")

        if "科技" in optimized or "tech" in optimized.lower():
            enhancements.append("futuristic technology aesthetic")

        # 添加质量增强词
        quality_terms = [
            "ultra-high quality",
            "8K resolution",
            "photorealistic",
            "professional photography"
        ]

        # 随机选择质量词避免重复
        selected_quality = random.choice(quality_terms)
        if selected_quality not in optimized.lower():
            enhancements.append(selected_quality)

        # 组合优化后的提示词
        if enhancements:
            optimized = f"{optimized}, {', '.join(enhancements)}"

        # 限制长度
        if len(optimized) > 500:
            optimized = optimized[:497] + "..."

        return optimized

    async def _preload_related_images(self, request: ImageRequest):
        """
        预加载相关图片

        Args:
            request: 当前图片请求
        """
        # 基于当前请求预测可能的后续请求
        related_prompts = self._generate_related_prompts(request.prompt)

        for prompt in related_prompts[:3]:  # 预加载最多3个相关图片
            # 检查是否已缓存
            cache_key = self._generate_cache_key_from_prompt(prompt)
            if not self.lru_cache.get(cache_key):
                # 添加到预加载队列
                self.preload_queue.append(prompt)

                # 异步生成（低优先级）
                preload_request = ImageRequest(
                    prompt=prompt,
                    request_id=f"preload_{cache_key}",
                    priority=0  # 最低优先级
                )

                asyncio.create_task(self._preload_image(preload_request))

    async def _preload_image(self, request: ImageRequest):
        """预加载单个图片"""
        try:
            await self.generate_image_async(request)
            logger.debug(f"预加载完成: {request.prompt[:50]}")
        except Exception as e:
            logger.debug(f"预加载失败: {str(e)}")

    def _generate_related_prompts(self, prompt: str) -> List[str]:
        """生成相关提示词"""
        related = []

        # 基于关键词生成变体
        keywords = prompt.split()[:5]  # 取前5个关键词

        # 生成变体
        variations = [
            "modern " + " ".join(keywords),
            "professional " + " ".join(keywords),
            "creative " + " ".join(keywords)
        ]

        for variation in variations:
            if variation != prompt:
                related.append(variation)

        return related

    def _create_optimized_placeholder(self, request: ImageRequest) -> bytes:
        """创建优化的占位图"""
        # 创建渐变背景的高质量占位图
        width = request.width
        height = request.height

        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)

        # 创建渐变背景
        for y in range(height):
            color_value = int(255 * (1 - y / height * 0.3))
            color = (color_value, color_value, 255)
            draw.rectangle([(0, y), (width, y + 1)], fill=color)

        # 添加文本
        text = request.prompt[:30] + "..." if len(request.prompt) > 30 else request.prompt

        try:
            font = ImageFont.load_default()
        except:
            font = None

        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = (height - text_height) // 2

            # 添加文本阴影
            draw.text((x + 2, y + 2), text, fill=(0, 0, 0, 128), font=font)
            draw.text((x, y), text, fill=(255, 255, 255), font=font)

        # 保存
        output = io.BytesIO()
        image.save(output, format='PNG', optimize=True)
        return output.getvalue()

    def _generate_cache_key(self, request: ImageRequest) -> str:
        """生成缓存键"""
        key_parts = [
            request.prompt,
            str(request.width),
            str(request.height),
            request.quality,
            request.model_preference or "default"
        ]

        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _generate_cache_key_from_prompt(self, prompt: str) -> str:
        """从提示词生成缓存键"""
        return hashlib.sha256(prompt.encode()).hexdigest()

    async def _s3_get_object_async(self, bucket: str, key: str):
        """异步S3获取对象"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: self.s3_client.get_object(Bucket=bucket, Key=key)
        )

    async def _s3_put_object_async(self, bucket: str, key: str, body: bytes):
        """异步S3上传对象"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType='image/png',
                Metadata={
                    'generated_at': str(int(time.time())),
                    'size': str(len(body))
                }
            )
        )

    def _update_performance_stats(self,
                                 model_config: ModelConfig,
                                 generation_time: float,
                                 success: bool):
        """更新性能统计"""
        self.performance_stats['total_requests'] += 1

        if success:
            self.performance_stats['successful_requests'] += 1
            self.performance_stats['total_generation_time'] += generation_time
            self.performance_stats['total_cost'] += model_config.cost_per_request

            # 更新模型成功率
            model_config.success_rate = min(1.0, model_config.success_rate * 1.01)
        else:
            self.performance_stats['failed_requests'] += 1

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        获取性能指标

        Returns:
            性能指标字典
        """
        total = self.performance_stats['total_requests']
        if total == 0:
            return {}

        return {
            'total_requests': total,
            'success_rate': self.performance_stats['successful_requests'] / total,
            'failure_rate': self.performance_stats['failed_requests'] / total,
            'cache_hit_rate': self.performance_stats['cache_hits'] / total,
            'avg_generation_time': self.performance_stats['total_generation_time'] /
                                  self.performance_stats['successful_requests']
                                  if self.performance_stats['successful_requests'] > 0 else 0,
            'total_cost': self.performance_stats['total_cost'],
            'lru_cache_stats': self.lru_cache.get_stats(),
            'model_stats': {
                model_id: {
                    'success_rate': config.success_rate,
                    'failure_count': config.failure_count,
                    'avg_response_time': config.avg_response_time
                }
                for model_id, config in self.model_configs.items()
            }
        }

    def send_metrics_to_cloudwatch(self):
        """发送指标到CloudWatch"""
        if not self.enable_monitoring:
            return

        metrics = self.get_performance_metrics()

        try:
            # 准备CloudWatch指标
            metric_data = [
                {
                    'MetricName': 'ImageGenerationSuccessRate',
                    'Value': metrics.get('success_rate', 0) * 100,
                    'Unit': 'Percent',
                    'Timestamp': datetime.now()
                },
                {
                    'MetricName': 'ImageGenerationAvgTime',
                    'Value': metrics.get('avg_generation_time', 0),
                    'Unit': 'Seconds',
                    'Timestamp': datetime.now()
                },
                {
                    'MetricName': 'ImageCacheHitRate',
                    'Value': metrics.get('cache_hit_rate', 0) * 100,
                    'Unit': 'Percent',
                    'Timestamp': datetime.now()
                },
                {
                    'MetricName': 'ImageGenerationCost',
                    'Value': metrics.get('total_cost', 0),
                    'Unit': 'None',
                    'Timestamp': datetime.now()
                }
            ]

            # 发送指标
            self.cloudwatch_client.put_metric_data(
                Namespace='AI-PPT-Assistant/ImageGeneration',
                MetricData=metric_data
            )

            logger.info("性能指标已发送到CloudWatch")

        except Exception as e:
            logger.error(f"发送CloudWatch指标失败: {str(e)}")


# Lambda处理器包装
def lambda_handler(event, context):
    """
    Lambda入口函数

    Args:
        event: Lambda事件
        context: Lambda上下文

    Returns:
        API响应
    """
    # 初始化服务（利用Lambda容器重用）
    global _service_instance
    if '_service_instance' not in globals():
        _service_instance = ImageProcessingServiceOptimized()

    service = _service_instance

    try:
        # 解析请求
        body = json.loads(event.get('body', '{}'))

        # 创建请求对象
        request = ImageRequest(
            prompt=body.get('prompt', ''),
            request_id=context.request_id,
            width=body.get('width', CONFIG.DEFAULT_IMAGE_WIDTH),
            height=body.get('height', CONFIG.DEFAULT_IMAGE_HEIGHT),
            quality=body.get('quality', 'premium'),
            model_preference=body.get('model', None),
            priority=body.get('priority', 1)
        )

        # 异步生成图片
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        response = loop.run_until_complete(
            service.generate_image_async(request)
        )

        # 发送监控指标
        service.send_metrics_to_cloudwatch()

        # 返回响应
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'X-Request-ID': request.request_id,
                'X-Model-Used': response.model_used,
                'X-Generation-Time': str(response.generation_time),
                'X-From-Cache': str(response.from_cache)
            },
            'body': json.dumps({
                'success': True,
                'image': base64.b64encode(response.image_data).decode('utf-8'),
                'metadata': {
                    'model': response.model_used,
                    'generation_time': response.generation_time,
                    'from_cache': response.from_cache,
                    'cost': response.cost
                },
                'performance_metrics': service.get_performance_metrics()
            })
        }

    except Exception as e:
        logger.error(f"Lambda处理失败: {str(e)}")

        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }

    finally:
        loop.close()