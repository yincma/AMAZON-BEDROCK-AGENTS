"""
Unit tests for Generate Content Lambda Function
"""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

# Set environment variables before importing the handler
os.environ["BEDROCK_MODEL_ID"] = "anthropic.claude-4-0"
os.environ["SESSIONS_TABLE"] = "test-sessions-table"
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["AWS_REGION"] = "us-west-2"
os.environ["MAX_CONCURRENT_SLIDES"] = "3"

from generate_content import (
    ContentRequest,
    SlideContent,
    calculate_word_count,
    create_slide_prompt,
    determine_slide_type,
    generate_slide_content,
    generate_slides_batch,
    generate_slides_parallel,
    lambda_handler,
)


@pytest.fixture
def valid_event():
    """Valid API Gateway event"""
    return {
        "body": json.dumps(
            {
                "presentation_id": "test-presentation-123",
                "session_id": "test-session-456",
                "outline": {
                    "title": "Test Presentation",
                    "language": "en",
                    "style": "professional",
                    "duration_minutes": 20,
                    "slides": [
                        {
                            "slide_number": 1,
                            "title": "Introduction",
                            "content_points": ["Welcome", "Agenda", "Objectives"],
                            "speaker_notes": "Welcome everyone",
                            "estimated_duration": 2,
                        },
                        {
                            "slide_number": 2,
                            "title": "Main Content",
                            "content_points": ["Point 1", "Point 2", "Point 3"],
                            "speaker_notes": "Explain main points",
                            "estimated_duration": 3,
                        },
                    ],
                },
                "detail_level": "medium",
                "parallel_generation": True,
            }
        ),
        "headers": {"Content-Type": "application/json"},
        "requestContext": {"requestId": "test-request-id"},
    }


@pytest.fixture
def mock_bedrock_response():
    """Mock Bedrock API response for content generation"""
    return {
        "main_points": ["Expanded point 1", "Expanded point 2", "Expanded point 3"],
        "detailed_content": "This is the detailed content for the slide with comprehensive information.",
        "speaker_notes": "These are detailed speaker notes to guide the presenter.",
        "visual_elements": [
            {
                "type": "chart",
                "description": "Bar chart showing data",
                "position": "right",
            },
            {
                "type": "image",
                "description": "Background image",
                "position": "background",
            },
        ],
        "animations_suggested": ["Fade in title", "Slide up bullets"],
        "data_visualizations": [
            {
                "type": "bar_chart",
                "data": {"x": [1, 2, 3], "y": [10, 20, 30]},
                "title": "Sample Data",
            }
        ],
        "references": ["Source 1", "Source 2"],
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.request_id = "test-request-id"
    context.function_name = "generate-content"
    context.memory_limit_in_mb = "256"
    context.invoked_function_arn = (
        "arn:aws:lambda:us-west-2:123456789:function:generate-content"
    )
    context.aws_request_id = "test-request-id"
    return context


class TestContentRequest:
    """Test request validation"""

    def test_valid_request(self):
        """Test valid request creation"""
        request = ContentRequest(
            presentation_id="test-123",
            outline={"title": "Test", "slides": []},
            detail_level="medium",
            parallel_generation=True,
        )
        assert request.presentation_id == "test-123"
        assert request.detail_level == "medium"

    def test_invalid_detail_level(self):
        """Test detail level validation"""
        with pytest.raises(ValueError):
            ContentRequest(
                presentation_id="test-123",
                outline={"title": "Test", "slides": []},
                detail_level="invalid_level",
            )

    def test_default_values(self):
        """Test default values for optional fields"""
        request = ContentRequest(
            presentation_id="test-123", outline={"title": "Test", "slides": []}
        )
        assert request.detail_level == "medium"
        assert request.include_data is False
        assert request.include_references is False
        assert request.parallel_generation is True


class TestSlideTypeDetection:
    """Test slide type determination"""

    def test_title_slide(self):
        """Test detection of title slide"""
        slide_type = determine_slide_type({}, 1, 10)
        assert slide_type == "title"

    def test_thank_you_slide(self):
        """Test detection of thank you slide"""
        slide_type = determine_slide_type({}, 10, 10)
        assert slide_type == "thank_you"

    def test_conclusion_slide(self):
        """Test detection of conclusion slide"""
        slide_type = determine_slide_type({}, 9, 10)
        assert slide_type == "conclusion"

    def test_section_slide(self):
        """Test detection of section divider slide"""
        slide_type = determine_slide_type({"title": "Section Overview"}, 5, 10)
        assert slide_type == "section"

    def test_content_slide(self):
        """Test detection of regular content slide"""
        slide_type = determine_slide_type({"title": "Regular Content"}, 5, 10)
        assert slide_type == "content"


class TestPromptCreation:
    """Test prompt generation for content"""

    def test_minimal_detail_prompt(self):
        """Test prompt for minimal detail level"""
        slide_info = {
            "slide_number": 1,
            "title": "Test Slide",
            "content_points": ["Point 1", "Point 2"],
            "content_type": "content",
        }
        prompt = create_slide_prompt(slide_info, "minimal", "en", "professional")

        assert "Test Slide" in prompt
        assert "minimal" in prompt.lower()
        assert "professional" in prompt

    def test_comprehensive_detail_prompt(self):
        """Test prompt for comprehensive detail level"""
        slide_info = {
            "slide_number": 1,
            "title": "Detailed Slide",
            "content_points": ["Complex Point"],
            "content_type": "content",
        }
        prompt = create_slide_prompt(slide_info, "comprehensive", "en", "academic")

        assert "comprehensive" in prompt.lower()
        assert "academic" in prompt

    def test_title_slide_prompt(self):
        """Test prompt for title slide generation"""
        slide_info = {
            "slide_number": 1,
            "title": "Presentation Title",
            "content_points": [],
            "content_type": "title",
        }
        prompt = create_slide_prompt(slide_info, "medium", "en", "professional")

        assert "title slide" in prompt.lower()
        assert "impactful" in prompt.lower()


class TestContentGeneration:
    """Test Bedrock content generation"""

    @patch("generate_content.bedrock_runtime")
    def test_successful_content_generation(self, mock_bedrock, mock_bedrock_response):
        """Test successful content generation for a slide"""
        mock_response = {"body": MagicMock()}
        mock_response["body"].read.return_value = json.dumps(
            {"content": [{"text": json.dumps(mock_bedrock_response)}]}
        ).encode()
        mock_bedrock.invoke_model.return_value = mock_response

        slide_info = {
            "slide_number": 1,
            "title": "Test Slide",
            "content_points": ["Point 1"],
        }

        result = generate_slide_content(slide_info, "medium", "en", "professional")

        assert result["main_points"] == mock_bedrock_response["main_points"]
        assert result["detailed_content"] == mock_bedrock_response["detailed_content"]
        assert "visual_elements" in result
        mock_bedrock.invoke_model.assert_called_once()

    @patch("generate_content.bedrock_runtime")
    def test_content_generation_with_markdown(
        self, mock_bedrock, mock_bedrock_response
    ):
        """Test JSON extraction from markdown code blocks"""
        mock_response = {"body": MagicMock()}
        mock_response["body"].read.return_value = json.dumps(
            {
                "content": [
                    {"text": f"```json\n{json.dumps(mock_bedrock_response)}\n```"}
                ]
            }
        ).encode()
        mock_bedrock.invoke_model.return_value = mock_response

        slide_info = {
            "slide_number": 1,
            "title": "Test Slide",
            "content_points": ["Point 1"],
        }

        result = generate_slide_content(slide_info, "medium", "en", "professional")

        assert result["main_points"] == mock_bedrock_response["main_points"]

    @patch("generate_content.bedrock_runtime")
    def test_content_generation_retry(self, mock_bedrock):
        """Test retry logic on Bedrock errors"""
        mock_bedrock.invoke_model.side_effect = [
            Exception("Temporary error"),
            Exception("Another error"),
            Exception("Final error"),
        ]

        slide_info = {
            "slide_number": 1,
            "title": "Test Slide",
            "content_points": ["Point 1"],
        }

        with pytest.raises(Exception):
            generate_slide_content(slide_info, "medium", "en", "professional")

        assert mock_bedrock.invoke_model.call_count == 3


class TestParallelGeneration:
    """Test parallel slide generation"""

    @patch("generate_content.generate_slide_content")
    def test_parallel_slide_generation(self, mock_generate, mock_bedrock_response):
        """Test generating multiple slides in parallel"""
        mock_generate.return_value = mock_bedrock_response

        slides = [
            {"slide_number": 1, "title": "Slide 1", "content_points": ["Point 1"]},
            {"slide_number": 2, "title": "Slide 2", "content_points": ["Point 2"]},
            {"slide_number": 3, "title": "Slide 3", "content_points": ["Point 3"]},
        ]

        result = generate_slides_parallel(slides, "medium", "en", "professional")

        assert len(result) == 3
        assert all(isinstance(slide, SlideContent) for slide in result)
        assert result[0].slide_number == 1
        assert result[1].slide_number == 2
        assert result[2].slide_number == 3
        assert mock_generate.call_count == 3

    @patch("generate_content.generate_slide_content")
    def test_parallel_generation_with_failure(
        self, mock_generate, mock_bedrock_response
    ):
        """Test parallel generation with some slides failing"""
        mock_generate.side_effect = [
            mock_bedrock_response,
            Exception("Generation failed"),
            mock_bedrock_response,
        ]

        slides = [
            {"slide_number": 1, "title": "Slide 1", "content_points": ["Point 1"]},
            {"slide_number": 2, "title": "Slide 2", "content_points": ["Point 2"]},
            {"slide_number": 3, "title": "Slide 3", "content_points": ["Point 3"]},
        ]

        result = generate_slides_parallel(slides, "medium", "en", "professional")

        assert len(result) == 3
        assert result[1].detailed_content == "Content generation failed. Please retry."


class TestBatchGeneration:
    """Test batch slide generation"""

    @patch("generate_content.generate_slide_content")
    def test_batch_slide_generation(self, mock_generate, mock_bedrock_response):
        """Test generating slides in batches"""
        mock_generate.return_value = mock_bedrock_response

        slides = [
            {"slide_number": i, "title": f"Slide {i}", "content_points": [f"Point {i}"]}
            for i in range(1, 6)
        ]

        result = generate_slides_batch(slides, "medium", "en", "professional")

        assert len(result) == 5
        assert all(isinstance(slide, SlideContent) for slide in result)
        assert mock_generate.call_count == 5


class TestWordCount:
    """Test word counting functionality"""

    def test_word_count_calculation(self):
        """Test calculating total word count across slides"""
        slides = [
            SlideContent(
                slide_number=1,
                title="Slide 1",
                content_type="content",
                main_points=["This is point one", "This is point two"],
                detailed_content="This is the detailed content with multiple words.",
                speaker_notes="These are speaker notes.",
                visual_elements=[],
            ),
            SlideContent(
                slide_number=2,
                title="Slide 2",
                content_type="content",
                main_points=["Another point"],
                detailed_content="More content here.",
                speaker_notes="More notes.",
                visual_elements=[],
            ),
        ]

        word_count = calculate_word_count(slides)

        # Count words manually for verification
        expected_count = (
            8
            + 4  # Slide 1 main points
            + 8  # Slide 1 detailed content
            + 4  # Slide 1 speaker notes
            + 2  # Slide 2 main points
            + 3  # Slide 2 detailed content
            + 2  # Slide 2 speaker notes
        )

        assert word_count == expected_count


class TestLambdaHandler:
    """Test main Lambda handler"""

    @patch("generate_content.generate_slides_parallel")
    @patch("generate_content.save_content_to_dynamodb")
    @patch("generate_content.save_content_to_s3")
    def test_successful_content_generation_handler(
        self,
        mock_s3,
        mock_dynamodb,
        mock_generate,
        valid_event,
        lambda_context,
        mock_bedrock_response,
    ):
        """Test successful content generation through Lambda handler"""
        mock_slides = [
            SlideContent(
                slide_number=1,
                title="Slide 1",
                content_type="title",
                main_points=["Point 1"],
                detailed_content="Content 1",
                speaker_notes="Notes 1",
                visual_elements=[],
            ),
            SlideContent(
                slide_number=2,
                title="Slide 2",
                content_type="content",
                main_points=["Point 2"],
                detailed_content="Content 2",
                speaker_notes="Notes 2",
                visual_elements=[],
            ),
        ]

        mock_generate.return_value = mock_slides
        mock_s3.return_value = (
            "s3://test-bucket/content/test-presentation-123/content.json"
        )

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["slides_generated"] == 2
        assert "total_word_count" in body

        mock_generate.assert_called_once()
        mock_dynamodb.assert_called_once()
        mock_s3.assert_called_once()

    def test_invalid_request_body(self, lambda_context):
        """Test handling of invalid request body"""
        event = {
            "body": json.dumps(
                {
                    "presentation_id": "test-123",
                    "outline": {"title": "Test"},
                    "detail_level": "invalid",
                }
            )
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert body["error"] == "Invalid request"

    def test_missing_slides_in_outline(self, lambda_context):
        """Test handling of outline without slides"""
        event = {
            "body": json.dumps(
                {
                    "presentation_id": "test-123",
                    "outline": {"title": "Test", "slides": []},
                }
            )
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "No slides found in outline"

    @patch("generate_content.generate_slides_batch")
    def test_sequential_generation_for_small_presentations(
        self, mock_generate, lambda_context
    ):
        """Test that small presentations use batch generation"""
        event = {
            "body": json.dumps(
                {
                    "presentation_id": "test-123",
                    "outline": {
                        "title": "Small Presentation",
                        "slides": [
                            {
                                "slide_number": 1,
                                "title": "Slide 1",
                                "content_points": ["Point 1"],
                            },
                            {
                                "slide_number": 2,
                                "title": "Slide 2",
                                "content_points": ["Point 2"],
                            },
                        ],
                    },
                    "parallel_generation": False,
                }
            )
        }

        mock_generate.return_value = []

        lambda_handler(event, lambda_context)

        mock_generate.assert_called_once()

    def test_cors_headers(self, valid_event, lambda_context):
        """Test CORS headers in response"""
        response = lambda_handler(valid_event, lambda_context)

        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert response["headers"]["Content-Type"] == "application/json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
