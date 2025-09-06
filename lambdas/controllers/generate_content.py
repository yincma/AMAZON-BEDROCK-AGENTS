"""
Generate Content Lambda Function - AI PPT Assistant
Expands presentation outline into detailed slide content using AWS Bedrock
"""

import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from utils.enhanced_config_manager import get_enhanced_config_manager

config_manager = get_enhanced_config_manager()
get_config = config_manager.get_value

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize AWS clients
bedrock_runtime = boto3.client(
    "bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-west-2")
)
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# Environment variables
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-4-0")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", get_config("aws.dynamodb.table"))
BUCKET_NAME = os.environ.get("S3_BUCKET", get_config("aws.s3.bucket"))
MAX_CONCURRENT_SLIDES = int(os.environ.get("MAX_CONCURRENT_SLIDES", "5"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "3"))

# Pydantic models


class SlideContent(BaseModel):
    """Model for individual slide content"""

    slide_number: int
    title: str
    content_type: str  # 'title', 'content', 'section', 'conclusion', 'thank_you'
    main_points: List[str]
    detailed_content: str
    speaker_notes: str
    visual_elements: List[Dict[str, str]]
    animations_suggested: Optional[List[str]] = None
    data_visualizations: Optional[List[Dict[str, Any]]] = None
    references: Optional[List[str]] = None


class ContentRequest(BaseModel):
    """Request model for content generation"""

    presentation_id: str = Field(..., description="Presentation ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    outline: Dict[str, Any] = Field(..., description="Presentation outline")
    detail_level: str = Field(default="medium", description="Content detail level")
    include_data: bool = Field(default=False, description="Include data visualizations")
    include_references: bool = Field(default=False, description="Include references")
    parallel_generation: bool = Field(
        default=True, description="Generate slides in parallel"
    )

    @validator("detail_level")
    def validate_detail_level(cls, v):
        allowed_levels = ["minimal", "medium", "detailed", "comprehensive"]
        if v not in allowed_levels:
            raise ValueError(
                f"Detail level must be one of: {', '.join(allowed_levels)}"
            )
        return v


class PresentationContent(BaseModel):
    """Model for complete presentation content"""

    presentation_id: str
    session_id: Optional[str]
    title: str
    slides: List[SlideContent]
    total_word_count: int
    estimated_duration: int
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


# Content generation prompts


def create_slide_prompt(
    slide_info: Dict, detail_level: str, language: str, style: str
) -> str:
    """Create prompt for individual slide content generation"""

    detail_instructions = {
        "minimal": "Keep content very brief, bullet points only",
        "medium": "Provide moderate detail with key explanations",
        "detailed": "Include comprehensive explanations and examples",
        "comprehensive": "Provide exhaustive detail with examples, data, and context",
    }

    content_type_instructions = {
        "title": "Create an impactful title slide with subtitle and key message",
        "content": "Develop detailed content with clear explanations",
        "section": "Create a section divider with overview of upcoming content",
        "conclusion": "Summarize key points and provide actionable takeaways",
        "thank_you": "Create a closing slide with contact information and Q&A prompt",
    }

    prompt = f"""You are an expert presentation content creator. Generate detailed content for the following slide.

Slide Information:
- Number: {slide_info.get('slide_number')}
- Title: {slide_info.get('title')}
- Content Points: {json.dumps(slide_info.get('content_points', []))}
- Type: {slide_info.get('content_type', 'content')}
- Style: {style}
- Language: {language}

Requirements:
1. Content Detail Level: {detail_instructions.get(detail_level, detail_level)}
2. Slide Type Instructions: {content_type_instructions.get(slide_info.get('content_type', 'content'))}
3. Generate:
   - Detailed content for each point (paragraph format)
   - Comprehensive speaker notes (what to say)
   - Visual element suggestions (charts, images, diagrams)
   - Animation suggestions (if appropriate)
   - Data visualizations (if relevant)

Return the content in the following JSON format:
{{
  "main_points": ["Expanded point 1", "Expanded point 2"],
  "detailed_content": "Full paragraph content for the slide",
  "speaker_notes": "Detailed notes for the presenter",
  "visual_elements": [
    {{"type": "chart", "description": "Bar chart showing...", "position": "right"}},
    {{"type": "image", "description": "Image of...", "position": "background"}}
  ],
  "animations_suggested": ["Fade in for title", "Slide up for bullets"],
  "data_visualizations": [
    {{"type": "bar_chart", "data": {{}}, "title": "Chart title"}}
  ],
  "references": ["Source 1", "Source 2"]
}}

Ensure the content is engaging, informative, and appropriate for the presentation style."""

    return prompt


@tracer.capture_method
def determine_slide_type(slide_info: Dict, position: int, total_slides: int) -> str:
    """Determine the content type of a slide based on its position and content"""

    if position == 1:
        return "title"
    elif position == total_slides:
        return "thank_you"
    elif position == total_slides - 1:
        return "conclusion"
    elif (
        "section" in slide_info.get("title", "").lower()
        or "overview" in slide_info.get("title", "").lower()
    ):
        return "section"
    else:
        return "content"


@tracer.capture_method
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_slide_content(
    slide_info: Dict, detail_level: str, language: str, style: str
) -> Dict[str, Any]:
    """Generate content for a single slide using Bedrock"""

    try:
        prompt = create_slide_prompt(slide_info, detail_level, language, style)

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.7,
            "top_p": 0.9,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
        )

        response_body = json.loads(response["body"].read())
        content = response_body.get("content", [{}])[0].get("text", "{}")

        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)

    except ClientError as e:
        logger.error(
            f"Bedrock API error for slide {slide_info.get('slide_number')}: {str(e)}"
        )
        raise
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse response for slide {slide_info.get('slide_number')}: {str(e)}"
        )
        raise ValueError("Invalid JSON response from Bedrock")
    except Exception as e:
        logger.error(
            f"Unexpected error generating content for slide {slide_info.get('slide_number')}: {str(e)}"
        )
        raise


@tracer.capture_method
def generate_slides_parallel(
    slides: List[Dict], detail_level: str, language: str, style: str
) -> List[SlideContent]:
    """Generate content for multiple slides in parallel"""

    generated_slides = []
    total_slides = len(slides)

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SLIDES) as executor:
        # Submit all slide generation tasks
        future_to_slide = {}
        for idx, slide in enumerate(slides, 1):
            slide["content_type"] = determine_slide_type(slide, idx, total_slides)
            future = executor.submit(
                generate_slide_content, slide, detail_level, language, style
            )
            future_to_slide[future] = (idx, slide)

        # Collect results as they complete
        for future in as_completed(future_to_slide):
            slide_number, slide_info = future_to_slide[future]
            try:
                content = future.result()
                slide_content = SlideContent(
                    slide_number=slide_number,
                    title=slide_info.get("title", ""),
                    content_type=slide_info.get("content_type", "content"),
                    main_points=content.get("main_points", []),
                    detailed_content=content.get("detailed_content", ""),
                    speaker_notes=content.get("speaker_notes", ""),
                    visual_elements=content.get("visual_elements", []),
                    animations_suggested=content.get("animations_suggested"),
                    data_visualizations=content.get("data_visualizations"),
                    references=content.get("references"),
                )
                generated_slides.append(slide_content)
                logger.info(f"Generated content for slide {slide_number}")

            except Exception as e:
                logger.error(
                    f"Failed to generate content for slide {slide_number}: {str(e)}"
                )
                # Create minimal content as fallback
                slide_content = SlideContent(
                    slide_number=slide_number,
                    title=slide_info.get("title", ""),
                    content_type=slide_info.get("content_type", "content"),
                    main_points=slide_info.get("content_points", []),
                    detailed_content="Content generation failed. Please retry.",
                    speaker_notes="",
                    visual_elements=[],
                )
                generated_slides.append(slide_content)

    # Sort slides by number to maintain order
    generated_slides.sort(key=lambda x: x.slide_number)
    return generated_slides


@tracer.capture_method
def generate_slides_batch(
    slides: List[Dict], detail_level: str, language: str, style: str
) -> List[SlideContent]:
    """Generate content for slides in batches (sequential processing)"""

    generated_slides = []
    total_slides = len(slides)

    for batch_start in range(0, total_slides, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_slides)
        batch = slides[batch_start:batch_end]

        for idx, slide in enumerate(batch, batch_start + 1):
            slide["content_type"] = determine_slide_type(slide, idx, total_slides)
            try:
                content = generate_slide_content(slide, detail_level, language, style)
                slide_content = SlideContent(
                    slide_number=idx,
                    title=slide.get("title", ""),
                    content_type=slide["content_type"],
                    main_points=content.get("main_points", []),
                    detailed_content=content.get("detailed_content", ""),
                    speaker_notes=content.get("speaker_notes", ""),
                    visual_elements=content.get("visual_elements", []),
                    animations_suggested=content.get("animations_suggested"),
                    data_visualizations=content.get("data_visualizations"),
                    references=content.get("references"),
                )
                generated_slides.append(slide_content)
                logger.info(f"Generated content for slide {idx} (batch mode)")

            except Exception as e:
                logger.error(f"Failed to generate content for slide {idx}: {str(e)}")
                # Create minimal content as fallback
                slide_content = SlideContent(
                    slide_number=idx,
                    title=slide.get("title", ""),
                    content_type=slide["content_type"],
                    main_points=slide.get("content_points", []),
                    detailed_content="Content generation failed. Please retry.",
                    speaker_notes="",
                    visual_elements=[],
                )
                generated_slides.append(slide_content)

    return generated_slides


@tracer.capture_method
def calculate_word_count(slides: List[SlideContent]) -> int:
    """Calculate total word count across all slides"""

    total_words = 0
    for slide in slides:
        # Count words in detailed content
        total_words += len(slide.detailed_content.split())
        # Count words in speaker notes
        total_words += len(slide.speaker_notes.split())
        # Count words in main points
        for point in slide.main_points:
            total_words += len(point.split())

    return total_words


@tracer.capture_method
def save_content_to_dynamodb(presentation: PresentationContent) -> None:
    """Save generated content to DynamoDB"""

    try:
        table = dynamodb.Table(SESSIONS_TABLE)

        item = {
            "session_id": presentation.session_id or str(uuid.uuid4()),
            "presentation_id": presentation.presentation_id,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "status": "content_generated",
            "title": presentation.title,
            "total_word_count": presentation.total_word_count,
            "estimated_duration": presentation.estimated_duration,
            "slides_count": len(presentation.slides),
            "metadata": presentation.metadata or {},
            "ttl": int(datetime.now(timezone.utc).timestamp())
            + (30 * 24 * 60 * 60),  # 30 days
        }

        table.put_item(Item=item)
        logger.info(
            f"Saved content metadata to DynamoDB: {presentation.presentation_id}"
        )

    except ClientError as e:
        logger.error(f"DynamoDB error: {str(e)}")
        raise


@tracer.capture_method
def save_content_to_s3(presentation: PresentationContent) -> str:
    """Save generated content to S3"""

    try:
        key = f"content/{presentation.presentation_id}/content.json"

        # Convert presentation to dict with slides serialized
        presentation_dict = presentation.dict()

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(presentation_dict, indent=2),
            ContentType="application/json",
            Metadata={
                "presentation_id": presentation.presentation_id,
                "word_count": str(presentation.total_word_count),
                "slides_count": str(len(presentation.slides)),
            },
        )

        logger.info(f"Saved content to S3: s3://{BUCKET_NAME}/{key}")
        return f"s3://{BUCKET_NAME}/{key}"

    except ClientError as e:
        logger.error(f"S3 error: {str(e)}")
        raise


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Main Lambda handler"""

    try:
        logger.info("Received content generation request", extra={"event": event})

        # Parse request body
        body = (
            json.loads(event.get("body", "{}"))
            if isinstance(event.get("body"), str)
            else event
        )

        # Validate request
        try:
            request = ContentRequest(**body)
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "Invalid request", "details": str(e)}),
            }

        # Extract outline information
        outline = request.outline
        slides = outline.get("slides", [])
        language = outline.get("language", "en")
        style = outline.get("style", "professional")

        if not slides:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"error": "No slides found in outline"}),
            }

        # Generate content for slides
        logger.info(f"Generating content for {len(slides)} slides")

        if request.parallel_generation and len(slides) > 3:
            generated_slides = generate_slides_parallel(
                slides, request.detail_level, language, style
            )
        else:
            generated_slides = generate_slides_batch(
                slides, request.detail_level, language, style
            )

        # Calculate metrics
        total_words = calculate_word_count(generated_slides)
        estimated_duration = outline.get("duration_minutes", 20)

        # Create presentation content object
        presentation = PresentationContent(
            presentation_id=request.presentation_id,
            session_id=request.session_id,
            title=outline.get("title", "Untitled Presentation"),
            slides=generated_slides,
            total_word_count=total_words,
            estimated_duration=estimated_duration,
            created_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "model_id": MODEL_ID,
                "detail_level": request.detail_level,
                "language": language,
                "style": style,
                "parallel_generation": request.parallel_generation,
            },
        )

        # Save to DynamoDB and S3
        save_content_to_dynamodb(presentation)
        s3_location = save_content_to_s3(presentation)

        # Record metrics
        metrics.add_metric(name="ContentGenerated", unit=MetricUnit.Count, value=1)
        metrics.add_metric(
            name="SlidesProcessed", unit=MetricUnit.Count, value=len(generated_slides)
        )
        metrics.add_metric(name="WordCount", unit=MetricUnit.Count, value=total_words)

        # Return success response
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "success": True,
                    "presentation_id": request.presentation_id,
                    "session_id": presentation.session_id,
                    "slides_generated": len(generated_slides),
                    "total_word_count": total_words,
                    "s3_location": s3_location,
                    "message": f"Successfully generated content for {len(generated_slides)} slides",
                },
                default=str,
            ),
        }

        logger.info(
            "Content generation completed successfully",
            extra={
                "presentation_id": request.presentation_id,
                "slides_count": len(generated_slides),
                "word_count": total_words,
            },
        )

        return response

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        metrics.add_metric(
            name="ContentGenerationError", unit=MetricUnit.Count, value=1
        )

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Internal server error", "message": str(e)}),
        }
