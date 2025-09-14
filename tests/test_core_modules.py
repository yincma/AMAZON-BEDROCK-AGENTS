"""
核心模块单元测试 - 提高代码覆盖率
专注于实际代码执行而非Mock
"""

import pytest
import json
import uuid
import boto3
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

# Import core modules
from src.content_generator import ContentGenerator
from src.ppt_compiler import PPTCompiler
from src.common.response_builder import ResponseBuilder
from src.common.s3_service import S3Service
from src.validators import RequestValidator
from src.exceptions import (
    ValidationError,
    PPTAssistantError,
    BedrockAPIError,
    S3OperationError
)
from src.constants import Config
from src.utils import retry_with_backoff


class TestContentGeneratorUnit:
    """内容生成器单元测试"""

    def test_content_generator_initialization(self):
        """测试内容生成器初始化"""
        generator = ContentGenerator()
        assert generator is not None
        assert hasattr(generator, 'model_id')
        assert hasattr(generator, 'bedrock_client')

    def test_content_generator_topic_validation(self):
        """测试主题验证"""
        generator = ContentGenerator()

        # 测试有效主题
        valid_topics = [
            "人工智能技术发展趋势",
            "区块链在金融领域的应用",
            "云计算架构设计原则"
        ]

        for topic in valid_topics:
            # 应该不抛出异常
            generator._validate_topic(topic)

    def test_content_generator_invalid_topic(self):
        """测试无效主题验证"""
        generator = ContentGenerator()

        # 测试无效主题
        invalid_topics = [
            "",  # 空字符串
            "a",  # 太短
            "ab",  # 太短
            None,  # None值
        ]

        for topic in invalid_topics:
            with pytest.raises(ValidationError):
                generator._validate_topic(topic)

    def test_content_generator_slides_count_validation(self):
        """测试幻灯片数量验证"""
        generator = ContentGenerator()

        # 测试有效数量
        valid_counts = [3, 5, 8, 10, 15, 20]
        for count in valid_counts:
            generator._validate_slides_count(count)

        # 测试无效数量
        invalid_counts = [0, 1, 2, 21, 100, -1]
        for count in invalid_counts:
            with pytest.raises(ValidationError):
                generator._validate_slides_count(count)


class TestPPTCompilerUnit:
    """PPT编译器单元测试"""

    def test_ppt_compiler_initialization(self):
        """测试PPT编译器初始化"""
        compiler = PPTCompiler()
        assert compiler is not None
        assert hasattr(compiler, 'template_styles')

    def test_ppt_compiler_validate_outline_structure(self):
        """测试大纲结构验证"""
        compiler = PPTCompiler()

        # 有效大纲结构
        valid_outline = {
            "title": "测试演示文稿",
            "slides": [
                {
                    "slide_number": 1,
                    "title": "标题页",
                    "content": ["主题：测试"]
                },
                {
                    "slide_number": 2,
                    "title": "内容页",
                    "content": ["要点1", "要点2"]
                }
            ],
            "metadata": {
                "total_slides": 2,
                "created_at": "2025-01-01T00:00:00"
            }
        }

        # 应该不抛出异常
        compiler._validate_outline_structure(valid_outline)

    def test_ppt_compiler_invalid_outline_structure(self):
        """测试无效大纲结构验证"""
        compiler = PPTCompiler()

        # 无效大纲结构
        invalid_outlines = [
            {},  # 空字典
            {"title": "只有标题"},  # 缺少slides
            {"slides": []},  # 缺少title
            {
                "title": "测试",
                "slides": [{"invalid": "structure"}]  # 无效slides结构
            }
        ]

        for outline in invalid_outlines:
            with pytest.raises(ValidationError):
                compiler._validate_outline_structure(outline)


class TestResponseBuilderUnit:
    """响应构建器单元测试"""

    def test_success_response_format(self):
        """测试成功响应格式"""
        data = {"test": "data", "number": 123}
        response = ResponseBuilder.success_response(200, data)

        assert response["statusCode"] == 200
        assert "headers" in response
        assert "body" in response
        assert "Access-Control-Allow-Origin" in response["headers"]

        body_data = json.loads(response["body"])
        assert body_data == data

    def test_error_response_format(self):
        """测试错误响应格式"""
        message = "测试错误消息"
        error_code = "TEST_ERROR"
        response = ResponseBuilder.error_response(400, message, error_code)

        assert response["statusCode"] == 400
        assert "headers" in response
        assert "body" in response

        body_data = json.loads(response["body"])
        assert "error" in body_data
        assert body_data["error"]["message"] == message
        assert body_data["error"]["code"] == error_code

    def test_validation_error_response(self):
        """测试验证错误响应"""
        message = "无效的输入"
        field = "topic"
        response = ResponseBuilder.validation_error_response(message, field)

        assert response["statusCode"] == 400
        body_data = json.loads(response["body"])
        assert body_data["error"]["field"] == field

    def test_internal_error_response(self):
        """测试内部错误响应"""
        response = ResponseBuilder.internal_error_response()

        assert response["statusCode"] == 500
        body_data = json.loads(response["body"])
        assert "error" in body_data


class TestS3ServiceUnit:
    """S3服务单元测试"""

    @patch('boto3.client')
    def test_s3_service_initialization(self, mock_boto3):
        """测试S3服务初始化"""
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client

        bucket_name = "test-bucket"
        s3_service = S3Service(bucket_name)

        assert s3_service.bucket_name == bucket_name
        assert s3_service.s3_client == mock_s3_client

    @patch('boto3.client')
    def test_s3_service_key_generation(self, mock_boto3):
        """测试S3键生成"""
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client

        s3_service = S3Service("test-bucket")

        # 测试PPT文件键生成
        presentation_id = "test-123"
        ppt_key = s3_service._generate_ppt_key(presentation_id)
        assert ppt_key.startswith(Config.S3.PPT_PREFIX)
        assert presentation_id in ppt_key
        assert ppt_key.endswith('.pptx')

        # 测试状态文件键生成
        status_key = s3_service._generate_status_key(presentation_id)
        assert status_key.startswith(Config.S3.STATUS_PREFIX)
        assert presentation_id in status_key
        assert status_key.endswith('.json')

    @patch('boto3.client')
    def test_s3_service_validate_bucket_name(self, mock_boto3):
        """测试存储桶名称验证"""
        mock_s3_client = Mock()
        mock_boto3.return_value = mock_s3_client

        s3_service = S3Service("test-bucket")

        # 有效的存储桶名称
        valid_names = ["test-bucket", "my-bucket-123", "valid.bucket.name"]
        for name in valid_names:
            s3_service._validate_bucket_name(name)  # 应该不抛出异常

        # 无效的存储桶名称
        invalid_names = ["", "UPPERCASE", "invalid_underscore", "too-long-" + "a" * 50]
        for name in invalid_names:
            with pytest.raises(S3OperationError):
                s3_service._validate_bucket_name(name)


class TestValidatorsUnit:
    """验证器单元测试"""

    def test_validate_generate_request(self):
        """测试生成请求验证"""
        # 有效请求
        valid_request = {
            "topic": "人工智能的未来发展",
            "page_count": 5
        }
        is_valid, error_msg = RequestValidator.validate_generate_request(valid_request)
        assert is_valid is True
        assert error_msg is None

        # 无效请求 - 缺少topic
        invalid_request = {"page_count": 5}
        is_valid, error_msg = RequestValidator.validate_generate_request(invalid_request)
        assert is_valid is False
        assert "Topic is required" in error_msg

        # 无效请求 - topic太短
        invalid_request = {"topic": "ab"}
        is_valid, error_msg = RequestValidator.validate_generate_request(invalid_request)
        assert is_valid is False
        assert "at least 3 characters" in error_msg

    def test_validate_status_request(self):
        """测试状态请求验证"""
        # 有效的presentation_id
        valid_id = str(uuid.uuid4())
        is_valid, error_msg = RequestValidator.validate_status_request(valid_id)
        assert is_valid is True
        assert error_msg is None

        # 无效的presentation_id
        is_valid, error_msg = RequestValidator.validate_status_request("")
        assert is_valid is False
        assert error_msg is not None

    def test_sanitize_topic(self):
        """测试主题清理函数"""
        # 正常输入
        clean_input = "正常的用户输入"
        sanitized = RequestValidator.sanitize_topic(clean_input)
        assert sanitized == clean_input.strip()

        # 需要清理的输入
        malicious_input = "<script>alert('xss')</script>人工智能"
        sanitized = RequestValidator.sanitize_topic(malicious_input)
        assert "<script>" not in sanitized
        assert "人工智能" in sanitized


class TestExceptionsUnit:
    """异常类单元测试"""

    def test_validation_error(self):
        """测试验证错误异常"""
        message = "无效的输入值"
        field = "topic"

        error = ValidationError(message, field)
        assert str(error) == message
        assert error.message == message
        assert error.field == field

    def test_bedrock_api_error(self):
        """测试Bedrock API错误异常"""
        message = "API调用失败"

        error = BedrockAPIError(message)
        assert str(error) == message

    def test_s3_operation_error(self):
        """测试S3操作错误异常"""
        message = "S3操作失败"

        error = S3OperationError(message)
        assert str(error) == message

    def test_ppt_assistant_error(self):
        """测试PPT助手通用错误异常"""
        message = "系统错误"

        error = PPTAssistantError(message)
        assert str(error) == message


class TestUtilsUnit:
    """工具函数单元测试"""

    def test_retry_with_backoff_success(self):
        """测试重试装饰器 - 成功情况"""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        def success_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_with_backoff_eventual_success(self):
        """测试重试装饰器 - 最终成功"""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        def eventual_success_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("临时错误")
            return "最终成功"

        result = eventual_success_function()
        assert result == "最终成功"
        assert call_count == 3

    def test_retry_with_backoff_failure(self):
        """测试重试装饰器 - 失败情况"""
        call_count = 0

        @retry_with_backoff(max_retries=2)
        def failure_function():
            nonlocal call_count
            call_count += 1
            raise Exception("持续错误")

        with pytest.raises(Exception, match="持续错误"):
            failure_function()

        assert call_count == 2  # 原始调用 + 1次重试


# 集成测试类
class TestIntegrationScenarios:
    """集成测试场景"""

    @patch('boto3.client')
    def test_content_generation_pipeline(self, mock_boto3):
        """测试内容生成管道"""
        # Mock Bedrock客户端
        mock_bedrock = Mock()
        mock_s3 = Mock()
        mock_boto3.side_effect = lambda service_name, **kwargs: {
            'bedrock-runtime': mock_bedrock,
            's3': mock_s3
        }[service_name]

        # Mock Bedrock响应
        mock_response = {
            "body": Mock(),
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        sample_outline = {
            "title": "人工智能技术",
            "slides": [
                {"slide_number": 1, "title": "标题页", "content": ["AI技术概述"]},
                {"slide_number": 2, "title": "核心技术", "content": ["机器学习", "深度学习"]},
                {"slide_number": 3, "title": "应用场景", "content": ["自动驾驶", "医疗诊断"]},
                {"slide_number": 4, "title": "发展趋势", "content": ["AGI发展", "技术融合"]},
                {"slide_number": 5, "title": "总结", "content": ["技术价值", "未来展望"]}
            ],
            "metadata": {
                "total_slides": 5,
                "created_at": "2025-01-01T00:00:00"
            }
        }

        mock_response["body"].read.return_value = json.dumps({
            "content": [{"text": json.dumps(sample_outline)}]
        }).encode()

        mock_bedrock.invoke_model.return_value = mock_response

        # 执行内容生成
        generator = ContentGenerator()
        outline = generator.generate_outline("人工智能技术", 5)

        # 验证结果
        assert outline is not None
        assert "title" in outline
        assert "slides" in outline
        assert len(outline["slides"]) == 5
        assert outline["metadata"]["total_slides"] == 5

    @patch('boto3.client')
    def test_ppt_compilation_pipeline(self, mock_boto3):
        """测试PPT编译管道"""
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3

        # 准备有效的大纲数据
        outline = {
            "title": "测试演示文稿",
            "slides": [
                {"slide_number": 1, "title": "标题页", "content": ["测试内容"]},
                {"slide_number": 2, "title": "内容页", "content": ["要点1", "要点2"]}
            ],
            "metadata": {"total_slides": 2}
        }

        # 执行PPT编译
        compiler = PPTCompiler()

        # 验证大纲结构（应该不抛出异常）
        compiler._validate_outline_structure(outline)

        # 测试样式应用
        styled_outline = compiler._apply_template_style(outline, "professional")
        assert styled_outline is not None

    def test_validation_pipeline(self):
        """测试验证管道"""
        # 测试完整的验证流程
        presentation_id = str(uuid.uuid4())

        # 验证生成请求
        request_body = {
            "topic": "人工智能技术发展",
            "page_count": 5
        }

        is_valid, error_msg = RequestValidator.validate_generate_request(request_body)
        assert is_valid is True
        assert error_msg is None

        # 验证状态请求
        is_valid, error_msg = RequestValidator.validate_status_request(presentation_id)
        assert is_valid is True
        assert error_msg is None

        # 清理输入
        clean_topic = RequestValidator.sanitize_topic(request_body["topic"])
        assert clean_topic == request_body["topic"]

        # 构建响应
        response_data = {
            "topic": clean_topic,
            "page_count": request_body["page_count"],
            "presentation_id": presentation_id
        }

        response = ResponseBuilder.success_response(200, response_data)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert body["topic"] == request_body["topic"]
        assert body["page_count"] == request_body["page_count"]
        assert body["presentation_id"] == presentation_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src", "--cov-report=term-missing"])