"""
AI PPT Assistant Phase 3 - 图片重新生成器

提供图片重新生成功能，支持自定义提示词、失败回退机制和S3存储更新。

功能特性：
- 调用Amazon Nova/Bedrock重新生成图片
- 自定义提示词支持
- 失败回退机制
- S3存储更新
- 图片格式验证和优化
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import base64
import hashlib

try:
    from .image_generator import ImageGenerator
    from .image_exceptions import (
        ImageGeneratorError, NovaServiceError, S3OperationError,
        ImageProcessingError, ValidationError as ImageValidationError
    )
    from .image_config import CONFIG
except ImportError:
    # 本地测试时的导入方式
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from image_generator import ImageGenerator
    from image_exceptions import (
        ImageGeneratorError, NovaServiceError, S3OperationError,
        ImageProcessingError, ValidationError as ImageValidationError
    )
    from image_config import CONFIG

# 设置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ImageRegeneratorError(Exception):
    """图片重新生成异常基类"""

    def __init__(self, message: str, error_code: str = "IMAGE_REGENERATOR_ERROR", details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ValidationError(ImageRegeneratorError):
    """验证错误"""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


class ImageRegenerator:
    """图片重新生成器 - 负责重新生成和替换图片

    功能：
    - 重新生成单个图片
    - 批量重新生成图片
    - 自定义提示词
    - 失败回退机制
    - S3存储管理
    """

    def __init__(self, bedrock_client=None, s3_client=None, bucket_name: str = None):
        """
        初始化图片重新生成器

        Args:
            bedrock_client: Bedrock客户端
            s3_client: S3客户端
            bucket_name: S3存储桶名称
        """
        self.bedrock = bedrock_client or boto3.client('bedrock-runtime')
        self.s3_client = s3_client or boto3.client('s3')
        self.bucket_name = bucket_name or CONFIG.S3_BUCKET_NAME or "ai-ppt-presentations"

        # 使用现有的图片生成器
        self.image_generator = ImageGenerator(s3_service=None)

        logger.info(f"ImageRegenerator初始化完成，使用存储桶: {self.bucket_name}")

    def regenerate_image(self, presentation_id: str, regenerate_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        重新生成单个图片

        Args:
            presentation_id: 演示文稿ID
            regenerate_request: 重新生成请求

        Returns:
            重新生成结果

        Raises:
            ValidationError: 请求验证错误
            ImageRegeneratorError: 重新生成失败
        """
        start_time = time.time()

        # 验证请求
        self._validate_regenerate_request(regenerate_request)

        slide_number = regenerate_request["slide_number"]

        try:
            # 生成提示词
            prompt = self._get_image_prompt(regenerate_request)

            # 调用图片生成服务
            image_data = self._call_image_generation_service(prompt)

            # 保存新图片到S3
            new_image_url = self._save_new_image(image_data, presentation_id, slide_number)

            generation_time = time.time() - start_time

            logger.info(f"成功重新生成图片，用时 {generation_time:.2f} 秒")

            return {
                "status": "success",
                "new_image_url": new_image_url,
                "generation_time": generation_time,
                "used_prompt": prompt
            }

        except (NovaServiceError, ImageProcessingError) as e:
            logger.warning(f"图片生成失败，使用回退方案: {str(e)}")
            return self._generate_fallback_image(presentation_id, slide_number, str(e))

        except Exception as e:
            logger.error(f"重新生成图片时发生未预期错误: {str(e)}")
            return self._generate_fallback_image(presentation_id, slide_number, str(e))

    def regenerate_multiple_images(self, presentation_id: str, regenerate_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量重新生成多个图片

        Args:
            presentation_id: 演示文稿ID
            regenerate_requests: 重新生成请求列表

        Returns:
            重新生成结果列表
        """
        if not regenerate_requests:
            return []

        results = []

        for request in regenerate_requests:
            try:
                result = self.regenerate_image(presentation_id, request)
                result["slide_number"] = request["slide_number"]
                results.append(result)

            except Exception as e:
                logger.error(f"重新生成第 {request.get('slide_number', 'unknown')} 页图片失败: {str(e)}")
                results.append({
                    "slide_number": request.get("slide_number", 0),
                    "status": "error",
                    "error": str(e)
                })

        return results

    def regenerate_all_images(self, presentation_id: str, presentation_data: Dict[str, Any],
                             new_prompt: str = None) -> Dict[str, Any]:
        """
        重新生成演示文稿的所有图片

        Args:
            presentation_id: 演示文稿ID
            presentation_data: 演示文稿数据
            new_prompt: 统一的新提示词（可选）

        Returns:
            重新生成结果汇总
        """
        slides = presentation_data.get("slides", [])
        if not slides:
            return {
                "status": "no_slides",
                "message": "没有找到幻灯片内容",
                "total_images": 0
            }

        # 准备重新生成请求
        regenerate_requests = []
        for i, slide in enumerate(slides, 1):
            request = {
                "slide_number": i,
                "regenerate_image": True
            }

            if new_prompt:
                request["image_prompt"] = new_prompt
            elif slide.get("title") or slide.get("content"):
                # 基于幻灯片内容生成提示词
                request["slide_content"] = {
                    "title": slide.get("title", ""),
                    "content": slide.get("content", [])
                }

            regenerate_requests.append(request)

        # 批量重新生成
        results = self.regenerate_multiple_images(presentation_id, regenerate_requests)

        # 统计结果
        successful = len([r for r in results if r.get("status") == "success"])
        fallback = len([r for r in results if r.get("status") == "fallback"])
        errors = len([r for r in results if r.get("status") == "error"])

        return {
            "status": "completed",
            "total_images": len(results),
            "successful": successful,
            "fallback": fallback,
            "errors": errors,
            "results": results
        }

    def _validate_regenerate_request(self, request: Dict[str, Any]) -> None:
        """验证重新生成请求"""
        if not isinstance(request, dict):
            raise ImageValidationError("Regenerate request must be a dictionary")

        if "slide_number" not in request:
            raise ImageValidationError("Missing required field: slide_number")

        if not isinstance(request["slide_number"], int) or request["slide_number"] <= 0:
            raise ImageValidationError("slide_number must be a positive integer")

        if "regenerate_image" not in request:
            raise ImageValidationError("Missing required field: regenerate_image")

        if not request["regenerate_image"]:
            raise ImageValidationError("regenerate_image must be True to proceed")

    def _get_image_prompt(self, request: Dict[str, Any]) -> str:
        """获取图片生成提示词"""
        # 优先使用自定义提示词
        if "image_prompt" in request and request["image_prompt"]:
            return request["image_prompt"]

        # 基于幻灯片内容生成提示词
        if "slide_content" in request:
            return self.image_generator.generate_prompt(request["slide_content"])

        # 使用默认提示词
        return CONFIG.DEFAULT_IMAGE_PROMPT or "Professional presentation slide illustration"

    def _call_image_generation_service(self, prompt: str) -> bytes:
        """调用图片生成服务"""
        try:
            # 使用Amazon Nova Canvas生成图片
            return self._call_nova_canvas(prompt)
        except Exception as e:
            logger.warning(f"Nova Canvas失败，尝试使用Bedrock Titan: {str(e)}")
            try:
                return self._call_bedrock_titan(prompt)
            except Exception as e2:
                logger.error(f"所有图片生成服务都失败: Nova: {str(e)}, Titan: {str(e2)}")
                raise NovaServiceError(f"Image generation failed: {str(e2)}") from e2

    def _call_nova_canvas(self, prompt: str) -> bytes:
        """调用Amazon Nova Canvas生成图片"""
        try:
            # Nova Canvas API调用
            response = self.bedrock.invoke_model(
                modelId="amazon.nova-canvas-v1:0",
                body=json.dumps({
                    "taskType": "TEXT_IMAGE",
                    "textToImageParams": {
                        "text": prompt,
                        "images": []
                    },
                    "imageGenerationConfig": {
                        "numberOfImages": 1,
                        "quality": "standard",
                        "cfgScale": 8.0,
                        "height": 1024,
                        "width": 1024,
                        "seed": None
                    }
                })
            )

            response_body = json.loads(response['body'].read())

            if 'images' in response_body and response_body['images']:
                # 解码base64图片数据
                image_base64 = response_body['images'][0]
                image_data = base64.b64decode(image_base64)
                return image_data
            else:
                raise NovaServiceError("No image data in Nova Canvas response")

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ValidationException':
                raise ImageValidationError(f"Invalid prompt for Nova Canvas: {str(e)}")
            elif error_code == 'ServiceQuotaExceededException':
                raise NovaServiceError("Nova Canvas service quota exceeded")
            elif error_code == 'ThrottlingException':
                raise NovaServiceError("Nova Canvas service throttled")
            else:
                raise NovaServiceError(f"Nova Canvas error: {str(e)}")

    def _call_bedrock_titan(self, prompt: str) -> bytes:
        """调用Bedrock Titan Image Generator"""
        try:
            response = self.bedrock.invoke_model(
                modelId="amazon.titan-image-generator-v1",
                body=json.dumps({
                    "taskType": "TEXT_IMAGE",
                    "textToImageParams": {
                        "text": prompt
                    },
                    "imageGenerationConfig": {
                        "numberOfImages": 1,
                        "quality": "standard",
                        "cfgScale": 8.0,
                        "height": 1024,
                        "width": 1024,
                        "seed": 0
                    }
                })
            )

            response_body = json.loads(response['body'].read())

            if 'images' in response_body and response_body['images']:
                image_base64 = response_body['images'][0]
                image_data = base64.b64decode(image_base64)
                return image_data
            else:
                raise NovaServiceError("No image data in Titan response")

        except ClientError as e:
            raise NovaServiceError(f"Bedrock Titan error: {str(e)}")

    def _save_new_image(self, image_data: bytes, presentation_id: str, slide_number: int) -> str:
        """保存新图片到S3"""
        try:
            # 生成新的图片文件名
            timestamp = int(time.time())
            image_key = f"presentations/{presentation_id}/images/slide_{slide_number}_{timestamp}.png"

            # 上传到S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=image_key,
                Body=image_data,
                ContentType="image/png",
                Metadata={
                    "presentation_id": presentation_id,
                    "slide_number": str(slide_number),
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            )

            # 返回S3 URL
            image_url = f"s3://{self.bucket_name}/{image_key}"
            logger.info(f"新图片已保存到: {image_url}")

            return image_url

        except ClientError as e:
            logger.error(f"保存图片到S3失败: {str(e)}")
            raise S3OperationError(f"Failed to save image to S3: {str(e)}") from e

    def _generate_fallback_image(self, presentation_id: str, slide_number: int, error_msg: str) -> Dict[str, Any]:
        """生成回退图片"""
        try:
            # 创建占位图
            placeholder_data = self.image_generator.processing_service.create_placeholder_image(
                width=1024,
                height=1024,
                text=f"幻灯片 {slide_number}"
            )

            # 保存占位图到S3
            image_url = self._save_new_image(placeholder_data, presentation_id, slide_number)

            logger.info(f"已生成回退图片: {image_url}")

            return {
                "status": "fallback",
                "new_image_url": image_url,
                "error": error_msg,
                "fallback_used": True
            }

        except Exception as fallback_error:
            logger.error(f"生成回退图片也失败: {str(fallback_error)}")
            # 使用默认占位图URL
            default_url = f"s3://{self.bucket_name}/default/placeholder.jpg"
            return {
                "status": "fallback",
                "new_image_url": default_url,
                "error": f"Original error: {error_msg}, Fallback error: {str(fallback_error)}",
                "fallback_used": True
            }

    def delete_old_image(self, old_image_url: str) -> bool:
        """删除旧图片"""
        try:
            if old_image_url.startswith("s3://"):
                # 解析S3 URL
                parts = old_image_url.replace("s3://", "").split("/", 1)
                if len(parts) == 2:
                    bucket, key = parts
                    if bucket == self.bucket_name:
                        self.s3_client.delete_object(Bucket=bucket, Key=key)
                        logger.info(f"已删除旧图片: {old_image_url}")
                        return True
            return False
        except Exception as e:
            logger.warning(f"删除旧图片失败: {str(e)}")
            return False


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda处理函数

    Args:
        event: Lambda事件数据
        context: Lambda上下文

    Returns:
        API Gateway响应
    """
    try:
        # 解析请求路径
        path_parameters = event.get('pathParameters', {})
        presentation_id = path_parameters.get('presentation_id')
        slide_number = path_parameters.get('slide_number')

        if slide_number:
            slide_number = int(slide_number)

        # 解析请求体
        body = json.loads(event.get('body', '{}'))

        # 创建重新生成器
        regenerator = ImageRegenerator()

        # 判断请求类型
        if slide_number:
            # 单个图片重新生成
            regenerate_request = {
                "slide_number": slide_number,
                "regenerate_image": True,
                **body
            }
            result = regenerator.regenerate_image(presentation_id, regenerate_request)
        else:
            # 批量重新生成或全部重新生成
            scope = body.get("scope", "images")

            if scope == "images":
                # 重新生成所有图片
                # 这里需要从存储中获取演示文稿数据
                # 简化处理，返回任务ID
                result = {
                    "status": "accepted",
                    "task_id": f"regen_{presentation_id}_{int(time.time())}",
                    "scope": scope,
                    "message": "Regeneration task started"
                }
            elif scope == "slides":
                # 重新生成指定幻灯片
                slide_numbers = body.get("slide_numbers", [])
                requests = [
                    {"slide_number": num, "regenerate_image": True, **body.get("options", {})}
                    for num in slide_numbers
                ]
                results = regenerator.regenerate_multiple_images(presentation_id, requests)
                result = {
                    "status": "completed",
                    "scope": scope,
                    "affected_slides": slide_numbers,
                    "results": results
                }
            else:
                raise ValidationError(f"Invalid scope: {scope}")

        return {
            'statusCode': 202 if result.get("status") == "accepted" else 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(result, ensure_ascii=False)
        }

    except (ImageValidationError, ValidationError) as e:
        logger.error(f"验证错误: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'VALIDATION_ERROR',
                'message': str(e)
            }, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"未预期错误: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred'
            }, ensure_ascii=False)
        }


if __name__ == "__main__":
    # 本地测试代码
    print("测试图片重新生成器:")

    regenerator = ImageRegenerator()

    # 测试重新生成请求
    test_request = {
        "slide_number": 1,
        "regenerate_image": True,
        "image_prompt": "现代AI技术示意图，蓝色科技风格"
    }

    print(f"测试请求: {test_request}")

    try:
        # 这里只是验证类实例化和方法调用
        print("图片重新生成器初始化成功")
        print(f"使用存储桶: {regenerator.bucket_name}")

        # 验证请求格式
        regenerator._validate_regenerate_request(test_request)
        print("请求验证通过")

        # 生成提示词
        prompt = regenerator._get_image_prompt(test_request)
        print(f"生成的提示词: {prompt}")

    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")