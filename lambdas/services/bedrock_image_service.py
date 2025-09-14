"""
Bedrock图片生成服务 - 统一管理所有AI图片生成模型的调用
"""

import json
import base64
import logging
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from enum import Enum

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ImageModel(Enum):
    """支持的图片生成模型"""
    NOVA_CANVAS = "amazon.nova-canvas-v1:0"
    STABILITY_SDXL = "stability.stable-diffusion-xl-v1"
    TITAN_IMAGE = "amazon.titan-image-generator-v2:0"

    @property
    def priority(self) -> int:
        """模型优先级（数字越小优先级越高）"""
        priorities = {
            self.NOVA_CANVAS: 1,
            self.STABILITY_SDXL: 2,
            self.TITAN_IMAGE: 3
        }
        return priorities.get(self, 999)


class BedrockImageService:
    """Bedrock图片生成服务"""

    def __init__(self, bedrock_client=None, cache_client=None):
        """
        初始化服务

        Args:
            bedrock_client: Bedrock Runtime客户端
            cache_client: 缓存客户端（DynamoDB或ElastiCache）
        """
        self.bedrock_client = bedrock_client or boto3.client('bedrock-runtime')
        self.cache_client = cache_client
        self.model_chain = sorted(ImageModel, key=lambda m: m.priority)

    def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 768,
        style_preset: str = "photographic",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        生成图片（带fallback机制）

        Args:
            prompt: 图片生成提示词
            negative_prompt: 负面提示词（不想出现的内容）
            width: 图片宽度
            height: 图片高度
            style_preset: 风格预设
            use_cache: 是否使用缓存

        Returns:
            包含图片数据和元信息的字典
        """
        # 检查缓存
        if use_cache and self.cache_client:
            cache_key = self._generate_cache_key(prompt, width, height, style_preset)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.info(f"Cache hit for prompt: {prompt[:50]}...")
                return cached_result

        # 尝试所有模型
        last_error = None
        for model in self.model_chain:
            try:
                logger.info(f"Attempting to generate image with {model.name}")
                result = self._generate_with_model(
                    model=model,
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                    style_preset=style_preset
                )

                # 保存到缓存
                if use_cache and self.cache_client:
                    self._save_to_cache(cache_key, result)

                return result

            except Exception as e:
                logger.warning(f"Failed with {model.name}: {str(e)}")
                last_error = e
                continue

        # 所有模型都失败
        raise Exception(f"All image generation models failed. Last error: {last_error}")

    def _generate_with_model(
        self,
        model: ImageModel,
        prompt: str,
        negative_prompt: Optional[str],
        width: int,
        height: int,
        style_preset: str
    ) -> Dict[str, Any]:
        """
        使用特定模型生成图片
        """
        if model == ImageModel.NOVA_CANVAS:
            return self._generate_nova_canvas(prompt, negative_prompt, width, height, style_preset)
        elif model == ImageModel.STABILITY_SDXL:
            return self._generate_stability_sdxl(prompt, negative_prompt, width, height, style_preset)
        elif model == ImageModel.TITAN_IMAGE:
            return self._generate_titan_image(prompt, negative_prompt, width, height)
        else:
            raise ValueError(f"Unsupported model: {model}")

    def _generate_nova_canvas(
        self,
        prompt: str,
        negative_prompt: Optional[str],
        width: int,
        height: int,
        style_preset: str
    ) -> Dict[str, Any]:
        """
        使用Amazon Nova Canvas生成图片
        """
        # Nova Canvas API格式
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt,
                "negativeText": negative_prompt or "",
                "numberOfImages": 1,
                "quality": "premium",
                "width": width,
                "height": height,
                "cfgScale": 8.0,
                "seed": None
            }
        }

        response = self.bedrock_client.invoke_model(
            modelId=ImageModel.NOVA_CANVAS.value,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())

        if 'images' not in response_body or len(response_body['images']) == 0:
            raise Exception("No images in Nova Canvas response")

        return {
            'image_data': base64.b64decode(response_body['images'][0]),
            'model': ImageModel.NOVA_CANVAS.value,
            'prompt': prompt,
            'width': width,
            'height': height,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

    def _generate_stability_sdxl(
        self,
        prompt: str,
        negative_prompt: Optional[str],
        width: int,
        height: int,
        style_preset: str
    ) -> Dict[str, Any]:
        """
        使用Stability AI SDXL生成图片
        """
        # Stability SDXL API格式
        request_body = {
            "text_prompts": [
                {"text": prompt, "weight": 1.0}
            ],
            "cfg_scale": 7.0,
            "steps": 30,
            "seed": 0,
            "width": width,
            "height": height,
            "style_preset": style_preset
        }

        if negative_prompt:
            request_body["text_prompts"].append(
                {"text": negative_prompt, "weight": -1.0}
            )

        response = self.bedrock_client.invoke_model(
            modelId=ImageModel.STABILITY_SDXL.value,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())

        if 'artifacts' not in response_body or len(response_body['artifacts']) == 0:
            raise Exception("No artifacts in Stability response")

        return {
            'image_data': base64.b64decode(response_body['artifacts'][0]['base64']),
            'model': ImageModel.STABILITY_SDXL.value,
            'prompt': prompt,
            'width': width,
            'height': height,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

    def _generate_titan_image(
        self,
        prompt: str,
        negative_prompt: Optional[str],
        width: int,
        height: int
    ) -> Dict[str, Any]:
        """
        使用Amazon Titan Image生成图片
        """
        # Titan Image API格式
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "premium",
                "height": height,
                "width": width,
                "cfgScale": 8.0,
                "seed": 0
            }
        }

        if negative_prompt:
            request_body["textToImageParams"]["negativeText"] = negative_prompt

        response = self.bedrock_client.invoke_model(
            modelId=ImageModel.TITAN_IMAGE.value,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())

        if 'images' not in response_body or len(response_body['images']) == 0:
            raise Exception("No images in Titan response")

        return {
            'image_data': base64.b64decode(response_body['images'][0]),
            'model': ImageModel.TITAN_IMAGE.value,
            'prompt': prompt,
            'width': width,
            'height': height,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

    def _generate_cache_key(
        self,
        prompt: str,
        width: int,
        height: int,
        style_preset: str
    ) -> str:
        """生成缓存键"""
        key_data = f"{prompt}:{width}:{height}:{style_preset}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取图片"""
        if not self.cache_client:
            return None

        try:
            # 这里需要根据实际的缓存服务实现
            # 示例：DynamoDB缓存
            return None  # TODO: 实现缓存读取
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
            return None

    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """保存到缓存"""
        if not self.cache_client:
            return

        try:
            # 这里需要根据实际的缓存服务实现
            # 示例：DynamoDB缓存
            pass  # TODO: 实现缓存保存
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    def enhance_prompt(self, base_prompt: str, context: Dict[str, Any]) -> str:
        """
        增强提示词

        Args:
            base_prompt: 基础提示词
            context: 上下文信息（如主题、风格、受众等）

        Returns:
            增强后的提示词
        """
        enhancements = []

        # 添加质量增强词
        enhancements.append("high quality, professional, 4K resolution")

        # 根据主题添加风格
        theme = context.get('theme', 'business')
        if theme == 'business':
            enhancements.append("corporate style, modern office environment")
        elif theme == 'technical':
            enhancements.append("futuristic, technology focused, digital art")
        elif theme == 'educational':
            enhancements.append("educational, clear visualization, informative")

        # 根据受众调整
        audience = context.get('audience', 'general')
        if audience == 'executive':
            enhancements.append("executive presentation, premium quality")
        elif audience == 'technical':
            enhancements.append("detailed technical illustration")

        # 组合提示词
        enhanced_prompt = f"{base_prompt}, {', '.join(enhancements)}"

        return enhanced_prompt

    def batch_generate(
        self,
        prompts: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量生成图片

        Args:
            prompts: 提示词列表
            **kwargs: 其他生成参数

        Returns:
            生成结果列表
        """
        results = []
        for prompt in prompts:
            try:
                result = self.generate_image(prompt, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to generate image for prompt: {prompt[:50]}... Error: {e}")
                results.append({
                    'error': str(e),
                    'prompt': prompt,
                    'status': 'failed'
                })

        return results