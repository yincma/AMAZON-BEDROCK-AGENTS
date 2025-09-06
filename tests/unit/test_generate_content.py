"""
Unit tests for generate_content Lambda function.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/controllers'))

@pytest.fixture
def lambda_context():
    """Mock Lambda context object."""
    context = Mock()
    context.function_name = 'test-generate-content'
    context.memory_limit_in_mb = 2048
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'
    context.aws_request_id = 'test-request-id'
    return context

@pytest.fixture
def valid_outline():
    """Valid outline for content generation."""
    return {
        'title': 'AI and Machine Learning',
        'slides': [
            {
                'title': 'Introduction',
                'key_points': ['What is AI?', 'Why it matters']
            },
            {
                'title': 'Machine Learning Basics',
                'key_points': ['Supervised Learning', 'Unsupervised Learning']
            }
        ]
    }

class TestGenerateContent:
    """Test suite for generate_content function."""
    
    @patch('generate_content.boto3.client')
    @patch('generate_content.concurrent.futures.ThreadPoolExecutor')
    def test_generate_content_success(self, mock_executor, mock_boto_client, valid_outline, lambda_context):
        """Test successful content generation."""
        # Mock Bedrock client
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Mock Bedrock response for each slide
        mock_response = {
            'body': MagicMock()
        }
        mock_response['body'].read.return_value = json.dumps({
            'content': [
                {
                    'text': json.dumps({
                        'title': 'Introduction',
                        'content': 'Welcome to AI and Machine Learning',
                        'bullet_points': ['AI is transforming industries', 'ML enables intelligent systems'],
                        'speaker_notes': 'Start with a brief overview'
                    })
                }
            ]
        }).encode('utf-8')
        mock_bedrock.invoke_model.return_value = mock_response
        
        # Mock ThreadPoolExecutor
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        mock_future = MagicMock()
        mock_future.result.return_value = {
            'title': 'Introduction',
            'content': 'Welcome to AI and Machine Learning',
            'bullet_points': ['AI is transforming industries', 'ML enables intelligent systems']
        }
        mock_executor_instance.submit.return_value = mock_future
        
        from generate_content import lambda_handler
        
        event = {
            'outline': valid_outline,
            'style': 'professional',
            'detail_level': 'medium'
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert 'slides' in body
        assert len(body['slides']) > 0
    
    @patch('generate_content.boto3.client')
    def test_generate_content_missing_outline(self, mock_boto_client, lambda_context):
        """Test handling of missing outline."""
        from generate_content import lambda_handler
        
        event = {
            'style': 'professional'
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'outline' in body['error'].lower()
    
    @patch('generate_content.boto3.client')
    def test_generate_content_empty_slides(self, mock_boto_client, lambda_context):
        """Test handling of empty slides list."""
        from generate_content import lambda_handler
        
        event = {
            'outline': {
                'title': 'Empty Presentation',
                'slides': []
            }
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
    
    @patch('generate_content.boto3.client')
    @patch('generate_content.concurrent.futures.ThreadPoolExecutor')
    def test_generate_content_parallel_processing(self, mock_executor, mock_boto_client, lambda_context):
        """Test parallel processing of multiple slides."""
        # Setup mocks
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Mock executor for parallel processing
        mock_executor_instance = MagicMock()
        mock_executor.return_value.__enter__.return_value = mock_executor_instance
        
        # Create multiple mock futures
        futures = []
        for i in range(5):
            mock_future = MagicMock()
            mock_future.result.return_value = {
                'title': f'Slide {i+1}',
                'content': f'Content for slide {i+1}',
                'bullet_points': [f'Point {i+1}']
            }
            futures.append(mock_future)
        
        mock_executor_instance.submit.side_effect = futures
        
        from generate_content import lambda_handler
        
        outline = {
            'title': 'Large Presentation',
            'slides': [{'title': f'Slide {i+1}', 'key_points': ['Point']} for i in range(5)]
        }
        
        event = {
            'outline': outline,
            'style': 'professional'
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert len(body['slides']) == 5
        # Verify parallel processing was used
        assert mock_executor_instance.submit.call_count == 5
    
    @patch('generate_content.boto3.client')
    def test_generate_content_bedrock_error(self, mock_boto_client, valid_outline, lambda_context):
        """Test handling of Bedrock API errors."""
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        mock_bedrock.invoke_model.side_effect = Exception('Bedrock timeout')
        
        from generate_content import lambda_handler
        
        event = {
            'outline': valid_outline,
            'style': 'professional'
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body

if __name__ == '__main__':
    pytest.main([__file__, '-v'])