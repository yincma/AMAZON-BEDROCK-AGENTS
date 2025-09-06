# Lambda Controllers - AI PPT Assistant

## Overview

This directory contains the Lambda function controllers for the AI PPT Assistant. Each controller handles specific business logic for presentation generation using AWS Bedrock and other AWS services.

## Functions

### 1. create_outline.py
Generates presentation outlines using AWS Bedrock Claude 3.5 Sonnet.

**Features:**
- Multi-language support (EN, JA, ZH, ES, FR, DE, PT, KO)
- Multiple presentation styles (professional, casual, academic, creative, technical)
- Customizable slide count and duration
- Input validation using Pydantic
- Automatic retry logic for API calls
- Saves to DynamoDB and S3

**Environment Variables:**
- `BEDROCK_MODEL_ID`: Claude model ID (default: anthropic.claude-3-5-sonnet-20241022-v2:0)
- `SESSIONS_TABLE`: DynamoDB table name for sessions
- `S3_BUCKET`: S3 bucket for storing outlines
- `MAX_SLIDES`: Maximum slides allowed (default: 20)
- `MIN_SLIDES`: Minimum slides required (default: 5)

**Request Format:**
```json
{
  "topic": "Introduction to AI",
  "audience": "beginners",
  "duration_minutes": 20,
  "style": "professional",
  "language": "en",
  "num_slides": 10,
  "include_examples": true,
  "user_id": "user-123"
}
```

**Response Format:**
```json
{
  "success": true,
  "presentation_id": "uuid",
  "session_id": "uuid",
  "outline": {
    "title": "Introduction to AI",
    "slides": [...]
  },
  "s3_location": "s3://bucket/path",
  "message": "Successfully generated outline with 10 slides"
}
```

## Testing

Run unit tests:
```bash
pytest test_create_outline.py -v
```

Run with coverage:
```bash
pytest test_create_outline.py --cov=create_outline --cov-report=html
```

## Deployment

These functions are deployed using Terraform. See `infrastructure/modules/lambda/` for deployment configuration.

### Manual Deployment:
```bash
# Package the function
zip -r function.zip create_outline.py

# Update function code
aws lambda update-function-code \
  --function-name ai-ppt-assistant-create-outline \
  --zip-file fileb://function.zip
```

## Error Handling

All functions implement comprehensive error handling:

1. **Input Validation**: Pydantic models validate all inputs
2. **Retry Logic**: Automatic retry for transient failures
3. **Graceful Degradation**: Functions continue even if optional services fail
4. **Structured Logging**: AWS Lambda Powertools for consistent logging
5. **Error Responses**: Clear error messages with appropriate HTTP status codes

## Monitoring

Functions use AWS Lambda Powertools for observability:

- **Logging**: Structured JSON logs sent to CloudWatch
- **Tracing**: X-Ray tracing for distributed tracing
- **Metrics**: Custom metrics for business logic

### Key Metrics:
- `OutlineGenerated`: Count of successful outline generations
- `SlidesCount`: Number of slides per outline
- `OutlineGenerationError`: Count of failures

## Best Practices

1. **Environment Variables**: Never hardcode sensitive values
2. **Error Handling**: Always catch and log exceptions
3. **Input Validation**: Validate all inputs before processing
4. **Idempotency**: Design functions to be idempotent
5. **Timeouts**: Set appropriate timeouts (default: 30s)
6. **Memory**: Allocate sufficient memory (recommended: 512MB)
7. **Layers**: Use Lambda layers for shared dependencies

## Dependencies

Functions use the shared Lambda layer containing:
- `boto3`: AWS SDK
- `pydantic`: Data validation
- `aws-lambda-powertools`: Logging, tracing, metrics
- `tenacity`: Retry logic
- Other dependencies defined in `lambdas/layers/requirements.txt`

## Security

- **IAM Roles**: Functions use least-privilege IAM roles
- **VPC**: Can be deployed in VPC for network isolation
- **Encryption**: Data encrypted at rest and in transit
- **API Keys**: API Gateway requires API keys for access
- **Input Sanitization**: All inputs validated and sanitized

## Future Enhancements

- [ ] Add caching for frequently requested outlines
- [ ] Implement batch outline generation
- [ ] Add support for custom templates
- [ ] Integrate with more AI models
- [ ] Add real-time progress updates via WebSocket