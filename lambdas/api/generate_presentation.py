"""
Lambda function for generating presentations
Handles POST /presentations/generate requests
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import boto3

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_utils import create_response

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime")
s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# Environment variables
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "presentations")
ORCHESTRATOR_AGENT_ID = os.environ.get("ORCHESTRATOR_AGENT_ID")
ORCHESTRATOR_ALIAS_ID = os.environ.get("ORCHESTRATOR_ALIAS_ID")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
S3_BUCKET = os.environ.get("S3_BUCKET")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for presentation generation requests

    Args:
        event: API Gateway event containing the request
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))

        # Validate required parameters
        validation_error = validate_request(body)
        if validation_error:
            return create_response(
                400,
                {
                    "error": "INVALID_REQUEST",
                    "message": validation_error,
                    "request_id": context.request_id,
                },
            )

        # Generate unique presentation ID
        presentation_id = str(uuid.uuid4())
        session_id = body.get("session_id", str(uuid.uuid4()))

        # Create presentation task
        task = create_presentation_task(presentation_id, session_id, body)

        # Store initial state in DynamoDB
        store_presentation_state(task)

        # Queue task for async processing
        queue_presentation_task(task)

        # Trigger Bedrock Orchestrator Agent
        invoke_orchestrator_agent(task)

        # Calculate estimated completion time
        estimated_completion = calculate_completion_time(body)

        # Return success response
        return create_response(
            202,
            {
                "task_id": presentation_id,
                "status": "pending",
                "created_at": task["created_at"],
                "estimated_completion": estimated_completion,
                "message": "Presentation generation started",
                "_links": {
                    "self": f"/tasks/{presentation_id}",
                    "result": f"/presentations/{presentation_id}",
                    "status": f"/tasks/{presentation_id}/status",
                },
            },
        )

    except Exception as e:
        logger.error(f"Error generating presentation: {str(e)}")
        return create_response(
            500,
            {
                "error": "INTERNAL_ERROR",
                "message": "Failed to generate presentation",
                "request_id": context.request_id,
            },
        )


def validate_request(body: Dict[str, Any]) -> Optional[str]:
    """
    Validate request parameters

    Args:
        body: Request body

    Returns:
        Error message if validation fails, None otherwise
    """
    # Required fields
    if not body.get("title"):
        return "Title is required"

    if not body.get("topic"):
        return "Topic is required"

    # Validate field lengths
    if len(body.get("title", "")) > 200:
        return "Title must be less than 200 characters"

    if len(body.get("topic", "")) > 1000:
        return "Topic must be less than 1000 characters"

    # Validate optional fields
    duration = body.get("duration")
    if duration and (duration < 5 or duration > 120):
        return "Duration must be between 5 and 120 minutes"

    slide_count = body.get("slide_count")
    if slide_count and (slide_count < 5 or slide_count > 100):
        return "Slide count must be between 5 and 100"

    language = body.get("language", "en")
    valid_languages = ["en", "ja", "zh", "es", "fr", "de", "pt", "ko"]
    if language not in valid_languages:
        return f"Language must be one of: {', '.join(valid_languages)}"

    style = body.get("style", "professional")
    valid_styles = ["professional", "creative", "minimalist", "technical", "academic"]
    if style not in valid_styles:
        return f"Style must be one of: {', '.join(valid_styles)}"

    return None


def create_presentation_task(
    presentation_id: str, session_id: str, body: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a presentation task object

    Args:
        presentation_id: Unique presentation ID
        session_id: Session ID
        body: Request body

    Returns:
        Task object
    """
    current_time = datetime.utcnow().isoformat() + "Z"

    return {
        "presentation_id": presentation_id,
        "session_id": session_id,
        "title": body["title"],
        "topic": body["topic"],
        "audience": body.get("audience", "general"),
        "duration": body.get("duration", 20),
        "slide_count": body.get("slide_count", 15),
        "language": body.get("language", "en"),
        "style": body.get("style", "professional"),
        "template": body.get("template", "default"),
        "include_speaker_notes": body.get("include_speaker_notes", True),
        "include_images": body.get("include_images", True),
        "status": "pending",
        "progress": 0,
        "created_at": current_time,
        "updated_at": current_time,
        "metadata": body.get("metadata", {}),
        "user_preferences": body.get("preferences", {}),
    }


def store_presentation_state(task: Dict[str, Any]) -> None:
    """
    Store presentation state in DynamoDB

    Args:
        task: Task object to store
    """
    table = dynamodb.Table(TABLE_NAME)

    # Add TTL (30 days from creation)
    ttl = int((datetime.utcnow() + timedelta(days=30)).timestamp())
    task["ttl"] = ttl

    table.put_item(Item=task)
    logger.info(f"Stored presentation state: {task['presentation_id']}")


def queue_presentation_task(task: Dict[str, Any]) -> None:
    """
    Queue task for async processing

    Args:
        task: Task object to queue
    """
    if not QUEUE_URL:
        logger.warning("SQS queue URL not configured, skipping queuing")
        return

    message = {
        "task_id": task["presentation_id"],
        "type": "generate_presentation",
        "priority": "normal",
        "data": task,
    }

    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(message),
        MessageAttributes={
            "task_type": {"StringValue": "presentation", "DataType": "String"},
            "priority": {"StringValue": "normal", "DataType": "String"},
        },
    )

    logger.info(f"Queued presentation task: {task['presentation_id']}")


def invoke_orchestrator_agent(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke Bedrock Orchestrator Agent to start generation

    Args:
        task: Task object

    Returns:
        Agent response
    """
    if not ORCHESTRATOR_AGENT_ID or not ORCHESTRATOR_ALIAS_ID:
        logger.warning("Orchestrator agent not configured, skipping agent invocation")
        return {}

    # Prepare input for the agent
    agent_input = f"""
    Please generate a presentation with the following requirements:

    Title: {task['title']}
    Topic: {task['topic']}
    Target Audience: {task['audience']}
    Duration: {task['duration']} minutes
    Number of Slides: {task['slide_count']}
    Language: {task['language']}
    Style: {task['style']}
    Template: {task['template']}
    Include Speaker Notes: {task['include_speaker_notes']}
    Include Images: {task['include_images']}

    Additional Context: {json.dumps(task.get('metadata', {}))}
    """

    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=ORCHESTRATOR_AGENT_ID,
            agentAliasId=ORCHESTRATOR_ALIAS_ID,
            sessionId=task["session_id"],
            inputText=agent_input.strip(),
            enableTrace=True,
        )

        # Process streaming response
        event_stream = response.get("completion", [])
        result = ""
        for event in event_stream:
            if "chunk" in event:
                chunk = event["chunk"]
                if "bytes" in chunk:
                    result += chunk["bytes"].decode("utf-8")

        logger.info(f"Orchestrator agent invoked for: {task['presentation_id']}")
        return {"response": result, "session_id": task["session_id"]}

    except Exception as e:
        logger.error(f"Error invoking orchestrator agent: {str(e)}")
        return {"error": str(e)}


def calculate_completion_time(body: Dict[str, Any]) -> str:
    """
    Calculate estimated completion time based on request parameters

    Args:
        body: Request body

    Returns:
        ISO format timestamp
    """
    # Base time: 30 seconds
    base_seconds = 30

    # Add time based on slide count
    slide_count = body.get("slide_count", 15)
    slide_seconds = slide_count * 3

    # Add time for images
    if body.get("include_images", True):
        image_seconds = slide_count * 5
    else:
        image_seconds = 0

    # Add time for speaker notes
    if body.get("include_speaker_notes", True):
        notes_seconds = slide_count * 2
    else:
        notes_seconds = 0

    # Calculate total time (max 180 seconds)
    total_seconds = min(
        base_seconds + slide_seconds + image_seconds + notes_seconds, 180
    )

    completion_time = datetime.utcnow() + timedelta(seconds=total_seconds)
    return completion_time.isoformat() + "Z"
