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

# Initialize AWS clients with explicit region (AWS Expert fix)
# AWS Lambda automatically sets AWS_REGION, but fallback to us-east-1
AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)
sqs = boto3.client("sqs", region_name=AWS_REGION)

# AWS Expert: Log region for debugging
print(f"AWS Expert Debug - Using region: {AWS_REGION}")

# Environment variables
# Use DYNAMODB_TABLE for tasks (corrected after infrastructure fix)
TASKS_TABLE = os.environ.get("DYNAMODB_TABLE", "ai-ppt-assistant-dev-tasks")
SESSIONS_TABLE = os.environ.get("DYNAMODB_SESSIONS_TABLE", "ai-ppt-assistant-dev-sessions")
ORCHESTRATOR_AGENT_ID = os.environ.get("ORCHESTRATOR_AGENT_ID")
ORCHESTRATOR_ALIAS_ID = os.environ.get("ORCHESTRATOR_ALIAS_ID")
QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
S3_BUCKET = os.environ.get("S3_BUCKET")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for multiple API endpoints:
    - POST /presentations - Create presentation
    - POST /sessions - Create session  
    - POST /agents/{name}/execute - Execute agent

    Args:
        event: API Gateway event containing the request
        context: Lambda context

    Returns:
        API Gateway response
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
        if resource == "/presentations" and http_method == "POST":
            return handle_create_presentation(event, context)
        elif resource == "/sessions" and http_method == "POST":
            return handle_create_session(event, context)
        elif resource == "/agents/{name}/execute" and http_method == "POST":
            return handle_execute_agent(event, context)
        # Fallback to path-based routing
        elif path.endswith("/presentations") and http_method == "POST":
            return handle_create_presentation(event, context)
        elif path.endswith("/sessions") and http_method == "POST":
            return handle_create_session(event, context)
        elif "/agents/" in path and path.endswith("/execute") and http_method == "POST":
            return handle_execute_agent(event, context)
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


def handle_create_presentation(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle POST /presentations requests
    """
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))

        # Validate required parameters
        validation_error = validate_presentation_request(body)
        if validation_error:
            return create_response(
                400,
                {
                    "error": "INVALID_REQUEST",
                    "message": validation_error,
                    "request_id": context.aws_request_id,
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

        # Return success response in OpenAPI-compliant format
        return create_response(
            202,
            {
                "presentation_id": presentation_id,
                "title": task["title"],
                "status": "pending",
                "progress": 0,
                "created_at": task["created_at"],
                "updated_at": task["created_at"],
                "estimated_completion_time": estimated_completion,
                "slide_count": task.get("slide_count", 15),
                "session_id": session_id,
            },
        )

    except Exception as e:
        logger.error(f"Error generating presentation: {str(e)}")
        return create_response(
            500,
            {
                "error": "INTERNAL_ERROR",
                "message": "Failed to generate presentation",
                "request_id": context.aws_request_id,
            },
        )


def validate_presentation_request(body: Dict[str, Any]) -> Optional[str]:
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
    # Use the tasks table (now correctly configured)
    table = dynamodb.Table(TASKS_TABLE)

    # Add TTL (30 days from creation)
    ttl = int((datetime.utcnow() + timedelta(days=30)).timestamp())
    task["ttl"] = ttl
    
    # Map presentation_id to task_id for consistency
    if "presentation_id" in task and "task_id" not in task:
        task["task_id"] = task["presentation_id"]

    # Store in the tasks table, not sessions table
    table.put_item(Item=task)
    logger.info(f"Stored presentation state in {TASKS_TABLE}: {task.get('task_id', task.get('presentation_id'))}")


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


def handle_create_session(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle POST /sessions requests - Create a new session
    """
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        
        # Validate required parameters
        validation_error = validate_session_request(body)
        if validation_error:
            return create_response(
                400,
                {
                    "error": "INVALID_REQUEST",
                    "message": validation_error,
                    "request_id": context.aws_request_id,
                },
            )
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        user_id = body.get("user_id")
        session_name = body.get("session_name", f"Session for {user_id}")
        metadata = body.get("metadata", {})
        
        # Create session record
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "session_name": session_name,
            "status": "active",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_activity": datetime.utcnow().isoformat() + "Z",
            "expires_at": (datetime.utcnow() + timedelta(hours=8)).isoformat() + "Z",
            "metadata": metadata,
        }
        
        # Store session in DynamoDB sessions table
        table = dynamodb.Table(os.environ.get("DYNAMODB_SESSIONS_TABLE", "ai-ppt-assistant-dev-sessions"))
        table.put_item(Item=session_data)
        
        logger.info(f"Created session: {session_id} for user: {user_id}")
        
        return create_response(
            202,
            {
                "session_id": session_id,
                "user_id": user_id,
                "session_name": session_name,
                "status": "active",
                "created_at": session_data["created_at"],
                "expires_at": session_data["expires_at"],
                "metadata": metadata,
            },
        )
    
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        return create_response(
            500,
            {
                "error": "INTERNAL_ERROR",
                "message": "Failed to create session",
                "request_id": context.aws_request_id,
            },
        )


def handle_execute_agent(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle POST /agents/{name}/execute requests - Execute a Bedrock agent
    """
    try:
        # Parse request body and path parameters
        body = json.loads(event.get("body", "{}"))
        path_parameters = event.get("pathParameters") or {}
        agent_name = path_parameters.get("name")
        
        # Validate request
        validation_error = validate_agent_request(body, agent_name)
        if validation_error:
            return create_response(
                400,
                {
                    "error": "INVALID_REQUEST", 
                    "message": validation_error,
                    "request_id": context.aws_request_id,
                },
            )
        
        # Extract parameters
        input_text = body.get("input")
        session_id = body.get("session_id", str(uuid.uuid4()))
        enable_trace = body.get("enable_trace", False)
        parameters = body.get("parameters", {})
        
        # Map agent names to agent IDs and aliases
        agent_mapping = {
            "orchestrator": {
                "agent_id": ORCHESTRATOR_AGENT_ID,
                "alias_id": ORCHESTRATOR_ALIAS_ID,
            }
            # Note: Other agents (content, visual, compiler) would be added here
            # when they are configured with action groups
        }
        
        if agent_name not in agent_mapping:
            return create_response(
                404,
                {
                    "error": "AGENT_NOT_FOUND",
                    "message": f"Agent '{agent_name}' not found. Available agents: {list(agent_mapping.keys())}",
                    "request_id": context.aws_request_id,
                },
            )
        
        agent_config = agent_mapping[agent_name]
        
        # Generate task ID for tracking
        task_id = str(uuid.uuid4())
        
        try:
            # Invoke Bedrock agent
            response = bedrock_agent_runtime.invoke_agent(
                agentId=agent_config["agent_id"],
                agentAliasId=agent_config["alias_id"],
                sessionId=session_id,
                inputText=input_text,
                enableTrace=enable_trace,
            )
            
            logger.info(f"Agent {agent_name} execution started with task_id: {task_id}")
            
            return create_response(
                202,
                {
                    "task_id": task_id,
                    "agent_name": agent_name,
                    "status": "processing",
                    "session_id": session_id,
                    "started_at": datetime.utcnow().isoformat() + "Z",
                    "input": input_text,
                    "enable_trace": enable_trace,
                    "_links": {
                        "status": f"/tasks/{task_id}",
                        "session": f"/sessions/{session_id}",
                    },
                },
            )
            
        except Exception as bedrock_error:
            logger.error(f"Bedrock agent execution failed: {str(bedrock_error)}")
            return create_response(
                500,
                {
                    "error": "AGENT_EXECUTION_FAILED",
                    "message": f"Failed to execute agent '{agent_name}': {str(bedrock_error)}",
                    "request_id": context.aws_request_id,
                },
            )
    
    except Exception as e:
        logger.error(f"Error executing agent: {str(e)}")
        return create_response(
            500,
            {
                "error": "INTERNAL_ERROR",
                "message": "Failed to execute agent",
                "request_id": context.aws_request_id,
            },
        )


def validate_session_request(body: Dict[str, Any]) -> Optional[str]:
    """
    Validate session creation request parameters
    
    Args:
        body: Request body
        
    Returns:
        Error message if validation fails, None otherwise
    """
    # Required fields
    if not body.get("user_id"):
        return "user_id is required"
    
    # Validate user_id format
    user_id = body.get("user_id", "")
    if len(user_id) > 50:
        return "user_id must be less than 50 characters"
    
    # Validate session_name if provided
    session_name = body.get("session_name")
    if session_name and len(session_name) > 100:
        return "session_name must be less than 100 characters"
    
    return None


def validate_agent_request(body: Dict[str, Any], agent_name: Optional[str]) -> Optional[str]:
    """
    Validate agent execution request parameters
    
    Args:
        body: Request body
        agent_name: Agent name from path parameter
        
    Returns:
        Error message if validation fails, None otherwise
    """
    # Required fields
    if not body.get("input"):
        return "input is required"
    
    if not agent_name:
        return "Agent name is required in path"
    
    # Validate input length
    input_text = body.get("input", "")
    if len(input_text) > 2000:
        return "input must be less than 2000 characters"
    
    # Validate agent name
    valid_agents = ["orchestrator", "content", "visual", "compiler"]
    if agent_name not in valid_agents:
        return f"Invalid agent name. Valid agents: {valid_agents}"
    
    return None
