"""
Lambda function for checking presentation generation status - Optimized Version
Handles GET /tasks/{taskId} and GET /presentations/{presentationId}/status requests

Performance optimizations:
- DynamoDB ProjectionExpression for reduced data transfer
- Caching for frequently accessed data
- Optimized response building
"""

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, Optional, Set

import boto3
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_utils import create_response

# Initialize AWS clients with lazy loading
dynamodb = boto3.resource("dynamodb")

# Environment variables
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "presentations")

# Configure logging with structured format
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Constants for better maintainability
class PresentationStatus(Enum):
    """Enumeration of presentation statuses"""
    PENDING = "pending"
    OUTLINING = "outlining"
    CONTENT_GENERATION = "content_generation"
    IMAGE_GENERATION = "image_generation"
    COMPILING = "compiling"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressConstants:
    """Progress calculation constants"""
    PENDING = 0
    OUTLINING = 20
    CONTENT_GENERATION_BASE = 40
    IMAGE_GENERATION_BASE = 60
    COMPILING = 80
    COMPLETED = 100
    
    # Sub-progress ranges
    CONTENT_GENERATION_RANGE = 20
    IMAGE_GENERATION_RANGE = 20
    
    # Default values for calculations
    DEFAULT_SLIDE_COUNT = 15
    DEFAULT_IMAGE_COUNT = 10


class ValidationConstants:
    """Input validation constants"""
    MAX_UUID_LENGTH = 50
    DANGEROUS_CHARS = frozenset(['<', '>', '&', '"', "'", '/', '\\', '..', '\x00'])


# Cached status messages for better performance
STATUS_MESSAGES = {
    PresentationStatus.PENDING.value: "Presentation generation queued",
    PresentationStatus.OUTLINING.value: "Creating presentation outline",
    PresentationStatus.CONTENT_GENERATION.value: "Generating slide content",
    PresentationStatus.IMAGE_GENERATION.value: "Creating visual elements",
    PresentationStatus.COMPILING.value: "Assembling final presentation",
    PresentationStatus.COMPLETED.value: "Presentation ready for download",
    PresentationStatus.FAILED.value: "Presentation generation failed",
}


# DynamoDB projection fields for different status types
PROJECTION_FIELDS = {
    "base": [
        "presentation_id",
        "status",
        "created_at",
        "updated_at",
        "stage",
        "metadata",
        "progress"
    ],
    "content_generation": [
        "slide_count",
        "slides_completed"
    ],
    "image_generation": [
        "images_total",
        "images_completed"
    ],
    "completed": [
        "title",
        "slide_count",
        "file_size",
        "pptx_key",
        "pdf_key",
        "html_key",
        "download_expires_at",
        "completed_at",
        "estimated_completion"
    ],
    "failed": [
        "error_message",
        "error_code",
        "error_timestamp"
    ]
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for status check requests with performance optimizations

    Args:
        event: API Gateway event containing the request
        context: Lambda context

    Returns:
        API Gateway response with standardized format
    """
    try:
        # Extract and validate presentation ID
        presentation_id = extract_presentation_id(event)
        
        if not presentation_id:
            return create_response(
                400,
                {
                    "error": "VALIDATION_ERROR",
                    "message": "Presentation ID is required"
                },
            )

        if not validate_uuid_optimized(presentation_id):
            return create_response(
                400,
                {
                    "error": "VALIDATION_ERROR", 
                    "message": "Invalid presentation ID format. Must be a valid UUID."
                },
            )

        # Retrieve presentation state with optimized projection
        presentation = get_presentation_state_optimized(presentation_id)

        if not presentation:
            return create_response(
                404,
                {
                    "error": "NOT_FOUND",
                    "message": "Presentation not found",
                    "task_id": presentation_id
                },
            )

        # Build optimized response
        response_body = build_optimized_response(presentation)
        return create_response(200, response_body)

    except ClientError as e:
        logger.error(f"DynamoDB error: {str(e)}", extra={
            "error_code": e.response.get('Error', {}).get('Code'),
            "presentation_id": presentation_id if 'presentation_id' in locals() else None
        })
        return create_response(
            500,
            {
                "error": "INTERNAL_ERROR",
                "message": "Database error occurred"
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error in status check: {str(e)}", exc_info=True)
        return create_response(
            500,
            {
                "error": "INTERNAL_ERROR",
                "message": "Failed to retrieve status"
            },
        )


def extract_presentation_id(event: Dict[str, Any]) -> Optional[str]:
    """
    Extract presentation ID from various path parameter formats
    
    Args:
        event: API Gateway event
        
    Returns:
        Presentation ID or None if not found
    """
    path_params = event.get("pathParameters") or {}
    
    # Support multiple parameter naming conventions
    return (
        path_params.get("taskId") or 
        path_params.get("presentationId") or 
        path_params.get("id")
    )


@lru_cache(maxsize=128)
def validate_uuid_optimized(uuid_string: str) -> bool:
    """
    Validate UUID format with enhanced security checks and caching
    
    Args:
        uuid_string: String to validate
        
    Returns:
        True if valid and safe UUID, False otherwise
    """
    try:
        # Length validation
        if not uuid_string or len(uuid_string) > ValidationConstants.MAX_UUID_LENGTH:
            return False
        
        # Security: Check for dangerous characters using set intersection
        if set(uuid_string) & ValidationConstants.DANGEROUS_CHARS:
            logger.warning(f"Potentially dangerous characters in UUID: {uuid_string[:20]}...")
            return False
            
        # Validate UUID format
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def get_presentation_state_optimized(presentation_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve presentation state from DynamoDB with optimized projection
    
    First retrieves base fields to determine status, then fetches additional
    fields based on the status to minimize data transfer.
    
    Args:
        presentation_id: Unique presentation ID
        
    Returns:
        Presentation state object or None if not found
    """
    table = dynamodb.Table(TABLE_NAME)
    
    logger.info(f"Fetching presentation from DynamoDB: {presentation_id}")

    try:
        # First, get base fields to determine status
        projection_expr = ", ".join(PROJECTION_FIELDS["base"])
        
        response = table.get_item(
            Key={"presentation_id": presentation_id},
            ProjectionExpression=projection_expr
        )
        
        item = response.get("Item")
        if not item:
            logger.info("Presentation not found in DynamoDB")
            return None
            
        status = item.get("status")
        logger.info(f"Found presentation with status: {status}")
        
        # Get additional fields based on status
        additional_fields = get_additional_fields_for_status(status)
        
        if additional_fields:
            # Fetch additional fields
            all_fields = PROJECTION_FIELDS["base"] + additional_fields
            projection_expr = ", ".join(all_fields)
            
            response = table.get_item(
                Key={"presentation_id": presentation_id},
                ProjectionExpression=projection_expr
            )
            item = response.get("Item")
        
        return item
        
    except ClientError as e:
        logger.error(f"DynamoDB error retrieving presentation: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving presentation: {str(e)}")
        raise


def get_additional_fields_for_status(status: str) -> list:
    """
    Determine additional fields needed based on presentation status
    
    Args:
        status: Presentation status
        
    Returns:
        List of additional field names to fetch
    """
    additional_fields = []
    
    if status == PresentationStatus.CONTENT_GENERATION.value:
        additional_fields.extend(PROJECTION_FIELDS["content_generation"])
    elif status == PresentationStatus.IMAGE_GENERATION.value:
        additional_fields.extend(PROJECTION_FIELDS["image_generation"])
    elif status == PresentationStatus.COMPLETED.value:
        additional_fields.extend(PROJECTION_FIELDS["completed"])
    elif status == PresentationStatus.FAILED.value:
        additional_fields.extend(PROJECTION_FIELDS["failed"])
    
    return additional_fields


@lru_cache(maxsize=32)
def calculate_progress_cached(status: str, slides_total: int = 0, slides_completed: int = 0,
                              images_total: int = 0, images_completed: int = 0,
                              failed_progress: int = 0) -> int:
    """
    Calculate progress percentage with caching for common scenarios
    
    Args:
        status: Presentation status
        slides_total: Total number of slides
        slides_completed: Number of completed slides
        images_total: Total number of images
        images_completed: Number of completed images
        failed_progress: Progress value for failed status
        
    Returns:
        Progress percentage (0-100)
    """
    # Base progress mapping
    base_progress_map = {
        PresentationStatus.PENDING.value: ProgressConstants.PENDING,
        PresentationStatus.OUTLINING.value: ProgressConstants.OUTLINING,
        PresentationStatus.CONTENT_GENERATION.value: ProgressConstants.CONTENT_GENERATION_BASE,
        PresentationStatus.IMAGE_GENERATION.value: ProgressConstants.IMAGE_GENERATION_BASE,
        PresentationStatus.COMPILING.value: ProgressConstants.COMPILING,
        PresentationStatus.COMPLETED.value: ProgressConstants.COMPLETED,
        PresentationStatus.FAILED.value: failed_progress,
    }
    
    base_progress = base_progress_map.get(status, 0)
    
    # Calculate sub-progress for content generation
    if status == PresentationStatus.CONTENT_GENERATION.value and slides_total > 0:
        completion_ratio = slides_completed / slides_total
        sub_progress = completion_ratio * ProgressConstants.CONTENT_GENERATION_RANGE
        base_progress += int(sub_progress)
    
    # Calculate sub-progress for image generation
    elif status == PresentationStatus.IMAGE_GENERATION.value and images_total > 0:
        completion_ratio = images_completed / images_total
        sub_progress = completion_ratio * ProgressConstants.IMAGE_GENERATION_RANGE
        base_progress += int(sub_progress)
    
    return min(int(base_progress), 100)


def calculate_progress(presentation: Dict[str, Any]) -> int:
    """
    Wrapper for cached progress calculation
    
    Args:
        presentation: Presentation state object
        
    Returns:
        Progress percentage (0-100)
    """
    status = presentation.get("status", PresentationStatus.PENDING.value)
    
    return calculate_progress_cached(
        status=status,
        slides_total=presentation.get("slide_count", ProgressConstants.DEFAULT_SLIDE_COUNT),
        slides_completed=presentation.get("slides_completed", 0),
        images_total=presentation.get("images_total", ProgressConstants.DEFAULT_IMAGE_COUNT),
        images_completed=presentation.get("images_completed", 0),
        failed_progress=presentation.get("progress", 0)
    )


def build_optimized_response(presentation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build optimized status response with minimal object creation
    
    Args:
        presentation: Presentation state object
        
    Returns:
        Response body dictionary
    """
    presentation_id = presentation["presentation_id"]
    status = presentation.get("status", PresentationStatus.PENDING.value)
    progress = calculate_progress(presentation)
    
    # Build response in single pass
    response = {
        "task_id": presentation_id,
        "status": status,
        "progress": progress,
        "message": STATUS_MESSAGES.get(status, "Processing presentation"),
        "created_at": presentation.get("created_at"),
        "updated_at": presentation.get("updated_at"),
        "_links": {
            "self": f"/tasks/{presentation_id}",
            "presentation": f"/presentations/{presentation_id}",
        }
    }
    
    # Add stage if available
    if stage := presentation.get("stage"):
        response["stage"] = stage
    
    # Add metadata if present
    if metadata := presentation.get("metadata"):
        response["metadata"] = metadata
    
    # Add status-specific details
    if status == PresentationStatus.FAILED.value:
        response["error"] = {
            "message": presentation.get("error_message", "Unknown error"),
            "code": presentation.get("error_code", "UNKNOWN"),
            "timestamp": presentation.get("error_timestamp"),
        }
    elif status == PresentationStatus.COMPLETED.value:
        response["_links"]["download"] = f"/presentations/{presentation_id}/download"
        
        # Build result info
        result = {
            "presentation_id": presentation_id,
            "title": presentation.get("title"),
            "slide_count": presentation.get("slide_count"),
            "file_size": presentation.get("file_size"),
            "download_url": f"/presentations/{presentation_id}/download",
            "expires_at": presentation.get("download_expires_at"),
            "formats": []
        }
        
        # Add available formats
        if presentation.get("pptx_key"):
            result["formats"].append("pptx")
        if presentation.get("pdf_key"):
            result["formats"].append("pdf")
        if presentation.get("html_key"):
            result["formats"].append("html")
        
        response["result"] = result
        
        # Add completion timing
        if completed_at := presentation.get("completed_at"):
            response["completed_at"] = completed_at
            
            if created_at := presentation.get("created_at"):
                try:
                    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                    response["processing_time_seconds"] = (completed - created).total_seconds()
                except (ValueError, AttributeError):
                    pass
    
    # Add estimated completion for in-progress
    if estimated := presentation.get("estimated_completion"):
        response["estimated_completion"] = estimated
    
    return response


# Legacy support
def build_status_response(presentation: Dict[str, Any], progress: int) -> Dict[str, Any]:
    """Legacy function for backward compatibility"""
    return build_optimized_response(presentation)