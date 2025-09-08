"""
Unit tests for get_task Lambda function.

This test file follows TDD principles and creates failing tests for the
GET /tasks/{task_id} endpoint functionality that needs to be implemented.

Test Scenarios:
1. Successfully retrieve task status
2. Return 404 when task doesn't exist
3. Return 400 for invalid task_id format
4. Handle DynamoDB connection errors gracefully
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
import sys
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

# Add Lambda function path to system path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/api'))


@pytest.fixture
def lambda_context():
    """Mock Lambda context object."""
    context = Mock()
    context.function_name = 'ai-ppt-assistant-get-task'
    context.memory_limit_in_mb = 512
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:ai-ppt-assistant-get-task'
    context.aws_request_id = 'test-request-id-' + str(uuid.uuid4())
    context.log_group_name = '/aws/lambda/ai-ppt-assistant-get-task'
    context.log_stream_name = '2025/01/07/[$LATEST]test-stream'
    context.get_remaining_time_in_millis = Mock(return_value=30000)
    return context


@pytest.fixture
def valid_task_id():
    """Generate a valid UUID for task ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_task_data():
    """Sample task data stored in DynamoDB."""
    task_id = str(uuid.uuid4())
    return {
        'task_id': task_id,
        'presentation_id': str(uuid.uuid4()),
        'status': 'processing',
        'task_type': 'generate_content',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'progress': Decimal('35'),
        'metadata': {
            'slide_number': 3,
            'total_slides': 10,
            'topic': 'AI and Machine Learning'
        },
        'result': None,
        'error': None,
        'retry_count': Decimal('0'),
        'ttl': Decimal(str(int(datetime.now(timezone.utc).timestamp()) + 86400))
    }


class TestGetTaskAPI:
    """Test suite for get_task API endpoint."""
    
    @patch('get_task.get_dynamodb_client')
    @patch.dict(os.environ, {
        'TASKS_TABLE_NAME': 'ai-ppt-assistant-dev-tasks',
        'LOG_LEVEL': 'DEBUG',
        'AWS_REGION': 'us-east-1'
    })
    def test_get_task_success(self, mock_get_dynamodb_client, lambda_context, sample_task_data):
        """Test successful retrieval of task status."""
        # Mock DynamoDB client
        mock_dynamodb = MagicMock()
        mock_get_dynamodb_client.return_value = mock_dynamodb
        
        # Mock DynamoDB get_item response
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'task_id': {'S': sample_task_data['task_id']},
                'presentation_id': {'S': sample_task_data['presentation_id']},
                'status': {'S': sample_task_data['status']},
                'task_type': {'S': sample_task_data['task_type']},
                'created_at': {'S': sample_task_data['created_at']},
                'updated_at': {'S': sample_task_data['updated_at']},
                'progress': {'N': str(sample_task_data['progress'])},
                'metadata': {'M': {
                    'slide_number': {'N': str(sample_task_data['metadata']['slide_number'])},
                    'total_slides': {'N': str(sample_task_data['metadata']['total_slides'])},
                    'topic': {'S': sample_task_data['metadata']['topic']}
                }},
                'retry_count': {'N': str(sample_task_data['retry_count'])},
                'ttl': {'N': str(sample_task_data['ttl'])}
            }
        }
        
        # Import the Lambda handler (this will fail as the module doesn't exist yet)
        from get_task import lambda_handler
        
        # Create the event
        event = {
            'pathParameters': {
                'task_id': sample_task_data['task_id']
            },
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Call the Lambda handler
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'headers' in result
        assert result['headers']['Content-Type'] == 'application/json'
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        
        body = json.loads(result['body'])
        assert body['success'] is True
        assert body['task']['task_id'] == sample_task_data['task_id']
        assert body['task']['status'] == 'processing'
        assert body['task']['progress'] == 35
        assert body['task']['task_type'] == 'generate_content'
        assert 'metadata' in body['task']
        assert body['task']['metadata']['slide_number'] == 3
        
        # Verify DynamoDB was called correctly
        mock_dynamodb.get_item.assert_called_once_with(
            TableName='ai-ppt-assistant-dev-tasks',
            Key={'task_id': {'S': sample_task_data['task_id']}}
        )
    
    @patch('get_task.get_dynamodb_client')
    @patch.dict(os.environ, {
        'TASKS_TABLE_NAME': 'ai-ppt-assistant-dev-tasks',
        'LOG_LEVEL': 'DEBUG',
        'AWS_REGION': 'us-east-1'
    })
    def test_get_task_not_found(self, mock_get_dynamodb_client, lambda_context, valid_task_id):
        """Test 404 response when task doesn't exist."""
        # Mock DynamoDB client
        mock_dynamodb = MagicMock()
        mock_get_dynamodb_client.return_value = mock_dynamodb
        
        # Mock DynamoDB get_item response with no item
        mock_dynamodb.get_item.return_value = {}
        
        # Import the Lambda handler
        from get_task import lambda_handler
        
        # Create the event
        event = {
            'pathParameters': {
                'task_id': valid_task_id
            },
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Call the Lambda handler
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 404
        assert 'headers' in result
        assert result['headers']['Content-Type'] == 'application/json'
        
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
        assert 'not found' in body['error'].lower()
        assert valid_task_id in body['error']
        
        # Verify DynamoDB was called
        mock_dynamodb.get_item.assert_called_once()
    
    @patch('get_task.get_dynamodb_client')
    @patch.dict(os.environ, {
        'TASKS_TABLE_NAME': 'ai-ppt-assistant-dev-tasks',
        'LOG_LEVEL': 'DEBUG',
        'AWS_REGION': 'us-east-1'
    })
    def test_get_task_invalid_id_format(self, mock_get_dynamodb_client, lambda_context):
        """Test 400 response for invalid task_id format."""
        # Import the Lambda handler
        from get_task import lambda_handler
        
        # Test various invalid task IDs
        invalid_task_ids = [
            'invalid-id',  # Not a UUID
            '123',  # Too short
            'not-a-uuid-at-all',  # Invalid format
            '',  # Empty string
            '12345678-1234-1234-1234-12345678901g',  # Invalid character in UUID
        ]
        
        for invalid_id in invalid_task_ids:
            # Create the event
            event = {
                'pathParameters': {
                    'task_id': invalid_id
                },
                'httpMethod': 'GET',
                'headers': {
                    'Content-Type': 'application/json'
                }
            }
            
            # Call the Lambda handler
            result = lambda_handler(event, lambda_context)
            
            # Assertions
            assert result['statusCode'] == 400, f"Failed for task_id: {invalid_id}"
            assert 'headers' in result
            assert result['headers']['Content-Type'] == 'application/json'
            
            body = json.loads(result['body'])
            assert body['success'] is False
            assert 'error' in body
            assert 'invalid' in body['error'].lower()
            
            # DynamoDB should not be called for invalid IDs
            mock_get_dynamodb_client.assert_not_called()
    
    @patch('get_task.get_dynamodb_client')
    @patch.dict(os.environ, {
        'TASKS_TABLE_NAME': 'ai-ppt-assistant-dev-tasks',
        'LOG_LEVEL': 'DEBUG',
        'AWS_REGION': 'us-east-1'
    })
    def test_get_task_missing_path_parameter(self, mock_get_dynamodb_client, lambda_context):
        """Test 400 response when task_id is missing from path parameters."""
        # Import the Lambda handler
        from get_task import lambda_handler
        
        # Create event without pathParameters
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Call the Lambda handler
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
        assert 'missing' in body['error'].lower()
        
        # Create event with empty pathParameters
        event = {
            'pathParameters': {},
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        result = lambda_handler(event, lambda_context)
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
    
    @patch('get_task.get_dynamodb_client')
    @patch.dict(os.environ, {
        'TASKS_TABLE_NAME': 'ai-ppt-assistant-dev-tasks',
        'LOG_LEVEL': 'DEBUG',
        'AWS_REGION': 'us-east-1'
    })
    def test_get_task_dynamodb_error(self, mock_get_dynamodb_client, lambda_context, valid_task_id):
        """Test proper error handling for DynamoDB connection errors."""
        # Mock DynamoDB client
        mock_dynamodb = MagicMock()
        mock_get_dynamodb_client.return_value = mock_dynamodb
        
        # Mock DynamoDB get_item to raise an error
        mock_dynamodb.get_item.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'Requested resource not found'
                }
            },
            'GetItem'
        )
        
        # Import the Lambda handler
        from get_task import lambda_handler
        
        # Create the event
        event = {
            'pathParameters': {
                'task_id': valid_task_id
            },
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Call the Lambda handler
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 500
        assert 'headers' in result
        assert result['headers']['Content-Type'] == 'application/json'
        
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
        assert 'database' in body['error'].lower() or 'dynamodb' in body['error'].lower()
        
        # Verify DynamoDB was called
        mock_dynamodb.get_item.assert_called_once()
    
    @patch('get_task.get_dynamodb_client')
    @patch.dict(os.environ, {
        'TASKS_TABLE_NAME': 'ai-ppt-assistant-dev-tasks',
        'LOG_LEVEL': 'DEBUG',
        'AWS_REGION': 'us-east-1'
    })
    def test_get_task_throttling_error(self, mock_get_dynamodb_client, lambda_context, valid_task_id):
        """Test handling of DynamoDB throttling errors."""
        # Mock DynamoDB client
        mock_dynamodb = MagicMock()
        mock_get_dynamodb_client.return_value = mock_dynamodb
        
        # Mock DynamoDB get_item to raise throttling error
        mock_dynamodb.get_item.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'ProvisionedThroughputExceededException',
                    'Message': 'The level of configured provisioned throughput for the table was exceeded'
                }
            },
            'GetItem'
        )
        
        # Import the Lambda handler
        from get_task import lambda_handler
        
        # Create the event
        event = {
            'pathParameters': {
                'task_id': valid_task_id
            },
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Call the Lambda handler
        result = lambda_handler(event, lambda_context)
        
        # Assertions - should return 503 Service Unavailable for throttling
        assert result['statusCode'] == 503
        assert 'headers' in result
        assert result['headers']['Content-Type'] == 'application/json'
        assert 'Retry-After' in result['headers']  # Should include retry header
        
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
        assert 'throttl' in body['error'].lower() or 'temporarily unavailable' in body['error'].lower()
    
    @patch('get_task.get_dynamodb_client')
    @patch.dict(os.environ, {
        'TASKS_TABLE_NAME': 'ai-ppt-assistant-dev-tasks',
        'LOG_LEVEL': 'DEBUG',
        'AWS_REGION': 'us-east-1'
    })
    def test_get_task_with_complex_metadata(self, mock_get_dynamodb_client, lambda_context):
        """Test retrieval of task with complex nested metadata."""
        task_id = str(uuid.uuid4())
        
        # Mock DynamoDB client
        mock_dynamodb = MagicMock()
        mock_get_dynamodb_client.return_value = mock_dynamodb
        
        # Mock DynamoDB response with complex metadata
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'task_id': {'S': task_id},
                'presentation_id': {'S': str(uuid.uuid4())},
                'status': {'S': 'completed'},
                'task_type': {'S': 'compile_pptx'},
                'created_at': {'S': datetime.now(timezone.utc).isoformat()},
                'updated_at': {'S': datetime.now(timezone.utc).isoformat()},
                'progress': {'N': '100'},
                'metadata': {'M': {
                    'slides': {'L': [
                        {'M': {
                            'slide_id': {'S': 'slide-1'},
                            'title': {'S': 'Introduction'},
                            'content_generated': {'BOOL': True}
                        }},
                        {'M': {
                            'slide_id': {'S': 'slide-2'},
                            'title': {'S': 'Main Content'},
                            'content_generated': {'BOOL': True}
                        }}
                    ]},
                    'style': {'S': 'professional'},
                    'theme': {'S': 'dark'},
                    'total_slides': {'N': '10'},
                    'generation_params': {'M': {
                        'model': {'S': 'claude-3'},
                        'temperature': {'N': '0.7'}
                    }}
                }},
                'result': {'M': {
                    'pptx_url': {'S': 's3://bucket/presentations/file.pptx'},
                    'file_size': {'N': '2048576'},
                    'generation_time': {'N': '45.5'}
                }},
                'retry_count': {'N': '0'},
                'ttl': {'N': str(int(datetime.now(timezone.utc).timestamp()) + 86400)}
            }
        }
        
        # Import the Lambda handler
        from get_task import lambda_handler
        
        # Create the event
        event = {
            'pathParameters': {
                'task_id': task_id
            },
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Call the Lambda handler
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert body['task']['status'] == 'completed'
        assert body['task']['progress'] == 100
        
        # Verify complex metadata is properly deserialized
        assert 'metadata' in body['task']
        assert 'slides' in body['task']['metadata']
        assert len(body['task']['metadata']['slides']) == 2
        assert body['task']['metadata']['slides'][0]['title'] == 'Introduction'
        assert body['task']['metadata']['generation_params']['temperature'] == 0.7
        
        # Verify result is properly deserialized
        assert 'result' in body['task']
        assert body['task']['result']['file_size'] == 2048576
        assert body['task']['result']['generation_time'] == 45.5
    
    @patch('get_task.get_dynamodb_client')
    @patch.dict(os.environ, {})  # Empty environment
    def test_get_task_missing_environment_variables(self, mock_get_dynamodb_client, lambda_context, valid_task_id):
        """Test proper error handling when required environment variables are missing."""
        # Import the Lambda handler
        from get_task import lambda_handler
        
        # Create the event
        event = {
            'pathParameters': {
                'task_id': valid_task_id
            },
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Call the Lambda handler
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
        assert 'configuration' in body['error'].lower() or 'environment' in body['error'].lower()


class TestGetTaskHelperFunctions:
    """Test helper functions in the get_task module."""
    
    def test_validate_uuid_format(self):
        """Test UUID validation helper function."""
        from get_task import validate_uuid
        
        # Valid UUIDs
        assert validate_uuid(str(uuid.uuid4())) is True
        assert validate_uuid('550e8400-e29b-41d4-a716-446655440000') is True
        assert validate_uuid('6ba7b810-9dad-11d1-80b4-00c04fd430c8') is True
        
        # Invalid UUIDs
        assert validate_uuid('invalid-uuid') is False
        assert validate_uuid('123') is False
        assert validate_uuid('') is False
        assert validate_uuid(None) is False
        assert validate_uuid('550e8400-e29b-41d4-a716-44665544000g') is False  # Invalid character
        assert validate_uuid('550e8400e29b41d4a716446655440000') is False  # Missing hyphens
    
    def test_deserialize_dynamodb_item(self):
        """Test DynamoDB item deserialization helper function."""
        from get_task import deserialize_dynamodb_item
        
        # Sample DynamoDB item
        dynamodb_item = {
            'task_id': {'S': 'test-id'},
            'status': {'S': 'processing'},
            'progress': {'N': '50'},
            'is_active': {'BOOL': True},
            'tags': {'L': [
                {'S': 'tag1'},
                {'S': 'tag2'}
            ]},
            'metadata': {'M': {
                'key': {'S': 'value'},
                'count': {'N': '10'}
            }},
            'null_field': {'NULL': True}
        }
        
        # Deserialize
        result = deserialize_dynamodb_item(dynamodb_item)
        
        # Assertions
        assert result['task_id'] == 'test-id'
        assert result['status'] == 'processing'
        assert result['progress'] == 50
        assert result['is_active'] is True
        assert result['tags'] == ['tag1', 'tag2']
        assert result['metadata']['key'] == 'value'
        assert result['metadata']['count'] == 10
        assert result['null_field'] is None
    
    def test_format_error_response(self):
        """Test error response formatting helper function."""
        from get_task import format_error_response
        
        # Test different error codes and messages
        response = format_error_response(400, "Invalid request")
        assert response['statusCode'] == 400
        assert json.loads(response['body'])['success'] is False
        assert json.loads(response['body'])['error'] == "Invalid request"
        
        response = format_error_response(404, "Task not found")
        assert response['statusCode'] == 404
        assert json.loads(response['body'])['error'] == "Task not found"
        
        response = format_error_response(500, "Internal server error")
        assert response['statusCode'] == 500
        assert json.loads(response['body'])['error'] == "Internal server error"


# Performance and Edge Case Tests
class TestGetTaskPerformance:
    """Test performance-related aspects and edge cases."""
    
    @patch('get_task.get_dynamodb_client')
    @patch.dict(os.environ, {
        'TASKS_TABLE_NAME': 'ai-ppt-assistant-dev-tasks',
        'LOG_LEVEL': 'DEBUG',
        'AWS_REGION': 'us-east-1'
    })
    def test_get_task_large_metadata(self, mock_get_dynamodb_client, lambda_context):
        """Test handling of tasks with very large metadata."""
        task_id = str(uuid.uuid4())
        
        # Create large metadata (but within DynamoDB limits)
        large_metadata = {
            'slides': [
                {
                    'slide_id': f'slide-{i}',
                    'title': f'Slide {i} Title',
                    'content': 'Lorem ipsum ' * 100,  # Large content
                    'speaker_notes': 'Notes ' * 50
                }
                for i in range(50)  # 50 slides
            ]
        }
        
        # Mock DynamoDB client
        mock_dynamodb = MagicMock()
        mock_get_dynamodb_client.return_value = mock_dynamodb
        
        # Convert metadata to DynamoDB format
        metadata_dynamodb = {'M': {}}
        metadata_dynamodb['M']['slides'] = {
            'L': [
                {'M': {
                    'slide_id': {'S': slide['slide_id']},
                    'title': {'S': slide['title']},
                    'content': {'S': slide['content']},
                    'speaker_notes': {'S': slide['speaker_notes']}
                }}
                for slide in large_metadata['slides']
            ]
        }
        
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'task_id': {'S': task_id},
                'presentation_id': {'S': str(uuid.uuid4())},
                'status': {'S': 'completed'},
                'task_type': {'S': 'generate_content'},
                'created_at': {'S': datetime.now(timezone.utc).isoformat()},
                'updated_at': {'S': datetime.now(timezone.utc).isoformat()},
                'progress': {'N': '100'},
                'metadata': metadata_dynamodb,
                'retry_count': {'N': '0'},
                'ttl': {'N': str(int(datetime.now(timezone.utc).timestamp()) + 86400)}
            }
        }
        
        # Import the Lambda handler
        from get_task import lambda_handler
        
        # Create the event
        event = {
            'pathParameters': {
                'task_id': task_id
            },
            'httpMethod': 'GET',
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Call the Lambda handler
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert len(body['task']['metadata']['slides']) == 50
        
        # Verify the response size is reasonable (should be compressed in real scenario)
        response_size = len(json.dumps(body))
        assert response_size < 6_000_000  # Lambda response limit is 6MB