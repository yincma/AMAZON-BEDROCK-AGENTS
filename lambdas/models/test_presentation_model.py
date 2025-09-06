"""
Unit tests for Presentation Model
"""

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Set environment variables before importing
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["TEMPLATES_BUCKET"] = "test-templates-bucket"
os.environ["SESSIONS_TABLE"] = "test-sessions-table"
os.environ["CACHE_TTL_SECONDS"] = "3600"
os.environ["MAX_TEMPLATE_SIZE_MB"] = "50"

from data_structures import (
    PresentationMetadata,
    PresentationStatus,
    SlideData,
    TemplateCategory,
    TemplateMetadata,
)
from presentation_model import (
    PresentationModel,
    presentation_model,
)


@pytest.fixture
def model():
    """Create a fresh PresentationModel instance"""
    return PresentationModel()


@pytest.fixture
def sample_template_metadata():
    """Sample template metadata"""
    return TemplateMetadata(
        template_id="template_001",
        name="Business Template",
        category=TemplateCategory.BUSINESS.value,
        description="Professional business template",
        s3_key="templates/business/template_001.pptx",
        file_size=1024000,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        tags=["business", "professional"],
        slide_layouts=["title", "content", "two_column"],
    )


@pytest.fixture
def sample_presentation_metadata():
    """Sample presentation metadata"""
    return PresentationMetadata(
        presentation_id="pres_001",
        session_id="session_001",
        title="Test Presentation",
        status=PresentationStatus.CREATED.value,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        template_id="template_001",
        slide_count=10,
        language="en",
        style="professional",
    )


@pytest.fixture
def sample_slides():
    """Sample slide data"""
    return [
        SlideData(
            slide_number=1,
            title="Introduction",
            content="Welcome to the presentation",
            speaker_notes="Start with a warm greeting",
            layout_type="title",
            images=[{"url": "https://example.com/logo.png", "position": "center"}],
        ),
        SlideData(
            slide_number=2,
            title="Main Content",
            content="Key points of discussion",
            speaker_notes="Elaborate on main points",
            layout_type="content",
            charts=[{"type": "bar", "data": {"x": [1, 2, 3], "y": [10, 20, 30]}}],
        ),
    ]


@pytest.fixture
def mock_s3_response():
    """Mock S3 list_objects_v2 response"""
    return {
        "Contents": [
            {
                "Key": "templates/business/template_001.pptx",
                "Size": 1024000,
                "LastModified": datetime.now(timezone.utc),
            },
            {
                "Key": "templates/academic/template_002.pptx",
                "Size": 2048000,
                "LastModified": datetime.now(timezone.utc),
            },
        ]
    }


class TestTemplateManagement:
    """Test template management functionality"""

    @patch.object(PresentationModel, "s3")
    def test_get_template_list_success(self, mock_s3, model, mock_s3_response):
        """Test successful template listing"""
        mock_s3.list_objects_v2.return_value = mock_s3_response
        mock_s3.get_object.return_value = {
            "Body": MagicMock(
                read=lambda: json.dumps(
                    {
                        "template_id": "template_001",
                        "name": "Business Template",
                        "category": "business",
                        "tags": ["business", "professional"],
                    }
                ).encode()
            )
        }

        templates = model.get_template_list()

        assert len(templates) == 2
        assert templates[0].name == "Business Template"
        assert templates[0].category == "business"
        mock_s3.list_objects_v2.assert_called_once()

    @patch.object(PresentationModel, "s3")
    def test_get_template_list_with_category(self, mock_s3, model, mock_s3_response):
        """Test template listing with category filter"""
        filtered_response = {
            "Contents": [mock_s3_response["Contents"][0]]  # Only business template
        }
        mock_s3.list_objects_v2.return_value = filtered_response

        templates = model.get_template_list(category="business")

        assert len(templates) <= 1
        mock_s3.list_objects_v2.assert_called_with(
            Bucket="test-templates-bucket", Prefix="templates/business/", Delimiter="/"
        )

    @patch.object(PresentationModel, "s3")
    def test_get_template_list_empty(self, mock_s3, model):
        """Test template listing with no templates"""
        mock_s3.list_objects_v2.return_value = {}

        templates = model.get_template_list()

        assert templates == []

    @patch.object(PresentationModel, "get_template_list")
    @patch.object(PresentationModel, "s3")
    def test_get_template_success(
        self, mock_s3, mock_get_list, model, sample_template_metadata
    ):
        """Test successful template retrieval"""
        mock_get_list.return_value = [sample_template_metadata]
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"template_data")
        }

        data, metadata = model.get_template("template_001")

        assert data == b"template_data"
        assert metadata.template_id == "template_001"
        mock_s3.get_object.assert_called_once()

    @patch.object(PresentationModel, "get_template_list")
    def test_get_template_not_found(self, mock_get_list, model):
        """Test template retrieval with non-existent template"""
        mock_get_list.return_value = []

        with pytest.raises(ValueError, match="Template not found"):
            model.get_template("nonexistent")

    @patch.object(PresentationModel, "get_template_list")
    def test_get_template_too_large(self, mock_get_list, model):
        """Test template retrieval with oversized template"""
        large_template = TemplateMetadata(
            template_id="large_template",
            name="Large Template",
            category="business",
            s3_key="templates/large.pptx",
            file_size=100 * 1024 * 1024,  # 100MB
        )
        mock_get_list.return_value = [large_template]

        with pytest.raises(ValueError, match="Template too large"):
            model.get_template("large_template")

    def test_template_caching(self, model):
        """Test template caching mechanism"""
        template_data = (b"cached_data", sample_template_metadata())

        # Cache a template
        model._cache_template("test_id", template_data)

        assert model._is_cached("test_id")
        assert model._template_cache["test_id"] == template_data

        # Clear cache
        model.clear_cache()
        assert not model._is_cached("test_id")


class TestPresentationManagement:
    """Test presentation management functionality"""

    @patch.object(PresentationModel, "sessions_table")
    def test_create_presentation_record(self, mock_table, model):
        """Test creating presentation record"""
        mock_table.put_item.return_value = {}

        presentation = model.create_presentation_record(
            presentation_id="pres_001",
            title="Test Presentation",
            session_id="session_001",
            template_id="template_001",
        )

        assert presentation.presentation_id == "pres_001"
        assert presentation.title == "Test Presentation"
        assert presentation.status == PresentationStatus.CREATED.value
        mock_table.put_item.assert_called_once()

    @patch.object(PresentationModel, "sessions_table")
    def test_get_presentation_record_exists(
        self, mock_table, model, sample_presentation_metadata
    ):
        """Test retrieving existing presentation record"""
        mock_table.get_item.return_value = {
            "Item": asdict(sample_presentation_metadata)
        }

        presentation = model.get_presentation_record("pres_001")

        assert presentation is not None
        assert presentation.presentation_id == "pres_001"
        assert presentation.title == "Test Presentation"

    @patch.object(PresentationModel, "sessions_table")
    def test_get_presentation_record_not_found(self, mock_table, model):
        """Test retrieving non-existent presentation record"""
        mock_table.get_item.return_value = {}

        presentation = model.get_presentation_record("nonexistent")

        assert presentation is None

    @patch.object(PresentationModel, "sessions_table")
    def test_update_presentation_status(self, mock_table, model):
        """Test updating presentation status"""
        mock_table.update_item.return_value = {}

        model.update_presentation_status(
            presentation_id="pres_001",
            status=PresentationStatus.COMPLETED.value,
            s3_key="presentations/pres_001/final.pptx",
            file_size=5000000,
            slide_count=15,
        )

        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args
        assert "pres_001" in call_args[1]["Key"].values()
        assert ":status" in call_args[1]["ExpressionAttributeValues"]

    @patch.object(PresentationModel, "sessions_table")
    def test_update_presentation_status_with_error(self, mock_table, model):
        """Test updating presentation status with error message"""
        mock_table.update_item.return_value = {}

        model.update_presentation_status(
            presentation_id="pres_001",
            status=PresentationStatus.FAILED.value,
            error_message="Generation failed",
        )

        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args
        assert ":error_message" in call_args[1]["ExpressionAttributeValues"]


class TestS3Operations:
    """Test S3 file operations"""

    @patch.object(PresentationModel, "s3")
    def test_save_presentation_to_s3(self, mock_s3, model):
        """Test saving presentation to S3"""
        mock_s3.put_object.return_value = {}
        mock_s3.generate_presigned_url.return_value = "https://presigned.url"

        file_data = b"presentation_data"
        s3_key, url = model.save_presentation_to_s3("pres_001", file_data)

        assert "presentations/pres_001/" in s3_key
        assert url == "https://presigned.url"
        mock_s3.put_object.assert_called_once()
        mock_s3.generate_presigned_url.assert_called_once()

    @patch.object(PresentationModel, "s3")
    def test_get_presentation_from_s3(self, mock_s3, model):
        """Test retrieving presentation from S3"""
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"presentation_data")
        }

        data = model.get_presentation_from_s3("presentations/pres_001/file.pptx")

        assert data == b"presentation_data"
        mock_s3.get_object.assert_called_once()

    @patch.object(PresentationModel, "s3")
    def test_generate_download_url(self, mock_s3, model):
        """Test generating presigned download URL"""
        mock_s3.generate_presigned_url.return_value = "https://download.url"

        url = model.generate_download_url("presentations/pres_001/file.pptx")

        assert url == "https://download.url"
        mock_s3.generate_presigned_url.assert_called_with(
            "get_object",
            Params={
                "Bucket": "test-bucket",
                "Key": "presentations/pres_001/file.pptx",
                "ResponseContentDisposition": "attachment",
            },
            ExpiresIn=3600,
        )


class TestContentManagement:
    """Test slide content management"""

    @patch.object(PresentationModel, "s3")
    def test_save_slide_content(self, mock_s3, model, sample_slides):
        """Test saving slide content to S3"""
        mock_s3.put_object.return_value = {}

        s3_key = model.save_slide_content("pres_001", sample_slides)

        assert s3_key == "content/pres_001/slides.json"
        mock_s3.put_object.assert_called_once()

        # Verify the content structure
        call_args = mock_s3.put_object.call_args
        body = json.loads(call_args[1]["Body"])
        assert body["presentation_id"] == "pres_001"
        assert body["slide_count"] == 2
        assert len(body["slides"]) == 2

    @patch.object(PresentationModel, "s3")
    def test_get_slide_content(self, mock_s3, model, sample_slides):
        """Test retrieving slide content from S3"""
        content = {
            "presentation_id": "pres_001",
            "slides": [asdict(slide) for slide in sample_slides],
            "slide_count": len(sample_slides),
        }

        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: json.dumps(content).encode())
        }

        slides = model.get_slide_content("pres_001")

        assert len(slides) == 2
        assert slides[0].slide_number == 1
        assert slides[0].title == "Introduction"
        assert slides[1].slide_number == 2


class TestImageManagement:
    """Test image management functionality"""

    @patch.object(PresentationModel, "s3")
    def test_save_image(self, mock_s3, model):
        """Test saving image to S3"""
        mock_s3.put_object.return_value = {}

        image_data = b"image_binary_data"
        url = model.save_image("pres_001", 1, image_data, "logo.png")

        assert "images/pres_001/slide_1/logo.png" in url
        mock_s3.put_object.assert_called_once()

        # Verify content type detection
        call_args = mock_s3.put_object.call_args
        assert call_args[1]["ContentType"] == "image/png"

    @patch.object(PresentationModel, "s3")
    def test_get_image(self, mock_s3, model):
        """Test retrieving image from S3"""
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"image_data")
        }

        data = model.get_image("images/pres_001/slide_1/logo.png")

        assert data == b"image_data"
        mock_s3.get_object.assert_called_once()


class TestSessionManagement:
    """Test session management functionality"""

    @patch.object(PresentationModel, "sessions_table")
    def test_get_session_presentations(self, mock_table, model):
        """Test retrieving presentations for a session"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "presentation_id": "pres_001",
                    "session_id": "session_001",
                    "title": "Presentation 1",
                    "status": "completed",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "presentation_id": "pres_002",
                    "session_id": "session_001",
                    "title": "Presentation 2",
                    "status": "in_progress",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            ]
        }

        presentations = model.get_session_presentations("session_001")

        assert len(presentations) == 2
        assert presentations[0].presentation_id == "pres_001"
        assert presentations[1].presentation_id == "pres_002"

    @patch.object(PresentationModel, "sessions_table")
    def test_get_session_presentations_empty(self, mock_table, model):
        """Test retrieving presentations for session with no presentations"""
        mock_table.query.return_value = {"Items": []}

        presentations = model.get_session_presentations("empty_session")

        assert presentations == []


class TestUtilityMethods:
    """Test utility methods"""

    def test_generate_template_id(self, model):
        """Test template ID generation"""
        s3_key = "templates/business/template.pptx"
        template_id = model._generate_template_id(s3_key)

        assert len(template_id) == 8
        # Should be consistent
        assert template_id == model._generate_template_id(s3_key)

    def test_cache_expiry(self, model, sample_template_metadata):
        """Test cache expiry mechanism"""
        template_data = (b"data", sample_template_metadata)

        # Cache template
        model._cache_template("test_id", template_data)
        assert model._is_cached("test_id")

        # Simulate cache expiry
        model._cache_timestamps["test_id"] = (
            datetime.now(timezone.utc).timestamp() - 7200
        )  # 2 hours ago

        assert not model._is_cached("test_id")
        assert "test_id" not in model._template_cache


class TestModuleLevelInstance:
    """Test module-level instance"""

    def test_module_instance_exists(self):
        """Test that module-level instance is available"""
        assert presentation_model is not None
        assert isinstance(presentation_model, PresentationModel)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
