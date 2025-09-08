"""
API Utilities - AI PPT Assistant
Shared utilities for API Lambda functions to eliminate code duplication
"""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(__name__)


# Standard HTTP status codes
class HTTPStatus:
    """HTTP status code constants"""

    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    REQUEST_TIMEOUT = 408
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


class APIResponseBuilder:
    """Builder for creating standardized API responses"""

    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id or str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()

    @staticmethod
    def create_headers(
        content_type: str = "application/json",
        additional_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Create standard response headers"""

        headers = {
            "Content-Type": content_type,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-API-Key, Authorization",
            "Access-Control-Max-Age": "86400",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }

        if additional_headers:
            headers.update(additional_headers)

        return headers

    def success_response(
        self,
        data: Any,
        status_code: int = HTTPStatus.OK,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create successful response"""

        response_body = {
            "success": True,
            "data": data,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
        }

        if message:
            response_body["message"] = message

        if metadata:
            response_body["metadata"] = metadata

        return {
            "statusCode": status_code,
            "headers": self.create_headers(),
            "body": json.dumps(response_body, default=str),
        }

    def error_response(
        self,
        error_code: str,
        error_message: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None,
        validation_errors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create error response"""

        response_body = {
            "success": False,
            "error": {
                "code": error_code,
                "message": error_message,
                "request_id": self.request_id,
                "timestamp": self.timestamp,
            },
        }

        if details:
            response_body["error"]["details"] = details

        if validation_errors:
            response_body["error"]["validation_errors"] = validation_errors

        return {
            "statusCode": status_code,
            "headers": self.create_headers(),
            "body": json.dumps(response_body, default=str),
        }

    def validation_error_response(
        self, validation_errors: List[str], error_message: str = "Validation failed"
    ) -> Dict[str, Any]:
        """Create validation error response"""

        return self.error_response(
            error_code="VALIDATION_ERROR",
            error_message=error_message,
            status_code=HTTPStatus.BAD_REQUEST,
            validation_errors=validation_errors,
        )

    def not_found_response(
        self, resource_type: str, resource_id: str
    ) -> Dict[str, Any]:
        """Create not found error response"""

        return self.error_response(
            error_code="NOT_FOUND",
            error_message=f"{resource_type} not found",
            status_code=HTTPStatus.NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )

    def timeout_response(
        self, operation: str, timeout_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create timeout error response"""

        return self.error_response(
            error_code="REQUEST_TIMEOUT",
            error_message=f"Operation '{operation}' timed out",
            status_code=HTTPStatus.REQUEST_TIMEOUT,
            details={"operation": operation, "timeout_info": timeout_info},
        )


class APIRequestParser:
    """Parser for extracting data from API Gateway events"""

    def __init__(self, event: Dict[str, Any], context: LambdaContext):
        self.event = event
        self.context = context
        self.request_id = context.aws_request_id if context else str(uuid.uuid4())

    def get_path_parameters(self) -> Dict[str, str]:
        """Extract path parameters"""
        return self.event.get("pathParameters") or {}

    def get_query_parameters(self) -> Dict[str, str]:
        """Extract query string parameters"""
        return self.event.get("queryStringParameters") or {}

    def get_headers(self) -> Dict[str, str]:
        """Extract headers (case-insensitive)"""
        headers = self.event.get("headers") or {}
        # Convert to lowercase for case-insensitive access
        return {k.lower(): v for k, v in headers.items()}

    def get_body(self) -> Dict[str, Any]:
        """Parse and return request body"""
        body = self.event.get("body", "{}")

        if isinstance(body, str):
            try:
                return json.loads(body) if body.strip() else {}
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse request body: {e}")
                raise ValueError(f"Invalid JSON in request body: {e}")

        return body or {}

    def get_user_context(self) -> Dict[str, Any]:
        """Extract user context from request"""
        # This would be enhanced with actual authentication context
        headers = self.get_headers()

        return {
            "user_agent": headers.get("user-agent", "unknown"),
            "source_ip": self.event.get("requestContext", {})
            .get("identity", {})
            .get("sourceIp"),
            "api_key_id": headers.get("x-api-key-id"),
            "request_time": self.event.get("requestContext", {}).get(
                "requestTimeEpoch"
            ),
        }

    def get_pagination_params(
        self, default_limit: int = 20, max_limit: int = 100
    ) -> Dict[str, Any]:
        """Extract pagination parameters"""
        query_params = self.get_query_parameters()

        try:
            limit = min(int(query_params.get("limit", default_limit)), max_limit)
        except (ValueError, TypeError):
            limit = default_limit

        cursor = query_params.get("cursor")
        offset = query_params.get("offset", "0")

        try:
            offset = int(offset)
        except (ValueError, TypeError):
            offset = 0

        return {"limit": limit, "offset": offset, "cursor": cursor}


class APIValidator:
    """Validator for common API request patterns"""

    @staticmethod
    def validate_uuid(value: str, field_name: str = "ID") -> bool:
        """Validate UUID format"""
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            raise ValueError(f"{field_name} must be a valid UUID")

    @staticmethod
    def validate_required_fields(
        data: Dict[str, Any], required_fields: List[str]
    ) -> List[str]:
        """Validate required fields are present and not empty"""
        errors = []

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif not data[field] or (
                isinstance(data[field], str) and not data[field].strip()
            ):
                errors.append(f"Field '{field}' cannot be empty")

        return errors

    @staticmethod
    def validate_string_length(
        value: str, field_name: str, min_length: int = 0, max_length: int = 1000
    ) -> None:
        """Validate string length"""
        if len(value) < min_length:
            raise ValueError(f"{field_name} must be at least {min_length} characters")
        if len(value) > max_length:
            raise ValueError(f"{field_name} must not exceed {max_length} characters")

    @staticmethod
    def validate_numeric_range(
        value: Union[int, float],
        field_name: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
    ) -> None:
        """Validate numeric range"""
        if min_value is not None and value < min_value:
            raise ValueError(f"{field_name} must be at least {min_value}")
        if max_value is not None and value > max_value:
            raise ValueError(f"{field_name} must not exceed {max_value}")


class APIMetricsHelper:
    """Helper for API metrics collection"""

    @staticmethod
    def record_api_metrics(
        metrics_instance: Any,
        endpoint: str,
        method: str,
        status_code: int,
        processing_time_ms: int,
        error_code: Optional[str] = None,
    ):
        """Record standard API metrics"""

        # Basic metrics
        metrics_instance.add_metric(
            name=f"API_{endpoint}_Requests", unit="Count", value=1
        )
        metrics_instance.add_metric(
            name=f"API_{endpoint}_ProcessingTime",
            unit="Milliseconds",
            value=processing_time_ms,
        )

        # Status code metrics
        if 200 <= status_code < 300:
            metrics_instance.add_metric(
                name=f"API_{endpoint}_Success", unit="Count", value=1
            )
        else:
            metrics_instance.add_metric(
                name=f"API_{endpoint}_Error", unit="Count", value=1
            )

            if error_code:
                metrics_instance.add_metric(
                    name=f"API_{endpoint}_{error_code}", unit="Count", value=1
                )

        # Method-specific metrics
        metrics_instance.add_metric(
            name=f"API_{method}_Requests", unit="Count", value=1
        )


# Convenience functions to maintain simplicity


def create_api_response(
    status_code: int,
    data: Optional[Any] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    request_id: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Create standardized API response

    Args:
        status_code: HTTP status code
        data: Response data (for success responses)
        error_code: Error code (for error responses)
        error_message: Error message (for error responses)
        request_id: Request ID for tracking
        **kwargs: Additional response fields
    """

    builder = APIResponseBuilder(request_id)

    if 200 <= status_code < 300:
        # Success response
        return builder.success_response(
            data=data or {},
            status_code=status_code,
            message=kwargs.get("message"),
            metadata=kwargs.get("metadata"),
        )
    else:
        # Error response
        return builder.error_response(
            error_code=error_code or "UNKNOWN_ERROR",
            error_message=error_message or "An error occurred",
            status_code=status_code,
            details=kwargs.get("details"),
            validation_errors=kwargs.get("validation_errors"),
        )


def parse_api_request(
    event: Dict[str, Any], context: LambdaContext
) -> APIRequestParser:
    """Create API request parser instance"""
    return APIRequestParser(event, context)


def validate_presentation_id(presentation_id: str) -> None:
    """Validate presentation ID format"""
    APIValidator.validate_uuid(presentation_id, "Presentation ID")


def validate_slide_id(slide_id: str) -> int:
    """Validate and convert slide ID to integer"""
    try:
        slide_num = int(slide_id)
        APIValidator.validate_numeric_range(
            slide_num, "Slide ID", min_value=1, max_value=100
        )
        return slide_num
    except ValueError:
        raise ValueError("Slide ID must be a positive integer")


def extract_and_validate_path_params(
    event: Dict[str, Any], required_params: List[str]
) -> Dict[str, str]:
    """Extract and validate required path parameters"""

    path_params = event.get("pathParameters") or {}
    errors = APIValidator.validate_required_fields(path_params, required_params)

    if errors:
        raise ValueError(f"Missing path parameters: {', '.join(errors)}")

    return path_params


def create_pagination_response(
    data: List[Any], total_count: int, limit: int, offset: int, base_url: str
) -> Dict[str, Any]:
    """Create paginated response structure"""

    has_next = offset + limit < total_count
    has_prev = offset > 0

    response = {
        "data": data,
        "pagination": {
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "current_page": (offset // limit) + 1,
            "total_pages": (total_count + limit - 1) // limit,
            "has_next": has_next,
            "has_previous": has_prev,
        },
        "_links": {"self": f"{base_url}?limit={limit}&offset={offset}"},
    }

    if has_next:
        response["_links"]["next"] = f"{base_url}?limit={limit}&offset={offset + limit}"

    if has_prev:
        response["_links"][
            "prev"
        ] = f"{base_url}?limit={limit}&offset={max(0, offset - limit)}"

    return response


def handle_api_exceptions(func):
    """Decorator for standardized API exception handling"""

    def wrapper(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
        start_time = time.time()
        request_id = context.aws_request_id if context else str(uuid.uuid4())

        try:
            # Execute the function
            result = func(event, context)

            # Record success metrics
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(
                "API request completed successfully",
                extra={
                    "request_id": request_id,
                    "processing_time_ms": processing_time,
                    "function_name": context.function_name if context else "unknown",
                },
            )

            return result

        except ValueError as e:
            # Validation errors
            processing_time = int((time.time() - start_time) * 1000)
            logger.warning(f"Validation error: {e}", extra={"request_id": request_id})

            return create_api_response(
                status_code=HTTPStatus.BAD_REQUEST,
                error_code="VALIDATION_ERROR",
                error_message=str(e),
                request_id=request_id,
                details={"processing_time_ms": processing_time},
            )

        except KeyError as e:
            # Missing required data
            processing_time = int((time.time() - start_time) * 1000)
            logger.warning(
                f"Missing required data: {e}", extra={"request_id": request_id}
            )

            return create_api_response(
                status_code=HTTPStatus.BAD_REQUEST,
                error_code="MISSING_REQUIRED_DATA",
                error_message=f"Missing required field: {str(e)}",
                request_id=request_id,
                details={"processing_time_ms": processing_time},
            )

        except FileNotFoundError as e:
            # Resource not found
            processing_time = int((time.time() - start_time) * 1000)
            logger.warning(f"Resource not found: {e}", extra={"request_id": request_id})

            return create_api_response(
                status_code=HTTPStatus.NOT_FOUND,
                error_code="RESOURCE_NOT_FOUND",
                error_message="Requested resource not found",
                request_id=request_id,
                details={"processing_time_ms": processing_time},
            )

        except PermissionError as e:
            # Access denied
            processing_time = int((time.time() - start_time) * 1000)
            logger.warning(f"Permission denied: {e}", extra={"request_id": request_id})

            return create_api_response(
                status_code=HTTPStatus.FORBIDDEN,
                error_code="PERMISSION_DENIED",
                error_message="Insufficient permissions to access resource",
                request_id=request_id,
                details={"processing_time_ms": processing_time},
            )

        except TimeoutError as e:
            # Timeout errors
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Request timeout: {e}", extra={"request_id": request_id})

            return create_api_response(
                status_code=HTTPStatus.REQUEST_TIMEOUT,
                error_code="REQUEST_TIMEOUT",
                error_message="Request processing timed out",
                request_id=request_id,
                details={
                    "processing_time_ms": processing_time,
                    "error_details": str(e),
                },
            )

        except Exception as e:
            # Generic server errors
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(
                f"Unexpected error: {e}",
                exc_info=True,
                extra={"request_id": request_id},
            )

            return create_api_response(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                error_code="INTERNAL_ERROR",
                error_message="An internal server error occurred",
                request_id=request_id,
                details={"processing_time_ms": processing_time},
            )

    return wrapper


# Legacy support function to replace existing create_response functions
def create_response(
    status_code: int, body: Dict[str, Any], request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Legacy API response creation function
    Maintains backward compatibility while using new standardized approach
    """

    # Determine if it's an error or success response
    # Only treat as error if status code indicates error OR if error field is a string (not a dict)
    is_api_error = (status_code >= 400) or (isinstance(body.get("error"), str))
    
    if is_api_error:
        error_code = body.get("error", "UNKNOWN_ERROR")
        error_message = body.get("message", "An error occurred")
        details = {k: v for k, v in body.items() if k not in ["error", "message"]}

        return create_api_response(
            status_code=status_code,
            error_code=error_code,
            error_message=error_message,
            request_id=request_id,
            details=details if details else None,
        )
    else:
        # Success response
        message = body.pop("message", None)
        metadata = body.pop("metadata", None)

        return create_api_response(
            status_code=status_code,
            data=body,
            request_id=request_id,
            message=message,
            metadata=metadata,
        )
