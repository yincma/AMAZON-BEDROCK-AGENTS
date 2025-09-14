"""
工具函数 - 提供重试、日志等通用功能
"""
import time
import logging
from functools import wraps
import json

logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries=3, backoff_factor=2, initial_delay=1, max_delay=30):
    """带指数退避和抖动的重试装饰器

    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避因子
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import random

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e)

                    # 检查是否是限流错误
                    if 'ThrottlingException' in error_msg or 'Too many requests' in error_msg:
                        if attempt == max_retries - 1:
                            logger.error(f"最终重试失败（限流）: {error_msg}")
                            raise

                        # 计算延迟时间：指数退避 + 抖动
                        base_delay = min(initial_delay * (backoff_factor ** attempt), max_delay)
                        # 添加随机抖动（0.5到1.5倍的基础延迟）
                        jitter = random.uniform(0.5, 1.5)
                        wait_time = base_delay * jitter

                        logger.warning(f"尝试 {attempt + 1} 失败（限流）, {wait_time:.1f}秒后重试")
                        time.sleep(wait_time)
                    else:
                        # 非限流错误，使用较短的重试延迟
                        if attempt == max_retries - 1:
                            logger.error(f"最终重试失败: {error_msg}")
                            raise

                        wait_time = initial_delay * (attempt + 1)
                        logger.warning(f"尝试 {attempt + 1} 失败, {wait_time}秒后重试: {error_msg}")
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