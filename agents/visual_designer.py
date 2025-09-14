"""
Visual Designer Agent - 视觉设计器
负责生成图片提示词、应用模板、优化布局
"""
import json
from typing import Dict, Any, List
import boto3
from botocore.config import Config

# 统一使用的模型
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"  # inference profile


class VisualDesignerAgent:
    """视觉设计Agent"""

    def __init__(self):
        """初始化Visual Designer Agent"""
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1',
            config=Config(read_timeout=30, retries={'max_attempts': 3})
        )

        # 预定义模板样式
        self.templates = {
            "modern": {
                "font_family": "Arial",
                "primary_color": "#2E86AB",
                "secondary_color": "#A23B72",
                "background": "#FFFFFF",
                "font_size": {"title": 44, "content": 24}
            },
            "classic": {
                "font_family": "Times New Roman",
                "primary_color": "#000080",
                "secondary_color": "#4169E1",
                "background": "#F5F5F5",
                "font_size": {"title": 40, "content": 22}
            },
            "default": {
                "font_family": "Calibri",
                "primary_color": "#333333",
                "secondary_color": "#666666",
                "background": "#FFFFFF",
                "font_size": {"title": 42, "content": 20}
            }
        }

    def generate_image_prompt(self, slide: Dict[str, Any]) -> str:
        """
        生成图片提示词

        Args:
            slide: 幻灯片内容

        Returns:
            图片生成提示词
        """
        title = slide.get("title", "")
        content = slide.get("content", "")
        image_type = slide.get("suggested_image_type", "photo")

        # 构建基础提示词
        if image_type == "diagram":
            base_prompt = f"Professional business diagram showing {title}, clean minimalist design, "
            base_prompt += "vector illustration, corporate colors, white background"
        elif image_type == "chart":
            base_prompt = f"Data visualization chart for {title}, modern infographic style, "
            base_prompt += "clear labels, professional color scheme"
        else:  # photo
            base_prompt = f"Professional stock photo representing {title}, business context, "
            base_prompt += "high quality, modern office or technology theme"

        # 添加内容相关的细节
        if content:
            if isinstance(content, str):
                content_hint = content[:100]
            elif isinstance(content, list):
                content_hint = " ".join(content)[:100]
            else:
                content_hint = str(content)[:100]

            base_prompt += f", related to: {content_hint}"

        # 添加风格修饰词
        base_prompt += ", professional presentation quality, 16:9 aspect ratio"

        return base_prompt

    def apply_template(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用模板样式

        Args:
            content: PPT内容

        Returns:
            应用样式后的内容
        """
        template_name = content.get("template", "modern")
        template = self.templates.get(template_name, self.templates["default"])

        # 应用样式到内容
        styled_content = content.copy()
        styled_content["template_applied"] = template_name
        styled_content["styles"] = template

        # 为每个幻灯片应用样式
        if "slides" in styled_content:
            for slide in styled_content["slides"]:
                slide["style"] = {
                    "title_font_size": template["font_size"]["title"],
                    "content_font_size": template["font_size"]["content"],
                    "title_color": template["primary_color"],
                    "content_color": template["secondary_color"],
                    "background": template["background"]
                }

        return styled_content

    def optimize_layout(self, slide: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化幻灯片布局

        Args:
            slide: 幻灯片内容

        Returns:
            优化后的布局信息
        """
        has_image = slide.get("image_url") is not None
        content_length = len(slide.get("content", []))
        slide_type = slide.get("type", "content")

        # 根据内容决定布局
        if slide_type == "title":
            layout = {
                "layout_type": "title_slide",
                "title_position": "center",
                "subtitle_position": "center_below",
                "image_position": "background" if has_image else None
            }
        elif slide_type == "conclusion":
            layout = {
                "layout_type": "summary",
                "title_position": "top",
                "content_position": "center",
                "image_position": "bottom" if has_image else None
            }
        else:  # content slides
            if has_image:
                if content_length <= 3:
                    # 少量内容，使用两栏布局
                    layout = {
                        "layout_type": "two_column",
                        "title_position": "top",
                        "text_position": "left",
                        "image_position": "right",
                        "column_ratio": "60:40"
                    }
                else:
                    # 内容较多，图片放在底部
                    layout = {
                        "layout_type": "content_with_image",
                        "title_position": "top",
                        "text_position": "middle",
                        "image_position": "bottom",
                        "image_size": "small"
                    }
            else:
                # 纯文本布局
                layout = {
                    "layout_type": "text_only",
                    "title_position": "top",
                    "content_position": "center",
                    "text_alignment": "left" if content_length > 3 else "center"
                }

        # 合并原始内容和布局信息
        optimized = slide.copy()
        optimized.update(layout)

        # 添加间距建议
        optimized["spacing"] = {
            "title_margin": "10%",
            "content_padding": "5%",
            "line_spacing": 1.5
        }

        return optimized

    def generate_color_scheme(self, theme: str) -> Dict[str, str]:
        """
        生成配色方案

        Args:
            theme: 主题名称

        Returns:
            配色方案
        """
        schemes = {
            "professional": {
                "primary": "#1E3A8A",
                "secondary": "#3B82F6",
                "accent": "#60A5FA",
                "text": "#1F2937",
                "background": "#FFFFFF"
            },
            "creative": {
                "primary": "#7C3AED",
                "secondary": "#A78BFA",
                "accent": "#FCD34D",
                "text": "#111827",
                "background": "#FEF3C7"
            },
            "minimal": {
                "primary": "#000000",
                "secondary": "#6B7280",
                "accent": "#EF4444",
                "text": "#111827",
                "background": "#F9FAFB"
            }
        }

        return schemes.get(theme, schemes["professional"])

    def create_visual_hierarchy(self, slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        创建视觉层次结构

        Args:
            slides: 幻灯片列表

        Returns:
            带有视觉层次的幻灯片列表
        """
        enhanced_slides = []

        for i, slide in enumerate(slides):
            enhanced = slide.copy()

            # 根据位置设置不同的视觉重要性
            if i == 0:  # 标题页
                enhanced["visual_weight"] = "heavy"
                enhanced["font_scale"] = 1.2
            elif i == len(slides) - 1:  # 结论页
                enhanced["visual_weight"] = "medium-heavy"
                enhanced["font_scale"] = 1.1
            elif slide.get("type") == "section":  # 章节页
                enhanced["visual_weight"] = "medium"
                enhanced["font_scale"] = 1.15
            else:  # 普通内容页
                enhanced["visual_weight"] = "normal"
                enhanced["font_scale"] = 1.0

            # 添加过渡效果建议
            if i > 0:
                enhanced["transition"] = "fade"
                enhanced["transition_duration"] = 0.5

            enhanced_slides.append(enhanced)

        return enhanced_slides

    def suggest_icons(self, bullet_points: List[str]) -> List[str]:
        """
        为要点建议图标

        Args:
            bullet_points: 要点列表

        Returns:
            图标建议列表
        """
        icons = []

        for point in bullet_points:
            point_lower = point.lower()

            if any(word in point_lower for word in ["growth", "增长", "提升", "上升"]):
                icons.append("chart-line-up")
            elif any(word in point_lower for word in ["team", "团队", "协作", "合作"]):
                icons.append("users")
            elif any(word in point_lower for word in ["idea", "创新", "想法", "创意"]):
                icons.append("lightbulb")
            elif any(word in point_lower for word in ["target", "目标", "目的", "达成"]):
                icons.append("target")
            elif any(word in point_lower for word in ["data", "数据", "分析", "统计"]):
                icons.append("chart-bar")
            else:
                icons.append("check-circle")

        return icons