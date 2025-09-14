"""
AI PPT Assistant Phase 3 - 一致性管理器

提供演示文稿一致性检测和自动修复功能。

功能特性：
- 检测内容不一致性
- 样式一致性验证
- 主题对齐检查
- 自动修复建议
- 版本控制支持
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple
import boto3
from botocore.exceptions import ClientError
from collections import Counter
import statistics

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ConsistencyError(Exception):
    """一致性检查异常基类"""

    def __init__(self, message: str, error_code: str = "CONSISTENCY_ERROR", details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ConsistencyManager:
    """一致性管理器 - 负责演示文稿一致性检测和修复

    功能：
    - 样式一致性检查
    - 内容结构一致性
    - 主题对齐度分析
    - 自动修复建议
    - 一致性评分
    """

    def __init__(self, s3_client=None, bucket_name: str = None):
        """
        初始化一致性管理器

        Args:
            s3_client: S3客户端
            bucket_name: S3存储桶名称
        """
        self.s3_client = s3_client or boto3.client('s3')
        self.bucket_name = bucket_name or "ai-ppt-presentations"

        # 一致性检查配置
        self.style_rules = {
            "title_length": {"min": 5, "max": 80},
            "content_items": {"min": 2, "max": 8},
            "content_item_length": {"min": 3, "max": 100},
            "speaker_notes_length": {"min": 10, "max": 500}
        }

        self.theme_keywords = {
            "technology": ["技术", "科技", "AI", "人工智能", "机器学习", "数据", "算法", "系统"],
            "business": ["商业", "市场", "客户", "销售", "收入", "增长", "策略", "管理"],
            "education": ["教育", "学习", "培训", "知识", "技能", "课程", "学生", "教学"],
            "healthcare": ["医疗", "健康", "医院", "患者", "治疗", "药物", "诊断", "康复"]
        }

        logger.info(f"ConsistencyManager初始化完成，使用存储桶: {self.bucket_name}")

    def validate_consistency(self, presentation_id: str) -> Dict[str, Any]:
        """
        验证演示文稿一致性

        Args:
            presentation_id: 演示文稿ID

        Returns:
            一致性验证结果
        """
        try:
            # 获取演示文稿数据
            presentation_data = self._get_presentation_data(presentation_id)
            slides = presentation_data.get("slides", [])

            if not slides:
                return {
                    "is_consistent": True,
                    "message": "No slides to validate",
                    "style_coherence": 1.0,
                    "theme_alignment": 1.0,
                    "recommendations": []
                }

            # 执行各项一致性检查
            style_result = self._check_style_consistency(slides)
            theme_result = self._check_theme_alignment(slides, presentation_data.get("topic", ""))
            structure_result = self._check_structure_consistency(slides)

            # 计算综合评分
            overall_score = (
                style_result["score"] * 0.4 +
                theme_result["score"] * 0.3 +
                structure_result["score"] * 0.3
            )

            # 收集所有问题和建议
            all_issues = []
            all_recommendations = []

            for result in [style_result, theme_result, structure_result]:
                all_issues.extend(result.get("issues", []))
                all_recommendations.extend(result.get("recommendations", []))

            is_consistent = overall_score >= 0.8 and len(all_issues) == 0

            logger.info(f"演示文稿 {presentation_id} 一致性检查完成，综合评分: {overall_score:.2f}")

            return {
                "is_consistent": is_consistent,
                "style_coherence": style_result["score"],
                "theme_alignment": theme_result["score"],
                "structure_consistency": structure_result["score"],
                "overall_score": overall_score,
                "issues": all_issues,
                "recommendations": all_recommendations,
                "details": {
                    "style": style_result,
                    "theme": theme_result,
                    "structure": structure_result
                }
            }

        except Exception as e:
            logger.error(f"一致性验证失败: {str(e)}")
            raise ConsistencyError(f"Failed to validate consistency: {str(e)}") from e

    def auto_fix_consistency(self, fix_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        自动修复一致性问题

        Args:
            fix_request: 修复请求

        Returns:
            修复结果
        """
        presentation_id = fix_request["presentation_id"]
        preserve_content = fix_request.get("preserve_content", True)
        auto_fix = fix_request.get("auto_fix", True)

        if not auto_fix:
            return {
                "status": "skipped",
                "message": "Auto-fix is disabled"
            }

        try:
            # 获取演示文稿数据
            presentation_data = self._get_presentation_data(presentation_id)
            slides = presentation_data.get("slides", [])

            if not slides:
                return {
                    "status": "no_changes",
                    "message": "No slides to fix"
                }

            # 执行修复
            changes_made = []
            fixed_issues = 0

            # 1. 标准化字体大小
            font_changes = self._standardize_fonts(slides)
            if font_changes:
                changes_made.extend(font_changes)
                fixed_issues += len(font_changes)

            # 2. 统一色彩方案
            color_changes = self._standardize_colors(slides)
            if color_changes:
                changes_made.extend(color_changes)
                fixed_issues += len(color_changes)

            # 3. 规范内容结构
            if not preserve_content:
                structure_changes = self._standardize_structure(slides)
                if structure_changes:
                    changes_made.extend(structure_changes)
                    fixed_issues += len(structure_changes)

            # 4. 统一布局样式
            layout_changes = self._standardize_layouts(slides)
            if layout_changes:
                changes_made.extend(layout_changes)
                fixed_issues += len(layout_changes)

            # 更新演示文稿数据
            presentation_data["slides"] = slides
            presentation_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # 保存修复后的数据
            self._save_presentation_data(presentation_id, presentation_data)

            # 重新检查一致性
            final_consistency = self.validate_consistency(presentation_id)

            logger.info(f"自动修复完成，修复了 {fixed_issues} 个问题")

            return {
                "status": "fixed",
                "fixed_issues": fixed_issues,
                "changes_made": changes_made,
                "final_consistency_score": final_consistency.get("overall_score", 0),
                "presentation_updated": True
            }

        except Exception as e:
            logger.error(f"自动修复失败: {str(e)}")
            raise ConsistencyError(f"Failed to auto-fix consistency: {str(e)}") from e

    def _get_presentation_data(self, presentation_id: str) -> Dict[str, Any]:
        """获取演示文稿数据"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=f"presentations/{presentation_id}.json"
            )
            return json.loads(response['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise ConsistencyError(f"Presentation {presentation_id} not found")
            raise ConsistencyError(f"Failed to retrieve presentation: {str(e)}")

    def _save_presentation_data(self, presentation_id: str, data: Dict[str, Any]) -> None:
        """保存演示文稿数据"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"presentations/{presentation_id}.json",
                Body=json.dumps(data, ensure_ascii=False, indent=2),
                ContentType="application/json"
            )
        except ClientError as e:
            raise ConsistencyError(f"Failed to save presentation: {str(e)}")

    def _check_style_consistency(self, slides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查样式一致性"""
        issues = []
        recommendations = []

        # 检查标题长度一致性
        title_lengths = []
        for i, slide in enumerate(slides, 1):
            title = slide.get("title", "")
            title_length = len(title)
            title_lengths.append(title_length)

            rules = self.style_rules["title_length"]
            if title_length < rules["min"]:
                issues.append(f"Slide {i} title too short ({title_length} chars)")
                recommendations.append(f"Expand slide {i} title to at least {rules['min']} characters")
            elif title_length > rules["max"]:
                issues.append(f"Slide {i} title too long ({title_length} chars)")
                recommendations.append(f"Shorten slide {i} title to under {rules['max']} characters")

        # 检查内容项数量一致性
        content_counts = []
        for i, slide in enumerate(slides, 1):
            content = slide.get("content", [])
            if isinstance(content, list):
                content_count = len(content)
                content_counts.append(content_count)

                rules = self.style_rules["content_items"]
                if content_count < rules["min"]:
                    issues.append(f"Slide {i} has too few content items ({content_count})")
                    recommendations.append(f"Add more content items to slide {i}")
                elif content_count > rules["max"]:
                    issues.append(f"Slide {i} has too many content items ({content_count})")
                    recommendations.append(f"Reduce content items in slide {i}")

        # 计算一致性评分
        score = 1.0
        if issues:
            # 根据问题数量降低评分
            score = max(0.0, 1.0 - (len(issues) * 0.1))

        return {
            "score": score,
            "issues": issues,
            "recommendations": recommendations,
            "metrics": {
                "title_lengths": title_lengths,
                "content_counts": content_counts
            }
        }

    def _check_theme_alignment(self, slides: List[Dict[str, Any]], topic: str) -> Dict[str, Any]:
        """检查主题对齐度"""
        # 分析主题关键词
        detected_theme = self._detect_theme(slides, topic)
        theme_score = self._calculate_theme_score(slides, detected_theme)

        issues = []
        recommendations = []

        if theme_score < 0.6:
            issues.append("Low theme consistency across slides")
            recommendations.append("Align slide content with main presentation theme")

        # 检查每个幻灯片的主题符合度
        for i, slide in enumerate(slides, 1):
            slide_score = self._calculate_slide_theme_score(slide, detected_theme)
            if slide_score < 0.4:
                issues.append(f"Slide {i} theme deviation detected")
                recommendations.append(f"Align slide {i} content with presentation theme")

        return {
            "score": theme_score,
            "detected_theme": detected_theme,
            "issues": issues,
            "recommendations": recommendations
        }

    def _check_structure_consistency(self, slides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查结构一致性"""
        issues = []
        recommendations = []

        # 检查幻灯片结构模式
        structures = []
        for slide in slides:
            structure = {
                "has_title": bool(slide.get("title")),
                "has_content": bool(slide.get("content")),
                "has_image": bool(slide.get("image_url")),
                "has_notes": bool(slide.get("speaker_notes"))
            }
            structures.append(structure)

        # 分析结构一致性
        structure_consistency = self._analyze_structure_patterns(structures)

        if structure_consistency < 0.8:
            issues.append("Inconsistent slide structure patterns")
            recommendations.append("Standardize slide layout and components")

        return {
            "score": structure_consistency,
            "issues": issues,
            "recommendations": recommendations,
            "structures": structures
        }

    def _detect_theme(self, slides: List[Dict[str, Any]], topic: str) -> str:
        """检测演示文稿主题"""
        all_text = topic + " "

        for slide in slides:
            all_text += slide.get("title", "") + " "
            content = slide.get("content", [])
            if isinstance(content, list):
                all_text += " ".join(str(item) for item in content) + " "

        all_text = all_text.lower()

        # 统计各主题关键词出现频率
        theme_scores = {}
        for theme, keywords in self.theme_keywords.items():
            score = sum(all_text.count(keyword) for keyword in keywords)
            theme_scores[theme] = score

        # 返回得分最高的主题
        if theme_scores:
            return max(theme_scores, key=theme_scores.get)
        return "general"

    def _calculate_theme_score(self, slides: List[Dict[str, Any]], theme: str) -> float:
        """计算整体主题一致性评分"""
        if theme not in self.theme_keywords:
            return 0.8  # 默认评分

        keyword_counts = []
        keywords = self.theme_keywords[theme]

        for slide in slides:
            slide_text = (slide.get("title", "") + " " +
                         " ".join(str(item) for item in slide.get("content", []))).lower()
            count = sum(slide_text.count(keyword) for keyword in keywords)
            keyword_counts.append(count)

        if not keyword_counts:
            return 0.5

        # 基于关键词分布计算评分
        avg_count = statistics.mean(keyword_counts)
        if avg_count == 0:
            return 0.3

        # 计算一致性（减少方差的影响）
        variance = statistics.variance(keyword_counts) if len(keyword_counts) > 1 else 0
        consistency = 1.0 / (1.0 + variance / (avg_count + 1))

        return min(1.0, consistency * 0.8 + 0.2)

    def _calculate_slide_theme_score(self, slide: Dict[str, Any], theme: str) -> float:
        """计算单个幻灯片的主题符合度"""
        if theme not in self.theme_keywords:
            return 0.8

        slide_text = (slide.get("title", "") + " " +
                     " ".join(str(item) for item in slide.get("content", []))).lower()

        keywords = self.theme_keywords[theme]
        keyword_count = sum(slide_text.count(keyword) for keyword in keywords)
        text_length = len(slide_text.split())

        if text_length == 0:
            return 0.5

        # 基于关键词密度计算评分
        density = keyword_count / text_length
        return min(1.0, density * 10)  # 调整比例

    def _analyze_structure_patterns(self, structures: List[Dict[str, Any]]) -> float:
        """分析结构模式一致性"""
        if not structures:
            return 1.0

        # 统计各种结构组合的出现频率
        structure_signatures = []
        for structure in structures:
            signature = tuple(sorted(structure.items()))
            structure_signatures.append(signature)

        # 计算最常见结构的比例
        signature_counts = Counter(structure_signatures)
        most_common_count = signature_counts.most_common(1)[0][1] if signature_counts else 0
        total_count = len(structure_signatures)

        consistency = most_common_count / total_count if total_count > 0 else 0
        return consistency

    def _standardize_fonts(self, slides: List[Dict[str, Any]]) -> List[str]:
        """标准化字体大小"""
        changes = []
        # 这里简化处理，实际应该分析字体样式
        for i, slide in enumerate(slides, 1):
            # 模拟字体标准化
            if "font_style" in slide and slide["font_style"] != "standard":
                slide["font_style"] = "standard"
                changes.append(f"Standardized font in slide {i}")
        return changes

    def _standardize_colors(self, slides: List[Dict[str, Any]]) -> List[str]:
        """统一色彩方案"""
        changes = []
        standard_colors = {"primary": "#1f4e79", "secondary": "#70ad47", "accent": "#c5504b"}

        for i, slide in enumerate(slides, 1):
            if "colors" in slide and slide["colors"] != standard_colors:
                slide["colors"] = standard_colors
                changes.append(f"Applied consistent color scheme to slide {i}")
        return changes

    def _standardize_structure(self, slides: List[Dict[str, Any]]) -> List[str]:
        """规范内容结构"""
        changes = []
        # 确保所有幻灯片都有基本结构
        for i, slide in enumerate(slides, 1):
            if not slide.get("title"):
                slide["title"] = f"幻灯片 {i}"
                changes.append(f"Added title to slide {i}")

            if not slide.get("content"):
                slide["content"] = ["内容待补充"]
                changes.append(f"Added placeholder content to slide {i}")
        return changes

    def _standardize_layouts(self, slides: List[Dict[str, Any]]) -> List[str]:
        """统一布局样式"""
        changes = []
        standard_layout = "title_content"

        for i, slide in enumerate(slides, 1):
            current_layout = slide.get("layout", "default")
            if current_layout != standard_layout:
                slide["layout"] = standard_layout
                changes.append(f"Standardized layout for slide {i}")
        return changes


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda处理函数

    Args:
        event: Lambda事件数据
        context: Lambda上下文

    Returns:
        API Gateway响应
    """
    try:
        # 解析请求路径和方法
        http_method = event.get('httpMethod', 'GET')
        path_parameters = event.get('pathParameters', {})
        presentation_id = path_parameters.get('presentation_id')

        if not presentation_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'MISSING_PARAMETER',
                    'message': 'presentation_id is required'
                }, ensure_ascii=False)
            }

        # 创建一致性管理器
        manager = ConsistencyManager()

        if http_method == 'GET':
            # 检查一致性
            result = manager.validate_consistency(presentation_id)
        elif http_method == 'POST':
            # 自动修复一致性
            body = json.loads(event.get('body', '{}'))
            fix_request = {
                "presentation_id": presentation_id,
                **body
            }
            result = manager.auto_fix_consistency(fix_request)
        else:
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'METHOD_NOT_ALLOWED',
                    'message': f'Method {http_method} not allowed'
                }, ensure_ascii=False)
            }

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(result, ensure_ascii=False)
        }

    except ConsistencyError as e:
        logger.error(f"一致性错误: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': e.error_code,
                'message': str(e),
                'details': e.details
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"未预期错误: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred'
            }, ensure_ascii=False)
        }


if __name__ == "__main__":
    # 本地测试代码
    print("测试一致性管理器:")

    manager = ConsistencyManager()

    # 测试数据
    test_slides = [
        {
            "slide_number": 1,
            "title": "AI技术概述",
            "content": ["人工智能定义", "发展历程", "核心技术"],
            "image_url": "s3://bucket/images/slide1.jpg",
            "speaker_notes": "这是第一页的演讲备注"
        },
        {
            "slide_number": 2,
            "title": "机器学习",
            "content": ["监督学习", "无监督学习"],
            "image_url": "s3://bucket/images/slide2.jpg",
            "speaker_notes": "第二页备注"
        }
    ]

    try:
        # 测试样式一致性检查
        style_result = manager._check_style_consistency(test_slides)
        print(f"样式一致性评分: {style_result['score']:.2f}")
        print(f"发现问题: {len(style_result['issues'])}")

        # 测试主题检测
        theme = manager._detect_theme(test_slides, "AI技术发展趋势")
        print(f"检测到的主题: {theme}")

        # 测试结构一致性
        structures = []
        for slide in test_slides:
            structure = {
                "has_title": bool(slide.get("title")),
                "has_content": bool(slide.get("content")),
                "has_image": bool(slide.get("image_url")),
                "has_notes": bool(slide.get("speaker_notes"))
            }
            structures.append(structure)

        structure_score = manager._analyze_structure_patterns(structures)
        print(f"结构一致性评分: {structure_score:.2f}")

        print("\n一致性管理器测试完成")

    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")