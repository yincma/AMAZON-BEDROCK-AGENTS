"""
统一的API处理器 - 处理所有API Gateway请求
"""
import json
import uuid
import os
import boto3
from datetime import datetime
from typing import Dict, Any, Optional
import logging

# 导入本地模块
import sys
sys.path.append('/opt/python')
sys.path.append('.')

from src.content_generator import ContentGenerator
from src.ppt_compiler import PPTCompiler
from src.common.response_builder import ResponseBuilder
from src.common.s3_service import S3Service, S3ServiceError
from src.constants import Config
from src.exceptions import ValidationError, ResourceNotFoundError, PPTAssistantError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class APIHandler:
    """统一的API处理器"""

    def __init__(self, s3_client=None):
        self.bucket_name = os.environ.get(Config.Env.S3_BUCKET, Config.Env.DEFAULT_BUCKET)
        self.s3_service = S3Service(self.bucket_name, s3_client)
        self.content_generator = ContentGenerator()
        self.ppt_compiler = PPTCompiler()

    def handle_generate(self, event: Dict) -> Dict:
        """处理POST /generate请求"""
        try:
            # 1. 解析请求body
            body_str = event.get('body')
            if not body_str:
                return ResponseBuilder.error_response(
                    Config.API.HTTP_BAD_REQUEST,
                    "Request body is required",
                    Config.Error.VALIDATION_ERROR
                )

            body = json.loads(body_str)
            topic = body.get('topic')
            page_count = body.get('page_count', 5)

            # 2. 验证输入参数
            if not topic:
                raise ValidationError("Topic is required", "topic")

            if not isinstance(topic, str) or len(topic.strip()) < Config.PPT.MIN_PAGE_COUNT:
                raise ValidationError(
                    f"Topic must be at least {Config.PPT.MIN_PAGE_COUNT} characters",
                    "topic", topic
                )

            if not isinstance(page_count, int) or page_count < Config.PPT.MIN_PAGE_COUNT or page_count > Config.PPT.MAX_PAGE_COUNT:
                raise ValidationError(
                    f"Page count must be between {Config.PPT.MIN_PAGE_COUNT} and {Config.PPT.MAX_PAGE_COUNT}",
                    "page_count", page_count
                )

            # 3. 生成presentation_id
            presentation_id = str(uuid.uuid4())

            # 4. 保存初始状态到S3
            self._save_initial_status(presentation_id, topic, page_count)

            # 5. 返回presentation_id和状态
            return ResponseBuilder.success_response(Config.API.HTTP_ACCEPTED, {
                'presentation_id': presentation_id,
                'status': Config.Status.STATUS_PROCESSING,
                'topic': topic,
                'page_count': page_count,
                'estimated_completion_time': 30  # 秒
            })

        except json.JSONDecodeError:
            return ResponseBuilder.error_response(
                Config.API.HTTP_BAD_REQUEST,
                "Invalid JSON in request body",
                Config.Error.JSON_PARSE_ERROR
            )
        except ValidationError as e:
            return ResponseBuilder.validation_error_response(e.message, e.field)
        except Exception as e:
            logger.error(f"Generate request failed: {str(e)}")
            return ResponseBuilder.internal_error_response()

    def handle_status(self, event: Dict) -> Dict:
        """处理GET /status/{id}请求"""
        try:
            # 1. 从path参数提取presentation_id
            path_params = event.get('pathParameters', {})
            presentation_id = path_params.get('id')

            if not presentation_id:
                raise ValidationError("Presentation ID required", "id")

            # 2. 从S3读取状态信息
            try:
                status_key = Config.File.STATUS_FILE_TEMPLATE.format(presentation_id=presentation_id)
                status_info = self.s3_service.download_json(status_key)
            except S3ServiceError:
                raise ResourceNotFoundError("Presentation", presentation_id)

            # 3. 返回状态和进度
            return ResponseBuilder.success_response(Config.API.HTTP_OK, status_info)

        except ValidationError as e:
            return ResponseBuilder.validation_error_response(e.message, e.field)
        except ResourceNotFoundError as e:
            return ResponseBuilder.not_found_response("Presentation", path_params.get('id', 'unknown'))
        except Exception as e:
            logger.error(f"Status request failed: {str(e)}")
            return ResponseBuilder.internal_error_response()

    def handle_download(self, event: Dict) -> Dict:
        """处理GET /download/{id}请求"""
        try:
            # 1. 从path参数提取presentation_id
            path_params = event.get('pathParameters', {})
            presentation_id = path_params.get('id')

            if not presentation_id:
                raise ValidationError("Presentation ID required", "id")

            # 2. 检查PPT是否已生成
            pptx_key = Config.File.PPTX_FILE_TEMPLATE.format(presentation_id=presentation_id)

            if not self.s3_service.object_exists(pptx_key):
                raise ResourceNotFoundError("Presentation file", presentation_id)

            # 3. 生成预签名下载URL
            download_url = self.s3_service.generate_presigned_url(
                pptx_key,
                Config.S3.DOWNLOAD_URL_EXPIRY
            )

            # 4. 返回下载链接
            return ResponseBuilder.success_response(Config.API.HTTP_OK, {
                'presentation_id': presentation_id,
                'download_url': download_url,
                'expires_in': Config.S3.DOWNLOAD_URL_EXPIRY
            })

        except ValidationError as e:
            return ResponseBuilder.validation_error_response(e.message, e.field)
        except ResourceNotFoundError as e:
            return ResponseBuilder.not_found_response("Presentation file", path_params.get('id', 'unknown'))
        except S3ServiceError as e:
            logger.error(f"S3 operation failed: {str(e)}")
            return ResponseBuilder.internal_error_response("Failed to access presentation file")
        except Exception as e:
            logger.error(f"Download request failed: {str(e)}")
            return ResponseBuilder.internal_error_response()

    def _save_initial_status(self, presentation_id: str, topic: str, page_count: int):
        """保存初始状态到S3"""
        status = {
            'presentation_id': presentation_id,
            'topic': topic,
            'page_count': page_count,
            'status': Config.Status.STATUS_PENDING,
            'progress': Config.Status.PROGRESS_START,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'steps': {
                Config.Status.STEP_OUTLINE_GENERATION: False,
                Config.Status.STEP_CONTENT_GENERATION: False,
                Config.Status.STEP_PPT_COMPILATION: False,
                Config.Status.STEP_UPLOAD_COMPLETE: False
            }
        }

        status_key = Config.File.STATUS_FILE_TEMPLATE.format(presentation_id=presentation_id)
        self.s3_service.upload_json(status_key, status)

    def _get_status_from_s3(self, presentation_id: str) -> Optional[Dict]:
        """从S3获取状态信息"""
        try:
            status_key = Config.File.STATUS_FILE_TEMPLATE.format(presentation_id=presentation_id)
            return self.s3_service.download_json(status_key)
        except S3ServiceError:
            return None



def handler(event, context):
    """Lambda主处理函数"""
    try:
        # 处理OPTIONS请求（CORS预检）
        if event.get('httpMethod') == 'OPTIONS':
            return ResponseBuilder.cors_response()

        # 解析请求路径和方法
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')

        api_handler = APIHandler()

        # 路由请求到对应处理器
        if path == '/generate' and http_method == 'POST':
            return api_handler.handle_generate(event)
        elif path.startswith('/status/') and http_method == 'GET':
            return api_handler.handle_status(event)
        elif path.startswith('/download/') and http_method == 'GET':
            return api_handler.handle_download(event)
        else:
            return ResponseBuilder.error_response(
                Config.API.HTTP_NOT_FOUND,
                'Endpoint not found',
                Config.Error.RESOURCE_NOT_FOUND
            )

    except PPTAssistantError as e:
        logger.error(f"Application error: {e.message}")
        return ResponseBuilder.error_response(
            Config.API.HTTP_INTERNAL_ERROR,
            e.message,
            e.error_code,
            e.details
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return ResponseBuilder.internal_error_response()


# 测试时可调用的函数
def handle_generate_request(request_data: Dict) -> Dict:
    """处理生成请求（测试用）"""
    api_handler = APIHandler()
    event = {
        'httpMethod': 'POST',
        'path': '/generate',
        'body': json.dumps(request_data)
    }
    return api_handler.handle_generate(event)


def get_presentation_status(presentation_id: str) -> Dict:
    """获取演示文稿状态（测试用）"""
    api_handler = APIHandler()
    event = {
        'httpMethod': 'GET',
        'path': f'/status/{presentation_id}',
        'pathParameters': {'id': presentation_id}
    }
    return api_handler.handle_status(event)


def handle_download_request(presentation_id: str, s3_client=None, bucket_name: str = None) -> Dict:
    """处理下载请求（测试用）"""
    api_handler = APIHandler()
    if s3_client:
        api_handler.s3_client = s3_client
    if bucket_name:
        api_handler.bucket_name = bucket_name

    event = {
        'httpMethod': 'GET',
        'path': f'/download/{presentation_id}',
        'pathParameters': {'id': presentation_id}
    }
    return api_handler.handle_download(event)