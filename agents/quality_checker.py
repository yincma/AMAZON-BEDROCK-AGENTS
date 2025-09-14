"""
Quality Checker Agent - 质量检查器
负责检查内容完整性、视觉质量、连贯性
"""
import json
from typing import Dict, Any, List
import boto3
from botocore.config import Config

# 统一使用的模型
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"  # inference profile


class QualityCheckerAgent:
    """质量检查Agent"""

    def __init__(self):
        """初始化Quality Checker Agent"""
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1',
            config=Config(read_timeout=30, retries={'max_attempts': 3})
        )

    def check_completeness(self, presentation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检查内容完整性

        Args:
            presentation: PPT内容

        Returns:
            问题列表
        """
        issues = []
        slides = presentation.get("slides", [])

        for i, slide in enumerate(slides, 1):
            # 检查标题
            if not slide.get("title") or slide["title"].strip() == "":
                issues.append({
                    "slide": i,
                    "issue": "missing_title",
                    "severity": "high",
                    "description": f"第{i}页缺少标题"
                })

            # 检查内容
            content = slide.get("content", "")
            bullet_points = slide.get("bullet_points", [])

            if slide.get("type") != "title":  # 标题页可以没有内容
                if not content and not bullet_points:
                    issues.append({
                        "slide": i,
                        "issue": "missing_content",
                        "severity": "high",
                        "description": f"第{i}页缺少内容"
                    })
                elif bullet_points and len(bullet_points) < 2:
                    issues.append({
                        "slide": i,
                        "issue": "insufficient_content",
                        "severity": "medium",
                        "description": f"第{i}页内容过少"
                    })

            # 检查演讲者备注
            if not slide.get("speaker_notes"):
                issues.append({
                    "slide": i,
                    "issue": "missing_speaker_notes",
                    "severity": "low",
                    "description": f"第{i}页缺少演讲者备注"
                })

        return issues

    def evaluate_visual_quality(self, presentation: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估视觉质量

        Args:
            presentation: PPT内容

        Returns:
            视觉质量评分和建议
        """
        slides = presentation.get("slides", [])
        total_slides = len(slides)

        # 统计图片覆盖率
        slides_with_images = sum(1 for slide in slides if slide.get("image_url"))
        image_coverage = slides_with_images / total_slides if total_slides > 0 else 0

        # 计算得分
        score = 0
        suggestions = []

        # 图片覆盖率评分（40分）
        image_score = image_coverage * 40
        score += image_score

        if image_coverage < 0.5:
            suggestions.append({
                "type": "image_coverage",
                "message": "建议增加更多配图，当前只有{:.0%}的页面有图片".format(image_coverage),
                "priority": "high"
            })

        # 布局多样性评分（30分）
        layout_types = set(slide.get("layout_type", "default") for slide in slides)
        layout_diversity = len(layout_types) / max(3, total_slides // 3)  # 期望至少有3种布局
        layout_score = min(30, layout_diversity * 30)
        score += layout_score

        if len(layout_types) < 3:
            suggestions.append({
                "type": "layout_diversity",
                "message": "建议使用更多样的布局，增加视觉吸引力",
                "priority": "medium"
            })

        # 样式一致性评分（30分）
        template_applied = all(slide.get("style") for slide in slides)
        consistency_score = 30 if template_applied else 15
        score += consistency_score

        if not template_applied:
            suggestions.append({
                "type": "style_consistency",
                "message": "部分页面缺少统一样式，建议应用模板",
                "priority": "medium"
            })

        return {
            "overall_score": round(score),
            "image_coverage": image_coverage,
            "layout_diversity": len(layout_types),
            "style_consistency": template_applied,
            "suggestions": suggestions,
            "grade": self._get_grade(score)
        }

    def check_coherence(self, presentation: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查内容连贯性

        Args:
            presentation: PPT内容

        Returns:
            连贯性评分和问题
        """
        slides = presentation.get("slides", [])
        issues = []
        score = 100  # 从满分开始扣分

        for i in range(len(slides) - 1):
            current_slide = slides[i]
            next_slide = slides[i + 1]

            # 检查主题跳跃
            coherence_score = self._calculate_coherence(
                current_slide.get("title", ""),
                next_slide.get("title", ""),
                current_slide.get("content", ""),
                next_slide.get("content", "")
            )

            if coherence_score < 0.5:
                issues.append({
                    "between_slides": [i + 1, i + 2],
                    "issue": "topic_jump",
                    "description": f"第{i+1}页到第{i+2}页主题跳跃较大",
                    "severity": "medium"
                })
                score -= 10

        # 检查整体结构
        has_intro = slides[0].get("type") == "title" if slides else False
        has_conclusion = slides[-1].get("type") in ["conclusion", "summary"] if slides else False

        if not has_intro:
            issues.append({
                "issue": "missing_introduction",
                "description": "缺少标题页",
                "severity": "high"
            })
            score -= 15

        if not has_conclusion:
            issues.append({
                "issue": "missing_conclusion",
                "description": "缺少总结页",
                "severity": "medium"
            })
            score -= 10

        return {
            "score": max(0, score),
            "issues": issues,
            "has_proper_structure": has_intro and has_conclusion,
            "recommendation": self._get_coherence_recommendation(score, issues)
        }

    def _calculate_coherence(self, title1: str, title2: str, content1: str, content2: str) -> float:
        """
        计算两页之间的连贯性分数

        Args:
            title1, title2: 两页的标题
            content1, content2: 两页的内容

        Returns:
            连贯性分数 (0-1)
        """
        # 简单的关键词匹配算法
        words1 = set(title1.lower().split() + str(content1).lower().split())
        words2 = set(title2.lower().split() + str(content2).lower().split())

        # 去除常见词
        stop_words = {"的", "是", "在", "和", "了", "有", "我", "他", "她", "它", "the", "is", "at", "and", "a", "an"}
        words1 = words1 - stop_words
        words2 = words2 - stop_words

        if not words1 or not words2:
            return 0.5  # 默认中等连贯性

        # 计算Jaccard相似度
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0

    def _get_grade(self, score: float) -> str:
        """根据分数返回等级"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _get_coherence_recommendation(self, score: int, issues: List[Dict[str, Any]]) -> str:
        """生成连贯性改进建议"""
        if score >= 90:
            return "内容连贯性很好，逻辑清晰"
        elif score >= 70:
            return "内容基本连贯，建议加强页面间的过渡"
        else:
            recommendations = ["内容连贯性需要改进"]
            if any(issue.get("issue") == "topic_jump" for issue in issues):
                recommendations.append("建议添加过渡页面或调整内容顺序")
            if any(issue.get("issue") == "missing_introduction" for issue in issues):
                recommendations.append("需要添加引言页")
            if any(issue.get("issue") == "missing_conclusion" for issue in issues):
                recommendations.append("需要添加总结页")
            return "；".join(recommendations)

    def generate_improvement_suggestions(self, presentation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成改进建议

        Args:
            presentation: PPT内容

        Returns:
            改进建议列表
        """
        suggestions = []

        # 检查各个方面
        completeness_issues = self.check_completeness(presentation)
        visual_evaluation = self.evaluate_visual_quality(presentation)
        coherence_check = self.check_coherence(presentation)

        # 基于完整性问题生成建议
        for issue in completeness_issues[:3]:  # 只取前3个最重要的问题
            suggestions.append({
                "type": "completeness",
                "slide": issue.get("slide"),
                "action": self._get_fix_action(issue["issue"]),
                "priority": issue["severity"]
            })

        # 基于视觉质量生成建议
        for suggestion in visual_evaluation["suggestions"][:2]:
            suggestions.append({
                "type": "visual",
                "action": suggestion["message"],
                "priority": suggestion["priority"]
            })

        # 基于连贯性生成建议
        if coherence_check["score"] < 80:
            suggestions.append({
                "type": "coherence",
                "action": coherence_check["recommendation"],
                "priority": "high" if coherence_check["score"] < 60 else "medium"
            })

        return suggestions

    def _get_fix_action(self, issue_type: str) -> str:
        """根据问题类型返回修复建议"""
        actions = {
            "missing_title": "添加页面标题",
            "missing_content": "补充页面内容",
            "insufficient_content": "增加更多要点",
            "missing_speaker_notes": "添加演讲者备注",
            "missing_image": "添加配图"
        }
        return actions.get(issue_type, "检查并修复问题")