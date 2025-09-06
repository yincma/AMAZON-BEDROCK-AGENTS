"""
Presentation Model - Data Access Layer for PPTX Compilation
Handles S3 operations, template management, and DynamoDB session management
"""

import hashlib
import json
import os
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import utilities
from utils.enhanced_config_manager import get_enhanced_config_manager

config_manager = get_enhanced_config_manager()
get_config = config_manager.get_value

# Import data structures
from models.data_structures import (
    PresentationMetadata,
    PresentationStatus,
    SlideData,
    TemplateMetadata,
    TemplateCategory,
)

# Import interfaces
from interfaces.presentation_model_interface import (
    IPresentationModel,
)

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize AWS clients
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

# Environment variables
BUCKET_NAME = os.environ.get("S3_BUCKET", get_config("aws.s3.bucket"))
TEMPLATES_BUCKET = os.environ.get(
    "TEMPLATES_BUCKET", get_config("aws.s3.templates_bucket")
)
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", get_config("aws.dynamodb.table"))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))
MAX_TEMPLATE_SIZE_MB = int(os.environ.get("MAX_TEMPLATE_SIZE_MB", "50"))


# Template categories
# TemplateCategory is now imported from models.data_structures


# Data structures are now imported from models.data_structures


class PresentationModel(IPresentationModel):
    """Data access layer for presentation management with interface compliance"""

    def __init__(self):
        self.s3 = s3
        self.dynamodb = dynamodb
        self.sessions_table = dynamodb.Table(SESSIONS_TABLE)
        self._template_cache = {}
        self._cache_timestamps = {}

    # Template Management
    @tracer.capture_method
    def get_template_list(
        self, category: Optional[str] = None
    ) -> List[TemplateMetadata]:
        """Get list of available templates"""
        try:
            templates = []

            # List templates from S3
            prefix = f"templates/{category}/" if category else "templates/"
            response = self.s3.list_objects_v2(
                Bucket=TEMPLATES_BUCKET, Prefix=prefix, Delimiter="/"
            )

            if "Contents" not in response:
                logger.info(f"No templates found for category: {category}")
                return templates

            # Process each template
            for obj in response["Contents"]:
                if obj["Key"].endswith(".pptx"):
                    # Get template metadata
                    try:
                        metadata_key = obj["Key"].replace(".pptx", "_metadata.json")
                        metadata_response = self.s3.get_object(
                            Bucket=TEMPLATES_BUCKET, Key=metadata_key
                        )
                        metadata = json.loads(metadata_response["Body"].read())

                        template = TemplateMetadata(
                            template_id=metadata.get(
                                "template_id", self._generate_template_id(obj["Key"])
                            ),
                            name=metadata.get("name", "Unnamed Template"),
                            category=metadata.get(
                                "category", TemplateCategory.DEFAULT.value
                            ),
                            description=metadata.get("description"),
                            thumbnail_url=metadata.get("thumbnail_url"),
                            s3_key=obj["Key"],
                            file_size=obj["Size"],
                            created_at=obj["LastModified"].isoformat(),
                            updated_at=obj["LastModified"].isoformat(),
                            tags=metadata.get("tags", []),
                            color_scheme=metadata.get("color_scheme"),
                            slide_layouts=metadata.get("slide_layouts", []),
                            font_family=metadata.get("font_family"),
                        )
                        templates.append(template)

                    except ClientError as e:
                        # If metadata doesn't exist, create basic template info
                        logger.warning(
                            f"No metadata for template {obj['Key']}: {str(e)}"
                        )
                        template = TemplateMetadata(
                            template_id=self._generate_template_id(obj["Key"]),
                            name=os.path.basename(obj["Key"]).replace(".pptx", ""),
                            category=category or TemplateCategory.DEFAULT.value,
                            s3_key=obj["Key"],
                            file_size=obj["Size"],
                            created_at=obj["LastModified"].isoformat(),
                            updated_at=obj["LastModified"].isoformat(),
                        )
                        templates.append(template)

            logger.info(f"Found {len(templates)} templates")
            return templates

        except ClientError as e:
            logger.error(f"Error listing templates: {str(e)}")
            raise

    @tracer.capture_method
    def get_template(self, template_id: str) -> Tuple[bytes, TemplateMetadata]:
        """Get template file and metadata"""

        # Check cache first
        if self._is_cached(template_id):
            logger.info(f"Returning cached template: {template_id}")
            return self._template_cache[template_id]

        try:
            # Find template by ID
            templates = self.get_template_list()
            template_metadata = None

            for template in templates:
                if template.template_id == template_id:
                    template_metadata = template
                    break

            if not template_metadata:
                raise ValueError(f"Template not found: {template_id}")

            # Check file size
            if template_metadata.file_size > MAX_TEMPLATE_SIZE_MB * 1024 * 1024:
                raise ValueError(
                    f"Template too large: {template_metadata.file_size} bytes"
                )

            # Download template from S3
            response = self.s3.get_object(
                Bucket=TEMPLATES_BUCKET, Key=template_metadata.s3_key
            )

            template_data = response["Body"].read()

            # Cache the template
            self._cache_template(template_id, (template_data, template_metadata))

            logger.info(
                f"Retrieved template: {template_id} ({len(template_data)} bytes)"
            )
            return template_data, template_metadata

        except ClientError as e:
            logger.error(f"Error retrieving template {template_id}: {str(e)}")
            raise

    @tracer.capture_method
    def get_default_template(self) -> Tuple[bytes, TemplateMetadata]:
        """Get default template"""
        try:
            # Try to get the default template
            return self.get_template("default")
        except ValueError:
            # If no default template exists, get the first available template
            templates = self.get_template_list()
            if not templates:
                raise ValueError("No templates available")
            return self.get_template(templates[0].template_id)

    # Presentation Management
    @tracer.capture_method
    def create_presentation_record(
        self,
        presentation_id: str,
        title: str,
        session_id: Optional[str] = None,
        template_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PresentationMetadata:
        """Create a new presentation record in DynamoDB"""

        try:
            now = datetime.now(timezone.utc).isoformat()

            presentation = PresentationMetadata(
                presentation_id=presentation_id,
                session_id=session_id,
                title=title,
                status=PresentationStatus.CREATED.value,
                created_at=now,
                updated_at=now,
                template_id=template_id,
                generation_metadata=metadata or {},
            )

            # Save to DynamoDB
            item = asdict(presentation)
            item["ttl"] = int(
                (datetime.now(timezone.utc) + timedelta(days=30)).timestamp()
            )

            self.sessions_table.put_item(Item=item)

            logger.info(f"Created presentation record: {presentation_id}")
            metrics.add_metric(
                name="PresentationCreated", unit=MetricUnit.Count, value=1
            )

            return presentation

        except ClientError as e:
            logger.error(f"Error creating presentation record: {str(e)}")
            raise

    @tracer.capture_method
    def get_presentation_record(
        self, presentation_id: str
    ) -> Optional[PresentationMetadata]:
        """Get presentation record from DynamoDB"""

        try:
            response = self.sessions_table.get_item(
                Key={"presentation_id": presentation_id}
            )

            if "Item" not in response:
                logger.warning(f"Presentation not found: {presentation_id}")
                return None

            item = response["Item"]

            return PresentationMetadata(
                presentation_id=item["presentation_id"],
                session_id=item.get("session_id"),
                title=item["title"],
                status=item["status"],
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                template_id=item.get("template_id"),
                s3_key=item.get("s3_key"),
                file_size=item.get("file_size", 0),
                slide_count=item.get("slide_count", 0),
                language=item.get("language", "en"),
                style=item.get("style", "professional"),
                duration_minutes=item.get("duration_minutes", 20),
                owner=item.get("owner"),
                tags=item.get("tags", []),
                generation_metadata=item.get("generation_metadata", {}),
            )

        except ClientError as e:
            logger.error(f"Error getting presentation record: {str(e)}")
            raise

    @tracer.capture_method
    def update_presentation_status(
        self,
        presentation_id: str,
        status: str,
        s3_key: Optional[str] = None,
        file_size: Optional[int] = None,
        slide_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        """Update presentation status in DynamoDB"""

        try:
            update_expression = "SET #status = :status, updated_at = :updated_at"
            expression_values = {
                ":status": status,
                ":updated_at": datetime.now(timezone.utc).isoformat(),
            }
            expression_names = {"#status": "status"}

            if s3_key:
                update_expression += ", s3_key = :s3_key"
                expression_values[":s3_key"] = s3_key

            if file_size is not None:
                update_expression += ", file_size = :file_size"
                expression_values[":file_size"] = file_size

            if slide_count is not None:
                update_expression += ", slide_count = :slide_count"
                expression_values[":slide_count"] = slide_count

            if error_message:
                update_expression += ", error_message = :error_message"
                expression_values[":error_message"] = error_message

            self.sessions_table.update_item(
                Key={"presentation_id": presentation_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names,
            )

            logger.info(f"Updated presentation status: {presentation_id} -> {status}")

        except ClientError as e:
            logger.error(f"Error updating presentation status: {str(e)}")
            raise

    # S3 File Operations
    @tracer.capture_method
    def save_presentation_to_s3(
        self, presentation_id: str, file_data: bytes, file_name: Optional[str] = None
    ) -> Tuple[str, str]:
        """Save presentation file to S3"""

        try:
            # Generate S3 key
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            file_name = file_name or f"{presentation_id}.pptx"
            s3_key = f"presentations/{presentation_id}/{timestamp}_{file_name}"

            # Upload to S3
            self.s3.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=file_data,
                ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                Metadata={
                    "presentation_id": presentation_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Generate presigned URL for download (valid for 1 hour)
            presigned_url = self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET_NAME, "Key": s3_key},
                ExpiresIn=3600,
            )

            logger.info(f"Saved presentation to S3: {s3_key} ({len(file_data)} bytes)")
            metrics.add_metric(name="PresentationSaved", unit=MetricUnit.Count, value=1)
            metrics.add_metric(
                name="PresentationSize", unit=MetricUnit.Bytes, value=len(file_data)
            )

            return s3_key, presigned_url

        except ClientError as e:
            logger.error(f"Error saving presentation to S3: {str(e)}")
            raise

    @tracer.capture_method
    def get_presentation_from_s3(self, s3_key: str) -> bytes:
        """Retrieve presentation file from S3"""

        try:
            response = self.s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)

            file_data = response["Body"].read()

            logger.info(
                f"Retrieved presentation from S3: {s3_key} ({len(file_data)} bytes)"
            )
            return file_data

        except ClientError as e:
            logger.error(f"Error retrieving presentation from S3: {str(e)}")
            raise

    @tracer.capture_method
    def generate_download_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for presentation download"""

        try:
            presigned_url = self.s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": BUCKET_NAME,
                    "Key": s3_key,
                    "ResponseContentDisposition": "attachment",
                },
                ExpiresIn=expires_in,
            )

            logger.info(f"Generated download URL for: {s3_key}")
            return presigned_url

        except ClientError as e:
            logger.error(f"Error generating download URL: {str(e)}")
            raise

    # Content Management
    @tracer.capture_method
    def save_slide_content(self, presentation_id: str, slides: List[SlideData]) -> str:
        """Save slide content to S3 as JSON"""

        try:
            # Convert slides to dict format
            slides_dict = [asdict(slide) for slide in slides]

            # Create content document
            content = {
                "presentation_id": presentation_id,
                "slides": slides_dict,
                "slide_count": len(slides),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Save to S3
            s3_key = f"content/{presentation_id}/slides.json"
            self.s3.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=json.dumps(content, indent=2),
                ContentType="application/json",
            )

            logger.info(f"Saved slide content: {s3_key} ({len(slides)} slides)")
            return s3_key

        except ClientError as e:
            logger.error(f"Error saving slide content: {str(e)}")
            raise

    @tracer.capture_method
    def get_slide_content(self, presentation_id: str) -> List[SlideData]:
        """Retrieve slide content from S3"""

        try:
            s3_key = f"content/{presentation_id}/slides.json"
            response = self.s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)

            content = json.loads(response["Body"].read())

            # Convert dict to SlideData objects
            slides = []
            for slide_dict in content["slides"]:
                slide = SlideData(
                    slide_number=slide_dict["slide_number"],
                    title=slide_dict["title"],
                    content=slide_dict["content"],
                    speaker_notes=slide_dict.get("speaker_notes"),
                    layout_type=slide_dict.get("layout_type", "content"),
                    images=slide_dict.get("images", []),
                    charts=slide_dict.get("charts", []),
                    metadata=slide_dict.get("metadata", {}),
                )
                slides.append(slide)

            logger.info(f"Retrieved slide content: {len(slides)} slides")
            return slides

        except ClientError as e:
            logger.error(f"Error retrieving slide content: {str(e)}")
            raise

    # Image Management
    @tracer.capture_method
    def save_image(
        self,
        presentation_id: str,
        slide_number: int,
        image_data: bytes,
        image_name: str,
    ) -> str:
        """Save image to S3 and return URL"""

        try:
            s3_key = f"images/{presentation_id}/slide_{slide_number}/{image_name}"

            # Detect content type
            content_type = "image/jpeg"
            if image_name.lower().endswith(".png"):
                content_type = "image/png"
            elif image_name.lower().endswith(".gif"):
                content_type = "image/gif"

            self.s3.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=image_data,
                ContentType=content_type,
            )

            # Generate URL
            url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

            logger.info(f"Saved image: {s3_key}")
            return url

        except ClientError as e:
            logger.error(f"Error saving image: {str(e)}")
            raise

    @tracer.capture_method
    def get_image(self, s3_key: str) -> bytes:
        """Retrieve image from S3"""

        try:
            response = self.s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)

            return response["Body"].read()

        except ClientError as e:
            logger.error(f"Error retrieving image: {str(e)}")
            raise

    # Session Management
    @tracer.capture_method
    def get_session_presentations(
        self, session_id: str, limit: int = 10
    ) -> List[PresentationMetadata]:
        """Get all presentations for a session"""

        try:
            response = self.sessions_table.query(
                IndexName="SessionIndex",  # Assuming GSI exists
                KeyConditionExpression="session_id = :session_id",
                ExpressionAttributeValues={":session_id": session_id},
                Limit=limit,
                ScanIndexForward=False,  # Most recent first
            )

            presentations = []
            for item in response.get("Items", []):
                presentation = PresentationMetadata(
                    presentation_id=item["presentation_id"],
                    session_id=item.get("session_id"),
                    title=item["title"],
                    status=item["status"],
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    template_id=item.get("template_id"),
                    s3_key=item.get("s3_key"),
                    file_size=item.get("file_size", 0),
                    slide_count=item.get("slide_count", 0),
                )
                presentations.append(presentation)

            logger.info(
                f"Found {len(presentations)} presentations for session {session_id}"
            )
            return presentations

        except ClientError as e:
            logger.error(f"Error getting session presentations: {str(e)}")
            return []

    # Utility Methods
    def _generate_template_id(self, s3_key: str) -> str:
        """Generate a unique template ID from S3 key"""
        return hashlib.md5(s3_key.encode()).hexdigest()[:8]

    def _is_cached(self, template_id: str) -> bool:
        """Check if template is cached and still valid"""
        if template_id not in self._template_cache:
            return False

        cached_time = self._cache_timestamps.get(template_id, 0)
        current_time = datetime.now(timezone.utc).timestamp()

        if current_time - cached_time > CACHE_TTL_SECONDS:
            # Cache expired
            del self._template_cache[template_id]
            del self._cache_timestamps[template_id]
            return False

        return True

    def _cache_template(
        self, template_id: str, template_data: Tuple[bytes, TemplateMetadata]
    ):
        """Cache template data"""
        self._template_cache[template_id] = template_data
        self._cache_timestamps[template_id] = datetime.now(timezone.utc).timestamp()
        logger.info(f"Cached template: {template_id}")

    def clear_cache(self):
        """Clear template cache"""
        self._template_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Cleared template cache")

    # Missing abstract method implementations
    def delete_presentation(self, presentation_id: str) -> None:
        """Delete presentation and associated data"""
        try:
            # Delete from DynamoDB
            self.presentations_table.delete_item(
                Key={"presentation_id": presentation_id}
            )
            # Note: S3 cleanup should be handled by a separate process
            logger.info(f"Deleted presentation: {presentation_id}")
        except ClientError as e:
            logger.error(f"Error deleting presentation {presentation_id}: {str(e)}")
            raise

    def get_presentation_history(
        self, presentation_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get presentation modification history"""
        try:
            # This is a stub implementation - in reality you'd query a history table
            response = self.presentations_table.get_item(
                Key={"presentation_id": presentation_id}
            )

            if "Item" in response:
                # Return current state as history entry
                return [
                    {
                        "timestamp": response["Item"].get("updated_at"),
                        "action": "update",
                        "version": "1.0",
                        "metadata": response["Item"],
                    }
                ]
            return []
        except ClientError as e:
            logger.error(f"Error getting history for {presentation_id}: {str(e)}")
            return []

    def list_templates(self, category: Optional[str] = None) -> List[TemplateMetadata]:
        """List available templates"""
        try:
            # Get list of template objects from S3
            response = s3.list_objects_v2(Bucket=TEMPLATES_BUCKET, Prefix="templates/")

            templates = []
            for obj in response.get("Contents", []):
                if obj["Key"].endswith(".pptx"):
                    template_id = self._generate_template_id(obj["Key"])
                    templates.append(
                        TemplateMetadata(
                            template_id=template_id,
                            name=obj["Key"].split("/")[-1].replace(".pptx", ""),
                            description=f"Template {template_id}",
                            category=category or "professional",
                            file_size=obj["Size"],
                            created_at=obj["LastModified"],
                            updated_at=obj["LastModified"],
                        )
                    )

            return templates
        except ClientError as e:
            logger.error(f"Error listing templates: {str(e)}")
            return []

    def backup_presentation(self, presentation_id: str) -> str:
        """Create backup of presentation and return backup ID"""
        try:
            backup_id = f"{presentation_id}_backup_{uuid.uuid4().hex[:8]}"

            # Get original presentation data
            response = self.presentations_table.get_item(
                Key={"presentation_id": presentation_id}
            )

            if "Item" in response:
                # Create backup entry
                backup_data = response["Item"].copy()
                backup_data["presentation_id"] = backup_id
                backup_data["original_id"] = presentation_id
                backup_data["backup_timestamp"] = datetime.now(timezone.utc).isoformat()

                self.presentations_table.put_item(Item=backup_data)
                logger.info(f"Created backup {backup_id} for {presentation_id}")
                return backup_id
            else:
                raise ValueError(f"Presentation {presentation_id} not found")

        except ClientError as e:
            logger.error(f"Error creating backup for {presentation_id}: {str(e)}")
            raise

    def restore_presentation(self, presentation_id: str, backup_id: str) -> None:
        """Restore presentation from backup"""
        try:
            # Get backup data
            backup_response = self.presentations_table.get_item(
                Key={"presentation_id": backup_id}
            )

            if "Item" not in backup_response:
                raise ValueError(f"Backup {backup_id} not found")

            # Restore data
            restore_data = backup_response["Item"].copy()
            restore_data["presentation_id"] = presentation_id
            restore_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            restore_data["restored_from"] = backup_id

            # Remove backup-specific fields
            restore_data.pop("original_id", None)
            restore_data.pop("backup_timestamp", None)

            self.presentations_table.put_item(Item=restore_data)
            logger.info(
                f"Restored presentation {presentation_id} from backup {backup_id}"
            )

        except ClientError as e:
            logger.error(
                f"Error restoring {presentation_id} from {backup_id}: {str(e)}"
            )
            raise

    def save_slide_data(self, presentation_id: str, slides: List[SlideData]) -> None:
        """Save slide data to storage"""
        try:
            # Store slide data in a separate table or as part of the presentation record
            slide_data = {
                "presentation_id": presentation_id,
                "slides": [asdict(slide) for slide in slides],
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "slide_count": len(slides),
            }

            # Update presentation record with slide count
            self.update_presentation_status(
                presentation_id,
                "slides_saved",
                slide_count=len(slides),
                slides_data=slide_data["slides"],
            )

            logger.info(
                f"Saved {len(slides)} slides for presentation {presentation_id}"
            )

        except Exception as e:
            logger.error(f"Error saving slide data for {presentation_id}: {str(e)}")
            raise


# Module-level instance for import
presentation_model = PresentationModel()
