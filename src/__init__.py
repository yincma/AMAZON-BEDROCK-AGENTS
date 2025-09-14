"""
AI-PPT-Assistant 内容生成模块
"""

from .content_generator import ContentGenerator, generate_outline, generate_slide_content, generate_and_save_content
from .content_validator import (
    validate_content_format,
    validate_content_length,
    check_content_coherence,
    validate_content_quality,
    validate_speaker_notes,
    validate_complete_presentation
)
from .config import *

__all__ = [
    'ContentGenerator',
    'generate_outline',
    'generate_slide_content',
    'generate_and_save_content',
    'validate_content_format',
    'validate_content_length',
    'check_content_coherence',
    'validate_content_quality',
    'validate_speaker_notes',
    'validate_complete_presentation'
]

__version__ = '1.0.0'