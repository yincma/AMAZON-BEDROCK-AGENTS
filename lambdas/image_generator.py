"""
AI-PPT-Assistant 图片生成器 - 重构版本

基于SOLID原则重构的图片生成功能：
- 单一责任原则：分离图片生成、S3操作、配置管理
- 依赖注入：支持外部依赖注入
- 开闭原则：易于扩展新功能
- 接口隔离：清晰的服务接口
"""

import logging
from typing import Dict, List, Any, Optional

try:
    from .image_config import CONFIG
    from .image_exceptions import (
        ImageGeneratorError, NovaServiceError, S3OperationError,
        ImageProcessingError, ValidationError
    )
    from .image_s3_service import ImageS3Service
    from .image_processing_service import ImageProcessingService
except ImportError:
    # 当作为独立模块导入时使用
    from image_config import CONFIG
    from image_exceptions import (
        ImageGeneratorError, NovaServiceError, S3OperationError,
        ImageProcessingError, ValidationError
    )
    from image_s3_service import ImageS3Service
    from image_processing_service import ImageProcessingService

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ImageGenerator:
    """图片生成器门面类 - 协调各个服务组件

    遵循SOLID原则的重构版本：
    - 单一责任：仅负责协调服务
    - 依赖注入：接受服务实例
    - 接口隔离：清晰的公共接口
    """

    def __init__(self,
                 processing_service: Optional[ImageProcessingService] = None,
                 s3_service: Optional[ImageS3Service] = None,
                 bucket_name: Optional[str] = None):
        """
        初始化图片生成器

        Args:
            processing_service: 图片处理服务实例
            s3_service: S3服务实例
            bucket_name: 存储桶名称
        """
        self.processing_service = processing_service or ImageProcessingService()
        self.s3_service = s3_service or ImageS3Service(bucket_name=bucket_name)

        logger.info(f"ImageGenerator初始化完成，使用存储桶: {self.s3_service.bucket_name}")

    def generate_prompt(self, slide_content: Dict[str, Any], target_audience: str = "business") -> str:
        """
        根据幻灯片内容生成图片提示词

        Args:
            slide_content: 幻灯片内容
            target_audience: 目标受众类型

        Returns:
            生成的提示词
        """
        if not slide_content:
            raise ValidationError("幻灯片内容不能为空", field_name="slide_content")

        return self.processing_service.generate_prompt(slide_content, target_audience)

    def generate_image(self, prompt: str, presentation_id: str, slide_number: int) -> Dict[str, Any]:
        """
        生成图片并保存到S3

        Args:
            prompt: 图片提示词
            presentation_id: 演示文稿ID
            slide_number: 幻灯片编号

        Returns:
            生成结果字典
        """
        if not prompt:
            raise ValidationError("图片提示词不能为空", field_name="prompt")
        if not presentation_id:
            raise ValidationError("演示文稿ID不能为空", field_name="presentation_id")
        if slide_number <= 0:
            raise ValidationError("幻灯片编号必须大于0", field_name="slide_number")

        try:
            # 生成图片
            image_data = self.processing_service.call_image_generation(prompt)

            # 保存到S3
            image_url = self.s3_service.save_image(image_data, presentation_id, slide_number)

            return {
                'status': 'success',
                'image_url': image_url,
                'prompt': prompt
            }


        except Exception as e:
            logger.error(f"图片生成过程发生未预期错误: {str(e)}")
            raise ImageGeneratorError(f"图片生成失败: {str(e)}") from e

    def save_to_s3(self, image_data: bytes, presentation_id: str, slide_number: int) -> str:
        """
        保存图片到S3

        Args:
            image_data: 图片数据
            presentation_id: 演示文稿ID
            slide_number: 幻灯片编号

        Returns:
            S3 URL
        """
        if not image_data:
            raise ValidationError("图片数据不能为空", field_name="image_data")

        return self.s3_service.save_image(image_data, presentation_id, slide_number)

    def generate_consistent_images(self, slides: List[Dict[str, Any]], presentation_id: str) -> List[Dict[str, Any]]:
        """
        为演示文稿生成一致风格的图片

        Args:
            slides: 幻灯片列表
            presentation_id: 演示文稿ID

        Returns:
            生成结果列表
        """
        if not slides:
            return []

        # 定义一致的风格参数
        base_style = {
            'color_scheme': CONFIG.DEFAULT_STYLE_SCHEME,
            'art_style': CONFIG.DEFAULT_ART_STYLE,
            'composition': CONFIG.DEFAULT_COMPOSITION
        }

        results = []

        for i, slide in enumerate(slides, 1):
            try:
                # 为每张幻灯片生成图片
                prompt = self.generate_prompt(slide)
                result = self.generate_image(prompt, presentation_id, i)
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

    def batch_generate_images(self, slides: List[Dict[str, Any]], presentation_id: str) -> List[Dict[str, Any]]:
        """
        批量生成图片

        Args:
            slides: 幻灯片列表
            presentation_id: 演示文稿ID

        Returns:
            生成结果列表
        """
        return self.generate_consistent_images(slides, presentation_id)

    def save_image_with_metadata(self, image_data: bytes, metadata: Dict[str, Any],
                                presentation_id: str, slide_number: int) -> Dict[str, Any]:
        """
        保存图片和元数据到S3

        Args:
            image_data: 图片数据
            metadata: 元数据
            presentation_id: 演示文稿ID
            slide_number: 幻灯片编号

        Returns:
            保存结果
        """
        return self.s3_service.save_image_with_metadata(image_data, metadata, presentation_id, slide_number)

    def validate_image_format(self, image_data: bytes, expected_format: str = 'PNG') -> bool:
        """
        验证图片格式

        Args:
            image_data: 图片数据
            expected_format: 期望的格式

        Returns:
            验证结果
        """
        return self.processing_service.validate_image_format(image_data, expected_format)

    def optimize_image_size(self, image_data: bytes, target_width: int = None,
                           target_height: int = None) -> bytes:
        """
        优化图片尺寸

        Args:
            image_data: 原始图片数据
            target_width: 目标宽度
            target_height: 目标高度

        Returns:
            优化后的图片数据
        """
        return self.processing_service.optimize_image_size(image_data, target_width, target_height)

    def generate_for_presentation(self, presentation_data: Dict[str, Any], presentation_id: str) -> Dict[str, Any]:
        """
        为整个演示文稿生成图片

        Args:
            presentation_data: 演示文稿数据
            presentation_id: 演示文稿ID

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
        results = self.batch_generate_images(slides, presentation_id)

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

    def _generate_fallback_image(self, prompt: str, presentation_id: str,
                               slide_number: int, error_msg: str) -> Dict[str, Any]:
        """
        生成占位图作为后备方案

        Args:
            prompt: 原始提示词
            presentation_id: 演示文稿ID
            slide_number: 幻灯片编号
            error_msg: 错误信息

        Returns:
            后备结果字典
        """
        try:
            # 生成占位图
            placeholder_data = self.processing_service.create_placeholder_image(text="演示图片")

            # 保存占位图到S3
            image_url = self.s3_service.save_image(placeholder_data, presentation_id, slide_number)

            return {
                'status': 'fallback',
                'image_url': image_url,
                'prompt': prompt,
                'error': error_msg
            }

        except Exception as fallback_error:
            logger.error(f"生成占位图也失败: {str(fallback_error)}")
            raise ImageGeneratorError(f"图片生成和占位图生成都失败: {error_msg}, {str(fallback_error)}") from fallback_error


# 向后兼容的函数接口
def generate_image_prompt(slide_content: Dict[str, Any]) -> str:
    """向后兼容的提示词生成函数"""
    generator = ImageGenerator()
    return generator.generate_prompt(slide_content)


def optimize_image_prompt(slide_content: Dict[str, Any], target_audience: str = "business") -> str:
    """优化图片提示词，生成更具体的描述"""
    generator = ImageGenerator()
    return generator.generate_prompt(slide_content, target_audience)


def generate_image(prompt: str, presentation_id: str, slide_number: int, s3_client) -> Dict[str, Any]:
    """向后兼容的图片生成函数"""
    s3_service = ImageS3Service(s3_client=s3_client)
    generator = ImageGenerator(s3_service=s3_service)
    return generator.generate_image(prompt, presentation_id, slide_number)


def save_image_to_s3(image_data: bytes, presentation_id: str, slide_number: int,
                     s3_client, bucket_name: str = None) -> str:
    """向后兼容的S3保存函数"""
    s3_service = ImageS3Service(s3_client=s3_client, bucket_name=bucket_name)
    return s3_service.save_image(image_data, presentation_id, slide_number)


def save_image_to_s3_with_retry(image_data: bytes, presentation_id: str, slide_number: int,
                               s3_client, max_retries: int = 3, bucket_name: str = None) -> Dict[str, Any]:
    """向后兼容的带重试的S3保存函数"""
    s3_service = ImageS3Service(s3_client=s3_client, bucket_name=bucket_name)
    return s3_service.save_image_with_retry(image_data, presentation_id, slide_number, max_retries)


def generate_consistent_images(slides: List[Dict[str, Any]], presentation_id: str, s3_client) -> List[Dict[str, Any]]:
    """向后兼容的一致性图片生成函数"""
    s3_service = ImageS3Service(s3_client=s3_client)
    generator = ImageGenerator(s3_service=s3_service)
    return generator.generate_consistent_images(slides, presentation_id)


def batch_generate_images(slides: List[Dict[str, Any]], presentation_id: str, s3_client) -> List[Dict[str, Any]]:
    """向后兼容的批量图片生成函数"""
    s3_service = ImageS3Service(s3_client=s3_client)
    generator = ImageGenerator(s3_service=s3_service)
    return generator.batch_generate_images(slides, presentation_id)


def batch_generate_prompts(slides: List[Dict[str, Any]]) -> List[str]:
    """批量生成图片提示词"""
    generator = ImageGenerator()
    return [generator.generate_prompt(slide) for slide in slides]


def save_image_with_metadata(image_data: bytes, metadata: Dict[str, Any],
                           presentation_id: str, slide_number: int, s3_client) -> Dict[str, Any]:
    """向后兼容的带元数据保存函数"""
    s3_service = ImageS3Service(s3_client=s3_client)
    return s3_service.save_image_with_metadata(image_data, metadata, presentation_id, slide_number)


def validate_image_format(image_data: bytes, expected_format: str = 'PNG') -> bool:
    """向后兼容的图片格式验证函数"""
    processing_service = ImageProcessingService()
    return processing_service.validate_image_format(image_data, expected_format)


def optimize_image_size(image_data: bytes, target_width: int = 1200,
                       target_height: int = 800) -> bytes:
    """向后兼容的图片尺寸优化函数"""
    processing_service = ImageProcessingService()
    return processing_service.optimize_image_size(image_data, target_width, target_height)


def create_placeholder_image(width: int = 1200, height: int = 800, text: str = "图片占位符") -> bytes:
    """向后兼容的占位图创建函数"""
    processing_service = ImageProcessingService()
    return processing_service.create_placeholder_image(width, height, text)


def generate_for_presentation(presentation_data: Dict[str, Any], presentation_id: str,
                            s3_client) -> Dict[str, Any]:
    """向后兼容的演示文稿图片生成函数"""
    s3_service = ImageS3Service(s3_client=s3_client)
    generator = ImageGenerator(s3_service=s3_service)
    return generator.generate_for_presentation(presentation_data, presentation_id)


# 重新导出异常类以保持向后兼容性
ImageGenerationError = NovaServiceError

# 向后兼容的Nova服务调用函数
def call_nova_image_generation(prompt: str) -> bytes:
    """向后兼容的Nova图片生成函数"""
    processing_service = ImageProcessingService()
    return processing_service.call_nova_image_generation(prompt)


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
    generator = ImageGenerator()
    prompt = generator.generate_prompt(test_slide)
    print(f"生成的提示词: {prompt}")

    print("\n测试占位图创建:")
    placeholder_data = create_placeholder_image(800, 600, "测试图片")
    print(f"占位图大小: {len(placeholder_data)} 字节")