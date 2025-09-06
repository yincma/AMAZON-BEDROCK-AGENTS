"""
Lambda function for checking presentation generation status
Handles GET /tasks/{taskId} and GET /presentations/{presentationId}/status requests
"""

import logging
import os
import sys
from typing import Any, Dict

import boto3

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_utils import create_response

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Environment variables
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "presentations")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for status check requests

    Args:
        event: API Gateway event containing the request
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        # Extract task/presentation ID from path parameters
        path_params = event.get("pathParameters", {})
        task_id = path_params.get("taskId") or path_params.get("presentationId")

        if not task_id:
            return create_response(
                400,
                {
                    "error": "INVALID_REQUEST",
                    "message": "Task ID is required",
                    "request_id": context.aws_request_id,
                },
            )

        # Retrieve presentation state from DynamoDB
        presentation = get_presentation_state(task_id)

        if not presentation:
            return create_response(
                404,
                {
                    "error": "NOT_FOUND",
                    "message": "Task not found",
                    "task_id": task_id,
                    "request_id": context.aws_request_id,
                },
            )

        # Calculate progress percentage
        progress = calculate_progress(presentation)

        # Build response based on status
        response_body = build_status_response(presentation, progress)

        return create_response(200, response_body)

    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        return create_response(
            500,
            {
                "error": "INTERNAL_ERROR",
                "message": "Failed to retrieve status",
                "request_id": context.aws_request_id,
            },
        )


def get_presentation_state(presentation_id: str) -> Dict[str, Any]:
    """
    Retrieve presentation state from DynamoDB

    Args:
        presentation_id: Unique presentation ID

    Returns:
        Presentation state object or None if not found
    """
    table = dynamodb.Table(TABLE_NAME)

    try:
        response = table.get_item(Key={"presentation_id": presentation_id})
        return response.get("Item")
    except Exception as e:
        logger.error(f"Error retrieving presentation state: {str(e)}")
        return None


def calculate_progress(presentation: Dict[str, Any]) -> int:
    """
    Calculate progress percentage based on status and stage

    Args:
        presentation: Presentation state object

    Returns:
        Progress percentage (0-100)
    """
    status = presentation.get("status", "pending")
    presentation.get("stage", "")

    # Status-based progress mapping
    progress_map = {
        "pending": 0,
        "outlining": 20,
        "content_generation": 40,
        "image_generation": 60,
        "compiling": 80,
        "completed": 100,
        "failed": presentation.get("progress", 0),
    }

    # Get base progress from status
    base_progress = progress_map.get(status, 0)

    # Add sub-progress for stages within a status
    if status == "content_generation":
        slides_total = presentation.get("slide_count", 15)
        slides_completed = presentation.get("slides_completed", 0)
        if slides_total > 0:
            sub_progress = (slides_completed / slides_total) * 20
            base_progress = 40 + int(sub_progress)

    elif status == "image_generation":
        images_total = presentation.get("images_total", 10)
        images_completed = presentation.get("images_completed", 0)
        if images_total > 0:
            sub_progress = (images_completed / images_total) * 20
            base_progress = 60 + int(sub_progress)

    return min(base_progress, 100)


def build_status_response(
    presentation: Dict[str, Any], progress: int
) -> Dict[str, Any]:
    """
    Build the status response object

    Args:
        presentation: Presentation state object
        progress: Progress percentage

    Returns:
        Response body
    """
    response = {
        "task_id": presentation["presentation_id"],
        "status": presentation.get("status", "pending"),
        "progress": progress,
        "created_at": presentation.get("created_at"),
        "updated_at": presentation.get("updated_at"),
    }

    # Add message based on status
    status_messages = {
        "pending": "Presentation generation queued",
        "outlining": "Creating presentation outline",
        "content_generation": "Generating slide content",
        "image_generation": "Creating visual elements",
        "compiling": "Assembling final presentation",
        "completed": "Presentation ready for download",
        "failed": "Presentation generation failed",
    }
    response["message"] = status_messages.get(
        presentation.get("status"), "Processing presentation"
    )

    # Add stage details if available
    if presentation.get("stage"):
        response["stage"] = presentation["stage"]

    # Add error details if failed
    if presentation.get("status") == "failed" and presentation.get("error"):
        response["error"] = {
            "message": presentation.get("error_message", "Unknown error"),
            "code": presentation.get("error_code", "UNKNOWN"),
            "timestamp": presentation.get("error_timestamp"),
        }

    # Add result information if completed
    if presentation.get("status") == "completed":
        response["result"] = {
            "presentation_id": presentation["presentation_id"],
            "title": presentation.get("title"),
            "slide_count": presentation.get("slide_count"),
            "file_size": presentation.get("file_size"),
            "download_url": f"/presentations/{presentation['presentation_id']}/download",
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
        response["result"]["formats"] = formats

    # Add links for navigation
    response["_links"] = {
        "self": f"/tasks/{presentation['presentation_id']}",
        "presentation": f"/presentations/{presentation['presentation_id']}",
    }

    if presentation.get("status") == "completed":
        response["_links"][
            "download"
        ] = f"/presentations/{presentation['presentation_id']}/download"

    # Add metadata if present
    if presentation.get("metadata"):
        response["metadata"] = presentation["metadata"]

    # Add timing information
    if presentation.get("estimated_completion"):
        response["estimated_completion"] = presentation["estimated_completion"]

    if presentation.get("completed_at"):
        response["completed_at"] = presentation["completed_at"]

        # Calculate processing time
        if presentation.get("created_at"):
            try:
                from datetime import datetime

                created = datetime.fromisoformat(
                    presentation["created_at"].replace("Z", "+00:00")
                )
                completed = datetime.fromisoformat(
                    presentation["completed_at"].replace("Z", "+00:00")
                )
                processing_time = (completed - created).total_seconds()
                response["processing_time_seconds"] = processing_time
            except (ValueError, AttributeError):
                # Ignore errors in processing time calculation
                pass

    return response
