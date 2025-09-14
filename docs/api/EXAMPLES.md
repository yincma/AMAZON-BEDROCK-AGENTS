# API Usage Examples

This document provides comprehensive examples for using the AI PPT Assistant API, including complete workflows, code samples in multiple languages, and advanced use cases.

## Table of Contents

- [Basic Workflows](#basic-workflows)
- [Authentication Examples](#authentication-examples)
- [Complete Integration Examples](#complete-integration-examples)
- [Advanced Use Cases](#advanced-use-cases)
- [Error Handling Examples](#error-handling-examples)
- [SDK Examples](#sdk-examples)

## Basic Workflows

### 1. Simple Presentation Generation

#### cURL Example
```bash
# Step 1: Generate presentation
curl -X POST https://api.ai-ppt-assistant.com/v1/presentations/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "topic": "Introduction to Machine Learning",
    "page_count": 8,
    "style": "professional",
    "language": "en",
    "audience": "technical"
  }'

# Response:
# {
#   "presentation_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "pending",
#   "estimated_completion_time": 30,
#   "status_url": "https://api.ai-ppt-assistant.com/v1/presentations/550e8400-e29b-41d4-a716-446655440000/status"
# }

# Step 2: Check status (poll until completed)
curl -X GET https://api.ai-ppt-assistant.com/v1/presentations/550e8400-e29b-41d4-a716-446655440000/status \
  -H "X-API-Key: your-api-key-here"

# Step 3: Download when ready
curl -X GET https://api.ai-ppt-assistant.com/v1/presentations/550e8400-e29b-41d4-a716-446655440000/download \
  -H "X-API-Key: your-api-key-here"
```

#### Python Example
```python
import requests
import time
import json

# Configuration
API_KEY = "your-api-key-here"
BASE_URL = "https://api.ai-ppt-assistant.com/v1"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def generate_simple_presentation():
    # Step 1: Generate presentation
    payload = {
        "topic": "Introduction to Machine Learning",
        "page_count": 8,
        "style": "professional",
        "language": "en",
        "audience": "technical"
    }

    response = requests.post(
        f"{BASE_URL}/presentations/generate",
        headers=HEADERS,
        json=payload
    )
    response.raise_for_status()

    generation_data = response.json()
    presentation_id = generation_data["presentation_id"]
    print(f"Generation started: {presentation_id}")

    # Step 2: Wait for completion
    while True:
        status_response = requests.get(
            f"{BASE_URL}/presentations/{presentation_id}/status",
            headers=HEADERS
        )
        status_response.raise_for_status()

        status_data = status_response.json()
        status = status_data["status"]
        progress = status_data.get("progress", 0)

        print(f"Status: {status}, Progress: {progress}%")

        if status == "completed":
            break
        elif status == "failed":
            raise Exception(f"Generation failed: {status_data.get('error', {}).get('message')}")

        time.sleep(5)  # Wait 5 seconds before next check

    # Step 3: Get download URL
    download_response = requests.get(
        f"{BASE_URL}/presentations/{presentation_id}/download",
        headers=HEADERS
    )
    download_response.raise_for_status()

    download_data = download_response.json()
    download_url = download_data["download_url"]

    print(f"Presentation ready: {download_url}")
    return download_url

# Run example
if __name__ == "__main__":
    download_url = generate_simple_presentation()
```

#### JavaScript Example
```javascript
const API_KEY = 'your-api-key-here';
const BASE_URL = 'https://api.ai-ppt-assistant.com/v1';

async function generateSimplePresentation() {
    // Step 1: Generate presentation
    const generateResponse = await fetch(`${BASE_URL}/presentations/generate`, {
        method: 'POST',
        headers: {
            'X-API-Key': API_KEY,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            topic: 'Introduction to Machine Learning',
            page_count: 8,
            style: 'professional',
            language: 'en',
            audience: 'technical'
        })
    });

    if (!generateResponse.ok) {
        throw new Error(`Generation failed: ${generateResponse.statusText}`);
    }

    const generationData = await generateResponse.json();
    const presentationId = generationData.presentation_id;
    console.log(`Generation started: ${presentationId}`);

    // Step 2: Wait for completion
    while (true) {
        const statusResponse = await fetch(
            `${BASE_URL}/presentations/${presentationId}/status`,
            {
                headers: { 'X-API-Key': API_KEY }
            }
        );

        if (!statusResponse.ok) {
            throw new Error(`Status check failed: ${statusResponse.statusText}`);
        }

        const statusData = await statusResponse.json();
        const status = statusData.status;
        const progress = statusData.progress || 0;

        console.log(`Status: ${status}, Progress: ${progress}%`);

        if (status === 'completed') {
            break;
        } else if (status === 'failed') {
            throw new Error(`Generation failed: ${statusData.error?.message}`);
        }

        await new Promise(resolve => setTimeout(resolve, 5000));
    }

    // Step 3: Get download URL
    const downloadResponse = await fetch(
        `${BASE_URL}/presentations/${presentationId}/download`,
        {
            headers: { 'X-API-Key': API_KEY }
        }
    );

    if (!downloadResponse.ok) {
        throw new Error(`Download failed: ${downloadResponse.statusText}`);
    }

    const downloadData = await downloadResponse.json();
    const downloadUrl = downloadData.download_url;

    console.log(`Presentation ready: ${downloadUrl}`);
    return downloadUrl;
}

// Usage
generateSimplePresentation()
    .then(url => console.log('Success:', url))
    .catch(error => console.error('Error:', error));
```

### 2. Advanced Presentation with Custom Metadata

```bash
curl -X POST https://api.ai-ppt-assistant.com/v1/presentations/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "topic": "Quarterly Business Review - Q4 2024",
    "page_count": 15,
    "style": "business",
    "language": "en",
    "audience": "executive",
    "metadata": {
      "company": "TechCorp Inc",
      "quarter": "Q4",
      "year": 2024,
      "include_charts": true,
      "include_financials": true,
      "theme_color": "#1E3A8A",
      "industry": "technology",
      "complexity_level": "executive",
      "sections": [
        "executive_summary",
        "financial_performance",
        "market_analysis",
        "strategic_initiatives",
        "outlook"
      ]
    }
  }'
```

## Authentication Examples

### API Key Authentication

```python
import requests

# Using API Key
headers = {
    "X-API-Key": "ak_1234567890abcdef",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.ai-ppt-assistant.com/v1/presentations/generate",
    headers=headers,
    json={"topic": "Test Presentation"}
)
```

### Bearer Token Authentication

```javascript
// Using JWT Bearer Token
const response = await fetch('https://api.ai-ppt-assistant.com/v1/presentations/generate', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        topic: 'Test Presentation'
    })
});
```

## Complete Integration Examples

### 1. Presentation Management System

```python
import requests
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class PresentationRequest:
    topic: str
    page_count: int = 10
    style: str = "professional"
    language: str = "en"
    audience: str = "general"
    metadata: Optional[Dict] = None

class AIPPTClient:
    def __init__(self, api_key: str, base_url: str = "https://api.ai-ppt-assistant.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)

    def generate_presentation(self, request: PresentationRequest) -> str:
        """Generate a new presentation and return presentation ID"""
        payload = {
            "topic": request.topic,
            "page_count": request.page_count,
            "style": request.style,
            "language": request.language,
            "audience": request.audience
        }

        if request.metadata:
            payload["metadata"] = request.metadata

        response = requests.post(
            f"{self.base_url}/presentations/generate",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()

        data = response.json()
        presentation_id = data["presentation_id"]

        self.logger.info(f"Started generation for presentation: {presentation_id}")
        return presentation_id

    def wait_for_completion(self, presentation_id: str, timeout: int = 300) -> Dict:
        """Wait for presentation to complete with timeout"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_status(presentation_id)

            if status["status"] == "completed":
                self.logger.info(f"Presentation {presentation_id} completed")
                return status
            elif status["status"] == "failed":
                error_msg = status.get("error", {}).get("message", "Unknown error")
                raise Exception(f"Generation failed: {error_msg}")

            self.logger.debug(f"Status: {status['status']}, Progress: {status.get('progress', 0)}%")
            time.sleep(5)

        raise TimeoutError(f"Presentation generation timed out after {timeout} seconds")

    def get_status(self, presentation_id: str) -> Dict:
        """Get presentation status"""
        response = requests.get(
            f"{self.base_url}/presentations/{presentation_id}/status",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def download_presentation(self, presentation_id: str) -> str:
        """Get download URL for completed presentation"""
        response = requests.get(
            f"{self.base_url}/presentations/{presentation_id}/download",
            headers=self.headers
        )
        response.raise_for_status()

        data = response.json()
        return data["download_url"]

    def update_slide(self, presentation_id: str, slide_number: int, updates: Dict, etag: Optional[str] = None) -> Dict:
        """Update a specific slide"""
        headers = self.headers.copy()
        if etag:
            headers["If-Match"] = etag

        response = requests.patch(
            f"{self.base_url}/presentations/{presentation_id}/slides/{slide_number}",
            headers=headers,
            json=updates
        )
        response.raise_for_status()
        return response.json()

    def regenerate_image(self, presentation_id: str, slide_number: int, prompt: str, style: str = "realistic") -> str:
        """Regenerate image for a specific slide"""
        payload = {
            "prompt": prompt,
            "style": style,
            "quality": "high"
        }

        response = requests.post(
            f"{self.base_url}/presentations/{presentation_id}/slides/{slide_number}/image",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()

        data = response.json()
        return data["task_id"]

    def get_task_status(self, task_id: str) -> Dict:
        """Get status of an async task"""
        response = requests.get(
            f"{self.base_url}/tasks/{task_id}/status",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def delete_presentation(self, presentation_id: str, force: bool = False) -> None:
        """Delete a presentation"""
        params = {"force": "true"} if force else {}

        response = requests.delete(
            f"{self.base_url}/presentations/{presentation_id}",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()

        self.logger.info(f"Deleted presentation: {presentation_id}")

# Usage Example
def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Initialize client
    client = AIPPTClient("your-api-key-here")

    # Create presentation request
    request = PresentationRequest(
        topic="Digital Transformation Strategy",
        page_count=12,
        style="business",
        audience="executive",
        metadata={
            "industry": "financial_services",
            "focus_areas": ["technology", "operations", "customer_experience"],
            "timeline": "2024-2025"
        }
    )

    try:
        # Generate presentation
        presentation_id = client.generate_presentation(request)

        # Wait for completion
        final_status = client.wait_for_completion(presentation_id)

        # Download presentation
        download_url = client.download_presentation(presentation_id)
        print(f"Presentation ready: {download_url}")

        # Example: Update slide 3 with custom content
        slide_updates = {
            "title": "Key Strategic Initiatives",
            "content": "• Cloud Migration\n• Data Analytics Platform\n• Customer Digital Experience",
            "speaker_notes": "Emphasize the ROI of each initiative"
        }

        update_result = client.update_slide(presentation_id, 3, slide_updates)
        print(f"Updated slide 3, new ETag: {update_result['etag']}")

        # Example: Regenerate image for slide 5
        task_id = client.regenerate_image(
            presentation_id,
            5,
            "Modern office with digital transformation elements",
            "professional"
        )
        print(f"Image regeneration started: {task_id}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
```

### 2. Batch Presentation Generator

```python
import asyncio
import aiohttp
from typing import List
import json

class BatchPresentationGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.ai-ppt-assistant.com/v1"
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    async def generate_multiple_presentations(self, requests: List[Dict]) -> List[str]:
        """Generate multiple presentations concurrently"""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._generate_single(session, request)
                for request in requests
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter successful results
            presentation_ids = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Request {i} failed: {result}")
                else:
                    presentation_ids.append(result)

            return presentation_ids

    async def _generate_single(self, session: aiohttp.ClientSession, request: Dict) -> str:
        """Generate a single presentation"""
        async with session.post(
            f"{self.base_url}/presentations/generate",
            headers=self.headers,
            json=request
        ) as response:
            response.raise_for_status()
            data = await response.json()
            return data["presentation_id"]

    async def wait_for_all_completions(self, presentation_ids: List[str]) -> List[Dict]:
        """Wait for all presentations to complete"""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._wait_for_completion(session, pid)
                for pid in presentation_ids
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in results if not isinstance(r, Exception)]

    async def _wait_for_completion(self, session: aiohttp.ClientSession, presentation_id: str) -> Dict:
        """Wait for a single presentation to complete"""
        while True:
            async with session.get(
                f"{self.base_url}/presentations/{presentation_id}/status",
                headers=self.headers
            ) as response:
                response.raise_for_status()
                status_data = await response.json()

                if status_data["status"] == "completed":
                    return status_data
                elif status_data["status"] == "failed":
                    raise Exception(f"Generation failed: {presentation_id}")

                await asyncio.sleep(5)

# Usage Example
async def main():
    generator = BatchPresentationGenerator("your-api-key-here")

    # Define multiple presentation requests
    requests = [
        {
            "topic": "Q1 2024 Financial Results",
            "style": "business",
            "page_count": 10
        },
        {
            "topic": "Product Roadmap 2024",
            "style": "professional",
            "page_count": 12
        },
        {
            "topic": "Team Performance Review",
            "style": "minimal",
            "page_count": 8
        }
    ]

    # Generate all presentations
    presentation_ids = await generator.generate_multiple_presentations(requests)
    print(f"Started {len(presentation_ids)} presentations")

    # Wait for all to complete
    completed = await generator.wait_for_all_completions(presentation_ids)
    print(f"Completed {len(completed)} presentations")

# Run the async function
asyncio.run(main())
```

## Advanced Use Cases

### 1. Slide-by-Slide Customization

```python
def customize_presentation_slides(client: AIPPTClient, presentation_id: str):
    """Customize each slide individually"""

    # Get current status to check number of slides
    status = client.get_status(presentation_id)
    total_slides = status["metadata"]["page_count"]

    customizations = {
        1: {
            "title": "Executive Summary",
            "layout": "title",
            "style_overrides": {
                "background_color": "#1E3A8A",
                "font_size": 24
            }
        },
        2: {
            "title": "Market Overview",
            "layout": "two_column",
            "content": "Left column: Market size and trends\nRight column: Competitive landscape"
        },
        3: {
            "title": "Our Solution",
            "layout": "image_left",
            "speaker_notes": "Emphasize unique value proposition"
        }
    }

    for slide_num, updates in customizations.items():
        if slide_num <= total_slides:
            try:
                result = client.update_slide(presentation_id, slide_num, updates)
                print(f"Updated slide {slide_num}: {result['etag']}")
            except Exception as e:
                print(f"Failed to update slide {slide_num}: {e}")
```

### 2. Dynamic Content with Real-time Data

```python
import requests
from datetime import datetime

def generate_data_driven_presentation(client: AIPPTClient):
    """Generate presentation with real-time data"""

    # Fetch real-time data (example: stock prices, metrics, etc.)
    def fetch_market_data():
        # This would typically call a real API
        return {
            "stock_price": "$142.35",
            "change": "+2.8%",
            "market_cap": "$2.1T",
            "pe_ratio": "28.5"
        }

    def fetch_business_metrics():
        return {
            "revenue": "$5.2M",
            "growth": "+15.3%",
            "customers": "12,847",
            "retention": "94.2%"
        }

    # Get current data
    market_data = fetch_market_data()
    business_metrics = fetch_business_metrics()
    current_date = datetime.now().strftime("%B %d, %Y")

    # Create presentation with dynamic content
    request = PresentationRequest(
        topic=f"Business Performance Dashboard - {current_date}",
        page_count=8,
        style="business",
        audience="executive",
        metadata={
            "data_snapshot": current_date,
            "auto_generated": True,
            "market_data": market_data,
            "business_metrics": business_metrics,
            "include_real_time_charts": True
        }
    )

    presentation_id = client.generate_presentation(request)
    return presentation_id
```

### 3. Multi-language Presentation Series

```python
def generate_multilingual_presentations(client: AIPPTClient, base_topic: str):
    """Generate the same presentation in multiple languages"""

    languages = [
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Spanish"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "zh", "name": "Chinese"}
    ]

    presentation_ids = {}

    for lang in languages:
        request = PresentationRequest(
            topic=base_topic,
            page_count=10,
            style="professional",
            language=lang["code"],
            metadata={
                "series": "multilingual",
                "base_topic": base_topic,
                "target_language": lang["name"]
            }
        )

        try:
            presentation_id = client.generate_presentation(request)
            presentation_ids[lang["code"]] = presentation_id
            print(f"Started generation for {lang['name']}: {presentation_id}")
        except Exception as e:
            print(f"Failed to start generation for {lang['name']}: {e}")

    return presentation_ids
```

### 4. A/B Testing Different Styles

```python
def ab_test_presentation_styles(client: AIPPTClient, topic: str):
    """Generate same content with different styles for A/B testing"""

    styles = ["professional", "creative", "minimal", "business"]
    results = {}

    for style in styles:
        request = PresentationRequest(
            topic=topic,
            page_count=8,
            style=style,
            metadata={
                "ab_test": True,
                "variant": style,
                "test_id": "style_comparison_001"
            }
        )

        try:
            presentation_id = client.generate_presentation(request)
            results[style] = {
                "presentation_id": presentation_id,
                "status": "generating"
            }
        except Exception as e:
            results[style] = {
                "error": str(e),
                "status": "failed"
            }

    return results
```

## Error Handling Examples

### 1. Comprehensive Error Handling

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class RobustAIPPTClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.ai-ppt-assistant.com/v1"

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def generate_presentation_with_error_handling(self, request: Dict):
        """Generate presentation with comprehensive error handling"""
        try:
            response = self.session.post(
                f"{self.base_url}/presentations/generate",
                headers=self.headers,
                json=request,
                timeout=30
            )

            # Handle different error types
            if response.status_code == 400:
                error_data = response.json()
                if error_data.get("error") == "VALIDATION_ERROR":
                    validation_errors = error_data.get("validation_errors", [])
                    error_msg = "Validation failed:\n"
                    for err in validation_errors:
                        error_msg += f"- {err['field']}: {err['message']}\n"
                    raise ValueError(error_msg)
                else:
                    raise ValueError(f"Bad request: {error_data.get('message')}")

            elif response.status_code == 401:
                raise PermissionError("Invalid API key or authentication failed")

            elif response.status_code == 403:
                error_data = response.json()
                if error_data.get("error") == "QUOTA_EXCEEDED":
                    quota_info = error_data.get("details", {})
                    raise Exception(f"Quota exceeded: {quota_info.get('quota_type')} - resets at {quota_info.get('reset_date')}")
                else:
                    raise PermissionError("Insufficient permissions")

            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise Exception(f"Rate limited. Please retry after {retry_after} seconds")

            elif response.status_code >= 500:
                error_data = response.json()
                incident_id = error_data.get("incident_id")
                raise Exception(f"Server error (incident: {incident_id}). Please try again or contact support")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            raise TimeoutError("Request timed out. Please try again")

        except requests.exceptions.ConnectionError:
            raise ConnectionError("Failed to connect to API. Check your network connection")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

# Usage with error handling
def safe_generate_presentation():
    client = RobustAIPPTClient("your-api-key-here")

    request = {
        "topic": "Test Presentation",
        "page_count": 5
    }

    try:
        result = client.generate_presentation_with_error_handling(request)
        print(f"Generation started: {result['presentation_id']}")
        return result["presentation_id"]

    except ValueError as e:
        print(f"Validation error: {e}")
        # Handle validation errors (fix request and retry)

    except PermissionError as e:
        print(f"Permission error: {e}")
        # Handle authentication/authorization errors

    except TimeoutError as e:
        print(f"Timeout error: {e}")
        # Handle timeout (retry with exponential backoff)

    except ConnectionError as e:
        print(f"Connection error: {e}")
        # Handle network issues

    except Exception as e:
        print(f"Unexpected error: {e}")
        # Handle other errors (logging, alerting, etc.)
```

### 2. Retry Logic with Exponential Backoff

```python
import time
import random
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1, max_delay=60):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Don't retry on client errors (4xx except 429)
                    if hasattr(e, 'response') and e.response is not None:
                        status_code = e.response.status_code
                        if 400 <= status_code < 500 and status_code != 429:
                            raise

                    if attempt == max_retries - 1:
                        raise last_exception

                    # Calculate delay with jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter

                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {total_delay:.2f} seconds...")
                    time.sleep(total_delay)

            raise last_exception
        return wrapper
    return decorator

# Usage
@retry_with_backoff(max_retries=3, base_delay=2)
def generate_with_retry(client, request):
    return client.generate_presentation(request)
```

## SDK Examples

### 1. Custom SDK Implementation

```python
class AIPPTAssistantSDK:
    """Full-featured SDK for AI PPT Assistant API"""

    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.ai-ppt-assistant.com/v1"

        # Configure session
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "AIPPTAssistant-Python-SDK/1.0.0"
        })

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def generate(self, **kwargs):
        """Generate presentation with keyword arguments"""
        return self._post("/presentations/generate", kwargs)

    def status(self, presentation_id: str):
        """Get presentation status"""
        return self._get(f"/presentations/{presentation_id}/status")

    def download(self, presentation_id: str, format: str = "pptx"):
        """Get download URL"""
        params = {"format": format} if format != "pptx" else {}
        return self._get(f"/presentations/{presentation_id}/download", params=params)

    def update_slide(self, presentation_id: str, slide_number: int, etag: str = None, **updates):
        """Update slide content"""
        headers = {}
        if etag:
            headers["If-Match"] = etag

        return self._patch(
            f"/presentations/{presentation_id}/slides/{slide_number}",
            updates,
            headers=headers
        )

    def regenerate_image(self, presentation_id: str, slide_number: int, **kwargs):
        """Regenerate slide image"""
        return self._post(f"/presentations/{presentation_id}/slides/{slide_number}/image", kwargs)

    def regenerate(self, presentation_id: str, **kwargs):
        """Regenerate presentation content"""
        return self._post(f"/presentations/{presentation_id}/regenerate", kwargs)

    def delete(self, presentation_id: str, force: bool = False):
        """Delete presentation"""
        params = {"force": force} if force else {}
        return self._delete(f"/presentations/{presentation_id}", params=params)

    def task_status(self, task_id: str):
        """Get task status"""
        return self._get(f"/tasks/{task_id}/status")

    def health(self):
        """Check API health"""
        return self._get("/health")

    # Helper methods
    def _get(self, path: str, params: dict = None):
        return self._request("GET", path, params=params)

    def _post(self, path: str, data: dict = None):
        return self._request("POST", path, json=data)

    def _patch(self, path: str, data: dict = None, headers: dict = None):
        return self._request("PATCH", path, json=data, headers=headers)

    def _delete(self, path: str, params: dict = None):
        return self._request("DELETE", path, params=params)

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"

        # Add custom headers if provided
        if "headers" in kwargs:
            headers = self.session.headers.copy()
            headers.update(kwargs["headers"])
            kwargs["headers"] = headers

        response = self.session.request(method, url, **kwargs)

        if response.status_code == 204:  # No content
            return None

        response.raise_for_status()
        return response.json()

# Usage Example
def main():
    with AIPPTAssistantSDK("your-api-key-here") as client:
        # Generate presentation
        result = client.generate(
            topic="Machine Learning Overview",
            page_count=10,
            style="professional",
            audience="technical"
        )

        presentation_id = result["presentation_id"]

        # Poll for completion
        while True:
            status = client.status(presentation_id)
            if status["status"] == "completed":
                break
            elif status["status"] == "failed":
                raise Exception("Generation failed")
            time.sleep(5)

        # Customize slide 2
        update_result = client.update_slide(
            presentation_id,
            2,
            title="Updated Title",
            content="New content here",
            layout="two_column"
        )

        # Get download URL
        download_info = client.download(presentation_id)
        print(f"Download URL: {download_info['download_url']}")

if __name__ == "__main__":
    main()
```

### 2. Async SDK Implementation

```python
import asyncio
import aiohttp
from typing import Dict, Optional

class AsyncAIPPTAssistantSDK:
    """Async SDK for high-performance applications"""

    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.ai-ppt-assistant.com/v1"
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "AIPPTAssistant-Async-SDK/1.0.0"
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=300)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    async def generate(self, **kwargs) -> Dict:
        """Generate presentation asynchronously"""
        return await self._post("/presentations/generate", kwargs)

    async def status(self, presentation_id: str) -> Dict:
        """Get presentation status"""
        return await self._get(f"/presentations/{presentation_id}/status")

    async def wait_for_completion(self, presentation_id: str, timeout: int = 300, poll_interval: int = 5) -> Dict:
        """Wait for presentation completion with async polling"""
        start_time = asyncio.get_event_loop().time()

        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                raise asyncio.TimeoutError("Presentation generation timed out")

            status = await self.status(presentation_id)

            if status["status"] == "completed":
                return status
            elif status["status"] == "failed":
                error_msg = status.get("error", {}).get("message", "Unknown error")
                raise Exception(f"Generation failed: {error_msg}")

            await asyncio.sleep(poll_interval)

    async def download(self, presentation_id: str, format: str = "pptx") -> Dict:
        """Get download URL"""
        path = f"/presentations/{presentation_id}/download"
        params = {"format": format} if format != "pptx" else None
        return await self._get(path, params=params)

    async def _get(self, path: str, params: dict = None) -> Dict:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, data: dict = None) -> Dict:
        return await self._request("POST", path, json=data)

    async def _request(self, method: str, path: str, **kwargs) -> Optional[Dict]:
        url = f"{self.base_url}{path}"

        async with self.session.request(method, url, **kwargs) as response:
            if response.status == 204:  # No content
                return None

            response.raise_for_status()
            return await response.json()

# Usage Example
async def async_main():
    async with AsyncAIPPTAssistantSDK("your-api-key-here") as client:
        # Generate multiple presentations concurrently
        tasks = [
            client.generate(topic=f"Presentation {i}", page_count=5)
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)
        presentation_ids = [r["presentation_id"] for r in results]

        # Wait for all to complete
        completion_tasks = [
            client.wait_for_completion(pid)
            for pid in presentation_ids
        ]

        completed = await asyncio.gather(*completion_tasks)

        # Get download URLs
        download_tasks = [
            client.download(pid)
            for pid in presentation_ids
        ]

        downloads = await asyncio.gather(*download_tasks)

        for i, download_info in enumerate(downloads):
            print(f"Presentation {i+1}: {download_info['download_url']}")

# Run async example
asyncio.run(async_main())
```

These examples demonstrate comprehensive usage patterns for the AI PPT Assistant API, from simple single-presentation generation to complex batch processing and error handling scenarios. The code samples provide a solid foundation for integrating the API into various types of applications.