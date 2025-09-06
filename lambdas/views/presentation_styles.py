"""
Presentation Styles and Color Schemes
Common styling definitions used across view components
"""

from dataclasses import dataclass
from typing import Dict

from pptx.dml.color import RGBColor


# Color schemes
class ColorScheme:
    """Predefined color schemes"""

    PROFESSIONAL = {
        "primary": RGBColor(31, 78, 121),  # Dark blue
        "secondary": RGBColor(46, 117, 182),  # Medium blue
        "accent": RGBColor(255, 192, 0),  # Gold
        "background": RGBColor(255, 255, 255),  # White
        "text": RGBColor(51, 51, 51),  # Dark gray
    }

    CREATIVE = {
        "primary": RGBColor(132, 60, 153),  # Purple
        "secondary": RGBColor(255, 87, 127),  # Pink
        "accent": RGBColor(255, 195, 0),  # Yellow
        "background": RGBColor(245, 245, 247),  # Light gray
        "text": RGBColor(36, 36, 36),  # Dark gray
    }

    MINIMALIST = {
        "primary": RGBColor(0, 0, 0),  # Black
        "secondary": RGBColor(128, 128, 128),  # Gray
        "accent": RGBColor(255, 255, 255),  # White
        "background": RGBColor(255, 255, 255),  # White
        "text": RGBColor(0, 0, 0),  # Black
    }

    TECHNICAL = {
        "primary": RGBColor(0, 123, 255),  # Blue
        "secondary": RGBColor(52, 199, 89),  # Green
        "accent": RGBColor(255, 149, 0),  # Orange
        "background": RGBColor(28, 28, 30),  # Dark
        "text": RGBColor(255, 255, 255),  # White
    }


@dataclass
class SlideStyle:
    """Style configuration for slides"""

    title_font: str = "Calibri"
    title_size: int = 44
    subtitle_font: str = "Calibri Light"
    subtitle_size: int = 32
    content_font: str = "Calibri"
    content_size: int = 18
    bullet_font: str = "Calibri"
    bullet_size: int = 16
    color_scheme: Dict[str, RGBColor] = None

    def __post_init__(self):
        if self.color_scheme is None:
            self.color_scheme = ColorScheme.PROFESSIONAL
