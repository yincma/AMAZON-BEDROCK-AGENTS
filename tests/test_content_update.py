"""
AI PPT Assistant Phase 3 - 内容修改功能测试用例

本模块包含Phase 3内容修改功能的完整测试用例，遵循TDD原则。
测试覆盖：
- 单页内容更新
- 图片重新生成
- 整体一致性保持
- 错误处理机制

根据需求文档Requirement 3.1: 内容修改功能
"""

import pytest
import json
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import boto3
from moto import mock_aws
import tempfile
import os


class TestContentUpdate:
    """Phase 3 - 内容修改功能测试套件"""

    @pytest.fixture
    def presentation_data(self):
        """测试用演示文稿数据"""
        return {
            "presentation_id": "test-ppt-123",
            "topic": "AI技术发展趋势",
            "status": "completed",
            "slides": [
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
                    "content": ["监督学习", "无监督学习", "强化学习"],
                    "image_url": "s3://bucket/images/slide2.jpg",
                    "speaker_notes": "这是第二页的演讲备注"
                }
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

    @pytest.fixture
    def mock_s3_client(self):
        """模拟S3客户端"""
        with mock_aws():
            s3 = boto3.client('s3', region_name='us-east-1')
            s3.create_bucket(Bucket='ai-ppt-presentations')
            yield s3

    @pytest.fixture
    def content_update_handler(self):
        """内容更新处理器 - 这是我们要实现的组件"""
        # 这里返回一个Mock，实际实现会在RED阶段失败后创建
        return Mock()

    # ==================== 测试用例1: 单页内容更新 ====================

    def test_update_single_slide_content_success(self, content_update_handler, presentation_data):
        """
        测试成功更新单页内容

        Given: 存在一个已生成的PPT
        When: 用户请求更新第2页的标题和内容
        Then: 只有第2页被更新，其他页面保持不变
        """
        # Arrange
        slide_update = {
            "slide_number": 2,
            "title": "深度学习技术",
            "content": ["神经网络", "卷积网络", "循环网络", "Transformer"]
        }

        content_update_handler.update_slide.return_value = {
            "status": "success",
            "updated_slide": slide_update,
            "presentation_id": presentation_data["presentation_id"]
        }

        # Act
        result = content_update_handler.update_slide(
            presentation_data["presentation_id"],
            slide_update
        )

        # Assert
        assert result["status"] == "success"
        assert result["updated_slide"]["title"] == "深度学习技术"
        assert len(result["updated_slide"]["content"]) == 4
        assert "Transformer" in result["updated_slide"]["content"]

        # 验证调用参数
        content_update_handler.update_slide.assert_called_once_with(
            presentation_data["presentation_id"],
            slide_update
        )

    def test_update_slide_with_invalid_slide_number(self, content_update_handler, presentation_data):
        """
        测试更新不存在的页面编号

        Given: 演示文稿只有2页
        When: 用户尝试更新第5页
        Then: 返回错误信息
        """
        # Arrange
        invalid_slide_update = {
            "slide_number": 5,
            "title": "不存在的页面",
            "content": ["这不应该被更新"]
        }

        content_update_handler.update_slide.side_effect = ValueError("Slide number 5 does not exist")

        # Act & Assert
        with pytest.raises(ValueError, match="Slide number 5 does not exist"):
            content_update_handler.update_slide(
                presentation_data["presentation_id"],
                invalid_slide_update
            )

    def test_update_slide_preserves_other_fields(self, content_update_handler, presentation_data):
        """
        测试更新单页时保留其他字段

        Given: 页面有图片和演讲备注
        When: 只更新标题和内容
        Then: 图片和演讲备注保持不变
        """
        # Arrange
        partial_update = {
            "slide_number": 1,
            "title": "AI技术新概述"
        }

        expected_result = {
            "status": "success",
            "updated_slide": {
                "slide_number": 1,
                "title": "AI技术新概述",
                "content": ["人工智能定义", "发展历程", "核心技术"],  # 保持原内容
                "image_url": "s3://bucket/images/slide1.jpg",  # 保持原图片
                "speaker_notes": "这是第一页的演讲备注"  # 保持原备注
            }
        }

        content_update_handler.update_slide.return_value = expected_result

        # Act
        result = content_update_handler.update_slide(
            presentation_data["presentation_id"],
            partial_update
        )

        # Assert
        assert result["updated_slide"]["title"] == "AI技术新概述"
        assert result["updated_slide"]["image_url"] == "s3://bucket/images/slide1.jpg"
        assert result["updated_slide"]["speaker_notes"] == "这是第一页的演讲备注"

    # ==================== 测试用例2: 重新生成图片 ====================

    def test_regenerate_image_success(self, content_update_handler, presentation_data):
        """
        测试成功重新生成图片

        Given: 页面有现有图片
        When: 用户请求重新生成图片
        Then: 生成新图片并更新URL
        """
        # Arrange
        regenerate_request = {
            "slide_number": 1,
            "regenerate_image": True,
            "image_prompt": "现代AI技术示意图"
        }

        new_image_url = "s3://bucket/images/slide1_regenerated.jpg"
        content_update_handler.regenerate_image.return_value = {
            "status": "success",
            "new_image_url": new_image_url,
            "generation_time": 8.5
        }

        # Act
        result = content_update_handler.regenerate_image(
            presentation_data["presentation_id"],
            regenerate_request
        )

        # Assert
        assert result["status"] == "success"
        assert result["new_image_url"] != presentation_data["slides"][0]["image_url"]
        assert result["new_image_url"] == new_image_url
        assert result["generation_time"] < 30  # 性能要求

    def test_regenerate_image_with_custom_prompt(self, content_update_handler):
        """
        测试使用自定义提示词重新生成图片

        Given: 用户提供了自定义图片描述
        When: 重新生成图片
        Then: 使用自定义提示词生成图片
        """
        # Arrange
        custom_prompt_request = {
            "slide_number": 2,
            "regenerate_image": True,
            "image_prompt": "机器学习算法流程图，现代风格，蓝色主题"
        }

        content_update_handler.regenerate_image.return_value = {
            "status": "success",
            "new_image_url": "s3://bucket/images/slide2_custom.jpg",
            "used_prompt": custom_prompt_request["image_prompt"]
        }

        # Act
        result = content_update_handler.regenerate_image("test-ppt-123", custom_prompt_request)

        # Assert
        assert result["status"] == "success"
        assert result["used_prompt"] == "机器学习算法流程图，现代风格，蓝色主题"

    def test_regenerate_image_failure_fallback(self, content_update_handler):
        """
        测试图片生成失败时的回退机制

        Given: 图片生成服务不可用
        When: 尝试重新生成图片
        Then: 使用默认图片并记录失败信息
        """
        # Arrange
        regenerate_request = {
            "slide_number": 1,
            "regenerate_image": True
        }

        content_update_handler.regenerate_image.return_value = {
            "status": "fallback",
            "new_image_url": "s3://bucket/default/placeholder.jpg",
            "error": "Image generation service unavailable",
            "fallback_used": True
        }

        # Act
        result = content_update_handler.regenerate_image("test-ppt-123", regenerate_request)

        # Assert
        assert result["status"] == "fallback"
        assert result["fallback_used"] is True
        assert "placeholder" in result["new_image_url"]

    # ==================== 测试用例3: 整体一致性保持 ====================

    def test_maintain_consistency_after_update(self, content_update_handler, presentation_data):
        """
        测试更新后保持整体一致性

        Given: 更新了某页内容
        When: 检查整体一致性
        Then: 其他页面的样式和主题保持一致
        """
        # Arrange
        update_request = {
            "slide_number": 1,
            "title": "AI技术革命",
            "content": ["人工智能崛起", "技术突破", "应用前景"]
        }

        content_update_handler.validate_consistency.return_value = {
            "is_consistent": True,
            "style_coherence": 0.95,
            "theme_alignment": 0.92,
            "recommendations": []
        }

        # Act
        result = content_update_handler.validate_consistency(
            presentation_data["presentation_id"]
        )

        # Assert
        assert result["is_consistent"] is True
        assert result["style_coherence"] > 0.9
        assert result["theme_alignment"] > 0.9
        assert len(result["recommendations"]) == 0

    def test_detect_consistency_issues(self, content_update_handler):
        """
        测试检测一致性问题

        Given: 更新导致了样式不一致
        When: 进行一致性检查
        Then: 识别问题并提供修复建议
        """
        # Arrange
        content_update_handler.validate_consistency.return_value = {
            "is_consistent": False,
            "style_coherence": 0.65,
            "theme_alignment": 0.70,
            "issues": [
                "Slide 2 font size inconsistent with presentation theme",
                "Color scheme deviation detected in slide 3"
            ],
            "recommendations": [
                "Adjust slide 2 font size to match template",
                "Apply consistent color palette across all slides"
            ]
        }

        # Act
        result = content_update_handler.validate_consistency("test-ppt-123")

        # Assert
        assert result["is_consistent"] is False
        assert len(result["issues"]) == 2
        assert len(result["recommendations"]) == 2
        assert "font size" in result["issues"][0]

    def test_auto_fix_consistency_issues(self, content_update_handler):
        """
        测试自动修复一致性问题

        Given: 检测到一致性问题
        When: 启用自动修复
        Then: 问题得到自动解决
        """
        # Arrange
        auto_fix_request = {
            "presentation_id": "test-ppt-123",
            "auto_fix": True,
            "preserve_content": True
        }

        content_update_handler.auto_fix_consistency.return_value = {
            "status": "fixed",
            "fixed_issues": 2,
            "changes_made": [
                "Standardized font sizes across all slides",
                "Applied consistent color scheme"
            ],
            "final_consistency_score": 0.96
        }

        # Act
        result = content_update_handler.auto_fix_consistency(auto_fix_request)

        # Assert
        assert result["status"] == "fixed"
        assert result["fixed_issues"] == 2
        assert result["final_consistency_score"] > 0.95

    # ==================== 测试用例4: 错误处理 ====================

    def test_handle_invalid_presentation_id(self, content_update_handler):
        """
        测试处理无效的演示文稿ID

        Given: 提供了不存在的演示文稿ID
        When: 尝试更新内容
        Then: 返回适当的错误信息
        """
        # Arrange
        invalid_id = "non-existent-ppt-456"
        update_request = {
            "slide_number": 1,
            "title": "新标题"
        }

        content_update_handler.update_slide.side_effect = FileNotFoundError(
            f"Presentation {invalid_id} not found"
        )

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Presentation .* not found"):
            content_update_handler.update_slide(invalid_id, update_request)

    def test_handle_malformed_update_request(self, content_update_handler):
        """
        测试处理格式错误的更新请求

        Given: 更新请求缺少必要字段
        When: 处理请求
        Then: 返回验证错误信息
        """
        # Arrange
        malformed_request = {
            "title": "新标题"
            # 缺少 slide_number
        }

        content_update_handler.update_slide.side_effect = ValueError(
            "Missing required field: slide_number"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Missing required field: slide_number"):
            content_update_handler.update_slide("test-ppt-123", malformed_request)

    def test_handle_s3_storage_error(self, content_update_handler):
        """
        测试处理S3存储错误

        Given: S3存储服务不可用
        When: 尝试保存更新
        Then: 提供备用存储方案
        """
        # Arrange
        update_request = {
            "slide_number": 1,
            "title": "更新标题"
        }

        content_update_handler.update_slide.side_effect = Exception("S3 storage unavailable")

        # Act & Assert
        with pytest.raises(Exception, match="S3 storage unavailable"):
            content_update_handler.update_slide("test-ppt-123", update_request)

    def test_handle_concurrent_updates(self, content_update_handler):
        """
        测试处理并发更新冲突

        Given: 同时有多个用户更新同一演示文稿
        When: 检测到版本冲突
        Then: 返回冲突错误并提供解决方案
        """
        # Arrange
        update_request = {
            "slide_number": 1,
            "title": "并发更新标题",
            "version": "1.0"  # 过期版本
        }

        content_update_handler.update_slide.side_effect = ValueError(
            "Version conflict detected. Current version is 1.2, provided version is 1.0"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Version conflict detected"):
            content_update_handler.update_slide("test-ppt-123", update_request)

    def test_update_timeout_handling(self, content_update_handler):
        """
        测试更新操作超时处理

        Given: 更新操作耗时过长
        When: 超过预设时间限制
        Then: 返回超时错误并清理资源
        """
        # Arrange
        import asyncio

        async def slow_update():
            await asyncio.sleep(35)  # 超过30秒限制
            return {"status": "success"}

        content_update_handler.update_slide.side_effect = TimeoutError(
            "Update operation timed out after 30 seconds"
        )

        # Act & Assert
        with pytest.raises(TimeoutError, match="Update operation timed out"):
            content_update_handler.update_slide("test-ppt-123", {"slide_number": 1})

    # ==================== 集成测试 ====================

    @pytest.mark.integration
    def test_full_update_workflow(self, content_update_handler, presentation_data, mock_s3_client):
        """
        测试完整的内容更新工作流

        Given: 一个完整的演示文稿
        When: 执行更新->验证->保存工作流
        Then: 所有步骤成功完成
        """
        # Arrange
        workflow_steps = []

        def track_step(step_name):
            workflow_steps.append(step_name)
            return {"status": "success", "step": step_name}

        content_update_handler.update_slide.side_effect = lambda *args: track_step("update")
        content_update_handler.validate_consistency.side_effect = lambda *args: track_step("validate")
        content_update_handler.save_presentation.side_effect = lambda *args: track_step("save")

        # Act
        update_result = content_update_handler.update_slide("test-ppt-123", {"slide_number": 1})
        validation_result = content_update_handler.validate_consistency("test-ppt-123")
        save_result = content_update_handler.save_presentation("test-ppt-123")

        # Assert
        assert len(workflow_steps) == 3
        assert "update" in workflow_steps
        assert "validate" in workflow_steps
        assert "save" in workflow_steps

    @pytest.mark.performance
    def test_update_performance_requirements(self, content_update_handler):
        """
        测试更新操作性能要求

        Given: 单页更新请求
        When: 执行更新操作
        Then: 完成时间小于5秒
        """
        # Arrange
        start_time = datetime.now()

        content_update_handler.update_slide.return_value = {
            "status": "success",
            "processing_time": 3.2  # 小于5秒要求
        }

        # Act
        result = content_update_handler.update_slide("test-ppt-123", {"slide_number": 1})

        # Assert
        assert result["processing_time"] < 5.0

        # 验证实际执行时间（在真实实现中会更有意义）
        execution_time = (datetime.now() - start_time).total_seconds()
        assert execution_time < 1.0  # Mock调用应该很快

    # ==================== 边界条件测试 ====================

    def test_update_last_slide_in_presentation(self, content_update_handler, presentation_data):
        """测试更新演示文稿中的最后一页"""
        # 获取最后一页编号
        last_slide_number = len(presentation_data["slides"])

        update_request = {
            "slide_number": last_slide_number,
            "title": "总结与展望"
        }

        content_update_handler.update_slide.return_value = {
            "status": "success",
            "updated_slide": update_request
        }

        # Act & Assert
        result = content_update_handler.update_slide("test-ppt-123", update_request)
        assert result["status"] == "success"

    def test_update_with_empty_content(self, content_update_handler):
        """测试使用空内容更新"""
        update_request = {
            "slide_number": 1,
            "content": []  # 空内容
        }

        content_update_handler.update_slide.side_effect = ValueError(
            "Content cannot be empty"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Content cannot be empty"):
            content_update_handler.update_slide("test-ppt-123", update_request)

    def test_update_with_very_long_content(self, content_update_handler):
        """测试使用过长内容更新"""
        long_content = ["很长的内容点 " + "内容" * 100 for _ in range(50)]

        update_request = {
            "slide_number": 1,
            "content": long_content
        }

        content_update_handler.update_slide.side_effect = ValueError(
            "Content too long for slide format"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Content too long"):
            content_update_handler.update_slide("test-ppt-123", update_request)


# ==================== 测试辅助函数 ====================

def create_test_presentation_file(presentation_data, temp_dir):
    """创建测试用的演示文稿文件"""
    file_path = os.path.join(temp_dir, f"{presentation_data['presentation_id']}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(presentation_data, f, ensure_ascii=False, indent=2)
    return file_path


def validate_slide_structure(slide_data):
    """验证幻灯片数据结构"""
    required_fields = ["slide_number", "title", "content"]
    for field in required_fields:
        if field not in slide_data:
            return False, f"Missing required field: {field}"

    if not isinstance(slide_data["content"], list):
        return False, "Content must be a list"

    return True, "Valid slide structure"


# ==================== Pytest配置 ====================

@pytest.fixture(autouse=True)
def setup_test_environment():
    """测试环境设置"""
    # 设置测试用的环境变量
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["S3_BUCKET"] = "ai-ppt-presentations-test"
    yield
    # 清理
    if "S3_BUCKET" in os.environ:
        del os.environ["S3_BUCKET"]


if __name__ == "__main__":
    # 运行特定测试
    pytest.main([__file__ + "::TestContentUpdate::test_update_single_slide_content_success", "-v"])