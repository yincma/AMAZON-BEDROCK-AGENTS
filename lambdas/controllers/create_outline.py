"""
Create Outline Lambda Function - AI PPT Assistant
Generates presentation outline using AWS Bedrock Claude 3.5 Sonnet
"""

import contextlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, validator
from tenacity import retry, stop_after_attempt, wait_exponential

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configuration management utilities
from utils.enhanced_config_manager import (
    get_enhanced_config_manager,
)

# Import timeout management utilities
from utils.timeout_manager import (
    TimeoutError,
    TimeoutManager,
    create_timeout_config,
    timeout_handler,
)

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics(namespace="AIPPTAssistant")

# Configuration initialization (Enhanced Config Manager)
config_manager = get_enhanced_config_manager()
aws_config = config_manager.get_aws_config()
s3_config = config_manager.get_s3_config()
dynamodb_config = config_manager.get_dynamodb_config()
bedrock_config = config_manager.get_bedrock_config()
performance_config = config_manager.get_performance_config()

# Initialize AWS clients with configured region
bedrock_runtime = boto3.client("bedrock-runtime", region_name=aws_config.region)
dynamodb = boto3.resource("dynamodb", region_name=aws_config.region)
s3 = boto3.client("s3", region_name=aws_config.region)

# Configuration values (now from Enhanced Config Manager)
MODEL_ID = bedrock_config.model_id
SESSIONS_TABLE = dynamodb_config.table
BUCKET_NAME = s3_config.bucket
MAX_SLIDES = performance_config.max_slides
MIN_SLIDES = performance_config.min_slides

# Pydantic models for validation


class OutlineRequest(BaseModel):
    """Request model for outline generation"""

    topic: str = Field(
        ..., min_length=3, max_length=500, description="Presentation topic"
    )
    audience: str = Field(
        default="general", max_length=100, description="Target audience"
    )
    duration_minutes: int = Field(
        default=20, ge=5, le=120, description="Presentation duration"
    )
    style: str = Field(default="professional", description="Presentation style")
    language: str = Field(default="en", description="Language code")
    num_slides: Optional[int] = Field(default=10, ge=MIN_SLIDES, le=MAX_SLIDES)
    include_examples: bool = Field(
        default=True, description="Include examples in content"
    )
    user_id: Optional[str] = Field(default=None, description="User identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier")

    @validator("style")
    def validate_style(cls, v):
        allowed_styles = ["professional", "casual", "academic", "creative", "technical"]
        if v.lower() not in allowed_styles:
            raise ValueError(f"Style must be one of: {', '.join(allowed_styles)}")
        return v.lower()

    @validator("language")
    def validate_language(cls, v):
        supported_languages = ["en", "ja", "zh", "es", "fr", "de", "pt", "ko"]
        if v.lower() not in supported_languages:
            raise ValueError(
                f"Language must be one of: {', '.join(supported_languages)}"
            )
        return v.lower()


class SlideOutline(BaseModel):
    """Model for individual slide outline"""

    slide_number: int
    title: str
    content_points: List[str]
    speaker_notes: Optional[str] = None
    suggested_visual: Optional[str] = None
    estimated_duration: Optional[int] = None


class PresentationOutline(BaseModel):
    """Model for complete presentation outline"""

    presentation_id: str
    topic: str
    title: str
    subtitle: Optional[str] = None
    audience: str
    duration_minutes: int
    style: str
    language: str
    slides: List[SlideOutline]
    created_at: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Prompt templates


def create_outline_prompt(request: OutlineRequest) -> str:
    """Create the prompt for outline generation"""

    language_instruction = {
        "en": "Generate in English",
        "ja": "Generate in Japanese (日本語で生成)",
        "zh": "Generate in Chinese (用中文生成)",
        "es": "Generate in Spanish",
        "fr": "Generate in French",
        "de": "Generate in German",
        "pt": "Generate in Portuguese",
        "ko": "Generate in Korean (한국어로 생성)",
    }

    style_guidance = {
        "professional": "formal, business-oriented, data-driven",
        "casual": "informal, conversational, engaging",
        "academic": "scholarly, research-based, thorough",
        "creative": "innovative, visual, storytelling",
        "technical": "detailed, precise, technical depth",
    }

    prompt = f"""You are an expert presentation designer. Create a comprehensive outline for a presentation on the following topic.

Topic: {request.topic}
Target Audience: {request.audience}
Duration: {request.duration_minutes} minutes
Number of Slides: {request.num_slides}
Style: {style_guidance.get(request.style, request.style)}
Language: {language_instruction.get(request.language, 'English')}

Please create a structured outline with the following requirements:
1. A compelling title and subtitle for the presentation
2. Exactly {request.num_slides} slides, each with:
   - A clear, concise title
   - 3-5 main content points
   - Brief speaker notes (1-2 sentences)
   - Suggested visual element or diagram
   - Estimated speaking time in minutes

3. The outline should follow this flow:
   - Opening slide (title/introduction)
   - Context/background (1-2 slides)
   - Main content (divided into logical sections)
   - Examples or case studies {' (include specific examples)' if request.include_examples else ''}
   - Key takeaways or summary
   - Closing slide (thank you/Q&A)

4. Ensure the content is:
   - Appropriate for the {request.audience} audience
   - Fits within {request.duration_minutes} minutes (approximately {request.duration_minutes // request.num_slides} minutes per slide)
   - Follows a {request.style} style
   - Logically structured and easy to follow

Return the outline in the following JSON format:
{{
  "title": "Main presentation title",
  "subtitle": "Optional subtitle",
  "slides": [
    {{
      "slide_number": 1,
      "title": "Slide title",
      "content_points": ["Point 1", "Point 2", "Point 3"],
      "speaker_notes": "What to say during this slide",
      "suggested_visual": "Description of visual element",
      "estimated_duration": 2
    }}
  ]
}}

Ensure the JSON is valid and properly formatted."""

    return prompt


@tracer.capture_method
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_bedrock(
    prompt: str, timeout_manager: Optional[TimeoutManager] = None
) -> Dict[str, Any]:
    """Call AWS Bedrock Claude API with retry logic and timeout monitoring"""

    try:
        # Check timeout before starting
        if timeout_manager:
            timeout_manager.check_timeout_status("bedrock_call")

        with (
            timeout_manager.operation("bedrock_preparation")
            if timeout_manager
            else contextlib.nullcontext()
        ):
            # Prepare the request
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.7,
                "top_p": 0.9,
                "messages": [{"role": "user", "content": prompt}],
            }

        with (
            timeout_manager.operation("bedrock_api_call")
            if timeout_manager
            else contextlib.nullcontext()
        ):
            # Call Bedrock with timeout awareness
            response = bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            )

        with (
            timeout_manager.operation("response_parsing")
            if timeout_manager
            else contextlib.nullcontext()
        ):
            # Parse response
            response_body = json.loads(response["body"].read())
            content = response_body.get("content", [{}])[0].get("text", "{}")

            # Extract JSON from the response
            # Handle potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

    except ClientError as e:
        logger.error(f"Bedrock API error: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Bedrock response: {str(e)}")
        logger.debug(f"Raw response: {content}")
        raise ValueError("Invalid JSON response from Bedrock")
    except Exception as e:
        logger.error(f"Unexpected error calling Bedrock: {str(e)}")
        raise


@tracer.capture_method
def save_to_dynamodb(outline: PresentationOutline) -> None:
    """Save outline to DynamoDB"""

    try:
        table = dynamodb.Table(SESSIONS_TABLE)

        item = {
            "session_id": outline.session_id or str(uuid.uuid4()),
            "presentation_id": outline.presentation_id,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "topic": outline.topic,
            "title": outline.title,
            "subtitle": outline.subtitle,
            "audience": outline.audience,
            "duration_minutes": outline.duration_minutes,
            "style": outline.style,
            "language": outline.language,
            "status": "outline_created",
            "slides_data": [slide.dict() for slide in outline.slides],
            "metadata": outline.metadata or {},
            "ttl": int(datetime.now(timezone.utc).timestamp())
            + (30 * 24 * 60 * 60),  # 30 days
        }

        table.put_item(Item=item)
        logger.info(f"Saved outline to DynamoDB: {outline.presentation_id}")

    except ClientError as e:
        logger.error(f"DynamoDB error: {str(e)}")
        raise


@tracer.capture_method
def save_to_s3(outline: PresentationOutline) -> str:
    """Save outline to S3"""

    try:
        key = f"outlines/{outline.presentation_id}/outline.json"

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(outline.dict(), indent=2),
            ContentType="application/json",
            Metadata={
                "presentation_id": outline.presentation_id,
                "topic": outline.topic,
                "language": outline.language,
            },
        )

        logger.info(f"Saved outline to S3: s3://{BUCKET_NAME}/{key}")
        return f"s3://{BUCKET_NAME}/{key}"

    except ClientError as e:
        logger.error(f"S3 error: {str(e)}")
        raise


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Main Lambda handler with timeout management"""

    # Initialize timeout management
    timeout_config = create_timeout_config(context, grace_period=5)

    with timeout_handler(context, timeout_config) as timeout_manager:
        try:
            # Log configuration summary for debugging
            logger.info(
                "Configuration loaded successfully",
                extra={
                    "aws_region": aws_config.region,
                    "model_id": bedrock_config.model_id,
                    "max_slides": performance_config.max_slides,
                },
            )

            # Validate environment configuration
            config_validation = config_manager.validate_configuration()
            if config_validation["errors"]:
                logger.error(
                    "Configuration validation failed",
                    extra={"validation_errors": config_validation["errors"]},
                )
                return {
                    "statusCode": 500,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": json.dumps(
                        {
                            "error": "Configuration error",
                            "details": config_validation["invalid"],
                        }
                    ),
                }

            # Log the incoming event
            logger.info("Received outline generation request", extra={"event": event})

            with timeout_manager.operation("request_validation"):
                # Parse request body
                body = (
                    json.loads(event.get("body", "{}"))
                    if isinstance(event.get("body"), str)
                    else event
                )

                # Validate request
                try:
                    request = OutlineRequest(**body)
                except Exception as e:
                    logger.error(f"Validation error: {str(e)}")
                    return {
                        "statusCode": 400,
                        "headers": {
                            "Content-Type": "application/json",
                            "Access-Control-Allow-Origin": "*",
                        },
                        "body": json.dumps(
                            {
                                "error": "Invalid request",
                                "details": str(e),
                                "timeout_info": timeout_manager.get_performance_summary(),
                            }
                        ),
                    }

            with timeout_manager.operation("setup_and_prompt_generation"):
                # Generate presentation ID and session ID
                presentation_id = str(uuid.uuid4())
                session_id = request.session_id or str(uuid.uuid4())

                # Create the prompt
                prompt = create_outline_prompt(request)

            # Call Bedrock to generate outline
            logger.info("Calling Bedrock to generate outline")
            outline_data = call_bedrock(prompt, timeout_manager)

            with timeout_manager.operation("data_processing"):
                # Create slide objects
                slides = []
                for slide_data in outline_data.get("slides", []):
                    slide = SlideOutline(
                        slide_number=slide_data.get("slide_number"),
                        title=slide_data.get("title"),
                        content_points=slide_data.get("content_points", []),
                        speaker_notes=slide_data.get("speaker_notes"),
                        suggested_visual=slide_data.get("suggested_visual"),
                        estimated_duration=slide_data.get("estimated_duration"),
                    )
                    slides.append(slide)

                # Create outline object
                outline = PresentationOutline(
                    presentation_id=presentation_id,
                    topic=request.topic,
                    title=outline_data.get("title", request.topic),
                    subtitle=outline_data.get("subtitle"),
                    audience=request.audience,
                    duration_minutes=request.duration_minutes,
                    style=request.style,
                    language=request.language,
                    slides=slides,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    session_id=session_id,
                    metadata={
                        "model_id": MODEL_ID,
                        "include_examples": request.include_examples,
                        "user_id": request.user_id,
                        "timeout_summary": timeout_manager.get_performance_summary(),
                    },
                )

            with timeout_manager.operation("data_persistence"):
                # Save to DynamoDB and S3
                save_to_dynamodb(outline)
                s3_location = save_to_s3(outline)

            # Record metrics
            metrics.add_metric(name="OutlineGenerated", unit=MetricUnit.Count, value=1)
            metrics.add_metric(
                name="SlidesCount", unit=MetricUnit.Count, value=len(slides)
            )

            # Return success response with timeout information
            response = {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "success": True,
                        "presentation_id": presentation_id,
                        "session_id": session_id,
                        "outline": outline.dict(),
                        "s3_location": s3_location,
                        "message": f"Successfully generated outline with {len(slides)} slides",
                        "performance_summary": timeout_manager.get_performance_summary(),
                    },
                    default=str,
                ),
            }

            logger.info(
                "Outline generation completed successfully",
                extra={
                    "presentation_id": presentation_id,
                    "slides_count": len(slides),
                    "performance_summary": timeout_manager.get_performance_summary(),
                },
            )

            return response

        except TimeoutError as e:
            logger.error(f"Timeout error: {str(e)}", exc_info=True)
            metrics.add_metric(
                name="OutlineGenerationTimeout", unit=MetricUnit.Count, value=1
            )

            return {
                "statusCode": 408,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "error": "Request timeout",
                        "message": str(e),
                        "timeout_info": timeout_manager.get_performance_summary(),
                    }
                ),
            }

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            metrics.add_metric(
                name="OutlineGenerationError", unit=MetricUnit.Count, value=1
            )

            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "error": "Internal server error",
                        "message": str(e),
                        "timeout_info": (
                            timeout_manager.get_performance_summary()
                            if "timeout_manager" in locals()
                            else None
                        ),
                    }
                ),
            }
