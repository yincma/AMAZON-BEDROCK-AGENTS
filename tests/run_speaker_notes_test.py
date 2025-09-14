#!/usr/bin/env python3
"""
演讲者备注功能测试运行器
主要测试核心功能，跳过需要AWS权限的测试
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入测试所需的模块
from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator
from lambdas.utils.speaker_notes_validator import SpeakerNotesValidator
from lambdas.utils.content_relevance_checker import ContentRelevanceChecker
from lambdas.services.pptx_integration_service import PPTXIntegrationService

def test_basic_generation():
    """测试基本的演讲者备注生成"""
    print("测试1: 基本生成功能...")

    generator = SpeakerNotesGenerator(use_fallback=True)

    slide_data = {
        "slide_number": 1,
        "title": "人工智能概述",
        "content": [
            "AI是计算机科学的一个分支",
            "从1950年代至今的发展历程",
            "AI正在改变我们的生活方式"
        ]
    }

    notes = generator.generate_notes(slide_data)

    assert len(notes) >= 100 and len(notes) <= 200, f"备注长度不符合要求: {len(notes)}"
    assert "人工智能" in notes or "幻灯片" in notes, "备注内容不相关"
    print("✓ 通过")

def test_length_validation():
    """测试长度验证"""
    print("\n测试2: 长度验证...")

    validator = SpeakerNotesValidator()

    # 测试太短的备注
    short_notes = "太短了"
    assert not validator.validate_length(short_notes), "短备注应该验证失败"

    # 测试正常长度的备注
    normal_notes = "这是一个长度适中的演讲者备注内容。" * 10  # 约180字
    assert validator.validate_length(normal_notes), f"正常备注应该验证通过，长度: {len(normal_notes.replace(' ', ''))}"

    # 测试太长的备注
    long_notes = "这是一个过长的演讲者备注。" * 20  # 超过200字
    assert not validator.validate_length(long_notes), "长备注应该验证失败"

    print("✓ 通过")

def test_content_relevance():
    """测试内容相关性"""
    print("\n测试3: 内容相关性...")

    checker = ContentRelevanceChecker()

    slide_data = {
        "title": "人工智能概述",
        "content": [
            "AI的定义和发展历程",
            "当前AI技术的主要应用领域",
            "AI对社会的影响和意义"
        ]
    }

    relevant_notes = "这个演讲备注讲述了人工智能的发展历程，从1950年代开始到现在的深度学习时代，AI技术正在改变我们的生活方式。"

    score = checker.calculate_relevance(slide_data, relevant_notes)
    assert score > 0.7, f"相关性得分应该大于0.7，实际: {score}"

    print("✓ 通过")

def test_empty_content_handling():
    """测试空内容处理"""
    print("\n测试4: 空内容处理...")

    generator = SpeakerNotesGenerator(use_fallback=True)

    empty_slide = {
        "slide_number": 1,
        "title": "空白幻灯片",
        "content": []
    }

    notes = generator.generate_notes(empty_slide)
    assert len(notes) >= 100, f"空内容备注长度不足: {len(notes)}"
    assert "空白" in notes or "visual" in notes.lower(), "空内容备注应该有特定说明"

    print("✓ 通过")

def test_special_characters():
    """测试特殊字符处理"""
    print("\n测试5: 特殊字符处理...")

    generator = SpeakerNotesGenerator(use_fallback=True)

    special_slide = {
        "slide_number": 1,
        "title": "数据分析 & 统计学 @ 2024",
        "content": [
            "数据量增长：100% ↑",
            "用户满意度：95% ✓",
            "成本效益：$1,000,000+ 节省"
        ]
    }

    notes = generator.generate_notes(special_slide)
    assert len(notes) >= 100, f"特殊字符备注长度不足: {len(notes)}"
    assert "数据" in notes or "统计" in notes, "特殊字符备注应该包含相关内容"

    print("✓ 通过")

def test_batch_generation():
    """测试批量生成"""
    print("\n测试6: 批量生成...")

    generator = SpeakerNotesGenerator(use_fallback=True)

    slides = [
        {"slide_number": 1, "title": "介绍", "content": ["欢迎"]},
        {"slide_number": 2, "title": "主题", "content": ["主要内容"]},
        {"slide_number": 3, "title": "总结", "content": ["谢谢"]}
    ]

    results = generator.batch_generate_notes(slides)

    assert len(results) == 3, f"应该生成3个备注，实际: {len(results)}"
    for result in results:
        assert "speaker_notes" in result
        assert len(result["speaker_notes"]) >= 100

    print("✓ 通过")

def test_english_generation():
    """测试英文生成"""
    print("\n测试7: 英文备注生成...")

    generator = SpeakerNotesGenerator(language="en", use_fallback=True)

    english_slide = {
        "slide_number": 1,
        "title": "Machine Learning",
        "content": [
            "Introduction to ML",
            "Deep Learning basics",
            "Applications"
        ]
    }

    notes = generator.generate_notes(english_slide)
    assert len(notes) >= 100, f"英文备注长度不足: {len(notes)}"
    # 检查是否是英文（不含中文字符）
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in notes)
    assert not has_chinese, "英文备注不应该包含中文"

    print("✓ 通过")

def test_pptx_integration():
    """测试PPT集成"""
    print("\n测试8: PPT集成...")

    service = PPTXIntegrationService()

    # 创建模拟的presentation对象
    mock_presentation = Mock()
    mock_slide = Mock()
    mock_slide.has_notes_slide = False
    mock_slide.notes_slide.notes_text_frame.text = ""
    mock_presentation.slides = [mock_slide]

    speaker_notes = "这是测试的演讲者备注内容。" * 5

    service.add_speaker_notes_to_slide(mock_presentation, 0, speaker_notes)

    # 验证设置了备注
    assert mock_slide.notes_slide.notes_text_frame.text == speaker_notes

    print("✓ 通过")

def main():
    """运行所有测试"""
    print("=" * 50)
    print("演讲者备注功能测试")
    print("=" * 50)

    tests = [
        test_basic_generation,
        test_length_validation,
        test_content_relevance,
        test_empty_content_handling,
        test_special_characters,
        test_batch_generation,
        test_english_generation,
        test_pptx_integration
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ 失败: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)

    if failed == 0:
        print("\n🎉 所有测试通过！演讲者备注功能实现完成。")
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，请检查实现。")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())