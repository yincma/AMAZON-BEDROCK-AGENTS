"""
Generate Image Lambda Function - AI PPT Assistant
Generates AI images for presentation slides using Amazon Bedrock
"""

import base64
import io
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3
import requests
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from PIL import Image
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
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
translate = boto3.client("translate")

# Environment variables
IMAGE_MODEL_ID = os.environ.get("IMAGE_MODEL_ID", "stability.stable-diffusion-xl-v1")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", get_config("aws.dynamodb.table"))
BUCKET_NAME = os.environ.get("S3_BUCKET", get_config("aws.s3.bucket"))
MAX_CONCURRENT_IMAGES = int(os.environ.get("MAX_CONCURRENT_IMAGES", "3"))
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")
DEFAULT_IMAGE_SIZE = os.environ.get("DEFAULT_IMAGE_SIZE", "1024x768")

# Pydantic models


class ImageRequest(BaseModel):
    """Request model for image generation"""

    presentation_id: str = Field(..., description="Presentation ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    slides: List[Dict[str, Any]] = Field(..., description="Slides requiring images")
    style: str = Field(default="professional", description="Image style")
    quality: str = Field(default="standard", description="Image quality")
    use_ai_generation: bool = Field(default=True, description="Use AI generation")
    fallback_to_stock: bool = Field(
        default=True, description="Fallback to stock images"
    )

    @validator("quality")
    def validate_quality(cls, v):
        allowed_qualities = ["draft", "standard", "high", "premium"]
        if v not in allowed_qualities:
            raise ValueError(f"Quality must be one of: {', '.join(allowed_qualities)}")
        return v

    @validator("style")
    def validate_style(cls, v):
        allowed_styles = [
            "professional",
            "creative",
            "minimalist",
            "photorealistic",
            "artistic",
            "corporate",
        ]
        if v not in allowed_styles:
            raise ValueError(f"Style must be one of: {', '.join(allowed_styles)}")
        return v


class GeneratedImage(BaseModel):
    """Model for generated image data"""

    slide_number: int
    image_url: str
    image_type: str  # 'ai_generated', 'stock', 'placeholder'
    prompt_used: str
    metadata: Dict[str, Any]
    s3_key: str
    thumbnail_url: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    """Response model for image generation"""

    presentation_id: str
    session_id: Optional[str]
    images_generated: List[GeneratedImage]
    total_images: int
    generation_time_seconds: float
    created_at: str


# Image generation functions


def optimize_prompt(description: str, style: str, language: str = "en") -> str:
    """Optimize prompt for image generation"""

    style_modifiers = {
        "professional": "professional, clean, business-appropriate, high quality",
        "creative": "creative, artistic, vibrant, imaginative",
        "minimalist": "minimalist, simple, clean lines, minimal colors",
        "photorealistic": "photorealistic, detailed, high resolution, lifelike",
        "artistic": "artistic, painterly, stylized, creative interpretation",
        "corporate": "corporate, modern, sleek, business professional",
    }

    # Translate to English if needed
    if language != "en" and language:
        try:
            response = translate.translate_text(
                Text=description, SourceLanguageCode=language, TargetLanguageCode="en"
            )
            description = response["TranslatedText"]
        except Exception as e:
            logger.warning(f"Translation failed, using original: {str(e)}")

    # Build optimized prompt
    base_prompt = f"{description}"
    style_suffix = style_modifiers.get(style, "professional, high quality")

    # Add technical specifications
    technical_specs = (
        "8k resolution, highly detailed, sharp focus, professional lighting"
    )

    # Combine all parts
    optimized_prompt = f"{base_prompt}, {style_suffix}, {technical_specs}"

    # Add negative prompt to avoid common issues
    negative_prompt = "blur, low quality, distorted, amateur, watermark, text overlay"

    return optimized_prompt, negative_prompt


@tracer.capture_method
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_with_bedrock(prompt: str, negative_prompt: str, quality: str) -> bytes:
    """Generate image using Amazon Bedrock"""

    try:
        # Configure quality parameters
        quality_settings = {
            "draft": {"steps": 20, "cfg_scale": 7, "width": 512, "height": 384},
            "standard": {"steps": 30, "cfg_scale": 8, "width": 1024, "height": 768},
            "high": {"steps": 50, "cfg_scale": 10, "width": 1536, "height": 1152},
            "premium": {"steps": 70, "cfg_scale": 12, "width": 2048, "height": 1536},
        }

        settings = quality_settings.get(quality, quality_settings["standard"])

        # Prepare request for Stable Diffusion
        if "stable-diffusion" in IMAGE_MODEL_ID:
            request_body = {
                "text_prompts": [
                    {"text": prompt, "weight": 1.0},
                    {"text": negative_prompt, "weight": -1.0},
                ],
                "cfg_scale": settings["cfg_scale"],
                "steps": settings["steps"],
                "width": settings["width"],
                "height": settings["height"],
                "seed": int.from_bytes(os.urandom(4), "big") % 1000000,
                "style_preset": "photographic",
            }
        # Prepare request for Titan Image Generator
        elif "titan" in IMAGE_MODEL_ID.lower():
            request_body = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {"text": prompt, "negativeText": negative_prompt},
                "imageGenerationConfig": {
                    "numberOfImages": 1,
                    "quality": quality.upper(),
                    "width": settings["width"],
                    "height": settings["height"],
                    "cfgScale": float(settings["cfg_scale"]),
                    "seed": int.from_bytes(os.urandom(4), "big") % 1000000,
                },
            }
        else:
            raise ValueError(f"Unsupported model: {IMAGE_MODEL_ID}")

        # Call Bedrock
        response = bedrock_runtime.invoke_model(
            modelId=IMAGE_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
        )

        # Parse response
        response_body = json.loads(response["body"].read())

        # Extract image data based on model
        if "stable-diffusion" in IMAGE_MODEL_ID:
            image_data = base64.b64decode(response_body["artifacts"][0]["base64"])
        elif "titan" in IMAGE_MODEL_ID.lower():
            image_data = base64.b64decode(response_body["images"][0])
        else:
            raise ValueError("Unable to parse image response")

        return image_data

    except ClientError as e:
        logger.error(f"Bedrock API error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating image: {str(e)}")
        raise


@tracer.capture_method
def fetch_stock_image(search_query: str, style: str) -> Tuple[bytes, str]:
    """Fetch stock image from Unsplash as fallback"""

    if not UNSPLASH_ACCESS_KEY:
        raise ValueError("Unsplash API key not configured")

    try:
        # Search for images
        headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
        params = {"query": search_query, "orientation": "landscape", "per_page": 1}

        response = requests.get(
            "https://api.unsplash.com/search/photos",
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        if data["results"]:
            image_url = data["results"][0]["urls"]["regular"]
            photographer = data["results"][0]["user"]["name"]

            # Download image
            image_response = requests.get(image_url, timeout=10)
            image_response.raise_for_status()

            return image_response.content, f"Photo by {photographer} on Unsplash"
        else:
            raise ValueError("No stock images found")

    except Exception as e:
        logger.error(f"Stock image fetch failed: {str(e)}")
        raise


@tracer.capture_method
def generate_placeholder_image(
    text: str, width: int = 1024, height: int = 768
) -> bytes:
    """Generate a simple placeholder image"""

    try:
        # Create image with gradient background
        img = Image.new("RGB", (width, height), color="white")

        # Use placeholder service
        placeholder_url = f"https://via.placeholder.com/{width}x{height}/4A90E2/FFFFFF?text={text[:50]}"

        response = requests.get(placeholder_url, timeout=5)
        if response.status_code == 200:
            return response.content

        # Fallback to local generation
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"Placeholder generation failed: {str(e)}")
        # Return minimal placeholder
        img = Image.new("RGB", (width, height), color="lightgray")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()


@tracer.capture_method
def save_image_to_s3(
    image_data: bytes, presentation_id: str, slide_number: int, image_type: str
) -> Tuple[str, str]:
    """Save image to S3 and return URLs"""

    try:
        # Generate S3 key
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        key = f"images/{presentation_id}/slide_{slide_number}_{timestamp}.png"

        # Upload to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=image_data,
            ContentType="image/png",
            Metadata={
                "presentation_id": presentation_id,
                "slide_number": str(slide_number),
                "image_type": image_type,
            },
        )

        # Generate presigned URL (valid for 7 days)
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": key},
            ExpiresIn=604800,  # 7 days
        )

        # Generate thumbnail
        thumbnail_key = key.replace(".png", "_thumb.png")
        img = Image.open(io.BytesIO(image_data))
        img.thumbnail((256, 192), Image.Resampling.LANCZOS)

        thumb_buffer = io.BytesIO()
        img.save(thumb_buffer, format="PNG")
        thumb_data = thumb_buffer.getvalue()

        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=thumbnail_key,
            Body=thumb_data,
            ContentType="image/png",
        )

        thumbnail_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": thumbnail_key},
            ExpiresIn=604800,
        )

        return url, thumbnail_url

    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise


@tracer.capture_method
def process_slide_image(
    slide: Dict,
    presentation_id: str,
    style: str,
    quality: str,
    use_ai: bool,
    use_stock: bool,
) -> GeneratedImage:
    """Process image generation for a single slide"""

    slide_number = slide.get("slide_number", 0)
    visual_description = slide.get("visual_element", slide.get("suggested_visual", ""))
    title = slide.get("title", "")

    if not visual_description:
        visual_description = f"Professional slide image for: {title}"

    try:
        # Optimize prompt
        optimized_prompt, negative_prompt = optimize_prompt(
            visual_description, style, slide.get("language", "en")
        )

        image_data = None
        image_type = "placeholder"
        attribution = ""

        # Try AI generation first
        if use_ai:
            try:
                logger.info(f"Generating AI image for slide {slide_number}")
                image_data = generate_with_bedrock(
                    optimized_prompt, negative_prompt, quality
                )
                image_type = "ai_generated"
            except Exception as e:
                logger.warning(
                    f"AI generation failed for slide {slide_number}: {str(e)}"
                )

        # Fallback to stock images
        if not image_data and use_stock:
            try:
                logger.info(f"Fetching stock image for slide {slide_number}")
                image_data, attribution = fetch_stock_image(visual_description, style)
                image_type = "stock"
            except Exception as e:
                logger.warning(
                    f"Stock image fetch failed for slide {slide_number}: {str(e)}"
                )

        # Final fallback to placeholder
        if not image_data:
            logger.info(f"Generating placeholder for slide {slide_number}")
            image_data = generate_placeholder_image(title)
            image_type = "placeholder"

        # Save to S3
        image_url, thumbnail_url = save_image_to_s3(
            image_data, presentation_id, slide_number, image_type
        )

        return GeneratedImage(
            slide_number=slide_number,
            image_url=image_url,
            image_type=image_type,
            prompt_used=optimized_prompt,
            metadata={
                "attribution": attribution,
                "quality": quality,
                "style": style,
                "original_description": visual_description,
            },
            s3_key=f"images/{presentation_id}/slide_{slide_number}",
            thumbnail_url=thumbnail_url,
        )

    except Exception as e:
        logger.error(f"Failed to process image for slide {slide_number}: {str(e)}")
        # Return error placeholder
        return GeneratedImage(
            slide_number=slide_number,
            image_url="https://via.placeholder.com/1024x768?text=Error",
            image_type="error",
            prompt_used="",
            metadata={"error": str(e)},
            s3_key="",
            thumbnail_url=None,
        )


@tracer.capture_method
def generate_images_parallel(
    slides: List[Dict],
    presentation_id: str,
    style: str,
    quality: str,
    use_ai: bool,
    use_stock: bool,
) -> List[GeneratedImage]:
    """Generate images for multiple slides in parallel"""

    generated_images = []

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_IMAGES) as executor:
        # Submit all image generation tasks
        future_to_slide = {}
        for slide in slides:
            future = executor.submit(
                process_slide_image,
                slide,
                presentation_id,
                style,
                quality,
                use_ai,
                use_stock,
            )
            future_to_slide[future] = slide

        # Collect results
        for future in as_completed(future_to_slide):
            try:
                image = future.result()
                generated_images.append(image)
                logger.info(f"Generated image for slide {image.slide_number}")
            except Exception as e:
                slide = future_to_slide[future]
                logger.error(f"Failed to generate image for slide: {str(e)}")
                # Add error placeholder
                generated_images.append(
                    GeneratedImage(
                        slide_number=slide.get("slide_number", 0),
                        image_url="https://via.placeholder.com/1024x768?text=Generation+Failed",
                        image_type="error",
                        prompt_used="",
                        metadata={"error": str(e)},
                        s3_key="",
                        thumbnail_url=None,
                    )
                )

    # Sort by slide number
    generated_images.sort(key=lambda x: x.slide_number)
    return generated_images


@tracer.capture_method
def save_metadata_to_dynamodb(response: ImageGenerationResponse) -> None:
    """Save image generation metadata to DynamoDB"""

    try:
        table = dynamodb.Table(SESSIONS_TABLE)

        item = {
            "session_id": response.session_id or str(uuid.uuid4()),
            "presentation_id": response.presentation_id,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "status": "images_generated",
            "images_count": response.total_images,
            "generation_time": response.generation_time_seconds,
            "ttl": int(datetime.now(timezone.utc).timestamp()) + (30 * 24 * 60 * 60),
        }

        table.put_item(Item=item)
        logger.info(f"Saved image metadata to DynamoDB: {response.presentation_id}")

    except ClientError as e:
        logger.error(f"DynamoDB error: {str(e)}")
        raise


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Main Lambda handler"""

    start_time = datetime.now(timezone.utc)

    try:
        logger.info("Received image generation request", extra={"event": event})

        # Parse request body
        body = (
            json.loads(event.get("body", "{}"))
            if isinstance(event.get("body"), str)
            else event
        )

        # Validate request
        try:
            request = ImageRequest(**body)
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

        # Filter slides that need images
        slides_needing_images = [
            slide
            for slide in request.slides
            if slide.get("visual_element") or slide.get("suggested_visual")
        ]

        if not slides_needing_images:
            # If no slides need images, return empty success
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps(
                    {
                        "success": True,
                        "message": "No slides require image generation",
                        "images_generated": [],
                    }
                ),
            }

        # Generate images
        logger.info(f"Generating images for {len(slides_needing_images)} slides")

        generated_images = generate_images_parallel(
            slides_needing_images,
            request.presentation_id,
            request.style,
            request.quality,
            request.use_ai_generation,
            request.fallback_to_stock,
        )

        # Calculate generation time
        end_time = datetime.now(timezone.utc)
        generation_time = (end_time - start_time).total_seconds()

        # Create response object
        response = ImageGenerationResponse(
            presentation_id=request.presentation_id,
            session_id=request.session_id,
            images_generated=generated_images,
            total_images=len(generated_images),
            generation_time_seconds=generation_time,
            created_at=end_time.isoformat(),
        )

        # Save metadata to DynamoDB
        save_metadata_to_dynamodb(response)

        # Record metrics
        metrics.add_metric(
            name="ImagesGenerated", unit=MetricUnit.Count, value=len(generated_images)
        )
        metrics.add_metric(
            name="GenerationTime", unit=MetricUnit.Seconds, value=generation_time
        )

        # Count image types
        ai_count = sum(
            1 for img in generated_images if img.image_type == "ai_generated"
        )
        stock_count = sum(1 for img in generated_images if img.image_type == "stock")
        placeholder_count = sum(
            1 for img in generated_images if img.image_type == "placeholder"
        )

        metrics.add_metric(
            name="AIImagesGenerated", unit=MetricUnit.Count, value=ai_count
        )
        metrics.add_metric(
            name="StockImagesUsed", unit=MetricUnit.Count, value=stock_count
        )
        metrics.add_metric(
            name="PlaceholdersUsed", unit=MetricUnit.Count, value=placeholder_count
        )

        # Return success response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(
                {
                    "success": True,
                    "presentation_id": request.presentation_id,
                    "images_generated": [img.dict() for img in generated_images],
                    "total_images": len(generated_images),
                    "generation_time_seconds": generation_time,
                    "statistics": {
                        "ai_generated": ai_count,
                        "stock_images": stock_count,
                        "placeholders": placeholder_count,
                    },
                    "message": f"Successfully generated {len(generated_images)} images",
                },
                default=str,
            ),
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        metrics.add_metric(name="ImageGenerationError", unit=MetricUnit.Count, value=1)

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "Internal server error", "message": str(e)}),
        }
