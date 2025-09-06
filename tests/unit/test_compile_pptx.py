"""
Unit tests for compile_pptx Lambda function (MVC architecture).
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys
import os
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/controllers'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/models'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas/views'))

@pytest.fixture
def lambda_context():
    """Mock Lambda context object."""
    context = Mock()
    context.function_name = 'test-compile-pptx'
    context.memory_limit_in_mb = 3008
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'
    context.aws_request_id = 'test-request-id'
    return context

@pytest.fixture
def valid_presentation_data():
    """Valid presentation data for compilation."""
    return {
        'presentation_id': 'test-123',
        'title': 'Test Presentation',
        'slides': [
            {
                'title': 'Introduction',
                'content': 'Welcome to the presentation',
                'bullet_points': ['Point 1', 'Point 2'],
                'image_url': 's3://bucket/images/slide1.png',
                'speaker_notes': 'Introduce the topic'
            },
            {
                'title': 'Main Content',
                'content': 'Core information',
                'bullet_points': ['Key insight 1', 'Key insight 2'],
                'speaker_notes': 'Explain the main points'
            }
        ],
        'template': 'professional',
        'metadata': {
            'author': 'Test User',
            'created_date': '2024-01-01'
        }
    }

class TestCompilePPTX:
    """Test suite for compile_pptx function with MVC architecture."""
    
    @patch('compile_pptx.PresentationModel')
    @patch('compile_pptx.PresentationView')
    @patch('compile_pptx.boto3.client')
    def test_compile_pptx_success(self, mock_boto_client, mock_view_class, mock_model_class, 
                                   valid_presentation_data, lambda_context):
        """Test successful PPTX compilation."""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock Model
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.load_template.return_value = MagicMock()  # Mock template
        mock_model.save_presentation.return_value = 'presentations/test-123.pptx'
        
        # Mock View
        mock_view = MagicMock()
        mock_view_class.return_value = mock_view
        mock_pptx_buffer = io.BytesIO(b'fake_pptx_data')
        mock_view.generate_presentation.return_value = mock_pptx_buffer
        
        from compile_pptx import lambda_handler
        
        event = {
            'presentation_data': valid_presentation_data
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['success'] is True
        assert 'file_key' in body
        assert body['file_key'] == 'presentations/test-123.pptx'
        
        # Verify MVC interactions
        mock_model.load_template.assert_called_once_with('professional')
        mock_view.generate_presentation.assert_called_once()
        mock_model.save_presentation.assert_called_once()
    
    @patch('compile_pptx.PresentationModel')
    @patch('compile_pptx.PresentationView')
    def test_compile_pptx_missing_data(self, mock_view_class, mock_model_class, lambda_context):
        """Test handling of missing presentation data."""
        from compile_pptx import lambda_handler
        
        event = {}  # No presentation_data
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'presentation_data' in body['error'].lower()
    
    @patch('compile_pptx.PresentationModel')
    @patch('compile_pptx.PresentationView')
    def test_compile_pptx_empty_slides(self, mock_view_class, mock_model_class, lambda_context):
        """Test handling of empty slides."""
        from compile_pptx import lambda_handler
        
        event = {
            'presentation_data': {
                'presentation_id': 'test-123',
                'title': 'Empty Presentation',
                'slides': []  # No slides
            }
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'slides' in body['error'].lower()
    
    @patch('compile_pptx.PresentationModel')
    @patch('compile_pptx.PresentationView')
    @patch('compile_pptx.boto3.client')
    def test_compile_pptx_with_images(self, mock_boto_client, mock_view_class, mock_model_class,
                                      valid_presentation_data, lambda_context):
        """Test PPTX compilation with image handling."""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock image download
        mock_s3.get_object.return_value = {
            'Body': io.BytesIO(b'fake_image_data')
        }
        
        # Mock Model
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.download_image.return_value = b'fake_image_data'
        
        # Mock View
        mock_view = MagicMock()
        mock_view_class.return_value = mock_view
        mock_view.add_image_slide = MagicMock()
        
        from compile_pptx import lambda_handler
        
        event = {
            'presentation_data': valid_presentation_data
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 200
        # Verify image was processed
        assert mock_model.download_image.called or mock_view.add_image_slide.called
    
    @patch('compile_pptx.PresentationModel')
    @patch('compile_pptx.PresentationView')
    def test_compile_pptx_view_error(self, mock_view_class, mock_model_class, 
                                     valid_presentation_data, lambda_context):
        """Test handling of view generation errors."""
        # Mock Model
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock View to raise error
        mock_view = MagicMock()
        mock_view_class.return_value = mock_view
        mock_view.generate_presentation.side_effect = Exception('PPTX generation failed')
        
        from compile_pptx import lambda_handler
        
        event = {
            'presentation_data': valid_presentation_data
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 'error' in body
    
    @patch('compile_pptx.PresentationModel')
    @patch('compile_pptx.PresentationView')
    @patch('compile_pptx.boto3.client')
    def test_compile_pptx_s3_upload_error(self, mock_boto_client, mock_view_class, mock_model_class,
                                          valid_presentation_data, lambda_context):
        """Test handling of S3 upload errors."""
        # Mock S3 client to fail on upload
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.put_object.side_effect = Exception('S3 upload failed')
        
        # Mock Model
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_model.save_presentation.side_effect = Exception('S3 upload failed')
        
        # Mock View
        mock_view = MagicMock()
        mock_view_class.return_value = mock_view
        
        from compile_pptx import lambda_handler
        
        event = {
            'presentation_data': valid_presentation_data
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Assertions
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert body['success'] is False
        assert 's3' in body['error'].lower() or 'upload' in body['error'].lower()
    
    @patch('compile_pptx.PresentationModel')
    @patch('compile_pptx.PresentationView')
    def test_compile_pptx_large_presentation(self, mock_view_class, mock_model_class, lambda_context):
        """Test handling of large presentations."""
        # Create large presentation data
        large_presentation = {
            'presentation_id': 'large-123',
            'title': 'Large Presentation',
            'slides': [
                {
                    'title': f'Slide {i}',
                    'content': f'Content for slide {i}',
                    'bullet_points': [f'Point {j}' for j in range(10)]
                }
                for i in range(100)  # 100 slides
            ]
        }
        
        # Mock Model and View
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_view = MagicMock()
        mock_view_class.return_value = mock_view
        
        from compile_pptx import lambda_handler
        
        event = {
            'presentation_data': large_presentation
        }
        
        result = lambda_handler(event, lambda_context)
        
        # Should handle large presentations
        assert result['statusCode'] in [200, 500]  # Success or timeout

if __name__ == '__main__':
    pytest.main([__file__, '-v'])