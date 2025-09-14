"""
Content Generator Agent - 内容生成器
负责生成幻灯片内容、演讲者备注
"""
import json
from typing import Dict, Any, List
import boto3
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed

# 统一使用的模型
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"  # inference profile


class ContentGeneratorAgent:
    """内容生成Agent"""

    def __init__(self):
        """初始化Content Generator Agent"""
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1',
            config=Config(read_timeout=30, retries={'max_attempts': 3})
        )

    def generate_slide_content(self, slide_outline: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成单页幻灯片内容

        Args:
            slide_outline: 幻灯片大纲

        Returns:
            完整的幻灯片内容
        """
        title = slide_outline.get("title", "")
        key_points = slide_outline.get("key_points", [])
        page_number = slide_outline.get("page_number", 1)
        slide_type = slide_outline.get("type", "content")

        # 根据类型生成不同的内容
        if slide_type == "title":
            return self._generate_title_slide(title, page_number)
        elif slide_type == "conclusion":
            return self._generate_conclusion_slide(title, key_points, page_number)
        else:
            return self._generate_content_slide(title, key_points, page_number)

    def _generate_title_slide(self, title: str, page_number: int) -> Dict[str, Any]:
        """生成标题页"""
        return {
            "page_number": page_number,
            "type": "title",
            "title": title,
            "subtitle": "AI生成的专业演示文稿",
            "bullet_points": [],
            "speaker_notes": f"欢迎大家，今天我们将讨论{title}这个重要主题。本演示文稿包含了关键要点和深入分析。",
            "suggested_image_type": "photo",
            "content": {
                "main_title": title,
                "subtitle": "AI生成的专业演示文稿",
                "date": "2024"
            }
        }

    def _generate_conclusion_slide(self, title: str, key_points: List[str], page_number: int) -> Dict[str, Any]:
        """生成结论页"""
        bullet_points = key_points if key_points else [
            "回顾了主要概念和关键要点",
            "探讨了实际应用和最佳实践",
            "展望了未来发展方向"
        ]

        speaker_notes = self._generate_speaker_notes({
            "title": title,
            "content": "总结要点：" + "；".join(bullet_points),
            "type": "conclusion"
        })

        return {
            "page_number": page_number,
            "type": "conclusion",
            "title": title,
            "bullet_points": bullet_points,
            "speaker_notes": speaker_notes,
            "suggested_image_type": "diagram",
            "content": {
                "summary": bullet_points,
                "call_to_action": "谢谢大家的关注！"
            }
        }

    def _generate_content_slide(self, title: str, key_points: List[str], page_number: int) -> Dict[str, Any]:
        """生成内容页"""
        # 如果没有提供要点，使用AI生成
        if not key_points or len(key_points) < 3:
            bullet_points = self._generate_bullet_points(title)
        else:
            bullet_points = key_points[:5]  # 最多5个要点

        # 生成演讲者备注
        speaker_notes = self._generate_speaker_notes({
            "title": title,
            "content": "\n".join(bullet_points),
            "type": "content"
        })

        # 确定建议的图片类型
        suggested_image_type = self._suggest_image_type(title, bullet_points)

        return {
            "page_number": page_number,
            "type": "content",
            "title": title,
            "bullet_points": bullet_points,
            "speaker_notes": speaker_notes,
            "suggested_image_type": suggested_image_type,
            "content": {
                "main_points": bullet_points,
                "details": self._generate_details(bullet_points)
            }
        }

    def _generate_bullet_points(self, title: str) -> List[str]:
        """使用AI生成要点"""
        prompt = f"""
        为标题为"{title}"的PPT页面生成3-5个关键要点。

        要求：
        1. 每个要点不超过20个字
        2. 内容专业、简洁
        3. 适合在演示中展示

        直接返回要点列表，每行一个要点。
        """

        response = self._call_bedrock(prompt)
        points = response.strip().split("\n")

        # 清理和格式化
        bullet_points = []
        for point in points:
            cleaned = point.strip().lstrip("•·-*123456789. ")
            if cleaned and len(cleaned) > 5:
                bullet_points.append(cleaned)

        # 确保至少有3个要点
        if len(bullet_points) < 3:
            bullet_points = [
                f"{title}的核心概念",
                f"{title}的主要特点",
                f"{title}的实际应用"
            ]

        return bullet_points[:5]

    def _generate_speaker_notes(self, slide_info: Dict[str, Any]) -> str:
        """生成演讲者备注"""
        title = slide_info.get("title", "")
        content = slide_info.get("content", "")
        slide_type = slide_info.get("type", "content")

        prompt = f"""
        为PPT页面生成演讲者备注。

        页面标题：{title}
        页面内容：{content}
        页面类型：{slide_type}

        要求：
        1. 长度100-200字
        2. 口语化，适合演讲
        3. 补充页面上没有的细节
        4. 包含过渡语句

        直接返回备注内容。
        """

        notes = self._call_bedrock(prompt)

        # 确保长度合适
        if len(notes) < 100:
            notes += f"关于{title}，还有一些重要的补充说明。这些内容对理解整体概念非常重要。"
        elif len(notes) > 200:
            notes = notes[:197] + "..."

        return notes

    def _suggest_image_type(self, title: str, content: List[str]) -> str:
        """建议图片类型"""
        combined_text = title + " " + " ".join(content)
        combined_lower = combined_text.lower()

        # 根据内容关键词判断
        if any(word in combined_lower for word in ["流程", "步骤", "process", "flow", "步", "阶段"]):
            return "diagram"
        elif any(word in combined_lower for word in ["数据", "统计", "比例", "data", "chart", "百分"]):
            return "chart"
        elif any(word in combined_lower for word in ["对比", "比较", "versus", "compare", "区别"]):
            return "diagram"
        else:
            return "photo"

    def _generate_details(self, bullet_points: List[str]) -> Dict[str, str]:
        """为要点生成详细说明"""
        details = {}
        for i, point in enumerate(bullet_points):
            details[f"point_{i+1}"] = f"{point}的详细说明和相关背景信息"
        return details

    def batch_generate(self, outline: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        批量生成多页内容

        Args:
            outline: 包含多页大纲的字典

        Returns:
            所有页面的内容列表
        """
        slides = outline.get("slides", [])
        results = []

        # 使用线程池并行生成
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_slide = {}

            for slide in slides:
                future = executor.submit(self.generate_slide_content, slide)
                future_to_slide[future] = slide

            # 收集结果
            for future in as_completed(future_to_slide):
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    # 如果生成失败，使用默认内容
                    slide = future_to_slide[future]
                    results.append(self._generate_default_content(slide))

        # 按页码排序
        results.sort(key=lambda x: x.get("page_number", 999))
        return results

    def _generate_default_content(self, slide: Dict[str, Any]) -> Dict[str, Any]:
        """生成默认内容（用于错误处理）"""
        return {
            "page_number": slide.get("page_number", 1),
            "type": slide.get("type", "content"),
            "title": slide.get("title", "页面标题"),
            "bullet_points": ["要点1", "要点2", "要点3"],
            "speaker_notes": "这一页的内容非常重要，请大家注意以下几点...",
            "suggested_image_type": "photo",
            "content": {
                "error": "自动生成失败，使用默认内容"
            }
        }

    def _call_bedrock(self, prompt: str) -> str:
        """调用Bedrock模型"""
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }

            response = self.bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(request_body)
            )

            result = json.loads(response['body'].read())
            return result.get("content", [{}])[0].get("text", "")
        except Exception as e:
            print(f"Bedrock调用失败: {e}")
            return ""

    def optimize_content(self, content: Dict[str, Any], feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据反馈优化内容

        Args:
            content: 原始内容
            feedback: 质量检查反馈

        Returns:
            优化后的内容
        """
        # 根据反馈类型进行优化
        if feedback.get("issue") == "missing_content":
            content["bullet_points"] = self._generate_bullet_points(content["title"])
        elif feedback.get("issue") == "too_long":
            content["bullet_points"] = [bp[:50] for bp in content["bullet_points"]]
        elif feedback.get("issue") == "coherence":
            # 重新生成以提高连贯性
            content = self.generate_slide_content({
                "title": content["title"],
                "page_number": content["page_number"],
                "type": content["type"]
            })

        return content


def generate_with_bedrock(prompt: str) -> str:
    """辅助函数：调用Bedrock（用于测试mock）"""
    generator = ContentGeneratorAgent()
    return generator._call_bedrock(prompt)