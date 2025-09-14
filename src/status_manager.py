"""
状态管理器 - 管理PPT生成过程的状态跟踪
"""
import json
import boto3
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PresentationStatus(Enum):
    """演示文稿状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    CONTENT_GENERATED = "content_generated"
    COMPILING = "compiling"
    COMPLETED = "completed"
    FAILED = "failed"

class StatusManager:
    """状态管理器"""

    def __init__(self, bucket_name: str, s3_client=None):
        """初始化状态管理器

        Args:
            bucket_name: S3存储桶名称
            s3_client: S3客户端（可选，用于测试）
        """
        self.s3_client = s3_client or boto3.client('s3')
        self.bucket_name = bucket_name

    def create_status(self, presentation_id: str, topic: str, page_count: int = 5) -> Dict:
        """创建初始状态

        Args:
            presentation_id: 演示文稿ID
            topic: PPT主题
            page_count: 页数

        Returns:
            状态字典
        """
        status = {
            'presentation_id': presentation_id,
            'topic': topic,
            'page_count': page_count,
            'status': PresentationStatus.PENDING.value,
            'progress': 0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'estimated_completion_time': datetime.utcnow().isoformat(),
            'current_step': 'initializing',
            'steps': {
                'outline_generation': False,
                'content_generation': False,
                'ppt_compilation': False,
                'upload_complete': False
            },
            'error_info': None
        }

        self.save_status(presentation_id, status)
        logger.info(f"创建初始状态: {presentation_id}")
        return status

    def update_status(self, presentation_id: str, status: str, progress: int,
                     step: Optional[str] = None, error_info: Optional[Dict] = None):
        """更新状态

        Args:
            presentation_id: 演示文稿ID
            status: 状态值
            progress: 进度百分比 (0-100)
            step: 当前完成的步骤
            error_info: 错误信息（如果有）
        """
        current_status = self.get_status(presentation_id)
        if current_status:
            current_status['status'] = status
            current_status['progress'] = min(100, max(0, progress))  # 确保在0-100范围内
            current_status['updated_at'] = datetime.utcnow().isoformat()

            if step:
                current_status['current_step'] = step
                if step in current_status['steps']:
                    current_status['steps'][step] = True

            if error_info:
                current_status['error_info'] = error_info

            # 计算预估完成时间
            if status == PresentationStatus.PROCESSING.value and progress > 0:
                # 简单的线性估算
                elapsed_time = (datetime.utcnow() - datetime.fromisoformat(
                    current_status['created_at'].replace('Z', '+00:00')
                )).total_seconds()

                if progress > 5:  # 避免除零
                    estimated_total_time = elapsed_time * (100 / progress)
                    remaining_time = max(0, estimated_total_time - elapsed_time)
                    estimated_completion = datetime.utcnow().timestamp() + remaining_time
                    current_status['estimated_completion_time'] = datetime.fromtimestamp(
                        estimated_completion
                    ).isoformat()

            self.save_status(presentation_id, current_status)
            logger.info(f"更新状态: {presentation_id} - {status} ({progress}%)")

    def get_status(self, presentation_id: str) -> Optional[Dict]:
        """获取状态

        Args:
            presentation_id: 演示文稿ID

        Returns:
            状态字典，如果不存在则返回None
        """
        try:
            key = f"presentations/{presentation_id}/status.json"
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            status = json.loads(response['Body'].read().decode('utf-8'))
            logger.debug(f"获取状态: {presentation_id}")
            return status
        except Exception as e:
            logger.warning(f"无法获取状态 {presentation_id}: {str(e)}")
            return None

    def save_status(self, presentation_id: str, status: Dict):
        """保存状态到S3

        Args:
            presentation_id: 演示文稿ID
            status: 状态字典
        """
        key = f"presentations/{presentation_id}/status.json"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(status, ensure_ascii=False, indent=2),
                ContentType='application/json'
            )
            logger.debug(f"保存状态到S3: {key}")
        except Exception as e:
            logger.error(f"保存状态失败 {presentation_id}: {str(e)}")
            raise

    def mark_failed(self, presentation_id: str, error_message: str, error_code: str = "UNKNOWN_ERROR"):
        """标记为失败状态

        Args:
            presentation_id: 演示文稿ID
            error_message: 错误信息
            error_code: 错误代码
        """
        error_info = {
            'error_code': error_code,
            'error_message': error_message,
            'error_time': datetime.utcnow().isoformat(),
            'retry_possible': True
        }

        self.update_status(
            presentation_id,
            PresentationStatus.FAILED.value,
            0,
            error_info=error_info
        )
        logger.error(f"标记失败状态: {presentation_id} - {error_message}")

    def mark_completed(self, presentation_id: str):
        """标记为完成状态

        Args:
            presentation_id: 演示文稿ID
        """
        self.update_status(
            presentation_id,
            PresentationStatus.COMPLETED.value,
            100,
            'upload_complete'
        )
        logger.info(f"标记完成状态: {presentation_id}")

    def list_presentations(self, status_filter: Optional[str] = None, limit: int = 50) -> list:
        """列出演示文稿

        Args:
            status_filter: 状态过滤器（可选）
            limit: 限制数量

        Returns:
            演示文稿状态列表
        """
        try:
            # 列出所有presentations目录下的status.json文件
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='presentations/',
                Delimiter='/'
            )

            presentations = []
            for obj in response.get('CommonPrefixes', []):
                prefix = obj['Prefix']
                presentation_id = prefix.split('/')[-2] if len(prefix.split('/')) > 2 else None

                if presentation_id:
                    status = self.get_status(presentation_id)
                    if status:
                        if not status_filter or status.get('status') == status_filter:
                            presentations.append(status)

                        if len(presentations) >= limit:
                            break

            # 按创建时间排序（最新的在前）
            presentations.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return presentations

        except Exception as e:
            logger.error(f"列出演示文稿失败: {str(e)}")
            return []

    def get_progress_details(self, presentation_id: str) -> Dict:
        """获取详细进度信息

        Args:
            presentation_id: 演示文稿ID

        Returns:
            详细进度信息字典
        """
        status = self.get_status(presentation_id)
        if not status:
            return {}

        steps = status.get('steps', {})
        completed_steps = sum(1 for step in steps.values() if step)
        total_steps = len(steps)

        progress_details = {
            'overall_progress': status.get('progress', 0),
            'completed_steps': completed_steps,
            'total_steps': total_steps,
            'current_step': status.get('current_step', ''),
            'steps_detail': {
                'outline_generation': {
                    'completed': steps.get('outline_generation', False),
                    'description': '生成PPT大纲'
                },
                'content_generation': {
                    'completed': steps.get('content_generation', False),
                    'description': '生成幻灯片内容'
                },
                'ppt_compilation': {
                    'completed': steps.get('ppt_compilation', False),
                    'description': '编译PPT文件'
                },
                'upload_complete': {
                    'completed': steps.get('upload_complete', False),
                    'description': '上传完成'
                }
            }
        }

        return progress_details

    def cleanup_old_presentations(self, days_old: int = 7):
        """清理旧的演示文稿

        Args:
            days_old: 保留天数
        """
        cutoff_time = datetime.utcnow().timestamp() - (days_old * 24 * 3600)

        presentations = self.list_presentations()
        cleaned_count = 0

        for presentation in presentations:
            created_at = presentation.get('created_at', '')
            try:
                created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                if created_time < cutoff_time:
                    presentation_id = presentation['presentation_id']
                    self._delete_presentation_files(presentation_id)
                    cleaned_count += 1
            except Exception as e:
                logger.warning(f"清理演示文稿失败: {str(e)}")

        logger.info(f"清理了 {cleaned_count} 个旧演示文稿")

    def _delete_presentation_files(self, presentation_id: str):
        """删除演示文稿相关的所有文件

        Args:
            presentation_id: 演示文稿ID
        """
        try:
            # 列出该presentation_id下的所有对象
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f'presentations/{presentation_id}/'
            )

            # 删除所有对象
            objects_to_delete = []
            for obj in response.get('Contents', []):
                objects_to_delete.append({'Key': obj['Key']})

            if objects_to_delete:
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects_to_delete}
                )
                logger.info(f"删除演示文稿文件: {presentation_id}")
        except Exception as e:
            logger.error(f"删除演示文稿文件失败 {presentation_id}: {str(e)}")


# 便捷函数
def create_status_manager(bucket_name: str = None, s3_client=None) -> StatusManager:
    """创建状态管理器实例"""
    if not bucket_name:
        bucket_name = 'ai-ppt-presentations-dev'
    return StatusManager(bucket_name, s3_client)


def get_status_from_s3(presentation_id: str, s3_client, bucket_name: str) -> Optional[Dict]:
    """从S3获取状态（兼容测试接口）"""
    manager = StatusManager(bucket_name, s3_client)
    return manager.get_status(presentation_id)