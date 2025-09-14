"""
类型定义 - 为项目提供类型安全的数据结构定义
"""
from typing import Dict, List, Any, Optional, Union, TypedDict, Literal
from datetime import datetime

# PPT相关类型
class SlideData(TypedDict):
    """幻灯片数据结构"""
    slide_number: int
    title: str
    content: List[str]

class SlideContent(TypedDict):
    """幻灯片详细内容结构"""
    slide_number: int
    title: str
    bullet_points: List[str]
    speaker_notes: Optional[str]

class OutlineData(TypedDict):
    """大纲数据结构"""
    title: str
    slides: List[SlideData]
    metadata: Dict[str, Any]

class PresentationContent(TypedDict):
    """完整演示文稿内容结构"""
    presentation_id: str
    title: str
    slides: List[SlideContent]
    metadata: Dict[str, Any]
    status: str

# 状态管理类型
PresentationStatus = Literal[
    "pending",
    "processing",
    "content_generated",
    "compiling",
    "completed",
    "failed"
]

class StatusSteps(TypedDict):
    """状态步骤结构"""
    outline_generation: bool
    content_generation: bool
    ppt_compilation: bool
    upload_complete: bool

class PresentationStatusData(TypedDict):
    """演示文稿状态数据结构"""
    presentation_id: str
    topic: str
    page_count: int
    status: PresentationStatus
    progress: int
    created_at: str
    updated_at: str
    estimated_completion_time: Optional[str]
    current_step: str
    steps: StatusSteps
    error_info: Optional[Dict[str, Any]]

# API请求/响应类型
class GenerateRequest(TypedDict):
    """生成请求数据结构"""
    topic: str
    page_count: Optional[int]
    style: Optional[str]

class GenerateResponse(TypedDict):
    """生成响应数据结构"""
    presentation_id: str
    status: str
    topic: str
    page_count: int
    estimated_completion_time: int

class StatusResponse(TypedDict):
    """状态查询响应数据结构"""
    presentation_id: str
    status: PresentationStatus
    progress: int
    current_step: str
    steps: StatusSteps
    error_info: Optional[Dict[str, Any]]

class DownloadResponse(TypedDict):
    """下载响应数据结构"""
    presentation_id: str
    download_url: str
    expires_in: int

class ErrorResponse(TypedDict):
    """错误响应数据结构"""
    error: str
    error_code: str
    timestamp: str
    details: Optional[Dict[str, Any]]

# AWS相关类型
class BedrockRequest(TypedDict):
    """Bedrock请求结构"""
    prompt: str
    max_tokens: int
    temperature: float
    top_p: float
    top_k: int
    stop_sequences: List[str]

class BedrockResponse(TypedDict):
    """Bedrock响应结构"""
    completion: str

# Lambda事件类型
class APIGatewayEvent(TypedDict):
    """API Gateway事件结构"""
    httpMethod: str
    path: str
    pathParameters: Optional[Dict[str, str]]
    queryStringParameters: Optional[Dict[str, str]]
    headers: Optional[Dict[str, str]]
    body: Optional[str]
    requestContext: Dict[str, Any]

class LambdaContext:
    """Lambda上下文类型（简化版）"""
    function_name: str
    function_version: str
    invoked_function_arn: str
    memory_limit_in_mb: int
    remaining_time_in_millis: int
    log_group_name: str
    log_stream_name: str
    aws_request_id: str

# S3相关类型
class S3Object(TypedDict):
    """S3对象信息结构"""
    Key: str
    LastModified: datetime
    ETag: str
    Size: int
    StorageClass: str

class S3Metadata(TypedDict):
    """S3对象元数据结构"""
    ContentLength: int
    ContentType: str
    LastModified: datetime
    ETag: str
    Metadata: Dict[str, str]

# 配置类型
class ConfigData(TypedDict):
    """配置数据结构"""
    s3_bucket: str
    aws_region: str
    bedrock_model_id: str
    log_level: str
    environment: str

# 验证相关类型
class ValidationResult(TypedDict):
    """验证结果结构"""
    is_valid: bool
    error_message: Optional[str]
    field: Optional[str]

# 重试相关类型
class RetryConfig(TypedDict):
    """重试配置结构"""
    max_retries: int
    backoff_base: float
    initial_delay: float
    max_delay: float

# 分页类型
class PaginationParams(TypedDict):
    """分页参数结构"""
    page: int
    per_page: int

class PaginatedResponse(TypedDict):
    """分页响应结构"""
    items: List[Any]
    page: int
    per_page: int
    total: int
    has_next: bool
    has_prev: bool

# 工具类型
ContentData = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
JSONSerializable = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]