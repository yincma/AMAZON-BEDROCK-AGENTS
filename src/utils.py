"""
工具函数 - 提供重试、日志等通用功能
"""
import time
import logging
from functools import wraps
import json

logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries=3, backoff_factor=2):
    """带指数退避的重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"最终重试失败: {str(e)}")
                        raise
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"尝试 {attempt + 1} 失败, {wait_time}秒后重试: {str(e)}")
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator

def validate_json_response(response_text):
    """验证并解析JSON响应"""
    try:
        # 尝试直接解析
        return json.loads(response_text)
    except json.JSONDecodeError:
        # 尝试从可能的包装中提取JSON
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"无法解析JSON响应: {response_text[:200]}...")

def clean_text(text):
    """清理文本，去除多余的空白和特殊字符"""
    if not text:
        return ""
    # 去除多余空白
    text = ' '.join(text.split())
    # 去除特殊字符
    text = text.replace('\u200b', '').replace('\ufeff', '')
    return text.strip()