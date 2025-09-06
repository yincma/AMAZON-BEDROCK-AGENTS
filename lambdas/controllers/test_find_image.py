"""
Unit tests for Find Image Lambda Function
"""

import json
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

# Set environment variables before importing the handler
os.environ["S3_BUCKET"] = "test-bucket"
os.environ["SESSIONS_TABLE"] = "test-sessions-table"
os.environ["IMAGE_LIBRARY_BUCKET"] = "test-library-bucket"
os.environ["PEXELS_API_KEY"] = "test-pexels-key"
os.environ["PIXABAY_API_KEY"] = "test-pixabay-key"
os.environ["MAX_SEARCH_RESULTS"] = "10"
os.environ["ENABLE_REKOGNITION"] = "true"

from find_image import (
    ImageResult,
    ImageSource,
    SearchRequest,
    analyze_image_with_rekognition,
    calculate_relevance_score,
    generate_placeholder_result,
    lambda_handler,
    search_images_parallel,
    search_pexels,
    search_pixabay,
    search_s3_library,
)


@pytest.fixture
def valid_event():
    """Valid API Gateway event"""
    return {
        "body": json.dumps(
            {
                "presentation_id": "test-presentation-123",
                "session_id": "test-session-456",
                "search_queries": ["business meeting", "data visualization"],
                "slide_context": {
                    "slide_number": 1,
                    "title": "Introduction",
                    "style": "professional",
                },
                "preferred_sources": ["pexels", "pixabay"],
                "max_results_per_query": 5,
                "include_metadata": True,
                "language": "en",
            }
        ),
        "headers": {"Content-Type": "application/json"},
        "requestContext": {"requestId": "test-request-id"},
    }


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.request_id = "test-request-id"
    context.function_name = "find-image"
    context.memory_limit_in_mb = "256"
    context.invoked_function_arn = (
        "arn:aws:lambda:us-west-2:123456789:function:find-image"
    )
    return context


@pytest.fixture
def mock_s3_response():
    """Mock S3 list objects response"""
    return {
        "Contents": [
            {
                "Key": "images/business_meeting_001.jpg",
                "Size": 1024000,
                "LastModified": datetime.now(timezone.utc),
            },
            {
                "Key": "images/business_meeting_002.jpg",
                "Size": 2048000,
                "LastModified": datetime.now(timezone.utc),
            },
        ]
    }


@pytest.fixture
def mock_pexels_response():
    """Mock Pexels API response"""
    return {
        "photos": [
            {
                "id": 12345,
                "width": 1920,
                "height": 1080,
                "url": "https://www.pexels.com/photo/12345/",
                "photographer": "John Doe",
                "src": {
                    "original": "https://images.pexels.com/photos/12345/original.jpg",
                    "large": "https://images.pexels.com/photos/12345/large.jpg",
                    "medium": "https://images.pexels.com/photos/12345/medium.jpg",
                },
                "alt": "Business meeting in modern office",
            }
        ],
        "total_results": 100,
        "page": 1,
        "per_page": 5,
    }


@pytest.fixture
def mock_pixabay_response():
    """Mock Pixabay API response"""
    return {
        "total": 50,
        "totalHits": 50,
        "hits": [
            {
                "id": 67890,
                "pageURL": "https://pixabay.com/photos/67890/",
                "type": "photo",
                "tags": "business, meeting, office",
                "previewURL": "https://cdn.pixabay.com/photo/preview.jpg",
                "largeImageURL": "https://cdn.pixabay.com/photo/large.jpg",
                "imageWidth": 1920,
                "imageHeight": 1080,
                "imageSize": 1500000,
                "user": "Jane Smith",
                "user_id": 123,
            }
        ],
    }


class TestSearchRequest:
    """Test request validation"""

    def test_valid_request(self):
        """Test valid request creation"""
        request = SearchRequest(
            presentation_id="test-123",
            search_queries=["test query"],
            max_results_per_query=5,
        )
        assert request.presentation_id == "test-123"
        assert request.search_queries == ["test query"]

    def test_invalid_sources(self):
        """Test source validation"""
        with pytest.raises(ValueError):
            SearchRequest(
                presentation_id="test-123",
                search_queries=["test"],
                preferred_sources=["invalid_source"],
            )

    def test_empty_queries(self):
        """Test empty queries validation"""
        with pytest.raises(ValueError):
            SearchRequest(presentation_id="test-123", search_queries=[])

    def test_max_queries_limit(self):
        """Test maximum queries limit"""
        with pytest.raises(ValueError):
            SearchRequest(
                presentation_id="test-123",
                search_queries=["q" + str(i) for i in range(11)],
            )


class TestS3Library:
    """Test S3 library search"""

    @patch("find_image.s3")
    def test_search_s3_library_success(self, mock_s3, mock_s3_response):
        """Test successful S3 library search"""
        mock_s3.list_objects_v2.return_value = mock_s3_response
        mock_s3.head_object.return_value = {
            "Metadata": {
                "title": "Business Meeting",
                "description": "Professional meeting",
                "tags": "business,meeting,office",
                "attribution": "Company Photos",
            }
        }
        mock_s3.generate_presigned_url.return_value = "https://s3.example.com/image.jpg"

        results = search_s3_library("business meeting", 5)

        assert len(results) == 2
        assert results[0].source == ImageSource.S3_LIBRARY.value
        assert results[0].title == "Business Meeting"
        assert "business" in results[0].tags

    @patch("find_image.s3")
    def test_search_s3_library_no_results(self, mock_s3):
        """Test S3 library search with no results"""
        mock_s3.list_objects_v2.return_value = {}

        results = search_s3_library("nonexistent", 5)

        assert results == []

    @patch("find_image.s3")
    def test_search_s3_library_error(self, mock_s3):
        """Test S3 library search error handling"""
        mock_s3.list_objects_v2.side_effect = Exception("S3 error")

        results = search_s3_library("test", 5)

        assert results == []


class TestPexelsSearch:
    """Test Pexels API search"""

    @patch("requests.get")
    def test_search_pexels_success(self, mock_get, mock_pexels_response):
        """Test successful Pexels search"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pexels_response
        mock_get.return_value = mock_response

        results = search_pexels("business meeting", 5)

        assert len(results) == 1
        assert results[0].source == ImageSource.PEXELS.value
        assert results[0].attribution == "Photo by John Doe"
        assert results[0].width == 1920

    @patch("requests.get")
    def test_search_pexels_api_error(self, mock_get):
        """Test Pexels API error"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        results = search_pexels("test", 5)

        assert results == []

    @patch("requests.get")
    def test_search_pexels_timeout(self, mock_get):
        """Test Pexels API timeout"""
        mock_get.side_effect = Exception("Timeout")

        results = search_pexels("test", 5)

        assert results == []


class TestPixabaySearch:
    """Test Pixabay API search"""

    @patch("requests.get")
    def test_search_pixabay_success(self, mock_get, mock_pixabay_response):
        """Test successful Pixabay search"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_pixabay_response
        mock_get.return_value = mock_response

        results = search_pixabay("business meeting", 5)

        assert len(results) == 1
        assert results[0].source == ImageSource.PIXABAY.value
        assert results[0].attribution == "Image by Jane Smith"
        assert "business" in results[0].tags

    @patch("requests.get")
    def test_search_pixabay_no_results(self, mock_get):
        """Test Pixabay search with no results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": [], "total": 0}
        mock_get.return_value = mock_response

        results = search_pixabay("obscure query", 5)

        assert results == []


class TestPlaceholderGeneration:
    """Test placeholder image generation"""

    def test_generate_placeholder(self):
        """Test placeholder generation"""
        result = generate_placeholder_result("test query")

        assert result.source == ImageSource.PLACEHOLDER.value
        assert "placeholder" in result.image_id
        assert result.width == 1920
        assert result.height == 1080
        assert result.relevance_score == 0.3

    def test_placeholder_consistency(self):
        """Test placeholder generation is consistent"""
        result1 = generate_placeholder_result("same query")
        result2 = generate_placeholder_result("same query")

        assert result1.image_id == result2.image_id
        assert result1.url == result2.url


class TestRekognitionAnalysis:
    """Test AWS Rekognition image analysis"""

    @patch("find_image.rekognition")
    @patch("requests.get")
    def test_analyze_image_success(self, mock_get, mock_rekognition):
        """Test successful image analysis"""
        mock_response = Mock()
        mock_response.content = b"image_data"
        mock_get.return_value = mock_response

        mock_rekognition.detect_labels.return_value = {
            "Labels": [
                {"Name": "Office", "Confidence": 95.5},
                {"Name": "Meeting", "Confidence": 90.2},
            ]
        }
        mock_rekognition.detect_text.return_value = {
            "TextDetections": [{"DetectedText": "AGENDA", "Type": "LINE"}]
        }

        result = analyze_image_with_rekognition("https://example.com/image.jpg")

        assert "Office" in result["labels"]
        assert "Meeting" in result["labels"]
        assert "AGENDA" in result["detected_text"]
        assert result["has_text"] is True

    @patch("find_image.rekognition")
    @patch("requests.get")
    def test_analyze_image_failure(self, mock_get, mock_rekognition):
        """Test image analysis failure handling"""
        mock_get.side_effect = Exception("Download failed")

        result = analyze_image_with_rekognition("https://example.com/image.jpg")

        assert result == {}


class TestRelevanceScoring:
    """Test relevance score calculation"""

    def test_calculate_relevance_basic(self):
        """Test basic relevance calculation"""
        image = ImageResult(
            image_id="test",
            source="pexels",
            url="https://example.com/image.jpg",
            title="Business Meeting Photo",
            tags=["business", "office"],
            relevance_score=0.5,
        )

        score = calculate_relevance_score(image, "business meeting", None)

        assert score > 0.5  # Should be higher due to matches
        assert score <= 1.0

    def test_calculate_relevance_with_context(self):
        """Test relevance with context"""
        image = ImageResult(
            image_id="test",
            source="pexels",
            url="https://example.com/image.jpg",
            title="Professional Office",
            tags=["business", "professional"],
            relevance_score=0.5,
        )

        context = {"style": "professional"}
        score = calculate_relevance_score(image, "office", context)

        assert score > 0.5  # Should be higher due to style match

    def test_placeholder_penalty(self):
        """Test placeholder relevance penalty"""
        image = ImageResult(
            image_id="placeholder_123",
            source=ImageSource.PLACEHOLDER.value,
            url="https://picsum.photos/1920/1080",
            title="Placeholder",
            tags=["placeholder"],
            relevance_score=0.6,
        )

        score = calculate_relevance_score(image, "test", None)

        assert score == 0.3  # Should be penalized


class TestParallelSearch:
    """Test parallel image search"""

    @patch("find_image.search_pixabay")
    @patch("find_image.search_pexels")
    @patch("find_image.search_s3_library")
    def test_parallel_search_success(self, mock_s3, mock_pexels, mock_pixabay):
        """Test successful parallel search"""
        mock_s3.return_value = [
            ImageResult(
                image_id="s3_1",
                source=ImageSource.S3_LIBRARY.value,
                url="https://s3.example.com/1.jpg",
                title="S3 Image",
                relevance_score=0.9,
            )
        ]
        mock_pexels.return_value = [
            ImageResult(
                image_id="pexels_1",
                source=ImageSource.PEXELS.value,
                url="https://pexels.com/1.jpg",
                title="Pexels Image",
                relevance_score=0.8,
            )
        ]
        mock_pixabay.return_value = []

        results = search_images_parallel(
            ["test query"],
            [
                ImageSource.S3_LIBRARY.value,
                ImageSource.PEXELS.value,
                ImageSource.PIXABAY.value,
            ],
            5,
        )

        assert "test query" in results
        assert len(results["test query"]) >= 2
        # Results should be sorted by relevance
        assert (
            results["test query"][0].relevance_score
            >= results["test query"][1].relevance_score
        )

    @patch("find_image.search_pixabay")
    @patch("find_image.search_pexels")
    def test_parallel_search_with_placeholder(self, mock_pexels, mock_pixabay):
        """Test parallel search falls back to placeholder"""
        mock_pexels.return_value = []
        mock_pixabay.return_value = []

        results = search_images_parallel(
            ["no results query"],
            [ImageSource.PEXELS.value, ImageSource.PIXABAY.value],
            5,
        )

        assert "no results query" in results
        assert len(results["no results query"]) == 1
        assert results["no results query"][0].source == ImageSource.PLACEHOLDER.value


class TestLambdaHandler:
    """Test main Lambda handler"""

    @patch("find_image.save_search_metadata")
    @patch("find_image.search_images_parallel")
    def test_successful_search(
        self, mock_search, mock_save, valid_event, lambda_context
    ):
        """Test successful image search"""
        mock_search.return_value = {
            "business meeting": [
                ImageResult(
                    image_id="img1",
                    source="pexels",
                    url="https://example.com/1.jpg",
                    title="Meeting",
                    relevance_score=0.8,
                )
            ],
            "data visualization": [
                ImageResult(
                    image_id="img2",
                    source="pixabay",
                    url="https://example.com/2.jpg",
                    title="Charts",
                    relevance_score=0.7,
                )
            ],
        }

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["total_results"] == 2
        assert "business meeting" in body["search_results"]
        assert "data visualization" in body["search_results"]

        mock_search.assert_called_once()
        mock_save.assert_called_once()

    def test_invalid_request(self, lambda_context):
        """Test invalid request handling"""
        event = {
            "body": json.dumps(
                {
                    "presentation_id": "test-123",
                    "search_queries": [],  # Invalid: empty queries
                }
            )
        }

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body

    @patch("find_image.search_images_parallel")
    def test_search_error_handling(self, mock_search, valid_event, lambda_context):
        """Test error handling during search"""
        mock_search.side_effect = Exception("Search failed")

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 500
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body

    @patch("find_image.analyze_image_with_rekognition")
    @patch("find_image.search_images_parallel")
    def test_rekognition_integration(
        self, mock_search, mock_rekognition, valid_event, lambda_context
    ):
        """Test Rekognition integration"""
        mock_search.return_value = {
            "business meeting": [
                ImageResult(
                    image_id="img1",
                    source="pexels",
                    url="https://example.com/1.jpg",
                    title="Meeting",
                    relevance_score=0.8,
                )
            ]
        }
        mock_rekognition.return_value = {
            "labels": ["Office", "Meeting"],
            "has_text": False,
        }

        response = lambda_handler(valid_event, lambda_context)

        assert response["statusCode"] == 200
        json.loads(response["body"])

        # Check if Rekognition was called for top results
        mock_rekognition.assert_called()

    def test_cors_headers(self, valid_event, lambda_context):
        """Test CORS headers in response"""
        response = lambda_handler(valid_event, lambda_context)

        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert response["headers"]["Content-Type"] == "application/json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
