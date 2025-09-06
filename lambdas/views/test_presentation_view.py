"""
Unit tests for Presentation View
"""

# Mock pptx module before importing presentation_view
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.modules["pptx"] = MagicMock()
sys.modules["pptx.util"] = MagicMock()
sys.modules["pptx.enum.text"] = MagicMock()
sys.modules["pptx.enum.shapes"] = MagicMock()
sys.modules["pptx.dml.color"] = MagicMock()
sys.modules["pptx.chart.data"] = MagicMock()
sys.modules["pptx.enum.chart"] = MagicMock()

from presentation_view import (
    ColorScheme,
    PresentationView,
    SlideLayout,
    SlideStyle,
    create_styled_presentation,
)


@pytest.fixture
def mock_presentation():
    """Create a mock Presentation object"""
    mock_pres = Mock()
    mock_pres.slides = Mock()
    mock_pres.slides.add_slide = Mock(return_value=Mock())
    mock_pres.slide_layouts = [Mock() for _ in range(9)]
    mock_pres.save = Mock()
    return mock_pres


@pytest.fixture
def presentation_view(mock_presentation):
    """Create a PresentationView instance with mocked presentation"""
    with patch("presentation_view.Presentation", return_value=mock_presentation):
        view = PresentationView()
    return view


@pytest.fixture
def sample_style():
    """Sample slide style"""
    return SlideStyle(
        title_font="Arial",
        title_size=48,
        content_font="Arial",
        content_size=20,
        color_scheme=ColorScheme.PROFESSIONAL,
    )


@pytest.fixture
def sample_slide():
    """Mock slide object"""
    slide = Mock()
    slide.shapes = Mock()
    slide.shapes.title = Mock()
    slide.shapes.title.text = ""
    slide.shapes.title.text_frame = Mock()
    slide.placeholders = [Mock(), Mock()]
    slide.notes_slide = Mock()
    slide.notes_slide.notes_text_frame = Mock()
    return slide


class TestPresentationViewInitialization:
    """Test PresentationView initialization"""

    def test_init_without_template(self):
        """Test initialization without template"""
        with patch("presentation_view.Presentation") as mock_pres_class:
            view = PresentationView()
            mock_pres_class.assert_called_once_with()
            assert view.style is not None

    def test_init_with_template(self):
        """Test initialization with template file"""
        with patch("os.path.exists", return_value=True):
            with patch("presentation_view.Presentation") as mock_pres_class:
                PresentationView(template_path="/path/to/template.pptx")
                mock_pres_class.assert_called_once_with("/path/to/template.pptx")

    def test_set_style(self, presentation_view, sample_style):
        """Test setting presentation style"""
        presentation_view.set_style(sample_style)
        assert presentation_view.style == sample_style


class TestTitleSlide:
    """Test title slide creation"""

    def test_add_title_slide_basic(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding basic title slide"""
        mock_presentation.slides.add_slide.return_value = sample_slide

        slide = presentation_view.add_title_slide(
            title="Test Presentation", subtitle="Test Subtitle"
        )

        assert slide == sample_slide
        mock_presentation.slides.add_slide.assert_called_once()
        assert sample_slide.shapes.title.text == "Test Presentation"

    def test_add_title_slide_with_author_date(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding title slide with author and date"""
        mock_presentation.slides.add_slide.return_value = sample_slide

        slide = presentation_view.add_title_slide(
            title="Test Presentation",
            subtitle="Subtitle",
            author="John Doe",
            date="2024-01-01",
        )

        assert slide == sample_slide
        # Check subtitle placeholder was set
        assert "John Doe" in sample_slide.placeholders[1].text
        assert "2024-01-01" in sample_slide.placeholders[1].text


class TestContentSlide:
    """Test content slide creation"""

    def test_add_content_slide(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding content slide with bullet points"""
        mock_presentation.slides.add_slide.return_value = sample_slide

        # Add mock content shape
        content_shape = Mock()
        content_shape.has_text_frame = True
        content_shape.text_frame = Mock()
        content_shape.text_frame.paragraphs = [Mock()]
        content_shape.text_frame.add_paragraph = Mock(return_value=Mock())
        sample_slide.shapes.__iter__ = Mock(
            return_value=iter([sample_slide.shapes.title, content_shape])
        )

        content = ["Point 1", "Point 2", "Point 3"]
        slide = presentation_view.add_content_slide(
            title="Content Slide", content=content
        )

        assert slide == sample_slide
        assert sample_slide.shapes.title.text == "Content Slide"

    def test_add_content_slide_with_number(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding content slide with slide number"""
        mock_presentation.slides.add_slide.return_value = sample_slide

        presentation_view.add_content_slide(
            title="Content", content=["Item 1"], slide_number=5
        )

        assert "5. Content" in sample_slide.shapes.title.text


class TestTwoContentSlide:
    """Test two-column content slide"""

    def test_add_two_content_slide(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding two-content slide"""
        mock_presentation.slides.add_slide.return_value = sample_slide

        # Create mock placeholders
        left_shape = Mock()
        left_shape.has_text_frame = True
        left_shape.text_frame = Mock()

        right_shape = Mock()
        right_shape.has_text_frame = True
        right_shape.text_frame = Mock()

        sample_slide.shapes.__iter__ = Mock(
            return_value=iter([sample_slide.shapes.title, left_shape, right_shape])
        )

        slide = presentation_view.add_two_content_slide(
            title="Comparison",
            left_content=["Left 1", "Left 2"],
            right_content=["Right 1", "Right 2"],
            left_title="Option A",
            right_title="Option B",
        )

        assert slide == sample_slide
        assert sample_slide.shapes.title.text == "Comparison"


class TestImageSlide:
    """Test image slide creation"""

    def test_add_image_slide_center(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding centered image slide"""
        mock_presentation.slides.add_slide.return_value = sample_slide
        sample_slide.shapes.add_picture = Mock(return_value=Mock())
        sample_slide.shapes.add_textbox = Mock(return_value=Mock())

        image_data = b"fake_image_data"
        slide = presentation_view.add_image_slide(
            title="Image Slide",
            image_data=image_data,
            caption="Test Caption",
            layout="center",
        )

        assert slide == sample_slide
        sample_slide.shapes.add_picture.assert_called_once()
        # Verify caption was added
        sample_slide.shapes.add_textbox.assert_called_once()

    def test_add_image_slide_left(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding left-aligned image slide"""
        mock_presentation.slides.add_slide.return_value = sample_slide
        sample_slide.shapes.add_picture = Mock(return_value=Mock())

        image_data = b"fake_image_data"
        slide = presentation_view.add_image_slide(
            title="Image Left", image_data=image_data, layout="left"
        )

        assert slide == sample_slide
        sample_slide.shapes.add_picture.assert_called_once()


class TestChartSlide:
    """Test chart slide creation"""

    def test_add_chart_slide_simple(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding simple chart slide"""
        mock_presentation.slides.add_slide.return_value = sample_slide
        mock_chart = Mock()
        mock_chart.chart = Mock()
        sample_slide.shapes.add_chart = Mock(return_value=mock_chart)

        data = {"Q1": 100, "Q2": 150, "Q3": 120, "Q4": 180}
        slide = presentation_view.add_chart_slide(
            title="Sales Chart",
            chart_type="column",
            data=data,
            chart_title="Quarterly Sales",
        )

        assert slide == sample_slide
        sample_slide.shapes.add_chart.assert_called_once()

    def test_add_chart_slide_complex(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding complex chart with categories and series"""
        mock_presentation.slides.add_slide.return_value = sample_slide
        mock_chart = Mock()
        mock_chart.chart = Mock()
        sample_slide.shapes.add_chart = Mock(return_value=mock_chart)

        data = {
            "categories": ["Q1", "Q2", "Q3", "Q4"],
            "series": {
                "Product A": [100, 120, 140, 160],
                "Product B": [80, 90, 100, 110],
            },
        }

        slide = presentation_view.add_chart_slide(
            title="Product Comparison", chart_type="line", data=data
        )

        assert slide == sample_slide
        sample_slide.shapes.add_chart.assert_called_once()


class TestSectionSlide:
    """Test section divider slide"""

    def test_add_section_slide(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding section slide"""
        mock_presentation.slides.add_slide.return_value = sample_slide

        # Add subtitle shape
        subtitle_shape = Mock()
        subtitle_shape.has_text_frame = True
        subtitle_shape.text_frame = Mock()
        sample_slide.shapes.__iter__ = Mock(
            return_value=iter([sample_slide.shapes.title, subtitle_shape])
        )

        slide = presentation_view.add_section_slide(
            title="Section 2", subtitle="Advanced Topics"
        )

        assert slide == sample_slide
        assert sample_slide.shapes.title.text == "Section 2"
        assert subtitle_shape.text == "Advanced Topics"


class TestClosingSlide:
    """Test closing/thank you slide"""

    def test_add_closing_slide_basic(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding basic closing slide"""
        mock_presentation.slides.add_slide.return_value = sample_slide
        sample_slide.shapes.add_textbox = Mock(return_value=Mock())

        slide = presentation_view.add_closing_slide()

        assert slide == sample_slide
        assert sample_slide.shapes.title.text == "Thank You"

    def test_add_closing_slide_with_contact(
        self, presentation_view, mock_presentation, sample_slide
    ):
        """Test adding closing slide with contact info"""
        mock_presentation.slides.add_slide.return_value = sample_slide
        textbox = Mock()
        textbox.text_frame = Mock()
        textbox.text_frame.paragraphs = [Mock()]
        textbox.text_frame.add_paragraph = Mock(return_value=Mock())
        sample_slide.shapes.add_textbox = Mock(return_value=textbox)

        contact_info = {"Email": "test@example.com", "Phone": "+1-234-567-8900"}

        slide = presentation_view.add_closing_slide(
            title="Questions?",
            contact_info=contact_info,
            additional_text="Feel free to reach out!",
        )

        assert slide == sample_slide
        sample_slide.shapes.add_textbox.assert_called_once()


class TestSpeakerNotes:
    """Test speaker notes functionality"""

    def test_add_speaker_notes(self, presentation_view, sample_slide):
        """Test adding speaker notes to slide"""
        notes = "These are the speaker notes for this slide."
        presentation_view.add_speaker_notes(sample_slide, notes)

        assert sample_slide.notes_slide.notes_text_frame.text == notes


class TestSavePresentation:
    """Test presentation saving"""

    def test_save_presentation_as_bytes(self, presentation_view, mock_presentation):
        """Test saving presentation as bytes"""
        mock_presentation.save = Mock()

        result = presentation_view.save_presentation()

        assert isinstance(result, bytes)
        mock_presentation.save.assert_called_once()

    def test_save_presentation_to_file(self, presentation_view, mock_presentation):
        """Test saving presentation to file"""
        mock_presentation.save = Mock()

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            result = presentation_view.save_presentation("/path/to/output.pptx")

            assert isinstance(result, bytes)
            mock_open.assert_called_once_with("/path/to/output.pptx", "wb")


class TestHelperMethods:
    """Test helper methods"""

    def test_get_slide_count(self, presentation_view, mock_presentation):
        """Test getting slide count"""
        mock_presentation.slides.__len__ = Mock(return_value=5)

        count = presentation_view.get_slide_count()

        assert count == 5

    def test_apply_template(self, presentation_view):
        """Test applying template from bytes"""
        template_data = b"template_bytes"

        with patch("presentation_view.Presentation") as mock_pres_class:
            mock_template = Mock()
            mock_pres_class.return_value = mock_template

            presentation_view.apply_template(template_data)

            assert presentation_view.presentation == mock_template


class TestStyledPresentation:
    """Test styled presentation creation"""

    def test_create_styled_presentation_professional(self):
        """Test creating professional styled presentation"""
        with patch("presentation_view.Presentation"):
            view = create_styled_presentation("professional")

            assert view is not None
            assert view.style.color_scheme == ColorScheme.PROFESSIONAL

    def test_create_styled_presentation_creative(self):
        """Test creating creative styled presentation"""
        with patch("presentation_view.Presentation"):
            view = create_styled_presentation("creative")

            assert view.style.color_scheme == ColorScheme.CREATIVE

    def test_create_styled_presentation_with_template(self):
        """Test creating styled presentation with template"""
        template_data = b"template_data"

        with patch("presentation_view.Presentation"):
            with patch.object(PresentationView, "apply_template") as mock_apply:
                view = create_styled_presentation("minimalist", template_data)

                mock_apply.assert_called_once_with(template_data)
                assert view.style.color_scheme == ColorScheme.MINIMALIST


class TestColorSchemes:
    """Test color scheme definitions"""

    def test_professional_color_scheme(self):
        """Test professional color scheme"""
        assert hasattr(ColorScheme, "PROFESSIONAL")
        assert "primary" in ColorScheme.PROFESSIONAL
        assert "secondary" in ColorScheme.PROFESSIONAL
        assert "accent" in ColorScheme.PROFESSIONAL
        assert "background" in ColorScheme.PROFESSIONAL
        assert "text" in ColorScheme.PROFESSIONAL

    def test_all_color_schemes_exist(self):
        """Test all color schemes are defined"""
        schemes = ["PROFESSIONAL", "CREATIVE", "MINIMALIST", "TECHNICAL"]
        for scheme in schemes:
            assert hasattr(ColorScheme, scheme)


class TestSlideLayouts:
    """Test slide layout enum"""

    def test_slide_layout_values(self):
        """Test slide layout enum values"""
        assert SlideLayout.TITLE.value == 0
        assert SlideLayout.CONTENT.value == 1
        assert SlideLayout.SECTION.value == 2
        assert SlideLayout.TWO_CONTENT.value == 3
        assert SlideLayout.BLANK.value == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
