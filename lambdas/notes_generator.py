"""
演讲者备注生成器 - 简化入口
提供简单的接口用于生成演讲者备注
"""

import json
import logging
from typing import Dict, Any, Optional
import boto3

from lambdas.controllers.generate_speaker_notes import SpeakerNotesGenerator

logger = logging.getLogger(__name__)


def generate_speaker_notes(
    slide_data: Dict[str, Any],
    language: str = "zh-CN",
    bedrock_client=None
) -> str:
    """
    生成单张幻灯片的演讲者备注

    Args:
        slide_data: 幻灯片数据
        language: 语言设置
        bedrock_client: Bedrock客户端（可选）

    Returns:
        str: 演讲者备注文本
    """
    generator = SpeakerNotesGenerator(
        bedrock_client=bedrock_client,
        language=language
    )
    return generator.generate_notes(slide_data)


def batch_generate_notes(
    slides: list,
    language: str = "zh-CN",
    bedrock_client=None
) -> list:
    """
    批量生成演讲者备注

    Args:
        slides: 幻灯片列表
        language: 语言设置
        bedrock_client: Bedrock客户端（可选）

    Returns:
        list: 包含演讲者备注的结果列表
    """
    generator = SpeakerNotesGenerator(
        bedrock_client=bedrock_client,
        language=language
    )
    return generator.batch_generate_notes(slides)


def add_notes_to_presentation(
    presentation_data: Dict[str, Any],
    language: str = "zh-CN",
    bedrock_client=None
) -> Dict[str, Any]:
    """
    为整个演示文稿添加演讲者备注

    Args:
        presentation_data: 演示文稿数据
        language: 语言设置
        bedrock_client: Bedrock客户端（可选）

    Returns:
        Dict: 包含演讲者备注的演示文稿数据
    """
    generator = SpeakerNotesGenerator(
        bedrock_client=bedrock_client,
        language=language
    )
    return generator.generate_for_presentation(presentation_data)


def lambda_handler(event, context):
    """
    Lambda函数处理器

    Args:
        event: Lambda事件
        context: Lambda上下文

    Returns:
        dict: API响应
    """
    try:
        # 解析请求
        body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event

        # 获取参数
        action = body.get('action', 'generate_single')
        language = body.get('language', 'zh-CN')

        if action == 'generate_single':
            # 生成单个备注
            slide_data = body.get('slide_data', {})
            notes = generate_speaker_notes(slide_data, language)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'speaker_notes': notes,
                    'slide_number': slide_data.get('slide_number', 1)
                })
            }

        elif action == 'generate_batch':
            # 批量生成
            slides = body.get('slides', [])
            results = batch_generate_notes(slides, language)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'results': results,
                    'total': len(results)
                })
            }

        elif action == 'add_to_presentation':
            # 添加到演示文稿
            presentation_data = body.get('presentation_data', {})
            updated_data = add_notes_to_presentation(presentation_data, language)

            return {
                'statusCode': 200,
                'body': json.dumps(updated_data)
            }

        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unknown action: {action}'
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