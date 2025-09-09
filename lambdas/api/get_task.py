"""
Lambda function for retrieving task status from DynamoDB.
Handles GET /tasks/{task_id} requests to return task status and progress information.

This function:
1. Validates the task_id UUID format
2. Retrieves task data from DynamoDB
3. Deserializes DynamoDB response format
4. Returns formatted task status with proper error handling

Author: AI PPT Assistant Team
"""

import json
import logging
import os
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional, Union, TypedDict
from functools import lru_cache
import time

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO').upper())

# Constants
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': os.environ.get('CORS_ORIGIN', '*'),
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, Authorization',
    'Cache-Control': 'no-cache, no-store, must-revalidate'
}

# DynamoDB client configuration with retry logic
# Note: AWS_REGION is automatically set by Lambda runtime
DYNAMODB_CONFIG = Config(
    region_name=os.environ.get('AWS_DEFAULT_REGION', os.environ.get('AWS_REGION', 'us-east-1')),
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'
    },
    max_pool_connections=10
)

# Type definitions for better type safety
class TaskData(TypedDict, total=False):
    task_id: str
    presentation_id: str
    status: str
    task_type: str
    created_at: str
    updated_at: str
    progress: int
    metadata: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    retry_count: int
    ttl: int

@lru_cache(maxsize=1)
def get_dynamodb_client():
    """
    Get cached DynamoDB client with connection pooling.
    
    Returns:
        boto3.client: Configured DynamoDB client
    """
    return boto3.client('dynamodb', config=DYNAMODB_CONFIG)


def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID format using efficient pattern matching.
    
    Args:
        uuid_string: String to validate as UUID
        
    Returns:
        True if valid UUID, False otherwise
        
    Note:
        Validates UUID v1-v5 formats with proper hyphen placement.
        Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    """
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    # Quick length check first (most efficient)
    if len(uuid_string) != 36:
        return False
    
    # Check hyphen positions
    if uuid_string[8] != '-' or uuid_string[13] != '-' or \
       uuid_string[18] != '-' or uuid_string[23] != '-':
        return False
    
    try:
        # Validate actual UUID format
        uuid_obj = uuid.UUID(uuid_string)
        # Ensure the string representation matches exactly (case-insensitive for UUID)
        return str(uuid_obj).lower() == uuid_string.lower()
    except (ValueError, TypeError, AttributeError):
        return False


def deserialize_dynamodb_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deserialize DynamoDB item format to native Python types.
    
    Optimized for performance with early returns and reduced function calls.
    
    Args:
        item: DynamoDB item in AttributeValue format
        
    Returns:
        Deserialized item with native Python types
    """
    if not item or not isinstance(item, dict):
        return {}
    
    def deserialize_attribute(attr_value: Dict[str, Any]) -> Any:
        """
        Deserialize a single DynamoDB attribute value.
        
        Performance optimized with most common types checked first.
        """
        if not isinstance(attr_value, dict):
            return attr_value
        
        # Most common types first for performance
        if 'S' in attr_value:
            return attr_value['S']
        
        if 'N' in attr_value:
            # Convert to appropriate numeric type
            num_str = str(attr_value['N'])
            try:
                # Check for decimal point to determine int vs float
                if '.' in num_str or 'e' in num_str.lower():
                    return float(num_str)
                return int(num_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse number '{num_str}': {e}")
                return num_str
        
        if 'BOOL' in attr_value:
            return attr_value['BOOL']
        
        if 'M' in attr_value:
            # Recursive deserialization for maps
            return {k: deserialize_attribute(v) for k, v in attr_value['M'].items()}
        
        if 'L' in attr_value:
            # Recursive deserialization for lists
            return [deserialize_attribute(item) for item in attr_value['L']]
        
        if 'NULL' in attr_value and attr_value['NULL']:
            return None
        
        # Less common types
        if 'SS' in attr_value:
            # String set - return as list for JSON compatibility
            return list(attr_value['SS'])
        
        if 'NS' in attr_value:
            # Number set - convert each to appropriate numeric type
            result = []
            for n in attr_value['NS']:
                n_str = str(n)
                try:
                    if '.' in n_str or 'e' in n_str.lower():
                        result.append(float(n_str))
                    else:
                        result.append(int(n_str))
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse number in set: {n_str}")
                    result.append(n_str)
            return result
        
        if 'BS' in attr_value:
            # Binary set - return as list for JSON compatibility
            return list(attr_value['BS'])
        
        # Unknown type - log and return as-is
        logger.warning(f"Unknown DynamoDB attribute type: {list(attr_value.keys())}")
        return attr_value
    
    # Deserialize all top-level attributes
    try:
        return {key: deserialize_attribute(value) for key, value in item.items()}
    except Exception as e:
        logger.error(f"Error deserializing DynamoDB item: {e}", exc_info=True)
        # Return partially deserialized item rather than failing completely
        return item


def format_response(
    status_code: int,
    success: bool,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    additional_headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Format standardized API response with consistent structure.
    
    Args:
        status_code: HTTP status code
        success: Whether the request was successful
        data: Response data (for successful responses)
        error: Error message (for error responses)
        additional_headers: Additional headers to include
        
    Returns:
        Formatted Lambda response
    """
    headers = CORS_HEADERS.copy()
    
    if additional_headers:
        headers.update(additional_headers)
    
    response_body = {'success': success}
    
    if success and data is not None:
        response_body.update(data)
    elif error:
        response_body['error'] = error
        # Add error details for debugging (in non-production)
        if os.environ.get('ENVIRONMENT', 'dev') != 'production':
            response_body['timestamp'] = time.time()
    
    # Custom JSON encoder for Decimal and other types
    def json_encoder(obj):
        if isinstance(obj, Decimal):
            # Convert Decimal to int or float
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return str(obj)
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(response_body, default=json_encoder, ensure_ascii=False)
    }


def format_error_response(
    status_code: int,
    error_message: str,
    additional_headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Format error response (wrapper for backward compatibility).
    """
    return format_response(
        status_code=status_code,
        success=False,
        error=error_message,
        additional_headers=additional_headers
    )


def format_success_response(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format successful task response in OpenAPI compliant format.
    """
    # Return task data directly for OpenAPI compliance
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps(task_data, default=lambda obj: str(obj) if isinstance(obj, Decimal) else str(obj))
    }


def extract_and_validate_task_id(event: Dict[str, Any]) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Extract and validate task_id from event.
    
    Args:
        event: API Gateway event
        
    Returns:
        Tuple of (task_id, error_response) where error_response is None if valid
    """
    # Extract task_id from path parameters
    path_parameters = event.get('pathParameters')
    if not path_parameters:
        logger.warning("Missing pathParameters in event")
        return None, format_error_response(400, "Missing required parameter: task_id")
    
    if 'task_id' not in path_parameters:
        logger.warning("Missing task_id in path parameters")
        return None, format_error_response(400, "Missing required parameter: task_id")
    
    task_id = path_parameters['task_id'].strip() if path_parameters['task_id'] else ''
    if not task_id:
        logger.warning("Empty task_id provided")
        return None, format_error_response(400, "Invalid task_id format. Must be a valid UUID.")
    
    # Validate task_id format
    if not validate_uuid(task_id):
        logger.warning(f"Invalid task_id format: {task_id}")
        return None, format_error_response(400, "Invalid task_id format. Must be a valid UUID.")
    
    return task_id, None


def get_task_from_dynamodb(
    task_id: str,
    table_name: str,
    max_retries: int = 3
) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Retrieve task from DynamoDB with retry logic.
    
    Args:
        task_id: Task ID to retrieve
        table_name: DynamoDB table name
        max_retries: Maximum number of retries for transient errors
        
    Returns:
        Tuple of (task_data, error_response) where error_response is None if successful
    """
    dynamodb_client = get_dynamodb_client()
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Retrieving task {task_id} from table {table_name} (attempt {attempt + 1})")
            
            response = dynamodb_client.get_item(
                TableName=table_name,
                Key={'task_id': {'S': task_id}}
            )
            
            # Check if task exists
            if 'Item' not in response or not response['Item']:
                logger.info(f"Task {task_id} not found in database")
                return None, format_error_response(404, f"Task {task_id} not found")
            
            # Deserialize DynamoDB item
            task_data = deserialize_dynamodb_item(response['Item'])
            return task_data, None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(f"DynamoDB ClientError (attempt {attempt + 1}): {error_code} - {error_message}")
            
            # Handle specific DynamoDB errors
            if error_code == 'ProvisionedThroughputExceededException':
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) * 0.1
                    logger.info(f"Throttled, retrying after {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    return None, format_error_response(
                        503,
                        "Service temporarily unavailable due to throttling. Please try again later.",
                        additional_headers={'Retry-After': '30'}
                    )
            elif error_code == 'ResourceNotFoundException':
                return None, format_error_response(
                    500,
                    "Database configuration error. Please contact support."
                )
            elif error_code == 'ValidationException':
                return None, format_error_response(400, "Invalid request format")
            elif error_code in ['InternalServerError', 'ServiceUnavailable']:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.1
                    logger.info(f"Transient error, retrying after {wait_time}s")
                    time.sleep(wait_time)
                    continue
                else:
                    return None, format_error_response(503, "Service temporarily unavailable")
            else:
                # Generic DynamoDB error
                return None, format_error_response(500, "Database error occurred")
    
    return None, format_error_response(500, "Failed to retrieve task after multiple attempts")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /tasks/{task_id} requests.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    request_id = context.aws_request_id if context else 'unknown'
    
    try:
        logger.info(f"Processing GET task request (request_id: {request_id})")
        
        # Extract and validate task_id
        task_id, error_response = extract_and_validate_task_id(event)
        if error_response:
            return error_response
        
        # Get table name from environment (now using standard DYNAMODB_TABLE)
        table_name = os.environ.get('DYNAMODB_TABLE')
        if not table_name:
            logger.error("DYNAMODB_TABLE environment variable not configured")
            return format_error_response(500, "Service configuration error")
        
        # Retrieve task from DynamoDB with retry logic
        task_data, error_response = get_task_from_dynamodb(task_id, table_name)
        if error_response:
            return error_response
        
        # Log success metrics
        logger.info(
            f"Successfully retrieved task {task_id}",
            extra={
                'task_id': task_id,
                'status': task_data.get('status'),
                'request_id': request_id,
                'remaining_time_ms': context.get_remaining_time_in_millis() if context else None
            }
        )
        
        return format_success_response(task_data)
        
    except Exception as e:
        logger.error(
            f"Unexpected error in lambda_handler: {str(e)}",
            exc_info=True,
            extra={'request_id': request_id}
        )
        
        # Return generic error in production, detailed error in dev
        if os.environ.get('ENVIRONMENT', 'dev') == 'production':
            return format_error_response(500, "Internal server error occurred")
        else:
            return format_error_response(
                500,
                f"Internal server error: {str(e)[:200]}"  # Limit error message length
            )