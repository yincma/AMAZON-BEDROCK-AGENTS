"""
Lambda function for modifying presentation slides
Handles PATCH /presentations/{presentationId}/slides/{slideId} requests
"""

import contextlib
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional


# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_utils import create_response
from utils.aws_service_utils import (
    get_bedrock_manager,
    get_dynamodb_manager,
    get_sqs_manager,
)
from utils.image_processor import process_visual_modification

# Import utilities
from utils.timeout_manager import (
    TimeoutError,
    TimeoutManager,
    create_timeout_config,
    timeout_handler,
)

# Environment variables (now using standardized config management)
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "presentations")
CONTENT_AGENT_ID = os.environ.get("CONTENT_AGENT_ID")
CONTENT_ALIAS_ID = os.environ.get("CONTENT_ALIAS_ID")
VISUAL_AGENT_ID = os.environ.get("VISUAL_AGENT_ID")
VISUAL_ALIAS_ID = os.environ.get("VISUAL_ALIAS_ID")
COMPILER_AGENT_ID = os.environ.get("COMPILER_AGENT_ID")
COMPILER_ALIAS_ID = os.environ.get("COMPILER_ALIAS_ID")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
S3_BUCKET = os.environ.get("S3_BUCKET")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize service managers (shared approach)
dynamodb_manager = get_dynamodb_manager()
sqs_manager = get_sqs_manager()
bedrock_manager = get_bedrock_manager()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for slide modification requests with timeout management

    Args:
        event: API Gateway event containing the request
        context: Lambda context

    Returns:
        API Gateway response
    """
    # Initialize timeout management
    timeout_config = create_timeout_config(context, grace_period=5)

    with timeout_handler(context, timeout_config) as timeout_manager:
        try:
            # Extract path parameters
            path_params = event.get("pathParameters", {})
            presentation_id = path_params.get("presentationId")
            slide_id = path_params.get("slideId")

            if not presentation_id or not slide_id:
                return create_response(
                    400,
                    {
                        "error": "INVALID_REQUEST",
                        "message": "Presentation ID and Slide ID are required",
                        "request_id": context.request_id,
                    },
                )

            # Parse request body
            body = json.loads(event.get("body", "{}"))

            # Validate modification request
            validation_error = validate_modification(body)
            if validation_error:
                return create_response(
                    400,
                    {
                        "error": "INVALID_MODIFICATION",
                        "message": validation_error,
                        "request_id": context.request_id,
                    },
                )

            # Retrieve presentation state
            presentation = get_presentation_state(presentation_id)

            if not presentation:
                return create_response(
                    404,
                    {
                        "error": "NOT_FOUND",
                        "message": "Presentation not found",
                        "presentation_id": presentation_id,
                        "request_id": context.request_id,
                    },
                )

            # Check if presentation is modifiable
            if presentation.get("status") not in ["completed", "modified"]:
                return create_response(
                    409,
                    {
                        "error": "NOT_MODIFIABLE",
                        "message": "Presentation must be completed before modification",
                        "status": presentation.get("status"),
                        "request_id": context.request_id,
                    },
                )

            # Validate slide exists
            slide_count = presentation.get("slide_count", 0)
            try:
                slide_number = int(slide_id)
                if slide_number < 1 or slide_number > slide_count:
                    return create_response(
                        404,
                        {
                            "error": "SLIDE_NOT_FOUND",
                            "message": f"Slide {slide_id} not found. Presentation has {slide_count} slides.",
                            "request_id": context.request_id,
                        },
                    )
            except ValueError:
                return create_response(
                    400,
                    {
                        "error": "INVALID_SLIDE_ID",
                        "message": "Slide ID must be a number",
                        "request_id": context.request_id,
                    },
                )

            # Create modification task
            modification_task = create_modification_task(
                presentation_id, slide_id, presentation, body
            )

            # Update presentation state
            update_presentation_state(presentation_id, modification_task)

            # Queue modification task
            queue_modification_task(modification_task)

            # Trigger appropriate agent based on modification type
            agent_response = trigger_modification_agent(
                modification_task, timeout_manager
            )

            # Return success response with timeout info
            response_body = {
                "task_id": modification_task["task_id"],
                "presentation_id": presentation_id,
                "slide_id": slide_id,
                "modification_type": modification_task["modification_type"],
                "status": "processing",
                "message": "Slide modification started",
                "created_at": modification_task["created_at"],
                "performance_summary": timeout_manager.get_performance_summary(),
                "_links": {
                    "self": f"/presentations/{presentation_id}/slides/{slide_id}",
                    "status": f"/tasks/{modification_task['task_id']}",
                    "presentation": f"/presentations/{presentation_id}",
                },
            }

            # Add visual processing results if available
            if "visual_processing" in agent_response:
                response_body["visual_processing"] = agent_response["visual_processing"]

            return create_response(202, response_body)

        except Exception as e:
            logger.error(f"Error modifying slide: {str(e)}")
            return create_response(
                500,
                {
                    "error": "INTERNAL_ERROR",
                    "message": "Failed to modify slide",
                    "request_id": context.request_id,
                },
            )


def validate_modification(body: Dict[str, Any]) -> Optional[str]:
    """
    Validate modification request

    Args:
        body: Request body

    Returns:
        Error message if validation fails, None otherwise
    """
    # Check for at least one modification
    if not body:
        return "No modifications specified"

    # Validate content modifications
    if "content" in body:
        content = body["content"]
        if not isinstance(content, dict):
            return "Content must be an object"

        if "title" in content and len(content["title"]) > 200:
            return "Slide title must be less than 200 characters"

        if "bullets" in content:
            if not isinstance(content["bullets"], list):
                return "Bullets must be an array"
            if len(content["bullets"]) > 10:
                return "Maximum 10 bullet points per slide"
            for bullet in content["bullets"]:
                if len(bullet) > 100:
                    return "Each bullet point must be less than 100 characters"

    # Validate visual modifications
    if "visual" in body:
        visual = body["visual"]
        if not isinstance(visual, dict):
            return "Visual must be an object"

        if "action" in visual:
            valid_actions = ["regenerate", "replace", "remove", "reposition"]
            if visual["action"] not in valid_actions:
                return f"Visual action must be one of: {', '.join(valid_actions)}"

        if "style" in visual:
            valid_styles = [
                "realistic",
                "abstract",
                "minimalist",
                "technical",
                "creative",
            ]
            if visual["style"] not in valid_styles:
                return f"Visual style must be one of: {', '.join(valid_styles)}"

    # Validate speaker notes modifications
    if "speaker_notes" in body:
        notes = body["speaker_notes"]
        if not isinstance(notes, str):
            return "Speaker notes must be a string"
        if len(notes) > 2000:
            return "Speaker notes must be less than 2000 characters"

    # Validate layout modifications
    if "layout" in body:
        layout = body["layout"]
        if not isinstance(layout, str):
            return "Layout must be a string"
        valid_layouts = ["title", "content", "two_column", "comparison", "image_focus"]
        if layout not in valid_layouts:
            return f"Layout must be one of: {', '.join(valid_layouts)}"

    return None


def get_presentation_state(presentation_id: str) -> Dict[str, Any]:
    """
    Retrieve presentation state from DynamoDB

    Args:
        presentation_id: Unique presentation ID

    Returns:
        Presentation state object or None if not found
    """
    table = dynamodb_manager.dynamodb.Table(TABLE_NAME)

    try:
        response = table.get_item(Key={"presentation_id": presentation_id})
        return response.get("Item")
    except Exception as e:
        logger.error(f"Error retrieving presentation state: {str(e)}")
        return None


def create_modification_task(
    presentation_id: str,
    slide_id: str,
    presentation: Dict[str, Any],
    modifications: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a modification task object

    Args:
        presentation_id: Presentation ID
        slide_id: Slide ID
        presentation: Current presentation state
        modifications: Requested modifications

    Returns:
        Modification task object
    """
    import uuid

    current_time = datetime.utcnow().isoformat() + "Z"
    task_id = str(uuid.uuid4())

    # Determine modification type
    modification_types = []
    if "content" in modifications:
        modification_types.append("content")
    if "visual" in modifications:
        modification_types.append("visual")
    if "speaker_notes" in modifications:
        modification_types.append("notes")
    if "layout" in modifications:
        modification_types.append("layout")

    return {
        "task_id": task_id,
        "presentation_id": presentation_id,
        "slide_id": slide_id,
        "slide_number": int(slide_id),
        "modification_type": ",".join(modification_types),
        "modifications": modifications,
        "original_presentation": {
            "title": presentation.get("title"),
            "language": presentation.get("language"),
            "style": presentation.get("style"),
        },
        "status": "pending",
        "created_at": current_time,
        "updated_at": current_time,
    }


def update_presentation_state(
    presentation_id: str, modification_task: Dict[str, Any]
) -> None:
    """
    Update presentation state with modification info

    Args:
        presentation_id: Presentation ID
        modification_task: Modification task object
    """
    table = dynamodb_manager.dynamodb.Table(TABLE_NAME)

    try:
        table.update_item(
            Key={"presentation_id": presentation_id},
            UpdateExpression="SET #status = :status, last_modified_at = :now, "
            "modification_count = if_not_exists(modification_count, :zero) + :one, "
            "active_modification = :task",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "modifying",
                ":now": modification_task["created_at"],
                ":zero": 0,
                ":one": 1,
                ":task": modification_task["task_id"],
            },
        )
        logger.info(f"Updated presentation state for modification: {presentation_id}")
    except Exception as e:
        logger.error(f"Failed to update presentation state: {str(e)}")


def queue_modification_task(task: Dict[str, Any]) -> None:
    """
    Queue modification task for async processing

    Args:
        task: Modification task object
    """
    if not QUEUE_URL:
        logger.warning("SQS queue URL not configured, skipping queuing")
        return

    message = {
        "task_id": task["task_id"],
        "type": "modify_slide",
        "priority": "high",  # Modifications get higher priority
        "data": task,
    }

    try:
        sqs_manager.sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message),
            MessageAttributes={
                "task_type": {"StringValue": "modification", "DataType": "String"},
                "priority": {"StringValue": "high", "DataType": "String"},
            },
        )
        logger.info(f"Queued modification task: {task['task_id']}")
    except Exception as e:
        logger.error(f"Failed to queue modification task: {str(e)}")


def trigger_modification_agent(
    task: Dict[str, Any], timeout_manager: Optional[TimeoutManager] = None
) -> Dict[str, Any]:
    """
    Trigger appropriate Bedrock agent for modification with enhanced image processing

    Args:
        task: Modification task object
        timeout_manager: Timeout management instance

    Returns:
        Agent response
    """
    modifications = task["modifications"]
    responses = {}

    # Trigger Content Agent for content modifications
    if "content" in modifications or "speaker_notes" in modifications:
        if CONTENT_AGENT_ID and CONTENT_ALIAS_ID:
            content_input = f"""
            Please modify slide {task['slide_id']} of the presentation:

            Original Title: {task['original_presentation']['title']}
            Language: {task['original_presentation']['language']}
            Style: {task['original_presentation']['style']}

            Modifications requested:
            {json.dumps(modifications.get('content', {}))}

            Speaker Notes Update: {modifications.get('speaker_notes', 'No changes')}

            Maintain consistency with the rest of the presentation.
            """

            try:
                response = bedrock_manager.bedrock_agent_runtime.invoke_agent(
                    agentId=CONTENT_AGENT_ID,
                    agentAliasId=CONTENT_ALIAS_ID,
                    sessionId=task["presentation_id"],
                    inputText=content_input.strip(),
                    enableTrace=True,
                )
                responses["content"] = process_agent_response(response)
                logger.info(
                    f"Content Agent invoked for modification: {task['task_id']}"
                )
            except Exception as e:
                logger.error(f"Error invoking Content Agent: {str(e)}")
                responses["content"] = {"error": str(e)}

    # Enhanced visual modifications with complete image processing
    if "visual" in modifications:
        visual_mods = modifications["visual"]

        try:
            # Process image modifications using enhanced image processor
            if timeout_manager:
                timeout_manager.check_timeout_status("visual_processing")

            with (
                timeout_manager.operation("visual_modification")
                if timeout_manager
                else contextlib.nullcontext()
            ):
                visual_result = process_visual_modification(
                    presentation_id=task["presentation_id"],
                    slide_number=int(task["slide_id"]),
                    visual_modifications=visual_mods,
                    timeout_manager=timeout_manager,
                )

                responses["visual_processing"] = visual_result

                # If visual processing succeeded, also invoke Visual Agent for coordination
                if visual_result.get("success") and VISUAL_AGENT_ID and VISUAL_ALIAS_ID:
                    visual_input = f"""
                    Visual modification completed for slide {task['slide_id']}:

                    Action taken: {visual_mods.get('action', 'modify')}
                    Processing result: {visual_result.get('message', 'Completed')}

                    Original request: {json.dumps(visual_mods)}
                    Presentation style: {task['original_presentation']['style']}

                    Please coordinate any additional visual adjustments needed for consistency.
                    """

                    try:
                        agent_response = bedrock_manager.invoke_agent(
                            agentId=VISUAL_AGENT_ID,
                            agentAliasId=VISUAL_ALIAS_ID,
                            sessionId=task["presentation_id"],
                            inputText=visual_input.strip(),
                            enableTrace=True,
                        )
                        responses["visual_agent"] = process_agent_response(
                            agent_response
                        )
                        logger.info(
                            f"Visual Agent coordinated for modification: {task['task_id']}"
                        )
                    except Exception as e:
                        logger.error(f"Error invoking Visual Agent: {str(e)}")
                        responses["visual_agent"] = {"error": str(e)}

                logger.info(
                    f"Visual processing completed for modification: {task['task_id']}"
                )

        except TimeoutError as e:
            logger.error(f"Timeout during visual processing: {e}")
            responses["visual_processing"] = {
                "success": False,
                "error": "Visual processing timeout",
                "details": str(e),
            }
        except Exception as e:
            logger.error(f"Error processing visual modifications: {str(e)}")
            responses["visual_processing"] = {"success": False, "error": str(e)}

    return responses


def process_agent_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process streaming response from Bedrock agent

    Args:
        response: Agent response

    Returns:
        Processed response
    """
    event_stream = response.get("completion", [])
    result = ""

    for event in event_stream:
        if "chunk" in event:
            chunk = event["chunk"]
            if "bytes" in chunk:
                result += chunk["bytes"].decode("utf-8")

    return {"response": result}


# create_response function moved to utils.api_utils for reuse
