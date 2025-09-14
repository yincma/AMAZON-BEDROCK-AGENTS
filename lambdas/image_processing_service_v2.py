"""
图片处理服务V2 - 集成真实AI图片生成服务
"""

import logging
import io
from typing import Dict, Any, Optional, List
from PIL import Image

import boto3

try:
    from .image_config import CONFIG
    from .image_exceptions import ImageProcessingError, NovaServiceError
    from .image_s3_service import S3Service as ImageS3Service
    from .services.bedrock_image_service import BedrockImageService
    from .services.image_cache_service import ImageCacheService
except ImportError:
    from image_config import CONFIG
    from image_exceptions import ImageProcessingError, NovaServiceError
    from image_s3_service import S3Service as ImageS3Service
    from services.bedrock_image_service import BedrockImageService
    from services.image_cache_service import ImageCacheService

logger = logging.getLogger(__name__)


class ImageProcessingServiceV2:
    """增强版图片处理服务 - 集成真实AI生成和缓存"""

    def __init__(
        self,
        bedrock_client=None,
        s3_service=None,
        cache_service=None,
        enable_cache: bool = True
    ):
        """
        初始化服务

        Args:
            bedrock_client: Bedrock客户端
            s3_service: S3服务
            cache_service: 缓存服务
            enable_cache: 是否启用缓存
        """
        self.bedrock_service = BedrockImageService(bedrock_client)
        import os
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'default-bucket')
        self.s3_service = s3_service or ImageS3Service(bucket_name=bucket_name)
        self.cache_service = cache_service or ImageCacheService()
        self.enable_cache = enable_cache

    def generate_slide_image(
        self,
        slide_content: Dict[str, Any],
        presentation_id: str,
        slide_number: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        为幻灯片生成图片

        Args:
            slide_content: 幻灯片内容
            presentation_id: 演示文稿ID
            slide_number: 幻灯片编号
            context: 上下文信息（主题、风格等）

        Returns:
            包含图片URL和元数据的结果
        """
        try:
            # 生成优化的提示词
            prompt = self._generate_optimized_prompt(slide_content, context)
            negative_prompt = self._generate_negative_prompt(context)

            # 检查缓存
            if self.enable_cache:
                cache_key = self.cache_service.generate_cache_key(
                    prompt=prompt,
                    width=CONFIG.DEFAULT_IMAGE_WIDTH,
                    height=CONFIG.DEFAULT_IMAGE_HEIGHT,
                    style=context.get('style', 'business') if context else 'business'
                )

                cached = self.cache_service.get_cached_image(cache_key)
                if cached:
                    logger.info(f"Using cached image for slide {slide_number}")
                    # 保存到演示文稿的S3位置
                    s3_result = self.s3_service.save_image_with_metadata(
                        image_data=cached['image_data'],
                        metadata={
                            'source': 'cache',
                            'cache_key': cache_key,
                            **cached['metadata']
                        },
                        presentation_id=presentation_id,
                        slide_number=slide_number
                    )
                    return s3_result

            # 生成新图片
            logger.info(f"Generating new image for slide {slide_number}")
            generation_result = self.bedrock_service.generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=CONFIG.DEFAULT_IMAGE_WIDTH,
                height=CONFIG.DEFAULT_IMAGE_HEIGHT,
                style_preset=self._get_style_preset(context),
                use_cache=False  # 已经在上层处理缓存
            )

            # 优化图片
            optimized_image = self._optimize_image(
                generation_result['image_data']
            )

            # 保存到S3
            s3_result = self.s3_service.save_image_with_metadata(
                image_data=optimized_image,
                metadata={
                    'prompt': prompt,
                    'negative_prompt': negative_prompt,
                    'model': generation_result['model'],
                    'generated_at': generation_result['generated_at']
                },
                presentation_id=presentation_id,
                slide_number=slide_number
            )

            # 保存到缓存
            if self.enable_cache and s3_result['status'] == 'success':
                self.cache_service.save_to_cache(
                    cache_key=cache_key,
                    image_data=optimized_image,
                    metadata=generation_result
                )

            return s3_result

        except Exception as e:
            logger.error(f"Failed to generate image for slide {slide_number}: {e}")
            # 生成占位图作为fallback
            return self._generate_fallback_image(
                slide_content, presentation_id, slide_number
            )

    def batch_generate_images(
        self,
        slides: List[Dict[str, Any]],
        presentation_id: str,
        context: Optional[Dict[str, Any]] = None,
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """
        批量生成图片

        Args:
            slides: 幻灯片列表
            presentation_id: 演示文稿ID
            context: 上下文信息
            parallel: 是否并行处理

        Returns:
            生成结果列表
        """
        results = []

        if parallel:
            # 使用线程池并行处理
            from concurrent.futures import ThreadPoolExecutor, as_completed

            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_slide = {
                    executor.submit(
                        self.generate_slide_image,
                        slide['content'],
                        presentation_id,
                        slide['number'],
                        context
                    ): slide
                    for slide in slides
                }

                for future in as_completed(future_to_slide):
                    slide = future_to_slide[future]
                    try:
                        result = future.result(timeout=30)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Failed to generate image for slide {slide['number']}: {e}")
                        results.append({
                            'status': 'failed',
                            'slide_number': slide['number'],
                            'error': str(e)
                        })
        else:
            # 串行处理
            for slide in slides:
                try:
                    result = self.generate_slide_image(
                        slide['content'],
                        presentation_id,
                        slide['number'],
                        context
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to generate image for slide {slide['number']}: {e}")
                    results.append({
                        'status': 'failed',
                        'slide_number': slide['number'],
                        'error': str(e)
                    })

        return results

    def _generate_optimized_prompt(
        self,
        slide_content: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """生成优化的提示词"""
        title = slide_content.get('title', '')
        content = slide_content.get('content', [])

        # 基础提示词
        base_prompt = f"{title}"

        # 添加内容关键词
        if content:
            keywords = self._extract_keywords(content)
            if keywords:
                base_prompt += f", {', '.join(keywords[:3])}"

        # 使用Bedrock服务增强提示词
        if context:
            enhanced_prompt = self.bedrock_service.enhance_prompt(
                base_prompt, context
            )
        else:
            enhanced_prompt = f"{base_prompt}, professional presentation slide, high quality"

        return enhanced_prompt

    def _generate_negative_prompt(
        self,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """生成负面提示词"""
        negative_prompts = [
            "low quality",
            "blurry",
            "pixelated",
            "watermark",
            "text overlay",
            "distorted"
        ]

        # 根据上下文添加特定的负面提示词
        if context:
            style = context.get('style', 'business')
            if style == 'business':
                negative_prompts.extend([
                    "casual", "unprofessional", "messy"
                ])
            elif style == 'technical':
                negative_prompts.extend([
                    "artistic", "abstract", "decorative"
                ])

        return ", ".join(negative_prompts)

    def _get_style_preset(self, context: Optional[Dict[str, Any]]) -> str:
        """获取风格预设"""
        if not context:
            return "photographic"

        style_map = {
            'business': 'photographic',
            'technical': 'digital-art',
            'creative': 'fantasy-art',
            'educational': 'line-art',
            'minimal': 'low-poly'
        }

        style = context.get('style', 'business')
        return style_map.get(style, 'photographic')

    def _optimize_image(self, image_data: bytes) -> bytes:
        """优化图片（压缩、调整大小等）"""
        try:
            with io.BytesIO(image_data) as img_buffer:
                image = Image.open(img_buffer)

                # 确保是RGB模式
                if image.mode != 'RGB':
                    image = image.convert('RGB')

                # 调整大小（如果需要）
                max_width = CONFIG.DEFAULT_IMAGE_WIDTH
                max_height = CONFIG.DEFAULT_IMAGE_HEIGHT

                if image.width > max_width or image.height > max_height:
                    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                # 保存优化后的图片
                output_buffer = io.BytesIO()
                image.save(
                    output_buffer,
                    format='PNG',
                    optimize=True,
                    quality=95
                )

                return output_buffer.getvalue()

        except Exception as e:
            logger.warning(f"Failed to optimize image: {e}")
            return image_data

    def _extract_keywords(self, content: List[str]) -> List[str]:
        """从内容中提取关键词"""
        # 简单的关键词提取（实际应用中可以使用NLP库）
        keywords = []
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}

        for item in content:
            words = item.lower().split()
            for word in words:
                if len(word) > 3 and word not in stop_words:
                    keywords.append(word)

        # 去重并返回前几个
        return list(dict.fromkeys(keywords))[:5]

    def _generate_fallback_image(
        self,
        slide_content: Dict[str, Any],
        presentation_id: str,
        slide_number: int
    ) -> Dict[str, Any]:
        """生成fallback占位图"""
        try:
            # 使用原始服务生成占位图
            from image_processing_service import ImageProcessingService
            fallback_service = ImageProcessingService()

            placeholder = fallback_service.create_placeholder_image(
                width=CONFIG.DEFAULT_IMAGE_WIDTH,
                height=CONFIG.DEFAULT_IMAGE_HEIGHT,
                text=slide_content.get('title', 'Image')[:50]
            )

            # 保存到S3
            s3_result = self.s3_service.save_image_with_metadata(
                image_data=placeholder,
                metadata={
                    'type': 'placeholder',
                    'reason': 'generation_failed'
                },
                presentation_id=presentation_id,
                slide_number=slide_number
            )

            return s3_result

        except Exception as e:
            logger.error(f"Failed to generate fallback image: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }