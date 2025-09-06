"""
Unit tests for Create Outline Lambda Function
"""

import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

# Set environment variables before importing the handler
os.environ["BEDROCK_MODEL_ID"] = "anthropic.claude-4-0"
os.environ["SESSIONS_TABLE"] = "test-sessions-table"
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["AWS_REGION"] = "us-west-2"

from create_outline import (
    OutlineRequest,
    PresentationOutline,
    call_bedrock,
    create_outline_prompt,
    lambda_handler,
    save_to_dynamodb,
    save_to_s3,
)


@pytest.fixture
def valid_event():
    """Valid API Gateway event"""
    return {
        "body": json.dumps(
            {
                "topic": "Introduction to Machine Learning",
                "audience": "beginners",
                "duration_minutes": 30,
                "style": "professional",
                "language": "en",
                "num_slides": 10,
                "include_examples": True,
                "user_id": "test-user-123",
            }
        ),
        "headers": {"Content-Type": "application/json"},
        "requestContext": {"requestId": "test-request-id"},
    }


@pytest.fixture
def mock_bedrock_response():
    """Mock Bedrock API response"""
    return {
        "title": "Introduction to Machine Learning",
        "subtitle": "A Beginner's Guide",
        "slides": [
            {
                "slide_number": 1,
                "title": "Welcome",
                "content_points": ["Introduction", "Objectives", "Overview"],
                "speaker_notes": "Welcome everyone to this presentation",
                "suggested_visual": "Title slide with modern design",
                "estimated_duration": 2,
            },
            {
                "slide_number": 2,
                "title": "What is Machine Learning?",
                "content_points": ["Definition", "Key concepts", "Applications"],
                "speaker_notes": "Explain the basic concept of ML",
                "suggested_visual": "Diagram showing ML process",
                "estimated_duration": 3,
            },
        ],
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.request_id = "test-request-id"
    context.function_name = "create-outline"
    context.memory_limit_in_mb = "256"
    context.invoked_function_arn = (
        "arn:aws:lambda:us-west-2:123456789:function:create-outline"
    )
    context.aws_request_id = "test-request-id"
    return context


class TestOutlineRequest:
    """Test request validation"""

    def test_valid_request(self):
        """Test valid request creation"""
        request = OutlineRequest(
            topic="Test Topic",
            audience="general",
            duration_minutes=20,
            style="professional",
            language="en",
            num_slides=10,
        )
        assert request.topic == "Test Topic"
        assert request.style == "professional"

    def test_invalid_topic_length(self):
        """Test topic length validation"""
        with pytest.raises(ValueError):
            OutlineRequest(topic="AB")  # Too short

    def test_invalid_style(self):
        """Test style validation"""
        with pytest.raises(ValueError):
            OutlineRequest(topic="Test Topic", style="invalid_style")

    def test_invalid_language(self):
        """Test language validation"""
        with pytest.raises(ValueError):
            OutlineRequest(topic="Test Topic", language="unsupported")

    def test_invalid_duration(self):
        """Test duration validation"""
        with pytest.raises(ValueError):
            OutlineRequest(topic="Test Topic", duration_minutes=200)  # Too long

    def test_invalid_num_slides(self):
        """Test slide count validation"""
        with pytest.raises(ValueError):
            OutlineRequest(topic="Test Topic", num_slides=50)  # Too many


class TestPromptCreation:
    """Test prompt generation"""

    def test_professional_style_prompt(self):
        """Test prompt for professional style"""
        request = OutlineRequest(
            topic="Cloud Computing",
            audience="IT professionals",
            style="professional",
            num_slides=8,
        )
        prompt = create_outline_prompt(request)

        assert "Cloud Computing" in prompt
        assert "IT professionals" in prompt
        assert "professional" in prompt
        assert "8 slides" in prompt

    def test_multilingual_prompt(self):
        """Test prompt for different languages"""
        request = OutlineRequest(topic="AI Ethics", language="ja")
        prompt = create_outline_prompt(request)

        assert "日本語で生成" in prompt

    def test_include_examples_prompt(self):
        """Test prompt with examples flag"""
        request = OutlineRequest(topic="Python Programming", include_examples=True)
        prompt = create_outline_prompt(request)

        assert "include specific examples" in prompt


class TestBedrockIntegration:
    """Test Bedrock API integration"""

    @patch("create_outline.bedrock_runtime")
    def test_successful_bedrock_call(self, mock_bedrock, mock_bedrock_response):
        """Test successful Bedrock API call"""
        mock_response = {"body": MagicMock()}
        mock_response["body"].read.return_value = json.dumps(
            {"content": [{"text": json.dumps(mock_bedrock_response)}]}
        ).encode()
        mock_bedrock.invoke_model.return_value = mock_response

        result = call_bedrock("Test prompt")

        assert result["title"] == "Introduction to Machine Learning"
        assert len(result["slides"]) == 2
        mock_bedrock.invoke_model.assert_called_once()

    @patch("create_outline.bedrock_runtime")
    def test_bedrock_retry_on_error(self, mock_bedrock):
        """Test retry logic on Bedrock errors"""
        mock_bedrock.invoke_model.side_effect = [
            Exception("Temporary error"),
            Exception("Another error"),
            {
                "body": MagicMock(
                    read=lambda: json.dumps(
                        {"content": [{"text": '{"title": "Test", "slides": []}'}]}
                    ).encode()
                )
            },
        ]

        with pytest.raises(Exception):
            call_bedrock("Test prompt")

        assert mock_bedrock.invoke_model.call_count == 3

    @patch("create_outline.bedrock_runtime")
    def test_bedrock_json_parsing_with_markdown(self, mock_bedrock):
        """Test JSON extraction from markdown code blocks"""
        mock_response = {"body": MagicMock()}
        mock_response["body"].read.return_value = json.dumps(
            {"content": [{"text": '```json\n{"title": "Test", "slides": []}\n```'}]}
        ).encode()
        mock_bedrock.invoke_model.return_value = mock_response

        result = call_bedrock("Test prompt")

        assert result["title"] == "Test"


class TestDynamoDBIntegration:
    """Test DynamoDB operations"""

    @patch("create_outline.dynamodb")
    def test_save_to_dynamodb(self, mock_dynamodb):
        """Test saving outline to DynamoDB"""
        mock_table = Mock()
        mock_dynamodb.Table.return_value = mock_table

        outline = PresentationOutline(
            presentation_id="test-id",
            topic="Test Topic",
            title="Test Title",
            audience="general",
            duration_minutes=20,
            style="professional",
            language="en",
            slides=[],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        save_to_dynamodb(outline)

        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]["Item"]
        assert call_args["presentation_id"] == "test-id"
        assert call_args["status"] == "outline_created"
        assert "ttl" in call_args


class TestS3Integration:
    """Test S3 operations"""

    @patch("create_outline.s3")
    def test_save_to_s3(self, mock_s3):
        """Test saving outline to S3"""
        outline = PresentationOutline(
            presentation_id="test-id",
            topic="Test Topic",
            title="Test Title",
            audience="general",
            duration_minutes=20,
            style="professional",
            language="en",
            slides=[],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        location = save_to_s3(outline)

        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args[1]
        assert call_args["Key"] == "outlines/test-id/outline.json"
        assert call_args["ContentType"] == "application/json"
        assert location == "s3://test-bucket/outlines/test-id/outline.json"


class TestLambdaHandler:
    """Test main Lambda handler"""

    @patch("create_outline.call_bedrock")
    @patch("create_outline.save_to_dynamodb")
    @patch("create_outline.save_to_s3")
    def test_successful_outline_generation(
        self,
        mock_s3,
        mock_dynamodb,
        mock_bedrock,
        valid_event,
        mock_bedrock_response,
        lambda_context,
    ):
        """Test successful outline generation flow"""
        mock_bedrock.return_value = mock_bedrock_response
        mock_s3.return_value = "s3://test-bucket/outlines/test-id/outline.json"

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert "presentation_id" in body
        assert "outline" in body
        assert len(body["outline"]["slides"]) == 2

        mock_bedrock.assert_called_once()
        mock_dynamodb.assert_called_once()
        mock_s3.assert_called_once()

    def test_invalid_request_body(self, lambda_context):
        """Test handling of invalid request body"""
        event = {"body": json.dumps({"topic": "AB"})}  # Too short

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert body["error"] == "Invalid request"

    def test_missing_body(self, lambda_context):
        """Test handling of missing body"""
        event = {}

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    @patch("create_outline.call_bedrock")
    def test_bedrock_error_handling(self, mock_bedrock, valid_event, lambda_context):
        """Test handling of Bedrock API errors"""
        mock_bedrock.side_effect = Exception("Bedrock API error")

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert "error" in body
        assert body["error"] == "Internal server error"

    def test_cors_headers(self, valid_event, lambda_context):
        """Test CORS headers in response"""
        response = lambda_handler(valid_event, lambda_context)

        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert response["headers"]["Content-Type"] == "application/json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
