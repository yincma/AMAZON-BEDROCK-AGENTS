"""
Find Image Lambda Function - AI PPT Assistant
Searches for relevant images from various sources
"""

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import boto3
import requests
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, validator
from utils.enhanced_config_manager import get_enhanced_config_manager

config_manager = get_enhanced_config_manager()
get_config = config_manager.get_value

# Initialize AWS Lambda Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Initialize AWS clients
s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
rekognition = boto3.client("rekognition")

# Environment variables
BUCKET_NAME = os.environ.get("S3_BUCKET", get_config("aws.s3.bucket"))
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", get_config("aws.dynamodb.table"))
IMAGE_LIBRARY_BUCKET = os.environ.get("IMAGE_LIBRARY_BUCKET", "")
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
MAX_SEARCH_RESULTS = int(os.environ.get("MAX_SEARCH_RESULTS", "10"))
ENABLE_REKOGNITION = os.environ.get("ENABLE_REKOGNITION", "false").lower() == "true"


# Image search sources
class ImageSource(Enum):
    S3_LIBRARY = "s3_library"
    PEXELS = "pexels"
    PIXABAY = "pixabay"
    PLACEHOLDER = "placeholder"


# Pydantic models
class SearchRequest(BaseModel):
    """Request model for image search"""

    presentation_id: str = Field(
        ..., min_length=1, description="Presentation identifier"
    )
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    search_queries: List[str] = Field(
        ..., min_items=1, max_items=10, description="Search terms"
    )
    slide_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Slide context"
    )
    preferred_sources: Optional[List[str]] = Field(
        default=None, description="Preferred image sources"
    )
    style_preferences: Optional[Dict[str, Any]] = Field(
        default=None, description="Style preferences"
    )
    max_results_per_query: int = Field(
        default=5, ge=1, le=20, description="Max results per query"
    )
    include_metadata: bool = Field(default=True, description="Include image metadata")
    language: str = Field(default="en", description="Language for search")

    @validator("preferred_sources")
    def validate_sources(cls, v):
        if v:
            valid_sources = [s.value for s in ImageSource]
            for source in v:
                if source not in valid_sources:
                    raise ValueError(
                        f"Invalid source: {source}. Must be one of {valid_sources}"
                    )
        return v


class ImageResult(BaseModel):
    """Model for found image"""

    image_id: str
    source: str
    url: str
    thumbnail_url: Optional[str] = None
    title: str
    description: Optional[str] = None
    tags: List[str] = []
    attribution: Optional[str] = None
    license: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    relevance_score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Response model for image search"""

    success: bool
    presentation_id: str
    search_results: Dict[str, List[ImageResult]]  # Query -> Results mapping
    total_results: int
    sources_searched: List[str]
    search_time_ms: int
    message: Optional[str] = None


# Search implementations
@tracer.capture_method
def search_s3_library(query: str, max_results: int) -> List[ImageResult]:
    """Search internal S3 image library"""
    results = []

    if not IMAGE_LIBRARY_BUCKET:
        logger.info("S3 library bucket not configured, skipping")
        return results

    try:
        # List objects with prefix matching
        prefix = f"images/{query.lower().replace(' ', '_')}"
        response = s3.list_objects_v2(
            Bucket=IMAGE_LIBRARY_BUCKET,
            Prefix=prefix,
            MaxKeys=max_results * 2,  # Get more to filter
        )

        if "Contents" not in response:
            return results

        for obj in response["Contents"][:max_results]:
            # Extract metadata
            try:
                metadata_response = s3.head_object(
                    Bucket=IMAGE_LIBRARY_BUCKET, Key=obj["Key"]
                )
                metadata = metadata_response.get("Metadata", {})

                # Generate presigned URL
                url = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": IMAGE_LIBRARY_BUCKET, "Key": obj["Key"]},
                    ExpiresIn=3600,
                )

                results.append(
                    ImageResult(
                        image_id=hashlib.md5(obj["Key"].encode()).hexdigest(),
                        source=ImageSource.S3_LIBRARY.value,
                        url=url,
                        title=metadata.get("title", obj["Key"].split("/")[-1]),
                        description=metadata.get("description"),
                        tags=(
                            metadata.get("tags", "").split(",")
                            if metadata.get("tags")
                            else []
                        ),
                        attribution=metadata.get("attribution"),
                        license=metadata.get("license", "Internal Use"),
                        file_size=obj["Size"],
                        relevance_score=0.9,  # High score for internal library
                    )
                )
            except Exception as e:
                logger.warning(f"Error processing S3 object {obj['Key']}: {str(e)}")
                continue

    except ClientError as e:
        logger.error(f"S3 search error: {str(e)}")

    return results


@tracer.capture_method
def search_pexels(query: str, max_results: int) -> List[ImageResult]:
    """Search Pexels API for stock images"""
    results = []

    if not PEXELS_API_KEY:
        logger.info("Pexels API key not configured, skipping")
        return results

    try:
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": query, "per_page": max_results, "orientation": "landscape"}

        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params=params,
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            for photo in data.get("photos", []):
                results.append(
                    ImageResult(
                        image_id=str(photo["id"]),
                        source=ImageSource.PEXELS.value,
                        url=photo["src"]["large"],
                        thumbnail_url=photo["src"]["medium"],
                        title=photo.get("alt", f"Pexels image {photo['id']}"),
                        description=photo.get("alt"),
                        tags=[query],  # Pexels doesn't provide tags
                        attribution=f"Photo by {photo['photographer']}",
                        license="Pexels License",
                        width=photo["width"],
                        height=photo["height"],
                        relevance_score=0.8,
                    )
                )

    except requests.RequestException as e:
        logger.error(f"Pexels API error: {str(e)}")

    return results


@tracer.capture_method
def search_pixabay(query: str, max_results: int) -> List[ImageResult]:
    """Search Pixabay API for stock images"""
    results = []

    if not PIXABAY_API_KEY:
        logger.info("Pixabay API key not configured, skipping")
        return results

    try:
        params = {
            "key": PIXABAY_API_KEY,
            "q": query,
            "per_page": max_results,
            "image_type": "photo",
            "orientation": "horizontal",
            "safesearch": "true",
        }

        response = requests.get("https://pixabay.com/api/", params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            for hit in data.get("hits", []):
                results.append(
                    ImageResult(
                        image_id=str(hit["id"]),
                        source=ImageSource.PIXABAY.value,
                        url=hit["largeImageURL"],
                        thumbnail_url=hit["previewURL"],
                        title=f"Pixabay image {hit['id']}",
                        description=None,
                        tags=hit.get("tags", "").split(", "),
                        attribution=f"Image by {hit['user']}",
                        license="Pixabay License",
                        width=hit["imageWidth"],
                        height=hit["imageHeight"],
                        file_size=hit.get("imageSize"),
                        relevance_score=0.7,
                    )
                )

    except requests.RequestException as e:
        logger.error(f"Pixabay API error: {str(e)}")

    return results


@tracer.capture_method
def generate_placeholder_result(query: str) -> ImageResult:
    """Generate a placeholder image result"""
    # Generate placeholder using picsum.photos or similar service
    seed = hashlib.md5(query.encode()).hexdigest()[:10]

    return ImageResult(
        image_id=f"placeholder_{seed}",
        source=ImageSource.PLACEHOLDER.value,
        url=f"https://picsum.photos/seed/{seed}/1920/1080",
        thumbnail_url=f"https://picsum.photos/seed/{seed}/400/300",
        title=f"Placeholder for '{query}'",
        description="AI-selected placeholder image",
        tags=[query, "placeholder"],
        attribution="Lorem Picsum",
        license="Creative Commons CC0",
        width=1920,
        height=1080,
        relevance_score=0.3,
    )


@tracer.capture_method
def analyze_image_with_rekognition(image_url: str) -> Dict[str, Any]:
    """Use AWS Rekognition to analyze image content"""
    if not ENABLE_REKOGNITION:
        return {}

    try:
        # Download image
        response = requests.get(image_url, timeout=5)
        image_bytes = response.content

        # Detect labels
        rekognition_response = rekognition.detect_labels(
            Image={"Bytes": image_bytes}, MaxLabels=10, MinConfidence=70
        )

        labels = [label["Name"] for label in rekognition_response["Labels"]]

        # Detect text if present
        text_response = rekognition.detect_text(Image={"Bytes": image_bytes})

        detected_text = [
            text["DetectedText"] for text in text_response.get("TextDetections", [])
        ]

        return {
            "labels": labels,
            "detected_text": detected_text,
            "dominant_colors": [],  # Could add color detection
            "has_text": len(detected_text) > 0,
        }

    except Exception as e:
        logger.warning(f"Rekognition analysis failed: {str(e)}")
        return {}


@tracer.capture_method
def calculate_relevance_score(
    result: ImageResult, query: str, context: Optional[Dict[str, Any]] = None
) -> float:
    """Calculate relevance score based on query match and context"""
    score = result.relevance_score  # Start with source's base score

    # Query matching in title and tags
    query_words = set(query.lower().split())
    title_words = set(result.title.lower().split()) if result.title else set()
    tag_words = set(" ".join(result.tags).lower().split()) if result.tags else set()

    # Increase score for matches
    title_matches = len(query_words & title_words)
    tag_matches = len(query_words & tag_words)

    score += title_matches * 0.1
    score += tag_matches * 0.05

    # Context matching if provided
    if context:
        if (
            context.get("style") == "professional"
            and "business" in " ".join(result.tags).lower()
        ):
            score += 0.1
        if (
            context.get("style") == "creative"
            and "artistic" in " ".join(result.tags).lower()
        ):
            score += 0.1

    # Penalize placeholders
    if result.source == ImageSource.PLACEHOLDER.value:
        score *= 0.5

    return min(1.0, score)  # Cap at 1.0


@tracer.capture_method
def search_images_parallel(
    queries: List[str], sources: List[str], max_results: int
) -> Dict[str, List[ImageResult]]:
    """Search for images in parallel across multiple sources"""
    all_results = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}

        for query in queries:
            query_futures = []

            # Submit searches to different sources
            if ImageSource.S3_LIBRARY.value in sources:
                future = executor.submit(search_s3_library, query, max_results)
                query_futures.append((ImageSource.S3_LIBRARY.value, future))

            if ImageSource.PEXELS.value in sources:
                future = executor.submit(search_pexels, query, max_results)
                query_futures.append((ImageSource.PEXELS.value, future))

            if ImageSource.PIXABAY.value in sources:
                future = executor.submit(search_pixabay, query, max_results)
                query_futures.append((ImageSource.PIXABAY.value, future))

            futures[query] = query_futures

        # Collect results
        for query, query_futures in futures.items():
            results = []

            for source, future in query_futures:
                try:
                    source_results = future.result(timeout=10)
                    results.extend(source_results)
                except Exception as e:
                    logger.error(f"Error searching {source} for '{query}': {str(e)}")

            # Add placeholder if no results
            if not results:
                results.append(generate_placeholder_result(query))

            # Calculate relevance scores and sort
            for result in results:
                result.relevance_score = calculate_relevance_score(result, query)

            results.sort(key=lambda x: x.relevance_score, reverse=True)

            # Limit results
            all_results[query] = results[:max_results]

    return all_results


@tracer.capture_method
def save_search_metadata(
    presentation_id: str,
    session_id: Optional[str],
    search_results: Dict[str, List[ImageResult]],
):
    """Save search metadata to DynamoDB"""
    try:
        table = dynamodb.Table(SESSIONS_TABLE)

        # Prepare item
        item = {
            "session_id": session_id or presentation_id,
            "presentation_id": presentation_id,
            "search_timestamp": int(datetime.now(timezone.utc).timestamp()),
            "search_type": "image_search",
            "queries": list(search_results.keys()),
            "results_count": sum(len(results) for results in search_results.values()),
            "sources": list(
                set(
                    result.source
                    for results in search_results.values()
                    for result in results
                )
            ),
        }

        # Save to DynamoDB
        table.put_item(Item=item)

        logger.info(f"Saved search metadata for presentation {presentation_id}")

    except ClientError as e:
        logger.error(f"Error saving search metadata: {str(e)}")


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Main Lambda handler for image search"""

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
            request = SearchRequest(**body)
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

        # Determine sources to search
        if request.preferred_sources:
            sources = request.preferred_sources
        else:
            # Default sources based on availability
            sources = []
            if IMAGE_LIBRARY_BUCKET:
                sources.append(ImageSource.S3_LIBRARY.value)
            if PEXELS_API_KEY:
                sources.append(ImageSource.PEXELS.value)
            if PIXABAY_API_KEY:
                sources.append(ImageSource.PIXABAY.value)
            if not sources:
                sources = [ImageSource.PLACEHOLDER.value]

        logger.info(f"Searching {len(request.search_queries)} queries across {sources}")

        # Perform parallel search
        search_results = search_images_parallel(
            request.search_queries, sources, request.max_results_per_query
        )

        # Optionally analyze images with Rekognition
        if ENABLE_REKOGNITION and request.include_metadata:
            for query_results in search_results.values():
                for result in query_results[:3]:  # Analyze top 3
                    if result.metadata is None:
                        result.metadata = {}
                    result.metadata["rekognition"] = analyze_image_with_rekognition(
                        result.url
                    )

        # Save metadata
        save_search_metadata(
            request.presentation_id, request.session_id, search_results
        )

        # Calculate search time
        search_time_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        # Record metrics
        metrics.add_metric(name="ImageSearchCompleted", unit=MetricUnit.Count, value=1)
        metrics.add_metric(
            name="TotalImagesFound",
            unit=MetricUnit.Count,
            value=sum(len(r) for r in search_results.values()),
        )
        metrics.add_metric(
            name="SearchTimeMs", unit=MetricUnit.Milliseconds, value=search_time_ms
        )

        # Prepare response
        response_data = SearchResponse(
            success=True,
            presentation_id=request.presentation_id,
            search_results=search_results,
            total_results=sum(len(results) for results in search_results.values()),
            sources_searched=sources,
            search_time_ms=search_time_ms,
            message="Image search completed successfully",
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
        metrics.add_metric(name="ImageSearchError", unit=MetricUnit.Count, value=1)

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
