"""
图片生成服务的异常定义
"""

class ImageGenerationException(Exception):
    """图片生成基础异常"""
    pass

class ModelNotAvailableException(ImageGenerationException):
    """模型不可用异常"""
    pass

class ImageGenerationFailedException(ImageGenerationException):
    """图片生成失败异常"""
    pass

class S3UploadException(ImageGenerationException):
    """S3上传失败异常"""
    pass

class InvalidPromptException(ImageGenerationException):
    """无效提示词异常"""
    pass
class ImageProcessingError(Exception): pass
class NovaServiceError(Exception): pass
class PlaceholderFallbackWarning(Warning): pass

# 添加缺失的异常类
class ImageGeneratorError(ImageGenerationException):
    """图片生成器错误"""
    pass

class S3OperationError(ImageGenerationException):
    """S3操作错误"""
    pass

class ValidationError(ImageGenerationException):
    """验证错误"""
    pass
