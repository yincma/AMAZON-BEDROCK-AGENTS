"""
Generate Speaker Notes Lambda Function - AI PPT Assistant
Generates context-aware speaker notes using AWS Bedrock Claude
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from enum import Enum
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
metrics = Metrics(namespace="AIPPTAssistant")

# Initialize AWS clients
bedrock_runtime = boto3.client(
    "bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-west-2")
)
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
translate = boto3.client("translate")

# Environment variables
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-4-0")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", get_config("aws.dynamodb.table"))
BUCKET_NAME = os.environ.get("S3_BUCKET", get_config("aws.s3.bucket"))
MAX_CONCURRENT_SLIDES = int(os.environ.get("MAX_CONCURRENT_SLIDES", "3"))
DEFAULT_SECONDS_PER_SLIDE = int(os.environ.get("DEFAULT_SECONDS_PER_SLIDE", "60"))

# Speaker note styles


class NoteStyle(Enum):
    DETAILED = "detailed"  # Comprehensive notes with examples and transitions
    CONCISE = "concise"  # Key points and essential information
    OUTLINE = "outline"  # Bullet points and structure only
    STORYTELLING = "storytelling"  # Narrative style with anecdotes
    TECHNICAL = "technical"  # Technical details and explanations


# Pydantic models


class SlideInfo(BaseModel):
    """Information about a single slide"""

    slide_number: int = Field(..., ge=1, description="Slide number")
    title: str = Field(..., description="Slide title")
    content: str = Field(..., description="Slide content")
    visual_description: Optional[str] = Field(
        default=None, description="Description of visuals"
    )
    estimated_duration: Optional[int] = Field(
        default=None, ge=1, description="Duration in seconds"
    )


class SpeakerNotesRequest(BaseModel):
    """Request model for speaker notes generation"""

    presentation_id: str = Field(
        ..., min_length=1, description="Presentation identifier"
    )
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    slides: List[SlideInfo] = Field(..., min_items=1, description="Slides information")
    presentation_context: Dict[str, Any] = Field(
        default={}, description="Overall presentation context"
    )
    audience_type: str = Field(default="general", description="Audience type")
    presentation_duration: int = Field(
        default=20, ge=1, le=180, description="Total duration in minutes"
    )
    note_style: str = Field(default="detailed", description="Style of speaker notes")
    language: str = Field(default="en", description="Language code")
    include_transitions: bool = Field(
        default=True, description="Include transition phrases"
    )
    include_timing: bool = Field(default=True, description="Include timing guidance")
    include_audience_interaction: bool = Field(
        default=False, description="Include audience interaction cues"
    )
    expertise_level: str = Field(
        default="intermediate", description="Speaker expertise level"
    )

    @validator("note_style")
    def validate_style(cls, v):
        valid_styles = [s.value for s in NoteStyle]
        if v not in valid_styles:
            raise ValueError(f"Style must be one of: {', '.join(valid_styles)}")
        return v

    @validator("expertise_level")
    def validate_expertise(cls, v):
        valid_levels = ["beginner", "intermediate", "expert"]
        if v not in valid_levels:
            raise ValueError(
                f"Expertise level must be one of: {', '.join(valid_levels)}"
            )
        return v

    @validator("language")
    def validate_language(cls, v):
        supported = ["en", "ja", "zh", "es", "fr", "de", "pt", "ko"]
        if v not in supported:
            raise ValueError(f"Language must be one of: {', '.join(supported)}")
        return v


class SpeakerNote(BaseModel):
    """Model for generated speaker notes"""

    slide_number: int
    main_points: List[str]
    detailed_notes: str
    transitions: Optional[Dict[str, str]] = None  # intro/outro transitions
    timing_guidance: Optional[Dict[str, Any]] = None
    audience_cues: Optional[List[str]] = None
    key_examples: Optional[List[str]] = None
    potential_questions: Optional[List[str]] = None
    technical_notes: Optional[str] = None
    confidence_level: float = Field(default=0.8, ge=0, le=1)


class SpeakerNotesResponse(BaseModel):
    """Response model for speaker notes generation"""

    success: bool
    presentation_id: str
    speaker_notes: List[SpeakerNote]
    overall_guidance: Optional[Dict[str, Any]] = None
    presentation_flow: Optional[List[str]] = None
    time_management: Optional[Dict[str, Any]] = None
    s3_location: Optional[str] = None
    generation_time_ms: int
    message: str


# Helper functions
@tracer.capture_method
def calculate_time_allocation(
    slides: List[SlideInfo], total_minutes: int
) -> Dict[int, int]:
    """Calculate time allocation for each slide"""

    total_seconds = total_minutes * 60
    time_allocation = {}

    # Check if slides have estimated durations
    has_estimates = any(slide.estimated_duration for slide in slides)

    if has_estimates:
        # Use provided estimates and adjust proportionally
        total_estimated = sum(
            slide.estimated_duration or DEFAULT_SECONDS_PER_SLIDE for slide in slides
        )
        ratio = total_seconds / total_estimated

        for slide in slides:
            duration = slide.estimated_duration or DEFAULT_SECONDS_PER_SLIDE
            time_allocation[slide.slide_number] = int(duration * ratio)
    else:
        # Distribute time with weight for first and last slides
        num_slides = len(slides)
        if num_slides == 1:
            time_allocation[1] = total_seconds
        else:
            # Give more time to intro and conclusion
            intro_time = int(total_seconds * 0.15)  # 15% for intro
            conclusion_time = int(total_seconds * 0.15)  # 15% for conclusion
            remaining_time = total_seconds - intro_time - conclusion_time

            middle_slides = num_slides - 2
            time_per_middle = (
                int(remaining_time / middle_slides) if middle_slides > 0 else 0
            )

            for i, slide in enumerate(slides):
                if i == 0:
                    time_allocation[slide.slide_number] = intro_time
                elif i == num_slides - 1:
                    time_allocation[slide.slide_number] = conclusion_time
                else:
                    time_allocation[slide.slide_number] = time_per_middle

    return time_allocation


@tracer.capture_method
def create_notes_prompt(
    slide: SlideInfo,
    context: Dict[str, Any],
    style: str,
    language: str,
    time_seconds: int,
    include_transitions: bool,
    include_audience: bool,
    expertise_level: str,
    prev_slide: Optional[SlideInfo] = None,
    next_slide: Optional[SlideInfo] = None,
) -> str:
    """Create prompt for speaker notes generation"""

    style_instructions = {
        NoteStyle.DETAILED.value: "Provide comprehensive notes with examples, explanations, and smooth transitions.",
        NoteStyle.CONCISE.value: "Focus on key points and essential information. Be brief but clear.",
        NoteStyle.OUTLINE.value: "Provide structured bullet points. Focus on the logical flow.",
        NoteStyle.STORYTELLING.value: "Create a narrative flow with anecdotes and engaging examples.",
        NoteStyle.TECHNICAL.value: "Include technical details, data points, and precise explanations.",
    }

    expertise_guidance = {
        "beginner": "Include detailed explanations and reminders. Provide confidence-building phrases.",
        "intermediate": "Balance guidance with flexibility. Include key points and optional elaborations.",
        "expert": "Focus on advanced insights and nuanced points. Assume familiarity with basics.",
    }

    # Build context about surrounding slides
    flow_context = ""
    if prev_slide:
        flow_context += (
            f"\nPrevious slide: '{prev_slide.title}' - Build from this context."
        )
    if next_slide:
        flow_context += (
            f"\nNext slide: '{next_slide.title}' - Prepare transition to this topic."
        )

    prompt = f"""You are an expert presentation coach creating speaker notes for a presenter.

SLIDE INFORMATION:
- Slide #{slide.slide_number}: {slide.title}
- Content: {slide.content}
- Visual Elements: {slide.visual_description or 'No specific visuals described'}
- Allocated Time: {time_seconds} seconds (approximately {time_seconds/60:.1f} minutes)
{flow_context}

PRESENTATION CONTEXT:
- Total Duration: {context.get('total_duration', 20)} minutes
- Audience: {context.get('audience', 'general professional')}
- Style: {context.get('style', 'professional')}
- Purpose: {context.get('purpose', 'inform and educate')}

REQUIREMENTS:
1. Style: {style_instructions.get(style, style)}
2. Language: Generate notes in {language}
3. Expertise Level: {expertise_guidance.get(expertise_level, expertise_level)}
4. Time Management: Notes should guide the speaker to use approximately {time_seconds} seconds

GENERATE SPEAKER NOTES WITH:
1. Opening statement for this slide (how to introduce the topic)
2. Main talking points (3-5 key points to cover)
3. Supporting details or examples for each point
4. Time markers (when to move to next point)
{"5. Transition phrase to next slide" if include_transitions and next_slide else ""}
{"6. Audience engagement cues (questions, interactions)" if include_audience else ""}
{"7. Technical notes or data points to mention" if style == NoteStyle.TECHNICAL.value else ""}
{"8. Potential questions and answers" if expertise_level == 'beginner' else ""}

Format the response as JSON:
{{
    "opening": "How to begin discussing this slide",
    "main_points": [
        "First key point to make",
        "Second key point",
        "Third key point"
    ],
    "detailed_notes": "Paragraph form of what to say, including examples and explanations",
    "transitions": {{
        "from_previous": "How to transition from previous slide",
        "to_next": "How to transition to next slide"
    }},
    "timing_guidance": {{
        "opening": "0:00-0:15",
        "main_content": "0:15-{int(time_seconds*0.8)}",
        "closing": "{int(time_seconds*0.8)}-{time_seconds}"
    }},
    "audience_cues": ["When to engage audience", "Questions to ask"],
    "key_examples": ["Example 1", "Example 2"],
    "potential_questions": ["Q: Common question?", "A: Answer"],
    "confidence_tips": ["Remember to...", "Key emphasis on..."]
}}

Ensure the notes sound natural when spoken and provide genuine value to the presenter."""

    return prompt


@tracer.capture_method
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_notes_for_slide(
    slide: SlideInfo,
    context: Dict[str, Any],
    style: str,
    language: str,
    time_seconds: int,
    include_transitions: bool,
    include_audience: bool,
    expertise_level: str,
    prev_slide: Optional[SlideInfo] = None,
    next_slide: Optional[SlideInfo] = None,
) -> Dict[str, Any]:
    """Generate speaker notes for a single slide using Bedrock"""

    try:
        # Create the prompt
        prompt = create_notes_prompt(
            slide,
            context,
            style,
            language,
            time_seconds,
            include_transitions,
            include_audience,
            expertise_level,
            prev_slide,
            next_slide,
        )

        # Call Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.7,
            "top_p": 0.9,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
        )

        # Parse response
        response_body = json.loads(response["body"].read())
        content = response_body.get("content", [{}])[0].get("text", "{}")

        # Extract JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        notes_data = json.loads(content)

        # Translate if needed
        if language != "en":
            notes_data = translate_notes(notes_data, language)

        return notes_data

    except Exception as e:
        logger.error(f"Error generating notes for slide {slide.slide_number}: {str(e)}")
        # Return fallback notes
        return {
            "opening": f"Present {slide.title}",
            "main_points": ["Key point from content"] * 3,
            "detailed_notes": f"Discuss the content of {slide.title}. {slide.content}",
            "confidence_tips": ["Speak clearly", "Make eye contact"],
        }


@tracer.capture_method
def translate_notes(notes_data: Dict[str, Any], target_language: str) -> Dict[str, Any]:
    """Translate speaker notes to target language"""

    try:

        def translate_text(text: str) -> str:
            if not text:
                return text
            response = translate.translate_text(
                Text=text, SourceLanguageCode="en", TargetLanguageCode=target_language
            )
            return response["TranslatedText"]

        # Translate all text fields
        if "opening" in notes_data:
            notes_data["opening"] = translate_text(notes_data["opening"])

        if "detailed_notes" in notes_data:
            notes_data["detailed_notes"] = translate_text(notes_data["detailed_notes"])

        if "main_points" in notes_data:
            notes_data["main_points"] = [
                translate_text(p) for p in notes_data["main_points"]
            ]

        if "audience_cues" in notes_data:
            notes_data["audience_cues"] = [
                translate_text(c) for c in notes_data["audience_cues"]
            ]

        if "key_examples" in notes_data:
            notes_data["key_examples"] = [
                translate_text(e) for e in notes_data["key_examples"]
            ]

        if "confidence_tips" in notes_data:
            notes_data["confidence_tips"] = [
                translate_text(t) for t in notes_data["confidence_tips"]
            ]

        return notes_data

    except Exception as e:
        logger.warning(f"Translation failed: {str(e)}")
        return notes_data  # Return original if translation fails


@tracer.capture_method
def generate_notes_parallel(
    slides: List[SlideInfo],
    context: Dict[str, Any],
    style: str,
    language: str,
    time_allocation: Dict[int, int],
    include_transitions: bool,
    include_audience: bool,
    expertise_level: str,
) -> List[SpeakerNote]:
    """Generate speaker notes for multiple slides in parallel"""

    speaker_notes = []

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SLIDES) as executor:
        futures = {}

        for i, slide in enumerate(slides):
            prev_slide = slides[i - 1] if i > 0 else None
            next_slide = slides[i + 1] if i < len(slides) - 1 else None
            time_seconds = time_allocation.get(
                slide.slide_number, DEFAULT_SECONDS_PER_SLIDE
            )

            future = executor.submit(
                generate_notes_for_slide,
                slide,
                context,
                style,
                language,
                time_seconds,
                include_transitions,
                include_audience,
                expertise_level,
                prev_slide,
                next_slide,
            )
            futures[future] = slide

        # Collect results
        for future in as_completed(futures):
            slide = futures[future]
            try:
                notes_data = future.result(timeout=30)

                speaker_note = SpeakerNote(
                    slide_number=slide.slide_number,
                    main_points=notes_data.get("main_points", []),
                    detailed_notes=notes_data.get("detailed_notes", ""),
                    transitions=notes_data.get("transitions"),
                    timing_guidance=notes_data.get("timing_guidance"),
                    audience_cues=notes_data.get("audience_cues"),
                    key_examples=notes_data.get("key_examples"),
                    potential_questions=notes_data.get("potential_questions"),
                    technical_notes=notes_data.get("technical_notes"),
                    confidence_level=0.9,
                )
                speaker_notes.append(speaker_note)

            except Exception as e:
                logger.error(
                    f"Failed to generate notes for slide {slide.slide_number}: {str(e)}"
                )
                # Add fallback notes
                speaker_notes.append(
                    SpeakerNote(
                        slide_number=slide.slide_number,
                        main_points=[f"Point about {slide.title}"],
                        detailed_notes=f"Present the content of {slide.title}",
                        confidence_level=0.5,
                    )
                )

    # Sort by slide number
    speaker_notes.sort(key=lambda x: x.slide_number)
    return speaker_notes


@tracer.capture_method
def generate_overall_guidance(
    slides: List[SlideInfo],
    context: Dict[str, Any],
    total_minutes: int,
    audience_type: str,
) -> Dict[str, Any]:
    """Generate overall presentation guidance"""

    guidance = {
        "opening_strategy": "Start with a strong hook to capture attention",
        "pacing_advice": f"Aim for approximately {total_minutes/len(slides):.1f} minutes per slide",
        "energy_management": "Maintain high energy for introduction and conclusion",
        "audience_engagement": f"For {audience_type} audience, focus on practical examples",
        "closing_strategy": "End with clear call-to-action and memorable takeaway",
        "backup_plans": {
            "running_over_time": "Skip detailed examples in middle slides",
            "running_under_time": "Expand on Q&A or add more examples",
            "technical_issues": "Have printed backup of key slides",
        },
        "confidence_builders": [
            "Practice the opening and closing slides most",
            "Have water nearby",
            "Take deep breaths between major sections",
            "Remember: you're the expert on this content",
        ],
    }

    return guidance


@tracer.capture_method
def save_notes_to_s3(
    presentation_id: str,
    speaker_notes: List[SpeakerNote],
    overall_guidance: Dict[str, Any],
) -> str:
    """Save speaker notes to S3"""

    try:
        # Prepare data
        notes_data = {
            "presentation_id": presentation_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "speaker_notes": [note.dict() for note in speaker_notes],
            "overall_guidance": overall_guidance,
            "version": "1.0",
        }

        # Save to S3
        key = f"speaker-notes/{presentation_id}/notes.json"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=json.dumps(notes_data, indent=2, default=str),
            ContentType="application/json",
            Metadata={
                "presentation_id": presentation_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"Saved speaker notes to S3: s3://{BUCKET_NAME}/{key}")
        return f"s3://{BUCKET_NAME}/{key}"

    except ClientError as e:
        logger.error(f"Error saving to S3: {str(e)}")
        raise


@tracer.capture_method
def save_metadata_to_dynamodb(
    presentation_id: str,
    session_id: Optional[str],
    notes_count: int,
    style: str,
    language: str,
):
    """Save generation metadata to DynamoDB"""

    try:
        table = dynamodb.Table(SESSIONS_TABLE)

        item = {
            "session_id": session_id or presentation_id,
            "presentation_id": presentation_id,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "operation": "speaker_notes_generation",
            "notes_count": notes_count,
            "style": style,
            "language": language,
            "status": "completed",
        }

        table.put_item(Item=item)
        logger.info(f"Saved metadata for presentation {presentation_id}")

    except ClientError as e:
        logger.error(f"Error saving metadata: {str(e)}")


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Main Lambda handler for speaker notes generation"""

    start_time = datetime.now(timezone.utc)

    try:
        # Parse request
        body = (
            json.loads(event.get("body", "{}"))
            if isinstance(event.get("body"), str)
            else event
        )

        # Validate request
        try:
            request = SpeakerNotesRequest(**body)
        except Exception as e:
            logger.error(f"Request validation error: {str(e)}")
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {"success": False, "error": "Invalid request", "details": str(e)}
                ),
            }

        logger.info(f"Generating speaker notes for {len(request.slides)} slides")

        # Calculate time allocation
        time_allocation = calculate_time_allocation(
            request.slides, request.presentation_duration
        )

        # Generate speaker notes in parallel
        speaker_notes = generate_notes_parallel(
            request.slides,
            request.presentation_context,
            request.note_style,
            request.language,
            time_allocation,
            request.include_transitions,
            request.include_audience_interaction,
            request.expertise_level,
        )

        # Generate overall guidance
        overall_guidance = generate_overall_guidance(
            request.slides,
            request.presentation_context,
            request.presentation_duration,
            request.audience_type,
        )

        # Add presentation flow
        presentation_flow = [
            f"Slide {note.slide_number}: {slide.title}"
            for note, slide in zip(speaker_notes, request.slides)
        ]

        # Calculate time management summary
        time_management = {
            "total_minutes": request.presentation_duration,
            "average_per_slide": request.presentation_duration / len(request.slides),
            "slide_timings": {
                f"slide_{num}": f"{sec//60}:{sec%60:02d}"
                for num, sec in time_allocation.items()
            },
        }

        # Save to S3
        s3_location = save_notes_to_s3(
            request.presentation_id, speaker_notes, overall_guidance
        )

        # Save metadata to DynamoDB
        save_metadata_to_dynamodb(
            request.presentation_id,
            request.session_id,
            len(speaker_notes),
            request.note_style,
            request.language,
        )

        # Calculate generation time
        generation_time_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        # Record metrics
        metrics.add_metric(name="SpeakerNotesGenerated", unit=MetricUnit.Count, value=1)
        metrics.add_metric(
            name="NotesPerPresentation", unit=MetricUnit.Count, value=len(speaker_notes)
        )
        metrics.add_metric(
            name="GenerationTimeMs",
            unit=MetricUnit.Milliseconds,
            value=generation_time_ms,
        )

        # Prepare response
        response_data = SpeakerNotesResponse(
            success=True,
            presentation_id=request.presentation_id,
            speaker_notes=speaker_notes,
            overall_guidance=overall_guidance,
            presentation_flow=presentation_flow,
            time_management=time_management,
            s3_location=s3_location,
            generation_time_ms=generation_time_ms,
            message=f"Successfully generated speaker notes for {len(speaker_notes)} slides",
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(response_data.dict(), default=str),
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        metrics.add_metric(name="SpeakerNotesError", unit=MetricUnit.Count, value=1)

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {"success": False, "error": "Internal server error", "message": str(e)}
            ),
        }
