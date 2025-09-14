"""
优化版PPT生成Lambda处理器
集成缓存、并行处理和性能优化

主要优化：
1. 多级缓存（内存/Redis）
2. 并行内容和图片生成
3. 连接池复用
4. 请求批处理
5. 预热机制
"""

import json
import os
import sys
import uuid
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

# 导入性能优化组件
from cache_manager import (
    get_cache_instance,
    CacheKeyGenerator,
    CacheWarmer,
    cached_function
)
from performance_optimizer import (
    PerformanceOptimizer,
    ParallelProcessor,
    ConnectionPoolManager
)

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 全局实例（Lambda容器复用）
cache = None
optimizer = None
conn_pool = None
parallel_processor = None


def init_globals():
    """初始化全局实例（利用Lambda容器复用）"""
    global cache, optimizer, conn_pool, parallel_processor

    if cache is None:
        cache = get_cache_instance()
        logger.info("Initialized cache instance")

    if optimizer is None:
        optimizer = PerformanceOptimizer()
        logger.info("Initialized performance optimizer")

    if conn_pool is None:
        conn_pool = ConnectionPoolManager()
        logger.info("Initialized connection pool")

    if parallel_processor is None:
        parallel_processor = ParallelProcessor(max_workers=10)
        logger.info("Initialized parallel processor")


def lambda_handler(event, context):
    """
    优化的Lambda处理函数

    Args:
        event: API Gateway事件
        context: Lambda上下文

    Returns:
        API响应
    """
    start_time = time.time()

    # 初始化全局实例
    init_globals()

    try:
        # 1. 解析请求
        if isinstance(event.get('body'), str):
            body = json.loads(event.get('body', '{}'))
        else:
            body = event.get('body', {})

        # 提取参数
        topic = body.get('topic')
        page_count = body.get('page_count', 10)
        template = body.get('template', 'modern')
        with_images = body.get('with_images', True)
        use_cache = body.get('use_cache', True)
        parallel_processing = body.get('parallel_processing', True)
        priority = body.get('priority', 'normal')

        # 验证输入
        if not topic:
            return create_response(400, {
                'error': 'Topic is required',
                'code': 'MISSING_TOPIC'
            })

        if not 1 <= page_count <= 30:
            return create_response(400, {
                'error': 'Page count must be between 1 and 30',
                'code': 'INVALID_PAGE_COUNT'
            })

        # 2. 生成请求ID和缓存键
        presentation_id = f"ppt-{uuid.uuid4().hex[:8]}"
        cache_key = CacheKeyGenerator.generate_presentation_key(
            topic=topic,
            page_count=page_count,
            template=template,
            with_images=with_images
        )

        logger.info(f"Processing request: {presentation_id}, cache_key: {cache_key}")

        # 3. 检查缓存（如果启用）
        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for presentation: {presentation_id}")

                # 更新缓存统计
                update_cache_stats('hit')

                # 快速返回缓存结果
                response_time = time.time() - start_time
                cached_result['presentation_id'] = presentation_id
                cached_result['cache_hit'] = True
                cached_result['response_time'] = response_time

                return create_response(200, cached_result)

        # 4. 缓存未命中，生成新内容
        logger.info(f"Cache miss for presentation: {presentation_id}, generating new content")
        update_cache_stats('miss')

        # 5. 使用优化器生成PPT
        generation_request = {
            'presentation_id': presentation_id,
            'topic': topic,
            'page_count': page_count,
            'template': template,
            'with_images': with_images,
            'parallel_processing': parallel_processing,
            'use_cache': use_cache,
            'priority': priority
        }

        # 根据优先级处理
        if priority == 'high':
            result = process_high_priority(generation_request)
        elif parallel_processing:
            result = process_parallel(generation_request)
        else:
            result = process_serial(generation_request)

        # 6. 验证生成结果
        if result.get('status') != 'success':
            logger.error(f"Generation failed: {result.get('error')}")
            return create_response(500, {
                'error': 'PPT generation failed',
                'details': result.get('error'),
                'presentation_id': presentation_id
            })

        # 7. 存储到缓存（如果成功）
        if use_cache and result.get('status') == 'success':
            # 计算TTL（根据内容复杂度）
            ttl = calculate_cache_ttl(page_count, with_images)

            # 异步存储到缓存
            cache.set(cache_key, result, ttl=ttl)
            logger.info(f"Cached result with TTL: {ttl} seconds")

        # 8. 计算最终响应时间
        total_time = time.time() - start_time
        result['response_time'] = total_time
        result['presentation_id'] = presentation_id
        result['cache_hit'] = False

        # 9. 记录性能指标
        log_performance_metrics(presentation_id, total_time, page_count)

        # 10. 返回成功响应
        return create_response(200, result)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_response(500, {
            'error': 'Internal server error',
            'message': str(e),
            'presentation_id': presentation_id if 'presentation_id' in locals() else None
        })


def process_parallel(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    并行处理PPT生成

    Args:
        request: 生成请求

    Returns:
        生成结果
    """
    start_time = time.time()
    presentation_id = request['presentation_id']
    page_count = request['page_count']

    try:
        # 并行生成大纲、内容和图片
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 提交任务
            outline_future = executor.submit(generate_outline, request)
            content_futures = []
            image_futures = []

            # 等待大纲完成
            outline = outline_future.result(timeout=10)

            # 基于大纲并行生成内容和图片
            for i in range(page_count):
                slide_data = {
                    'slide_number': i + 1,
                    'topic': request['topic'],
                    'template': request['template'],
                    'outline': outline['slides'][i] if i < len(outline.get('slides', [])) else {}
                }

                # 内容生成任务
                content_future = executor.submit(generate_slide_content, slide_data)
                content_futures.append(content_future)

                # 图片生成任务（如果需要）
                if request.get('with_images'):
                    image_future = executor.submit(generate_slide_image, slide_data)
                    image_futures.append(image_future)

            # 收集结果
            slides = []
            for i, content_future in enumerate(as_completed(content_futures, timeout=25)):
                try:
                    content = content_future.result()
                    slide = {
                        'slide_number': i + 1,
                        'content': content
                    }

                    # 添加图片（如果有）
                    if image_futures and i < len(image_futures):
                        try:
                            image = image_futures[i].result(timeout=5)
                            slide['image'] = image
                        except:
                            slide['image'] = None

                    slides.append(slide)
                except Exception as e:
                    logger.error(f"Failed to generate slide {i+1}: {e}")
                    slides.append({
                        'slide_number': i + 1,
                        'content': {'error': str(e)},
                        'image': None
                    })

        # 计算性能指标
        total_time = time.time() - start_time
        parallel_efficiency = calculate_parallel_efficiency(total_time, page_count)

        return {
            'status': 'success',
            'presentation_id': presentation_id,
            'outline': outline,
            'slides': sorted(slides, key=lambda x: x['slide_number']),
            'generation_time': total_time,
            'parallel_efficiency': parallel_efficiency,
            'optimization_method': 'parallel'
        }

    except Exception as e:
        logger.error(f"Parallel processing failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'presentation_id': presentation_id
        }


def process_serial(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    串行处理PPT生成（降级模式）

    Args:
        request: 生成请求

    Returns:
        生成结果
    """
    start_time = time.time()
    presentation_id = request['presentation_id']
    page_count = request['page_count']

    try:
        # 串行生成
        outline = generate_outline(request)
        slides = []

        for i in range(page_count):
            slide_data = {
                'slide_number': i + 1,
                'topic': request['topic'],
                'template': request['template'],
                'outline': outline['slides'][i] if i < len(outline.get('slides', [])) else {}
            }

            # 生成内容
            content = generate_slide_content(slide_data)

            # 生成图片（如果需要）
            image = None
            if request.get('with_images'):
                image = generate_slide_image(slide_data)

            slides.append({
                'slide_number': i + 1,
                'content': content,
                'image': image
            })

        total_time = time.time() - start_time

        return {
            'status': 'success',
            'presentation_id': presentation_id,
            'outline': outline,
            'slides': slides,
            'generation_time': total_time,
            'optimization_method': 'serial'
        }

    except Exception as e:
        logger.error(f"Serial processing failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'presentation_id': presentation_id
        }


def process_high_priority(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    高优先级处理（分配更多资源）

    Args:
        request: 生成请求

    Returns:
        生成结果
    """
    # 为高优先级请求分配更多并行资源
    request['parallel_workers'] = 15  # 增加并行度
    return process_parallel(request)


@cached_function(ttl=300, cache_level="l1")
def generate_outline(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成PPT大纲（带缓存）

    Args:
        request: 包含topic, page_count等信息

    Returns:
        大纲数据
    """
    # 这里应该调用实际的大纲生成逻辑
    # 为了演示，返回模拟数据
    topic = request['topic']
    page_count = request['page_count']

    slides = []
    for i in range(page_count):
        if i == 0:
            title = f"{topic} - 概述"
        elif i == page_count - 1:
            title = "总结与展望"
        else:
            title = f"{topic} - 第{i}部分"

        slides.append({
            'number': i + 1,
            'title': title,
            'key_points': [f"要点{j+1}" for j in range(3)]
        })

    return {
        'title': topic,
        'slides': slides,
        'generated_at': datetime.now().isoformat()
    }


def generate_slide_content(slide_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    生成幻灯片内容

    Args:
        slide_data: 幻灯片数据

    Returns:
        内容数据
    """
    # 模拟内容生成延迟
    time.sleep(0.2)

    return {
        'title': slide_data.get('outline', {}).get('title', f"Slide {slide_data['slide_number']}"),
        'bullets': [
            f"内容点 {i+1} for slide {slide_data['slide_number']}"
            for i in range(3)
        ],
        'notes': f"演讲者备注 for slide {slide_data['slide_number']}"
    }


def generate_slide_image(slide_data: Dict[str, Any]) -> Optional[str]:
    """
    生成幻灯片图片

    Args:
        slide_data: 幻灯片数据

    Returns:
        图片URL或None
    """
    # 模拟图片生成延迟
    time.sleep(0.3)

    # 返回模拟的图片URL
    return f"https://example.com/images/slide_{slide_data['slide_number']}.jpg"


def calculate_cache_ttl(page_count: int, with_images: bool) -> int:
    """
    计算缓存TTL

    Args:
        page_count: 页数
        with_images: 是否包含图片

    Returns:
        TTL（秒）
    """
    # 基础TTL: 1小时
    base_ttl = 3600

    # 根据复杂度调整
    if page_count > 15:
        base_ttl *= 2  # 复杂PPT缓存更久
    if with_images:
        base_ttl = int(base_ttl * 1.5)  # 带图片的缓存更久

    # 最大24小时
    return min(base_ttl, 86400)


def calculate_parallel_efficiency(total_time: float, page_count: int) -> float:
    """
    计算并行效率

    Args:
        total_time: 总时间
        page_count: 页数

    Returns:
        效率值（0-1）
    """
    # 估算串行时间
    estimated_serial_time = page_count * 0.5  # 每页0.5秒

    if estimated_serial_time == 0:
        return 1.0

    # 计算效率
    efficiency = (estimated_serial_time - total_time) / estimated_serial_time
    return max(0, min(1, efficiency))


def update_cache_stats(event_type: str):
    """
    更新缓存统计

    Args:
        event_type: 'hit' 或 'miss'
    """
    try:
        # 这里可以发送到CloudWatch
        logger.info(f"Cache {event_type}")
    except:
        pass


def log_performance_metrics(presentation_id: str, total_time: float, page_count: int):
    """
    记录性能指标

    Args:
        presentation_id: 演示文稿ID
        total_time: 总时间
        page_count: 页数
    """
    try:
        metrics = {
            'presentation_id': presentation_id,
            'total_time': total_time,
            'page_count': page_count,
            'time_per_page': total_time / page_count if page_count > 0 else 0,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"Performance metrics: {json.dumps(metrics)}")

        # 发送到CloudWatch（如果需要）
        # cloudwatch_client.put_metric_data(...)

    except Exception as e:
        logger.error(f"Failed to log metrics: {e}")


def create_response(status_code: int, body: Any) -> Dict[str, Any]:
    """
    创建标准API响应

    Args:
        status_code: HTTP状态码
        body: 响应体

    Returns:
        API Gateway响应格式
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Cache-Control': 'no-cache' if status_code != 200 else 'max-age=300'
        },
        'body': json.dumps(body, ensure_ascii=False, default=str)
    }


# 预热处理器（用于Lambda预热）
def warmer_handler(event, context):
    """
    Lambda预热处理器

    Args:
        event: 预热事件
        context: Lambda上下文

    Returns:
        预热响应
    """
    if event.get('source') == 'serverless-plugin-warmup':
        logger.info('Lambda warmer invocation')

        # 初始化全局实例
        init_globals()

        # 预热缓存
        if cache:
            warmer = CacheWarmer(cache)
            warmed_count = warmer.warm_popular_content(top_n=10)
            logger.info(f"Warmed {warmed_count} cache items")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Lambda is warm'})
        }

    # 不是预热请求，执行正常处理
    return handler(event, context)