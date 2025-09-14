"""
内容生成器 - 使用Amazon Bedrock Claude生成PPT内容

责任:
- 生成PPT大纲和幻的片内容
- 封装Bedrock API调用逻辑
- 提供内容验证和错误处理

注意: S3操作已分离到独立的服务类中
"""
import json
import boto3
import uuid
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from botocore.exceptions import ClientError

from .config import (
    BEDROCK_MODEL_ID,
    MAX_TOKENS,
    TEMPERATURE,
    DEFAULT_PAGE_COUNT,
    MIN_PAGE_COUNT,
    MAX_PAGE_COUNT,
    S3_BUCKET,
    AWS_REGION
)
from .prompts import OUTLINE_PROMPT, CONTENT_PROMPT
from .utils import retry_with_backoff, validate_json_response, clean_text
from .constants import Config
from .exceptions import (
    ContentGenerationError,
    OutlineGenerationError,
    BedrockAPIError,
    handle_aws_error
)
from .common.s3_service import S3Service
from .types import (
    OutlineData,
    SlideContent,
    PresentationContent,
    BedrockRequest,
    BedrockResponse
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ContentGenerator:
    """使用Bedrock Claude生成PPT内容"""

    def __init__(self,
                 bedrock_client: Optional[Any] = None,
                 s3_service: Optional[S3Service] = None) -> None:
        """初始化内容生成器

        Args:
            bedrock_client: Bedrock客户端（可选，用于测试）
            s3_service: S3服务实例（可选）
        """
        self.bedrock_client = bedrock_client or boto3.client(
            'bedrock-runtime',
            region_name=AWS_REGION
        )
        self.s3_service = s3_service
        self.model_id = BEDROCK_MODEL_ID

    @retry_with_backoff(max_retries=Config.Bedrock.MAX_RETRIES)
    def _invoke_bedrock(self, prompt: str) -> str:
        """调用Bedrock API

        Args:
            prompt: 提示词

        Returns:
            模型响应文本
        """
        try:
            # 构建请求体 - 使用 Claude 3 Messages API 格式
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": Config.Bedrock.DEFAULT_MAX_TOKENS,
                "temperature": Config.Bedrock.DEFAULT_TEMPERATURE,
                "top_p": Config.Bedrock.DEFAULT_TOP_P,
                "top_k": Config.Bedrock.DEFAULT_TOP_K
            }

            # 调用Bedrock
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                contentType=Config.API.CONTENT_TYPE_JSON,
                accept=Config.API.CONTENT_TYPE_JSON,
                body=json.dumps(request_body)
            )

            # 解析响应 - Claude 3 格式
            response_body = json.loads(response['body'].read())
            completion = response_body.get('content', [{}])[0].get('text', '')

            if not completion:
                raise BedrockAPIError(
                    "Bedrock返回了空响应",
                    model_id=self.model_id
                )

            return completion

        except ClientError as e:
            logger.error(f"Bedrock API调用失败: {str(e)}")
            raise handle_aws_error(e)
        except Exception as e:
            logger.error(f"处理Bedrock响应时出错: {str(e)}")
            raise BedrockAPIError(f"处理Bedrock响应时出错: {str(e)}", model_id=self.model_id)

    def generate_outline(self,
                        topic: str,
                        page_count: int = DEFAULT_PAGE_COUNT) -> OutlineData:
        """生成PPT大纲

        Args:
            topic: PPT主题
            page_count: 页数（3-20）

        Returns:
            包含大纲信息的字典
        """
        # 验证页数
        if page_count < Config.PPT.MIN_PAGE_COUNT or page_count > Config.PPT.MAX_PAGE_COUNT:
            raise OutlineGenerationError(
                f"页数必须在{Config.PPT.MIN_PAGE_COUNT}-{Config.PPT.MAX_PAGE_COUNT}之间",
                topic=topic,
                page_count=page_count
            )

        # 构建提示词
        prompt = OUTLINE_PROMPT.format(topic=topic, page_count=page_count)

        # 调用Bedrock
        try:
            response_text = self._invoke_bedrock(prompt)
            # 解析JSON响应
            outline = validate_json_response(response_text)
        except BedrockAPIError:
            raise
        except Exception as e:
            logger.error(f"解析大纲响应失败: {str(e)}")
            # 返回默认大纲结构
            outline = self._create_default_outline(topic, page_count)

        # 确保必要字段存在
        if "title" not in outline:
            outline["title"] = topic
        if "metadata" not in outline:
            outline["metadata"] = {}
        outline["metadata"]["total_slides"] = page_count
        outline["metadata"]["created_at"] = datetime.now().isoformat()

        return outline

    def generate_slide_content(self,
                              outline: OutlineData,
                              include_speaker_notes: bool = True) -> List[SlideContent]:
        """为每页生成详细内容

        Args:
            outline: PPT大纲
            include_speaker_notes: 是否包含演讲者备注

        Returns:
            包含详细内容的幻灯片列表
        """
        slides = []
        topic = outline.get("title", "")

        for slide_info in outline.get("slides", []):
            slide_number = slide_info.get("slide_number", len(slides) + 1)
            slide_title = slide_info.get("title", f"幻灯片 {slide_number}")
            slide_purpose = slide_info.get("content", [""])[0] if slide_info.get("content") else ""

            # 构建提示词
            prompt = CONTENT_PROMPT.format(
                page_title=slide_title,
                page_purpose=slide_purpose,
                topic=topic,
                slide_number=slide_number
            )

            # 调用Bedrock生成内容
            try:
                response_text = self._invoke_bedrock(prompt)
                # 解析响应
                slide_content = validate_json_response(response_text)
            except BedrockAPIError:
                logger.warning(f"幻灯片 {slide_number} Bedrock调用失败，使用默认内容")
                slide_content = self._create_default_slide_content(
                    slide_number, slide_title, slide_info.get("content", [])
                )
            except Exception as e:
                logger.warning(f"幻灯片 {slide_number} 内容解析失败: {str(e)}，使用默认内容")
                slide_content = self._create_default_slide_content(
                    slide_number, slide_title, slide_info.get("content", [])
                )

            # 确保必要字段
            if "slide_number" not in slide_content:
                slide_content["slide_number"] = slide_number
            if "title" not in slide_content:
                slide_content["title"] = slide_title
            if "bullet_points" not in slide_content or len(slide_content["bullet_points"]) < Config.PPT.MIN_BULLET_POINTS:
                slide_content["bullet_points"] = self._ensure_min_bullets(
                    slide_content.get("bullet_points", []),
                    slide_info.get("content", []),
                    Config.PPT.MIN_BULLET_POINTS
                )

            # 添加演讲者备注
            if include_speaker_notes and "speaker_notes" not in slide_content:
                slide_content["speaker_notes"] = f"介绍{slide_title}的主要内容"

            slides.append(slide_content)

        return slides

    def save_to_s3(self,
                   presentation_id: str,
                   content: PresentationContent) -> str:
        """保存内容到S3

        Args:
            presentation_id: 演示文稿ID
            content: 要保存的内容

        Returns:
            S3对象路径

        Raises:
            ContentGenerationError: 当S3服务不可用时
        """
        if not self.s3_service:
            raise ContentGenerationError(
                "S3服务未初始化，无法保存内容",
                stage="content_save"
            )

        try:
            # 构建S3 key
            s3_key = Config.File.CONTENT_FILE_TEMPLATE.format(presentation_id=presentation_id)

            # 使用S3服务上传
            self.s3_service.upload_json(s3_key, content)

            logger.info(f"内容已保存到S3: {s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"保存到S3失败: {str(e)}")
            raise ContentGenerationError(
                f"保存内容到S3失败: {str(e)}",
                stage="content_save"
            )

    def _create_default_outline(self, topic: str, page_count: int) -> OutlineData:
        """创建默认大纲结构"""
        slides = []

        # 标题页
        slides.append({
            "slide_number": 1,
            "title": topic,
            "content": ["介绍主题", "概述内容", "设定期望"]
        })

        # 中间内容页
        for i in range(2, page_count):
            slides.append({
                "slide_number": i,
                "title": f"{topic} - 第{i}部分",
                "content": [f"要点{i}.1", f"要点{i}.2", f"要点{i}.3"]
            })

        # 总结页
        slides.append({
            "slide_number": page_count,
            "title": "总结",
            "content": ["关键要点回顾", "行动建议", "Q&A"]
        })

        return {
            "title": topic,
            "slides": slides,
            "metadata": {
                "total_slides": page_count,
                "created_at": datetime.now().isoformat()
            }
        }

    def _create_default_slide_content(self,
                                     slide_number: int,
                                     title: str,
                                     content_hints: List[str]) -> SlideContent:
        """创建默认幻灯片内容"""
        # 如果有内容提示，使用它们；否则创建默认要点
        if content_hints and len(content_hints) >= Config.PPT.MIN_BULLET_POINTS:
            bullet_points = content_hints[:Config.PPT.MIN_BULLET_POINTS]
        else:
            bullet_points = [
                f"{title}的第一个关键点",
                f"{title}的第二个关键点",
                f"{title}的第三个关键点"
            ]

        return SlideContent(
            slide_number=slide_number,
            title=title,
            bullet_points=bullet_points,
            speaker_notes=f"这一页介绍{title}的主要内容"
        )

    def _ensure_min_bullets(self,
                           bullets: List[str],
                           hints: List[str],
                           min_count: int = Config.PPT.MIN_BULLET_POINTS) -> List[str]:
        """确保有最少数量的要点

        Args:
            bullets: 现有的要点列表
            hints: 提示列表
            min_count: 最少要点数量

        Returns:
            调整后的要点列表
        """
        result = bullets[:min_count] if bullets else []

        # 如果不足最少数量，从hints补充
        if len(result) < min_count and hints:
            for hint in hints:
                if len(result) >= min_count:
                    break
                if hint not in result:
                    result.append(hint)

        # 如果还是不足，添加默认要点
        while len(result) < min_count:
            result.append(f"补充要点 {len(result) + 1}")

        return result[:min_count]


# 独立函数，供测试和外部调用
def generate_outline(topic: str, slides_count: int, bedrock_client=None) -> Dict[str, Any]:
    """生成PPT大纲（独立函数）"""
    generator = ContentGenerator(bedrock_client=bedrock_client)
    return generator.generate_outline(topic, slides_count)

def generate_slide_content(outline: Dict, bedrock_client=None, include_speaker_notes: bool = True) -> Dict[str, Any]:
    """生成幻灯片详细内容（独立函数）"""
    generator = ContentGenerator(bedrock_client=bedrock_client)
    slides = generator.generate_slide_content(outline, include_speaker_notes)
    return {"slides": slides}

def generate_and_save_content(outline: Dict, presentation_id: str, bedrock_client=None,
                             s3_client=None, bucket_name: str = None) -> Dict[str, Any]:
    """生成内容并保存到S3（独立函数）"""
    generator = ContentGenerator(bedrock_client=bedrock_client, s3_client=s3_client)

    # 生成详细内容
    slides = generator.generate_slide_content(outline)

    # 构建完整内容
    content = {
        "presentation_id": presentation_id,
        "title": outline.get("title", ""),
        "slides": slides,
        "metadata": outline.get("metadata", {}),
        "status": "completed"
    }

    # 保存到S3
    if bucket_name:
        # 如果指定了bucket，临时修改配置
        import src.config as config
        original_bucket = config.S3_BUCKET
        config.S3_BUCKET = bucket_name
        s3_key = generator.save_to_s3(presentation_id, content)
        config.S3_BUCKET = original_bucket
    else:
        s3_key = generator.save_to_s3(presentation_id, content)

    return {
        "s3_key": s3_key,
        "presentation_id": presentation_id,
        "content": content
    }