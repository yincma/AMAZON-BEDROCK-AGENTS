"""
自定义异常类 - 提供类型安全的异常处理体系
"""
from typing import Optional, Dict, Any
from .constants import Config

class PPTAssistantError(Exception):
    """PPT助手应用的基础异常类"""

    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        """初始化异常

        Args:
            message: 错误消息
            error_code: 错误代码
            details: 额外的错误详情
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or Config.Error.UNKNOWN_ERROR
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            包含异常信息的字典
        """
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details
        }

class ValidationError(PPTAssistantError):
    """输入验证异常"""

    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['invalid_value'] = str(value)

        super().__init__(
            message,
            Config.Error.VALIDATION_ERROR,
            details
        )
        self.field = field
        self.value = value

class ContentGenerationError(PPTAssistantError):
    """内容生成异常"""

    def __init__(self, message: str, stage: str = None, bedrock_error: str = None):
        details = {}
        if stage:
            details['generation_stage'] = stage
        if bedrock_error:
            details['bedrock_error'] = bedrock_error

        super().__init__(
            message,
            Config.Error.CONTENT_GENERATION_FAILED,
            details
        )
        self.stage = stage
        self.bedrock_error = bedrock_error

class OutlineGenerationError(ContentGenerationError):
    """大纲生成异常"""

    def __init__(self, message: str, topic: str = None, page_count: int = None):
        details = {
            'generation_stage': 'outline'
        }
        if topic:
            details['topic'] = topic
        if page_count:
            details['page_count'] = page_count

        super().__init__(message, 'outline', None)
        self.error_code = Config.Error.OUTLINE_GENERATION_FAILED
        self.details.update(details)

class PPTCompilationError(PPTAssistantError):
    """PPT编译异常"""

    def __init__(self, message: str, slides_count: int = None, compilation_stage: str = None):
        details = {}
        if slides_count:
            details['slides_count'] = slides_count
        if compilation_stage:
            details['compilation_stage'] = compilation_stage

        super().__init__(
            message,
            Config.Error.PPT_COMPILATION_FAILED,
            details
        )

class S3OperationError(PPTAssistantError):
    """S3操作异常"""

    def __init__(self, message: str, operation: str = None,
                 bucket: str = None, key: str = None, aws_error_code: str = None):
        details = {}
        if operation:
            details['s3_operation'] = operation
        if bucket:
            details['bucket'] = bucket
        if key:
            details['key'] = key
        if aws_error_code:
            details['aws_error_code'] = aws_error_code

        super().__init__(
            message,
            Config.Error.S3_OPERATION_FAILED,
            details
        )

class BedrockAPIError(PPTAssistantError):
    """Bedrock API异常"""

    def __init__(self, message: str, model_id: str = None,
                 request_id: str = None, aws_error_code: str = None):
        details = {}
        if model_id:
            details['model_id'] = model_id
        if request_id:
            details['request_id'] = request_id
        if aws_error_code:
            details['aws_error_code'] = aws_error_code

        super().__init__(
            message,
            Config.Error.BEDROCK_API_FAILED,
            details
        )

class TimeoutError(PPTAssistantError):
    """超时异常"""

    def __init__(self, message: str, operation: str = None,
                 timeout_seconds: int = None):
        details = {}
        if operation:
            details['operation'] = operation
        if timeout_seconds:
            details['timeout_seconds'] = timeout_seconds

        super().__init__(
            message,
            Config.Error.TIMEOUT_ERROR,
            details
        )

class ResourceNotFoundError(PPTAssistantError):
    """资源未找到异常"""

    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} not found: {resource_id}"
        details = {
            'resource_type': resource_type,
            'resource_id': resource_id
        }

        super().__init__(
            message,
            Config.Error.RESOURCE_NOT_FOUND,
            details
        )

class ConfigurationError(PPTAssistantError):
    """配置错误异常"""

    def __init__(self, message: str, config_key: str = None):
        details = {}
        if config_key:
            details['config_key'] = config_key

        super().__init__(
            message,
            Config.Error.SYSTEM_ERROR,
            details
        )

class AuthenticationError(PPTAssistantError):
    """认证异常"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message,
            "AUTHENTICATION_ERROR"
        )

class AuthorizationError(PPTAssistantError):
    """授权异常"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message,
            "AUTHORIZATION_ERROR"
        )

class RateLimitError(PPTAssistantError):
    """频率限制异常"""

    def __init__(self, message: str = "Rate limit exceeded",
                 retry_after: int = None):
        details = {}
        if retry_after:
            details['retry_after'] = retry_after

        super().__init__(
            message,
            "RATE_LIMIT_ERROR",
            details
        )

class RetryableError(PPTAssistantError):
    """可重试异常"""

    def __init__(self, message: str, max_retries: int = None,
                 current_retry: int = None):
        details = {}
        if max_retries:
            details['max_retries'] = max_retries
        if current_retry is not None:
            details['current_retry'] = current_retry

        super().__init__(message, Config.Error.SYSTEM_ERROR, details)
        self.max_retries = max_retries
        self.current_retry = current_retry

    def should_retry(self) -> bool:
        """检查是否应该重试

        Returns:
            是否应该重试
        """
        if self.max_retries is None or self.current_retry is None:
            return True
        return self.current_retry < self.max_retries

# 异常处理辅助函数
def handle_aws_error(aws_error) -> PPTAssistantError:
    """将AWS异常转换为应用异常

    Args:
        aws_error: AWS SDK异常

    Returns:
        应用级异常
    """
    from botocore.exceptions import ClientError, BotoCoreError

    if isinstance(aws_error, ClientError):
        error_code = aws_error.response['Error']['Code']
        error_message = aws_error.response['Error']['Message']

        if 'S3' in str(type(aws_error)) or 's3' in error_message.lower():
            return S3OperationError(
                error_message,
                aws_error_code=error_code
            )
        elif 'bedrock' in error_message.lower():
            return BedrockAPIError(
                error_message,
                aws_error_code=error_code
            )
        else:
            return PPTAssistantError(
                error_message,
                Config.Error.SYSTEM_ERROR,
                {'aws_error_code': error_code}
            )

    elif isinstance(aws_error, BotoCoreError):
        return PPTAssistantError(
            str(aws_error),
            Config.Error.SYSTEM_ERROR,
            {'error_type': 'BotoCoreError'}
        )

    else:
        return PPTAssistantError(
            str(aws_error),
            Config.Error.UNKNOWN_ERROR
        )

def create_validation_error(field: str, value: Any,
                          expected: str = None) -> ValidationError:
    """创建验证错误

    Args:
        field: 字段名
        value: 无效值
        expected: 期望的格式说明

    Returns:
        ValidationError实例
    """
    if expected:
        message = f"Invalid {field}: {value}. Expected: {expected}"
    else:
        message = f"Invalid {field}: {value}"

    return ValidationError(message, field, value)

def is_retryable_error(error: Exception) -> bool:
    """检查异常是否可以重试

    Args:
        error: 异常实例

    Returns:
        是否可重试
    """
    if isinstance(error, RetryableError):
        return error.should_retry()

    if isinstance(error, (TimeoutError, BedrockAPIError, S3OperationError)):
        return True

    # AWS相关的临时错误
    if hasattr(error, 'response') and 'Error' in error.response:
        error_code = error.response['Error']['Code']
        retryable_codes = [
            'ThrottlingException',
            'ServiceUnavailable',
            'InternalServerError',
            'RequestTimeout',
            'TooManyRequestsException'
        ]
        return error_code in retryable_codes

    return False