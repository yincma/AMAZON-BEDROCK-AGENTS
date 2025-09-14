"""
请求验证器 - 验证API请求的输入数据
"""
from typing import Dict, Tuple, Optional, Any
import re
import json
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class RequestValidator:
    """请求验证器"""

    @staticmethod
    def validate_generate_request(body: Dict) -> Tuple[bool, Optional[str]]:
        """验证生成请求

        Args:
            body: 请求体字典

        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 检查必需字段
            if not body:
                return False, "Request body is required"

            if not body.get('topic'):
                return False, "Topic is required"

            topic = body['topic']

            # 验证topic格式
            if not isinstance(topic, str):
                return False, "Topic must be a string"

            topic = topic.strip()
            if len(topic) < 3:
                return False, "Topic must be at least 3 characters"

            if len(topic) > 200:
                return False, "Topic must be less than 200 characters"

            # 检查可选的page_count
            page_count = body.get('page_count', 5)
            if page_count is not None:
                if not isinstance(page_count, int):
                    return False, "Page count must be an integer"

                if page_count < 3 or page_count > 20:
                    return False, "Page count must be between 3 and 20"

            # 检查slides_count (兼容性)
            slides_count = body.get('slides_count')
            if slides_count is not None:
                if not isinstance(slides_count, int):
                    return False, "Slides count must be an integer"

                if slides_count < 3 or slides_count > 20:
                    return False, "Slides count must be between 3 and 20"

            # 检查style（可选）
            style = body.get('style')
            if style is not None:
                if not isinstance(style, str):
                    return False, "Style must be a string"

                valid_styles = ['professional', 'casual', 'academic', 'creative']
                if style not in valid_styles:
                    return False, f"Style must be one of: {', '.join(valid_styles)}"

            # 检查是否包含恶意内容
            if RequestValidator.contains_malicious_content(topic):
                return False, "Topic contains invalid content"

            # 检查其他可选字段的恶意内容
            if style and RequestValidator.contains_malicious_content(style):
                return False, "Style contains invalid content"

            return True, None

        except Exception as e:
            logger.error(f"验证生成请求时出错: {str(e)}")
            return False, "Request validation failed"

    @staticmethod
    def validate_presentation_id(presentation_id: str) -> bool:
        """验证presentation_id格式

        Args:
            presentation_id: 演示文稿ID

        Returns:
            是否有效的UUID格式
        """
        if not presentation_id:
            return False

        if not isinstance(presentation_id, str):
            return False

        # UUID格式验证（支持带连字符和不带连字符的格式）
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$',
            re.IGNORECASE
        )

        return bool(uuid_pattern.match(presentation_id))

    @staticmethod
    def contains_malicious_content(text: str) -> bool:
        """检查恶意内容

        Args:
            text: 要检查的文本

        Returns:
            是否包含恶意内容
        """
        if not isinstance(text, str):
            return True

        # 简单的黑名单检查
        blacklist = [
            '<script',
            '</script',
            'javascript:',
            'onerror=',
            'onclick=',
            'onload=',
            'eval(',
            'exec(',
            'system(',
            'shell_exec',
            'passthru',
            '<iframe',
            'data:text/html',
            'vbscript:',
            'file://',
            'ftp://',
            '../',
            '..\\',
            'rm -rf',
            'DROP TABLE',
            'DELETE FROM',
            'INSERT INTO',
            'UPDATE SET',
            '--',
            '/*',
            '*/',
            'union select',
            'concat(',
            'char('
        ]

        text_lower = text.lower()
        return any(word in text_lower for word in blacklist)

    @staticmethod
    def validate_json_request(request_body: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """验证JSON请求体

        Args:
            request_body: JSON字符串

        Returns:
            (是否有效, 解析后的字典, 错误信息)
        """
        try:
            if not request_body:
                return False, None, "Request body is empty"

            if not isinstance(request_body, str):
                return False, None, "Request body must be a string"

            # 检查JSON大小限制（1MB）
            if len(request_body.encode('utf-8')) > 1024 * 1024:
                return False, None, "Request body too large (max 1MB)"

            # 解析JSON
            try:
                data = json.loads(request_body)
            except json.JSONDecodeError as e:
                return False, None, f"Invalid JSON format: {str(e)}"

            # 验证JSON是否为字典
            if not isinstance(data, dict):
                return False, None, "Request body must be a JSON object"

            return True, data, None

        except Exception as e:
            logger.error(f"JSON验证失败: {str(e)}")
            return False, None, "JSON validation failed"

    @staticmethod
    def sanitize_text(text: str) -> str:
        """清理文本内容

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        if not isinstance(text, str):
            return ""

        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)

        # 移除危险字符
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\n', '\r', '\t']
        for char in dangerous_chars:
            text = text.replace(char, ' ')

        # 压缩多个空格为单个空格
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    @staticmethod
    def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
        """验证文件扩展名

        Args:
            filename: 文件名
            allowed_extensions: 允许的扩展名列表

        Returns:
            是否为允许的扩展名
        """
        if not filename or not isinstance(filename, str):
            return False

        # 获取文件扩展名
        if '.' not in filename:
            return False

        extension = filename.split('.')[-1].lower()
        return extension in [ext.lower() for ext in allowed_extensions]

    @staticmethod
    def validate_content_type(content_type: str, allowed_types: list) -> bool:
        """验证内容类型

        Args:
            content_type: 内容类型
            allowed_types: 允许的类型列表

        Returns:
            是否为允许的内容类型
        """
        if not content_type or not isinstance(content_type, str):
            return False

        content_type = content_type.lower().split(';')[0].strip()
        return content_type in [t.lower() for t in allowed_types]

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """验证API密钥格式

        Args:
            api_key: API密钥

        Returns:
            是否为有效格式
        """
        if not api_key or not isinstance(api_key, str):
            return False

        # 简单的格式验证：至少32个字符，只包含字母数字和连字符
        if len(api_key) < 32:
            return False

        pattern = re.compile(r'^[A-Za-z0-9\-_]+$')
        return bool(pattern.match(api_key))

    @staticmethod
    def validate_pagination_params(page: Any, per_page: Any) -> Tuple[bool, Optional[str], Optional[int], Optional[int]]:
        """验证分页参数

        Args:
            page: 页码
            per_page: 每页数量

        Returns:
            (是否有效, 错误信息, 页码, 每页数量)
        """
        try:
            # 默认值
            default_page = 1
            default_per_page = 10

            # 验证页码
            if page is None:
                page = default_page
            else:
                try:
                    page = int(page)
                    if page < 1:
                        return False, "Page must be greater than 0", None, None
                    if page > 1000:
                        return False, "Page must be less than 1000", None, None
                except (ValueError, TypeError):
                    return False, "Page must be an integer", None, None

            # 验证每页数量
            if per_page is None:
                per_page = default_per_page
            else:
                try:
                    per_page = int(per_page)
                    if per_page < 1:
                        return False, "Per page must be greater than 0", None, None
                    if per_page > 100:
                        return False, "Per page must be less than 100", None, None
                except (ValueError, TypeError):
                    return False, "Per page must be an integer", None, None

            return True, None, page, per_page

        except Exception as e:
            logger.error(f"分页参数验证失败: {str(e)}")
            return False, "Pagination validation failed", None, None


# 独立验证函数，供测试使用
def validate_generate_request(body: Dict) -> Tuple[bool, Optional[str]]:
    """验证生成请求（独立函数）"""
    return RequestValidator.validate_generate_request(body)


def validate_presentation_id(presentation_id: str) -> bool:
    """验证演示文稿ID（独立函数）"""
    return RequestValidator.validate_presentation_id(presentation_id)


def sanitize_request(request_data: Dict) -> Dict:
    """清理请求数据（独立函数）"""
    if not isinstance(request_data, dict):
        return {}

    sanitized = {}
    for key, value in request_data.items():
        if isinstance(value, str):
            sanitized[key] = RequestValidator.sanitize_text(value)
        elif isinstance(value, (int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, dict):
            sanitized[key] = sanitize_request(value)
        elif isinstance(value, list):
            sanitized[key] = [
                RequestValidator.sanitize_text(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def parse_request_body(body: str) -> Dict:
    """解析请求体（独立函数）"""
    is_valid, data, error = RequestValidator.validate_json_request(body)
    if not is_valid:
        raise ValueError(error)
    return data