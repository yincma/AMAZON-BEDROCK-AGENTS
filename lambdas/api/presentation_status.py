"""
Lambda function for checking presentation generation status
Handles GET /tasks/{taskId} and GET /presentations/{presentationId}/status requests

Refactored for improved maintainability, performance, and security
"""

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

import boto3
from boto3.dynamodb.conditions import Attr
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
    DANGEROUS_CHARS = ['<', '>', '&', '"', "'", '/', '\\', '..', '\x00']


STATUS_MESSAGES = {
    PresentationStatus.PENDING.value: "Presentation generation queued",
    PresentationStatus.OUTLINING.value: "Creating presentation outline",
    PresentationStatus.CONTENT_GENERATION.value: "Generating slide content",
    PresentationStatus.IMAGE_GENERATION.value: "Creating visual elements",
    PresentationStatus.COMPILING.value: "Assembling final presentation",
    PresentationStatus.COMPLETED.value: "Presentation ready for download",
    PresentationStatus.FAILED.value: "Presentation generation failed",
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for multiple status check endpoints:
    - GET /presentations/{id} - Get presentation status
    - GET /sessions/{id} - Get session information

    Args:
        event: API Gateway event containing the request
        context: Lambda context

    Returns:
        API Gateway response with standardized format
    """
    try:
        # Extract path and HTTP method for routing
        path = event.get("path", "")
        resource = event.get("resource", "")
        http_method = event.get("httpMethod", "")
        path_parameters = event.get("pathParameters") or {}
        
        logger.info(f"Request: {http_method} {path}")
        logger.info(f"Resource: {resource}")
        logger.info(f"Path parameters: {path_parameters}")
        
        # Route to appropriate handler based on resource path
        if resource == "/presentations/{id}" and http_method == "GET":
            return handle_get_presentation_status(event, context)
        elif resource == "/sessions/{id}" and http_method == "GET":
            return handle_get_session(event, context)
        # Fallback to path-based routing
        elif "/presentations/" in path and http_method == "GET":
            return handle_get_presentation_status(event, context)
        elif "/sessions/" in path and http_method == "GET":
            return handle_get_session(event, context)
        else:
            return create_response(
                404,
                {
                    "error": "NOT_FOUND",
                    "message": f"Endpoint {http_method} {path} not found",
                    "request_id": context.aws_request_id,
                },
            )

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return create_response(
            500,
            {
                "error": "INTERNAL_ERROR", 
                "message": "Internal server error",
                "request_id": context.aws_request_id,
            },
        )


def handle_get_presentation_status(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle GET /presentations/{id} requests
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

        if not validate_uuid(presentation_id):
            return create_response(
                400,
                {
                    "error": "VALIDATION_ERROR", 
                    "message": "Invalid presentation ID format. Must be a valid UUID."
                },
            )

        # Retrieve presentation state with optimized projection
        presentation = get_presentation_state(presentation_id)

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


def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format with enhanced security checks
    
    Args:
        uuid_string: String to validate
        
    Returns:
        True if valid and safe UUID, False otherwise
    """
    try:
        # Length validation
        if not uuid_string or len(uuid_string) > ValidationConstants.MAX_UUID_LENGTH:
            return False
        
        # Security: Check for dangerous characters
        if any(char in uuid_string for char in ValidationConstants.DANGEROUS_CHARS):
            logger.warning(f"Potentially dangerous characters in UUID: {uuid_string[:20]}...")
            return False
            
        # Validate UUID format
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def get_presentation_state(presentation_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve presentation state from DynamoDB using scan to find by presentation_id
    
    Args:
        presentation_id: Unique presentation ID (stored as attribute, not key)
        
    Returns:
        Presentation state object or None if not found
    """
    table = dynamodb.Table(TABLE_NAME)
    
    logger.info(f"Fetching presentation from DynamoDB: {presentation_id}")

    try:
        # Since presentation_id is not the primary key, we need to scan/query
        # The table uses session_id as primary key, but stores presentation_id as attribute
        response = table.scan(
            FilterExpression=Attr('presentation_id').eq(presentation_id),
            Limit=1  # We only expect one result
        )
        
        items = response.get("Items", [])
        item = items[0] if items else None
        
        if item:
            logger.info(f"Found presentation with status: {item.get('status')}")
        else:
            logger.info("Presentation not found in DynamoDB")
            
        return item
    except ClientError as e:
        logger.error(f"DynamoDB error retrieving presentation: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving presentation: {str(e)}")
        raise


def calculate_progress(presentation: Dict[str, Any]) -> int:
    """
    Calculate progress percentage based on status and sub-stages
    
    Args:
        presentation: Presentation state object
        
    Returns:
        Progress percentage (0-100)
    """
    status = presentation.get("status", PresentationStatus.PENDING.value)
    
    # Base progress mapping
    base_progress_map = {
        PresentationStatus.PENDING.value: ProgressConstants.PENDING,
        PresentationStatus.OUTLINING.value: ProgressConstants.OUTLINING,
        PresentationStatus.CONTENT_GENERATION.value: ProgressConstants.CONTENT_GENERATION_BASE,
        PresentationStatus.IMAGE_GENERATION.value: ProgressConstants.IMAGE_GENERATION_BASE,
        PresentationStatus.COMPILING.value: ProgressConstants.COMPILING,
        PresentationStatus.COMPLETED.value: ProgressConstants.COMPLETED,
        PresentationStatus.FAILED.value: presentation.get("progress", 0),
    }
    
    base_progress = base_progress_map.get(status, 0)
    
    # Calculate sub-progress for content generation
    if status == PresentationStatus.CONTENT_GENERATION.value:
        base_progress = calculate_content_progress(presentation, base_progress)
    
    # Calculate sub-progress for image generation
    elif status == PresentationStatus.IMAGE_GENERATION.value:
        base_progress = calculate_image_progress(presentation, base_progress)
    
    return min(int(base_progress), 100)


def calculate_content_progress(presentation: Dict[str, Any], base_progress: int) -> int:
    """
    Calculate progress for content generation phase
    
    Args:
        presentation: Presentation state
        base_progress: Base progress value
        
    Returns:
        Updated progress value
    """
    slides_total = presentation.get("slide_count", ProgressConstants.DEFAULT_SLIDE_COUNT)
    slides_completed = presentation.get("slides_completed", 0)
    
    if slides_total > 0:
        completion_ratio = slides_completed / slides_total
        sub_progress = completion_ratio * ProgressConstants.CONTENT_GENERATION_RANGE
        return base_progress + int(sub_progress)
    
    return base_progress


def calculate_image_progress(presentation: Dict[str, Any], base_progress: int) -> int:
    """
    Calculate progress for image generation phase
    
    Args:
        presentation: Presentation state
        base_progress: Base progress value
        
    Returns:
        Updated progress value
    """
    images_total = presentation.get("images_total", ProgressConstants.DEFAULT_IMAGE_COUNT)
    images_completed = presentation.get("images_completed", 0)
    
    if images_total > 0:
        completion_ratio = images_completed / images_total
        sub_progress = completion_ratio * ProgressConstants.IMAGE_GENERATION_RANGE
        return base_progress + int(sub_progress)
    
    return base_progress


def build_optimized_response(presentation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build optimized status response with modular structure
    
    Args:
        presentation: Presentation state object
        
    Returns:
        Response body dictionary
    """
    presentation_id = presentation["presentation_id"]
    status = presentation.get("status", PresentationStatus.PENDING.value)
    progress = calculate_progress(presentation)
    
    # Build base response
    response = build_base_response(presentation, progress)
    
    # Add status-specific details
    if status == PresentationStatus.FAILED.value:
        add_error_details(response, presentation)
    elif status == PresentationStatus.COMPLETED.value:
        add_completion_details(response, presentation)
    
    # Add navigation links
    add_navigation_links(response, presentation_id, status)
    
    # Add optional metadata and timing
    add_optional_fields(response, presentation)
    
    return response


def build_base_response(presentation: Dict[str, Any], progress: int) -> Dict[str, Any]:
    """
    Build the base response structure
    
    Args:
        presentation: Presentation state
        progress: Calculated progress percentage
        
    Returns:
        Base response dictionary
    """
    status = presentation.get("status", PresentationStatus.PENDING.value)
    
    return {
        "task_id": presentation["presentation_id"],
        "status": status,
        "progress": progress,
        "message": STATUS_MESSAGES.get(status, "Processing presentation"),
        "created_at": presentation.get("created_at"),
        "updated_at": presentation.get("updated_at"),
    }


def add_error_details(response: Dict[str, Any], presentation: Dict[str, Any]) -> None:
    """
    Add error details to failed presentations
    
    Args:
        response: Response dictionary to modify
        presentation: Presentation state
    """
    response["error"] = {
        "message": presentation.get("error_message", "Unknown error"),
        "code": presentation.get("error_code", "UNKNOWN"),
        "timestamp": presentation.get("error_timestamp"),
    }


def add_completion_details(response: Dict[str, Any], presentation: Dict[str, Any]) -> None:
    """
    Add completion details for successful presentations
    
    Args:
        response: Response dictionary to modify
        presentation: Presentation state
    """
    presentation_id = presentation["presentation_id"]
    
    result = {
        "presentation_id": presentation_id,
        "title": presentation.get("title"),
        "slide_count": presentation.get("slide_count"),
        "file_size": presentation.get("file_size"),
        "download_url": f"/presentations/{presentation_id}/download",
        "expires_at": presentation.get("download_expires_at"),
    }
    
    # Add available formats
    formats = []
    if presentation.get("pptx_key"):
        formats.append("pptx")
    if presentation.get("pdf_key"):
        formats.append("pdf")
    if presentation.get("html_key"):
        formats.append("html")
    result["formats"] = formats
    
    response["result"] = result


def add_navigation_links(response: Dict[str, Any], presentation_id: str, status: str) -> None:
    """
    Add HATEOAS navigation links
    
    Args:
        response: Response dictionary to modify
        presentation_id: Presentation ID
        status: Current status
    """
    links = {
        "self": f"/tasks/{presentation_id}",
        "presentation": f"/presentations/{presentation_id}",
    }
    
    if status == PresentationStatus.COMPLETED.value:
        links["download"] = f"/presentations/{presentation_id}/download"
    
    response["_links"] = links


def add_optional_fields(response: Dict[str, Any], presentation: Dict[str, Any]) -> None:
    """
    Add optional metadata and timing information
    
    Args:
        response: Response dictionary to modify
        presentation: Presentation state
    """
    # Add stage if available
    if presentation.get("stage"):
        response["stage"] = presentation["stage"]
    
    # Add metadata if present
    if presentation.get("metadata"):
        response["metadata"] = presentation["metadata"]
    
    # Add timing information
    if presentation.get("estimated_completion"):
        response["estimated_completion"] = presentation["estimated_completion"]
    
    if presentation.get("completed_at"):
        response["completed_at"] = presentation["completed_at"]
        
        # Calculate processing time
        processing_time = calculate_processing_time(
            presentation.get("created_at"),
            presentation.get("completed_at")
        )
        if processing_time is not None:
            response["processing_time_seconds"] = processing_time


def calculate_processing_time(created_at: Optional[str], completed_at: Optional[str]) -> Optional[float]:
    """
    Calculate processing time between creation and completion
    
    Args:
        created_at: Creation timestamp
        completed_at: Completion timestamp
        
    Returns:
        Processing time in seconds or None if calculation fails
    """
    if not created_at or not completed_at:
        return None
    
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        return (completed - created).total_seconds()
    except (ValueError, AttributeError) as e:
        logger.debug(f"Failed to calculate processing time: {e}")
        return None


def build_status_response(
    presentation: Dict[str, Any], progress: int
) -> Dict[str, Any]:
    """
    Legacy function maintained for backward compatibility
    Delegates to optimized response builder
    
    Args:
        presentation: Presentation state object
        progress: Progress percentage
        
    Returns:
        Response body
    """
    # Use the new optimized response builder
    return build_optimized_response(presentation)


def handle_get_session(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle GET /sessions/{id} requests - Get session information
    """
    try:
        # Extract session ID from path parameters
        path_parameters = event.get("pathParameters") or {}
        session_id = path_parameters.get("id")
        
        if not session_id:
            return create_response(
                400,
                {
                    "error": "VALIDATION_ERROR",
                    "message": "Session ID is required"
                },
            )

        if not validate_uuid(session_id):
            return create_response(
                400,
                {
                    "error": "VALIDATION_ERROR", 
                    "message": "Invalid session ID format. Must be a valid UUID."
                },
            )

        # Get session from DynamoDB sessions table
        session_data = get_session_data(session_id)

        if not session_data:
            return create_response(
                404,
                {
                    "error": "SESSION_NOT_FOUND",
                    "message": f"Session {session_id} not found"
                },
            )

        # Build response with session data
        response_data = {
            "session_id": session_data.get("session_id"),
            "user_id": session_data.get("user_id"),
            "session_name": session_data.get("session_name"),
            "status": session_data.get("status"),
            "created_at": session_data.get("created_at"),
            "last_activity": session_data.get("last_activity"),
            "expires_at": session_data.get("expires_at"),
            "metadata": session_data.get("metadata", {}),
        }

        logger.info(f"Successfully retrieved session: {session_id}")
        return create_response(200, response_data)

    except Exception as e:
        logger.error(f"Error getting session {session_id}: {str(e)}")
        return create_response(
            500,
            {
                "error": "INTERNAL_ERROR",
                "message": "Failed to retrieve session",
                "request_id": context.aws_request_id,
            },
        )


def get_session_data(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve session data from DynamoDB
    
    Args:
        session_id: Session ID to retrieve
        
    Returns:
        Session data dictionary or None if not found
    """
    try:
        # Get sessions table
        sessions_table_name = os.environ.get("DYNAMODB_SESSIONS_TABLE", "ai-ppt-assistant-dev-sessions")
        table = dynamodb.Table(sessions_table_name)
        
        # Query the session by ID
        response = table.get_item(
            Key={"session_id": session_id},
            ProjectionExpression="session_id, user_id, session_name, #status, created_at, last_activity, expires_at, metadata",
            ExpressionAttributeNames={
                "#status": "status"  # status is a reserved keyword in DynamoDB
            }
        )
        
        return response.get("Item")
        
    except ClientError as e:
        logger.error(f"DynamoDB error retrieving session {session_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving session {session_id}: {e}")
        return None