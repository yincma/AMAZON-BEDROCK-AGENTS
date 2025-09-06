"""
Common Data Structures for Presentation Services
Shared data classes used across interfaces and implementations
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TemplateCategory(Enum):
    """Template category enumeration"""

    BUSINESS = "business"
    ACADEMIC = "academic"
    CREATIVE = "creative"
    MINIMALIST = "minimalist"
    TECHNICAL = "technical"
    DEFAULT = "default"


class PresentationStatus(Enum):
    """Status values for presentations"""

    CREATED = "created"
    GENERATING_OUTLINE = "generating_outline"
    GENERATING_CONTENT = "generating_content"
    GENERATING_IMAGES = "generating_images"
    GENERATING_SPEAKER_NOTES = "generating_speaker_notes"
    COMPILING = "compiling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PresentationMetadata:
    """Metadata for a presentation"""

    presentation_id: str
    session_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: str = PresentationStatus.CREATED.value
    template_id: Optional[str] = None
    style: Optional[str] = "professional"
    slide_count: int = 0
    file_size: int = 0
    s3_key: Optional[str] = None
    download_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SlideData:
    """Data structure for individual slide content"""

    slide_number: int
    title: str
    content: str
    notes: Optional[str] = None
    layout: str = "title_content"
    images: Optional[List[Dict[str, Any]]] = None
    charts: Optional[List[Dict[str, Any]]] = None


@dataclass
class TemplateMetadata:
    """Metadata for presentation templates"""

    template_id: str
    name: str
    description: str
    category: str = "professional"
    file_size: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: str = "1.0"
    tags: Optional[List[str]] = None
    s3_key: str = ""
    thumbnail_url: Optional[str] = None
    color_scheme: Optional[Dict[str, Any]] = None
    slide_layouts: Optional[List[str]] = None
    font_family: Optional[str] = None
