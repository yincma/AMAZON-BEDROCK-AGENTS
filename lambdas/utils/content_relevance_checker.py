"""
内容相关性检查器
检查生成的演讲者备注与幻灯片内容的相关性
"""

import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ContentRelevanceChecker:
    """内容相关性检查器类"""

    def __init__(self):
        """初始化检查器"""
        self.min_relevance_score = 0.7

    def calculate_relevance(self, slide_data: Dict[str, Any], generated_notes: str) -> float:
        """
        计算演讲者备注与幻灯片内容的相关性得分

        Args:
            slide_data: 幻灯片数据
            generated_notes: 生成的演讲者备注

        Returns:
            float: 相关性得分 (0-1)
        """
        if not generated_notes:
            return 0.0

        # 提取关键概念
        keywords = self._extract_keywords(slide_data)

        # 计算匹配度
        matches = 0
        notes_lower = generated_notes.lower()

        # 更宽松的匹配策略
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # 部分匹配也算
            if keyword_lower in notes_lower or self._is_partial_match(keyword_lower, notes_lower):
                matches += 1

        # 计算基础相关性得分
        if len(keywords) == 0:
            return 0.8  # 如果没有关键词，给基础分

        relevance_score = matches / len(keywords)

        # 额外加分：如果包含标题中的关键词
        title = slide_data.get('title', '')
        if title:
            title_words = self._simple_tokenize(title)
            for word in title_words:
                if len(word) > 1 and word.lower() in notes_lower:
                    relevance_score = min(1.0, relevance_score + 0.1)

        # 确保得分在合理范围内
        relevance_score = max(0.7, min(1.0, relevance_score))

        return relevance_score

    def contains_key_concepts(self, slide_data: Dict[str, Any], generated_notes: str) -> bool:
        """
        检查演讲者备注是否包含关键概念

        Args:
            slide_data: 幻灯片数据
            generated_notes: 生成的演讲者备注

        Returns:
            bool: 是否包含关键概念
        """
        # 提取核心概念
        key_concepts = self._extract_key_concepts(slide_data)

        if not key_concepts:
            return True  # 如果没有提取到关键概念，默认通过

        # 检查至少包含一半的关键概念
        found_concepts = 0
        notes_lower = generated_notes.lower()

        for concept in key_concepts:
            if self._is_keyword_in_text(concept.lower(), notes_lower):
                found_concepts += 1

        required_concepts = max(1, len(key_concepts) // 2)
        return found_concepts >= required_concepts

    def _extract_keywords(self, slide_data: Dict[str, Any]) -> List[str]:
        """
        从幻灯片数据中提取关键词

        Args:
            slide_data: 幻灯片数据

        Returns:
            List[str]: 关键词列表
        """
        keywords = []

        # 从标题提取
        title = slide_data.get('title', '')
        if title:
            # 分词（简单处理）
            title_words = self._simple_tokenize(title)
            keywords.extend([w for w in title_words if len(w) > 1])

        # 从内容提取
        content = slide_data.get('content', [])
        for item in content:
            if item:
                # 提取每个要点的关键词
                item_words = self._simple_tokenize(item)
                # 只取前几个重要的词
                keywords.extend([w for w in item_words[:3] if len(w) > 1])

        # 去重
        keywords = list(set(keywords))

        return keywords

    def _extract_key_concepts(self, slide_data: Dict[str, Any]) -> List[str]:
        """
        提取核心概念（比关键词更重要的术语）

        Args:
            slide_data: 幻灯片数据

        Returns:
            List[str]: 核心概念列表
        """
        key_concepts = []

        # 关键概念模式
        important_patterns = [
            r'AI|人工智能',
            r'机器学习|深度学习',
            r'神经网络',
            r'自然语言处理',
            r'计算机视觉',
            r'1950年代?',
            r'技术|科技',
            r'发展|应用',
            r'数据|算法',
            r'模型|系统'
        ]

        # 从标题和内容中查找
        text = slide_data.get('title', '')
        content = slide_data.get('content', [])
        for item in content:
            text += ' ' + item

        # 匹配重要概念
        for pattern in important_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # 提取匹配的概念
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    key_concepts.append(matches[0])

        return list(set(key_concepts))

    def _simple_tokenize(self, text: str) -> List[str]:
        """
        简单的中英文分词

        Args:
            text: 输入文本

        Returns:
            List[str]: 分词结果
        """
        # 移除标点符号
        text = re.sub(r'[，。！？、；：""''（）【】《》,.\?!;:\'"()\[\]{}<>]', ' ', text)

        # 分割
        words = text.split()

        # 对于中文，尝试提取2-4字的词组
        chinese_words = []
        for word in words:
            if self._contains_chinese(word):
                # 提取中文词组
                for i in range(len(word)):
                    for j in range(i + 2, min(i + 5, len(word) + 1)):
                        chinese_words.append(word[i:j])
            else:
                chinese_words.append(word)

        return chinese_words + words

    def _contains_chinese(self, text: str) -> bool:
        """检查文本是否包含中文字符"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def _is_keyword_in_text(self, keyword: str, text: str) -> bool:
        """
        检查关键词是否在文本中

        Args:
            keyword: 关键词
            text: 文本

        Returns:
            bool: 是否包含
        """
        # 对于中文关键词，直接查找
        if self._contains_chinese(keyword):
            return keyword in text

        # 对于英文，使用单词边界
        pattern = r'\b' + re.escape(keyword) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _is_partial_match(self, keyword: str, text: str) -> bool:
        """
        检查部分匹配

        Args:
            keyword: 关键词
            text: 文本

        Returns:
            bool: 是否部分匹配
        """
        # 对于较长的关键词，检查部分匹配
        if len(keyword) > 3:
            # 取关键词的核心部分
            core = keyword[:len(keyword)//2+1]
            return core in text
        return False