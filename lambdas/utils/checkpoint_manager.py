"""
Checkpoint Manager - AI PPT Assistant
Implements checkpoint and recovery functionality for long-running tasks
"""

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.enhanced_config_manager import get_enhanced_config_manager

# Import timeout management
from utils.timeout_manager import TimeoutManager

config_manager = get_enhanced_config_manager()
get_config = config_manager.get_value

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# Environment variables
CHECKPOINTS_TABLE = os.environ.get(
    "CHECKPOINTS_TABLE", get_config("aws.dynamodb.checkpoints_table")
)
S3_BUCKET = os.environ.get("S3_BUCKET", get_config("aws.s3.bucket"))
CHECKPOINT_TTL_HOURS = int(os.environ.get("CHECKPOINT_TTL_HOURS", "24"))
MAX_CHECKPOINTS_PER_TASK = int(os.environ.get("MAX_CHECKPOINTS_PER_TASK", "50"))


class CheckpointStatus(Enum):
    """Checkpoint status enumeration"""

    CREATED = "created"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    RESTORED = "restored"


class TaskStage(Enum):
    """Task processing stages"""

    INITIALIZATION = "initialization"
    OUTLINE_CREATION = "outline_creation"
    CONTENT_GENERATION = "content_generation"
    IMAGE_PROCESSING = "image_processing"
    SPEAKER_NOTES = "speaker_notes"
    COMPILATION = "compilation"
    FINALIZATION = "finalization"
    COMPLETED = "completed"


@dataclass
class CheckpointData:
    """Checkpoint data structure"""

    checkpoint_id: str
    task_id: str
    task_type: str  # 'presentation_generation', 'presentation_modification', etc.
    presentation_id: str
    stage: TaskStage
    status: CheckpointStatus
    created_at: str
    updated_at: str
    progress_percentage: float
    current_step: str
    next_step: Optional[str] = None

    # Task-specific data
    presentation_metadata: Optional[Dict[str, Any]] = None
    outline_data: Optional[Dict[str, Any]] = None
    slides_data: Optional[List[Dict[str, Any]]] = None
    images_data: Optional[Dict[str, Any]] = None
    speaker_notes_data: Optional[Dict[str, Any]] = None

    # State data
    processed_slides: List[int] = None
    failed_operations: List[Dict[str, Any]] = None
    retry_count: int = 0
    error_message: Optional[str] = None

    # Recovery data
    recovery_instructions: Optional[Dict[str, Any]] = None
    s3_data_keys: Optional[List[str]] = None

    # TTL for automatic cleanup
    ttl: int = 0

    def __post_init__(self):
        if self.processed_slides is None:
            self.processed_slides = []
        if self.failed_operations is None:
            self.failed_operations = []
        if self.s3_data_keys is None:
            self.s3_data_keys = []

        # Set TTL if not provided
        if self.ttl == 0:
            self.ttl = int(
                (
                    datetime.now(timezone.utc) + timedelta(hours=CHECKPOINT_TTL_HOURS)
                ).timestamp()
            )


class CheckpointManager:
    """
    Checkpoint manager for handling task state persistence and recovery

    Features:
    - Automatic checkpoint creation at key stages
    - State persistence in DynamoDB with S3 backup for large data
    - Recovery point detection and restoration
    - Progress tracking and resumption
    - Cleanup of expired checkpoints
    """

    def __init__(self, timeout_manager: Optional[TimeoutManager] = None):
        self.timeout_manager = timeout_manager
        self.dynamodb_table = dynamodb.Table(CHECKPOINTS_TABLE)
        self.s3_client = s3

    @tracer.capture_method
    def create_checkpoint(
        self,
        task_id: str,
        task_type: str,
        presentation_id: str,
        stage: TaskStage,
        current_step: str,
        progress_percentage: float,
        **checkpoint_data,
    ) -> CheckpointData:
        """Create a new checkpoint for task state"""

        if self.timeout_manager:
            self.timeout_manager.check_timeout_status("checkpoint_creation")

        checkpoint_id = (
            f"{task_id}_{stage.value}_{int(datetime.now(timezone.utc).timestamp())}"
        )
        current_time = datetime.now(timezone.utc).isoformat()

        checkpoint = CheckpointData(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            task_type=task_type,
            presentation_id=presentation_id,
            stage=stage,
            status=CheckpointStatus.CREATED,
            created_at=current_time,
            updated_at=current_time,
            progress_percentage=progress_percentage,
            current_step=current_step,
            **checkpoint_data,
        )

        # Save checkpoint to DynamoDB
        self._save_checkpoint_to_db(checkpoint)

        # Save large data to S3 if needed
        self._save_large_data_to_s3(checkpoint)

        logger.info(
            f"Checkpoint created: {checkpoint_id} for task {task_id} at stage {stage.value}"
        )
        metrics.add_metric(name="CheckpointCreated", unit=MetricUnit.Count, value=1)

        return checkpoint

    @tracer.capture_method
    def update_checkpoint(
        self,
        checkpoint_id: str,
        progress_percentage: Optional[float] = None,
        current_step: Optional[str] = None,
        next_step: Optional[str] = None,
        status: Optional[CheckpointStatus] = None,
        error_message: Optional[str] = None,
        **update_data,
    ) -> bool:
        """Update existing checkpoint"""

        if self.timeout_manager:
            self.timeout_manager.check_timeout_status("checkpoint_update")

        try:
            update_expression = "SET updated_at = :updated_at"
            expression_values = {":updated_at": datetime.now(timezone.utc).isoformat()}

            if progress_percentage is not None:
                update_expression += ", progress_percentage = :progress"
                expression_values[":progress"] = progress_percentage

            if current_step is not None:
                update_expression += ", current_step = :current_step"
                expression_values[":current_step"] = current_step

            if next_step is not None:
                update_expression += ", next_step = :next_step"
                expression_values[":next_step"] = next_step

            if status is not None:
                update_expression += ", #status = :status"
                expression_values[":status"] = status.value

            if error_message is not None:
                update_expression += ", error_message = :error_msg"
                expression_values[":error_msg"] = error_message

            # Add any additional update data
            for key, value in update_data.items():
                if key not in ["checkpoint_id", "task_id", "created_at"]:
                    update_expression += f", {key} = :{key}"
                    expression_values[f":{key}"] = value

            self.dynamodb_table.update_item(
                Key={"checkpoint_id": checkpoint_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames={"#status": "status"} if status else None,
                ExpressionAttributeValues=expression_values,
            )

            logger.info(f"Checkpoint updated: {checkpoint_id}")
            return True

        except ClientError as e:
            logger.error(f"Error updating checkpoint: {e}")
            return False

    @tracer.capture_method
    def get_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointData]:
        """Retrieve checkpoint by ID"""

        try:
            response = self.dynamodb_table.get_item(
                Key={"checkpoint_id": checkpoint_id}
            )

            if "Item" not in response:
                return None

            item = response["Item"]

            # Convert DynamoDB item to CheckpointData
            checkpoint = CheckpointData(
                checkpoint_id=item["checkpoint_id"],
                task_id=item["task_id"],
                task_type=item["task_type"],
                presentation_id=item["presentation_id"],
                stage=TaskStage(item["stage"]),
                status=CheckpointStatus(item["status"]),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
                progress_percentage=float(item["progress_percentage"]),
                current_step=item["current_step"],
                next_step=item.get("next_step"),
                presentation_metadata=item.get("presentation_metadata"),
                outline_data=item.get("outline_data"),
                slides_data=item.get("slides_data"),
                images_data=item.get("images_data"),
                speaker_notes_data=item.get("speaker_notes_data"),
                processed_slides=item.get("processed_slides", []),
                failed_operations=item.get("failed_operations", []),
                retry_count=item.get("retry_count", 0),
                error_message=item.get("error_message"),
                recovery_instructions=item.get("recovery_instructions"),
                s3_data_keys=item.get("s3_data_keys", []),
                ttl=item.get("ttl", 0),
            )

            # Load large data from S3 if needed
            self._load_large_data_from_s3(checkpoint)

            return checkpoint

        except ClientError as e:
            logger.error(f"Error retrieving checkpoint: {e}")
            return None

    @tracer.capture_method
    def get_task_checkpoints(
        self, task_id: str, limit: int = 10
    ) -> List[CheckpointData]:
        """Get all checkpoints for a task, ordered by creation time"""

        try:
            # Query by GSI on task_id
            response = self.dynamodb_table.query(
                IndexName="TaskIdIndex",  # Assuming GSI exists
                KeyConditionExpression="task_id = :task_id",
                ExpressionAttributeValues={":task_id": task_id},
                ScanIndexForward=False,  # Descending order (newest first)
                Limit=limit,
            )

            checkpoints = []
            for item in response.get("Items", []):
                checkpoint = CheckpointData(
                    checkpoint_id=item["checkpoint_id"],
                    task_id=item["task_id"],
                    task_type=item["task_type"],
                    presentation_id=item["presentation_id"],
                    stage=TaskStage(item["stage"]),
                    status=CheckpointStatus(item["status"]),
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    progress_percentage=float(item["progress_percentage"]),
                    current_step=item["current_step"],
                    next_step=item.get("next_step"),
                    processed_slides=item.get("processed_slides", []),
                    retry_count=item.get("retry_count", 0),
                    error_message=item.get("error_message"),
                )
                checkpoints.append(checkpoint)

            return checkpoints

        except ClientError as e:
            logger.error(f"Error querying checkpoints for task {task_id}: {e}")
            return []

    @tracer.capture_method
    def find_recovery_point(self, task_id: str) -> Optional[CheckpointData]:
        """Find the best recovery point for a failed task"""

        checkpoints = self.get_task_checkpoints(task_id)

        # Find the latest successful checkpoint
        for checkpoint in checkpoints:
            if checkpoint.status in [
                CheckpointStatus.ACTIVE,
                CheckpointStatus.COMPLETED,
            ]:
                logger.info(
                    f"Found recovery point: {checkpoint.checkpoint_id} at stage {checkpoint.stage.value}"
                )
                return checkpoint

        # If no successful checkpoint, return the latest one
        if checkpoints:
            logger.info(
                f"Using latest checkpoint as recovery point: {checkpoints[0].checkpoint_id}"
            )
            return checkpoints[0]

        logger.warning(f"No recovery point found for task {task_id}")
        return None

    @tracer.capture_method
    def restore_from_checkpoint(self, checkpoint: CheckpointData) -> Dict[str, Any]:
        """Restore task state from checkpoint"""

        if self.timeout_manager:
            self.timeout_manager.check_timeout_status("checkpoint_restore")

        try:
            # Mark checkpoint as being used for restoration
            self.update_checkpoint(
                checkpoint.checkpoint_id, status=CheckpointStatus.RESTORED
            )

            # Prepare restoration data
            restoration_data = {
                "checkpoint_id": checkpoint.checkpoint_id,
                "task_id": checkpoint.task_id,
                "presentation_id": checkpoint.presentation_id,
                "resume_stage": checkpoint.stage.value,
                "next_step": checkpoint.next_step,
                "progress_percentage": checkpoint.progress_percentage,
                "processed_slides": checkpoint.processed_slides,
                "failed_operations": checkpoint.failed_operations,
                "retry_count": checkpoint.retry_count + 1,
            }

            # Include task-specific data
            if checkpoint.presentation_metadata:
                restoration_data["presentation_metadata"] = (
                    checkpoint.presentation_metadata
                )
            if checkpoint.outline_data:
                restoration_data["outline_data"] = checkpoint.outline_data
            if checkpoint.slides_data:
                restoration_data["slides_data"] = checkpoint.slides_data
            if checkpoint.images_data:
                restoration_data["images_data"] = checkpoint.images_data
            if checkpoint.speaker_notes_data:
                restoration_data["speaker_notes_data"] = checkpoint.speaker_notes_data

            logger.info(f"Restored from checkpoint: {checkpoint.checkpoint_id}")
            metrics.add_metric(
                name="CheckpointRestored", unit=MetricUnit.Count, value=1
            )

            return restoration_data

        except Exception as e:
            logger.error(f"Error restoring from checkpoint: {e}")
            return {}

    @tracer.capture_method
    def cleanup_expired_checkpoints(self, task_id: Optional[str] = None) -> int:
        """Clean up expired checkpoints"""

        try:
            current_time = int(datetime.now(timezone.utc).timestamp())
            deleted_count = 0

            if task_id:
                # Clean up specific task
                checkpoints = self.get_task_checkpoints(task_id, limit=100)
                for checkpoint in checkpoints:
                    if checkpoint.ttl < current_time:
                        self._delete_checkpoint(checkpoint)
                        deleted_count += 1
            else:
                # Scan for expired checkpoints (use with caution in production)
                response = self.dynamodb_table.scan(
                    FilterExpression="#ttl < :current_time",
                    ExpressionAttributeNames={"#ttl": "ttl"},
                    ExpressionAttributeValues={":current_time": current_time},
                    Limit=50,  # Process in batches
                )

                for item in response.get("Items", []):
                    self._delete_checkpoint_by_id(item["checkpoint_id"])
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired checkpoints")
                metrics.add_metric(
                    name="CheckpointsDeleted",
                    unit=MetricUnit.Count,
                    value=deleted_count,
                )

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up checkpoints: {e}")
            return 0

    def _save_checkpoint_to_db(self, checkpoint: CheckpointData) -> None:
        """Save checkpoint to DynamoDB"""

        try:
            # Convert to dict and handle None values
            item = asdict(checkpoint)

            # Convert enums to strings
            item["stage"] = checkpoint.stage.value
            item["status"] = checkpoint.status.value

            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}

            self.dynamodb_table.put_item(Item=item)

        except ClientError as e:
            logger.error(f"Error saving checkpoint to DynamoDB: {e}")
            raise

    def _save_large_data_to_s3(self, checkpoint: CheckpointData) -> None:
        """Save large checkpoint data to S3"""

        large_data_fields = ["slides_data", "images_data"]

        for field in large_data_fields:
            data = getattr(checkpoint, field)
            if data and len(json.dumps(data)) > 100000:  # > 100KB
                s3_key = f"checkpoints/{checkpoint.task_id}/{checkpoint.checkpoint_id}/{field}.json"

                try:
                    self.s3_client.put_object(
                        Bucket=S3_BUCKET,
                        Key=s3_key,
                        Body=json.dumps(data),
                        ContentType="application/json",
                    )

                    checkpoint.s3_data_keys.append(s3_key)
                    setattr(
                        checkpoint, field, {"s3_key": s3_key}
                    )  # Replace with reference

                except ClientError as e:
                    logger.error(f"Error saving large data to S3: {e}")

    def _load_large_data_from_s3(self, checkpoint: CheckpointData) -> None:
        """Load large checkpoint data from S3"""

        for s3_key in checkpoint.s3_data_keys:
            try:
                response = self.s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
                data = json.loads(response["Body"].read())

                # Determine field name from S3 key
                field_name = s3_key.split("/")[-1].replace(".json", "")
                setattr(checkpoint, field_name, data)

            except ClientError as e:
                logger.warning(f"Could not load S3 data {s3_key}: {e}")

    def _delete_checkpoint(self, checkpoint: CheckpointData) -> None:
        """Delete checkpoint and associated S3 data"""

        # Delete S3 data
        for s3_key in checkpoint.s3_data_keys:
            try:
                self.s3_client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
            except ClientError as e:
                logger.warning(f"Could not delete S3 data {s3_key}: {e}")

        # Delete from DynamoDB
        self._delete_checkpoint_by_id(checkpoint.checkpoint_id)

    def _delete_checkpoint_by_id(self, checkpoint_id: str) -> None:
        """Delete checkpoint by ID"""

        try:
            self.dynamodb_table.delete_item(Key={"checkpoint_id": checkpoint_id})
        except ClientError as e:
            logger.error(f"Error deleting checkpoint {checkpoint_id}: {e}")


# Utility functions
def create_checkpoint_manager(
    timeout_manager: Optional[TimeoutManager] = None,
) -> CheckpointManager:
    """Create checkpoint manager instance"""
    return CheckpointManager(timeout_manager)


def create_task_checkpoint(
    checkpoint_manager: CheckpointManager,
    task_id: str,
    task_type: str,
    presentation_id: str,
    stage: TaskStage,
    current_step: str,
    progress: float,
    **data,
) -> CheckpointData:
    """Utility function to create checkpoint"""
    return checkpoint_manager.create_checkpoint(
        task_id=task_id,
        task_type=task_type,
        presentation_id=presentation_id,
        stage=stage,
        current_step=current_step,
        progress_percentage=progress,
        **data,
    )
