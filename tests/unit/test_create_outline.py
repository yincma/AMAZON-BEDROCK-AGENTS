"""
Unit tests for create_outline Lambda function.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path for Lambda function imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/controllers'))

@pytest.fixture
def lambda_context():
    """Mock Lambda context object."""
    context = Mock()
    context.function_name = 'test-function'
    context.memory_limit_in_mb = 1024
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'
    context.aws_request_id = 'test-request-id'
    return context

@pytest.fixture
def valid_event():
    """Valid Lambda event for testing."""
    return {
        'topic': 'AI and Machine Learning',
        'target_audience': 'Technical professionals',
        'duration': 30,
        'slide_count': 10,
        'style': 'professional',
        'language': 'en'
    }

class TestCreateOutline:
    """Test suite for create_outline function."""
    
    @patch('create_outline.boto3.client')
    def test_create_outline_success(self, mock_boto_client, valid_event, lambda_context):
        """Test successful outline creation."""
        # Mock Bedrock client
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Mock Bedrock response
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': json.dumps({
                        'title': 'AI and Machine Learning',
                        'slides': [
                            {'title': 'Introduction', 'key_points': ['Overview', 'Objectives']},
                            {'title': 'Core Concepts', 'key_points': ['Neural Networks', 'Deep Learning']}
                        ]
                    })
                }
            ]
        }).encode('utf-8')
        mock_bedrock.invoke_model.return_value = mock_response
        
        # Import and test
        from create_outline import lambda_handler
        result = lambda_handler(valid_event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert 'outline' in body
        assert body['outline']['title'] == 'AI and Machine Learning'
        assert len(body['outline']['slides']) == 2
        
    @patch('create_outline.boto3.client')
    def test_create_outline_missing_topic(self, mock_boto_client, lambda_context):
        """Test handling of missing topic parameter."""
        from create_outline import lambda_handler
        
        # Event without topic
        event = {
            'target_audience': 'Technical professionals',
            'duration': 30
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
        assert 'topic' in body['error'].lower()
    
    @patch('create_outline.boto3.client')
    def test_create_outline_bedrock_error(self, mock_boto_client, valid_event, lambda_context):
        """Test handling of Bedrock API errors."""
        # Mock Bedrock client to raise exception
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        mock_bedrock.invoke_model.side_effect = Exception('Bedrock service error')
        
        from create_outline import lambda_handler
        result = lambda_handler(valid_event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
        
    @patch('create_outline.boto3.client')
    def test_create_outline_invalid_language(self, mock_boto_client, lambda_context):
        """Test handling of invalid language code."""
        from create_outline import lambda_handler
        
        event = {
            'topic': 'AI and Machine Learning',
            'language': 'invalid_lang',
            'duration': 30
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions - should use default language
        assert result['statusCode'] in [200, 400]
    
    @patch('create_outline.boto3.client')
    def test_create_outline_with_custom_parameters(self, mock_boto_client, lambda_context):
        """Test outline creation with custom parameters."""
        # Mock Bedrock client
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Mock response
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': json.dumps({
                        'title': 'Technical Deep Dive',
                        'slides': [{'title': 'Slide 1', 'key_points': ['Point 1']}] * 15
                    })
                }
            ]
        }).encode('utf-8')
        mock_bedrock.invoke_model.return_value = mock_response
        
        from create_outline import lambda_handler
        
        event = {
            'topic': 'Technical Deep Dive',
            'target_audience': 'Engineers',
            'duration': 60,
            'slide_count': 15,
            'style': 'technical'
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert len(body['outline']['slides']) == 15

# Test runner
if __name__ == '__main__':
    pytest.main([__file__, '-v'])