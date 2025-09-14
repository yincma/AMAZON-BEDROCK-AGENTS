"""
演讲者备注生成控制器
负责为PPT幻灯片生成演讲者备注
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# 配置常量
SPEAKER_NOTE_MIN_LENGTH = 100
SPEAKER_NOTE_MAX_LENGTH = 200


class SpeakerNotesGenerator:
    """演讲者备注生成器类"""

    def __init__(self, bedrock_client=None, language="zh-CN", use_fallback=False):
        """
        初始化演讲者备注生成器

        Args:
            bedrock_client: Bedrock客户端实例
            language: 生成语言 (zh-CN 或 en)
            use_fallback: 是否启用fallback机制
        """
        self.bedrock_client = bedrock_client
        if not self.bedrock_client:
            try:
                self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
            except:
                # 如果无法创建客户端，使用fallback模式
                self.use_fallback = True
                self.bedrock_client = None
        self.language = language
        self.use_fallback = use_fallback or (self.bedrock_client is None)
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    def generate_notes(self, slide_data: Dict[str, Any]) -> str:
        """
        为单张幻灯片生成演讲者备注

        Args:
            slide_data: 幻灯片数据，包含title和content

        Returns:
            str: 生成的演讲者备注（100-200字）
        """
        # 处理空内容的情况
        content = slide_data.get('content', [])
        if not content or all(not item for item in content):
            return self._generate_fallback_notes(slide_data)

        # 处理超长内容的情况 - 直接使用fallback生成合适长度的备注
        total_content = ''.join(str(c) for c in content)
        if len(total_content) > 500:  # 内容过长时使用fallback
            return self._generate_fallback_notes(slide_data)

        try:
            # 构建提示词
            prompt = self._build_prompt(slide_data)

            # 调用Bedrock生成备注
            response = self._invoke_bedrock(prompt)

            # 提取和验证备注
            speaker_notes = self._extract_notes(response)

            # 确保长度符合要求
            speaker_notes = self._ensure_length(speaker_notes, slide_data)

            return speaker_notes

        except Exception as e:
            logger.error(f"生成演讲者备注失败: {str(e)}")
            if self.use_fallback:
                self._used_fallback = True  # 标记使用了fallback
                return self._generate_fallback_notes(slide_data)
            raise

    def _build_prompt(self, slide_data: Dict[str, Any]) -> str:
        """构建生成演讲者备注的提示词 - 咨询顾问风格"""
        title = slide_data.get('title', '')
        content = slide_data.get('content', [])
        slide_number = slide_data.get('slide_number', 1)
        total_slides = slide_data.get('total_slides', 10)

        # 根据语言选择提示词
        if self.language == "en":
            prompt = f"""As a senior strategy consultant, prepare professional speaker notes for this presentation slide.

Slide Information:
- Title: {title}
- Position: Slide {slide_number} of {total_slides}
- Key Points:
{chr(10).join(f"  • {item}" for item in content)}

Professional Speaker Script (100-200 words):

Structure your notes with:
1. Opening transition linking from previous slide (if not first slide)
2. Core message delivery with business impact
3. Supporting evidence or examples
4. Bridge to next slide (if not last slide)

Use confident, action-oriented language that demonstrates expertise while remaining accessible.

Speaker Notes:"""
        else:
            prompt = f"""作为资深战略咨询顾问，为以下演示页面准备专业的演讲脚本。

页面信息：
- 标题：{title}
- 位置：第{slide_number}页，共{total_slides}页
- 核心要点：
{chr(10).join(f"  • {item}" for item in content)}

专业演讲脚本（100-200字）：

脚本结构要求：
1. 开场衔接：自然过渡（如非首页）
2. 核心论述：强调商业价值和关键洞察
3. 支撑论据：提供数据支撑或行业案例
4. 过渡引导：预告下一页内容（如非末页）

语言风格：
- 专业但不失亲和力
- 使用主动语态和行动导向表述
- 包含"基于我们的分析"、"这意味着"等咨询常用语

演讲者备注："""

        return prompt

    def _invoke_bedrock(self, prompt: str) -> Dict[str, Any]:
        """调用Bedrock API生成内容"""
        # 如果没有客户端，抛出异常让fallback处理
        if not self.bedrock_client:
            raise Exception("Bedrock客户端不可用")

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )

        response_body = json.loads(response['body'].read())
        return response_body

    def _extract_notes(self, response: Dict[str, Any]) -> str:
        """从Bedrock响应中提取演讲者备注"""
        if 'content' in response and response['content']:
            return response['content'][0].get('text', '')
        elif 'completion' in response:
            return response['completion']
        else:
            raise ValueError("无法从响应中提取演讲者备注")

    def _ensure_length(self, notes: str, slide_data: Dict[str, Any]) -> str:
        """确保演讲者备注长度在100-200字之间"""
        notes = notes.strip()

        # 如果太短，扩展内容
        if len(notes) < SPEAKER_NOTE_MIN_LENGTH:
            title = slide_data.get('title', '')
            if self.language == "en":
                extension = f" When presenting this slide about {title}, emphasize the key points and provide relevant examples to engage the audience."
            else:
                extension = f"在展示关于{title}的这张幻灯片时，请强调关键要点并提供相关示例以吸引观众的注意力。"
            notes = notes + extension

        # 如果太长，截断但保持完整句子
        if len(notes) > SPEAKER_NOTE_MAX_LENGTH:
            # 找到最后一个句号的位置
            sentences = notes[:SPEAKER_NOTE_MAX_LENGTH]
            last_period = max(
                sentences.rfind('。'),
                sentences.rfind('.'),
                sentences.rfind('！'),
                sentences.rfind('!'),
                sentences.rfind('？'),
                sentences.rfind('?')
            )
            if last_period > SPEAKER_NOTE_MIN_LENGTH:
                notes = sentences[:last_period + 1]
            else:
                notes = sentences[:SPEAKER_NOTE_MAX_LENGTH]

        return notes

    def _generate_fallback_notes(self, slide_data: Dict[str, Any]) -> str:
        """生成fallback演讲者备注"""
        title = slide_data.get('title', '幻灯片')
        content = slide_data.get('content', [])

        # 处理空内容的特殊情况
        if not content or all(not item for item in content):
            if self.language == "en":
                notes = f"This slide '{title}' serves as a visual presentation element. Take this opportunity to engage with your audience through discussion, provide additional context about the topic, share relevant experiences, and answer any questions they may have. Use this moment to reinforce key messages and ensure audience understanding of the concepts presented."
            else:
                notes = f"这张标题为'{title}'的空白幻灯片可以作为视觉展示元素。请利用这个机会与观众进行互动交流，提供关于主题的额外背景信息，分享相关经验，并回答观众可能有的任何问题。使用这个时刻来强化关键信息，确保观众理解所呈现的概念。您可以通过举例说明、案例分析或实际应用来丰富演讲内容。"
            return notes[:SPEAKER_NOTE_MAX_LENGTH]

        if self.language == "en":
            notes = f"This slide about {title} covers important points. "
            if content:
                # 清理特殊字符
                clean_content = str(content[0]).replace('&', 'and').replace('@', 'at').replace('$', 'dollar')[:50]
                notes += f"Focus on explaining: {clean_content}. "
            notes += "Provide relevant examples and engage with the audience through questions or discussions to ensure understanding."
        else:
            notes = f"这张关于{title}的幻灯片涵盖了重要的观点。"
            if content:
                # 清理特殊字符
                clean_content = str(content[0]).replace('&', '和').replace('@', '在').replace('$', '元')[:50]
                notes += f"重点解释：{clean_content}。"
            notes += "提供相关的例子，并通过提问或讨论与观众互动，确保他们理解关键概念。建议使用实际案例来说明理论概念。"

        return self._ensure_length(notes, slide_data)

    def batch_generate_notes(self, slides_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量生成多张幻灯片的演讲者备注

        Args:
            slides_data: 幻灯片数据列表

        Returns:
            List[Dict]: 包含slide_number和speaker_notes的结果列表
        """
        results = []

        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_slide = {
                executor.submit(self.generate_notes, slide): slide
                for slide in slides_data
            }

            for future in as_completed(future_to_slide):
                slide = future_to_slide[future]
                try:
                    speaker_notes = future.result(timeout=5)
                    results.append({
                        "slide_number": slide.get("slide_number", 0),
                        "speaker_notes": speaker_notes
                    })
                except Exception as e:
                    logger.error(f"批量生成失败: {str(e)}")
                    # 使用fallback
                    results.append({
                        "slide_number": slide.get("slide_number", 0),
                        "speaker_notes": self._generate_fallback_notes(slide)
                    })

        # 按slide_number排序
        results.sort(key=lambda x: x["slide_number"])
        return results

    def generate_for_presentation(self, presentation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        为整个演示文稿生成演讲者备注

        Args:
            presentation_data: 演示文稿数据

        Returns:
            Dict: 包含所有演讲者备注的演示文稿数据
        """
        slides = presentation_data.get('slides', [])

        # 批量生成备注
        notes_results = self.batch_generate_notes(slides)

        # 将备注添加到原始数据
        for slide, notes_result in zip(slides, notes_results):
            slide['speaker_notes'] = notes_result['speaker_notes']

        presentation_data['speaker_notes_included'] = True
        return presentation_data

    def add_notes_to_ppt(self, presentation, slide_index: int, speaker_notes: str):
        """
        将演讲者备注添加到PPT文件

        Args:
            presentation: python-pptx的Presentation对象
            slide_index: 幻灯片索引
            speaker_notes: 演讲者备注内容
        """
        try:
            slide = presentation.slides[slide_index]
            # 获取或创建notes slide
            if not slide.has_notes_slide:
                slide.notes_slide
            # 设置备注文本
            slide.notes_slide.notes_text_frame.text = speaker_notes
        except Exception as e:
            logger.error(f"添加演讲者备注到PPT失败: {str(e)}")
            raise

    def generate_notes_with_fallback(self, slide_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用fallback机制生成演讲者备注

        Args:
            slide_data: 幻灯片数据

        Returns:
            Dict: 包含speaker_notes和fallback标志的结果
        """
        # 临时设置use_fallback为True以确保fallback
        original_use_fallback = self.use_fallback
        self.use_fallback = True

        try:
            speaker_notes = self.generate_notes(slide_data)
            # 如果成功但使用了fallback（在generate_notes内部）
            if hasattr(self, '_used_fallback'):
                return {
                    "speaker_notes": speaker_notes,
                    "fallback": True
                }
            return {
                "speaker_notes": speaker_notes,
                "fallback": False
            }
        except Exception as e:
            logger.warning(f"主服务失败，使用fallback: {str(e)}")
            speaker_notes = self._generate_fallback_notes(slide_data)
            return {
                "speaker_notes": speaker_notes,
                "fallback": True
            }
        finally:
            self.use_fallback = original_use_fallback


def lambda_handler(event, context):
    """Lambda函数入口"""
    try:
        # 获取请求数据
        slide_data = event.get('slide_data', {})
        language = event.get('language', 'zh-CN')

        # 创建生成器
        generator = SpeakerNotesGenerator(language=language)

        # 生成演讲者备注
        speaker_notes = generator.generate_notes(slide_data)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'speaker_notes': speaker_notes,
                'language': language
            })
        }

    except Exception as e:
        logger.error(f"Lambda执行失败: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }