"""
Unit tests for generate_image Lambda function.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import base64
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/controllers'))

@pytest.fixture
def lambda_context():
    """Mock Lambda context object."""
    context = Mock()
    context.function_name = 'test-generate-image'
    context.memory_limit_in_mb = 1024
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'
    context.aws_request_id = 'test-request-id'
    return context

@pytest.fixture
def valid_event():
    """Valid event for image generation."""
    return {
        'slide_title': 'Introduction to AI',
        'slide_content': 'AI is transforming the world',
        'style': 'professional',
        'image_type': 'conceptual'
    }

class TestGenerateImage:
    """Test suite for generate_image function."""
    
    @patch('generate_image.boto3.client')
    def test_generate_image_success(self, mock_boto_client, valid_event, lambda_context):
        """Test successful image generation."""
        # Mock Bedrock and S3 clients
        mock_bedrock = MagicMock()
        mock_s3 = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return mock_bedrock
            elif service_name == 's3':
                return mock_s3
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Mock Nova image generation response
        mock_image_data = b'fake_image_data'
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'images': [base64.b64encode(mock_image_data).decode('utf-8')]
        }).encode('utf-8')
        mock_bedrock.invoke_model.return_value = mock_response
        
        # Mock S3 upload
        mock_s3.put_object.return_value = {'ETag': '"abc123"'}
        
        from generate_image import lambda_handler
        result = lambda_handler(valid_event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert 'image_url' in body
        assert body['image_url'].startswith('s3://')
        
        # Verify S3 upload was called
        mock_s3.put_object.assert_called_once()
    
    @patch('generate_image.boto3.client')
    def test_generate_image_nova_failure_with_fallback(self, mock_boto_client, valid_event, lambda_context):
        """Test fallback to placeholder when Nova fails."""
        # Mock clients
        mock_bedrock = MagicMock()
        mock_s3 = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return mock_bedrock
            elif service_name == 's3':
                return mock_s3
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Mock Nova failure
        mock_bedrock.invoke_model.side_effect = Exception('Nova service unavailable')
        
        from generate_image import lambda_handler
        result = lambda_handler(valid_event, lambda_context)
        
        # Assertions - should return placeholder
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert 'image_url' in body
        assert 'placeholder' in body['image_url']
    
    @patch('generate_image.boto3.client')
    def test_generate_image_missing_parameters(self, mock_boto_client, lambda_context):
        """Test handling of missing required parameters."""
        from generate_image import lambda_handler
        
        event = {
            'style': 'professional'
            # Missing slide_title and slide_content
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
    
    @patch('generate_image.boto3.client')
    def test_generate_image_prompt_optimization(self, mock_boto_client, lambda_context):
        """Test image prompt optimization."""
        # Mock clients
        mock_bedrock = MagicMock()
        mock_s3 = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return mock_bedrock
            elif service_name == 's3':
                return mock_s3
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Capture the prompt sent to Nova
        def capture_prompt(*args, **kwargs):
            body = json.loads(kwargs.get('body', '{}'))
            assert 'prompt' in body
            assert 'professional' in body['prompt'].lower()
            assert 'ai' in body['prompt'].lower()
            
            return {
                'body': MagicMock(read=lambda: json.dumps({
                    'images': [base64.b64encode(b'image').decode('utf-8')]
                }).encode('utf-8'))
            }
        
        mock_bedrock.invoke_model.side_effect = capture_prompt
        
        from generate_image import lambda_handler
        
        event = {
            'slide_title': 'AI Revolution',
            'slide_content': 'How AI is changing industries',
            'style': 'professional',
            'image_type': 'conceptual',
            'color_scheme': 'blue'
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        mock_bedrock.invoke_model.assert_called_once()
    
    @patch('generate_image.boto3.client')
    @patch('generate_image.os.environ')
    def test_generate_image_with_environment_config(self, mock_environ, mock_boto_client, valid_event, lambda_context):
        """Test image generation with environment configuration."""
        # Set environment variables
        mock_environ.get.side_effect = lambda key, default=None: {
            'S3_BUCKET': 'test-bucket',
            'NOVA_MODEL_ID': 'amazon.nova-canvas-v1:0',
            'LOG_LEVEL': 'DEBUG'
        }.get(key, default)
        
        # Mock clients
        mock_bedrock = MagicMock()
        mock_s3 = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'bedrock-runtime':
                return mock_bedrock
            elif service_name == 's3':
                return mock_s3
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Mock successful response
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'images': [base64.b64encode(b'image_data').decode('utf-8')]
        }).encode('utf-8')
        mock_bedrock.invoke_model.return_value = mock_response
        
        from generate_image import lambda_handler
        result = lambda_handler(valid_event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        
        # Verify correct bucket was used
        s3_call_args = mock_s3.put_object.call_args
        assert s3_call_args[1]['Bucket'] == 'test-bucket'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])