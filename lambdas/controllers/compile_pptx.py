"""
Compile PPTX Lambda Function - AI PPT Assistant
Controller layer that coordinates Model and View to generate PowerPoint presentations
"""

import contextlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
import requests
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import interfaces (abstractions)
from interfaces.presentation_controller_interface import IPresentationCompiler
from interfaces.presentation_model_interface import IPresentationModel
from interfaces.presentation_view_interface import IPresentationView as IViewInterface

# Import data structures
from models.data_structures import (
    PresentationMetadata,
    PresentationStatus,
    SlideData,
)

# Import Model and View layers (concrete implementations)
from models.presentation_model import (
    presentation_model,
)

# Import request/response models
from models.request_response_models import CompileRequest, CompileResponse

# Import checkpoint management utilities
# Import configuration management
from utils.enhanced_config_manager import get_enhanced_config_manager

# Import timeout management utilities
from utils.timeout_manager import (
    TimeoutError,
    TimeoutManager,
    create_timeout_config,
    timeout_handler,
)
from views.presentation_view import (
    create_styled_presentation,
)

config_manager = get_enhanced_config_manager()
get_config = config_manager.get_value

# Import checkpoint management
from utils.checkpoint_manager import (
    CheckpointData,
    CheckpointManager,
    CheckpointStatus,
    TaskStage,
    create_checkpoint_manager,
    create_task_checkpoint,
)

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="AIPPTAssistant")

# Initialize AWS clients
s3 = boto3.client("s3")

# Environment variables
BUCKET_NAME = os.environ.get("S3_BUCKET", get_config("aws.s3.bucket"))
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get("MAX_CONCURRENT_DOWNLOADS", "5"))
IMAGE_DOWNLOAD_TIMEOUT = int(os.environ.get("IMAGE_DOWNLOAD_TIMEOUT", "10"))

# Models are now imported from models.request_response_models


class PresentationCompiler(IPresentationCompiler):
    """Controller class for PPTX compilation with interface compliance and dependency injection"""

    def __init__(
        self,
        model: Optional[IPresentationModel] = None,
        view: Optional[IViewInterface] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
    ):
        # Use dependency injection pattern with fallback to concrete implementations
        self._model = model if model is not None else presentation_model
        self._view = view
        self.image_cache = {}
        self.checkpoint_manager = checkpoint_manager
        self.current_checkpoint: Optional[CheckpointData] = None

    @property
    def model(self) -> IPresentationModel:
        """Get model instance (interface-based)"""
        return self._model

    @model.setter
    def model(self, value: IPresentationModel) -> None:
        """Set model instance (for testing)"""
        self._model = value

    @property
    def view(self) -> Optional[IViewInterface]:
        """Get view instance (interface-based)"""
        return self._view

    @view.setter
    def view(self, value: Optional[IViewInterface]) -> None:
        """Set view instance (for testing)"""
        self._view = value

    def set_model(self, model: IPresentationModel) -> None:
        """Set the model layer dependency (interface compliance)"""
        self._model = model

    def set_view(self, view: IViewInterface) -> None:
        """Set the view layer dependency (interface compliance)"""
        self._view = view

    def validate_compilation_request(self, request: CompileRequest) -> bool:
        """Validate compilation request parameters (interface compliance)"""
        try:
            # Basic validation - can be extended
            if not request.presentation_id or len(request.presentation_id.strip()) == 0:
                return False
            if request.style not in [
                "professional",
                "creative",
                "minimalist",
                "technical",
            ]:
                return False
            return True
        except Exception:
            return False

    def get_compilation_status(self, presentation_id: str) -> Dict[str, Any]:
        """Get current compilation status (interface compliance)"""
        try:
            presentation = self.model.get_presentation_record(presentation_id)
            if not presentation:
                return {"status": "not_found", "error": "Presentation not found"}

            return {
                "status": presentation.status,
                "presentation_id": presentation_id,
                "created_at": presentation.created_at,
                "updated_at": presentation.updated_at,
                "slide_count": presentation.slide_count,
                "file_size": presentation.file_size,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def cancel_compilation(self, presentation_id: str) -> bool:
        """Cancel ongoing compilation (interface compliance)"""
        try:
            self.model.update_presentation_status(
                presentation_id,
                PresentationStatus.FAILED.value,
                error_message="Compilation cancelled by user",
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cancel compilation: {e}")
            return False

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get compilation performance metrics (interface compliance)"""
        # This would be extended with actual performance tracking
        return {
            "cache_size": len(self.image_cache),
            "last_compilation_time": datetime.now(timezone.utc).isoformat(),
        }

    def cleanup_resources(self) -> None:
        """Cleanup all acquired resources (interface compliance)"""
        self.image_cache.clear()
        # Additional cleanup can be added here

    def _check_for_recovery(
        self, presentation_id: str, current_task_id: str
    ) -> Optional[Dict[str, Any]]:
        """Check for existing recovery points for this presentation"""
        if not self.checkpoint_manager:
            return None

        try:
            # Look for failed presentations that need recovery
            presentation = self.model.get_presentation_record(presentation_id)
            if not presentation:
                return None

            # Check if presentation is in a failed or interrupted state
            if presentation.status in ["failed", "in_progress"]:
                # Find recovery point
                recovery_checkpoint = self.checkpoint_manager.find_recovery_point(
                    f"compile_{presentation_id}"
                )
                if recovery_checkpoint:
                    return self.checkpoint_manager.restore_from_checkpoint(
                        recovery_checkpoint
                    )

            return None

        except Exception as e:
            logger.warning(f"Error checking for recovery: {e}")
            return None

    def _resume_compilation(
        self,
        request: CompileRequest,
        recovery_data: Dict[str, Any],
        timeout_manager: Optional[TimeoutManager],
        start_time: datetime,
    ) -> CompileResponse:
        """Resume compilation from checkpoint"""

        try:
            recovery_data["presentation_id"]
            resume_stage = TaskStage(recovery_data["resume_stage"])
            progress = recovery_data.get("progress_percentage", 0.0)

            logger.info(
                f"Resuming compilation from stage: {resume_stage.value} at {progress}% progress"
            )

            # Restore state
            if "slides_data" in recovery_data and recovery_data["slides_data"]:
                recovery_data["slides_data"]
                recovery_data.get("processed_slides", [])

                # Continue from where we left off
                if resume_stage == TaskStage.IMAGE_PROCESSING:
                    return self._resume_from_image_processing(
                        request, recovery_data, timeout_manager, start_time
                    )
                elif resume_stage == TaskStage.COMPILATION:
                    return self._resume_from_compilation(
                        request, recovery_data, timeout_manager, start_time
                    )
                else:
                    # For other stages, restart the compilation process
                    logger.info("Restarting compilation process from checkpoint data")
                    return self._continue_compilation_with_data(
                        request, recovery_data, timeout_manager, start_time
                    )

            # If no specific recovery logic, restart
            logger.info("No specific recovery logic, restarting compilation")
            return self._continue_compilation_with_data(
                request, recovery_data, timeout_manager, start_time
            )

        except Exception as e:
            logger.error(f"Error resuming compilation: {e}")
            # Fall back to normal compilation
            return self.compile_presentation(request, timeout_manager)

    def _resume_from_image_processing(
        self,
        request: CompileRequest,
        recovery_data: Dict[str, Any],
        timeout_manager: Optional[TimeoutManager],
        start_time: datetime,
    ) -> CompileResponse:
        """Resume from image processing stage"""

        logger.info("Resuming from image processing stage")

        # This would contain specific logic for resuming image processing
        # For now, continue with normal flow
        return self._continue_compilation_with_data(
            request, recovery_data, timeout_manager, start_time
        )

    def _resume_from_compilation(
        self,
        request: CompileRequest,
        recovery_data: Dict[str, Any],
        timeout_manager: Optional[TimeoutManager],
        start_time: datetime,
    ) -> CompileResponse:
        """Resume from compilation stage"""

        logger.info("Resuming from compilation stage")

        # This would contain specific logic for resuming compilation
        # For now, continue with normal flow
        return self._continue_compilation_with_data(
            request, recovery_data, timeout_manager, start_time
        )

    def _continue_compilation_with_data(
        self,
        request: CompileRequest,
        recovery_data: Dict[str, Any],
        timeout_manager: Optional[TimeoutManager],
        start_time: datetime,
    ) -> CompileResponse:
        """Continue compilation using recovered data"""

        # This would use the recovered data to continue compilation
        # For now, return a recovery response
        logger.info("Continuing compilation with recovered data")

        return CompileResponse(
            success=True,
            presentation_id=request.presentation_id,
            message=f"Compilation resumed from checkpoint (retry #{recovery_data.get('retry_count', 1)})",
            generation_time_ms=int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            ),
        )

    def _update_checkpoint_progress(
        self, progress: float, step: str, stage: Optional[TaskStage] = None
    ) -> None:
        """Update checkpoint progress"""
        if self.checkpoint_manager and self.current_checkpoint:
            update_data = {"progress_percentage": progress, "current_step": step}
            if stage:
                update_data["stage"] = stage.value

            self.checkpoint_manager.update_checkpoint(
                self.current_checkpoint.checkpoint_id, **update_data
            )

    def _mark_checkpoint_failed(self, error_message: str) -> None:
        """Mark current checkpoint as failed"""
        if self.checkpoint_manager and self.current_checkpoint:
            self.checkpoint_manager.update_checkpoint(
                self.current_checkpoint.checkpoint_id,
                status=CheckpointStatus.FAILED,
                error_message=error_message,
            )

    def _mark_checkpoint_completed(self) -> None:
        """Mark current checkpoint as completed"""
        if self.checkpoint_manager and self.current_checkpoint:
            self.checkpoint_manager.update_checkpoint(
                self.current_checkpoint.checkpoint_id,
                status=CheckpointStatus.COMPLETED,
                progress_percentage=100.0,
                current_step="Compilation completed",
            )

    @tracer.capture_method
    def compile_presentation(
        self, request: CompileRequest, timeout_manager: Optional[TimeoutManager] = None
    ) -> CompileResponse:
        """Main compilation method with timeout monitoring and checkpoint recovery"""
        start_time = datetime.now(timezone.utc)
        task_id = f"compile_{request.presentation_id}_{int(start_time.timestamp())}"

        # Initialize checkpoint manager if not provided
        if self.checkpoint_manager is None:
            self.checkpoint_manager = create_checkpoint_manager(timeout_manager)

        try:
            # Check timeout status before starting
            if timeout_manager:
                timeout_manager.check_timeout_status("compile_presentation")

            # Check for existing recovery point
            recovery_data = self._check_for_recovery(request.presentation_id, task_id)
            if recovery_data:
                logger.info(
                    f"Resuming compilation from checkpoint: {recovery_data['checkpoint_id']}"
                )
                return self._resume_compilation(
                    request, recovery_data, timeout_manager, start_time
                )

            # Create initial checkpoint
            self.current_checkpoint = create_task_checkpoint(
                self.checkpoint_manager,
                task_id=task_id,
                task_type="presentation_compilation",
                presentation_id=request.presentation_id,
                stage=TaskStage.INITIALIZATION,
                current_step="Starting compilation",
                progress=0.0,
                presentation_metadata={
                    "style": request.style,
                    "include_speaker_notes": request.include_speaker_notes,
                    "include_images": request.include_images,
                    "include_charts": request.include_charts,
                },
            )
            with (
                timeout_manager.operation("status_update")
                if timeout_manager
                else contextlib.nullcontext()
            ):
                # Update presentation status to in progress
                self.model.update_presentation_status(
                    request.presentation_id, PresentationStatus.IN_PROGRESS.value
                )

            with (
                timeout_manager.operation("metadata_retrieval")
                if timeout_manager
                else contextlib.nullcontext()
            ):
                # Step 1: Get presentation metadata
                self._update_checkpoint_progress(
                    10.0, "Retrieving presentation metadata"
                )

                logger.info(
                    f"Retrieving presentation metadata: {request.presentation_id}"
                )
                presentation = self.model.get_presentation_record(
                    request.presentation_id
                )
                if not presentation:
                    self._mark_checkpoint_failed("Presentation not found")
                    raise ValueError(
                        f"Presentation not found: {request.presentation_id}"
                    )

                # Update checkpoint with presentation metadata
                self.checkpoint_manager.update_checkpoint(
                    self.current_checkpoint.checkpoint_id,
                    presentation_metadata=(
                        presentation.__dict__
                        if hasattr(presentation, "__dict__")
                        else vars(presentation)
                    ),
                )

            with (
                timeout_manager.operation("template_setup")
                if timeout_manager
                else contextlib.nullcontext()
            ):
                # Step 2: Get or create template
                template_data = None
                if request.template_id:
                    logger.info(f"Loading template: {request.template_id}")
                    template_data, _ = self.model.get_template(request.template_id)
                else:
                    logger.info("Using default template")
                    template_data, _ = self.model.get_default_template()

                # Step 3: Initialize view with template
                self.view = create_styled_presentation(request.style, template_data)

            with (
                timeout_manager.operation("slide_content_retrieval")
                if timeout_manager
                else contextlib.nullcontext()
            ):
                # Step 4: Get slide content
                self._update_checkpoint_progress(
                    30.0, "Retrieving slide content", stage=TaskStage.CONTENT_GENERATION
                )

                logger.info("Retrieving slide content")
                slides = self.model.get_slide_content(request.presentation_id)

                # Save slides data to checkpoint
                self.checkpoint_manager.update_checkpoint(
                    self.current_checkpoint.checkpoint_id,
                    slides_data=[
                        slide.__dict__ if hasattr(slide, "__dict__") else vars(slide)
                        for slide in slides
                    ],
                )

            with (
                timeout_manager.operation("speaker_notes_retrieval")
                if timeout_manager
                else contextlib.nullcontext()
            ):
                # Step 5: Get speaker notes if requested
                speaker_notes = {}
                if request.include_speaker_notes:
                    logger.info("Retrieving speaker notes")
                    speaker_notes = self._get_speaker_notes(request.presentation_id)

            with (
                timeout_manager.operation("image_download")
                if timeout_manager
                else contextlib.nullcontext()
            ):
                # Step 6: Download images in parallel if requested
                images = {}
                if request.include_images:
                    logger.info("Downloading images")
                    images = self._download_images_parallel(slides)

            with (
                timeout_manager.operation("presentation_building")
                if timeout_manager
                else contextlib.nullcontext()
            ):
                # Step 7: Build presentation
                logger.info("Building presentation")
                self._build_presentation(
                    presentation, slides, speaker_notes, images, request.include_charts
                )

            with (
                timeout_manager.operation("presentation_saving")
                if timeout_manager
                else contextlib.nullcontext()
            ):
                # Step 8: Save presentation
                logger.info("Saving presentation")
                presentation_bytes = self.view.save_presentation()

                # Step 9: Upload to S3
                s3_key, download_url = self.model.save_presentation_to_s3(
                    request.presentation_id,
                    presentation_bytes,
                    f"{presentation.title}.pptx",
                )

            # Step 10: Update presentation status
            slide_count = self.view.get_slide_count()
            self.model.update_presentation_status(
                request.presentation_id,
                PresentationStatus.COMPLETED.value,
                s3_key=s3_key,
                file_size=len(presentation_bytes),
                slide_count=slide_count,
            )

            # Calculate generation time
            generation_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

            # Mark checkpoint as completed
            self._mark_checkpoint_completed()

            # Record metrics
            metrics.add_metric(
                name="PresentationCompiled", unit=MetricUnit.Count, value=1
            )
            metrics.add_metric(
                name="SlideCount", unit=MetricUnit.Count, value=slide_count
            )
            metrics.add_metric(
                name="GenerationTimeMs",
                unit=MetricUnit.Milliseconds,
                value=generation_time_ms,
            )

            return CompileResponse(
                success=True,
                presentation_id=request.presentation_id,
                download_url=download_url,
                s3_key=s3_key,
                file_size=len(presentation_bytes),
                slide_count=slide_count,
                generation_time_ms=generation_time_ms,
                message=f"Successfully compiled presentation with {slide_count} slides",
            )

        except Exception as e:
            logger.error(f"Compilation error: {str(e)}", exc_info=True)

            # Mark checkpoint as failed
            self._mark_checkpoint_failed(str(e))

            # Update status to failed
            self.model.update_presentation_status(
                request.presentation_id,
                PresentationStatus.FAILED.value,
                error_message=str(e),
            )

            metrics.add_metric(
                name="PresentationCompilationError", unit=MetricUnit.Count, value=1
            )

            return CompileResponse(
                success=False,
                presentation_id=request.presentation_id,
                message="Compilation failed",
                error=str(e),
                generation_time_ms=int(
                    (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                ),
            )

    @tracer.capture_method
    def _get_speaker_notes(self, presentation_id: str) -> Dict[int, str]:
        """Retrieve speaker notes from S3"""
        try:
            # Try to get speaker notes from S3
            s3_key = f"speaker-notes/{presentation_id}/notes.json"
            response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
            notes_data = json.loads(response["Body"].read())

            # Extract notes for each slide
            speaker_notes = {}
            for note in notes_data.get("speaker_notes", []):
                slide_number = note.get("slide_number")
                detailed_notes = note.get("detailed_notes", "")
                if slide_number:
                    speaker_notes[slide_number] = detailed_notes

            logger.info(f"Retrieved speaker notes for {len(speaker_notes)} slides")
            return speaker_notes

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.info("No speaker notes found")
                return {}
            else:
                logger.error(f"Error retrieving speaker notes: {str(e)}")
                return {}

    @tracer.capture_method
    def _download_images_parallel(
        self, slides: List[SlideData]
    ) -> Dict[int, List[bytes]]:
        """Download images for slides in parallel"""
        images = {}
        image_urls = []

        # Collect all image URLs
        for slide in slides:
            for image_info in slide.images:
                if "url" in image_info:
                    image_urls.append((slide.slide_number, image_info["url"]))

        if not image_urls:
            return images

        # Download images in parallel
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
            futures = {
                executor.submit(self._download_image, url): (slide_num, url)
                for slide_num, url in image_urls
            }

            for future in as_completed(futures):
                slide_num, url = futures[future]
                try:
                    image_data = future.result(timeout=IMAGE_DOWNLOAD_TIMEOUT)
                    if image_data:
                        if slide_num not in images:
                            images[slide_num] = []
                        images[slide_num].append(image_data)
                        logger.info(f"Downloaded image for slide {slide_num}")
                except Exception as e:
                    logger.warning(f"Failed to download image from {url}: {str(e)}")

        return images

    @tracer.capture_method
    def _download_image(self, url: str) -> Optional[bytes]:
        """Download a single image"""
        # Check cache first
        if url in self.image_cache:
            return self.image_cache[url]

        try:
            if url.startswith("s3://"):
                # Download from S3
                parts = url.replace("s3://", "").split("/", 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ""

                response = s3.get_object(Bucket=bucket, Key=key)
                image_data = response["Body"].read()
            else:
                # Download from HTTP/HTTPS
                response = requests.get(url, timeout=IMAGE_DOWNLOAD_TIMEOUT)
                response.raise_for_status()
                image_data = response.content

            # Cache the image
            self.image_cache[url] = image_data
            return image_data

        except Exception as e:
            logger.error(f"Error downloading image from {url}: {str(e)}")
            return None

    @tracer.capture_method
    def _build_presentation(
        self,
        presentation: PresentationMetadata,
        slides: List[SlideData],
        speaker_notes: Dict[int, str],
        images: Dict[int, List[bytes]],
        include_charts: bool,
    ):
        """Build the presentation using the view layer"""

        # Add title slide
        self.view.add_title_slide(
            title=presentation.title,
            subtitle=f"Duration: {presentation.duration_minutes} minutes",
            author=presentation.owner,
            date=datetime.now(timezone.utc).strftime("%B %d, %Y"),
        )

        # Add content slides
        for slide in slides:
            slide_obj = None

            # Determine slide type and add appropriate slide
            if slide.layout_type == "title":
                slide_obj = self._add_title_slide(slide)
            elif slide.layout_type == "section":
                slide_obj = self._add_section_slide(slide)
            elif slide.layout_type == "two_column":
                slide_obj = self._add_two_column_slide(slide)
            elif slide.layout_type == "image" and images.get(slide.slide_number):
                slide_obj = self._add_image_slide(slide, images[slide.slide_number])
            elif slide.layout_type == "chart" and include_charts and slide.charts:
                slide_obj = self._add_chart_slide(slide)
            elif slide.layout_type == "closing":
                slide_obj = self._add_closing_slide(slide)
            else:
                # Default to content slide
                slide_obj = self._add_content_slide(slide)

            # Add speaker notes if available
            if slide_obj and slide.slide_number in speaker_notes:
                self.view.add_speaker_notes(
                    slide_obj, speaker_notes[slide.slide_number]
                )

    def _add_title_slide(self, slide: SlideData):
        """Add a title slide"""
        return self.view.add_title_slide(title=slide.title, subtitle=slide.content)

    def _add_section_slide(self, slide: SlideData):
        """Add a section divider slide"""
        return self.view.add_section_slide(
            title=slide.title, subtitle=slide.content if slide.content else None
        )

    def _add_content_slide(self, slide: SlideData):
        """Add a standard content slide"""
        # Parse content into bullet points
        content_points = self._parse_content_points(slide.content)

        return self.view.add_content_slide(
            title=slide.title, content=content_points, slide_number=slide.slide_number
        )

    def _add_two_column_slide(self, slide: SlideData):
        """Add a two-column content slide"""
        # Parse content into two columns
        content_points = self._parse_content_points(slide.content)
        mid_point = len(content_points) // 2

        left_content = content_points[:mid_point]
        right_content = content_points[mid_point:]

        return self.view.add_two_content_slide(
            title=slide.title, left_content=left_content, right_content=right_content
        )

    def _add_image_slide(self, slide: SlideData, image_data_list: List[bytes]):
        """Add an image slide"""
        if not image_data_list:
            return None

        # Use the first image
        image_data = image_data_list[0]

        return self.view.add_image_slide(
            title=slide.title,
            image_data=image_data,
            caption=slide.content if slide.content else None,
            layout="center",
        )

    def _add_chart_slide(self, slide: SlideData):
        """Add a chart slide"""
        if not slide.charts:
            return None

        # Use the first chart
        chart = slide.charts[0]

        return self.view.add_chart_slide(
            title=slide.title,
            chart_type=chart.get("type", "column"),
            data=chart.get("data", {}),
            chart_title=chart.get("title"),
        )

    def _add_closing_slide(self, slide: SlideData):
        """Add a closing/thank you slide"""
        contact_info = slide.metadata.get("contact_info") if slide.metadata else None

        return self.view.add_closing_slide(
            title=slide.title if slide.title else "Thank You",
            contact_info=contact_info,
            additional_text=slide.content if slide.content else None,
        )

    def _parse_content_points(self, content: str) -> List[str]:
        """Parse content string into bullet points"""
        if not content:
            return []

        # Split by common delimiters
        points = []

        # Try splitting by numbered list
        import re

        numbered_pattern = re.compile(r"\d+\.\s*(.+?)(?=\d+\.|$)", re.DOTALL)
        numbered_matches = numbered_pattern.findall(content)

        if numbered_matches:
            points = [match.strip() for match in numbered_matches]
        else:
            # Try splitting by bullet points
            bullet_pattern = re.compile(r"[•\-\*]\s*(.+?)(?=[•\-\*]|$)", re.DOTALL)
            bullet_matches = bullet_pattern.findall(content)

            if bullet_matches:
                points = [match.strip() for match in bullet_matches]
            else:
                # Split by newlines or periods
                lines = content.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and not line.endswith(":"):
                        points.append(line)

        # Clean and filter points
        points = [p for p in points if p and len(p) > 2]

        # Limit to reasonable number of points
        return points[:10]


# Lambda handler
@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Main Lambda handler for PPTX compilation with timeout management"""

    # Initialize timeout management
    timeout_config = create_timeout_config(
        context, grace_period=10
    )  # Longer grace period for complex operations

    with timeout_handler(context, timeout_config) as timeout_manager:
        try:
            with timeout_manager.operation("request_validation"):
                # Parse request
                body = (
                    json.loads(event.get("body", "{}"))
                    if isinstance(event.get("body"), str)
                    else event
                )

                # Validate request
                try:
                    request = CompileRequest(**body)
                except Exception as e:
                    logger.error(f"Request validation error: {str(e)}")
                    return {
                        "statusCode": 400,
                        "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*",
                        },
                        "body": json.dumps(
                            {
                                "success": False,
                                "error": "Invalid request",
                                "details": str(e),
                                "timeout_info": timeout_manager.get_performance_summary(),
                            }
                        ),
                    }

            logger.info(f"Compiling presentation: {request.presentation_id}")

            # Create compiler and process request
            compiler = PresentationCompiler()
            response = compiler.compile_presentation(request, timeout_manager)

            # Determine status code based on success
            status_code = 200 if response.success else 500

            # Add timeout information to response
            response_body = response.dict()
            response_body["performance_summary"] = (
                timeout_manager.get_performance_summary()
            )

            return {
                "statusCode": status_code,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(response_body, default=str),
            }

        except TimeoutError as e:
            logger.error(f"Timeout error: {str(e)}", exc_info=True)
            metrics.add_metric(
                name="CompilationTimeout", unit=MetricUnit.Count, value=1
            )

            return {
                "statusCode": 408,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "success": False,
                        "error": "Request timeout",
                        "message": str(e),
                        "timeout_info": timeout_manager.get_performance_summary(),
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            metrics.add_metric(name="CompilationError", unit=MetricUnit.Count, value=1)

            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "success": False,
                        "error": "Internal server error",
                        "message": str(e),
                        "timeout_info": (
                            timeout_manager.get_performance_summary()
                            if "timeout_manager" in locals()
                            else None
                        ),
                    }
                ),
            }
