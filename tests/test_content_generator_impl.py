"""
内容生成测试 - 验证已实现的AI内容生成功能
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.content_generator import ContentGenerator, generate_outline, generate_slide_content, generate_and_save_content
from src.content_validator import (
    validate_content_format,
    validate_content_length,
    check_content_coherence,
    validate_content_quality
)


class TestContentGeneratorImplementation:
    """内容生成器实现测试"""

    @pytest.mark.unit
    def test_generate_outline_basic(self, mock_bedrock_client, sample_outline):
        """测试基本的大纲生成功能"""
        # Given
        topic = "人工智能的未来"
        page_count = 5

        # Mock Bedrock响应
        mock_response = {
            "body": Mock(),
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }
        mock_response["body"].read.return_value = json.dumps({
            "completion": json.dumps(sample_outline)
        }).encode()

        mock_bedrock_client.invoke_model.return_value = mock_response

        # When
        outline = generate_outline(topic, page_count, mock_bedrock_client)

        # Then
        assert outline["title"] == topic
        assert len(outline["slides"]) == page_count
        assert "metadata" in outline
        assert outline["metadata"]["total_slides"] == page_count

    @pytest.mark.unit
    def test_generate_outline_with_invalid_page_count(self, mock_bedrock_client):
        """测试无效页数的处理"""
        # Given
        topic = "测试主题"

        # When & Then - 页数太少
        with pytest.raises(ValueError) as exc_info:
            generate_outline(topic, 2, mock_bedrock_client)
        assert "页数必须在3-20之间" in str(exc_info.value)

        # When & Then - 页数太多
        with pytest.raises(ValueError) as exc_info:
            generate_outline(topic, 25, mock_bedrock_client)
        assert "页数必须在3-20之间" in str(exc_info.value)

    @pytest.mark.unit
    def test_generate_slide_content(self, mock_bedrock_client, sample_outline):
        """测试幻灯片内容生成"""
        # Given
        generator = ContentGenerator(bedrock_client=mock_bedrock_client)

        # Mock详细内容响应
        detailed_content = {
            "slide_number": 1,
            "title": "人工智能概述",
            "bullet_points": [
                "AI是计算机科学的一个分支",
                "从1950年代至今的发展历程",
                "AI正在改变我们的生活方式"
            ],
            "speaker_notes": "介绍AI的基本概念"
        }

        mock_response = {
            "body": Mock(),
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }
        mock_response["body"].read.return_value = json.dumps({
            "completion": json.dumps(detailed_content)
        }).encode()

        mock_bedrock_client.invoke_model.return_value = mock_response

        # When
        slides = generator.generate_slide_content(sample_outline)

        # Then
        assert len(slides) == len(sample_outline["slides"])
        for slide in slides:
            assert "title" in slide
            assert "bullet_points" in slide
            assert len(slide["bullet_points"]) == 3
            assert "speaker_notes" in slide

    @pytest.mark.unit
    def test_save_to_s3(self, mock_bedrock_client):
        """测试S3保存功能"""
        # Given
        mock_s3_client = Mock()
        generator = ContentGenerator(
            bedrock_client=mock_bedrock_client,
            s3_client=mock_s3_client
        )
        presentation_id = "test-123"
        content = {
            "presentation_id": presentation_id,
            "title": "测试标题",
            "slides": []
        }

        # When
        s3_key = generator.save_to_s3(presentation_id, content)

        # Then
        assert s3_key == f"presentations/{presentation_id}/content/slides.json"
        # 验证S3调用
        mock_s3_client.put_object.assert_called_once()

    @pytest.mark.unit
    def test_content_format_validation(self, sample_slide_content):
        """测试内容格式验证"""
        # Given
        valid_content = sample_slide_content
        invalid_content = {"invalid": "format"}

        # When & Then
        assert validate_content_format(valid_content) == True
        assert validate_content_format(invalid_content) == False

    @pytest.mark.unit
    def test_content_length_validation(self):
        """测试内容长度验证"""
        # Given
        valid_content = {
            "slides": [
                {
                    "title": "合适长度的标题",
                    "bullet_points": [
                        "这是一个长度合适的要点，包含足够的信息",
                        "另一个合适长度的要点，内容充实",
                        "第三个要点，长度也很合适"
                    ]
                }
            ]
        }

        too_short_content = {
            "slides": [
                {
                    "title": "标题",
                    "bullet_points": [
                        "太短",
                        "也太短",
                        "还是太短"
                    ]
                }
            ]
        }

        # When & Then
        assert validate_content_length(valid_content) == True
        assert validate_content_length(too_short_content) == False

    @pytest.mark.unit
    def test_content_coherence_check(self, sample_outline):
        """测试内容连贯性检查"""
        # Given
        coherent_content = {
            "slides": [
                {
                    "title": "人工智能概述",
                    "bullet_points": [
                        "AI技术的发展历程",
                        "机器学习的基本原理",
                        "深度学习的应用场景"
                    ]
                }
            ]
        }

        incoherent_content = {
            "slides": [
                {
                    "title": "烹饪技巧",
                    "bullet_points": [
                        "如何做红烧肉",
                        "炒菜的火候控制",
                        "调味料的使用方法"
                    ]
                }
            ]
        }

        # When & Then
        assert check_content_coherence(sample_outline, coherent_content) == True
        assert check_content_coherence(sample_outline, incoherent_content) == False

    @pytest.mark.unit
    def test_complete_generation_flow(self, mock_bedrock_client):
        """测试完整的生成流程"""
        # Given
        mock_s3_client = Mock()
        topic = "云计算技术"
        presentation_id = "test-complete-123"

        # Mock大纲响应
        outline_response = {
            "title": topic,
            "slides": [
                {"slide_number": 1, "title": "标题页", "content": ["介绍"]},
                {"slide_number": 2, "title": "内容页", "content": ["要点1", "要点2", "要点3"]},
                {"slide_number": 3, "title": "总结页", "content": ["总结"]}
            ],
            "metadata": {"total_slides": 3}
        }

        # Mock内容响应
        content_response = {
            "slide_number": 1,
            "title": "云计算概述",
            "bullet_points": [
                "云计算是通过互联网提供计算资源的模式",
                "包括IaaS、PaaS和SaaS三种服务模式",
                "具有弹性伸缩、按需付费等特点"
            ],
            "speaker_notes": "介绍云计算的基本概念"
        }

        # 设置mock响应
        mock_response = Mock()
        mock_response.get.return_value.read.return_value = json.dumps({
            "completion": json.dumps(outline_response)
        }).encode()

        # 使用side_effect来返回不同的响应
        responses = []
        # 第一次调用返回大纲
        response1 = {"body": Mock(), "ResponseMetadata": {"HTTPStatusCode": 200}}
        response1["body"].read.return_value = json.dumps({
            "completion": json.dumps(outline_response)
        }).encode()
        responses.append(response1)

        # 后续调用返回内容
        for _ in range(3):  # 3个幻灯片
            response = {"body": Mock(), "ResponseMetadata": {"HTTPStatusCode": 200}}
            response["body"].read.return_value = json.dumps({
                "completion": json.dumps(content_response)
            }).encode()
            responses.append(response)

        mock_bedrock_client.invoke_model.side_effect = responses

        # When
        result = generate_and_save_content(
            outline_response,
            presentation_id,
            mock_bedrock_client,
            mock_s3_client,
            "test-bucket"
        )

        # Then
        assert result["presentation_id"] == presentation_id
        assert "s3_key" in result
        assert "content" in result
        assert result["content"]["status"] == "completed"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])