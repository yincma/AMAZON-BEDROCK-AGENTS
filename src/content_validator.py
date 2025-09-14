"""
内容验证器 - 验证生成的PPT内容质量和格式
"""
import json
from typing import Dict, List, Any, Optional
import logging
import re

from .config import (
    MIN_BULLET_LENGTH,
    MAX_BULLET_LENGTH,
    MAX_TITLE_LENGTH
)

logger = logging.getLogger(__name__)

def validate_content_format(content: Dict) -> bool:
    """验证内容格式是否符合预定义的JSON模式

    Args:
        content: 要验证的内容

    Returns:
        True如果格式正确，否则False
    """
    # 检查必要的顶级字段
    if not isinstance(content, dict):
        return False

    # 检查slides字段
    if "slides" not in content:
        return False

    slides = content.get("slides", [])
    if not isinstance(slides, list):
        return False

    # 验证每个slide的格式
    for slide in slides:
        if not isinstance(slide, dict):
            return False

        # 检查必要字段
        required_fields = ["title", "bullet_points"]
        for field in required_fields:
            if field not in slide:
                return False

        # 验证bullet_points是列表
        if not isinstance(slide.get("bullet_points", []), list):
            return False

        # 验证title是字符串
        if not isinstance(slide.get("title", ""), str):
            return False

    return True

def validate_content_length(content: Dict) -> bool:
    """验证内容长度是否在合理范围内

    Args:
        content: 要验证的内容

    Returns:
        True如果长度合适，否则False
    """
    slides = content.get("slides", [])

    for slide in slides:
        # 验证标题长度
        title = slide.get("title", "")
        if len(title) > MAX_TITLE_LENGTH:
            logger.warning(f"标题过长: {len(title)} 字符")
            return False

        # 验证要点长度
        bullet_points = slide.get("bullet_points", [])
        for bullet in bullet_points:
            if not isinstance(bullet, str):
                continue

            bullet_length = len(bullet)
            if bullet_length < MIN_BULLET_LENGTH:
                logger.warning(f"要点过短: {bullet_length} 字符")
                return False
            if bullet_length > MAX_BULLET_LENGTH:
                logger.warning(f"要点过长: {bullet_length} 字符")
                return False

    return True

def check_content_coherence(outline: Dict, content: Dict) -> bool:
    """检查生成的内容是否与原始大纲主题一致

    Args:
        outline: 原始大纲
        content: 生成的内容

    Returns:
        True如果内容连贯一致，否则False
    """
    # 获取主题关键词
    topic = outline.get("title", "")
    if not topic:
        return True  # 没有主题时跳过检查

    # 提取主题关键词（简单的分词）
    topic_keywords = set()
    # 中文分词（简单实现）- 提取2字以上的词组
    chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', topic.lower())
    topic_keywords.update(chinese_words)
    # 英文分词
    english_words = re.findall(r'[a-zA-Z]{2,}', topic.lower())
    topic_keywords.update([w.lower() for w in english_words])

    # 特殊处理常见的AI相关词汇
    ai_keywords = {'人工智能', 'ai', '智能', '机器', '学习', '深度', '神经', '算法'}

    # 检查内容中是否包含主题相关词汇
    slides = content.get("slides", [])
    relevance_score = 0
    total_content = ""

    for slide in slides:
        slide_content = slide.get("title", "") + " "
        slide_content += " ".join(slide.get("bullet_points", []))
        total_content += slide_content.lower() + " "

    # 计算相关性分数
    found_keywords = set()
    for keyword in topic_keywords:
        if keyword in total_content:
            found_keywords.add(keyword)
            relevance_score += 1

    # 检查AI相关关键词
    for ai_word in ai_keywords:
        if ai_word in total_content.lower():
            relevance_score += 0.5  # AI相关词汇给予部分分数

    # 如果有超过25%的关键词出现在内容中，或者有AI相关词汇，认为是连贯的
    if topic_keywords:
        coherence_ratio = relevance_score / len(topic_keywords)
        return coherence_ratio >= 0.25 or relevance_score >= 1

    # 如果没有提取到关键词，检查是否有相关内容
    return len(total_content) > 50  # 至少有一定长度的内容

def validate_content_quality(content: Dict, min_length: int = MIN_BULLET_LENGTH,
                            max_length: int = MAX_BULLET_LENGTH) -> bool:
    """验证内容质量

    Args:
        content: 要验证的内容
        min_length: 最小要点长度
        max_length: 最大要点长度

    Returns:
        True如果质量合格，否则False
    """
    slides = content.get("slides", [])

    if not slides:
        return False

    for slide in slides:
        # 检查要点数量
        bullet_points = slide.get("bullet_points", [])
        if len(bullet_points) < 3:
            logger.warning(f"要点数量不足: {len(bullet_points)}")
            return False

        # 检查每个要点的质量
        for bullet in bullet_points:
            if not isinstance(bullet, str):
                return False

            # 检查长度
            if not (min_length <= len(bullet) <= max_length):
                return False

            # 检查是否有实质内容（不只是空白或标点）
            if not re.search(r'[\u4e00-\u9fa5a-zA-Z]', bullet):
                return False

    return True

def validate_speaker_notes(content: Dict) -> bool:
    """验证演讲者备注

    Args:
        content: 要验证的内容

    Returns:
        True如果备注存在且有效，否则False
    """
    slides = content.get("slides", [])

    for slide in slides:
        speaker_notes = slide.get("speaker_notes", "")

        # 检查备注是否存在
        if not speaker_notes:
            continue

        # 检查备注长度（至少20个字符）
        if len(speaker_notes) < 20:
            logger.warning(f"演讲备注过短: {len(speaker_notes)} 字符")
            return False

        # 检查是否有实质内容
        if not re.search(r'[\u4e00-\u9fa5a-zA-Z]', speaker_notes):
            return False

    return True

def validate_complete_presentation(outline: Dict, content: Dict) -> Dict[str, Any]:
    """完整验证演示文稿

    Args:
        outline: PPT大纲
        content: 生成的内容

    Returns:
        包含验证结果的字典
    """
    validation_results = {
        "is_valid": True,
        "errors": [],
        "warnings": []
    }

    # 格式验证
    if not validate_content_format(content):
        validation_results["is_valid"] = False
        validation_results["errors"].append("内容格式不正确")

    # 长度验证
    if not validate_content_length(content):
        validation_results["warnings"].append("部分内容长度不符合规范")

    # 连贯性验证
    if not check_content_coherence(outline, content):
        validation_results["warnings"].append("内容与主题相关性较低")

    # 质量验证
    if not validate_content_quality(content):
        validation_results["is_valid"] = False
        validation_results["errors"].append("内容质量不符合要求")

    # 演讲备注验证
    if not validate_speaker_notes(content):
        validation_results["warnings"].append("演讲备注可能需要改进")

    return validation_results