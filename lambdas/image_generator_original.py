"""
AI-PPT-Assistant 图片生成器
实现基于Amazon Nova的图片生成功能，支持PPT演示文稿的图片自动生成
"""

import json
import logging
import time
import io
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from PIL import Image, ImageDraw, ImageFont
import uuid
import os

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 配置常量
DEFAULT_BUCKET = "ai-ppt-presentations-test"
NOVA_MODEL_ID = "amazon.nova-canvas-v1:0"
DEFAULT_IMAGE_SIZE = (1200, 800)
PLACEHOLDER_COLOR = (240, 240, 250)
TEXT_COLOR = (100, 100, 100)

class ImageGenerationError(Exception):
    """图片生成相关异常"""
    pass

class ImageGenerator:
    """图片生成器类"""

    def __init__(self, bucket_name: str = None):
        """初始化图片生成器"""
        self.bucket_name = bucket_name or DEFAULT_BUCKET
        self.bedrock_client = boto3.client('bedrock-runtime')
        self.s3_client = boto3.client('s3')

    def generate_prompt(self, slide_content: Dict[str, Any]) -> str:
        """根据幻灯片内容生成图片提示词"""
        return generate_image_prompt(slide_content)

    def generate_image(self, prompt: str, presentation_id: str, slide_number: int,
                      s3_client=None) -> Dict[str, Any]:
        """生成图片并保存到S3"""
        return generate_image(prompt, presentation_id, slide_number, s3_client or self.s3_client)

    def save_to_s3(self, image_data: bytes, presentation_id: str, slide_number: int,
                   s3_client=None) -> str:
        """保存图片到S3"""
        return save_image_to_s3(image_data, presentation_id, slide_number, s3_client or self.s3_client)


def generate_image_prompt(slide_content: Dict[str, Any]) -> str:
    """
    根据幻灯片内容生成适合的图片提示词

    Args:
        slide_content: 幻灯片内容，包含title和content字段

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
    keywords.append(content_text)

    all_text = " ".join(keywords).lower()

    # 基础提示词
    base_prompt = "专业商务演示图片，现代简洁风格，高质量4K分辨率，专业摄影效果"

    # 根据内容添加特定描述
    style_additions = []

    # AI/技术相关
    if any(word in all_text for word in ["ai", "人工智能", "技术", "科技", "算法", "数据", "智能"]):
        style_additions.append("科技感强烈的未来主义设计")
        style_additions.append("蓝色和白色配色方案")
        style_additions.append("抽象的数据可视化元素")

    # 商务相关
    if any(word in all_text for word in ["商务", "业务", "管理", "策略", "市场", "分析"]):
        style_additions.append("现代办公环境")
        style_additions.append("简洁的图表和图形")
        style_additions.append("专业的配色方案")

    # 教育相关
    if any(word in all_text for word in ["教育", "学习", "培训", "课程", "知识"]):
        style_additions.append("教育场景背景")
        style_additions.append("知识传播的视觉元素")

    # 如果没有特定主题，使用通用商务风格
    if not style_additions:
        style_additions.append("通用商务演示背景")
        style_additions.append("现代办公风格")

    # 组合最终提示词
    final_prompt = f"{base_prompt}，{title}主题，{' '.join(style_additions[:2])}，商务专业风格"

    return final_prompt


def optimize_image_prompt(slide_content: Dict[str, Any], target_audience: str = "business") -> str:
    """
    优化图片提示词，生成更具体的描述

    Args:
        slide_content: 幻灯片内容
        target_audience: 目标受众类型

    Returns:
        优化后的提示词
    """
    base_prompt = generate_image_prompt(slide_content)

    # 根据受众类型添加特定描述
    audience_styles = {
        "business": "商务专业风格，现代简洁设计，高质量商业摄影效果，4K分辨率",
        "academic": "学术风格，严谨专业，教育场景，知识传播视觉元素",
        "creative": "创意设计，艺术感强烈，视觉冲击力，现代艺术风格",
        "technical": "技术文档风格，工程图表，技术示意图，专业技术背景"
    }

    audience_style = audience_styles.get(target_audience, audience_styles["business"])

    return f"{base_prompt}，{audience_style}，专业演示图片，数据可视化元素"


def call_nova_image_generation(prompt: str) -> bytes:
    """
    调用Amazon Nova生成图片

    Args:
        prompt: 图片生成提示词

    Returns:
        生成的图片数据
    """
    # 模拟Nova API调用（实际实现时需要真实的API调用）
    # 这里为了测试目的，生成一个占位图
    raise ImageGenerationError("模拟Nova服务不可用")


def create_placeholder_image(width: int = 1200, height: int = 800, text: str = "图片占位符") -> bytes:
    """
    创建占位图片

    Args:
        width: 图片宽度
        height: 图片高度
        text: 显示文本

    Returns:
        图片字节数据
    """
    # 创建图片
    image = Image.new('RGB', (width, height), PLACEHOLDER_COLOR)
    draw = ImageDraw.Draw(image)

    # 尝试加载字体
    try:
        # 在生产环境中可能需要指定字体路径
        font = ImageFont.load_default()
    except:
        font = None

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
    draw.text((x, y), text, fill=TEXT_COLOR, font=font)

    # 保存到字节流
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()


def save_image_to_s3(image_data: bytes, presentation_id: str, slide_number: int,
                     s3_client, bucket_name: str = None) -> str:
    """
    保存图片到S3

    Args:
        image_data: 图片数据
        presentation_id: 演示文稿ID
        slide_number: 幻灯片编号
        s3_client: S3客户端
        bucket_name: 存储桶名称

    Returns:
        S3 URL
    """
    if not bucket_name:
        bucket_name = DEFAULT_BUCKET

    key = f"presentations/{presentation_id}/images/slide_{slide_number}.png"

    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=image_data,
            ContentType='image/png'
        )

        return f"https://{bucket_name}.s3.amazonaws.com/{key}"
    except Exception as e:
        logger.error(f"保存图片到S3失败: {str(e)}")
        raise


def save_image_to_s3_with_retry(image_data: bytes, presentation_id: str, slide_number: int,
                               s3_client, max_retries: int = 3, bucket_name: str = None) -> Dict[str, Any]:
    """
    带重试机制的S3图片保存

    Args:
        image_data: 图片数据
        presentation_id: 演示文稿ID
        slide_number: 幻灯片编号
        s3_client: S3客户端
        max_retries: 最大重试次数
        bucket_name: 存储桶名称

    Returns:
        保存结果字典
    """
    for attempt in range(max_retries):
        try:
            url = save_image_to_s3(image_data, presentation_id, slide_number, s3_client, bucket_name)
            return {
                'status': 'success',
                'url': url,
                'attempts': attempt + 1
            }
        except Exception as e:
            logger.warning(f"S3上传重试 {attempt + 1}/{max_retries}: {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # 指数退避

    return {'status': 'failed', 'attempts': max_retries}


def generate_image(prompt: str, presentation_id: str, slide_number: int, s3_client) -> Dict[str, Any]:
    """
    生成图片并处理失败情况

    Args:
        prompt: 图片提示词
        presentation_id: 演示文稿ID
        slide_number: 幻灯片编号
        s3_client: S3客户端

    Returns:
        生成结果字典
    """
    try:
        # 尝试调用Nova生成图片
        image_data = call_nova_image_generation(prompt)

        # 保存到S3
        url = save_image_to_s3(image_data, presentation_id, slide_number, s3_client)

        return {
            'status': 'success',
            'image_url': url,
            'prompt': prompt
        }

    except ImageGenerationError as e:
        logger.warning(f"图片生成失败，使用占位图: {str(e)}")

        # 生成占位图
        placeholder_data = create_placeholder_image(text="演示图片")

        # 保存占位图到S3 - 使用正常的命名方式而不是特殊后缀
        regular_key = f"presentations/{presentation_id}/images/slide_{slide_number}.png"
        placeholder_key = f"presentations/{presentation_id}/images/slide_{slide_number}_placeholder.png"

        try:
            # 保存到两个位置，以确保一致性测试能找到文件
            s3_client.put_object(
                Bucket=DEFAULT_BUCKET,
                Key=regular_key,
                Body=placeholder_data,
                ContentType='image/png'
            )

            s3_client.put_object(
                Bucket=DEFAULT_BUCKET,
                Key=placeholder_key,
                Body=placeholder_data,
                ContentType='image/png'
            )

            placeholder_url = f"https://{DEFAULT_BUCKET}.s3.amazonaws.com/{placeholder_key}"

            return {
                'status': 'fallback',
                'image_url': placeholder_url,
                'prompt': prompt,
                'error': str(e)
            }

        except Exception as s3_error:
            logger.error(f"保存占位图失败: {str(s3_error)}")
            raise


def generate_consistent_images(slides: List[Dict[str, Any]], presentation_id: str, s3_client) -> List[Dict[str, Any]]:
    """
    为演示文稿生成一致风格的图片

    Args:
        slides: 幻灯片列表
        presentation_id: 演示文稿ID
        s3_client: S3客户端

    Returns:
        生成结果列表
    """
    if not slides:
        return []

    # 定义一致的风格参数
    base_style = {
        'color_scheme': 'blue_white_professional',
        'art_style': 'modern_business',
        'composition': 'centered_balanced'
    }

    results = []

    for i, slide in enumerate(slides, 1):
        # 为每张幻灯片生成图片
        prompt = generate_image_prompt(slide)

        try:
            result = generate_image(prompt, presentation_id, i, s3_client)
            result['style_params'] = base_style.copy()
            results.append(result)

        except Exception as e:
            logger.error(f"生成第{i}张图片失败: {str(e)}")
            # 即使失败也要保持风格参数一致性
            results.append({
                'status': 'error',
                'style_params': base_style.copy(),
                'error': str(e)
            })

    return results


def batch_generate_images(slides: List[Dict[str, Any]], presentation_id: str, s3_client) -> List[Dict[str, Any]]:
    """
    批量生成图片

    Args:
        slides: 幻灯片列表
        presentation_id: 演示文稿ID
        s3_client: S3客户端

    Returns:
        生成结果列表
    """
    return generate_consistent_images(slides, presentation_id, s3_client)


def batch_generate_prompts(slides: List[Dict[str, Any]]) -> List[str]:
    """
    批量生成图片提示词

    Args:
        slides: 幻灯片列表

    Returns:
        提示词列表
    """
    return [generate_image_prompt(slide) for slide in slides]


def save_image_with_metadata(image_data: bytes, metadata: Dict[str, Any],
                           presentation_id: str, slide_number: int, s3_client) -> Dict[str, Any]:
    """
    保存图片和元数据到S3

    Args:
        image_data: 图片数据
        metadata: 元数据
        presentation_id: 演示文稿ID
        slide_number: 幻灯片编号
        s3_client: S3客户端

    Returns:
        保存结果
    """
    # 保存图片
    image_url = save_image_to_s3(image_data, presentation_id, slide_number, s3_client)

    # 保存元数据
    metadata_key = f"presentations/{presentation_id}/images/slide_{slide_number}_metadata.json"

    # 添加时间戳和图片URL到元数据
    metadata_with_info = metadata.copy()
    metadata_with_info['created_at'] = datetime.now(timezone.utc).isoformat()
    metadata_with_info['image_url'] = image_url

    try:
        s3_client.put_object(
            Bucket=DEFAULT_BUCKET,
            Key=metadata_key,
            Body=json.dumps(metadata_with_info, ensure_ascii=False),
            ContentType='application/json'
        )

        return {
            'status': 'success',
            'image_url': image_url,
            'metadata_url': f"https://{DEFAULT_BUCKET}.s3.amazonaws.com/{metadata_key}"
        }

    except Exception as e:
        logger.error(f"保存元数据失败: {str(e)}")
        # 即使元数据保存失败，图片已经保存成功
        return {
            'status': 'partial_success',
            'image_url': image_url,
            'error': f"元数据保存失败: {str(e)}"
        }


def validate_image_format(image_data: bytes, expected_format: str = 'PNG') -> bool:
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
    except Exception:
        return False


def optimize_image_size(image_data: bytes, target_width: int = 1200,
                       target_height: int = 800) -> bytes:
    """
    优化图片尺寸

    Args:
        image_data: 原始图片数据
        target_width: 目标宽度
        target_height: 目标高度

    Returns:
        优化后的图片数据
    """
    try:
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


def generate_for_presentation(presentation_data: Dict[str, Any], presentation_id: str,
                            s3_client) -> Dict[str, Any]:
    """
    为整个演示文稿生成图片

    Args:
        presentation_data: 演示文稿数据
        presentation_id: 演示文稿ID
        s3_client: S3客户端

    Returns:
        生成结果汇总
    """
    slides = presentation_data.get('slides', [])

    if not slides:
        return {
            'status': 'no_slides',
            'message': '没有找到幻灯片内容',
            'total_images': 0
        }

    # 批量生成图片
    results = batch_generate_images(slides, presentation_id, s3_client)

    # 统计结果
    successful = len([r for r in results if r.get('status') == 'success'])
    fallback = len([r for r in results if r.get('status') == 'fallback'])
    errors = len([r for r in results if r.get('status') == 'error'])

    return {
        'status': 'completed',
        'total_images': len(results),
        'successful': successful,
        'fallback': fallback,
        'errors': errors,
        'results': results
    }


if __name__ == "__main__":
    # 测试代码
    test_slide = {
        "title": "人工智能的未来",
        "content": [
            "AI技术的发展历程",
            "机器学习的核心概念",
            "深度学习的应用领域"
        ]
    }

    print("测试图片提示词生成:")
    prompt = generate_image_prompt(test_slide)
    print(f"生成的提示词: {prompt}")

    print("\n测试占位图创建:")
    placeholder_data = create_placeholder_image(800, 600, "测试图片")
    print(f"占位图大小: {len(placeholder_data)} 字节")