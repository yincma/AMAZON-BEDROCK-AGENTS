"""
Presentation View Interface - Abstract Rendering Layer
Defines the contract for presentation rendering and styling operations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Import concrete data structures
from views.presentation_styles import SlideStyle


class IPresentationRenderer(ABC):
    """Interface for basic presentation rendering operations"""

    @abstractmethod
    def initialize_presentation(
        self, template_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize a new presentation with optional template"""

    @abstractmethod
    def save_presentation(self) -> bytes:
        """Save presentation and return binary data"""

    @abstractmethod
    def get_slide_count(self) -> int:
        """Get number of slides in presentation"""

    @abstractmethod
    def clear_presentation(self) -> None:
        """Clear all slides and reset presentation"""


class ISlideCreator(ABC):
    """Interface for creating different types of slides"""

    @abstractmethod
    def add_title_slide(
        self,
        title: str,
        subtitle: Optional[str] = None,
        author: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Any:
        """Add a title slide to the presentation"""

    @abstractmethod
    def add_content_slide(
        self, title: str, content: List[str], slide_number: Optional[int] = None
    ) -> Any:
        """Add a content slide with bullet points"""

    @abstractmethod
    def add_section_slide(self, title: str, subtitle: Optional[str] = None) -> Any:
        """Add a section divider slide"""

    @abstractmethod
    def add_two_content_slide(
        self, title: str, left_content: List[str], right_content: List[str]
    ) -> Any:
        """Add a two-column content slide"""

    @abstractmethod
    def add_image_slide(
        self,
        title: str,
        image_data: bytes,
        caption: Optional[str] = None,
        layout: str = "center",
    ) -> Any:
        """Add a slide with an image"""

    @abstractmethod
    def add_chart_slide(
        self,
        title: str,
        chart_type: str,
        data: Dict[str, Any],
        chart_title: Optional[str] = None,
    ) -> Any:
        """Add a slide with a chart"""

    @abstractmethod
    def add_closing_slide(
        self,
        title: str = "Thank You",
        contact_info: Optional[Dict[str, str]] = None,
        additional_text: Optional[str] = None,
    ) -> Any:
        """Add a closing slide"""


class ISlideStyler(ABC):
    """Interface for styling slides and presentation elements"""

    @abstractmethod
    def apply_slide_style(self, slide: Any, style: SlideStyle) -> None:
        """Apply style to a specific slide"""

    @abstractmethod
    def set_color_scheme(self, color_scheme: Dict[str, Any]) -> None:
        """Set color scheme for the presentation"""

    @abstractmethod
    def apply_font_styling(
        self,
        element: Any,
        font_name: str,
        font_size: int,
        color: Optional[Any] = None,
        bold: bool = False,
        italic: bool = False,
    ) -> None:
        """Apply font styling to text element"""

    @abstractmethod
    def set_slide_background(
        self, slide: Any, background_type: str, background_data: Any
    ) -> None:
        """Set slide background (color, image, gradient)"""


class ISlideEnhancer(ABC):
    """Interface for adding enhancements to slides"""

    @abstractmethod
    def add_speaker_notes(self, slide: Any, notes: str) -> None:
        """Add speaker notes to a slide"""

    @abstractmethod
    def add_transition_effect(
        self, slide: Any, effect_type: str, duration: float = 0.5
    ) -> None:
        """Add transition effect to slide"""

    @abstractmethod
    def add_animation(
        self,
        element: Any,
        animation_type: str,
        trigger: str = "click",
        delay: float = 0.0,
    ) -> None:
        """Add animation to slide element"""

    @abstractmethod
    def add_hyperlink(
        self, element: Any, url: str, tooltip: Optional[str] = None
    ) -> None:
        """Add hyperlink to slide element"""


class IPresentationView(
    IPresentationRenderer, ISlideCreator, ISlideStyler, ISlideEnhancer
):
    """Complete interface for presentation view operations"""

    @abstractmethod
    def set_presentation_properties(
        self,
        title: str,
        author: Optional[str] = None,
        subject: Optional[str] = None,
        category: Optional[str] = None,
    ) -> None:
        """Set presentation metadata properties"""

    @abstractmethod
    def duplicate_slide(self, slide_index: int) -> Any:
        """Duplicate a slide at given index"""

    @abstractmethod
    def delete_slide(self, slide_index: int) -> None:
        """Delete slide at given index"""

    @abstractmethod
    def reorder_slides(self, from_index: int, to_index: int) -> None:
        """Move slide from one position to another"""

    @abstractmethod
    def get_slide_by_index(self, index: int) -> Any:
        """Get slide object by index"""

    @abstractmethod
    def export_slide_as_image(
        self,
        slide_index: int,
        format: str = "PNG",
        width: int = 1920,
        height: int = 1080,
    ) -> bytes:
        """Export specific slide as image"""


class IPresentationTemplate(ABC):
    """Interface for template management"""

    @abstractmethod
    def load_template(self, template_data: Dict[str, Any]) -> None:
        """Load template configuration"""

    @abstractmethod
    def apply_template_to_slide(self, slide: Any, layout_type: str) -> None:
        """Apply template layout to specific slide"""

    @abstractmethod
    def get_template_layouts(self) -> List[str]:
        """Get available template layout types"""

    @abstractmethod
    def customize_template(self, modifications: Dict[str, Any]) -> None:
        """Apply customizations to current template"""


class IPresentationValidator(ABC):
    """Interface for presentation validation"""

    @abstractmethod
    def validate_slide_content(self, slide: Any) -> bool:
        """Validate slide content and structure"""

    @abstractmethod
    def validate_presentation_structure(self) -> bool:
        """Validate overall presentation structure"""

    @abstractmethod
    def get_validation_warnings(self) -> List[str]:
        """Get list of validation warnings"""

    @abstractmethod
    def get_accessibility_report(self) -> Dict[str, Any]:
        """Generate accessibility compliance report"""


# Factory interface for creating view instances
class IPresentationViewFactory(ABC):
    """Factory interface for creating view instances"""

    @abstractmethod
    def create_view(self, style: str, **config) -> IPresentationView:
        """Create a presentation view instance"""

    @abstractmethod
    def create_template_manager(self, **config) -> IPresentationTemplate:
        """Create a template manager instance"""

    @abstractmethod
    def create_validator(self, **config) -> IPresentationValidator:
        """Create a presentation validator instance"""

    @abstractmethod
    def get_supported_styles(self) -> List[str]:
        """Get list of supported presentation styles"""
