"""
Lambda function for downloading presentations
Handles GET /presentations/{presentationId}/download requests
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import boto3

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_utils import create_response

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# Environment variables
# Use DYNAMODB_TASKS_TABLE for tasks, fallback to DYNAMODB_TABLE for compatibility
TASKS_TABLE = os.environ.get("DYNAMODB_TASKS_TABLE", os.environ.get("DYNAMODB_TABLE", "ai-ppt-assistant-dev-tasks"))
S3_BUCKET = os.environ.get("S3_BUCKET")
DOWNLOAD_EXPIRY_SECONDS = int(
    os.environ.get("DOWNLOAD_EXPIRY_SECONDS", "3600")
)  # 1 hour

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for presentation download requests

    Args:
        event: API Gateway event containing the request
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        # Extract presentation ID from path parameters
        path_params = event.get("pathParameters", {})
        # Support both 'id' and 'presentationId' for compatibility
        presentation_id = path_params.get("id") or path_params.get("presentationId")

        if not presentation_id:
            return create_response(
                400,
                {
                    "error": "INVALID_REQUEST",
                    "message": "Presentation ID is required",
                    "request_id": context.aws_request_id,
                },
            )

        # Extract query parameters
        query_params = event.get("queryStringParameters", {}) or {}
        format_type = query_params.get("format", "pptx").lower()

        # Validate format
        valid_formats = ["pptx", "pdf", "html", "png"]
        if format_type not in valid_formats:
            return create_response(
                400,
                {
                    "error": "INVALID_FORMAT",
                    "message": f"Format must be one of: {', '.join(valid_formats)}",
                    "request_id": context.aws_request_id,
                },
            )

        # Retrieve presentation state from DynamoDB
        presentation = get_presentation_state(presentation_id)

        if not presentation:
            return create_response(
                404,
                {
                    "error": "NOT_FOUND",
                    "message": "Presentation not found",
                    "presentation_id": presentation_id,
                    "request_id": context.aws_request_id,
                },
            )

        # Check if presentation is completed
        if presentation.get("status") != "completed":
            return create_response(
                409,
                {
                    "error": "NOT_READY",
                    "message": "Presentation is not ready for download",
                    "status": presentation.get("status", "unknown"),
                    "presentation_id": presentation_id,
                    "request_id": context.aws_request_id,
                },
            )

        # Get S3 key for requested format
        s3_key = get_s3_key(presentation, format_type)

        if not s3_key:
            return create_response(
                404,
                {
                    "error": "FORMAT_NOT_AVAILABLE",
                    "message": f"Presentation not available in {format_type} format",
                    "available_formats": get_available_formats(presentation),
                    "presentation_id": presentation_id,
                    "request_id": context.aws_request_id,
                },
            )

        # Check if direct download is requested
        if query_params.get("direct", "false").lower() == "true":
            # Return redirect to presigned URL
            presigned_url = generate_presigned_url(s3_key, presentation_id, format_type)

            if not presigned_url:
                return create_response(
                    500,
                    {
                        "error": "URL_GENERATION_FAILED",
                        "message": "Failed to generate download URL",
                        "request_id": context.aws_request_id,
                    },
                )

            return {
                "statusCode": 302,
                "headers": {
                    "Location": presigned_url,
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                },
            }

        # Generate presigned URL
        presigned_url = generate_presigned_url(s3_key, presentation_id, format_type)

        if not presigned_url:
            return create_response(
                500,
                {
                    "error": "URL_GENERATION_FAILED",
                    "message": "Failed to generate download URL",
                    "request_id": context.aws_request_id,
                },
            )

        # Update download count
        update_download_count(presentation_id)

        # Build response
        response_body = {
            "presentation_id": presentation_id,
            "title": presentation.get("title"),
            "format": format_type,
            "download_url": presigned_url,
            "expires_at": (
                datetime.utcnow() + timedelta(seconds=DOWNLOAD_EXPIRY_SECONDS)
            ).isoformat()
            + "Z",
            "file_size": get_file_size(s3_key),
            "content_type": get_content_type(format_type),
            "_links": {
                "self": f"/presentations/{presentation_id}/download?format={format_type}",
                "presentation": f"/presentations/{presentation_id}",
                "status": f"/presentations/{presentation_id}/status",
            },
        }

        # Add alternative formats
        available_formats = get_available_formats(presentation)
        if len(available_formats) > 1:
            response_body["alternative_formats"] = [
                {
                    "format": fmt,
                    "url": f"/presentations/{presentation_id}/download?format={fmt}",
                }
                for fmt in available_formats
                if fmt != format_type
            ]

        return create_response(200, response_body)

    except Exception as e:
        logger.error(f"Error generating download URL: {str(e)}")
        return create_response(
            500,
            {
                "error": "INTERNAL_ERROR",
                "message": "Failed to process download request",
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
    table = dynamodb.Table(TASKS_TABLE)

    try:
        # Tasks table uses task_id as the key, not presentation_id
        response = table.get_item(Key={"task_id": presentation_id})
        item = response.get("Item")
        
        # If not found by task_id, try as presentation_id (backward compatibility)
        if not item:
            response = table.get_item(Key={"presentation_id": presentation_id})
            item = response.get("Item")
        
        return item
    except Exception as e:
        logger.error(f"Error retrieving presentation state: {str(e)}")
        return None


def get_s3_key(presentation: Dict[str, Any], format_type: str) -> Optional[str]:
    """
    Get S3 key for requested format

    Args:
        presentation: Presentation state object
        format_type: Requested format

    Returns:
        S3 key or None if not available
    """
    key_mapping = {
        "pptx": "pptx_key",
        "pdf": "pdf_key",
        "html": "html_key",
        "png": "images_key",
    }

    key_field = key_mapping.get(format_type)
    if not key_field:
        return None

    return presentation.get(key_field)


def get_available_formats(presentation: Dict[str, Any]) -> list:
    """
    Get list of available formats for presentation

    Args:
        presentation: Presentation state object

    Returns:
        List of available format strings
    """
    formats = []
    if presentation.get("pptx_key"):
        formats.append("pptx")
    if presentation.get("pdf_key"):
        formats.append("pdf")
    if presentation.get("html_key"):
        formats.append("html")
    if presentation.get("images_key"):
        formats.append("png")

    return formats


def generate_presigned_url(
    s3_key: str, presentation_id: str, format_type: str
) -> Optional[str]:
    """
    Generate presigned URL for S3 object download

    Args:
        s3_key: S3 object key
        presentation_id: Presentation ID
        format_type: File format

    Returns:
        Presigned URL or None if generation fails
    """
    if not S3_BUCKET:
        logger.error("S3 bucket not configured")
        return None

    try:
        # Generate filename for download
        filename = f"presentation_{presentation_id}.{format_type}"
        if format_type == "png":
            filename = f"presentation_{presentation_id}_slides.zip"

        # Generate presigned URL
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": s3_key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=DOWNLOAD_EXPIRY_SECONDS,
        )

        return presigned_url

    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        return None


def get_file_size(s3_key: str) -> Optional[int]:
    """
    Get file size from S3

    Args:
        s3_key: S3 object key

    Returns:
        File size in bytes or None
    """
    if not S3_BUCKET:
        return None

    try:
        response = s3.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return response.get("ContentLength")
    except Exception as e:
        logger.error(f"Error getting file size for {s3_key}: {str(e)}")
        return None


def get_content_type(format_type: str) -> str:
    """
    Get content type for format

    Args:
        format_type: File format

    Returns:
        MIME content type
    """
    content_types = {
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
        "html": "text/html",
        "png": "application/zip",  # For multiple images
    }

    return content_types.get(format_type, "application/octet-stream")


def update_download_count(presentation_id: str) -> None:
    """
    Update download count for presentation

    Args:
        presentation_id: Presentation ID
    """
    table = dynamodb.Table(TABLE_NAME)

    try:
        table.update_item(
            Key={"presentation_id": presentation_id},
            UpdateExpression="SET download_count = if_not_exists(download_count, :zero) + :one, last_downloaded_at = :now",
            ExpressionAttributeValues={
                ":zero": 0,
                ":one": 1,
                ":now": datetime.utcnow().isoformat() + "Z",
            },
        )
    except Exception as e:
        logger.warning(f"Failed to update download count: {str(e)}")
