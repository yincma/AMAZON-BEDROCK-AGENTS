"""
Unit tests for Generate Image Lambda Function
"""

import base64
import io
import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from PIL import Image

# Set environment variables before importing the handler
os.environ["IMAGE_MODEL_ID"] = "stability.stable-diffusion-xl-v1"
os.environ["SESSIONS_TABLE"] = "test-sessions-table"
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["AWS_REGION"] = "us-west-2"
os.environ["MAX_CONCURRENT_IMAGES"] = "2"
os.environ["UNSPLASH_ACCESS_KEY"] = "test-key"

from generate_image import (
    GeneratedImage,
    ImageRequest,
    fetch_stock_image,
    generate_images_parallel,
    generate_placeholder_image,
    generate_with_bedrock,
    lambda_handler,
    optimize_prompt,
    process_slide_image,
    save_image_to_s3,
)


@pytest.fixture
def valid_event():
    """Valid API Gateway event"""
    return {
        "body": json.dumps(
            {
                "presentation_id": "test-presentation-123",
                "session_id": "test-session-456",
                "slides": [
                    {
                        "slide_number": 1,
                        "title": "Introduction",
                        "visual_element": "Modern office workspace with computers",
                        "language": "en",
                    },
                    {
                        "slide_number": 2,
                        "title": "Data Analysis",
                        "suggested_visual": "Bar chart showing growth trends",
                        "language": "en",
                    },
                ],
                "style": "professional",
                "quality": "standard",
                "use_ai_generation": True,
                "fallback_to_stock": True,
            }
        ),
        "headers": {"Content-Type": "application/json"},
        "requestContext": {"requestId": "test-request-id"},
    }


@pytest.fixture
def mock_image_data():
    """Mock image data"""
    img = Image.new("RGB", (1024, 768), color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.request_id = "test-request-id"
    context.function_name = "generate-image"
    context.memory_limit_in_mb = "256"
    context.invoked_function_arn = (
        "arn:aws:lambda:us-west-2:123456789:function:generate-image"
    )
    return context


class TestImageRequest:
    """Test request validation"""

    def test_valid_request(self):
        """Test valid request creation"""
        request = ImageRequest(
            presentation_id="test-123",
            slides=[],
            style="professional",
            quality="standard",
        )
        assert request.presentation_id == "test-123"
        assert request.style == "professional"

    def test_invalid_quality(self):
        """Test quality validation"""
        with pytest.raises(ValueError):
            ImageRequest(presentation_id="test-123", slides=[], quality="invalid")

    def test_invalid_style(self):
        """Test style validation"""
        with pytest.raises(ValueError):
            ImageRequest(presentation_id="test-123", slides=[], style="invalid_style")

    def test_default_values(self):
        """Test default values"""
        request = ImageRequest(presentation_id="test-123", slides=[])
        assert request.quality == "standard"
        assert request.use_ai_generation is True
        assert request.fallback_to_stock is True


class TestPromptOptimization:
    """Test prompt optimization"""

    @patch("generate_image.translate")
    def test_prompt_optimization_english(self, mock_translate):
        """Test prompt optimization for English text"""
        prompt, negative = optimize_prompt(
            "A beautiful sunset over the ocean", "professional", "en"
        )

        assert "beautiful sunset over the ocean" in prompt
        assert "professional" in prompt
        assert "8k resolution" in prompt
        assert "blur" in negative
        mock_translate.translate_text.assert_not_called()

    @patch("generate_image.translate")
    def test_prompt_optimization_translation(self, mock_translate):
        """Test prompt optimization with translation"""
        mock_translate.translate_text.return_value = {
            "TranslatedText": "A beautiful sunset"
        }

        prompt, negative = optimize_prompt("Un hermoso atardecer", "artistic", "es")

        assert "beautiful sunset" in prompt
        assert "artistic" in prompt
        mock_translate.translate_text.assert_called_once()

    def test_different_styles(self):
        """Test different style modifiers"""
        styles = [
            "professional",
            "creative",
            "minimalist",
            "photorealistic",
            "artistic",
            "corporate",
        ]

        for style in styles:
            prompt, _ = optimize_prompt("test image", style, "en")
            assert style in prompt.lower() or "business" in prompt.lower()


class TestBedrockGeneration:
    """Test Bedrock image generation"""

    @patch("generate_image.bedrock_runtime")
    def test_stable_diffusion_generation(self, mock_bedrock, mock_image_data):
        """Test image generation with Stable Diffusion"""
        mock_response = {"body": MagicMock()}
        mock_response["body"].read.return_value = json.dumps(
            {"artifacts": [{"base64": base64.b64encode(mock_image_data).decode()}]}
        ).encode()
        mock_bedrock.invoke_model.return_value = mock_response

        result = generate_with_bedrock("test prompt", "negative prompt", "standard")

        assert result == mock_image_data
        mock_bedrock.invoke_model.assert_called_once()

        # Check request structure
        call_args = json.loads(mock_bedrock.invoke_model.call_args[1]["body"])
        assert call_args["text_prompts"][0]["text"] == "test prompt"
        assert call_args["cfg_scale"] == 8

    @patch("generate_image.bedrock_runtime")
    @patch("generate_image.IMAGE_MODEL_ID", "amazon.titan-image-generator-v1")
    def test_titan_generation(self, mock_bedrock, mock_image_data):
        """Test image generation with Titan"""
        mock_response = {"body": MagicMock()}
        mock_response["body"].read.return_value = json.dumps(
            {"images": [base64.b64encode(mock_image_data).decode()]}
        ).encode()
        mock_bedrock.invoke_model.return_value = mock_response

        result = generate_with_bedrock("test prompt", "negative prompt", "high")

        assert result == mock_image_data
        mock_bedrock.invoke_model.assert_called_once()

    @patch("generate_image.bedrock_runtime")
    def test_generation_retry(self, mock_bedrock):
        """Test retry logic on Bedrock errors"""
        mock_bedrock.invoke_model.side_effect = [
            Exception("Temporary error"),
            Exception("Another error"),
            Exception("Final error"),
        ]

        with pytest.raises(Exception):
            generate_with_bedrock("test", "negative", "standard")

        assert mock_bedrock.invoke_model.call_count == 3


class TestStockImages:
    """Test stock image fetching"""

    @patch("requests.get")
    def test_fetch_stock_image_success(self, mock_get, mock_image_data):
        """Test successful stock image fetch"""
        # Mock search response
        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "results": [
                {
                    "urls": {"regular": "https://example.com/image.jpg"},
                    "user": {"name": "Test Photographer"},
                }
            ]
        }

        # Mock image download response
        image_response = Mock()
        image_response.status_code = 200
        image_response.content = mock_image_data

        mock_get.side_effect = [search_response, image_response]

        image_data, attribution = fetch_stock_image("sunset", "professional")

        assert image_data == mock_image_data
        assert "Test Photographer" in attribution
        assert mock_get.call_count == 2

    @patch("requests.get")
    def test_fetch_stock_image_no_results(self, mock_get):
        """Test stock image fetch with no results"""
        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = {"results": []}

        mock_get.return_value = search_response

        with pytest.raises(ValueError, match="No stock images found"):
            fetch_stock_image("obscure query", "professional")

    def test_fetch_stock_no_api_key(self):
        """Test stock image fetch without API key"""
        with patch.dict(os.environ, {"UNSPLASH_ACCESS_KEY": ""}):
            with pytest.raises(ValueError, match="Unsplash API key not configured"):
                fetch_stock_image("test", "professional")


class TestPlaceholderGeneration:
    """Test placeholder image generation"""

    @patch("requests.get")
    def test_placeholder_from_service(self, mock_get):
        """Test placeholder generation from service"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"placeholder image data"
        mock_get.return_value = mock_response

        result = generate_placeholder_image("Test Slide")

        assert result == b"placeholder image data"
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_placeholder_fallback(self, mock_get):
        """Test placeholder generation fallback"""
        mock_get.side_effect = Exception("Service unavailable")

        result = generate_placeholder_image("Test")

        # Should return PNG data
        assert result.startswith(b"\x89PNG")


class TestS3Operations:
    """Test S3 operations"""

    @patch("generate_image.s3")
    def test_save_image_to_s3(self, mock_s3, mock_image_data):
        """Test saving image to S3"""
        mock_s3.generate_presigned_url.side_effect = [
            "https://s3.example.com/image.png",
            "https://s3.example.com/image_thumb.png",
        ]

        url, thumb_url = save_image_to_s3(
            mock_image_data, "presentation-123", 1, "ai_generated"
        )

        assert url == "https://s3.example.com/image.png"
        assert thumb_url == "https://s3.example.com/image_thumb.png"

        # Check S3 put_object was called twice (image and thumbnail)
        assert mock_s3.put_object.call_count == 2


class TestSlideProcessing:
    """Test individual slide processing"""

    @patch("generate_image.generate_with_bedrock")
    @patch("generate_image.save_image_to_s3")
    def test_process_slide_with_ai(self, mock_s3, mock_bedrock, mock_image_data):
        """Test processing slide with AI generation"""
        mock_bedrock.return_value = mock_image_data
        mock_s3.return_value = (
            "https://s3.example.com/image.png",
            "https://s3.example.com/thumb.png",
        )

        slide = {
            "slide_number": 1,
            "title": "Test Slide",
            "visual_element": "Beautiful landscape",
        }

        result = process_slide_image(
            slide, "presentation-123", "professional", "standard", True, True
        )

        assert result.slide_number == 1
        assert result.image_type == "ai_generated"
        assert result.image_url == "https://s3.example.com/image.png"
        mock_bedrock.assert_called_once()

    @patch("generate_image.generate_with_bedrock")
    @patch("generate_image.fetch_stock_image")
    @patch("generate_image.save_image_to_s3")
    def test_process_slide_fallback_to_stock(
        self, mock_s3, mock_stock, mock_bedrock, mock_image_data
    ):
        """Test fallback to stock images"""
        mock_bedrock.side_effect = Exception("AI generation failed")
        mock_stock.return_value = (mock_image_data, "Photo by Test")
        mock_s3.return_value = (
            "https://s3.example.com/stock.png",
            "https://s3.example.com/thumb.png",
        )

        slide = {
            "slide_number": 2,
            "title": "Test Slide",
            "suggested_visual": "Office workspace",
        }

        result = process_slide_image(
            slide, "presentation-123", "professional", "standard", True, True
        )

        assert result.image_type == "stock"
        assert "Photo by Test" in result.metadata["attribution"]
        mock_stock.assert_called_once()


class TestParallelGeneration:
    """Test parallel image generation"""

    @patch("generate_image.process_slide_image")
    def test_parallel_generation(self, mock_process):
        """Test generating multiple images in parallel"""
        mock_process.side_effect = [
            GeneratedImage(
                slide_number=1,
                image_url="url1",
                image_type="ai_generated",
                prompt_used="prompt1",
                metadata={},
                s3_key="key1",
            ),
            GeneratedImage(
                slide_number=2,
                image_url="url2",
                image_type="stock",
                prompt_used="prompt2",
                metadata={},
                s3_key="key2",
            ),
        ]

        slides = [
            {"slide_number": 1, "visual_element": "image1"},
            {"slide_number": 2, "visual_element": "image2"},
        ]

        results = generate_images_parallel(
            slides, "presentation-123", "professional", "standard", True, True
        )

        assert len(results) == 2
        assert results[0].slide_number == 1
        assert results[1].slide_number == 2
        assert mock_process.call_count == 2


class TestLambdaHandler:
    """Test main Lambda handler"""

    @patch("generate_image.generate_images_parallel")
    @patch("generate_image.save_metadata_to_dynamodb")
    def test_successful_image_generation(
        self, mock_dynamodb, mock_generate, valid_event, lambda_context
    ):
        """Test successful image generation through Lambda handler"""
        mock_images = [
            GeneratedImage(
                slide_number=1,
                image_url="url1",
                image_type="ai_generated",
                prompt_used="prompt1",
                metadata={},
                s3_key="key1",
            ),
            GeneratedImage(
                slide_number=2,
                image_url="url2",
                image_type="stock",
                prompt_used="prompt2",
                metadata={},
                s3_key="key2",
            ),
        ]

        mock_generate.return_value = mock_images

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["total_images"] == 2
        assert body["statistics"]["ai_generated"] == 1
        assert body["statistics"]["stock_images"] == 1

        mock_generate.assert_called_once()
        mock_dynamodb.assert_called_once()

    def test_no_slides_needing_images(self, lambda_context):
        """Test handling when no slides need images"""
        event = {
            "body": json.dumps(
                {
                    "presentation_id": "test-123",
                    "slides": [{"slide_number": 1, "title": "Text only slide"}],
                }
            )
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["message"] == "No slides require image generation"

    def test_invalid_request(self, lambda_context):
        """Test handling of invalid request"""
        event = {
            "body": json.dumps(
                {
                    "presentation_id": "test-123",
                    "slides": [],
                    "quality": "invalid_quality",
                }
            )
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_cors_headers(self, valid_event, lambda_context):
        """Test CORS headers in response"""
        response = lambda_handler(valid_event, lambda_context)

        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert response["headers"]["Content-Type"] == "application/json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
