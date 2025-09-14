"""
演讲者备注相关异常定义
"""


class SpeakerNotesException(Exception):
    """演讲者备注基础异常"""
    pass


class BedrockServiceError(SpeakerNotesException):
    """Bedrock服务错误"""
    pass


class ValidationError(SpeakerNotesException):
    """验证错误"""
    pass


class PPTXIntegrationError(SpeakerNotesException):
    """PPTX集成错误"""
    pass


class GenerationTimeoutError(SpeakerNotesException):
    """生成超时错误"""
    pass


class ContentRelevanceError(SpeakerNotesException):
    """内容相关性错误"""
    pass