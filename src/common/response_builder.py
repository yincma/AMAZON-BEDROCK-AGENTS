"""
响应构建器 - 统一API响应格式，消除重复代码
"""
import json
from typing import Dict, Any, Optional
from ..constants import Config

class ResponseBuilder:
    """统一的API响应构建器"""

    @staticmethod
    def success_response(status_code: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建成功响应

        Args:
            status_code: HTTP状态码
            data: 响应数据

        Returns:
            标准化的成功响应字典
        """
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': Config.API.CONTENT_TYPE_JSON,
                **Config.API.CORS_HEADERS
            },
            'body': json.dumps(data, ensure_ascii=False)
        }

    @staticmethod
    def error_response(status_code: int, message: str,
                      error_code: Optional[str] = None,
                      details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """构建错误响应

        Args:
            status_code: HTTP状态码
            message: 错误消息
            error_code: 错误代码（可选）
            details: 额外的错误详情（可选）

        Returns:
            标准化的错误响应字典
        """
        error_body = {
            'error': message,
            'timestamp': ResponseBuilder._get_current_timestamp()
        }

        if error_code:
            error_body['error_code'] = error_code

        if details:
            error_body['details'] = details

        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': Config.API.CONTENT_TYPE_JSON,
                **Config.API.CORS_HEADERS
            },
            'body': json.dumps(error_body)
        }

    @staticmethod
    def cors_response() -> Dict[str, Any]:
        """构建CORS预检响应

        Returns:
            CORS预检响应字典
        """
        return {
            'statusCode': Config.API.HTTP_OK,
            'headers': Config.API.CORS_HEADERS,
            'body': ''
        }

    @staticmethod
    def _get_current_timestamp() -> str:
        """获取当前时间戳

        Returns:
            ISO格式的时间戳字符串
        """
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'

    @staticmethod
    def validation_error_response(message: str,
                                field: Optional[str] = None) -> Dict[str, Any]:
        """构建验证错误响应

        Args:
            message: 验证错误消息
            field: 出错的字段名（可选）

        Returns:
            验证错误响应字典
        """
        details = {'field': field} if field else None
        return ResponseBuilder.error_response(
            Config.API.HTTP_BAD_REQUEST,
            message,
            Config.Error.VALIDATION_ERROR,
            details
        )

    @staticmethod
    def not_found_response(resource_type: str,
                          resource_id: str) -> Dict[str, Any]:
        """构建资源未找到响应

        Args:
            resource_type: 资源类型
            resource_id: 资源ID

        Returns:
            资源未找到响应字典
        """
        return ResponseBuilder.error_response(
            Config.API.HTTP_NOT_FOUND,
            f"{resource_type} not found",
            Config.Error.RESOURCE_NOT_FOUND,
            {'resource_type': resource_type, 'resource_id': resource_id}
        )

    @staticmethod
    def internal_error_response(message: str = "Internal server error",
                              error_code: str = None) -> Dict[str, Any]:
        """构建内部服务器错误响应

        Args:
            message: 错误消息
            error_code: 错误代码

        Returns:
            内部错误响应字典
        """
        return ResponseBuilder.error_response(
            Config.API.HTTP_INTERNAL_ERROR,
            message,
            error_code or Config.Error.SYSTEM_ERROR
        )

    @staticmethod
    def service_unavailable_response(message: str = "Service temporarily unavailable",
                                   retry_after: Optional[int] = None) -> Dict[str, Any]:
        """构建服务不可用响应

        Args:
            message: 错误消息
            retry_after: 重试等待时间（秒）

        Returns:
            服务不可用响应字典
        """
        headers = {
            'Content-Type': Config.API.CONTENT_TYPE_JSON,
            **Config.API.CORS_HEADERS
        }

        if retry_after:
            headers['Retry-After'] = str(retry_after)

        return {
            'statusCode': Config.API.HTTP_SERVICE_UNAVAILABLE,
            'headers': headers,
            'body': json.dumps({
                'error': message,
                'error_code': Config.Error.SYSTEM_ERROR,
                'timestamp': ResponseBuilder._get_current_timestamp(),
                'retry_after': retry_after
            })
        }