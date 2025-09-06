"""
Unit tests for API Lambda functions.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/api'))

@pytest.fixture
def lambda_context():
    """Mock Lambda context object."""
    context = Mock()
    context.function_name = 'test-api'
    context.memory_limit_in_mb = 512
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'
    context.aws_request_id = 'test-request-id'
    return context

class TestGeneratePresentationAPI:
    """Test suite for generate_presentation API endpoint."""
    
    @patch('generate_presentation.boto3.client')
    @patch('generate_presentation.uuid.uuid4')
    def test_generate_presentation_success(self, mock_uuid, mock_boto_client, lambda_context):
        """Test successful presentation generation request."""
        # Mock UUID
        mock_uuid.return_value = 'test-presentation-id'
        
        # Mock clients
        mock_dynamodb = MagicMock()
        mock_sqs = MagicMock()
        mock_bedrock = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'dynamodb':
                return mock_dynamodb
            elif service_name == 'sqs':
                return mock_sqs
            elif service_name == 'bedrock-runtime':
                return mock_bedrock
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Mock Bedrock agent response
        mock_bedrock.invoke_agent.return_value = {
            'completion': 'Agent started processing'
        }
        
        from generate_presentation import lambda_handler
        
        event = {
            'body': json.dumps({
                'topic': 'AI and ML',
                'target_audience': 'Engineers',
                'duration': 30,
                'style': 'technical'
            })
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 202
        body = json.loads(result['body'])
        assert body['success'] is True
        assert 'presentation_id' in body
        assert body['presentation_id'] == 'test-presentation-id'
        assert 'status' in body
        assert body['status'] == 'processing'
        
        # Verify DynamoDB was called
        mock_dynamodb.put_item.assert_called_once()
        # Verify SQS was called
        mock_sqs.send_message.assert_called_once()
    
    @patch('generate_presentation.boto3.client')
    def test_generate_presentation_invalid_request(self, mock_boto_client, lambda_context):
        """Test handling of invalid request body."""
        from generate_presentation import lambda_handler
        
        event = {
            'body': json.dumps({
                # Missing required 'topic' field
                'duration': 30
            })
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'topic' in body['error'].lower()
    
    @patch('generate_presentation.boto3.client')
    def test_generate_presentation_malformed_json(self, mock_boto_client, lambda_context):
        """Test handling of malformed JSON."""
        from generate_presentation import lambda_handler
        
        event = {
            'body': 'invalid json {{'
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False

class TestPresentationStatusAPI:
    """Test suite for presentation_status API endpoint."""
    
    @patch('presentation_status.boto3.client')
    def test_get_status_success(self, mock_boto_client, lambda_context):
        """Test successful status retrieval."""
        # Mock DynamoDB
        mock_dynamodb = MagicMock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock DynamoDB response
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'presentation_id': {'S': 'test-123'},
                'status': {'S': 'completed'},
                'progress': {'N': '100'},
                'created_at': {'S': '2024-01-01T00:00:00Z'},
                'file_key': {'S': 'presentations/test-123.pptx'}
            }
        }
        
        from presentation_status import lambda_handler
        
        event = {
            'pathParameters': {
                'id': 'test-123'
            }
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert body['status'] == 'completed'
        assert body['progress'] == 100
    
    @patch('presentation_status.boto3.client')
    def test_get_status_not_found(self, mock_boto_client, lambda_context):
        """Test status retrieval for non-existent presentation."""
        # Mock DynamoDB
        mock_dynamodb = MagicMock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock empty response
        mock_dynamodb.get_item.return_value = {}
        
        from presentation_status import lambda_handler
        
        event = {
            'pathParameters': {
                'id': 'non-existent'
            }
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 404
        body = json.loads(result['body'])
        assert body['success'] is False

class TestPresentationDownloadAPI:
    """Test suite for presentation_download API endpoint."""
    
    @patch('presentation_download.boto3.client')
    def test_download_success(self, mock_boto_client, lambda_context):
        """Test successful download URL generation."""
        # Mock clients
        mock_dynamodb = MagicMock()
        mock_s3 = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'dynamodb':
                return mock_dynamodb
            elif service_name == 's3':
                return mock_s3
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Mock DynamoDB response
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'presentation_id': {'S': 'test-123'},
                'status': {'S': 'completed'},
                'file_key': {'S': 'presentations/test-123.pptx'}
            }
        }
        
        # Mock S3 presigned URL
        mock_s3.generate_presigned_url.return_value = 'https://s3.amazonaws.com/bucket/test-123.pptx?signature=xxx'
        
        from presentation_download import lambda_handler
        
        event = {
            'pathParameters': {
                'id': 'test-123'
            },
            'queryStringParameters': {
                'format': 'pptx'
            }
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert 'download_url' in body
        assert body['download_url'].startswith('https://')
        assert 'expires_in' in body
    
    @patch('presentation_download.boto3.client')
    def test_download_not_ready(self, mock_boto_client, lambda_context):
        """Test download attempt for incomplete presentation."""
        # Mock DynamoDB
        mock_dynamodb = MagicMock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock in-progress presentation
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'presentation_id': {'S': 'test-123'},
                'status': {'S': 'processing'},
                'progress': {'N': '50'}
            }
        }
        
        from presentation_download import lambda_handler
        
        event = {
            'pathParameters': {
                'id': 'test-123'
            }
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'not ready' in body['error'].lower()

class TestModifySlideAPI:
    """Test suite for modify_slide API endpoint."""
    
    @patch('modify_slide.boto3.client')
    def test_modify_slide_content(self, mock_boto_client, lambda_context):
        """Test successful slide content modification."""
        # Mock clients
        mock_dynamodb = MagicMock()
        mock_sqs = MagicMock()
        mock_bedrock = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'dynamodb':
                return mock_dynamodb
            elif service_name == 'sqs':
                return mock_sqs
            elif service_name == 'bedrock-runtime':
                return mock_bedrock
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Mock DynamoDB response
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'presentation_id': {'S': 'test-123'},
                'status': {'S': 'completed'},
                'slides': {'L': [
                    {'M': {'slide_id': {'S': 'slide-1'}, 'title': {'S': 'Original Title'}}}
                ]}
            }
        }
        
        from modify_slide import lambda_handler
        
        event = {
            'pathParameters': {
                'id': 'test-123',
                'slideId': 'slide-1'
            },
            'body': json.dumps({
                'modification_type': 'content',
                'new_content': 'Updated content for the slide'
            })
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 202
        body = json.loads(result['body'])
        assert body['success'] is True
        assert body['status'] == 'processing'
        
        # Verify update was queued
        mock_sqs.send_message.assert_called_once()
    
    @patch('modify_slide.boto3.client')
    def test_modify_slide_invalid_type(self, mock_boto_client, lambda_context):
        """Test handling of invalid modification type."""
        from modify_slide import lambda_handler
        
        event = {
            'pathParameters': {
                'id': 'test-123',
                'slideId': 'slide-1'
            },
            'body': json.dumps({
                'modification_type': 'invalid_type',
                'new_content': 'Some content'
            })
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'modification_type' in body['error'].lower()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])