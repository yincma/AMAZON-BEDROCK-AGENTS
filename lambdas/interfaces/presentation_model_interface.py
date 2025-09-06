"""
Presentation Model Interface - Abstract Data Access Layer
Defines the contract for presentation data operations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

# Import data structures (these remain concrete)
from models.data_structures import (
    PresentationMetadata,
    SlideData,
    TemplateMetadata,
)


class IPresentationModelReader(ABC):
    """Interface for read operations on presentation data"""

    @abstractmethod
    def get_presentation_record(
        self, presentation_id: str
    ) -> Optional[PresentationMetadata]:
        """Retrieve presentation metadata by ID"""

    @abstractmethod
    def get_slide_content(self, presentation_id: str) -> List[SlideData]:
        """Get slide content for a presentation"""

    @abstractmethod
    def get_template(
        self, template_id: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[TemplateMetadata]]:
        """Get template data and metadata"""

    @abstractmethod
    def get_default_template(self) -> Tuple[Dict[str, Any], TemplateMetadata]:
        """Get the default template"""

    @abstractmethod
    def list_templates(self, category: Optional[str] = None) -> List[TemplateMetadata]:
        """List available templates"""


class IPresentationModelWriter(ABC):
    """Interface for write operations on presentation data"""

    @abstractmethod
    def update_presentation_status(
        self, presentation_id: str, status: str, **kwargs
    ) -> None:
        """Update presentation status and metadata"""

    @abstractmethod
    def save_presentation_to_s3(
        self, presentation_id: str, presentation_data: bytes, filename: str
    ) -> Tuple[str, str]:
        """Save presentation to S3 and return S3 key and download URL"""

    @abstractmethod
    def save_slide_data(self, presentation_id: str, slides: List[SlideData]) -> None:
        """Save slide data to storage"""


class IPresentationModel(IPresentationModelReader, IPresentationModelWriter):
    """Complete interface for presentation model operations"""

    @abstractmethod
    def create_presentation_record(
        self, presentation_id: str, metadata: PresentationMetadata
    ) -> None:
        """Create a new presentation record"""

    @abstractmethod
    def delete_presentation(self, presentation_id: str) -> None:
        """Delete presentation and associated data"""

    @abstractmethod
    def get_presentation_history(
        self, presentation_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get presentation modification history"""

    @abstractmethod
    def backup_presentation(self, presentation_id: str) -> str:
        """Create backup of presentation and return backup ID"""

    @abstractmethod
    def restore_presentation(self, presentation_id: str, backup_id: str) -> None:
        """Restore presentation from backup"""


class IPresentationCache(ABC):
    """Interface for presentation caching operations"""

    @abstractmethod
    def get_cached_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template from cache"""

    @abstractmethod
    def cache_template(
        self, template_id: str, template_data: Dict[str, Any], ttl: int = 3600
    ) -> None:
        """Cache template data"""

    @abstractmethod
    def invalidate_cache(self, key: str) -> None:
        """Invalidate cache entry"""

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear all cache entries"""


class IPresentationValidator(ABC):
    """Interface for presentation data validation"""

    @abstractmethod
    def validate_presentation_data(self, presentation_data: Dict[str, Any]) -> bool:
        """Validate presentation data structure"""

    @abstractmethod
    def validate_slide_data(self, slide_data: SlideData) -> bool:
        """Validate individual slide data"""

    @abstractmethod
    def validate_template_data(self, template_data: Dict[str, Any]) -> bool:
        """Validate template data structure"""

    @abstractmethod
    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors from last validation"""


# Factory interface for creating model instances
class IPresentationModelFactory(ABC):
    """Factory interface for creating model instances"""

    @abstractmethod
    def create_model(self, **config) -> IPresentationModel:
        """Create a presentation model instance"""

    @abstractmethod
    def create_cache(self, **config) -> IPresentationCache:
        """Create a cache instance"""

    @abstractmethod
    def create_validator(self, **config) -> IPresentationValidator:
        """Create a validator instance"""
