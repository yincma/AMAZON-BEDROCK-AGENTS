"""
Unit tests for Compile PPTX Lambda Function
"""

import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

# Set environment variables before importing
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["MAX_CONCURRENT_DOWNLOADS"] = "5"
os.environ["IMAGE_DOWNLOAD_TIMEOUT"] = "10"

# Mock the modules before import
sys.modules["models.presentation_model"] = MagicMock()
sys.modules["views.presentation_view"] = MagicMock()

from compile_pptx import (
    CompileRequest,
    CompileResponse,
    PresentationCompiler,
    lambda_handler,
)

# Import mocked modules for use in tests
from models.presentation_model import (
    PresentationMetadata,
    PresentationStatus,
    SlideData,
)


@pytest.fixture
def valid_event():
    """Valid API Gateway event"""
    return {
        "body": json.dumps(
            {
                "presentation_id": "test-presentation-123",
                "session_id": "test-session-456",
                "template_id": "template-001",
                "style": "professional",
                "include_speaker_notes": True,
                "include_images": True,
                "include_charts": True,
                "output_format": "pptx",
            }
        ),
        "headers": {"Content-Type": "application/json"},
        "requestContext": {"requestId": "test-request-id"},
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.request_id = "test-request-id"
    context.function_name = "compile-pptx"
    context.memory_limit_in_mb = "512"
    context.invoked_function_arn = (
        "arn:aws:lambda:us-west-2:123456789:function:compile-pptx"
    )
    return context


@pytest.fixture
def sample_presentation_metadata():
    """Sample presentation metadata"""
    return PresentationMetadata(
        presentation_id="test-presentation-123",
        session_id="test-session-456",
        title="Test Presentation",
        status=PresentationStatus.CREATED.value,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        duration_minutes=20,
        owner="Test User",
    )


@pytest.fixture
def sample_slides():
    """Sample slide data"""
    return [
        SlideData(
            slide_number=1,
            title="Introduction",
            content="Welcome to the presentation",
            layout_type="title",
            images=[],
            charts=[],
        ),
        SlideData(
            slide_number=2,
            title="Main Content",
            content="• Point 1\n• Point 2\n• Point 3",
            layout_type="content",
            images=[{"url": "https://example.com/image.jpg"}],
            charts=[],
        ),
        SlideData(
            slide_number=3,
            title="Data Analysis",
            content="Chart showing trends",
            layout_type="chart",
            images=[],
            charts=[
                {
                    "type": "column",
                    "data": {"Q1": 100, "Q2": 150, "Q3": 120},
                    "title": "Quarterly Results",
                }
            ],
        ),
        SlideData(
            slide_number=4,
            title="Thank You",
            content="Questions?",
            layout_type="closing",
            images=[],
            charts=[],
        ),
    ]


@pytest.fixture
def sample_speaker_notes():
    """Sample speaker notes data"""
    return {
        "speaker_notes": [
            {
                "slide_number": 1,
                "detailed_notes": "Welcome everyone to this presentation",
            },
            {
                "slide_number": 2,
                "detailed_notes": "These are the main points to discuss",
            },
        ]
    }


@pytest.fixture
def mock_compiler():
    """Create a mock PresentationCompiler"""
    compiler = PresentationCompiler()
    compiler.model = Mock()
    compiler.view = Mock()
    return compiler


class TestCompileRequest:
    """Test request validation"""

    def test_valid_request(self):
        """Test valid request creation"""
        request = CompileRequest(presentation_id="test-123", style="professional")
        assert request.presentation_id == "test-123"
        assert request.style == "professional"
        assert request.include_speaker_notes is True  # default

    def test_invalid_style(self):
        """Test style validation"""
        with pytest.raises(ValueError):
            CompileRequest(presentation_id="test-123", style="invalid_style")

    def test_invalid_format(self):
        """Test output format validation"""
        with pytest.raises(ValueError):
            CompileRequest(
                presentation_id="test-123", output_format="pdf"
            )  # Not supported yet

    def test_optional_fields(self):
        """Test optional field defaults"""
        request = CompileRequest(presentation_id="test-123")
        assert request.template_id is None
        assert request.session_id is None
        assert request.include_images is True
        assert request.include_charts is True


class TestPresentationCompiler:
    """Test PresentationCompiler class"""

    @patch("compile_pptx.create_styled_presentation")
    def test_compile_presentation_success(
        self,
        mock_create_view,
        mock_compiler,
        sample_presentation_metadata,
        sample_slides,
    ):
        """Test successful presentation compilation"""
        # Setup mocks
        mock_compiler.model.get_presentation_record.return_value = (
            sample_presentation_metadata
        )
        mock_compiler.model.get_template.return_value = (b"template_data", Mock())
        mock_compiler.model.get_slide_content.return_value = sample_slides
        mock_compiler.model.save_presentation_to_s3.return_value = (
            "s3://bucket/key.pptx",
            "https://download.url",
        )

        mock_view = Mock()
        mock_view.save_presentation.return_value = b"presentation_data"
        mock_view.get_slide_count.return_value = 4
        mock_create_view.return_value = mock_view
        mock_compiler.view = mock_view

        # Create request
        request = CompileRequest(
            presentation_id="test-presentation-123", template_id="template-001"
        )

        # Compile
        response = mock_compiler.compile_presentation(request)

        # Assertions
        assert response.success is True
        assert response.presentation_id == "test-presentation-123"
        assert response.slide_count == 4
        assert response.download_url == "https://download.url"

        # Verify method calls
        mock_compiler.model.update_presentation_status.assert_called()
        mock_view.save_presentation.assert_called_once()

    def test_compile_presentation_not_found(self, mock_compiler):
        """Test compilation with non-existent presentation"""
        mock_compiler.model.get_presentation_record.return_value = None

        request = CompileRequest(presentation_id="non-existent")

        response = mock_compiler.compile_presentation(request)

        assert response.success is False
        assert "not found" in response.error.lower()

    @patch("compile_pptx.s3")
    def test_get_speaker_notes_success(
        self, mock_s3, mock_compiler, sample_speaker_notes
    ):
        """Test retrieving speaker notes"""
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(sample_speaker_notes).encode())
        }

        notes = mock_compiler._get_speaker_notes("test-presentation-123")

        assert 1 in notes
        assert 2 in notes
        assert notes[1] == "Welcome everyone to this presentation"

    @patch("compile_pptx.s3")
    def test_get_speaker_notes_not_found(self, mock_s3, mock_compiler):
        """Test speaker notes not found"""
        from botocore.exceptions import ClientError

        mock_s3.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )

        notes = mock_compiler._get_speaker_notes("test-presentation-123")

        assert notes == {}


class TestImageDownloading:
    """Test image downloading functionality"""

    @patch("requests.get")
    def test_download_image_http(self, mock_get, mock_compiler):
        """Test downloading image from HTTP URL"""
        mock_response = Mock()
        mock_response.content = b"image_data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        image_data = mock_compiler._download_image("https://example.com/image.jpg")

        assert image_data == b"image_data"
        mock_get.assert_called_once()

    @patch("compile_pptx.s3")
    def test_download_image_s3(self, mock_s3, mock_compiler):
        """Test downloading image from S3"""
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"s3_image_data")
        }

        image_data = mock_compiler._download_image("s3://bucket/path/image.jpg")

        assert image_data == b"s3_image_data"
        mock_s3.get_object.assert_called_once()

    def test_download_image_cached(self, mock_compiler):
        """Test image caching"""
        mock_compiler.image_cache["test_url"] = b"cached_data"

        image_data = mock_compiler._download_image("test_url")

        assert image_data == b"cached_data"

    @patch("requests.get")
    def test_download_images_parallel(self, mock_get, mock_compiler, sample_slides):
        """Test parallel image downloading"""
        mock_response = Mock()
        mock_response.content = b"image_data"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        images = mock_compiler._download_images_parallel(sample_slides)

        assert 2 in images  # Slide 2 has an image
        assert len(images[2]) == 1
        assert images[2][0] == b"image_data"


class TestPresentationBuilding:
    """Test presentation building functionality"""

    def test_build_presentation(
        self,
        mock_compiler,
        sample_presentation_metadata,
        sample_slides,
        sample_speaker_notes,
    ):
        """Test building presentation from components"""
        mock_view = Mock()
        mock_compiler.view = mock_view

        speaker_notes = {1: "Notes for slide 1", 2: "Notes for slide 2"}
        images = {2: [b"image_data"]}

        mock_compiler._build_presentation(
            sample_presentation_metadata,
            sample_slides,
            speaker_notes,
            images,
            include_charts=True,
        )

        # Verify title slide was added
        mock_view.add_title_slide.assert_called_once()

        # Verify speaker notes were added
        assert mock_view.add_speaker_notes.call_count >= 2

    def test_parse_content_points_numbered(self, mock_compiler):
        """Test parsing numbered list content"""
        content = "1. First point\n2. Second point\n3. Third point"

        points = mock_compiler._parse_content_points(content)

        assert len(points) == 3
        assert "First point" in points[0]
        assert "Second point" in points[1]

    def test_parse_content_points_bullets(self, mock_compiler):
        """Test parsing bullet point content"""
        content = "• First point\n• Second point\n• Third point"

        points = mock_compiler._parse_content_points(content)

        assert len(points) == 3
        assert "First point" in points[0]

    def test_parse_content_points_plain(self, mock_compiler):
        """Test parsing plain text content"""
        content = "First line\nSecond line\nThird line"

        points = mock_compiler._parse_content_points(content)

        assert len(points) == 3
        assert points[0] == "First line"


class TestSlideTypeHandling:
    """Test different slide type handling"""

    def test_add_title_slide(self, mock_compiler):
        """Test adding title slide"""
        mock_view = Mock()
        mock_compiler.view = mock_view

        slide = SlideData(
            slide_number=1, title="Title", content="Subtitle", layout_type="title"
        )

        mock_compiler._add_title_slide(slide)

        mock_view.add_title_slide.assert_called_once_with(
            title="Title", subtitle="Subtitle"
        )

    def test_add_section_slide(self, mock_compiler):
        """Test adding section slide"""
        mock_view = Mock()
        mock_compiler.view = mock_view

        slide = SlideData(
            slide_number=2,
            title="Section Title",
            content="Section subtitle",
            layout_type="section",
        )

        mock_compiler._add_section_slide(slide)

        mock_view.add_section_slide.assert_called_once()

    def test_add_chart_slide(self, mock_compiler):
        """Test adding chart slide"""
        mock_view = Mock()
        mock_compiler.view = mock_view

        slide = SlideData(
            slide_number=3,
            title="Chart",
            content="",
            layout_type="chart",
            charts=[{"type": "bar", "data": {"A": 10, "B": 20}, "title": "Test Chart"}],
        )

        mock_compiler._add_chart_slide(slide)

        mock_view.add_chart_slide.assert_called_once()

    def test_add_closing_slide(self, mock_compiler):
        """Test adding closing slide"""
        mock_view = Mock()
        mock_compiler.view = mock_view

        slide = SlideData(
            slide_number=10,
            title="Thank You",
            content="Questions?",
            layout_type="closing",
            metadata={"contact_info": {"Email": "test@example.com"}},
        )

        mock_compiler._add_closing_slide(slide)

        mock_view.add_closing_slide.assert_called_once()


class TestLambdaHandler:
    """Test Lambda handler"""

    @patch("compile_pptx.PresentationCompiler")
    def test_successful_compilation(
        self, mock_compiler_class, valid_event, lambda_context
    ):
        """Test successful Lambda execution"""
        mock_compiler = Mock()
        mock_response = CompileResponse(
            success=True,
            presentation_id="test-presentation-123",
            download_url="https://download.url",
            s3_key="s3://bucket/key",
            file_size=1000000,
            slide_count=10,
            generation_time_ms=5000,
            message="Success",
        )
        mock_compiler.compile_presentation.return_value = mock_response
        mock_compiler_class.return_value = mock_compiler

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["presentation_id"] == "test-presentation-123"

    def test_invalid_request(self, lambda_context):
        """Test invalid request handling"""
        event = {
            "body": json.dumps(
                {"presentation_id": "test-123", "style": "invalid_style"}
            )
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "Invalid request" in body["error"]

    @patch("compile_pptx.PresentationCompiler")
    def test_compilation_failure(
        self, mock_compiler_class, valid_event, lambda_context
    ):
        """Test compilation failure handling"""
        mock_compiler = Mock()
        mock_response = CompileResponse(
            success=False,
            presentation_id="test-presentation-123",
            message="Compilation failed",
            error="Some error occurred",
            generation_time_ms=1000,
        )
        mock_compiler.compile_presentation.return_value = mock_response
        mock_compiler_class.return_value = mock_compiler

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body

    def test_cors_headers(self, valid_event, lambda_context):
        """Test CORS headers in response"""
        response = lambda_handler(valid_event, lambda_context)

        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert response["headers"]["Content-Type"] == "application/json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
