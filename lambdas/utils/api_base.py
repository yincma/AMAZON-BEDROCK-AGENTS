"""
统一的API基础设施模块
提供请求验证、响应构建、错误处理等基础功能
"""

import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class HttpStatus(Enum):
    """HTTP状态码枚举"""
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


class ErrorCode(Enum):
    """统一错误码"""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FIELD_TYPE = "INVALID_FIELD_TYPE"
    INVALID_FIELD_VALUE = "INVALID_FIELD_VALUE"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


class ValidationError(Exception):
    """验证错误异常"""
    def __init__(self, message: str, field: str = None, value: Any = None, code: str = None):
        self.message = message
        self.field = field
        self.value = value
        self.code = code or ErrorCode.VALIDATION_ERROR.value
        super().__init__(message)


class ResourceNotFoundError(Exception):
    """资源未找到异常"""
    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(self.message)


class ConflictError(Exception):
    """资源冲突异常"""
    def __init__(self, message: str, resource_type: str = None, resource_id: str = None):
        self.message = message
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(message)


class RequestValidator:
    """请求验证器"""

    @staticmethod
    def validate_required_fields(data: Dict, required_fields: List[str]) -> None:
        """验证必填字段"""
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)

        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}",
                code=ErrorCode.MISSING_REQUIRED_FIELD.value
            )

    @staticmethod
    def validate_field_type(value: Any, field_name: str, expected_type: type) -> None:
        """验证字段类型"""
        if not isinstance(value, expected_type):
            raise ValidationError(
                f"Field '{field_name}' must be of type {expected_type.__name__}",
                field=field_name,
                value=value,
                code=ErrorCode.INVALID_FIELD_TYPE.value
            )

    @staticmethod
    def validate_string_length(value: str, field_name: str, min_length: int = None, max_length: int = None) -> None:
        """验证字符串长度"""
        if min_length and len(value) < min_length:
            raise ValidationError(
                f"Field '{field_name}' must be at least {min_length} characters",
                field=field_name,
                value=value,
                code=ErrorCode.INVALID_FIELD_VALUE.value
            )

        if max_length and len(value) > max_length:
            raise ValidationError(
                f"Field '{field_name}' must not exceed {max_length} characters",
                field=field_name,
                value=value,
                code=ErrorCode.INVALID_FIELD_VALUE.value
            )

    @staticmethod
    def validate_number_range(value: float, field_name: str, min_value: float = None, max_value: float = None) -> None:
        """验证数字范围"""
        if min_value is not None and value < min_value:
            raise ValidationError(
                f"Field '{field_name}' must be at least {min_value}",
                field=field_name,
                value=value,
                code=ErrorCode.INVALID_FIELD_VALUE.value
            )

        if max_value is not None and value > max_value:
            raise ValidationError(
                f"Field '{field_name}' must not exceed {max_value}",
                field=field_name,
                value=value,
                code=ErrorCode.INVALID_FIELD_VALUE.value
            )

    @staticmethod
    def validate_enum_value(value: Any, field_name: str, allowed_values: List[Any]) -> None:
        """验证枚举值"""
        if value not in allowed_values:
            raise ValidationError(
                f"Field '{field_name}' must be one of: {', '.join(map(str, allowed_values))}",
                field=field_name,
                value=value,
                code=ErrorCode.INVALID_FIELD_VALUE.value
            )

    @staticmethod
    def validate_uuid(value: str, field_name: str) -> None:
        """验证UUID格式"""
        try:
            uuid.UUID(value)
        except ValueError:
            raise ValidationError(
                f"Field '{field_name}' must be a valid UUID",
                field=field_name,
                value=value,
                code=ErrorCode.INVALID_FIELD_VALUE.value
            )

    @staticmethod
    def parse_and_validate_body(event: Dict, required_fields: List[str] = None) -> Dict:
        """解析并验证请求体"""
        body_str = event.get('body')
        if not body_str:
            if required_fields:
                raise ValidationError("Request body is required", code=ErrorCode.MISSING_REQUIRED_FIELD.value)
            return {}

        try:
            body = json.loads(body_str)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in request body: {str(e)}", code=ErrorCode.INVALID_FIELD_TYPE.value)

        if required_fields:
            RequestValidator.validate_required_fields(body, required_fields)

        return body


class ResponseBuilder:
    """统一响应构建器"""

    # 默认CORS头
    DEFAULT_CORS_HEADERS = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS,PATCH'
    }

    @classmethod
    def success_response(cls, status_code: int = 200, data: Any = None, message: str = None, headers: Dict = None) -> Dict:
        """构建成功响应"""
        response_body = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        if message:
            response_body['message'] = message

        if data is not None:
            response_body['data'] = data

        return cls._build_response(status_code, response_body, headers)

    @classmethod
    def error_response(cls, status_code: int, error_code: str, message: str, details: Any = None, headers: Dict = None) -> Dict:
        """构建错误响应"""
        response_body = {
            'success': False,
            'error': {
                'code': error_code,
                'message': message
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }

        if details:
            response_body['error']['details'] = details

        return cls._build_response(status_code, response_body, headers)

    @classmethod
    def validation_error_response(cls, message: str, field: str = None, details: Any = None) -> Dict:
        """构建验证错误响应"""
        error_details = {}
        if field:
            error_details['field'] = field
        if details:
            error_details.update(details if isinstance(details, dict) else {'info': details})

        return cls.error_response(
            HttpStatus.BAD_REQUEST.value,
            ErrorCode.VALIDATION_ERROR.value,
            message,
            error_details if error_details else None
        )

    @classmethod
    def not_found_response(cls, resource_type: str, resource_id: str) -> Dict:
        """构建资源未找到响应"""
        return cls.error_response(
            HttpStatus.NOT_FOUND.value,
            ErrorCode.RESOURCE_NOT_FOUND.value,
            f"{resource_type} not found",
            {'resource_type': resource_type, 'resource_id': resource_id}
        )

    @classmethod
    def internal_error_response(cls, message: str = None) -> Dict:
        """构建内部错误响应"""
        return cls.error_response(
            HttpStatus.INTERNAL_SERVER_ERROR.value,
            ErrorCode.INTERNAL_ERROR.value,
            message or "An internal error occurred"
        )

    @classmethod
    def cors_response(cls) -> Dict:
        """构建CORS预检响应"""
        return {
            'statusCode': 200,
            'headers': cls.DEFAULT_CORS_HEADERS,
            'body': ''
        }

    @classmethod
    def _build_response(cls, status_code: int, body: Dict, headers: Dict = None) -> Dict:
        """构建HTTP响应"""
        response_headers = cls.DEFAULT_CORS_HEADERS.copy()
        response_headers['Content-Type'] = 'application/json'

        if headers:
            response_headers.update(headers)

        return {
            'statusCode': status_code,
            'headers': response_headers,
            'body': json.dumps(body, ensure_ascii=False, default=str)
        }


class APIHandler:
    """API处理器基类"""

    def __init__(self):
        self.validator = RequestValidator()
        self.response_builder = ResponseBuilder()
        self.logger = logging.getLogger(self.__class__.__name__)

    def handle_request(self, event: Dict, context: Any) -> Dict:
        """处理请求的统一入口"""
        try:
            # 处理CORS预检请求
            if event.get('httpMethod') == 'OPTIONS':
                return self.response_builder.cors_response()

            # 记录请求信息
            self._log_request(event)

            # 路由到具体处理方法
            response = self._route_request(event, context)

            # 记录响应信息
            self._log_response(response)

            return response

        except ValidationError as e:
            self.logger.warning(f"Validation error: {e.message}")
            return self.response_builder.validation_error_response(e.message, e.field, {'value': e.value} if e.value else None)

        except ResourceNotFoundError as e:
            self.logger.warning(f"Resource not found: {e.message}")
            return self.response_builder.not_found_response(e.resource_type, e.resource_id)

        except ConflictError as e:
            self.logger.warning(f"Conflict error: {e.message}")
            return self.response_builder.error_response(
                HttpStatus.CONFLICT.value,
                ErrorCode.RESOURCE_ALREADY_EXISTS.value,
                e.message,
                {'resource_type': e.resource_type, 'resource_id': e.resource_id} if e.resource_type else None
            )

        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return self.response_builder.internal_error_response()

    def _route_request(self, event: Dict, context: Any) -> Dict:
        """路由请求到具体处理方法（子类实现）"""
        raise NotImplementedError("Subclass must implement _route_request method")

    def _log_request(self, event: Dict) -> None:
        """记录请求日志"""
        self.logger.info(f"Request: {event.get('httpMethod')} {event.get('path')}")
        if event.get('queryStringParameters'):
            self.logger.info(f"Query params: {event['queryStringParameters']}")
        if event.get('pathParameters'):
            self.logger.info(f"Path params: {event['pathParameters']}")

    def _log_response(self, response: Dict) -> None:
        """记录响应日志"""
        self.logger.info(f"Response status: {response.get('statusCode')}")


def with_error_handling(func: Callable) -> Callable:
    """错误处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e.message}")
            return ResponseBuilder.validation_error_response(e.message, e.field)
        except ResourceNotFoundError as e:
            logger.warning(f"Resource not found in {func.__name__}: {e.message}")
            return ResponseBuilder.not_found_response(e.resource_type, e.resource_id)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            return ResponseBuilder.internal_error_response()

    return wrapper


def validate_request(**validators):
    """请求验证装饰器"""
    def decorator(func: Callable) -> Callable:
        def wrapper(self, event: Dict, *args, **kwargs):
            # 解析请求体
            if 'body_required' in validators and validators['body_required']:
                body = RequestValidator.parse_and_validate_body(
                    event,
                    validators.get('required_fields', [])
                )
                event['parsed_body'] = body

            # 验证路径参数
            if 'path_params' in validators:
                path_params = event.get('pathParameters', {})
                for param, rules in validators['path_params'].items():
                    if param not in path_params:
                        raise ValidationError(f"Path parameter '{param}' is required")

                    value = path_params[param]
                    if 'type' in rules and rules['type'] == 'uuid':
                        RequestValidator.validate_uuid(value, param)

            # 验证查询参数
            if 'query_params' in validators:
                query_params = event.get('queryStringParameters', {}) or {}
                for param, rules in validators['query_params'].items():
                    if rules.get('required') and param not in query_params:
                        raise ValidationError(f"Query parameter '{param}' is required")

                    if param in query_params:
                        value = query_params[param]
                        if 'type' in rules:
                            if rules['type'] == 'int':
                                try:
                                    query_params[param] = int(value)
                                except ValueError:
                                    raise ValidationError(f"Query parameter '{param}' must be an integer")
                            elif rules['type'] == 'bool':
                                query_params[param] = value.lower() in ('true', '1', 'yes')

                        if 'enum' in rules:
                            RequestValidator.validate_enum_value(value, param, rules['enum'])

            return func(self, event, *args, **kwargs)

        return wrapper
    return decorator