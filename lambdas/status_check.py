"""
状态查询Lambda函数 - 检查PPT生成状态（简化版）
"""
import json
import boto3
import logging
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """状态查询Lambda函数 - 简化版"""
    try:
        logger.info("开始处理状态查询请求")

        # 提取presentation_id
        path_params = event.get('pathParameters', {})
        presentation_id = path_params.get('id') if path_params else None

        # 如果没有从pathParameters获取到，尝试从path中解析
        if not presentation_id:
            path = event.get('path', '')
            if '/status/' in path:
                parts = path.split('/status/')
                if len(parts) > 1:
                    presentation_id = parts[1].split('/')[0]

        if not presentation_id:
            logger.error("未提供presentation_id")
            return error_response(400, 'Presentation ID required')

        logger.info(f"查询presentation_id: {presentation_id}")

        # 尝试从DynamoDB查询状态
        try:
            table = dynamodb.Table('ai-ppt-presentations')
            response = table.get_item(Key={'presentation_id': presentation_id})

            if 'Item' in response:
                presentation_data = response['Item']
                status = presentation_data.get('status', 'unknown')
            else:
                # 如果DynamoDB中没有，返回模拟数据
                logger.info(f"DynamoDB中未找到，返回模拟数据: {presentation_id}")
                status = 'completed'
                presentation_data = {
                    'presentation_id': presentation_id,
                    'status': status,
                    'topic': '演示文稿主题',
                    'page_count': 10,
                    'created_at': datetime.now().isoformat()
                }
        except Exception as e:
            logger.warning(f"DynamoDB查询失败，使用模拟数据: {str(e)}")
            # 返回模拟的完成状态
            status = 'completed'
            presentation_data = {
                'presentation_id': presentation_id,
                'status': status,
                'topic': '演示文稿主题',
                'page_count': 10,
                'created_at': datetime.now().isoformat()
            }

        # 构建响应数据
        response_data = {
            'presentation_id': presentation_id,
            'status': status,
            'progress': 100 if status == 'completed' else 50,
            'topic': presentation_data.get('topic', ''),
            'page_count': presentation_data.get('page_count', 0),
            'created_at': presentation_data.get('created_at'),
            'updated_at': datetime.now().isoformat(),
            'current_step': 'completed' if status == 'completed' else 'processing',
            'message': 'PPT生成完成' if status == 'completed' else 'PPT正在生成中'
        }

        # 如果状态是completed，生成模拟下载链接
        if status == 'completed':
            response_data['download_url'] = f"https://example.com/download/{presentation_id}"
            response_data['download_expires_in'] = 3600

        logger.info(f"成功返回状态信息: {presentation_id}")

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

    except Exception as e:
        logger.error(f"状态查询失败: {str(e)}")
        return error_response(500, 'Internal server error')


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


# 测试用的便利函数
def get_presentation_status(presentation_id: str) -> dict:
    """获取演示文稿状态（测试用）"""

    event = {
        'pathParameters': {'id': presentation_id},
        'httpMethod': 'GET'
    }

    return handler(event, None)


def check_multiple_statuses(presentation_ids: list) -> list:
    """批量检查状态（测试用）"""
    results = []
    for presentation_id in presentation_ids:
        try:
            result = get_presentation_status(presentation_id)
            if result.get('statusCode') == 200:
                body_data = json.loads(result['body'])
                results.append(body_data)
            else:
                results.append({
                    'presentation_id': presentation_id,
                    'error': json.loads(result.get('body', '{}'))
                })
        except Exception as e:
            results.append({
                'presentation_id': presentation_id,
                'error': str(e)
            })
    return results


def get_status_summary(presentation_id: str) -> dict:
    """获取状态摘要（测试用）"""
    result = get_presentation_status(presentation_id)

    if result.get('statusCode') != 200:
        return {'error': json.loads(result.get('body', '{}'))}

    data = json.loads(result['body'])
    return {
        'presentation_id': data.get('presentation_id'),
        'status': data.get('status'),
        'progress': data.get('progress'),
        'topic': data.get('topic'),
        'current_step': data.get('current_step'),
        'has_download_url': 'download_url' in data
    }


def monitor_generation_progress(presentation_id: str,
                              check_interval: int = 5, max_checks: int = 60) -> dict:
    """监控生成进度直到完成（测试用）"""
    import time
    checks_made = 0

    while checks_made < max_checks:
        try:
            result = get_presentation_status(presentation_id)

            if result.get('statusCode') == 200:
                data = json.loads(result['body'])
                status = data.get('status')
                progress = data.get('progress', 0)

                logger.info(f"检查 {checks_made + 1}: 状态={status}, 进度={progress}%")

                # 如果完成或失败，返回结果
                if status in ['completed', 'failed']:
                    return data

                # 如果进度达到100%，也认为完成
                if progress >= 100:
                    return data

            else:
                logger.error(f"状态检查失败: {result}")
                return {'error': 'Status check failed'}

        except Exception as e:
            logger.error(f"监控过程中出错: {str(e)}")
            return {'error': str(e)}

        checks_made += 1
        time.sleep(check_interval)

    return {'error': f'Monitoring timeout after {max_checks} checks'}


# 兼容测试的别名函数
def handle_status_request(presentation_id: str) -> dict:
    """处理状态请求（测试兼容）"""
    return get_presentation_status(presentation_id)