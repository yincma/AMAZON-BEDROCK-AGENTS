# API Error Codes Reference

This document provides comprehensive information about all error codes returned by the AI PPT Assistant API, including their meanings, common causes, and resolution strategies.

## Error Response Format

All API errors follow the RFC 7807 Problem Details format with consistent structure:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error description",
  "details": {
    "field": "specific_field",
    "additional_context": "value"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "trace_id": "1-63f7b3c0-7a5e3f8d9c2b1a0e"
}
```

## HTTP Status Code Overview

| Status | Category | Description |
|--------|----------|-------------|
| 2xx | Success | Request processed successfully |
| 4xx | Client Error | Problem with the request |
| 5xx | Server Error | Problem on the server side |

## 4xx Client Errors

### 400 Bad Request

#### VALIDATION_ERROR
**Description:** Request validation failed due to invalid parameters or request body.

**Common Causes:**
- Missing required fields
- Invalid field values
- Field length violations
- Invalid data types
- Malformed JSON

**Example Response:**
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
    },
    {
      "field": "topic",
      "message": "Cannot be empty",
      "value": "",
      "constraint": "required"
    }
  ],
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Check all required fields are provided
- Validate field values against documented constraints
- Ensure correct data types
- Verify JSON syntax

#### JSON_PARSE_ERROR
**Description:** Request body contains invalid JSON.

**Common Causes:**
- Malformed JSON syntax
- Missing quotes or brackets
- Trailing commas
- Invalid escape sequences

**Example Response:**
```json
{
  "error": "JSON_PARSE_ERROR",
  "message": "Invalid JSON in request body",
  "details": {
    "line": 5,
    "column": 12,
    "syntax_error": "Unexpected token }"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Validate JSON syntax using a JSON validator
- Check for missing quotes, brackets, or commas
- Remove trailing commas
- Ensure proper character encoding (UTF-8)

#### INVALID_UUID_FORMAT
**Description:** Provided UUID parameter has invalid format.

**Common Causes:**
- Incorrect UUID format
- Missing hyphens
- Wrong character length
- Invalid characters

**Example Response:**
```json
{
  "error": "INVALID_UUID_FORMAT",
  "message": "Invalid UUID format for presentation ID",
  "details": {
    "field": "presentationId",
    "provided_value": "invalid-uuid-123",
    "expected_format": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Ensure UUID follows standard format (8-4-4-4-12 hex digits)
- Check for correct hyphen placement
- Verify all characters are valid hex digits (0-9, a-f, A-F)

### 401 Unauthorized

#### MISSING_API_KEY
**Description:** API key not provided in request headers.

**Common Causes:**
- Missing X-API-Key header
- Empty API key value
- Incorrect header name

**Example Response:**
```json
{
  "error": "MISSING_API_KEY",
  "message": "API key is required",
  "details": {
    "expected_header": "X-API-Key",
    "provided_headers": ["Content-Type", "User-Agent"]
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Include X-API-Key header in all requests
- Ensure API key value is not empty
- Verify header name spelling

#### INVALID_API_KEY
**Description:** Provided API key is invalid or expired.

**Common Causes:**
- Incorrect API key
- Expired API key
- Revoked API key
- API key for wrong environment

**Example Response:**
```json
{
  "error": "INVALID_API_KEY",
  "message": "Invalid API key provided",
  "details": {
    "key_prefix": "ak_123...",
    "issue": "key_not_found"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Verify API key is correct
- Check API key hasn't expired
- Ensure using correct environment API key
- Contact support if key should be valid

#### EXPIRED_TOKEN
**Description:** JWT Bearer token has expired.

**Common Causes:**
- Token past expiration time
- Clock skew issues
- Token not refreshed

**Example Response:**
```json
{
  "error": "EXPIRED_TOKEN",
  "message": "JWT token has expired",
  "details": {
    "expired_at": "2024-01-15T10:00:00Z",
    "current_time": "2024-01-15T10:30:00Z",
    "token_age_seconds": 1800
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Refresh JWT token
- Check system clock synchronization
- Implement automatic token refresh

#### INVALID_TOKEN
**Description:** JWT Bearer token is malformed or invalid.

**Common Causes:**
- Malformed JWT structure
- Invalid signature
- Wrong signing algorithm
- Token tampering

**Example Response:**
```json
{
  "error": "INVALID_TOKEN",
  "message": "Invalid JWT token",
  "details": {
    "issue": "invalid_signature",
    "algorithm": "expected_HS256"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Verify token wasn't modified
- Check signing algorithm matches
- Ensure proper token encoding
- Generate new token if needed

### 403 Forbidden

#### INSUFFICIENT_PERMISSIONS
**Description:** API key lacks required permissions for the requested operation.

**Common Causes:**
- Read-only key attempting write operation
- Key restricted to specific endpoints
- Account tier limitations

**Example Response:**
```json
{
  "error": "INSUFFICIENT_PERMISSIONS",
  "message": "API key does not have permission for this operation",
  "details": {
    "required_permission": "presentations:delete",
    "current_permissions": ["presentations:read", "presentations:create"],
    "operation": "DELETE /presentations/{id}"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Check API key permissions
- Upgrade account tier if needed
- Request additional permissions
- Use appropriate API key for operation

#### QUOTA_EXCEEDED
**Description:** Account quota or usage limit exceeded.

**Common Causes:**
- Monthly generation quota reached
- Storage limit exceeded
- Concurrent request limit hit

**Example Response:**
```json
{
  "error": "QUOTA_EXCEEDED",
  "message": "Monthly presentation generation quota exceeded",
  "details": {
    "quota_type": "monthly_generations",
    "limit": 100,
    "used": 100,
    "reset_date": "2024-02-01T00:00:00Z"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Wait for quota reset
- Upgrade account plan
- Optimize usage patterns
- Contact support for quota increase

### 404 Not Found

#### PRESENTATION_NOT_FOUND
**Description:** Requested presentation does not exist or is not accessible.

**Common Causes:**
- Incorrect presentation ID
- Presentation was deleted
- Presentation belongs to different account
- Presentation expired

**Example Response:**
```json
{
  "error": "PRESENTATION_NOT_FOUND",
  "message": "Presentation not found",
  "details": {
    "presentation_id": "550e8400-e29b-41d4-a716-446655440000",
    "resource_type": "presentation"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Verify presentation ID is correct
- Check presentation hasn't been deleted
- Ensure using correct API key
- List presentations to find correct ID

#### SLIDE_NOT_FOUND
**Description:** Requested slide number does not exist in the presentation.

**Common Causes:**
- Slide number out of range
- Presentation has fewer slides than expected
- Zero-based indexing confusion (API uses 1-based)

**Example Response:**
```json
{
  "error": "SLIDE_NOT_FOUND",
  "message": "Slide not found",
  "details": {
    "slide_number": 15,
    "total_slides": 10,
    "valid_range": "1-10"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Check total number of slides in presentation
- Use 1-based indexing (first slide is 1, not 0)
- Verify slide number is within valid range

#### TASK_NOT_FOUND
**Description:** Requested task ID does not exist or is not accessible.

**Common Causes:**
- Incorrect task ID
- Task expired or cleaned up
- Task belongs to different account

**Example Response:**
```json
{
  "error": "TASK_NOT_FOUND",
  "message": "Task not found",
  "details": {
    "task_id": "task_123e4567-e89b-12d3-a456-426614174000",
    "resource_type": "task"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Verify task ID is correct
- Check task hasn't expired
- Ensure using correct API key

### 409 Conflict

#### PRESENTATION_LOCKED
**Description:** Presentation is currently locked by another operation.

**Common Causes:**
- Concurrent modifications
- Previous operation still in progress
- Lock not properly released

**Example Response:**
```json
{
  "error": "PRESENTATION_LOCKED",
  "message": "Presentation is locked by another operation",
  "details": {
    "lock_token": "lock_789e0123-f45g-67h8-i901-234567890abc",
    "locked_at": "2024-01-15T10:25:00Z",
    "lock_expires": "2024-01-15T10:35:00Z",
    "operation": "slide_update"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Wait for lock to expire
- Retry after lock expiration time
- Check if other operations are in progress
- Contact support if lock persists unexpectedly

#### INVALID_STATE_TRANSITION
**Description:** Operation not allowed in current presentation state.

**Common Causes:**
- Trying to download incomplete presentation
- Modifying failed presentation
- Deleting presentation during generation

**Example Response:**
```json
{
  "error": "INVALID_STATE_TRANSITION",
  "message": "Cannot download presentation in current state",
  "details": {
    "current_state": "processing",
    "allowed_states": ["completed"],
    "operation": "download"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Wait for presentation to reach required state
- Check presentation status before operation
- Use appropriate endpoints for current state

### 412 Precondition Failed

#### ETAG_MISMATCH
**Description:** ETag in If-Match header doesn't match current resource version.

**Common Causes:**
- Resource modified by another request
- Outdated ETag value
- Missing ETag in concurrent update

**Example Response:**
```json
{
  "error": "ETAG_MISMATCH",
  "message": "Resource has been modified by another request",
  "details": {
    "current_etag": "\"33a64df551425fcc55e4d42a148795d9f25f89d4\"",
    "provided_etag": "\"22b53de441324fcc44d3d31b138684d8f14e78c3\"",
    "resource_version": 5
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Fetch latest resource version
- Update ETag value
- Retry operation with correct ETag
- Implement conflict resolution strategy

### 429 Too Many Requests

#### RATE_LIMIT_EXCEEDED
**Description:** Rate limit exceeded for the current time window.

**Common Causes:**
- Too many requests in short time period
- Burst traffic patterns
- Inefficient polling intervals
- Multiple clients using same API key

**Example Response:**
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Please try again later.",
  "details": {
    "limit": 10,
    "window": "1 minute",
    "reset_time": "2024-01-15T10:31:00Z",
    "retry_after_seconds": 60
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Response Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 2024-01-15T10:31:00Z
Retry-After: 60
```

**Resolution:**
- Wait for rate limit to reset
- Implement exponential backoff
- Reduce request frequency
- Use appropriate polling intervals
- Consider caching responses

## 5xx Server Errors

### 500 Internal Server Error

#### INTERNAL_ERROR
**Description:** Unexpected server error occurred.

**Common Causes:**
- Database connectivity issues
- Service dependency failures
- Unhandled exceptions
- Resource exhaustion

**Example Response:**
```json
{
  "error": "INTERNAL_ERROR",
  "message": "An internal error occurred. Please try again later.",
  "details": {
    "error_id": "ERR-2024-0115-001",
    "component": "presentation_generator"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z",
  "support_contact": "support@ai-ppt-assistant.com",
  "incident_id": "INC-2024-0115-001"
}
```

**Resolution:**
- Retry request after brief delay
- Check system status page
- Contact support with incident ID
- Implement circuit breaker pattern

#### DATABASE_ERROR
**Description:** Database operation failed.

**Common Causes:**
- Database connection timeout
- Query timeout
- Database overload
- Data corruption

**Example Response:**
```json
{
  "error": "DATABASE_ERROR",
  "message": "Database operation failed",
  "details": {
    "operation": "presentation_lookup",
    "timeout_seconds": 30
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z",
  "incident_id": "INC-2024-0115-002"
}
```

**Resolution:**
- Retry request with exponential backoff
- Check if issue is persistent
- Contact support if problem continues

#### SERVICE_UNAVAILABLE
**Description:** Required service dependency is unavailable.

**Common Causes:**
- AWS service outage
- Bedrock API unavailable
- S3 service issues
- Network connectivity problems

**Example Response:**
```json
{
  "error": "SERVICE_UNAVAILABLE",
  "message": "Required service is temporarily unavailable",
  "details": {
    "service": "bedrock_api",
    "status": "unreachable",
    "last_success": "2024-01-15T10:00:00Z"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z",
  "estimated_recovery": "2024-01-15T11:00:00Z"
}
```

**Resolution:**
- Wait for service recovery
- Check AWS service status
- Monitor system status page
- Retry after estimated recovery time

### 503 Service Unavailable

#### MAINTENANCE_MODE
**Description:** Service is temporarily unavailable due to maintenance.

**Common Causes:**
- Scheduled maintenance
- System upgrades
- Emergency maintenance

**Example Response:**
```json
{
  "error": "MAINTENANCE_MODE",
  "message": "Service temporarily unavailable for maintenance",
  "details": {
    "maintenance_type": "scheduled",
    "started_at": "2024-01-15T10:00:00Z",
    "estimated_end": "2024-01-15T12:00:00Z"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Response Headers:**
```
Retry-After: 7200
```

**Resolution:**
- Wait for maintenance to complete
- Check status page for updates
- Retry after estimated end time

## Domain-Specific Errors

### AI Generation Errors

#### AI_SERVICE_ERROR
**Description:** AI model service encountered an error.

**Common Causes:**
- Model overload
- Invalid prompt format
- Content policy violation
- Model timeout

**Example Response:**
```json
{
  "error": "AI_SERVICE_ERROR",
  "message": "AI content generation failed",
  "details": {
    "model": "anthropic.claude-v2",
    "error_type": "content_filter",
    "prompt_length": 1500
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Modify prompt content
- Reduce prompt length
- Check content guidelines
- Retry with different parameters

#### CONTENT_FILTER_VIOLATION
**Description:** Generated content violates content policy.

**Common Causes:**
- Inappropriate topic
- Sensitive content detection
- Policy violation in prompt

**Example Response:**
```json
{
  "error": "CONTENT_FILTER_VIOLATION",
  "message": "Content violates usage policies",
  "details": {
    "violation_type": "inappropriate_content",
    "category": "harmful_content"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Review content policy
- Modify topic or prompt
- Use appropriate content
- Contact support if error is unexpected

### File Processing Errors

#### FILE_GENERATION_ERROR
**Description:** PowerPoint file generation failed.

**Common Causes:**
- Template corruption
- Memory limitations
- File system errors
- Content formatting issues

**Example Response:**
```json
{
  "error": "FILE_GENERATION_ERROR",
  "message": "PowerPoint file generation failed",
  "details": {
    "stage": "template_processing",
    "slides_processed": 7,
    "total_slides": 10
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Retry generation
- Reduce slide count if issue persists
- Contact support with error details

#### STORAGE_ERROR
**Description:** File storage operation failed.

**Common Causes:**
- S3 service issues
- Storage quota exceeded
- Permission errors
- Network issues

**Example Response:**
```json
{
  "error": "STORAGE_ERROR",
  "message": "Failed to store presentation file",
  "details": {
    "operation": "s3_upload",
    "file_size": 2457600,
    "bucket": "ai-ppt-presentations"
  },
  "request_id": "req_123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Resolution:**
- Retry operation
- Check storage quota
- Contact support if persistent

## Error Handling Best Practices

### 1. Error Detection and Classification

```python
def handle_api_error(response):
    if response.status_code >= 400:
        error_data = response.json()
        error_code = error_data.get('error')

        # Categorize errors
        if response.status_code == 429:
            # Rate limiting - implement backoff
            retry_after = int(response.headers.get('Retry-After', 60))
            handle_rate_limit(retry_after)
        elif response.status_code in [500, 502, 503, 504]:
            # Server errors - retry with exponential backoff
            handle_server_error(error_data)
        elif response.status_code == 401:
            # Authentication error - refresh credentials
            handle_auth_error(error_data)
        else:
            # Client error - fix request
            handle_client_error(error_data)
```

### 2. Retry Logic with Exponential Backoff

```python
import time
import random

def exponential_backoff_retry(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return func()
        except APIError as e:
            if attempt == max_retries - 1:
                raise

            if e.status_code in [500, 502, 503, 504, 429]:
                # Calculate delay with jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
            else:
                # Don't retry client errors
                raise
```

### 3. Logging and Monitoring

```python
import logging

def log_api_error(error_response, request_context):
    logger = logging.getLogger('api_client')

    logger.error(
        "API Error",
        extra={
            'error_code': error_response.get('error'),
            'message': error_response.get('message'),
            'request_id': error_response.get('request_id'),
            'endpoint': request_context.get('endpoint'),
            'method': request_context.get('method'),
            'user_id': request_context.get('user_id'),
            'timestamp': error_response.get('timestamp')
        }
    )
```

### 4. User-Friendly Error Messages

```python
ERROR_MESSAGES = {
    'VALIDATION_ERROR': 'Please check your input and try again.',
    'RATE_LIMIT_EXCEEDED': 'Too many requests. Please wait a moment and try again.',
    'PRESENTATION_NOT_FOUND': 'The requested presentation could not be found.',
    'INTERNAL_ERROR': 'We encountered a technical issue. Please try again later.',
    'MAINTENANCE_MODE': 'The service is temporarily unavailable for maintenance.'
}

def get_user_friendly_message(error_code):
    return ERROR_MESSAGES.get(error_code, 'An unexpected error occurred.')
```

## Troubleshooting Guide

### Common Issues and Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Authentication failures | 401 errors on all requests | Check API key validity and format |
| Rate limit errors | 429 errors during peak usage | Implement proper retry logic with backoff |
| Timeout errors | Long-running requests failing | Increase timeout values, check network |
| Validation errors | 400 errors with validation details | Review request format and field values |
| Resource not found | 404 errors for valid resources | Verify resource IDs and account access |

### When to Contact Support

Contact support when encountering:
- Persistent 500 errors with incident IDs
- Unexpected authentication failures
- Rate limits lower than documented
- Data corruption or loss
- Service degradation lasting > 15 minutes

### Support Information

When contacting support, provide:
- Request ID from error response
- Complete error response body
- Timestamp of the request
- Steps to reproduce the issue
- Expected vs. actual behavior

**Contact Information:**
- Email: support@ai-ppt-assistant.com
- Priority Support: enterprise@ai-ppt-assistant.com
- Status Page: https://status.ai-ppt-assistant.com
- Documentation: https://docs.ai-ppt-assistant.com