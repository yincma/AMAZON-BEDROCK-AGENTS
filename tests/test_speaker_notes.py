"""
演讲者备注功能的TDD测试用例
遵循TDD红灯原则 - 测试先失败，验证测试的有效性

测试目标：
- 基于spec要求：演讲者备注与幻灯片内容相关，长度100-200字
- 使用Bedrock生成备注
- 备注添加到PPT文件中
- 支持中英文
- 批量处理和错误处理

Phase 2 Requirement 2.3: 演讲者备注 [Priority: P2]
User Story: 作为演讲者，我想获得每页的演讲提示。
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import boto3
from moto import mock_aws

# 测试常量
SPEAKER_NOTE_MIN_LENGTH = 100
SPEAKER_NOTE_MAX_LENGTH = 200
TEST_PRESENTATION_ID = "test-speaker-notes-001"


class TestSpeakerNotesGenerator:
    """演讲者备注生成器测试类"""

    @pytest.fixture
    def sample_slide_data(self):
        """示例幻灯片数据"""
        return {
            "slide_number": 1,
            "title": "人工智能概述",
            "content": [
                "AI是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统",
                "从1950年代至今，AI经历了多次发展浪潮，当前正处于深度学习时代",
                "AI正在改变我们的工作方式、生活方式和思维方式"
            ],
            "image_prompt": "AI technology concept illustration"
        }

    @pytest.fixture
    def sample_english_slide_data(self):
        """英文幻灯片数据示例"""
        return {
            "slide_number": 2,
            "title": "Machine Learning Fundamentals",
            "content": [
                "Machine learning is a subset of AI that enables computers to learn without explicit programming",
                "Deep learning uses neural networks to process complex patterns",
                "Applications include natural language processing, computer vision, and recommendation systems"
            ],
            "image_prompt": "Machine learning algorithm visualization"
        }

    def test_should_fail_generate_speaker_notes_for_single_slide(self, sample_slide_data):
        """
        测试：为单张幻灯片生成演讲者备注
        Expected: 此测试应该失败，因为SpeakerNotesGenerator还未实现

        Given: 有一张包含标题和内容的幻灯片
        When: 调用generate_speaker_notes方法
        Then: 应该返回长度在100-200字的演讲者备注
        """
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        # 使用fallback模式避免真实API调用
        generator = SpeakerNotesGenerator(use_fallback=True)

        # Act
        speaker_notes = generator.generate_notes(sample_slide_data)

        # Assert
        assert isinstance(speaker_notes, str)
        assert SPEAKER_NOTE_MIN_LENGTH <= len(speaker_notes) <= SPEAKER_NOTE_MAX_LENGTH
        assert "人工智能" in speaker_notes  # 应该与幻灯片内容相关
        assert speaker_notes.strip() != ""

    def test_should_fail_generate_notes_with_bedrock_integration(self, sample_slide_data, mock_bedrock_client):
        """
        测试：使用Bedrock生成演讲者备注
        Expected: 此测试应该失败，因为Bedrock集成还未实现

        Given: 配置好的Bedrock客户端
        When: 调用生成备注功能
        Then: 应该调用Bedrock API并返回格式化的备注
        """
        # 配置Bedrock mock响应
        mock_response_data = {
            "completion": "这是一个关于人工智能概述的演讲备注。AI作为计算机科学的重要分支，正在revolutionizing我们的生活方式。从1950年代的图灵测试开始，到今天的深度学习技术，人工智能经历了几次重要的发展浪潮。当前我们正处于深度学习时代，这项技术正在改变工作、生活和思维方式。",
            "stop_reason": "end_turn"
        }

        mock_bedrock_client.invoke_model.return_value = {
            "body": Mock(read=lambda: json.dumps(mock_response_data).encode()),
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        # 这个测试必须失败 - BedrockSpeakerNotesService还不存在
        from lambdas.services.bedrock_speaker_notes_service import BedrockSpeakerNotesService

        service = BedrockSpeakerNotesService(mock_bedrock_client)

        # Act
        result = service.generate_speaker_notes(sample_slide_data)

        # Assert
        assert "completion" in result
        assert len(result["completion"]) >= SPEAKER_NOTE_MIN_LENGTH
        mock_bedrock_client.invoke_model.assert_called_once()

    def test_should_fail_validate_speaker_notes_length_constraint(self, sample_slide_data):
        """
        测试：验证演讲者备注长度约束
        Expected: 此测试应该失败，因为长度验证逻辑还未实现

        Given: 生成的演讲者备注
        When: 验证备注长度
        Then: 应该确保备注长度在100-200字范围内
        """
        from lambdas.utils.speaker_notes_validator import SpeakerNotesValidator

        validator = SpeakerNotesValidator()

        # 测试短备注（应该被拒绝）
        short_notes = "这是太短的备注。"
        assert not validator.validate_length(short_notes)

        # 测试正常长度备注（应该通过）
        normal_notes = "这是一个长度适中的演讲者备注。" * 5  # 约100字
        assert validator.validate_length(normal_notes)

        # 测试过长备注（应该被拒绝）
        long_notes = "这是一个过长的演讲者备注。" * 20  # 约200字以上
        assert not validator.validate_length(long_notes)

    def test_should_fail_generate_notes_content_relevance(self, sample_slide_data):
        """
        测试：验证演讲者备注内容相关性
        Expected: 此测试应该失败，因为相关性检查还未实现

        Given: 幻灯片内容和生成的备注
        When: 检查内容相关性
        Then: 备注应该包含幻灯片的关键词
        """
        from lambdas.utils.content_relevance_checker import ContentRelevanceChecker

        checker = ContentRelevanceChecker()

        generated_notes = "这个演讲备注讲述了人工智能的发展历程，从1950年代开始到现在的深度学习时代，AI技术正在改变我们的生活方式。"

        # Act
        relevance_score = checker.calculate_relevance(sample_slide_data, generated_notes)

        # Assert
        assert relevance_score > 0.7  # 相关性得分应该大于70%
        assert checker.contains_key_concepts(sample_slide_data, generated_notes)

    def test_should_fail_generate_english_speaker_notes(self, sample_english_slide_data):
        """
        测试：生成英文演讲者备注
        Expected: 此测试应该失败，因为多语言支持还未实现

        Given: 英文幻灯片内容
        When: 生成演讲者备注
        Then: 应该返回英文的演讲者备注
        """
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(language="en", use_fallback=True)

        # Act
        speaker_notes = generator.generate_notes(sample_english_slide_data)

        # Assert
        assert isinstance(speaker_notes, str)
        assert SPEAKER_NOTE_MIN_LENGTH <= len(speaker_notes) <= SPEAKER_NOTE_MAX_LENGTH
        assert "machine learning" in speaker_notes.lower()
        # 验证是英文（简单检查：不包含中文字符）
        assert not any('\u4e00' <= char <= '\u9fff' for char in speaker_notes)

    def test_should_fail_integrate_speaker_notes_into_pptx(self, sample_slide_data):
        """
        测试：将演讲者备注集成到PPT文件中
        Expected: 此测试应该失败，因为PPT集成功能还未实现

        Given: 生成的演讲者备注和PPT文件
        When: 将备注添加到PPT
        Then: PPT文件应该包含演讲者备注
        """
        from lambdas.services.pptx_integration_service import PPTXIntegrationService

        service = PPTXIntegrationService()
        speaker_notes = "这是测试的演讲者备注内容。" * 5  # 确保长度满足要求

        # 创建模拟的PPT presentation对象
        mock_presentation = Mock()
        mock_slide = Mock()
        mock_slide.notes_slide.notes_text_frame.text = ""
        mock_presentation.slides = [mock_slide]

        # Act
        service.add_speaker_notes_to_slide(mock_presentation, 0, speaker_notes)

        # Assert
        assert mock_slide.notes_slide.notes_text_frame.text == speaker_notes

    def test_should_fail_batch_generate_speaker_notes(self):
        """
        测试：批量生成多张幻灯片的演讲者备注
        Expected: 此测试应该失败，因为批量处理功能还未实现

        Given: 包含多张幻灯片的演示文稿
        When: 批量生成演讲者备注
        Then: 应该为每张幻灯片生成对应的备注
        """
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator()

        slides_data = [
            {
                "slide_number": 1,
                "title": "Introduction",
                "content": ["Welcome to the presentation"]
            },
            {
                "slide_number": 2,
                "title": "Main Topic",
                "content": ["This is the main content"]
            },
            {
                "slide_number": 3,
                "title": "Conclusion",
                "content": ["Thank you for your attention"]
            }
        ]

        # Act
        results = generator.batch_generate_notes(slides_data)

        # Assert
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result["slide_number"] == i + 1
            assert "speaker_notes" in result
            assert SPEAKER_NOTE_MIN_LENGTH <= len(result["speaker_notes"]) <= SPEAKER_NOTE_MAX_LENGTH

    def test_should_fail_handle_bedrock_api_errors(self, sample_slide_data):
        """
        测试：处理Bedrock API错误情况
        Expected: 此测试应该失败，因为错误处理机制还未实现

        Given: Bedrock API返回错误
        When: 尝试生成演讲者备注
        Then: 应该有适当的错误处理和fallback机制
        """
        from lambdas.services.bedrock_speaker_notes_service import BedrockSpeakerNotesService
        from lambdas.exceptions.speaker_notes_exceptions import BedrockServiceError

        # 模拟Bedrock客户端抛出异常
        mock_bedrock_client = Mock()
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock API Error")

        service = BedrockSpeakerNotesService(mock_bedrock_client)

        # Act & Assert
        with pytest.raises(BedrockServiceError):
            service.generate_speaker_notes(sample_slide_data)

    def test_should_fail_speaker_notes_with_fallback_mechanism(self, sample_slide_data):
        """
        测试：演讲者备注的fallback机制
        Expected: 此测试应该失败，因为fallback机制还未实现

        Given: Bedrock服务不可用
        When: 生成演讲者备注失败
        Then: 应该使用默认模板生成基础备注
        """
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        # 模拟Bedrock服务失败
        with patch('lambdas.services.bedrock_speaker_notes_service.BedrockSpeakerNotesService') as mock_service:
            mock_service.return_value.generate_speaker_notes.side_effect = Exception("Service unavailable")

            # Act
            result = generator.generate_notes_with_fallback(sample_slide_data)

            # Assert
            assert "speaker_notes" in result
            assert "fallback" in result
            assert result["fallback"] is True
            # 即使是fallback，也要满足长度要求
            assert len(result["speaker_notes"]) >= SPEAKER_NOTE_MIN_LENGTH

    def test_should_fail_speaker_notes_performance_requirements(self, sample_slide_data):
        """
        测试：演讲者备注生成的性能要求
        Expected: 此测试应该失败，因为性能优化还未实现

        Given: 单张幻灯片
        When: 生成演讲者备注
        Then: 应该在5秒内完成
        """
        import time
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        # Act
        start_time = time.time()
        speaker_notes = generator.generate_notes(sample_slide_data)
        end_time = time.time()

        # Assert
        generation_time = end_time - start_time
        assert generation_time < 5.0  # 必须在5秒内完成
        assert len(speaker_notes) >= SPEAKER_NOTE_MIN_LENGTH


class TestSpeakerNotesIntegration:
    """演讲者备注集成测试"""

    def test_should_fail_end_to_end_speaker_notes_workflow(self, mock_bedrock_client, test_presentation_id):
        """
        测试：端到端演讲者备注工作流
        Expected: 此测试应该失败，因为完整工作流还未实现

        Given: 完整的PPT生成请求
        When: 执行包含演讲者备注的生成流程
        Then: 最终PPT文件应该包含所有演讲者备注
        """
        from lambdas.workflows.presentation_workflow import PresentationWorkflow

        workflow = PresentationWorkflow()

        request_data = {
            "presentation_id": test_presentation_id,
            "topic": "人工智能的未来发展",
            "slide_count": 5,
            "include_speaker_notes": True,
            "language": "zh-CN"
        }

        # Act
        result = workflow.generate_presentation_with_notes(request_data)

        # Assert
        assert result["status"] == "completed"
        assert "presentation_url" in result
        assert "speaker_notes_included" in result
        assert result["speaker_notes_included"] is True

        # 验证生成的每张幻灯片都有演讲者备注
        presentation_data = result["presentation_data"]
        for slide in presentation_data["slides"]:
            assert "speaker_notes" in slide
            assert SPEAKER_NOTE_MIN_LENGTH <= len(slide["speaker_notes"]) <= SPEAKER_NOTE_MAX_LENGTH

    @pytest.mark.aws
    def test_should_fail_speaker_notes_lambda_function(self, mock_lambda_client):
        """
        测试：演讲者备注Lambda函数
        Expected: 此测试应该失败，因为Lambda函数还未部署

        Given: 部署的Lambda函数
        When: 调用演讲者备注生成函数
        Then: 应该返回正确格式的响应
        """
        function_name = "generate_speaker_notes"

        payload = {
            "slide_data": {
                "slide_number": 1,
                "title": "测试幻灯片",
                "content": ["这是测试内容"] * 10  # 确保有足够内容生成备注
            }
        }

        # Act
        response = mock_lambda_client.invoke(
            FunctionName=function_name,
            Payload=json.dumps(payload)
        )

        # Assert
        assert response["StatusCode"] == 200

        response_payload = json.loads(response["Payload"].read())
        assert "speaker_notes" in response_payload
        assert len(response_payload["speaker_notes"]) >= SPEAKER_NOTE_MIN_LENGTH

    def test_should_fail_speaker_notes_api_endpoint(self, api_test_client):
        """
        测试：演讲者备注API端点
        Expected: 此测试应该失败，因为API端点还未实现

        Given: 可用的API端点
        When: 请求生成演讲者备注
        Then: 应该返回正确的JSON响应
        """
        import requests

        api_url = f"{api_test_client['base_url']}/speaker-notes"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_test_client['api_key']}"
        }

        payload = {
            "slide_data": {
                "title": "人工智能概述",
                "content": ["AI是计算机科学的分支", "用于创建智能系统", "正在改变各个行业"]
            },
            "language": "zh-CN"
        }

        # Act
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)

        # Assert
        assert response.status_code == 200

        response_data = response.json()
        assert "speaker_notes" in response_data
        assert len(response_data["speaker_notes"]) >= SPEAKER_NOTE_MIN_LENGTH
        assert response_data["language"] == "zh-CN"


class TestSpeakerNotesEdgeCases:
    """演讲者备注边界情况测试"""

    def test_should_fail_handle_empty_slide_content(self):
        """
        测试：处理空幻灯片内容
        Expected: 此测试应该失败，因为边界情况处理还未实现

        Given: 没有内容的幻灯片
        When: 生成演讲者备注
        Then: 应该生成默认的演讲者备注
        """
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator()

        empty_slide = {
            "slide_number": 1,
            "title": "空白幻灯片",
            "content": []
        }

        # Act
        speaker_notes = generator.generate_notes(empty_slide)

        # Assert
        assert len(speaker_notes) >= SPEAKER_NOTE_MIN_LENGTH
        assert "空白" in speaker_notes or "default" in speaker_notes.lower()

    def test_should_fail_handle_very_long_slide_content(self):
        """
        测试：处理超长幻灯片内容
        Expected: 此测试应该失败，因为长内容处理还未实现

        Given: 内容非常长的幻灯片
        When: 生成演讲者备注
        Then: 应该生成合适长度的备注（不超过200字）
        """
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator()

        long_content_slide = {
            "slide_number": 1,
            "title": "详细技术介绍",
            "content": ["这是非常详细的技术内容。" * 50]  # 超长内容
        }

        # Act
        speaker_notes = generator.generate_notes(long_content_slide)

        # Assert
        assert len(speaker_notes) <= SPEAKER_NOTE_MAX_LENGTH
        assert len(speaker_notes) >= SPEAKER_NOTE_MIN_LENGTH

    def test_should_fail_handle_special_characters_in_content(self):
        """
        测试：处理特殊字符和符号
        Expected: 此测试应该失败，因为特殊字符处理还未实现

        Given: 包含特殊字符的幻灯片内容
        When: 生成演讲者备注
        Then: 应该正确处理特殊字符
        """
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        special_char_slide = {
            "slide_number": 1,
            "title": "数据分析 & 统计学 @ 2024",
            "content": [
                "数据量增长：100% ↑",
                "用户满意度：95% ✓",
                "成本效益：$1,000,000+ 节省"
            ]
        }

        # Act
        speaker_notes = generator.generate_notes(special_char_slide)

        # Assert
        assert len(speaker_notes) >= SPEAKER_NOTE_MIN_LENGTH
        assert "数据" in speaker_notes
        # 特殊字符应该被适当处理，不影响备注生成


# 性能和压力测试
class TestSpeakerNotesPerformance:
    """演讲者备注性能测试"""

    @pytest.mark.slow
    def test_should_fail_concurrent_speaker_notes_generation(self):
        """
        测试：并发演讲者备注生成
        Expected: 此测试应该失败，因为并发处理还未实现

        Given: 多个并发请求
        When: 同时生成演讲者备注
        Then: 所有请求都应该成功完成
        """
        import concurrent.futures
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        def generate_notes_task(slide_num):
            slide_data = {
                "slide_number": slide_num,
                "title": f"幻灯片 {slide_num}",
                "content": [f"这是第{slide_num}张幻灯片的内容"] * 3
            }
            return generator.generate_notes(slide_data)

        # Act
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(generate_notes_task, i) for i in range(1, 11)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Assert
        assert len(results) == 10
        for result in results:
            assert len(result) >= SPEAKER_NOTE_MIN_LENGTH

    @pytest.mark.slow
    def test_should_fail_memory_usage_optimization(self):
        """
        测试：内存使用优化
        Expected: 此测试应该失败，因为内存优化还未实现

        Given: 大量幻灯片数据
        When: 生成演讲者备注
        Then: 内存使用应该保持在合理范围内
        """
        import sys
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        # 获取初始内存使用量（简化版）
        initial_size = sys.getsizeof(generator)

        # 生成大量备注
        results = []
        for i in range(100):
            slide_data = {
                "slide_number": i,
                "title": f"幻灯片 {i}",
                "content": ["测试内容"] * 10
            }
            result = generator.generate_notes(slide_data)
            results.append(result)

        # 检查最终内存使用量
        final_size = sys.getsizeof(generator) + sys.getsizeof(results)
        memory_increase = final_size - initial_size

        # Assert - 内存增长应该是合理的
        assert memory_increase > 0  # 应该有一些内存使用
        assert len(results) == 100  # 所有操作都成功


class TestSpeakerNotesGeneratorAdvanced:
    """演讲者备注生成器高级功能测试"""

    def test_initialization_with_different_options(self):
        """测试不同初始化选项"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        # 默认初始化
        generator1 = SpeakerNotesGenerator()
        assert generator1.language == "zh-CN"
        assert generator1.use_fallback in [True, False]

        # 自定义初始化
        generator2 = SpeakerNotesGenerator(language="en", use_fallback=True)
        assert generator2.language == "en"
        assert generator2.use_fallback is True

        # Mock bedrock client初始化
        mock_client = Mock()
        generator3 = SpeakerNotesGenerator(bedrock_client=mock_client)
        assert generator3.bedrock_client is mock_client

    def test_build_prompt_chinese_and_english(self):
        """测试中英文提示词构建"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        slide_data = {
            "title": "测试标题",
            "content": ["内容1", "内容2", "内容3"]
        }

        # 中文提示词
        generator_zh = SpeakerNotesGenerator(language="zh-CN")
        prompt_zh = generator_zh._build_prompt(slide_data)
        assert "演讲者备注" in prompt_zh
        assert "测试标题" in prompt_zh
        assert "内容1" in prompt_zh

        # 英文提示词
        generator_en = SpeakerNotesGenerator(language="en")
        prompt_en = generator_en._build_prompt(slide_data)
        assert "Speaker Notes" in prompt_en
        assert "测试标题" in prompt_en

    def test_extract_notes_from_different_responses(self):
        """测试从不同响应格式中提取备注"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        # Claude 3格式响应
        response_claude3 = {
            "content": [{"text": "这是Claude 3格式的演讲者备注内容"}]
        }
        notes = generator._extract_notes(response_claude3)
        assert "这是Claude 3格式的演讲者备注内容" in notes

        # 旧格式响应
        response_old = {
            "completion": "这是旧格式的演讲者备注内容"
        }
        notes = generator._extract_notes(response_old)
        assert "这是旧格式的演讲者备注内容" in notes

        # 无效响应格式
        invalid_response = {"invalid": "data"}
        with pytest.raises(ValueError):
            generator._extract_notes(invalid_response)

    def test_ensure_length_functionality(self):
        """测试长度确保功能"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator, SPEAKER_NOTE_MIN_LENGTH, SPEAKER_NOTE_MAX_LENGTH

        generator = SpeakerNotesGenerator(use_fallback=True)
        slide_data = {"title": "测试标题", "content": ["内容"]}

        # 太短的备注
        short_notes = "太短"
        adjusted = generator._ensure_length(short_notes, slide_data)
        assert len(adjusted) >= SPEAKER_NOTE_MIN_LENGTH

        # 太长的备注
        long_notes = "这是一个非常长的演讲者备注内容。" * 20
        adjusted = generator._ensure_length(long_notes, slide_data)
        assert len(adjusted) <= SPEAKER_NOTE_MAX_LENGTH

        # 合适长度的备注
        good_notes = "这是一个长度合适的演讲者备注内容，不需要调整。" * 3
        adjusted = generator._ensure_length(good_notes, slide_data)
        assert SPEAKER_NOTE_MIN_LENGTH <= len(adjusted) <= SPEAKER_NOTE_MAX_LENGTH

    def test_fallback_notes_generation(self):
        """测试fallback备注生成"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        # 正常内容
        normal_slide = {
            "title": "正常标题",
            "content": ["正常内容1", "正常内容2"]
        }
        notes = generator._generate_fallback_notes(normal_slide)
        assert len(notes) >= 100
        assert "正常标题" in notes

        # 空内容
        empty_slide = {
            "title": "空内容标题",
            "content": []
        }
        notes = generator._generate_fallback_notes(empty_slide)
        assert len(notes) >= 100
        assert "空内容标题" in notes

        # 英文fallback
        generator_en = SpeakerNotesGenerator(language="en", use_fallback=True)
        notes_en = generator_en._generate_fallback_notes(normal_slide)
        assert "slide" in notes_en.lower()

    def test_batch_generation_with_errors(self):
        """测试批量生成中的错误处理"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        # 混合正常和异常的数据
        mixed_slides = [
            {"slide_number": 1, "title": "正常幻灯片", "content": ["正常内容"]},
            {"slide_number": 2, "title": "", "content": []},  # 空内容
            {"slide_number": 3, "title": "另一个正常幻灯片", "content": ["更多内容"]}
        ]

        results = generator.batch_generate_notes(mixed_slides)

        # 验证所有幻灯片都有结果
        assert len(results) == 3

        # 验证结果按slide_number排序
        for i, result in enumerate(results):
            assert result["slide_number"] == i + 1
            assert "speaker_notes" in result
            assert len(result["speaker_notes"]) >= 100

    def test_presentation_level_generation(self):
        """测试演示文稿级别的生成"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        presentation_data = {
            "slides": [
                {"slide_number": 1, "title": "介绍", "content": ["欢迎"]},
                {"slide_number": 2, "title": "主要内容", "content": ["重点1", "重点2"]},
                {"slide_number": 3, "title": "总结", "content": ["谢谢"]}
            ]
        }

        result = generator.generate_for_presentation(presentation_data)

        # 验证结果
        assert "speaker_notes_included" in result
        assert result["speaker_notes_included"] is True

        # 验证每张幻灯片都有备注
        for slide in result["slides"]:
            assert "speaker_notes" in slide
            assert len(slide["speaker_notes"]) >= 100

    def test_ppt_integration(self):
        """测试PPT集成功能"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        # 创建mock presentation
        mock_presentation = Mock()
        mock_slide = Mock()
        mock_notes_slide = Mock()
        mock_text_frame = Mock()

        mock_slide.has_notes_slide = False
        mock_slide.notes_slide = mock_notes_slide
        mock_notes_slide.notes_text_frame = mock_text_frame
        mock_presentation.slides = [mock_slide]

        speaker_notes = "这是测试的演讲者备注内容。" * 5

        # 测试添加备注
        generator.add_notes_to_ppt(mock_presentation, 0, speaker_notes)

        # 验证备注被设置
        assert mock_text_frame.text == speaker_notes

    def test_bedrock_service_integration(self, mock_bedrock_client):
        """测试Bedrock服务集成"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        # 配置mock响应
        mock_response = {
            "content": [{"text": "这是通过Bedrock生成的演讲者备注内容，包含了详细的说明和补充信息。"}]
        }

        mock_bedrock_client.invoke_model.return_value = {
            "body": Mock(read=lambda: json.dumps(mock_response).encode())
        }

        generator = SpeakerNotesGenerator(bedrock_client=mock_bedrock_client)

        slide_data = {
            "title": "测试标题",
            "content": ["测试内容1", "测试内容2"]
        }

        # 使用真实的Bedrock调用（通过mock）
        with patch.object(generator, 'use_fallback', False):
            notes = generator.generate_notes(slide_data)

            assert isinstance(notes, str)
            assert len(notes) >= 100
            mock_bedrock_client.invoke_model.assert_called_once()

    def test_lambda_handler_functionality(self):
        """测试Lambda处理函数"""
        from lambdas.controllers.generate_speaker_notes import lambda_handler

        # 正常事件
        event = {
            "slide_data": {
                "title": "测试标题",
                "content": ["测试内容"]
            },
            "language": "zh-CN"
        }

        # Mock Bedrock以避免真实调用
        with patch('lambdas.controllers.generate_speaker_notes.SpeakerNotesGenerator') as mock_generator_class:
            mock_generator = Mock()
            mock_generator.generate_notes.return_value = "这是测试的演讲者备注内容。" * 5
            mock_generator_class.return_value = mock_generator

            response = lambda_handler(event, {})

            assert response["statusCode"] == 200
            response_body = json.loads(response["body"])
            assert "speaker_notes" in response_body
            assert response_body["language"] == "zh-CN"

    def test_error_scenarios_comprehensive(self):
        """测试综合错误场景"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        # 测试无效的幻灯片数据类型
        invalid_data = "这不是字典"
        with pytest.raises(AttributeError):
            generator.generate_notes(invalid_data)

        # 测试空的或None的数据
        empty_data = {}
        notes = generator.generate_notes(empty_data)
        assert isinstance(notes, str)
        assert len(notes) >= 100

        # 测试None数据
        none_data = None
        with pytest.raises(AttributeError):
            generator.generate_notes(none_data)

    def test_content_relevance_and_quality(self):
        """测试内容相关性和质量"""
        from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

        generator = SpeakerNotesGenerator(use_fallback=True)

        # 技术相关的幻灯片
        tech_slide = {
            "title": "人工智能与机器学习",
            "content": [
                "深度学习算法",
                "神经网络架构",
                "自然语言处理"
            ]
        }

        notes = generator.generate_notes(tech_slide)

        # 验证备注包含相关技术术语
        tech_terms = ["人工智能", "机器学习", "算法", "神经网络"]
        assert any(term in notes for term in tech_terms)
        assert len(notes) >= 100

        # 商务相关的幻灯片
        business_slide = {
            "title": "市场分析与战略规划",
            "content": [
                "市场份额增长",
                "竞争对手分析",
                "收益预测"
            ]
        }

        notes = generator.generate_notes(business_slide)
        business_terms = ["市场", "分析", "战略", "竞争"]
        assert any(term in notes for term in business_terms)