# AI PPT Assistant API Documentation

## 📚 API Overview

The AI PPT Assistant provides a RESTful API for generating professional presentations using Amazon Bedrock's AI capabilities. This document describes all available endpoints, request/response formats, and error handling.

**Base URL**: `https://api.ai-ppt-assistant.example.com/v1`  
**Authentication**: API Key via `x-api-key` header  
**Content Type**: `application/json`

## 🔐 Authentication

All API requests require authentication using an API key:

```http
x-api-key: your-api-key-here
```

Example:
```bash
curl -H "x-api-key: your-api-key-here" \
     -H "Content-Type: application/json" \
     https://api.ai-ppt-assistant.example.com/v1/presentations
```

## 📍 Endpoints

### 1. Generate Presentation

Create a new presentation based on the provided topic and parameters.

#### Request

```http
POST /presentations
```

#### Headers
```http
Content-Type: application/json
x-api-key: your-api-key
```

#### Request Body

```json
{
  "topic": "string",              // Required: Main topic of the presentation
  "target_audience": "string",    // Optional: Target audience description
  "duration": "number",            // Optional: Presentation duration in minutes (default: 30)
  "slide_count": "number",         // Optional: Number of slides (default: 10, max: 30)
  "style": "string",              // Optional: "professional", "creative", "technical", "educational"
  "language": "string",           // Optional: ISO 639-1 language code (default: "en")
  "include_images": "boolean",    // Optional: Generate AI images for slides (default: true)
  "include_speaker_notes": "boolean", // Optional: Generate speaker notes (default: true)
  "template": "string",           // Optional: Template name (default: "professional")
  "custom_instructions": "string" // Optional: Additional instructions for AI
}
```

#### Response

**Success Response (202 Accepted)**
```json
{
  "success": true,
  "presentation_id": "uuid-string",
  "status": "processing",
  "message": "Presentation generation started",
  "estimated_time_seconds": 45,
  "links": {
    "status": "/presentations/uuid-string/status",
    "download": "/presentations/uuid-string/download"
  }
}
```

#### Example

```bash
curl -X POST https://api.ai-ppt-assistant.example.com/v1/presentations \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "topic": "Introduction to Artificial Intelligence",
    "target_audience": "Business executives with non-technical background",
    "duration": 30,
    "slide_count": 12,
    "style": "professional",
    "language": "en",
    "include_images": true,
    "include_speaker_notes": true
  }'
```

### 2. Get Presentation Status

Check the current status of a presentation generation request.

#### Request

```http
GET /presentations/{presentation_id}/status
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| presentation_id | string (UUID) | Yes | Unique presentation identifier |

#### Response

**Success Response (200 OK)**
```json
{
  "success": true,
  "presentation_id": "uuid-string",
  "status": "completed|processing|failed",
  "progress": 85,                    // Percentage (0-100)
  "current_step": "generating_images",
  "steps_completed": [
    "outline_creation",
    "content_generation"
  ],
  "steps_remaining": [
    "image_generation",
    "compilation"
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:05:00Z",
  "metadata": {
    "slide_count": 12,
    "has_images": true,
    "has_speaker_notes": true
  },
  "error": null                      // Error message if status is "failed"
}
```

#### Status Values

| Status | Description |
|--------|-------------|
| `pending` | Request received, waiting to start |
| `outlining` | Creating presentation outline |
| `content_generation` | Generating slide content |
| `image_generation` | Creating AI images |
| `compiling` | Assembling final presentation |
| `completed` | Presentation ready for download |
| `failed` | Generation failed (see error field) |

#### Example

```bash
curl -X GET https://api.ai-ppt-assistant.example.com/v1/presentations/123e4567-e89b-12d3-a456-426614174000/status \
  -H "x-api-key: your-api-key"
```

### 3. Download Presentation

Download the generated presentation in various formats.

#### Request

```http
GET /presentations/{presentation_id}/download
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| presentation_id | string (UUID) | Yes | Unique presentation identifier |
| format | string | No | Output format: "pptx", "pdf", "html", "png" (default: "pptx") |
| include_notes | boolean | No | Include speaker notes in download (default: true) |

#### Response

**Success Response (200 OK)**
```json
{
  "success": true,
  "presentation_id": "uuid-string",
  "download_url": "https://s3-presigned-url...",
  "expires_in": 3600,               // URL expiry in seconds
  "file_size": 2456789,             // File size in bytes
  "format": "pptx",
  "filename": "AI_Introduction_2024.pptx"
}
```

**Error Response (400 Bad Request)**
```json
{
  "success": false,
  "error": "Presentation not ready for download",
  "status": "processing",
  "progress": 60
}
```

#### Example

```bash
# Download as PPTX
curl -X GET "https://api.ai-ppt-assistant.example.com/v1/presentations/123e4567-e89b-12d3-a456-426614174000/download?format=pptx" \
  -H "x-api-key: your-api-key"

# Download as PDF
curl -X GET "https://api.ai-ppt-assistant.example.com/v1/presentations/123e4567-e89b-12d3-a456-426614174000/download?format=pdf" \
  -H "x-api-key: your-api-key"
```

### 4. Modify Slide

Modify specific slides in an existing presentation.

#### Request

```http
PATCH /presentations/{presentation_id}/slides/{slide_id}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| presentation_id | string (UUID) | Yes | Unique presentation identifier |
| slide_id | string | Yes | Slide identifier (e.g., "slide-1", "slide-2") |

#### Request Body

```json
{
  "modification_type": "content|visual|speaker_notes|layout",
  "new_content": "string",          // For content modifications
  "new_title": "string",            // For title updates
  "bullet_points": ["string"],      // For bullet point updates
  "image_prompt": "string",         // For visual modifications
  "speaker_notes": "string",        // For speaker notes updates
  "layout": "string"                // Layout type: "title", "content", "two_column", "image_left", "image_right"
}
```

#### Response

**Success Response (202 Accepted)**
```json
{
  "success": true,
  "presentation_id": "uuid-string",
  "slide_id": "slide-3",
  "modification_id": "mod-uuid",
  "status": "processing",
  "message": "Slide modification initiated"
}
```

#### Example

```bash
curl -X PATCH https://api.ai-ppt-assistant.example.com/v1/presentations/123e4567/slides/slide-3 \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "modification_type": "content",
    "new_content": "Updated content with latest statistics",
    "bullet_points": [
      "AI market grew 40% in 2024",
      "85% of enterprises use AI",
      "ROI increased by 3x"
    ]
  }'
```

### 5. List Presentations

Get a list of all presentations for the authenticated user.

#### Request

```http
GET /presentations
```

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | number | No | Number of results (default: 10, max: 100) |
| offset | number | No | Pagination offset (default: 0) |
| status | string | No | Filter by status |
| sort_by | string | No | Sort field: "created_at", "updated_at", "title" |
| order | string | No | Sort order: "asc", "desc" (default: "desc") |

#### Response

**Success Response (200 OK)**
```json
{
  "success": true,
  "total": 42,
  "limit": 10,
  "offset": 0,
  "presentations": [
    {
      "presentation_id": "uuid-string",
      "title": "Introduction to AI",
      "status": "completed",
      "slide_count": 12,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:05:00Z",
      "file_size": 2456789,
      "downloads": 5
    }
  ],
  "links": {
    "next": "/presentations?limit=10&offset=10",
    "prev": null
  }
}
```

#### Example

```bash
curl -X GET "https://api.ai-ppt-assistant.example.com/v1/presentations?limit=5&status=completed" \
  -H "x-api-key: your-api-key"
```

### 6. Delete Presentation

Delete a presentation and all associated resources.

#### Request

```http
DELETE /presentations/{presentation_id}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| presentation_id | string (UUID) | Yes | Unique presentation identifier |

#### Response

**Success Response (200 OK)**
```json
{
  "success": true,
  "message": "Presentation deleted successfully",
  "presentation_id": "uuid-string"
}
```

#### Example

```bash
curl -X DELETE https://api.ai-ppt-assistant.example.com/v1/presentations/123e4567 \
  -H "x-api-key: your-api-key"
```

## 🔄 Webhooks

Configure webhooks to receive real-time updates about presentation generation.

### Webhook Configuration

```http
POST /webhooks
```

```json
{
  "url": "https://your-domain.com/webhook",
  "events": ["presentation.completed", "presentation.failed"],
  "secret": "your-webhook-secret"
}
```

### Webhook Events

| Event | Description |
|-------|-------------|
| `presentation.started` | Generation started |
| `presentation.progress` | Progress update |
| `presentation.completed` | Generation completed |
| `presentation.failed` | Generation failed |
| `slide.modified` | Slide modification completed |

### Webhook Payload

```json
{
  "event": "presentation.completed",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "presentation_id": "uuid-string",
    "status": "completed",
    "download_url": "https://...",
    "metadata": {
      "slide_count": 12,
      "processing_time_seconds": 45
    }
  },
  "signature": "sha256=..."
}
```

## ❌ Error Responses

### Error Response Format

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "Additional error details"
  },
  "request_id": "req-uuid",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 OK | Request successful |
| 202 Accepted | Request accepted for processing |
| 400 Bad Request | Invalid request parameters |
| 401 Unauthorized | Missing or invalid API key |
| 403 Forbidden | Access denied |
| 404 Not Found | Resource not found |
| 409 Conflict | Resource conflict (e.g., duplicate request) |
| 422 Unprocessable Entity | Valid request but unable to process |
| 429 Too Many Requests | Rate limit exceeded |
| 500 Internal Server Error | Server error |
| 503 Service Unavailable | Service temporarily unavailable |

### Error Codes

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `INVALID_API_KEY` | API key is invalid or expired | 401 |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 |
| `INVALID_TOPIC` | Topic is missing or invalid | 400 |
| `INVALID_SLIDE_COUNT` | Slide count exceeds limits | 400 |
| `PRESENTATION_NOT_FOUND` | Presentation ID not found | 404 |
| `PRESENTATION_NOT_READY` | Presentation still processing | 400 |
| `GENERATION_FAILED` | AI generation failed | 500 |
| `BEDROCK_ERROR` | Bedrock service error | 503 |
| `S3_ERROR` | Storage service error | 500 |
| `QUOTA_EXCEEDED` | Account quota exceeded | 403 |

### Error Examples

**Invalid Request**
```json
{
  "success": false,
  "error": "Invalid slide count",
  "error_code": "INVALID_SLIDE_COUNT",
  "details": {
    "slide_count": 50,
    "max_allowed": 30
  },
  "request_id": "req-123",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Rate Limiting**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "limit": 100,
    "remaining": 0,
    "reset_at": "2024-01-01T01:00:00Z"
  },
  "request_id": "req-456",
  "timestamp": "2024-01-01T00:30:00Z"
}
```

## 🎯 Rate Limiting

API requests are rate limited to ensure fair usage:

| Tier | Requests/Hour | Burst | Concurrent Generations |
|------|---------------|-------|------------------------|
| Free | 10 | 5 | 1 |
| Basic | 100 | 20 | 3 |
| Pro | 1000 | 100 | 10 |
| Enterprise | Custom | Custom | Custom |

Rate limit information is included in response headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067200
```

## 🔄 Pagination

List endpoints support pagination using `limit` and `offset` parameters:

```bash
# First page
GET /presentations?limit=10&offset=0

# Second page
GET /presentations?limit=10&offset=10
```

Paginated responses include navigation links:
```json
{
  "links": {
    "first": "/presentations?limit=10&offset=0",
    "prev": "/presentations?limit=10&offset=0",
    "next": "/presentations?limit=10&offset=20",
    "last": "/presentations?limit=10&offset=40"
  }
}
```

## 🌍 Localization

The API supports multiple languages for presentation generation:

### Supported Languages

| Code | Language | Support Level |
|------|----------|---------------|
| en | English | Full |
| es | Spanish | Full |
| fr | French | Full |
| de | German | Full |
| it | Italian | Full |
| pt | Portuguese | Full |
| zh | Chinese (Simplified) | Full |
| ja | Japanese | Full |
| ko | Korean | Full |
| ru | Russian | Limited |
| ar | Arabic | Limited |

### Language Headers

You can specify preferred language using the `Accept-Language` header:
```http
Accept-Language: es-ES
```

## 📚 Code Examples

### Python

```python
import requests
import time

API_KEY = "your-api-key"
BASE_URL = "https://api.ai-ppt-assistant.example.com/v1"

# Generate presentation
def generate_presentation(topic, **kwargs):
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "topic": topic,
        **kwargs
    }
    
    response = requests.post(
        f"{BASE_URL}/presentations",
        json=payload,
        headers=headers
    )
    
    if response.status_code == 202:
        return response.json()["presentation_id"]
    else:
        raise Exception(f"Error: {response.json()}")

# Check status
def check_status(presentation_id):
    headers = {"x-api-key": API_KEY}
    
    response = requests.get(
        f"{BASE_URL}/presentations/{presentation_id}/status",
        headers=headers
    )
    
    return response.json()

# Download presentation
def download_presentation(presentation_id, format="pptx"):
    headers = {"x-api-key": API_KEY}
    
    response = requests.get(
        f"{BASE_URL}/presentations/{presentation_id}/download",
        params={"format": format},
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        return data["download_url"]
    else:
        raise Exception(f"Error: {response.json()}")

# Example usage
if __name__ == "__main__":
    # Generate presentation
    pres_id = generate_presentation(
        topic="Introduction to Python Programming",
        target_audience="Beginners",
        slide_count=15,
        style="educational"
    )
    
    print(f"Presentation ID: {pres_id}")
    
    # Wait for completion
    while True:
        status = check_status(pres_id)
        print(f"Status: {status['status']} ({status['progress']}%)")
        
        if status["status"] == "completed":
            break
        elif status["status"] == "failed":
            raise Exception(f"Generation failed: {status['error']}")
        
        time.sleep(5)
    
    # Download
    download_url = download_presentation(pres_id)
    print(f"Download URL: {download_url}")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

const API_KEY = 'your-api-key';
const BASE_URL = 'https://api.ai-ppt-assistant.example.com/v1';

// Generate presentation
async function generatePresentation(topic, options = {}) {
  try {
    const response = await axios.post(
      `${BASE_URL}/presentations`,
      {
        topic,
        ...options
      },
      {
        headers: {
          'x-api-key': API_KEY,
          'Content-Type': 'application/json'
        }
      }
    );
    
    return response.data.presentation_id;
  } catch (error) {
    throw new Error(`Generation failed: ${error.response.data.error}`);
  }
}

// Check status
async function checkStatus(presentationId) {
  const response = await axios.get(
    `${BASE_URL}/presentations/${presentationId}/status`,
    {
      headers: { 'x-api-key': API_KEY }
    }
  );
  
  return response.data;
}

// Wait for completion
async function waitForCompletion(presentationId, checkInterval = 5000) {
  while (true) {
    const status = await checkStatus(presentationId);
    console.log(`Status: ${status.status} (${status.progress}%)`);
    
    if (status.status === 'completed') {
      return status;
    } else if (status.status === 'failed') {
      throw new Error(`Generation failed: ${status.error}`);
    }
    
    await new Promise(resolve => setTimeout(resolve, checkInterval));
  }
}

// Example usage
(async () => {
  try {
    // Generate presentation
    const presentationId = await generatePresentation(
      'Modern Web Development',
      {
        target_audience: 'Developers',
        slide_count: 20,
        style: 'technical'
      }
    );
    
    console.log(`Presentation ID: ${presentationId}`);
    
    // Wait for completion
    await waitForCompletion(presentationId);
    
    console.log('Presentation ready!');
  } catch (error) {
    console.error('Error:', error.message);
  }
})();
```

### cURL

```bash
#!/bin/bash

API_KEY="your-api-key"
BASE_URL="https://api.ai-ppt-assistant.example.com/v1"

# Generate presentation
response=$(curl -s -X POST "$BASE_URL/presentations" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Cloud Computing Fundamentals",
    "target_audience": "IT Professionals",
    "slide_count": 15,
    "style": "professional"
  }')

presentation_id=$(echo $response | jq -r '.presentation_id')
echo "Presentation ID: $presentation_id"

# Check status in a loop
while true; do
  status_response=$(curl -s -X GET "$BASE_URL/presentations/$presentation_id/status" \
    -H "x-api-key: $API_KEY")
  
  status=$(echo $status_response | jq -r '.status')
  progress=$(echo $status_response | jq -r '.progress')
  
  echo "Status: $status ($progress%)"
  
  if [ "$status" = "completed" ]; then
    echo "Presentation ready!"
    break
  elif [ "$status" = "failed" ]; then
    echo "Generation failed!"
    exit 1
  fi
  
  sleep 5
done

# Get download URL
download_response=$(curl -s -X GET "$BASE_URL/presentations/$presentation_id/download" \
  -H "x-api-key: $API_KEY")

download_url=$(echo $download_response | jq -r '.download_url')
echo "Download URL: $download_url"

# Download file
curl -o presentation.pptx "$download_url"
```

## 🔒 Security Best Practices

1. **API Key Security**
   - Never expose API keys in client-side code
   - Rotate keys regularly
   - Use environment variables for storage

2. **HTTPS Only**
   - All API communication must use HTTPS
   - SSL/TLS certificate validation required

3. **Input Validation**
   - Sanitize all user inputs
   - Implement request size limits
   - Validate file formats

4. **Rate Limiting**
   - Implement client-side rate limiting
   - Handle 429 responses gracefully
   - Use exponential backoff for retries

## 📞 Support

For API support:
- Email: api-support@ai-ppt-assistant.com
- Documentation: https://docs.ai-ppt-assistant.com
- Status Page: https://status.ai-ppt-assistant.com
- GitHub Issues: https://github.com/your-org/ai-ppt-assistant/issues

## 🔄 Changelog

### Version 1.1.0 (2024-01-15)
- Added slide modification endpoint
- Improved error messages
- Added webhook support

### Version 1.0.0 (2024-01-01)
- Initial API release
- Basic presentation generation
- Status tracking
- File download support