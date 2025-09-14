# AI PPT Assistant API Reference

## Overview

The AI PPT Assistant API is a RESTful service that enables automated creation and management of PowerPoint presentations using Amazon Bedrock AI models. This API provides comprehensive functionality for presentation generation, slide-level editing, image management, and resource monitoring.

### Base URLs

| Environment | Base URL |
|------------|----------|
| Production | `https://api.ai-ppt-assistant.com/v1` |
| Staging | `https://staging-api.ai-ppt-assistant.com/v1` |
| Development | `https://dev-api.ai-ppt-assistant.com/v1` |

### Authentication

The API supports two authentication methods:

#### API Key Authentication
Include your API key in the request header:
```
X-API-Key: your-api-key-here
```

#### Bearer Token Authentication
Include your JWT token in the Authorization header:
```
Authorization: Bearer your-jwt-token-here
```

### Rate Limiting

Different endpoints have different rate limits:

| Endpoint Type | Rate Limit | Window |
|---------------|------------|---------|
| Generate Presentation | 10 requests | per minute |
| Status Checks | 60 requests | per minute |
| Slide Updates | 30 requests | per minute |
| Image Generation | 5 requests | per minute |
| Health Checks | No limit | - |

Rate limit information is returned in response headers:
- `X-RateLimit-Limit`: Maximum requests allowed in the time window
- `X-RateLimit-Remaining`: Number of requests remaining in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

### Content Types

All requests and responses use `application/json` unless otherwise specified.

### Request IDs

Every API response includes a unique `request_id` for debugging and support purposes. Include this ID when contacting support about specific requests.

## Endpoints

### 1. Generate Presentation

Creates a new AI-generated PowerPoint presentation based on the provided topic and parameters.

**Endpoint:** `POST /presentations/generate`

**Request Body:**
```json
{
  "topic": "Introduction to Machine Learning",
  "page_count": 8,
  "style": "professional",
  "language": "en",
  "audience": "technical",
  "metadata": {
    "industry": "technology",
    "complexity_level": "intermediate",
    "include_diagrams": true
  }
}
```

**Parameters:**
- `topic` (string, required): Main topic or theme of the presentation (3-200 characters)
- `page_count` (integer, optional): Number of slides to generate (3-20, default: 10)
- `style` (string, optional): Visual style (`professional`, `creative`, `minimal`, `academic`, `business`)
- `language` (string, optional): Content language (`en`, `zh`, `ja`, `ko`, `es`, `fr`, `de`, `it`, `pt`, `ru`)
- `audience` (string, optional): Target audience (`general`, `technical`, `executive`, `academic`, `children`, `sales`)
- `metadata` (object, optional): Additional customization parameters

**Response (202 Accepted):**
```json
{
  "presentation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "estimated_completion_time": 30,
  "status_url": "https://api.ai-ppt-assistant.com/v1/presentations/550e8400-e29b-41d4-a716-446655440000/status",
  "message": "Presentation generation started successfully",
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000"
}
```

**cURL Example:**
```bash
curl -X POST https://api.ai-ppt-assistant.com/v1/presentations/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "topic": "Introduction to Machine Learning",
    "page_count": 8,
    "style": "professional",
    "audience": "technical"
  }'
```

### 2. Get Presentation Status

Retrieves the current status and progress of a presentation generation task.

**Endpoint:** `GET /presentations/{presentationId}/status`

**Path Parameters:**
- `presentationId` (string, required): UUID of the presentation

**Response (200 OK):**
```json
{
  "presentation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 65,
  "current_step": "content_generation",
  "estimated_completion_time": 120,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "metadata": {
    "topic": "Introduction to Machine Learning",
    "page_count": 10,
    "version": 1
  }
}
```

**Status Values:**
- `pending`: Generation request received, waiting to start
- `processing`: AI generation in progress
- `content_generated`: Content created, starting compilation
- `compiling`: Creating PPTX file
- `completed`: Presentation ready for download
- `failed`: Generation failed (see error field)

**cURL Example:**
```bash
curl -X GET https://api.ai-ppt-assistant.com/v1/presentations/550e8400-e29b-41d4-a716-446655440000/status \
  -H "X-API-Key: your-api-key-here"
```

### 3. Download Presentation

Generates a secure, time-limited download URL for the completed presentation file.

**Endpoint:** `GET /presentations/{presentationId}/download`

**Path Parameters:**
- `presentationId` (string, required): UUID of the presentation

**Query Parameters:**
- `format` (string, optional): Download format (`pptx` - default and only supported format)

**Response (200 OK):**
```json
{
  "presentation_id": "550e8400-e29b-41d4-a716-446655440000",
  "download_url": "https://s3.amazonaws.com/ai-ppt-bucket/presentations/550e8400-e29b-41d4-a716-446655440000.pptx?X-Amz-Algorithm=...",
  "expires_in": 3600,
  "expires_at": "2024-01-15T11:40:00Z",
  "file_size": 2457600,
  "filename": "introduction-to-machine-learning.pptx",
  "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "checksum": "d41d8cd98f00b204e9800998ecf8427e"
}
```

**cURL Example:**
```bash
curl -X GET https://api.ai-ppt-assistant.com/v1/presentations/550e8400-e29b-41d4-a716-446655440000/download \
  -H "X-API-Key: your-api-key-here"
```

### 4. Update Slide Content

Updates the content of a specific slide in the presentation. Supports partial updates with optimistic concurrency control.

**Endpoint:** `PATCH /presentations/{presentationId}/slides/{slideNumber}`

**Path Parameters:**
- `presentationId` (string, required): UUID of the presentation
- `slideNumber` (integer, required): Slide number (1-based index, 1-100)

**Headers:**
- `If-Match` (string, optional): ETag for concurrency control

**Request Body:**
```json
{
  "title": "New Slide Title",
  "content": "Updated slide content with new information",
  "speaker_notes": "Additional notes for the presenter",
  "layout": "two_column",
  "style_overrides": {
    "background_color": "#F5F5F5",
    "font_family": "Calibri",
    "font_size": 14,
    "text_color": "#333333"
  }
}
```

**Parameters:**
- `title` (string, optional): Slide title (max 100 characters)
- `content` (string, optional): Main slide content (max 2000 characters)
- `speaker_notes` (string, optional): Speaker notes (max 1000 characters)
- `layout` (string, optional): Layout (`title`, `content`, `two_column`, `image_left`, `image_right`, `comparison`, `bullet_points`)
- `style_overrides` (object, optional): Style customizations

**Response (200 OK):**
```json
{
  "presentation_id": "550e8400-e29b-41d4-a716-446655440000",
  "slide_number": 5,
  "updated_at": "2024-01-15T10:45:00Z",
  "etag": "\"33a64df551425fcc55e4d42a148795d9f25f89d4\"",
  "preview_url": "https://s3.amazonaws.com/ai-ppt-bucket/presentations/550e8400-e29b-41d4-a716-446655440000/previews/slide_5.png",
  "version": 2
}
```

**cURL Example:**
```bash
curl -X PATCH https://api.ai-ppt-assistant.com/v1/presentations/550e8400-e29b-41d4-a716-446655440000/slides/5 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -H "If-Match: \"33a64df551425fcc55e4d42a148795d9f25f89d4\"" \
  -d '{
    "title": "Updated Title",
    "content": "New content for this slide"
  }'
```

### 5. Regenerate Slide Image

Regenerates the image for a specific slide using AI image generation with custom prompts and styling options.

**Endpoint:** `POST /presentations/{presentationId}/slides/{slideNumber}/image`

**Path Parameters:**
- `presentationId` (string, required): UUID of the presentation
- `slideNumber` (integer, required): Slide number (1-based index)

**Request Body:**
```json
{
  "prompt": "A modern office workspace with computers and natural lighting",
  "style": "realistic",
  "dimensions": {
    "width": 1024,
    "height": 768
  },
  "seed": 12345,
  "quality": "high"
}
```

**Parameters:**
- `prompt` (string, optional): Custom image generation prompt (max 500 characters)
- `style` (string, optional): Image style (`realistic`, `cartoon`, `abstract`, `diagram`, `infographic`, `photo`, `illustration`)
- `dimensions` (object, optional): Image dimensions in pixels
  - `width` (integer): Width (256-2048, default: 1024)
  - `height` (integer): Height (256-2048, default: 768)
- `seed` (integer, optional): Seed for reproducible generation (0-2147483647)
- `quality` (string, optional): Generation quality (`standard`, `high`, `premium`)

**Response (202 Accepted):**
```json
{
  "task_id": "task_123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "estimated_time": 15,
  "status_url": "https://api.ai-ppt-assistant.com/v1/tasks/task_123e4567-e89b-12d3-a456-426614174000/status",
  "message": "Image regeneration started successfully"
}
```

**cURL Example:**
```bash
curl -X POST https://api.ai-ppt-assistant.com/v1/presentations/550e8400-e29b-41d4-a716-446655440000/slides/3/image \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "prompt": "Professional diagram showing data flow",
    "style": "diagram",
    "quality": "high"
  }'
```

### 6. Regenerate Presentation

Regenerates specific parts or the entire presentation with new content while optionally preserving existing styling.

**Endpoint:** `POST /presentations/{presentationId}/regenerate`

**Path Parameters:**
- `presentationId` (string, required): UUID of the presentation

**Request Body:**
```json
{
  "scope": "slides",
  "slide_numbers": [2, 4, 6, 8],
  "options": {
    "preserve_style": true,
    "preserve_images": false,
    "new_prompt": "Focus more on practical implementation examples",
    "language": "en"
  }
}
```

**Parameters:**
- `scope` (string, required): What to regenerate (`all`, `slides`, `images`, `content`)
- `slide_numbers` (array, optional): Specific slides to regenerate (required if scope is 'slides')
- `options` (object, optional): Regeneration options
  - `preserve_style` (boolean): Keep existing visual styling (default: true)
  - `preserve_images` (boolean): Keep existing images (default: false)
  - `new_prompt` (string): New prompt to guide regeneration (max 500 characters)
  - `language` (string): Change content language

**Response (202 Accepted):**
```json
{
  "task_id": "task_456e7890-e12b-34d5-a678-901234567890",
  "scope": "slides",
  "affected_slides": [2, 4, 6, 8],
  "status": "pending",
  "estimated_time": 60,
  "status_url": "https://api.ai-ppt-assistant.com/v1/tasks/task_456e7890-e12b-34d5-a678-901234567890/status"
}
```

**cURL Example:**
```bash
curl -X POST https://api.ai-ppt-assistant.com/v1/presentations/550e8400-e29b-41d4-a716-446655440000/regenerate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "scope": "slides",
    "slide_numbers": [2, 4, 6],
    "options": {
      "preserve_style": true,
      "new_prompt": "Add more technical details"
    }
  }'
```

### 7. Delete Presentation

Permanently deletes a presentation and all associated resources. This action cannot be undone.

**Endpoint:** `DELETE /presentations/{presentationId}`

**Path Parameters:**
- `presentationId` (string, required): UUID of the presentation

**Query Parameters:**
- `force` (boolean, optional): Force deletion even if presentation is being processed (default: false)

**Response (204 No Content):**
```
HTTP/1.1 204 No Content
X-Cleanup-Task-Id: cleanup_789e0123-f45g-67h8-i901-234567890abc
```

**cURL Example:**
```bash
curl -X DELETE https://api.ai-ppt-assistant.com/v1/presentations/550e8400-e29b-41d4-a716-446655440000?force=true \
  -H "X-API-Key: your-api-key-here"
```

### 8. Get Task Status

Retrieves the status of an asynchronous task (image generation, regeneration, etc.).

**Endpoint:** `GET /tasks/{taskId}/status`

**Path Parameters:**
- `taskId` (string, required): UUID of the task

**Response (200 OK):**
```json
{
  "task_id": "task_123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:30:45Z",
  "result": {
    "image_url": "https://s3.amazonaws.com/ai-ppt-bucket/images/generated_image_123.png",
    "dimensions": {
      "width": 1024,
      "height": 768
    }
  }
}
```

**cURL Example:**
```bash
curl -X GET https://api.ai-ppt-assistant.com/v1/tasks/task_123e4567-e89b-12d3-a456-426614174000/status \
  -H "X-API-Key: your-api-key-here"
```

### 9. Health Check

Returns the health status of the API and its dependencies.

**Endpoint:** `GET /health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "uptime": 86400,
  "services": {
    "bedrock": {
      "status": "healthy",
      "latency": 15.7,
      "last_check": "2024-01-15T10:30:00Z"
    },
    "s3": {
      "status": "healthy",
      "latency": 8.2,
      "last_check": "2024-01-15T10:30:00Z"
    },
    "dynamodb": {
      "status": "healthy",
      "latency": 12.1,
      "last_check": "2024-01-15T10:30:00Z"
    },
    "lambda": {
      "status": "healthy",
      "latency": 25.3,
      "last_check": "2024-01-15T10:30:00Z"
    }
  },
  "metrics": {
    "requests_per_minute": 15.2,
    "average_generation_time": 45.7,
    "success_rate": 0.987
  }
}
```

**cURL Example:**
```bash
curl -X GET https://api.ai-ppt-assistant.com/v1/health
```

## Error Handling

### Error Response Format

All errors follow RFC 7807 Problem Details format:

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Request validation failed",
  "validation_errors": [
    {
      "field": "page_count",
      "message": "Must be between 3 and 20",
      "value": 25,
      "constraint": "max:20"
    }
  ],
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### HTTP Status Codes

| Status Code | Description | When It Occurs |
|-------------|-------------|----------------|
| 200 | OK | Request successful |
| 202 | Accepted | Asynchronous operation started |
| 204 | No Content | Resource deleted successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict (wrong state, locked) |
| 412 | Precondition Failed | ETag mismatch |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error occurred |
| 503 | Service Unavailable | Service temporarily unavailable |

### Common Error Codes

| Error Code | Description | Resolution |
|------------|-------------|------------|
| `VALIDATION_ERROR` | Request validation failed | Check request parameters and format |
| `UNAUTHORIZED` | Authentication failed | Verify API key or JWT token |
| `NOT_FOUND` | Resource not found | Check resource ID and availability |
| `CONFLICT` | Resource in wrong state | Wait for resource to reach correct state |
| `PRECONDITION_FAILED` | ETag mismatch | Refresh resource and retry |
| `RATE_LIMITED` | Rate limit exceeded | Wait and retry after the specified time |
| `INTERNAL_ERROR` | Server error | Retry request; contact support if persistent |

## SDKs and Code Examples

### Python Example

```python
import requests
import json
import time

class AIPPTAssistant:
    def __init__(self, api_key, base_url="https://api.ai-ppt-assistant.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def generate_presentation(self, topic, page_count=10, style="professional"):
        """Generate a new presentation"""
        url = f"{self.base_url}/presentations/generate"
        payload = {
            "topic": topic,
            "page_count": page_count,
            "style": style
        }

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def get_status(self, presentation_id):
        """Get presentation status"""
        url = f"{self.base_url}/presentations/{presentation_id}/status"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def wait_for_completion(self, presentation_id, timeout=300):
        """Wait for presentation to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_status(presentation_id)

            if status['status'] == 'completed':
                return status
            elif status['status'] == 'failed':
                raise Exception(f"Generation failed: {status.get('error', {}).get('message')}")

            time.sleep(5)

        raise TimeoutError("Presentation generation timed out")

    def download_presentation(self, presentation_id):
        """Get download URL"""
        url = f"{self.base_url}/presentations/{presentation_id}/download"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

# Usage example
client = AIPPTAssistant("your-api-key-here")

# Generate presentation
result = client.generate_presentation(
    topic="Introduction to Machine Learning",
    page_count=8,
    style="professional"
)
presentation_id = result['presentation_id']

# Wait for completion
status = client.wait_for_completion(presentation_id)
print(f"Presentation completed: {status}")

# Get download URL
download_info = client.download_presentation(presentation_id)
print(f"Download URL: {download_info['download_url']}")
```

### JavaScript Example

```javascript
class AIPPTAssistant {
    constructor(apiKey, baseUrl = 'https://api.ai-ppt-assistant.com/v1') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'X-API-Key': apiKey,
            'Content-Type': 'application/json'
        };
    }

    async generatePresentation(topic, pageCount = 10, style = 'professional') {
        const response = await fetch(`${this.baseUrl}/presentations/generate`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                topic,
                page_count: pageCount,
                style
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    async getStatus(presentationId) {
        const response = await fetch(`${this.baseUrl}/presentations/${presentationId}/status`, {
            headers: this.headers
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    async waitForCompletion(presentationId, timeout = 300000) {
        const startTime = Date.now();

        while (Date.now() - startTime < timeout) {
            const status = await this.getStatus(presentationId);

            if (status.status === 'completed') {
                return status;
            } else if (status.status === 'failed') {
                throw new Error(`Generation failed: ${status.error?.message}`);
            }

            await new Promise(resolve => setTimeout(resolve, 5000));
        }

        throw new Error('Presentation generation timed out');
    }

    async downloadPresentation(presentationId) {
        const response = await fetch(`${this.baseUrl}/presentations/${presentationId}/download`, {
            headers: this.headers
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }
}

// Usage example
const client = new AIPPTAssistant('your-api-key-here');

async function createPresentation() {
    try {
        // Generate presentation
        const result = await client.generatePresentation(
            'Introduction to Machine Learning',
            8,
            'professional'
        );

        console.log('Generation started:', result.presentation_id);

        // Wait for completion
        const status = await client.waitForCompletion(result.presentation_id);
        console.log('Presentation completed:', status);

        // Get download URL
        const downloadInfo = await client.downloadPresentation(result.presentation_id);
        console.log('Download URL:', downloadInfo.download_url);

    } catch (error) {
        console.error('Error:', error);
    }
}

createPresentation();
```

## Best Practices

### 1. Error Handling
- Always check response status codes
- Implement retry logic with exponential backoff for transient errors
- Store request IDs for debugging purposes
- Handle rate limiting gracefully

### 2. Asynchronous Operations
- Use polling with appropriate intervals (5-10 seconds)
- Implement timeouts for long-running operations
- Consider webhooks for production applications

### 3. Security
- Never expose API keys in client-side code
- Use environment variables for API keys
- Implement proper authentication and authorization
- Validate all user inputs before sending to API

### 4. Performance
- Cache status responses when appropriate
- Use appropriate request timeouts
- Implement connection pooling for high-throughput applications
- Monitor rate limits and adjust request patterns

### 5. Resource Management
- Clean up unused presentations to save storage costs
- Use appropriate expiration times for download URLs
- Monitor resource usage and set up alerts

### 6. Monitoring
- Log all API interactions for debugging
- Monitor error rates and response times
- Set up alerting for critical failures
- Track usage patterns and optimize accordingly

## Support

For technical support, please contact:
- Email: support@ai-ppt-assistant.com
- Documentation: https://docs.ai-ppt-assistant.com
- Status Page: https://status.ai-ppt-assistant.com

Include the following information in support requests:
- Request ID from error response
- Timestamp of the request
- Complete error response
- Steps to reproduce the issue