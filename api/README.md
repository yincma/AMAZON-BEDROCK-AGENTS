# AI PPT Assistant API

RESTful API for AI-powered presentation generation using Amazon Bedrock Agents.

## Overview

This API provides endpoints for creating, managing, and downloading AI-generated presentations. It integrates with four specialized Bedrock Agents (Orchestrator, Content, Visual, and Compiler) to create professional presentations from simple text prompts.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│  API Gateway │────▶│   Lambda    │
└─────────────┘     └──────────────┘     └─────────────┘
                                                │
                            ┌───────────────────┼───────────────────┐
                            │                   │                   │
                      ┌─────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐
                      │  DynamoDB │      │    SQS    │      │    S3     │
                      └───────────┘      └─────┬─────┘      └───────────┘
                                               │
                                         ┌─────▼─────┐
                                         │ Processor │
                                         │  Lambda   │
                                         └─────┬─────┘
                                               │
                    ┌──────────────────────────┼──────────────────────┐
                    │                          │                      │
              ┌─────▼─────┐            ┌──────▼──────┐        ┌──────▼──────┐
              │  Bedrock  │            │   Bedrock   │        │   Bedrock   │
              │   Agents  │            │    Agents   │        │   Agents    │
              └───────────┘            └─────────────┘        └─────────────┘
```

## Features

### Core Features
- **Async Presentation Generation**: Create presentations asynchronously with progress tracking
- **Multi-Format Export**: Support for PPTX, PDF, HTML, and image formats
- **Template Support**: Pre-defined templates for different presentation styles
- **Multi-Language**: Support for 8 languages (EN, JA, ZH, ES, FR, DE, PT, KO)
- **Customization**: Extensive customization options for style, tone, and audience

### API Features
- **RESTful Design**: Standard REST API with OpenAPI 3.0 specification
- **Authentication**: Support for API Key, JWT, and OAuth2
- **Rate Limiting**: Built-in rate limiting per user/API key
- **Async Processing**: Task-based async processing with status polling
- **Health Checks**: Comprehensive health and readiness endpoints
- **CORS Support**: Full CORS support for browser-based clients
- **Caching**: Intelligent caching for improved performance
- **Monitoring**: CloudWatch metrics and X-Ray tracing

## Quick Start

### Prerequisites
- AWS Account with appropriate permissions
- Bedrock Agents deployed (see agents/ directory)
- AWS CLI configured
- Python 3.13+ (for local development)

### Deployment

1. **Deploy with Terraform:**
```bash
cd ../infrastructure
terraform init
terraform plan -var-file="config/environments/dev.tfvars"
terraform apply -var-file="config/environments/dev.tfvars" \
  -var="orchestrator_agent_id=<AGENT_ID>" \
  -var="orchestrator_alias_id=<ALIAS_ID>" \
  -var="content_agent_id=<AGENT_ID>" \
  -var="content_alias_id=<ALIAS_ID>" \
  -var="visual_agent_id=<AGENT_ID>" \
  -var="visual_alias_id=<ALIAS_ID>" \
  -var="compiler_agent_id=<AGENT_ID>" \
  -var="compiler_alias_id=<ALIAS_ID>"
```

2. **Get the API endpoint:**
```bash
terraform output api_endpoint
```

## API Endpoints

### Presentations

#### Create Presentation
```http
POST /presentations
Content-Type: application/json
X-API-Key: <your-api-key>

{
  "title": "Q4 2024 Business Review",
  "topic": "Quarterly business performance and strategic outlook",
  "language": "en",
  "slide_count": 15,
  "style": "corporate",
  "template": "executive_summary"
}
```

Response:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "estimated_completion": "2024-01-15T10:33:00Z",
  "_links": {
    "self": "/tasks/123e4567-e89b-12d3-a456-426614174000",
    "result": "/presentations/456e7890-e89b-12d3-a456-426614174000"
  }
}
```

#### List Presentations
```http
GET /presentations?page_size=20&sort_by=created_at&sort_order=desc
X-API-Key: <your-api-key>
```

#### Get Presentation
```http
GET /presentations/{presentationId}
X-API-Key: <your-api-key>
```

#### Download Presentation
```http
GET /presentations/{presentationId}/download?format=pptx
X-API-Key: <your-api-key>
```

### Tasks

#### Get Task Status
```http
GET /tasks/{taskId}
X-API-Key: <your-api-key>
```

Response:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100,
  "message": "Presentation created successfully",
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:32:45Z",
  "result": {
    "presentation_id": "456e7890-e89b-12d3-a456-426614174000",
    "download_url": "/presentations/456e7890-e89b-12d3-a456-426614174000/download"
  }
}
```

### Templates

#### List Templates
```http
GET /templates?category=business
```

### Health Checks

#### Health Check
```http
GET /health
```

#### Readiness Check
```http
GET /health/ready
```

## Authentication

### API Key
Include your API key in the request header:
```http
X-API-Key: your-api-key-here
```

### JWT Bearer Token
Include JWT token in Authorization header:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### OAuth2
Use OAuth2 flow for user authentication:
```
Authorization URL: https://auth.example.com/oauth/authorize
Token URL: https://auth.example.com/oauth/token
Scopes: read, write, admin
```

## Rate Limiting

Default rate limits:
- **Standard**: 60 requests/minute, burst of 100
- **POST /presentations**: 10 requests/minute, burst of 15
- **Per User**: Limits apply per authenticated user

Rate limit headers:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642248000
```

## Error Handling

Standard error response format:
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Title and topic are required",
    "details": {
      "missing_fields": ["title", "topic"]
    },
    "request_id": "req-123456",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

Error codes:
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error
- `503` - Service Unavailable

## Async Processing

1. **Submit request**: POST to create endpoint returns task ID
2. **Poll status**: GET task status endpoint to check progress
3. **Download result**: Once completed, download the presentation

Recommended polling strategy:
- First 10 seconds: Poll every 2 seconds
- 10-30 seconds: Poll every 5 seconds
- After 30 seconds: Poll every 10 seconds

## Development

### Local Testing

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run tests:**
```bash
pytest tests/
```

3. **Local server:**
```bash
sam local start-api
```

### API Documentation

View the full OpenAPI specification:
```bash
open openapi.yaml
```

Generate API documentation:
```bash
npx @redocly/openapi-cli preview-docs openapi.yaml
```

## Monitoring

### CloudWatch Metrics
- `PresentationCreated`: Number of presentations created
- `PresentationDownloaded`: Number of downloads
- `TaskCompleted`: Successfully completed tasks
- `TaskFailed`: Failed tasks

### CloudWatch Alarms
- API 4xx errors > 10 in 5 minutes
- Lambda errors > 5 in 5 minutes
- SQS DLQ messages > 0
- DynamoDB throttling > 0

### X-Ray Tracing
Enabled for all API calls and Lambda functions. View traces in AWS X-Ray console.

## Best Practices

### Request Optimization
- Batch operations when possible
- Use appropriate page sizes for list operations
- Cache responses client-side when appropriate
- Compress large request payloads

### Error Handling
- Implement exponential backoff for retries
- Handle rate limiting gracefully
- Log errors for debugging
- Provide meaningful error messages to users

### Security
- Rotate API keys regularly
- Use HTTPS for all requests
- Implement proper CORS policies
- Validate and sanitize all inputs
- Use least privilege IAM roles

## Troubleshooting

### Common Issues

1. **Task stuck in processing:**
   - Check SQS DLQ for failed messages
   - Review Lambda logs for errors
   - Verify Bedrock Agent availability

2. **Authentication failures:**
   - Verify API key is valid
   - Check token expiration
   - Ensure proper headers are sent

3. **Download failures:**
   - Check S3 bucket permissions
   - Verify presentation is completed
   - Check CloudFront distribution status

4. **Rate limiting:**
   - Implement exponential backoff
   - Consider upgrading rate limits
   - Distribute requests over time

## Support

For issues and questions:
- GitHub Issues: [project-repo/issues]
- Email: support@example.com
- Slack: #ai-ppt-assistant

## License

MIT License - see LICENSE file for details