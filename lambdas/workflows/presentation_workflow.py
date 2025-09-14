"""
演示文稿工作流
包含演讲者备注的完整PPT生成流程
"""

import json
import logging
from typing import Dict, Any
import boto3

from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

logger = logging.getLogger(__name__)


class PresentationWorkflow:
    """演示文稿工作流类"""

    def __init__(self, bedrock_client=None, s3_client=None):
        """
        初始化工作流

        Args:
            bedrock_client: Bedrock客户端
            s3_client: S3客户端
        """
        self.bedrock_client = bedrock_client or boto3.client('bedrock-runtime', region_name='us-east-1')
        self.s3_client = s3_client or boto3.client('s3')
        self.speaker_notes_generator = SpeakerNotesGenerator(bedrock_client=self.bedrock_client)

    def generate_presentation_with_notes(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成包含演讲者备注的演示文稿

        Args:
            request_data: 请求数据，包含topic, slide_count等

        Returns:
            Dict: 生成结果
        """
        try:
            presentation_id = request_data.get('presentation_id')
            topic = request_data.get('topic')
            slide_count = request_data.get('slide_count', 5)
            include_speaker_notes = request_data.get('include_speaker_notes', True)
            language = request_data.get('language', 'zh-CN')

            # 步骤1: 生成大纲
            outline = self._generate_outline(topic, slide_count)

            # 步骤2: 生成详细内容
            slides_content = self._generate_detailed_content(outline)

            # 步骤3: 如果需要，生成演讲者备注
            if include_speaker_notes:
                slides_with_notes = self._add_speaker_notes(slides_content, language)
            else:
                slides_with_notes = slides_content

            # 步骤4: 生成PPT文件
            ppt_url = self._generate_ppt_file(presentation_id, slides_with_notes)

            # 构建响应
            result = {
                "status": "completed",
                "presentation_id": presentation_id,
                "presentation_url": ppt_url,
                "speaker_notes_included": include_speaker_notes,
                "presentation_data": {
                    "title": topic,
                    "slides": slides_with_notes,
                    "total_slides": len(slides_with_notes)
                }
            }

            return result

        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "presentation_id": request_data.get('presentation_id')
            }

    def _generate_outline(self, topic: str, slide_count: int) -> Dict[str, Any]:
        """生成演示文稿大纲"""
        # 简化的大纲生成逻辑
        outline = {
            "title": topic,
            "slides": []
        }

        # 根据slide_count生成基础大纲
        slide_titles = [
            "引言",
            "核心概念",
            "技术细节",
            "应用案例",
            "总结与展望"
        ]

        for i in range(min(slide_count, len(slide_titles))):
            outline["slides"].append({
                "slide_number": i + 1,
                "title": slide_titles[i],
                "content": [f"{slide_titles[i]}的要点1", f"{slide_titles[i]}的要点2", f"{slide_titles[i]}的要点3"]
            })

        return outline

    def _generate_detailed_content(self, outline: Dict[str, Any]) -> list:
        """生成详细内容"""
        slides = []

        for slide_outline in outline["slides"]:
            slide = {
                "slide_number": slide_outline["slide_number"],
                "title": f"{outline['title']} - {slide_outline['title']}",
                "content": slide_outline["content"]
            }
            slides.append(slide)

        return slides

    def _add_speaker_notes(self, slides: list, language: str) -> list:
        """为每张幻灯片添加演讲者备注"""
        self.speaker_notes_generator.language = language

        # 批量生成备注
        notes_results = self.speaker_notes_generator.batch_generate_notes(slides)

        # 合并备注到幻灯片数据
        for slide, notes_result in zip(slides, notes_results):
            slide['speaker_notes'] = notes_result['speaker_notes']

        return slides

    def _generate_ppt_file(self, presentation_id: str, slides: list) -> str:
        """生成PPT文件并上传到S3"""
        # 这里简化处理，实际应该调用PPT编译服务
        s3_key = f"presentations/{presentation_id}/presentation.pptx"

        # 模拟上传
        self.s3_client.put_object(
            Bucket='ai-ppt-presentations',
            Key=s3_key,
            Body=json.dumps({"slides": slides}),
            ContentType='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )

        # 生成预签名URL
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': 'ai-ppt-presentations', 'Key': s3_key},
            ExpiresIn=3600
        )

        return url