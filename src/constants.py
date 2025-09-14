"""
项目常量定义 - 集中管理所有配置常量，消除硬编码
"""
from typing import List

class APIConstants:
    """API相关常量"""
    # 响应状态码
    HTTP_OK = 200
    HTTP_ACCEPTED = 202
    HTTP_BAD_REQUEST = 400
    HTTP_NOT_FOUND = 404
    HTTP_INTERNAL_ERROR = 500
    HTTP_SERVICE_UNAVAILABLE = 503

    # CORS头信息
    CORS_HEADERS = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }

    # 内容类型
    CONTENT_TYPE_JSON = 'application/json'
    CONTENT_TYPE_PPTX = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'

class FileConstants:
    """文件相关常量"""
    # 大小限制
    MAX_JSON_SIZE_BYTES = 1024 * 1024  # 1MB
    MAX_TOPIC_LENGTH = 200
    MIN_TOPIC_LENGTH = 3

    # 文件路径模板
    STATUS_FILE_TEMPLATE = "presentations/{presentation_id}/status.json"
    CONTENT_FILE_TEMPLATE = "presentations/{presentation_id}/content/slides.json"
    PPTX_FILE_TEMPLATE = "presentations/{presentation_id}/output/presentation.pptx"
    METADATA_FILE_TEMPLATE = "presentations/{presentation_id}/metadata.json"

    # 支持的文件扩展名
    ALLOWED_EXTENSIONS: List[str] = ['pptx', 'json']
    ALLOWED_CONTENT_TYPES: List[str] = [
        'application/json',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ]

class PPTConstants:
    """PPT生成相关常量"""
    # 页数限制
    MIN_PAGE_COUNT = 3
    MAX_PAGE_COUNT = 20
    DEFAULT_PAGE_COUNT = 5

    # 每页要点数量
    MIN_BULLET_POINTS = 3
    MAX_BULLET_POINTS = 5
    DEFAULT_BULLET_POINTS = 3

    # 支持的样式
    SUPPORTED_STYLES: List[str] = ['professional', 'casual', 'academic', 'creative']
    DEFAULT_STYLE = 'professional'

class BedrockConstants:
    """Bedrock API相关常量"""
    # 模型参数
    DEFAULT_MAX_TOKENS = 2000
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_TOP_P = 0.9
    DEFAULT_TOP_K = 250

    # 停止序列
    STOP_SEQUENCES: List[str] = ["\n\nHuman:"]

    # 重试配置
    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2
    RETRY_INITIAL_DELAY = 1

class S3Constants:
    """S3相关常量"""
    # URL过期时间（秒）
    DEFAULT_URL_EXPIRY = 3600  # 1小时
    DOWNLOAD_URL_EXPIRY = 3600  # 1小时
    UPLOAD_URL_EXPIRY = 300     # 5分钟

    # 存储桶前缀
    PRESENTATIONS_PREFIX = "presentations/"

    # 批量操作限制
    MAX_DELETE_OBJECTS = 1000

class SecurityConstants:
    """安全相关常量"""
    # API密钥最小长度
    MIN_API_KEY_LENGTH = 32

    # 危险内容黑名单
    MALICIOUS_PATTERNS: List[str] = [
        '<script', '</script', 'javascript:', 'onerror=', 'onclick=', 'onload=',
        'eval(', 'exec(', 'system(', 'shell_exec', 'passthru', '<iframe',
        'data:text/html', 'vbscript:', 'file://', 'ftp://', '../', '..\\',
        'rm -rf', 'DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE SET',
        '--', '/*', '*/', 'union select', 'concat(', 'char('
    ]

    # 允许的字符模式
    UUID_PATTERN = r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$'
    API_KEY_PATTERN = r'^[A-Za-z0-9\-_]+$'

class PaginationConstants:
    """分页相关常量"""
    DEFAULT_PAGE = 1
    DEFAULT_PER_PAGE = 10
    MAX_PER_PAGE = 100
    MAX_PAGE_NUMBER = 1000

class TimeoutConstants:
    """超时相关常量"""
    # Lambda函数超时
    LAMBDA_TIMEOUT_SECONDS = 300  # 5分钟

    # API调用超时
    BEDROCK_TIMEOUT_SECONDS = 60   # 1分钟
    S3_TIMEOUT_SECONDS = 30        # 30秒

    # 重试延迟
    RETRY_DELAY_SECONDS = 2

class LoggingConstants:
    """日志相关常量"""
    # 日志级别
    DEFAULT_LOG_LEVEL = "INFO"

    # 日志格式
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 敏感信息掩码
    SENSITIVE_FIELDS = ['api_key', 'token', 'password', 'secret']

class ErrorCodes:
    """错误代码常量"""
    # 系统错误
    SYSTEM_ERROR = "SYSTEM_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

    # 验证错误
    VALIDATION_ERROR = "VALIDATION_ERROR"
    JSON_PARSE_ERROR = "JSON_PARSE_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"

    # 业务错误
    OUTLINE_GENERATION_FAILED = "OUTLINE_GENERATION_FAILED"
    CONTENT_GENERATION_FAILED = "CONTENT_GENERATION_FAILED"
    PPT_COMPILATION_FAILED = "PPT_COMPILATION_FAILED"
    CONTENT_SAVE_FAILED = "CONTENT_SAVE_FAILED"

    # 资源错误
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    S3_OPERATION_FAILED = "S3_OPERATION_FAILED"
    BEDROCK_API_FAILED = "BEDROCK_API_FAILED"

class EnvironmentConstants:
    """环境变量名称常量"""
    S3_BUCKET = "S3_BUCKET"
    AWS_REGION = "AWS_REGION"
    BEDROCK_MODEL_ID = "BEDROCK_MODEL_ID"
    LOG_LEVEL = "LOG_LEVEL"
    ENVIRONMENT = "ENVIRONMENT"

    # 默认值
    DEFAULT_BUCKET = "ai-ppt-presentations-dev"
    DEFAULT_REGION = "us-east-1"
    DEFAULT_MODEL_ID = "anthropic.claude-v2"

class StatusConstants:
    """状态相关常量"""
    # 演示文稿状态
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_CONTENT_GENERATED = "content_generated"
    STATUS_COMPILING = "compiling"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    # 处理步骤
    STEP_OUTLINE_GENERATION = "outline_generation"
    STEP_CONTENT_GENERATION = "content_generation"
    STEP_PPT_COMPILATION = "ppt_compilation"
    STEP_UPLOAD_COMPLETE = "upload_complete"

    # 进度百分比
    PROGRESS_START = 0
    PROGRESS_OUTLINE_COMPLETE = 25
    PROGRESS_CONTENT_COMPLETE = 50
    PROGRESS_COMPILATION_COMPLETE = 75
    PROGRESS_FINISHED = 100

# 便捷访问类
class Config:
    """统一配置访问接口"""
    API = APIConstants
    File = FileConstants
    PPT = PPTConstants
    Bedrock = BedrockConstants
    S3 = S3Constants
    Security = SecurityConstants
    Pagination = PaginationConstants
    Timeout = TimeoutConstants
    Logging = LoggingConstants
    Error = ErrorCodes
    Env = EnvironmentConstants
    Status = StatusConstants