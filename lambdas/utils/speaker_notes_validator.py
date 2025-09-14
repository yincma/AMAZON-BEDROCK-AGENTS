"""
演讲者备注验证器
验证生成的演讲者备注是否符合要求
"""

import logging

logger = logging.getLogger(__name__)

# 常量定义
SPEAKER_NOTE_MIN_LENGTH = 100
SPEAKER_NOTE_MAX_LENGTH = 200


class SpeakerNotesValidator:
    """演讲者备注验证器类"""

    def __init__(self):
        """初始化验证器"""
        self.min_length = SPEAKER_NOTE_MIN_LENGTH
        self.max_length = SPEAKER_NOTE_MAX_LENGTH

    def validate_length(self, notes: str) -> bool:
        """
        验证演讲者备注长度是否符合要求

        Args:
            notes: 演讲者备注文本

        Returns:
            bool: 长度是否在100-200字之间
        """
        if not notes:
            return False

        # 中文字符计算：使用实际字符数而不是字节数
        notes_text = notes.strip()
        # 移除空格和标点符号用于计算长度
        notes_for_count = notes_text.replace(' ', '').replace('\n', '').replace('\t', '')
        notes_length = len(notes_for_count)

        # 检查是否在范围内
        is_valid = self.min_length <= notes_length <= self.max_length

        if not is_valid:
            logger.warning(f"备注长度不符合要求: {notes_length}字 (要求: {self.min_length}-{self.max_length}字)")

        return is_valid

    def validate_content(self, notes: str, slide_data: dict) -> bool:
        """
        验证演讲者备注内容的相关性

        Args:
            notes: 演讲者备注
            slide_data: 幻灯片数据

        Returns:
            bool: 内容是否相关
        """
        if not notes:
            return False

        # 检查是否包含关键词
        title = slide_data.get('title', '')
        content = slide_data.get('content', [])

        # 提取关键词
        keywords = []
        if title:
            # 简单的关键词提取
            keywords.extend(title.split())

        for item in content:
            if item:
                # 提取内容中的关键词
                words = item.split()[:5]  # 取前5个词
                keywords.extend(words)

        # 检查备注中是否包含关键词
        notes_lower = notes.lower()
        relevance_count = 0

        for keyword in keywords:
            if len(keyword) > 2 and keyword.lower() in notes_lower:
                relevance_count += 1

        # 至少包含20%的关键词
        relevance_ratio = relevance_count / len(keywords) if keywords else 0
        return relevance_ratio >= 0.2

    def validate_quality(self, notes: str) -> bool:
        """
        验证演讲者备注的质量

        Args:
            notes: 演讲者备注

        Returns:
            bool: 质量是否合格
        """
        if not notes:
            return False

        # 检查是否包含实质内容
        notes = notes.strip()

        # 不应该是纯标点或纯数字
        if notes.replace(' ', '').replace('。', '').replace('，', '').replace('.', '').replace(',', '') == '':
            return False

        # 应该包含至少一个句子
        has_sentence = '。' in notes or '.' in notes or '！' in notes or '!' in notes

        return has_sentence

    def validate_all(self, notes: str, slide_data: dict) -> dict:
        """
        执行所有验证

        Args:
            notes: 演讲者备注
            slide_data: 幻灯片数据

        Returns:
            dict: 验证结果
        """
        return {
            'length_valid': self.validate_length(notes),
            'content_valid': self.validate_content(notes, slide_data),
            'quality_valid': self.validate_quality(notes),
            'is_valid': all([
                self.validate_length(notes),
                self.validate_content(notes, slide_data),
                self.validate_quality(notes)
            ])
        }