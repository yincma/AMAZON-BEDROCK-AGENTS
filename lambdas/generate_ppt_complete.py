"""
完整的PPT生成处理函数 - 端到端处理PPT生成流程
"""
import json
import uuid
import logging
import os
import sys
from typing import Dict

# 添加路径以导入模块
sys.path.append('/opt/python')
sys.path.append('.')

from src.content_generator import ContentGenerator
from src.ppt_compiler import PPTCompiler
from src.status_manager import StatusManager, PresentationStatus
from src.validators import RequestValidator
from src.common.s3_service import S3Service

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """完整的PPT生成处理函数"""
    presentation_id = None
    status_manager = None

    try:
        # 获取环境变量
        bucket_name = os.environ.get('S3_BUCKET', 'ai-ppt-presentations-dev')

        # 1. 解析和验证请求
        logger.info("开始处理PPT生成请求")

        body_str = event.get('body', '{}')
        if isinstance(body_str, dict):
            body = body_str
        else:
            body = json.loads(body_str)

        is_valid, error_msg = RequestValidator.validate_generate_request(body)
        if not is_valid:
            logger.error(f"请求验证失败: {error_msg}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': error_msg})
            }

        topic = body['topic']
        page_count = body.get('page_count') or body.get('slides_count', 5)
        style = body.get('style', 'professional')

        presentation_id = str(uuid.uuid4())
        logger.info(f"生成presentation_id: {presentation_id}")

        # 2. 初始化管理器
        status_manager = StatusManager(bucket_name)
        s3_service = S3Service(bucket_name)
        content_generator = ContentGenerator(s3_service=s3_service)
        ppt_compiler = PPTCompiler()

        # 3. 创建初始状态
        logger.info("创建初始状态")
        status_manager.create_status(presentation_id, topic, page_count)

        # 4. 生成大纲
        logger.info("开始生成PPT大纲")
        status_manager.update_status(
            presentation_id,
            PresentationStatus.PROCESSING.value,
            25,
            'outline_generation'
        )

        try:
            outline = content_generator.generate_outline(topic, page_count)
            logger.info(f"大纲生成成功，包含 {len(outline.get('slides', []))} 页")
        except Exception as e:
            logger.error(f"大纲生成失败: {str(e)}")
            status_manager.mark_failed(presentation_id, f"大纲生成失败: {str(e)}", "OUTLINE_GENERATION_FAILED")
            return error_response(500, f"大纲生成失败: {str(e)}")

        # 5. 生成详细内容
        logger.info("开始生成详细内容")
        status_manager.update_status(
            presentation_id,
            PresentationStatus.PROCESSING.value,
            50,
            'content_generation'
        )

        try:
            slides = content_generator.generate_slide_content(outline, include_speaker_notes=True)
            logger.info(f"内容生成成功，生成了 {len(slides)} 页详细内容")
        except Exception as e:
            logger.error(f"内容生成失败: {str(e)}")
            status_manager.mark_failed(presentation_id, f"内容生成失败: {str(e)}", "CONTENT_GENERATION_FAILED")
            return error_response(500, f"内容生成失败: {str(e)}")

        # 6. 保存内容到S3
        logger.info("保存内容到S3")
        content = {
            'presentation_id': presentation_id,
            'topic': topic,
            'style': style,
            'page_count': page_count,
            'slides': slides,
            'metadata': {
                'created_at': outline.get('metadata', {}).get('created_at'),
                'total_slides': len(slides),
                'generation_completed_at': status_manager.get_status(presentation_id).get('updated_at')
            }
        }

        try:
            content_s3_key = content_generator.save_to_s3(presentation_id, content)
            logger.info(f"内容已保存到S3: {content_s3_key}")
        except Exception as e:
            logger.error(f"保存内容到S3失败: {str(e)}")
            status_manager.mark_failed(presentation_id, f"保存内容失败: {str(e)}", "CONTENT_SAVE_FAILED")
            return error_response(500, f"保存内容失败: {str(e)}")

        # 7. 生成图片
        logger.info("开始生成幻灯片图片")
        status_manager.update_status(
            presentation_id,
            PresentationStatus.PROCESSING.value,
            65,
            'image_generation'
        )

        try:
            # 导入图片生成器
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)

            from image_generator import ImageGenerator
            from image_processing_service import ImageProcessingService
            from image_s3_service import ImageS3Service

            # 初始化图片生成器
            image_generator = ImageGenerator(
                processing_service=ImageProcessingService(),
                s3_service=ImageS3Service(bucket_name=bucket_name),
                bucket_name=bucket_name
            )

            # 为每个幻灯片生成图片
            for i, slide in enumerate(slides, 1):
                try:
                    # 生成图片提示词
                    prompt = image_generator.generate_prompt(slide, target_audience="business")
                    logger.info(f"幻灯片 {i} 图片提示词: {prompt}")

                    # 生成并保存图片
                    image_result = image_generator.generate_image(prompt, presentation_id, i)

                    # 将图片URL添加到幻灯片数据中
                    slide['image_url'] = image_result.get('image_url', '')
                    slide['image_prompt'] = image_result.get('prompt', '')

                    logger.info(f"幻灯片 {i} 图片生成成功: {image_result.get('image_url', 'N/A')}")

                except Exception as img_error:
                    logger.warning(f"幻灯片 {i} 图片生成失败: {str(img_error)}，将使用占位图")
                    # 即使图片生成失败，也继续处理，不中断整个流程
                    slide['image_url'] = ''
                    slide['image_prompt'] = ''

            # 更新内容，包含图片URL
            content['slides'] = slides

            # 重新保存更新后的内容到S3
            try:
                updated_content_s3_key = content_generator.save_to_s3(presentation_id, content)
                logger.info(f"更新后的内容已保存到S3: {updated_content_s3_key}")
            except Exception as save_error:
                logger.warning(f"保存更新内容失败: {str(save_error)}")

        except Exception as e:
            logger.warning(f"图片生成模块加载失败: {str(e)}，将跳过图片生成")
            # 图片生成失败不应中断整个流程

        # 8. 编译PPT
        logger.info("开始编译PPT文件")
        status_manager.update_status(
            presentation_id,
            PresentationStatus.COMPILING.value,
            75,
            'ppt_compilation'
        )

        try:
            # 使用PPT编译器生成PPTX文件
            from src.ppt_compiler import create_pptx_from_content
            pptx_bytes = create_pptx_from_content(content, include_notes=True)

            # 保存PPTX到S3
            pptx_key = f"presentations/{presentation_id}/output/presentation.pptx"
            ppt_compiler.s3_client.put_object(
                Bucket=bucket_name,
                Key=pptx_key,
                Body=pptx_bytes,
                ContentType='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            )

            logger.info(f"PPT编译成功，已保存到: {pptx_key}")

            # 生成下载链接
            download_url = ppt_compiler.generate_download_url(pptx_key, expires_in=3600)

        except Exception as e:
            logger.error(f"PPT编译失败: {str(e)}")
            status_manager.mark_failed(presentation_id, f"PPT编译失败: {str(e)}", "PPT_COMPILATION_FAILED")
            return error_response(500, f"PPT编译失败: {str(e)}")

        # 9. 标记完成
        logger.info("PPT生成流程完成")
        status_manager.mark_completed(presentation_id)

        # 10. 返回成功响应
        response_data = {
            'presentation_id': presentation_id,
            'status': 'completed',
            'topic': topic,
            'page_count': page_count,
            'slides_generated': len(slides),
            'download_url': download_url,
            'expires_in': 3600,
            'completion_time': status_manager.get_status(presentation_id).get('updated_at')
        }

        logger.info(f"PPT生成成功完成: {presentation_id}")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps(response_data, ensure_ascii=False)
        }

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {str(e)}")
        if presentation_id and status_manager:
            status_manager.mark_failed(presentation_id, f"请求格式错误: {str(e)}", "JSON_PARSE_ERROR")
        return error_response(400, "Invalid JSON format")

    except Exception as e:
        logger.error(f"PPT生成过程中发生未预期错误: {str(e)}")
        if presentation_id and status_manager:
            status_manager.mark_failed(presentation_id, f"系统错误: {str(e)}", "SYSTEM_ERROR")
        return error_response(500, "Internal server error")


def error_response(status_code: int, message: str) -> dict:
    """构建错误响应"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps({'error': message})
    }


def handle_request_with_timeout(request_data: Dict, timeout_seconds: int) -> Dict:
    """处理带超时的请求（测试用）"""
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Request timed out after {timeout_seconds} seconds")

    # 设置超时信号
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)

    try:
        # 模拟事件结构
        event = {
            'body': json.dumps(request_data),
            'httpMethod': 'POST'
        }
        result = handler(event, None)
        signal.alarm(0)  # 取消超时
        return result
    except TimeoutError:
        signal.alarm(0)  # 取消超时
        raise
    finally:
        signal.alarm(0)  # 确保清除超时


def handle_generate_request_with_retry(request_data: Dict, max_retries: int = 3) -> Dict:
    """带重试的生成请求处理（测试用）"""
    last_error = None

    for attempt in range(max_retries):
        try:
            event = {
                'body': json.dumps(request_data),
                'httpMethod': 'POST'
            }
            result = handler(event, None)

            # 检查是否成功
            if result.get('statusCode') == 200:
                return result
            else:
                last_error = result
                logger.warning(f"尝试 {attempt + 1} 失败: {result.get('body', '')}")

        except Exception as e:
            last_error = str(e)
            logger.warning(f"尝试 {attempt + 1} 发生异常: {str(e)}")

        # 如果不是最后一次尝试，等待一段时间
        if attempt < max_retries - 1:
            import time
            time.sleep(2 ** attempt)  # 指数退避

    # 所有重试都失败了
    if isinstance(last_error, dict):
        return last_error
    else:
        return error_response(503, f"Service temporarily unavailable after {max_retries} retries")


# 测试用的简化函数
def generate_ppt_sync(topic: str, page_count: int = 5, style: str = 'professional') -> Dict:
    """同步生成PPT（测试用）"""
    request_data = {
        'topic': topic,
        'page_count': page_count,
        'style': style
    }

    event = {
        'body': json.dumps(request_data),
        'httpMethod': 'POST'
    }

    return handler(event, None)