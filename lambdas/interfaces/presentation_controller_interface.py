"""
Presentation Controller Interface - Abstract Business Logic Layer
Defines the contract for presentation compilation and orchestration operations
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# Import request/response models (these remain concrete)
from models.request_response_models import CompileRequest, CompileResponse

# Import interfaces
from .presentation_model_interface import IPresentationModel
from .presentation_view_interface import IPresentationView


class IPresentationCompiler(ABC):
    """Interface for presentation compilation operations"""

    @abstractmethod
    def compile_presentation(
        self, request: CompileRequest, timeout_manager: Optional[Any] = None
    ) -> CompileResponse:
        """Main compilation method"""

    @abstractmethod
    def validate_compilation_request(self, request: CompileRequest) -> bool:
        """Validate compilation request parameters"""

    @abstractmethod
    def get_compilation_status(self, presentation_id: str) -> Dict[str, Any]:
        """Get current compilation status"""

    @abstractmethod
    def cancel_compilation(self, presentation_id: str) -> bool:
        """Cancel ongoing compilation"""


class IPresentationOrchestrator(ABC):
    """Interface for orchestrating presentation generation workflow"""

    @abstractmethod
    def initialize_compilation(self, request: CompileRequest) -> str:
        """Initialize compilation process and return task ID"""

    @abstractmethod
    def setup_resources(
        self, presentation_id: str, template_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Setup required resources for compilation"""

    @abstractmethod
    def coordinate_content_generation(
        self,
        presentation_id: str,
        include_images: bool = True,
        include_charts: bool = True,
    ) -> Dict[str, Any]:
        """Coordinate content generation across multiple sources"""

    @abstractmethod
    def finalize_presentation(
        self, presentation_id: str, output_options: Dict[str, Any]
    ) -> CompileResponse:
        """Finalize and deliver the presentation"""


class IContentProcessor(ABC):
    """Interface for processing different types of content"""

    @abstractmethod
    def process_slide_content(self, slide_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual slide content"""

    @abstractmethod
    def process_speaker_notes(self, notes_data: Dict[str, Any]) -> Dict[str, str]:
        """Process speaker notes for all slides"""

    @abstractmethod
    def process_images(
        self, image_requests: List[Dict[str, Any]]
    ) -> Dict[int, List[bytes]]:
        """Process and download images for slides"""

    @abstractmethod
    def process_charts(self, chart_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process chart data for visualization"""


class IResourceManager(ABC):
    """Interface for managing compilation resources"""

    @abstractmethod
    def acquire_resources(self, resource_type: str, **params) -> Any:
        """Acquire required resources (templates, images, etc.)"""

    @abstractmethod
    def release_resources(self, resource_id: str) -> None:
        """Release acquired resources"""

    @abstractmethod
    def cache_resource(
        self, resource_id: str, resource_data: Any, ttl: int = 3600
    ) -> None:
        """Cache resource for future use"""

    @abstractmethod
    def get_resource_status(self, resource_id: str) -> Dict[str, Any]:
        """Get status of a specific resource"""


class IQualityController(ABC):
    """Interface for quality control during compilation"""

    @abstractmethod
    def validate_input_data(self, request: CompileRequest) -> List[str]:
        """Validate input data and return list of issues"""

    @abstractmethod
    def check_content_quality(
        self, presentation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check content quality and accessibility"""

    @abstractmethod
    def verify_output_integrity(self, output_data: bytes) -> bool:
        """Verify output file integrity"""

    @abstractmethod
    def generate_quality_report(self, presentation_id: str) -> Dict[str, Any]:
        """Generate comprehensive quality report"""


class IPresentationController(
    IPresentationCompiler,
    IPresentationOrchestrator,
    IContentProcessor,
    IResourceManager,
    IQualityController,
):
    """Complete interface for presentation controller operations"""

    @abstractmethod
    def set_model(self, model: IPresentationModel) -> None:
        """Set the model layer dependency"""

    @abstractmethod
    def set_view(self, view: IPresentationView) -> None:
        """Set the view layer dependency"""

    @abstractmethod
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get compilation performance metrics"""

    @abstractmethod
    def cleanup_resources(self) -> None:
        """Cleanup all acquired resources"""


# Specialized interfaces for different compilation strategies
class IAsyncCompiler(ABC):
    """Interface for asynchronous compilation"""

    @abstractmethod
    async def compile_presentation_async(
        self, request: CompileRequest
    ) -> CompileResponse:
        """Asynchronous compilation method"""

    @abstractmethod
    async def get_compilation_progress(self, task_id: str) -> Dict[str, Any]:
        """Get progress of async compilation"""


class IBatchCompiler(ABC):
    """Interface for batch compilation"""

    @abstractmethod
    def compile_presentations_batch(
        self, requests: List[CompileRequest]
    ) -> List[CompileResponse]:
        """Compile multiple presentations in batch"""

    @abstractmethod
    def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get status of batch compilation"""


# Factory interface for creating controller instances
class IPresentationControllerFactory(ABC):
    """Factory interface for creating controller instances"""

    @abstractmethod
    def create_compiler(
        self, model: IPresentationModel, view: IPresentationView, **config
    ) -> IPresentationCompiler:
        """Create a presentation compiler instance"""

    @abstractmethod
    def create_orchestrator(self, **config) -> IPresentationOrchestrator:
        """Create an orchestrator instance"""

    @abstractmethod
    def create_quality_controller(self, **config) -> IQualityController:
        """Create a quality controller instance"""

    @abstractmethod
    def create_async_compiler(self, **config) -> IAsyncCompiler:
        """Create an async compiler instance"""

    @abstractmethod
    def create_batch_compiler(self, **config) -> IBatchCompiler:
        """Create a batch compiler instance"""
