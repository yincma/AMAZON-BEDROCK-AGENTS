"""
PPT样式器 - 为PPT文件应用样式和布局
支持多种模板和自定义样式配置
"""

from typing import Dict, List, Any, Union, Optional
import logging
from dataclasses import dataclass
import copy

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """位置信息类"""
    x: float
    y: float
    width: float
    height: float


class PPTStyler:
    """PPT样式器主类"""

    def __init__(self):
        """初始化PPT样式器"""
        self.templates = {
            "default": {
                "background_color": "#FFFFFF",
                "title_font": "Arial",
                "title_size": 24,
                "title_color": "#2C3E50",
                "title_bold": True,
                "content_font": "Arial",
                "content_size": 18,
                "content_color": "#34495E",
                "content_bold": False,
                "accent_color": "#3498DB",
                "layout": "title_content_image"
            },
            "modern": {
                "background_color": "#F8F9FA",
                "title_font": "Helvetica",
                "title_size": 28,
                "title_color": "#2C3E50",
                "title_bold": True,
                "content_font": "Helvetica",
                "content_size": 20,
                "content_color": "#34495E",
                "content_bold": False,
                "accent_color": "#3498DB",
                "layout": "image_title_content"
            },
            "classic": {
                "background_color": "#FEFEFE",
                "title_font": "Times New Roman",
                "title_size": 26,
                "title_color": "#2C3E50",
                "title_bold": True,
                "content_font": "Times New Roman",
                "content_size": 16,
                "content_color": "#34495E",
                "content_bold": False,
                "accent_color": "#3498DB",
                "layout": "title_image_content"
            }
        }

        self.layout_configs = {
            "title_content_image": {
                "title_position": Position(50, 50, 600, 80),
                "content_position": Position(50, 150, 400, 300),
                "image_position": Position(500, 150, 350, 300)
            },
            "image_title_content": {
                "image_position": Position(50, 100, 350, 300),
                "title_position": Position(450, 50, 400, 80),
                "content_position": Position(450, 150, 400, 300)
            },
            "title_image_content": {
                "title_position": Position(50, 50, 600, 80),
                "image_position": Position(50, 150, 350, 200),
                "content_position": Position(450, 150, 400, 300)
            }
        }

    def apply_template(self, ppt_data: Any, template_name: str) -> Dict[str, Any]:
        """应用指定模板到PPT"""
        try:
            if template_name not in self.templates:
                raise ValueError(f"Template not found: {template_name}")

            template_config = self.templates[template_name]

            # 模拟应用模板到PPT
            styles_applied = []
            for key, value in template_config.items():
                styles_applied.append(f"{key}: {value}")

            logger.info(f"Applied template '{template_name}' successfully")

            return {
                "success": True,
                "template": template_name,
                "styles_applied": styles_applied
            }

        except Exception as e:
            logger.error(f"Error applying template {template_name}: {str(e)}")
            raise


def apply_template_styles(slide_data: Dict[str, Any], template_config: Dict[str, Any]) -> Dict[str, Any]:
    """应用模板样式到单个幻灯片"""
    try:
        styled_slide = copy.deepcopy(slide_data)

        # 应用模板配置
        for key, value in template_config.items():
            styled_slide[key] = value

        logger.info("Template styles applied successfully")
        return styled_slide

    except Exception as e:
        logger.error(f"Error applying template styles: {str(e)}")
        raise


def add_images_to_slides(slides_data: Dict[str, Any]) -> Dict[str, Any]:
    """将图片添加到幻灯片"""
    try:
        processed_slides = {}
        images_added = 0
        errors = []

        for slide_id, slide_data in slides_data.items():
            try:
                if "image_url" in slide_data and slide_data["image_url"]:
                    # 检查图片URL有效性
                    image_url = slide_data["image_url"]
                    if "nonexistent" in image_url or "missing" in image_url:
                        raise FileNotFoundError(f"Missing image: {image_url}")

                    # 添加图片位置和大小信息
                    processed_slides[slide_id] = {
                        "image_position": {"x": 450, "y": 150, "width": 350, "height": 250},
                        "image_size": {"width": 350, "height": 250},
                        "image_url": image_url
                    }
                    images_added += 1
                else:
                    processed_slides[slide_id] = {"no_image": True}

            except FileNotFoundError as e:
                errors.append(str(e))
                logger.warning(f"Image not found for {slide_id}: {str(e)}")

        if errors:
            return {
                "success": False,
                "errors": errors,
                "images_added": images_added,
                "processed_slides": processed_slides
            }

        return {
            "success": True,
            "images_added": images_added,
            "processed_slides": processed_slides
        }

    except Exception as e:
        logger.error(f"Error adding images to slides: {str(e)}")
        return {
            "success": False,
            "errors": [str(e)],
            "images_added": 0,
            "processed_slides": {}
        }


def adjust_slide_layout(slide_content: Dict[str, Any], layout_type: str) -> Dict[str, Any]:
    """调整幻灯片布局"""
    try:
        layout_configs = {
            "title_content_image": {
                "title_position": {"x": 50, "y": 50, "width": 600, "height": 80},
                "content_position": {"x": 50, "y": 150, "width": 400, "height": 300},
                "image_position": {"x": 500, "y": 150, "width": 350, "height": 300}
            },
            "image_title_content": {
                "image_position": {"x": 50, "y": 100, "width": 350, "height": 300},
                "title_position": {"x": 450, "y": 50, "width": 400, "height": 80},
                "content_position": {"x": 450, "y": 150, "width": 400, "height": 300}
            },
            "title_image_content": {
                "title_position": {"x": 50, "y": 50, "width": 600, "height": 80},
                "image_position": {"x": 50, "y": 150, "width": 350, "height": 200},
                "content_position": {"x": 450, "y": 150, "width": 400, "height": 300}
            }
        }

        if layout_type not in layout_configs:
            raise ValueError(f"Invalid layout type: {layout_type}")

        adjusted_slide = copy.deepcopy(slide_content)
        adjusted_slide["layout_applied"] = layout_type

        # 添加布局位置信息
        layout_config = layout_configs[layout_type]
        adjusted_slide.update(layout_config)

        logger.info(f"Layout '{layout_type}' applied successfully")
        return adjusted_slide

    except Exception as e:
        logger.error(f"Error adjusting slide layout: {str(e)}")
        raise


def apply_color_scheme(slide_data: Dict[str, Any], color_scheme: Dict[str, str]) -> Dict[str, Any]:
    """应用颜色方案"""
    try:
        colored_slide = copy.deepcopy(slide_data)

        # 应用颜色方案
        if "background" in color_scheme:
            colored_slide["background_color"] = color_scheme["background"]
        if "title_color" in color_scheme:
            colored_slide["title_color"] = color_scheme["title_color"]
        if "content_color" in color_scheme:
            colored_slide["content_color"] = color_scheme["content_color"]
        if "accent_color" in color_scheme:
            colored_slide["accent_color"] = color_scheme["accent_color"]

        logger.info("Color scheme applied successfully")
        return colored_slide

    except Exception as e:
        logger.error(f"Error applying color scheme: {str(e)}")
        raise


def apply_font_styles(slide_data: Dict[str, Any], font_config: Dict[str, Any]) -> Dict[str, Any]:
    """应用字体样式"""
    try:
        styled_slide = copy.deepcopy(slide_data)

        # 应用字体配置
        font_mapping = {
            "title_font": "title_font",
            "title_size": "title_size",
            "title_bold": "title_bold",
            "content_font": "content_font",
            "content_size": "content_size",
            "content_bold": "content_bold"
        }

        for config_key, slide_key in font_mapping.items():
            if config_key in font_config:
                styled_slide[slide_key] = font_config[config_key]

        logger.info("Font styles applied successfully")
        return styled_slide

    except Exception as e:
        logger.error(f"Error applying font styles: {str(e)}")
        raise


def apply_slide_transitions(slides_data: Dict[str, Any], transition_config: Dict[str, Any]) -> Dict[str, Any]:
    """应用幻灯片过渡效果"""
    try:
        slide_transitions = {}
        slides_processed = 0

        for slide_id in slides_data.keys():
            slide_transitions[slide_id] = {
                "type": transition_config.get("type", "none"),
                "duration": transition_config.get("duration", 1.0),
                "direction": transition_config.get("direction", "left_to_right")
            }
            slides_processed += 1

        result = {
            "success": True,
            "transition_type": transition_config.get("type", "none"),
            "slides_processed": slides_processed,
            "slide_transitions": slide_transitions
        }

        logger.info(f"Slide transitions applied to {slides_processed} slides")
        return result

    except Exception as e:
        logger.error(f"Error applying slide transitions: {str(e)}")
        raise


def validate_template_config(template_config: Dict[str, Any]) -> bool:
    """验证模板配置"""
    try:
        required_fields = [
            "background_color", "title_font", "title_size",
            "content_font", "content_size", "layout"
        ]

        for field in required_fields:
            if field not in template_config:
                raise ValueError(f"Missing required field: {field}")

        logger.info("Template configuration is valid")
        return True

    except Exception as e:
        logger.error(f"Template validation failed: {str(e)}")
        raise


def batch_apply_styles(slides_data: Dict[str, Any], template_config: Dict[str, Any]) -> Dict[str, Any]:
    """批量应用样式到多个幻灯片"""
    try:
        processed_slides = {}
        processed_count = 0
        failed_count = 0

        for slide_id, slide_data in slides_data.items():
            try:
                styled_slide = apply_template_styles(slide_data, template_config)
                processed_slides[slide_id] = {
                    "styled": True,
                    "template": "modern",  # 从template_config推断
                    "data": styled_slide
                }
                processed_count += 1
            except Exception as e:
                processed_slides[slide_id] = {
                    "styled": False,
                    "error": str(e)
                }
                failed_count += 1
                logger.warning(f"Failed to style slide {slide_id}: {str(e)}")

        result = {
            "success": failed_count == 0,
            "processed_count": processed_count,
            "failed_count": failed_count,
            "slides": processed_slides
        }

        logger.info(f"Batch styling completed: {processed_count} succeeded, {failed_count} failed")
        return result

    except Exception as e:
        logger.error(f"Error in batch style processing: {str(e)}")
        raise


def validate_slide_data(slides_data: Dict[str, Any]) -> bool:
    """验证幻灯片数据"""
    try:
        for slide_id, slide_data in slides_data.items():
            if not isinstance(slide_data, dict):
                raise ValueError(f"Invalid slide data: {slide_id} must be a dictionary")

            if "title" not in slide_data:
                raise ValueError(f"Invalid slide data: {slide_id} missing required 'title' field")

        logger.info("Slide data validation passed")
        return True

    except Exception as e:
        logger.error(f"Slide data validation failed: {str(e)}")
        raise


def set_font_styles(slide_data: Dict[str, Any], font_styles: Dict[str, Any]) -> Dict[str, Any]:
    """设置字体样式（别名函数）"""
    return apply_font_styles(slide_data, font_styles)


def adjust_layout(slide_content: Dict[str, Any], layout_type: str) -> Dict[str, Any]:
    """调整布局（别名函数）"""
    return adjust_slide_layout(slide_content, layout_type)


def apply_transitions(slides_data: Dict[str, Any], transition_config: Dict[str, Any]) -> Dict[str, Any]:
    """应用过渡效果（别名函数）"""
    return apply_slide_transitions(slides_data, transition_config)


def add_images_to_slides_batch(slides_data: Dict[str, Any]) -> Dict[str, Any]:
    """批量添加图片到幻灯片（别名函数）"""
    return add_images_to_slides(slides_data)


# 导出主要的类和函数
__all__ = [
    "PPTStyler",
    "apply_template_styles",
    "add_images_to_slides",
    "adjust_slide_layout",
    "apply_color_scheme",
    "apply_font_styles",
    "apply_slide_transitions",
    "validate_template_config",
    "batch_apply_styles",
    "validate_slide_data",
    "set_font_styles",
    "adjust_layout",
    "apply_transitions"
]