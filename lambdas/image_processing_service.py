"""
图片处理服务模块 - 专门处理图片生成和处理逻辑
"""

import logging
import io
import json
import base64
import time
import random
import hashlib
from typing import Dict, Any, List, Tuple, Optional

from PIL import Image, ImageDraw, ImageFont
import boto3
from botocore.exceptions import ClientError, BotoCoreError

try:
    from .image_config import CONFIG
    from .image_exceptions import ImageProcessingError, NovaServiceError
except ImportError:
    from image_config import CONFIG
    from image_exceptions import ImageProcessingError, NovaServiceError

logger = logging.getLogger(__name__)


class ImageProcessingService:
    """图片处理服务类 - 单一责任：处理图片生成、优化和验证"""

    def __init__(self, bedrock_client=None, s3_client=None, enable_caching=True):
        """
        初始化图片处理服务

        Args:
            bedrock_client: Bedrock客户端实例，如果不提供则创建新的
            s3_client: S3客户端实例，用于缓存
            enable_caching: 是否启用缓存
        """
        self.bedrock_client = bedrock_client or boto3.client('bedrock-runtime')
        self.s3_client = s3_client or boto3.client('s3') if enable_caching else None
        self.enable_caching = enable_caching
        self._cache = {}  # 内存缓存

        # 支持的模型列表，按优先级排序
        self.supported_models = [
            "amazon.nova-canvas-v1:0",
            "stability.stable-diffusion-xl-v1"
        ]

    def generate_prompt(self, slide_content: Dict[str, Any], target_audience: str = "business") -> str:
        """
        根据幻灯片内容生成图片提示词

        Args:
            slide_content: 幻灯片内容，包含title和content字段
            target_audience: 目标受众类型

        Returns:
            生成的图片提示词字符串
        """
        title = slide_content.get('title', '').strip()
        content_list = slide_content.get('content', [])

        # 处理空内容的情况
        if not title and not content_list:
            return "专业商务演示背景，现代简洁风格，高质量4K，商务风格"

        # 提取关键词
        keywords = []
        if title:
            keywords.append(title)

        # 从内容中提取关键词
        content_text = " ".join(content_list) if content_list else ""
        if content_text:
            keywords.append(content_text)

        all_text = " ".join(keywords).lower()

        # 咨询公司风格的基础提示词
        base_prompt = "顶级咨询公司风格的专业商务图片，极简主义设计，高端商务感，4K超清晰度"

        # 根据内容添加特定描述
        style_additions = self._analyze_content_style(all_text)

        # 根据受众类型添加特定描述
        audience_style = self._get_audience_style(target_audience)

        # 添加咨询公司特有的视觉元素
        consultant_elements = "抽象几何图形，数据可视化元素，专业图表，商务蓝配色方案"

        # 组合最终提示词 - 更强调专业性和洞察力
        final_prompt = f"{base_prompt}，{title}相关的战略洞察图像，{consultant_elements}，{' '.join(style_additions[:2])}，{audience_style}，无文字，清晰简洁"

        return final_prompt

    def call_image_generation(self, prompt: str, model_preference: str = None) -> bytes:
        """
        使用Amazon Nova等服务生成真实的AI图片，支持多级fallback

        Args:
            prompt: 图片生成提示词
            model_preference: 首选模型，如果不指定则使用默认顺序

        Returns:
            生成的图片数据

        Raises:
            ImageProcessingError: 所有生成方式都失败时
        """
        # 优化提示词
        optimized_prompt = self._optimize_prompt(prompt)

        # 检查缓存
        if self.enable_caching:
            cached_image = self._get_cached_image(optimized_prompt)
            if cached_image:
                logger.info("从缓存返回图片")
                return cached_image

        # 确定模型尝试顺序
        models_to_try = self._get_model_priority_list(model_preference)

        last_error = None
        for model_id in models_to_try:
            try:
                logger.info(f"尝试使用模型 {model_id} 生成图片")
                image_data = self._call_bedrock_model(optimized_prompt, model_id)

                # 缓存成功的结果
                if self.enable_caching:
                    self._cache_image(optimized_prompt, image_data)

                logger.info(f"模型 {model_id} 成功生成图片")
                return image_data

            except Exception as e:
                last_error = e
                logger.warning(f"模型 {model_id} 调用失败: {str(e)}，尝试下一个模型")
                continue

        # 所有模型都失败，记录详细错误并回退到占位图
        logger.error(f"所有模型都失败，最后错误: {str(last_error)}")
        logger.warning("回退到高质量占位图")
        return self.create_placeholder_image(
            CONFIG.DEFAULT_IMAGE_WIDTH,
            CONFIG.DEFAULT_IMAGE_HEIGHT,
            prompt[:50] + "..." if len(prompt) > 50 else prompt
        )

    def _call_bedrock_model(self, prompt: str, model_id: str) -> bytes:
        """
        调用指定的Bedrock模型生成图片，支持重试机制

        Args:
            prompt: 图片生成提示词
            model_id: 模型ID

        Returns:
            生成的图片字节数据

        Raises:
            NovaServiceError: API调用失败
        """
        for attempt in range(CONFIG.MAX_RETRY_ATTEMPTS):
            try:
                if model_id == "amazon.nova-canvas-v1:0":
                    return self._call_nova_api(prompt, model_id)
                elif model_id.startswith("stability."):
                    return self._call_stability_api(prompt, model_id)
                else:
                    raise NovaServiceError(f"不支持的模型: {model_id}")

            except (ClientError, BotoCoreError) as e:
                if attempt < CONFIG.MAX_RETRY_ATTEMPTS - 1:
                    # 指数退避
                    delay = CONFIG.RETRY_DELAY_SECONDS * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"第{attempt + 1}次尝试失败，{delay:.2f}秒后重试: {str(e)}")
                    time.sleep(delay)
                else:
                    raise NovaServiceError(f"模型 {model_id} 调用失败: {str(e)}", service_response=getattr(e, 'response', None))
            except Exception as e:
                logger.error(f"处理模型 {model_id} 响应时出错: {str(e)}")
                raise NovaServiceError(f"处理模型 {model_id} 响应时出错: {str(e)}")

    def _call_nova_api(self, prompt: str, model_id: str) -> bytes:
        """
        调用Amazon Nova Canvas API生成图片

        Args:
            prompt: 图片生成提示词
            model_id: Nova模型ID

        Returns:
            生成的图片字节数据

        Raises:
            NovaServiceError: API调用失败
        """
        # 构建Nova API请求体
        request_body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {
                "text": prompt
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "quality": "premium",
                "width": CONFIG.DEFAULT_IMAGE_WIDTH,
                "height": CONFIG.DEFAULT_IMAGE_HEIGHT,
                "cfgScale": 8.0,
                "seed": 42
            }
        }

        # 调用Bedrock Nova模型
        response = self.bedrock_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        # 解析响应
        response_body = json.loads(response['body'].read())

        # 从响应中提取图片数据
        if 'images' in response_body and len(response_body['images']) > 0:
            image_base64 = response_body['images'][0]
            image_data = base64.b64decode(image_base64)

            logger.info(f"Nova模型 {model_id} 调用成功，生成真实AI图片")
            return image_data
        else:
            raise NovaServiceError("Nova API响应中没有图片数据")

    def _call_stability_api(self, prompt: str, model_id: str) -> bytes:
        """
        调用Stability AI API生成图片

        Args:
            prompt: 图片生成提示词
            model_id: Stability模型ID

        Returns:
            生成的图片字节数据

        Raises:
            NovaServiceError: API调用失败
        """
        # 构建Stability API请求体
        request_body = {
            "text_prompts": [
                {
                    "text": prompt,
                    "weight": 1.0
                }
            ],
            "cfg_scale": 8,
            "width": CONFIG.DEFAULT_IMAGE_WIDTH,
            "height": CONFIG.DEFAULT_IMAGE_HEIGHT,
            "samples": 1,
            "steps": 50
        }

        # 调用Bedrock Stability模型
        response = self.bedrock_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )

        # 解析响应
        response_body = json.loads(response['body'].read())

        # 从响应中提取图片数据
        if 'artifacts' in response_body and len(response_body['artifacts']) > 0:
            image_base64 = response_body['artifacts'][0]['base64']
            image_data = base64.b64decode(image_base64)

            logger.info(f"Stability模型 {model_id} 调用成功，生成真实AI图片")
            return image_data
        else:
            raise NovaServiceError("Stability API响应中没有图片数据")

    def create_placeholder_image(self, width: int = None, height: int = None, text: str = "图片占位符") -> bytes:
        """
        创建占位图片

        Args:
            width: 图片宽度，默认使用配置值
            height: 图片高度，默认使用配置值
            text: 显示文本

        Returns:
            图片字节数据

        Raises:
            ImageProcessingError: 图片创建失败
        """
        try:
            width = width or CONFIG.DEFAULT_IMAGE_WIDTH
            height = height or CONFIG.DEFAULT_IMAGE_HEIGHT

            # 创建图片
            image = Image.new('RGB', (width, height), CONFIG.PLACEHOLDER_COLOR)
            draw = ImageDraw.Draw(image)

            # 尝试加载字体
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
                logger.warning("无法加载默认字体，将使用系统字体")

            # 计算文本位置
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                # 估算文本大小
                text_width = len(text) * 8
                text_height = 16

            x = (width - text_width) // 2
            y = (height - text_height) // 2

            # 绘制文本
            draw.text((x, y), text, fill=CONFIG.TEXT_COLOR, font=font)

            # 保存到字节流
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue()

        except Exception as e:
            logger.error(f"创建占位图失败: {str(e)}")
            raise ImageProcessingError(
                message=f"创建占位图失败: {str(e)}",
                processing_step="placeholder_creation"
            ) from e

    def validate_image_format(self, image_data: bytes, expected_format: str = 'PNG') -> bool:
        """
        验证图片格式

        Args:
            image_data: 图片数据
            expected_format: 期望的格式

        Returns:
            验证结果
        """
        try:
            with io.BytesIO(image_data) as img_buffer:
                image = Image.open(img_buffer)
                return image.format == expected_format.upper()
        except Exception as e:
            logger.warning(f"图片格式验证失败: {str(e)}")
            return False

    def optimize_image_size(self, image_data: bytes, target_width: int = None,
                           target_height: int = None) -> bytes:
        """
        优化图片尺寸

        Args:
            image_data: 原始图片数据
            target_width: 目标宽度，默认使用配置值
            target_height: 目标高度，默认使用配置值

        Returns:
            优化后的图片数据
        """
        try:
            target_width = target_width or CONFIG.DEFAULT_IMAGE_WIDTH
            target_height = target_height or CONFIG.DEFAULT_IMAGE_HEIGHT

            with io.BytesIO(image_data) as img_buffer:
                image = Image.open(img_buffer)

                # 如果图片已经是目标尺寸或更小，直接返回
                if image.width <= target_width and image.height <= target_height:
                    return image_data

                # 计算缩放比例，保持长宽比
                width_ratio = target_width / image.width
                height_ratio = target_height / image.height
                scale_ratio = min(width_ratio, height_ratio)

                new_width = int(image.width * scale_ratio)
                new_height = int(image.height * scale_ratio)

                # 调整大小
                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # 保存到字节流
                output_buffer = io.BytesIO()
                resized_image.save(output_buffer, format='PNG')
                return output_buffer.getvalue()

        except Exception as e:
            logger.error(f"图片尺寸优化失败: {str(e)}")
            return image_data  # 返回原始数据

    def _analyze_content_style(self, content_text: str) -> List[str]:
        """分析内容并返回风格建议"""
        style_additions = []

        # AI/技术相关
        if any(word in content_text for word in ["ai", "人工智能", "技术", "科技", "算法", "数据", "智能"]):
            style_additions.extend([
                "科技感强烈的未来主义设计",
                "蓝色和白色配色方案",
                "抽象的数据可视化元素"
            ])

        # 商务相关
        elif any(word in content_text for word in ["商务", "业务", "管理", "策略", "市场", "分析"]):
            style_additions.extend([
                "现代办公环境",
                "简洁的图表和图形",
                "专业的配色方案"
            ])

        # 教育相关
        elif any(word in content_text for word in ["教育", "学习", "培训", "课程", "知识"]):
            style_additions.extend([
                "教育场景背景",
                "知识传播的视觉元素"
            ])

        # 如果没有特定主题，使用通用商务风格
        if not style_additions:
            style_additions.extend([
                "通用商务演示背景",
                "现代办公风格"
            ])

        return style_additions

    def _get_audience_style(self, target_audience: str) -> str:
        """根据受众类型返回风格描述"""
        audience_styles = {
            "business": "商务专业风格，现代简洁设计，高质量商业摄影效果",
            "academic": "学术风格，严谨专业，教育场景，知识传播视觉元素",
            "creative": "创意设计，艺术感强烈，视觉冲击力，现代艺术风格",
            "technical": "技术文档风格，工程图表，技术示意图，专业技术背景"
        }

        return audience_styles.get(target_audience, audience_styles["business"])

    def _optimize_prompt(self, prompt: str) -> str:
        """
        优化提示词，提高图片生成质量

        Args:
            prompt: 原始提示词

        Returns:
            优化后的提示词
        """
        # 基础优化规则
        optimized = prompt.strip()

        # 添加质量修饰符（如果还没有的话）
        quality_keywords = ["高质量", "4K", "高清", "专业", "精细"]
        if not any(keyword in optimized for keyword in quality_keywords):
            optimized += "，高质量4K分辨率"

        # 添加风格描述（如果还没有的话）
        style_keywords = ["风格", "设计", "摄影", "艺术"]
        if not any(keyword in optimized for keyword in style_keywords):
            optimized += "，现代专业设计风格"

        # 限制长度，避免过长的提示词
        if len(optimized) > 500:
            optimized = optimized[:500].rsplit('，', 1)[0]

        logger.debug(f"提示词优化: '{prompt}' -> '{optimized}'")
        return optimized

    def _get_model_priority_list(self, model_preference: str = None) -> List[str]:
        """
        获取模型优先级列表

        Args:
            model_preference: 首选模型

        Returns:
            按优先级排序的模型列表
        """
        if model_preference and model_preference in self.supported_models:
            # 将首选模型放在第一位
            priority_list = [model_preference]
            priority_list.extend([m for m in self.supported_models if m != model_preference])
            return priority_list
        else:
            return self.supported_models.copy()

    def _get_cache_key(self, prompt: str) -> str:
        """
        生成缓存键

        Args:
            prompt: 提示词

        Returns:
            缓存键
        """
        # 使用SHA256哈希生成稳定的缓存键
        return hashlib.sha256(prompt.encode('utf-8')).hexdigest()

    def _get_cached_image(self, prompt: str) -> Optional[bytes]:
        """
        从缓存中获取图片

        Args:
            prompt: 提示词

        Returns:
            缓存的图片数据，如果没有则返回None
        """
        cache_key = self._get_cache_key(prompt)

        # 首先检查内存缓存
        if cache_key in self._cache:
            logger.debug("从内存缓存返回图片")
            return self._cache[cache_key]

        # 如果启用了S3缓存，检查S3
        if self.s3_client and CONFIG.DEFAULT_BUCKET:
            try:
                s3_key = f"image_cache/{cache_key}.png"
                response = self.s3_client.get_object(
                    Bucket=CONFIG.DEFAULT_BUCKET,
                    Key=s3_key
                )
                image_data = response['Body'].read()

                # 将结果存入内存缓存
                self._cache[cache_key] = image_data
                logger.debug("从S3缓存返回图片")
                return image_data

            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchKey':
                    logger.warning(f"S3缓存检查失败: {str(e)}")

        return None

    def _cache_image(self, prompt: str, image_data: bytes) -> None:
        """
        缓存图片

        Args:
            prompt: 提示词
            image_data: 图片数据
        """
        cache_key = self._get_cache_key(prompt)

        # 存入内存缓存
        self._cache[cache_key] = image_data

        # 如果启用了S3缓存，也存入S3
        if self.s3_client and CONFIG.DEFAULT_BUCKET:
            try:
                s3_key = f"image_cache/{cache_key}.png"
                # 创建ASCII安全的元数据
                safe_prompt = prompt[:1000].encode('ascii', 'ignore').decode('ascii')
                self.s3_client.put_object(
                    Bucket=CONFIG.DEFAULT_BUCKET,
                    Key=s3_key,
                    Body=image_data,
                    ContentType='image/png',
                    Metadata={
                        'prompt_hash': self._get_cache_key(prompt)[:32],  # 使用哈希而不是原始提示词
                        'generated_at': str(int(time.time())),
                        'image_size': str(len(image_data))
                    }
                )
                logger.debug("图片已缓存到S3")
            except Exception as e:
                logger.warning(f"S3缓存失败: {str(e)}")

    def clear_cache(self) -> None:
        """清除内存缓存"""
        self._cache.clear()
        logger.info("内存缓存已清除")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计数据
        """
        return {
            "memory_cache_size": len(self._cache),
            "cache_enabled": self.enable_caching,
            "s3_cache_enabled": self.s3_client is not None
        }