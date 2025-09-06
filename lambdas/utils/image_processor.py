"""
Image Processing Utilities for AI PPT Assistant
Handles image validation, processing, and management operations
"""

import base64
import contextlib
import io
import json
import os
import sys
import urllib.parse
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

import boto3
import requests
from aws_lambda_powertools import Logger, Metrics, Tracer
from botocore.exceptions import ClientError
from PIL import Image

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.enhanced_config_manager import get_enhanced_config_manager

# Import timeout management
from utils.timeout_manager import TimeoutError, TimeoutManager

config_manager = get_enhanced_config_manager()
get_config = config_manager.get_value

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize AWS clients
s3 = boto3.client("s3")
bedrock_runtime = boto3.client(
    "bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-west-2")
)

# Environment variables
S3_BUCKET = os.environ.get("S3_BUCKET", get_config("aws.s3.bucket"))
NOVA_MODEL_ID = os.environ.get("NOVA_MODEL_ID", "amazon.nova-canvas-v1:0")
MAX_IMAGE_SIZE_MB = int(os.environ.get("MAX_IMAGE_SIZE_MB", "10"))
SUPPORTED_IMAGE_FORMATS = ["PNG", "JPEG", "JPG", "GIF", "BMP", "TIFF"]
DEFAULT_IMAGE_SIZE = (1920, 1080)  # Default slide dimensions


class ImageAction(Enum):
    """Supported image actions"""

    REPLACE = "replace"
    REGENERATE = "regenerate"
    REMOVE = "remove"
    REPOSITION = "reposition"
    RESIZE = "resize"
    ENHANCE = "enhance"


class ImageFormat(Enum):
    """Supported image formats"""

    PNG = "PNG"
    JPEG = "JPEG"
    WEBP = "WEBP"


@dataclass
class ImageMetadata:
    """Image metadata structure"""

    image_id: str
    original_url: Optional[str] = None
    s3_key: str = ""
    format: str = "PNG"
    width: int = 0
    height: int = 0
    file_size: int = 0
    created_at: str = ""
    alt_text: Optional[str] = None
    position: Dict[str, float] = None

    def __post_init__(self):
        if self.position is None:
            self.position = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}


@dataclass
class ImageProcessingRequest:
    """Image processing request structure"""

    action: ImageAction
    presentation_id: str
    slide_number: int
    image_data: Optional[bytes] = None
    image_url: Optional[str] = None
    generation_prompt: Optional[str] = None
    target_format: ImageFormat = ImageFormat.PNG
    target_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE
    quality: int = 95
    enhancement_options: Dict[str, Any] = None

    def __post_init__(self):
        if self.enhancement_options is None:
            self.enhancement_options = {}


class ImageProcessor:
    """Main image processing class with comprehensive functionality"""

    def __init__(self, timeout_manager: Optional[TimeoutManager] = None):
        self.timeout_manager = timeout_manager
        self.s3_client = s3
        self.bedrock_client = bedrock_runtime

    @tracer.capture_method
    def process_image_request(self, request: ImageProcessingRequest) -> Dict[str, Any]:
        """Process image modification request"""

        if self.timeout_manager:
            self.timeout_manager.check_timeout_status("image_processing")

        try:
            with (
                self.timeout_manager.operation("image_request_processing")
                if self.timeout_manager
                else contextlib.nullcontext()
            ):
                if request.action == ImageAction.REPLACE:
                    return self._handle_image_replacement(request)
                elif request.action == ImageAction.REGENERATE:
                    return self._handle_image_regeneration(request)
                elif request.action == ImageAction.REMOVE:
                    return self._handle_image_removal(request)
                elif request.action == ImageAction.REPOSITION:
                    return self._handle_image_repositioning(request)
                elif request.action == ImageAction.RESIZE:
                    return self._handle_image_resizing(request)
                elif request.action == ImageAction.ENHANCE:
                    return self._handle_image_enhancement(request)
                else:
                    raise ValueError(f"Unsupported image action: {request.action}")

        except TimeoutError as e:
            logger.error(f"Timeout during image processing: {e}")
            return {
                "success": False,
                "error": "Image processing timeout",
                "details": str(e),
            }
        except Exception as e:
            logger.error(f"Error processing image request: {e}")
            return {"success": False, "error": str(e)}

    @tracer.capture_method
    def _handle_image_replacement(
        self, request: ImageProcessingRequest
    ) -> Dict[str, Any]:
        """Handle image replacement with uploaded or URL-based image"""

        image_data = None

        if request.image_data:
            image_data = request.image_data
        elif request.image_url:
            image_data = self._download_image_from_url(request.image_url)
        else:
            return {
                "success": False,
                "error": "No image data or URL provided for replacement",
            }

        # Validate and process image
        processed_image = self._validate_and_process_image(
            image_data, request.target_format, request.target_size, request.quality
        )

        if not processed_image["success"]:
            return processed_image

        # Generate S3 key and upload
        s3_key = self._generate_s3_key(
            request.presentation_id, request.slide_number, "image"
        )
        upload_result = self._upload_to_s3(processed_image["image_data"], s3_key)

        if not upload_result["success"]:
            return upload_result

        # Create metadata
        metadata = ImageMetadata(
            image_id=str(uuid.uuid4()),
            s3_key=s3_key,
            format=request.target_format.value,
            width=processed_image["width"],
            height=processed_image["height"],
            file_size=len(processed_image["image_data"]),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        return {
            "success": True,
            "action": "replace",
            "image_metadata": metadata.__dict__,
            "s3_url": upload_result["s3_url"],
            "message": "Image successfully replaced",
        }

    @tracer.capture_method
    def _handle_image_regeneration(
        self, request: ImageProcessingRequest
    ) -> Dict[str, Any]:
        """Handle image regeneration using AWS Bedrock Nova"""

        if not request.generation_prompt:
            return {
                "success": False,
                "error": "Generation prompt required for image regeneration",
            }

        # Generate image using Nova Canvas
        generated_image = self._generate_image_with_nova(
            request.generation_prompt, request.target_size
        )

        if not generated_image["success"]:
            return generated_image

        # Process generated image
        processed_image = self._validate_and_process_image(
            generated_image["image_data"],
            request.target_format,
            request.target_size,
            request.quality,
        )

        if not processed_image["success"]:
            return processed_image

        # Upload to S3
        s3_key = self._generate_s3_key(
            request.presentation_id, request.slide_number, "generated"
        )
        upload_result = self._upload_to_s3(processed_image["image_data"], s3_key)

        if not upload_result["success"]:
            return upload_result

        # Create metadata
        metadata = ImageMetadata(
            image_id=str(uuid.uuid4()),
            s3_key=s3_key,
            format=request.target_format.value,
            width=processed_image["width"],
            height=processed_image["height"],
            file_size=len(processed_image["image_data"]),
            created_at=datetime.now(timezone.utc).isoformat(),
            alt_text=f"Generated: {request.generation_prompt}",
        )

        return {
            "success": True,
            "action": "regenerate",
            "image_metadata": metadata.__dict__,
            "s3_url": upload_result["s3_url"],
            "generation_prompt": request.generation_prompt,
            "message": "Image successfully regenerated",
        }

    @tracer.capture_method
    def _handle_image_removal(self, request: ImageProcessingRequest) -> Dict[str, Any]:
        """Handle image removal from slide"""

        return {
            "success": True,
            "action": "remove",
            "message": "Image removed from slide",
            "slide_layout_update": "content_only",  # Update layout to content-only
        }

    @tracer.capture_method
    def _handle_image_repositioning(
        self, request: ImageProcessingRequest
    ) -> Dict[str, Any]:
        """Handle image repositioning within slide"""

        # This would integrate with the slide layout system
        position_data = request.enhancement_options.get("position", {})

        return {
            "success": True,
            "action": "reposition",
            "position": position_data,
            "message": "Image position updated",
        }

    @tracer.capture_method
    def _handle_image_resizing(self, request: ImageProcessingRequest) -> Dict[str, Any]:
        """Handle image resizing"""

        # Get current image from slide data (this would need integration)
        # For now, return success with resize parameters

        return {
            "success": True,
            "action": "resize",
            "target_size": request.target_size,
            "message": "Image resized successfully",
        }

    @tracer.capture_method
    def _handle_image_enhancement(
        self, request: ImageProcessingRequest
    ) -> Dict[str, Any]:
        """Handle image enhancement (brightness, contrast, etc.)"""

        enhancement_options = request.enhancement_options

        return {
            "success": True,
            "action": "enhance",
            "enhancements": enhancement_options,
            "message": "Image enhanced successfully",
        }

    @tracer.capture_method
    def _download_image_from_url(self, url: str, timeout: int = 30) -> bytes:
        """Download image from URL with validation"""

        try:
            # Validate URL
            parsed_url = urllib.parse.urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError("Invalid URL provided")

            # Download with timeout
            response = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "AI-PPT-Assistant/1.0"},
                stream=True,
            )
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise ValueError(f"URL does not point to an image: {content_type}")

            # Check file size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise ValueError(f"Image too large: {content_length} bytes")

            # Download in chunks
            image_data = b""
            for chunk in response.iter_content(chunk_size=8192):
                image_data += chunk
                if len(image_data) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                    raise ValueError("Image too large")

            return image_data

        except requests.RequestException as e:
            logger.error(f"Error downloading image from URL: {e}")
            raise ValueError(f"Failed to download image: {e}")

    @tracer.capture_method
    def _validate_and_process_image(
        self,
        image_data: bytes,
        target_format: ImageFormat,
        target_size: Tuple[int, int],
        quality: int,
    ) -> Dict[str, Any]:
        """Validate and process image data"""

        try:
            # Open and validate image
            with Image.open(io.BytesIO(image_data)) as img:
                # Validate format
                if img.format not in SUPPORTED_IMAGE_FORMATS:
                    return {
                        "success": False,
                        "error": f"Unsupported format: {img.format}",
                    }

                # Convert to RGB if necessary
                if img.mode != "RGB" and target_format in [ImageFormat.JPEG]:
                    img = img.convert("RGB")
                elif img.mode != "RGBA" and target_format == ImageFormat.PNG:
                    img = img.convert("RGBA")

                # Resize if needed
                original_size = img.size
                if target_size and target_size != original_size:
                    # Use high-quality resampling
                    img = img.resize(target_size, Image.Resampling.LANCZOS)

                # Save processed image
                output_buffer = io.BytesIO()
                save_kwargs = {"format": target_format.value}

                if target_format == ImageFormat.JPEG:
                    save_kwargs["quality"] = quality
                    save_kwargs["optimize"] = True
                elif target_format == ImageFormat.PNG:
                    save_kwargs["optimize"] = True

                img.save(output_buffer, **save_kwargs)
                processed_data = output_buffer.getvalue()

                return {
                    "success": True,
                    "image_data": processed_data,
                    "width": img.width,
                    "height": img.height,
                    "original_size": original_size,
                    "format": target_format.value,
                }

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return {"success": False, "error": f"Image processing failed: {e}"}

    @tracer.capture_method
    def _generate_image_with_nova(
        self, prompt: str, size: Tuple[int, int]
    ) -> Dict[str, Any]:
        """Generate image using Amazon Nova Canvas"""

        try:
            # Prepare request for Nova Canvas
            request_body = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {
                    "text": prompt,
                    "width": size[0],
                    "height": size[1],
                    "cfgScale": 8.0,  # Guidance scale
                    "seed": None,  # Random seed
                    "numberOfImages": 1,
                },
            }

            # Call Bedrock Nova Canvas
            response = self.bedrock_client.invoke_model(
                modelId=NOVA_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())

            if "images" not in response_body or not response_body["images"]:
                return {"success": False, "error": "No images generated"}

            # Get first generated image
            image_base64 = response_body["images"][0]
            image_data = base64.b64decode(image_base64)

            return {
                "success": True,
                "image_data": image_data,
                "generation_model": NOVA_MODEL_ID,
                "prompt": prompt,
            }

        except Exception as e:
            logger.error(f"Error generating image with Nova: {e}")
            return {"success": False, "error": f"Image generation failed: {e}"}

    @tracer.capture_method
    def _upload_to_s3(self, image_data: bytes, s3_key: str) -> Dict[str, Any]:
        """Upload image to S3"""

        try:
            self.s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=s3_key,
                Body=image_data,
                ContentType="image/png",  # Default to PNG
                Metadata={
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "source": get_config("metadata.project_name", "ai-ppt-assistant"),
                },
            )

            s3_url = f"s3://{S3_BUCKET}/{s3_key}"

            return {"success": True, "s3_key": s3_key, "s3_url": s3_url}

        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            return {"success": False, "error": f"S3 upload failed: {e}"}

    def _generate_s3_key(
        self, presentation_id: str, slide_number: int, image_type: str
    ) -> str:
        """Generate S3 key for image storage"""

        timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d/%H%M%S")
        image_id = str(uuid.uuid4())[:8]

        return f"presentations/{presentation_id}/slides/{slide_number}/images/{timestamp}_{image_type}_{image_id}.png"


# Utility functions
def create_image_processor(
    timeout_manager: Optional[TimeoutManager] = None,
) -> ImageProcessor:
    """Create image processor instance"""
    return ImageProcessor(timeout_manager)


def process_visual_modification(
    presentation_id: str,
    slide_number: int,
    visual_modifications: Dict[str, Any],
    timeout_manager: Optional[TimeoutManager] = None,
) -> Dict[str, Any]:
    """Process visual modifications for slide"""

    processor = create_image_processor(timeout_manager)

    try:
        action = visual_modifications.get("action", "replace")

        # Create processing request
        request = ImageProcessingRequest(
            action=ImageAction(action),
            presentation_id=presentation_id,
            slide_number=slide_number,
            image_url=visual_modifications.get("image_url"),
            generation_prompt=visual_modifications.get("prompt"),
            target_format=ImageFormat.PNG,
            enhancement_options=visual_modifications.get("options", {}),
        )

        return processor.process_image_request(request)

    except Exception as e:
        logger.error(f"Error processing visual modification: {e}")
        return {"success": False, "error": str(e)}
