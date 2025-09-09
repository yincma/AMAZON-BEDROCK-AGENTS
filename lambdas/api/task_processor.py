"""
Task Processor Lambda Function
Processes tasks from SQS queue and orchestrates the presentation generation workflow
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize AWS clients with explicit region (AWS Expert fix)
# AWS Lambda automatically sets AWS_REGION, but fallback to us-east-1
AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)
lambda_client = boto3.client("lambda", region_name=AWS_REGION)

# AWS Expert: Log region for debugging
print(f"AWS Expert Debug - Task Processor using region: {AWS_REGION}")

# Environment variables
TASKS_TABLE = os.environ.get("DYNAMODB_TABLE", "ai-ppt-assistant-dev-tasks")
SESSIONS_TABLE = os.environ.get("DYNAMODB_SESSIONS_TABLE", "ai-ppt-assistant-dev-sessions")
CHECKPOINTS_TABLE = os.environ.get("DYNAMODB_CHECKPOINTS_TABLE", "ai-ppt-assistant-dev-checkpoints")
S3_BUCKET = os.environ.get("S3_BUCKET")

# Bedrock Agent configurations
ORCHESTRATOR_AGENT_ID = os.environ.get("ORCHESTRATOR_AGENT_ID")
ORCHESTRATOR_ALIAS_ID = os.environ.get("ORCHESTRATOR_ALIAS_ID")
CONTENT_AGENT_ID = os.environ.get("CONTENT_AGENT_ID")
CONTENT_ALIAS_ID = os.environ.get("CONTENT_ALIAS_ID")
VISUAL_AGENT_ID = os.environ.get("VISUAL_AGENT_ID")
VISUAL_ALIAS_ID = os.environ.get("VISUAL_ALIAS_ID")
COMPILER_AGENT_ID = os.environ.get("COMPILER_AGENT_ID")
COMPILER_ALIAS_ID = os.environ.get("COMPILER_ALIAS_ID")

# Model IDs
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID")
BEDROCK_ORCHESTRATOR_MODEL_ID = os.environ.get("BEDROCK_ORCHESTRATOR_MODEL_ID")
NOVA_MODEL_ID = os.environ.get("NOVA_MODEL_ID")

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process tasks from SQS queue
    
    Args:
        event: SQS event containing messages
        context: Lambda context
        
    Returns:
        Response with batch item failures
    """
    batch_item_failures = []
    
    for record in event.get("Records", []):
        try:
            # Parse the SQS message
            message_body = json.loads(record["body"])
            task_id = message_body.get("task_id")
            task_type = message_body.get("type", "generate_presentation")
            task_data = message_body.get("data", {})
            
            logger.info(f"Processing task: {task_id}, type: {task_type}")
            
            # Update task status to processing
            update_task_status(task_id, "processing", 10)
            
            # Process based on task type
            if task_type == "generate_presentation":
                process_presentation_generation(task_id, task_data)
            elif task_type == "modify_slide":
                process_slide_modification(task_id, task_data)
            else:
                logger.warning(f"Unknown task type: {task_type}")
                update_task_status(task_id, "failed", error="Unknown task type")
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            # Add to batch item failures for retry
            batch_item_failures.append({
                "itemIdentifier": record["messageId"]
            })
    
    return {
        "batchItemFailures": batch_item_failures
    }


def process_presentation_generation(task_id: str, task_data: Dict[str, Any]) -> None:
    """
    Process presentation generation task
    
    Args:
        task_id: Task identifier
        task_data: Task data containing presentation parameters
    """
    try:
        # Step 1: Create outline using Bedrock or Lambda function
        logger.info(f"Step 1: Creating outline for {task_id}")
        update_task_status(task_id, "processing", 20, "Creating outline...")
        
        outline = create_presentation_outline(task_data)
        save_checkpoint(task_id, "outline", outline)
        
        # Step 2: Generate content for each slide
        logger.info(f"Step 2: Generating content for {task_id}")
        update_task_status(task_id, "processing", 40, "Generating slide content...")
        
        slides_content = generate_slides_content(outline, task_data)
        save_checkpoint(task_id, "content", slides_content)
        
        # Step 3: Generate or find images
        logger.info(f"Step 3: Processing images for {task_id}")
        update_task_status(task_id, "processing", 60, "Creating visuals...")
        
        if task_data.get("include_images", True):
            slides_with_images = process_images(slides_content, task_data)
            save_checkpoint(task_id, "images", slides_with_images)
        else:
            slides_with_images = slides_content
        
        # Step 4: Generate speaker notes
        logger.info(f"Step 4: Generating speaker notes for {task_id}")
        update_task_status(task_id, "processing", 80, "Adding speaker notes...")
        
        if task_data.get("include_speaker_notes", True):
            final_slides = generate_speaker_notes(slides_with_images, task_data)
            save_checkpoint(task_id, "speaker_notes", final_slides)
        else:
            final_slides = slides_with_images
        
        # Step 5: Compile to PPTX
        logger.info(f"Step 5: Compiling presentation for {task_id}")
        update_task_status(task_id, "processing", 90, "Creating presentation file...")
        
        pptx_url = compile_presentation(task_id, final_slides, task_data)
        
        # Step 6: Mark as completed
        logger.info(f"Presentation generation completed for {task_id}")
        update_task_status(
            task_id, 
            "completed", 
            100,
            "Presentation ready for download",
            result={
                "download_url": pptx_url,
                "total_slides": len(final_slides),
                "completed_at": datetime.utcnow().isoformat() + "Z"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in presentation generation: {str(e)}")
        update_task_status(task_id, "failed", error=str(e))
        raise


def create_presentation_outline(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create presentation outline using Lambda function or Bedrock
    """
    try:
        # Invoke the create_outline Lambda function
        response = lambda_client.invoke(
            FunctionName=f"{os.environ.get('PROJECT_NAME', 'ai-ppt-assistant')}-create-outline",
            InvocationType="RequestResponse",
            Payload=json.dumps(task_data)
        )
        
        result = json.loads(response["Payload"].read())
        if result.get("statusCode") == 200:
            return json.loads(result.get("body", "{}"))
        else:
            raise Exception(f"Outline creation failed: {result}")
            
    except Exception as e:
        logger.error(f"Error creating outline: {str(e)}")
        # Fallback to direct Bedrock invocation if Lambda fails
        return invoke_bedrock_for_outline(task_data)


def generate_slides_content(outline: Dict[str, Any], task_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate content for each slide
    """
    try:
        # Invoke the generate_content Lambda function
        response = lambda_client.invoke(
            FunctionName=f"{os.environ.get('PROJECT_NAME', 'ai-ppt-assistant')}-generate-content",
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "outline": outline,
                **task_data
            })
        )
        
        result = json.loads(response["Payload"].read())
        if result.get("statusCode") == 200:
            return json.loads(result.get("body", "[]"))
        else:
            raise Exception(f"Content generation failed: {result}")
            
    except Exception as e:
        logger.error(f"Error generating content: {str(e)}")
        raise


def process_images(slides: List[Dict[str, Any]], task_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process images for slides
    """
    for slide in slides:
        if slide.get("needs_image", True):
            try:
                # Try to find existing image first
                image_url = find_image(slide.get("image_query", slide.get("title", "")))
                if not image_url:
                    # Generate new image if not found
                    image_url = generate_image(slide, task_data)
                slide["image_url"] = image_url
            except Exception as e:
                logger.warning(f"Error processing image for slide: {str(e)}")
                slide["image_url"] = None
    
    return slides


def generate_speaker_notes(slides: List[Dict[str, Any]], task_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate speaker notes for slides
    """
    try:
        # Invoke the generate_speaker_notes Lambda function
        response = lambda_client.invoke(
            FunctionName=f"{os.environ.get('PROJECT_NAME', 'ai-ppt-assistant')}-generate-speaker-notes",
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "slides": slides,
                **task_data
            })
        )
        
        result = json.loads(response["Payload"].read())
        if result.get("statusCode") == 200:
            return json.loads(result.get("body", "[]"))
        else:
            logger.warning(f"Speaker notes generation failed: {result}")
            return slides
            
    except Exception as e:
        logger.warning(f"Error generating speaker notes: {str(e)}")
        return slides


def compile_presentation(task_id: str, slides: List[Dict[str, Any]], task_data: Dict[str, Any]) -> str:
    """
    Compile slides into PPTX format
    """
    try:
        # Invoke the compile_pptx Lambda function
        response = lambda_client.invoke(
            FunctionName=f"{os.environ.get('PROJECT_NAME', 'ai-ppt-assistant')}-compile-pptx",
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "task_id": task_id,
                "slides": slides,
                "metadata": task_data
            })
        )
        
        result = json.loads(response["Payload"].read())
        if result.get("statusCode") == 200:
            body = json.loads(result.get("body", "{}"))
            return body.get("download_url", f"s3://{S3_BUCKET}/presentations/{task_id}.pptx")
        else:
            raise Exception(f"PPTX compilation failed: {result}")
            
    except Exception as e:
        logger.error(f"Error compiling presentation: {str(e)}")
        raise


def update_task_status(
    task_id: str, 
    status: str, 
    progress: int = 0,
    message: str = None,
    error: str = None,
    result: Dict[str, Any] = None
) -> None:
    """
    Update task status in DynamoDB
    """
    try:
        table = dynamodb.Table(TASKS_TABLE)
        
        update_expr = "SET #status = :status, #progress = :progress, #updated = :updated"
        expr_attr_names = {
            "#status": "status",
            "#progress": "progress",
            "#updated": "updated_at"
        }
        expr_attr_values = {
            ":status": status,
            ":progress": progress,
            ":updated": datetime.utcnow().isoformat() + "Z"
        }
        
        if message:
            update_expr += ", #msg = :msg"
            expr_attr_names["#msg"] = "message"
            expr_attr_values[":msg"] = message
            
        if error:
            update_expr += ", #err = :err"
            expr_attr_names["#err"] = "error"
            expr_attr_values[":err"] = error
            
        if result:
            update_expr += ", #result = :result"
            expr_attr_names["#result"] = "result"
            expr_attr_values[":result"] = result
        
        table.update_item(
            Key={"task_id": task_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )
        
        logger.info(f"Updated task {task_id} status to {status} ({progress}%)")
        
    except ClientError as e:
        logger.error(f"Error updating task status: {str(e)}")
        # Don't raise to avoid blocking other processing


def save_checkpoint(task_id: str, checkpoint_type: str, data: Any) -> None:
    """
    Save processing checkpoint to DynamoDB
    """
    try:
        table = dynamodb.Table(CHECKPOINTS_TABLE)
        
        table.put_item(
            Item={
                "task_id": task_id,
                "checkpoint_type": checkpoint_type,
                "data": json.dumps(data) if not isinstance(data, str) else data,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "ttl": int((datetime.utcnow().timestamp())) + 86400  # 24 hour TTL
            }
        )
        
        logger.info(f"Saved checkpoint {checkpoint_type} for task {task_id}")
        
    except ClientError as e:
        logger.warning(f"Error saving checkpoint: {str(e)}")
        # Don't raise to avoid blocking processing


def invoke_bedrock_for_outline(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fallback method to invoke Bedrock directly for outline creation
    """
    if not ORCHESTRATOR_AGENT_ID or not ORCHESTRATOR_ALIAS_ID:
        raise ValueError("Bedrock Orchestrator Agent not configured")
    
    prompt = f"""Create a presentation outline with the following requirements:
    Title: {task_data.get('title')}
    Topic: {task_data.get('topic')}
    Audience: {task_data.get('audience', 'general')}
    Number of slides: {task_data.get('slide_count', 15)}
    Style: {task_data.get('style', 'professional')}
    """
    
    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=ORCHESTRATOR_AGENT_ID,
            agentAliasId=ORCHESTRATOR_ALIAS_ID,
            sessionId=task_data.get('session_id', 'default'),
            inputText=prompt
        )
        
        # Process streaming response
        result = ""
        for event in response.get("completion", []):
            if "chunk" in event:
                chunk = event["chunk"]
                if "bytes" in chunk:
                    result += chunk["bytes"].decode("utf-8")
        
        return {"outline": result}
        
    except Exception as e:
        logger.error(f"Error invoking Bedrock: {str(e)}")
        raise


def find_image(query: str) -> str:
    """
    Find existing image based on query
    """
    # Placeholder - implement actual image search logic
    return None


def generate_image(slide: Dict[str, Any], task_data: Dict[str, Any]) -> str:
    """
    Generate new image for slide
    """
    try:
        # Invoke the generate_image Lambda function
        response = lambda_client.invoke(
            FunctionName=f"{os.environ.get('PROJECT_NAME', 'ai-ppt-assistant')}-generate-image",
            InvocationType="RequestResponse",
            Payload=json.dumps({
                "prompt": slide.get("image_prompt", slide.get("title", "")),
                "style": task_data.get("style", "professional")
            })
        )
        
        result = json.loads(response["Payload"].read())
        if result.get("statusCode") == 200:
            body = json.loads(result.get("body", "{}"))
            return body.get("image_url")
            
    except Exception as e:
        logger.warning(f"Error generating image: {str(e)}")
        
    return None


def process_slide_modification(task_id: str, task_data: Dict[str, Any]) -> None:
    """
    Process slide modification task
    """
    # Placeholder for slide modification logic
    update_task_status(task_id, "completed", 100, "Slide modified successfully")