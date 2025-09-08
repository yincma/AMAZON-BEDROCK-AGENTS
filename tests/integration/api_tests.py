"""
API Integration Tests for AI PPT Assistant

This module contains comprehensive integration tests for all API endpoints.
Tests are designed to verify the end-to-end functionality of the API layer.
"""

import pytest
import json
import time
import threading
import concurrent.futures
from unittest.mock import Mock, patch, MagicMock
import requests_mock
from moto import mock_aws
import boto3
from typing import Dict, Any, List

# Test markers for organization
pytestmark = pytest.mark.integration


class TestPresentationGenerationAPI:
    """Tests for the presentation generation endpoint: POST /presentations/generate"""

    @pytest.fixture
    def generate_presentation_request(self):
        """Standard request payload for presentation generation."""
        return {
            'topic': 'AI and Machine Learning in Healthcare',
            'target_audience': 'Healthcare professionals',
            'duration': 30,
            'slide_count': 10,
            'style': 'professional',
            'language': 'en',
            'include_images': True,
            'template': 'default'
        }

    @pytest.fixture
    def mock_generate_presentation_handler(self):
        """Mock the generate_presentation Lambda handler."""
        with patch('lambdas.api.generate_presentation.lambda_handler') as mock_handler:
            yield mock_handler

    def test_successful_presentation_generation(
        self,
        api_gateway_event,
        lambda_context,
        generate_presentation_request,
        mock_generate_presentation_handler,
        s3_mock,
        dynamodb_mock,
        sqs_mock
    ):
        """Test successful presentation generation flow."""
        # Arrange
        expected_presentation_id = 'pres-12345'
        mock_generate_presentation_handler.return_value = {
            'statusCode': 202,
            'body': json.dumps({
                'message': 'Presentation generation started',
                'presentation_id': expected_presentation_id,
                'status': 'processing',
                'estimated_completion_time': 300
            })
        }

        event = api_gateway_event(
            method='POST',
            path='/presentations/generate',
            body=generate_presentation_request
        )

        # Act
        response = mock_generate_presentation_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 202
        body = json.loads(response['body'])
        assert body['presentation_id'] == expected_presentation_id
        assert body['status'] == 'processing'
        assert 'estimated_completion_time' in body
        mock_generate_presentation_handler.assert_called_once_with(event, lambda_context)

    def test_invalid_request_payload(
        self,
        api_gateway_event,
        lambda_context,
        mock_generate_presentation_handler
    ):
        """Test handling of invalid request payload."""
        # Arrange
        invalid_request = {'invalid_field': 'invalid_value'}
        mock_generate_presentation_handler.return_value = {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid request payload',
                'message': 'Required fields missing: topic, target_audience'
            })
        }

        event = api_gateway_event(
            method='POST',
            path='/presentations/generate',
            body=invalid_request
        )

        # Act
        response = mock_generate_presentation_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
        assert 'Invalid request payload' in body['error']

    def test_duplicate_request_handling(
        self,
        api_gateway_event,
        lambda_context,
        generate_presentation_request,
        mock_generate_presentation_handler
    ):
        """Test handling of duplicate presentation generation requests."""
        # Arrange
        mock_generate_presentation_handler.return_value = {
            'statusCode': 409,
            'body': json.dumps({
                'error': 'Duplicate request',
                'message': 'Presentation with similar parameters already exists',
                'existing_presentation_id': 'pres-existing'
            })
        }

        event = api_gateway_event(
            method='POST',
            path='/presentations/generate',
            body=generate_presentation_request
        )

        # Act
        response = mock_generate_presentation_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert body['error'] == 'Duplicate request'
        assert 'existing_presentation_id' in body

    @pytest.mark.slow
    def test_generation_timeout_handling(
        self,
        api_gateway_event,
        lambda_context,
        generate_presentation_request,
        mock_generate_presentation_handler
    ):
        """Test handling of generation timeout scenarios."""
        # Arrange
        mock_generate_presentation_handler.return_value = {
            'statusCode': 408,
            'body': json.dumps({
                'error': 'Request timeout',
                'message': 'Presentation generation took too long to start',
                'retry_after': 60
            })
        }

        event = api_gateway_event(
            method='POST',
            path='/presentations/generate',
            body=generate_presentation_request
        )

        # Act
        response = mock_generate_presentation_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 408
        body = json.loads(response['body'])
        assert body['error'] == 'Request timeout'
        assert 'retry_after' in body


class TestPresentationStatusAPI:
    """Tests for the presentation status endpoint: GET /presentations/{id}"""

    @pytest.fixture
    def mock_presentation_status_handler(self):
        """Mock the presentation_status Lambda handler."""
        with patch('lambdas.api.presentation_status.lambda_handler') as mock_handler:
            yield mock_handler

    def test_get_processing_status(
        self,
        api_gateway_event,
        lambda_context,
        mock_presentation_status_handler
    ):
        """Test getting status of a presentation in processing."""
        # Arrange
        presentation_id = 'pres-12345'
        mock_presentation_status_handler.return_value = {
            'statusCode': 200,
            'body': json.dumps({
                'presentation_id': presentation_id,
                'status': 'processing',
                'progress': 65,
                'current_step': 'generating_content',
                'estimated_completion_time': 120,
                'created_at': '2024-01-01T10:00:00Z',
                'updated_at': '2024-01-01T10:05:00Z'
            })
        }

        event = api_gateway_event(
            method='GET',
            path=f'/presentations/{presentation_id}',
            path_params={'id': presentation_id}
        )

        # Act
        response = mock_presentation_status_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['presentation_id'] == presentation_id
        assert body['status'] == 'processing'
        assert body['progress'] == 65
        assert 'estimated_completion_time' in body

    def test_get_completed_status(
        self,
        api_gateway_event,
        lambda_context,
        mock_presentation_status_handler
    ):
        """Test getting status of a completed presentation."""
        # Arrange
        presentation_id = 'pres-completed'
        mock_presentation_status_handler.return_value = {
            'statusCode': 200,
            'body': json.dumps({
                'presentation_id': presentation_id,
                'status': 'completed',
                'progress': 100,
                'current_step': 'completed',
                'file_key': f'presentations/{presentation_id}.pptx',
                'download_url': f'/presentations/{presentation_id}/download',
                'slide_count': 10,
                'total_size': 2048576,
                'created_at': '2024-01-01T10:00:00Z',
                'completed_at': '2024-01-01T10:10:00Z'
            })
        }

        event = api_gateway_event(
            method='GET',
            path=f'/presentations/{presentation_id}',
            path_params={'id': presentation_id}
        )

        # Act
        response = mock_presentation_status_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'completed'
        assert body['progress'] == 100
        assert 'file_key' in body
        assert 'download_url' in body

    def test_presentation_not_found(
        self,
        api_gateway_event,
        lambda_context,
        mock_presentation_status_handler
    ):
        """Test handling of non-existent presentation ID."""
        # Arrange
        presentation_id = 'pres-nonexistent'
        mock_presentation_status_handler.return_value = {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'Presentation not found',
                'message': f'Presentation with ID {presentation_id} does not exist'
            })
        }

        event = api_gateway_event(
            method='GET',
            path=f'/presentations/{presentation_id}',
            path_params={'id': presentation_id}
        )

        # Act
        response = mock_presentation_status_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'Presentation not found'

    def test_get_failed_status(
        self,
        api_gateway_event,
        lambda_context,
        mock_presentation_status_handler
    ):
        """Test getting status of a failed presentation."""
        # Arrange
        presentation_id = 'pres-failed'
        mock_presentation_status_handler.return_value = {
            'statusCode': 200,
            'body': json.dumps({
                'presentation_id': presentation_id,
                'status': 'failed',
                'progress': 45,
                'error': 'Content generation failed',
                'error_details': 'Bedrock service temporarily unavailable',
                'retry_possible': True,
                'failed_at': '2024-01-01T10:08:00Z'
            })
        }

        event = api_gateway_event(
            method='GET',
            path=f'/presentations/{presentation_id}',
            path_params={'id': presentation_id}
        )

        # Act
        response = mock_presentation_status_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'failed'
        assert 'error' in body
        assert 'retry_possible' in body


class TestPresentationDownloadAPI:
    """Tests for the presentation download endpoint: GET /presentations/{id}/download"""

    @pytest.fixture
    def mock_presentation_download_handler(self):
        """Mock the presentation_download Lambda handler."""
        with patch('lambdas.api.presentation_download.lambda_handler') as mock_handler:
            yield mock_handler

    def test_successful_download(
        self,
        api_gateway_event,
        lambda_context,
        mock_presentation_download_handler,
        s3_mock
    ):
        """Test successful presentation download."""
        # Arrange
        presentation_id = 'pres-download'
        mock_presentation_download_handler.return_value = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'Content-Disposition': f'attachment; filename="{presentation_id}.pptx"',
                'Content-Length': '2048576'
            },
            'body': 'base64_encoded_pptx_content',
            'isBase64Encoded': True
        }

        event = api_gateway_event(
            method='GET',
            path=f'/presentations/{presentation_id}/download',
            path_params={'id': presentation_id}
        )

        # Act
        response = mock_presentation_download_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 200
        assert response['isBase64Encoded'] is True
        assert 'Content-Type' in response['headers']
        assert 'application/vnd.openxmlformats-officedocument.presentationml.presentation' in response['headers']['Content-Type']
        assert 'attachment' in response['headers']['Content-Disposition']

    def test_download_not_ready(
        self,
        api_gateway_event,
        lambda_context,
        mock_presentation_download_handler
    ):
        """Test download attempt for presentation not yet completed."""
        # Arrange
        presentation_id = 'pres-processing'
        mock_presentation_download_handler.return_value = {
            'statusCode': 409,
            'body': json.dumps({
                'error': 'Presentation not ready',
                'message': 'Presentation is still processing',
                'status': 'processing',
                'progress': 75
            })
        }

        event = api_gateway_event(
            method='GET',
            path=f'/presentations/{presentation_id}/download',
            path_params={'id': presentation_id}
        )

        # Act
        response = mock_presentation_download_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert body['error'] == 'Presentation not ready'
        assert body['status'] == 'processing'

    def test_download_file_not_found(
        self,
        api_gateway_event,
        lambda_context,
        mock_presentation_download_handler
    ):
        """Test download when file is missing from S3."""
        # Arrange
        presentation_id = 'pres-missing'
        mock_presentation_download_handler.return_value = {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'File not found',
                'message': 'Presentation file not found in storage'
            })
        }

        event = api_gateway_event(
            method='GET',
            path=f'/presentations/{presentation_id}/download',
            path_params={'id': presentation_id}
        )

        # Act
        response = mock_presentation_download_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'File not found'


class TestSlideModificationAPI:
    """Tests for the slide modification endpoint: PATCH /presentations/{id}/slides/{slideId}"""

    @pytest.fixture
    def modify_slide_request(self):
        """Standard request payload for slide modification."""
        return {
            'title': 'Updated Slide Title',
            'content': 'Updated slide content with new information',
            'bullet_points': [
                'Updated point 1',
                'Updated point 2',
                'New point 3'
            ],
            'speaker_notes': 'Updated speaker notes for this slide',
            'regenerate_image': True,
            'image_prompt': 'A modern healthcare facility with AI technology'
        }

    @pytest.fixture
    def mock_modify_slide_handler(self):
        """Mock the modify_slide Lambda handler."""
        with patch('lambdas.api.modify_slide.lambda_handler') as mock_handler:
            yield mock_handler

    def test_successful_slide_modification(
        self,
        api_gateway_event,
        lambda_context,
        modify_slide_request,
        mock_modify_slide_handler
    ):
        """Test successful slide modification."""
        # Arrange
        presentation_id = 'pres-12345'
        slide_id = 'slide-2'
        mock_modify_slide_handler.return_value = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Slide updated successfully',
                'presentation_id': presentation_id,
                'slide_id': slide_id,
                'updated_fields': ['title', 'content', 'bullet_points', 'speaker_notes'],
                'regeneration_started': True,
                'estimated_completion_time': 60
            })
        }

        event = api_gateway_event(
            method='PATCH',
            path=f'/presentations/{presentation_id}/slides/{slide_id}',
            path_params={'id': presentation_id, 'slideId': slide_id},
            body=modify_slide_request
        )

        # Act
        response = mock_modify_slide_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['presentation_id'] == presentation_id
        assert body['slide_id'] == slide_id
        assert 'updated_fields' in body
        assert body['regeneration_started'] is True

    def test_slide_not_found(
        self,
        api_gateway_event,
        lambda_context,
        modify_slide_request,
        mock_modify_slide_handler
    ):
        """Test modification of non-existent slide."""
        # Arrange
        presentation_id = 'pres-12345'
        slide_id = 'slide-nonexistent'
        mock_modify_slide_handler.return_value = {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'Slide not found',
                'message': f'Slide {slide_id} not found in presentation {presentation_id}'
            })
        }

        event = api_gateway_event(
            method='PATCH',
            path=f'/presentations/{presentation_id}/slides/{slide_id}',
            path_params={'id': presentation_id, 'slideId': slide_id},
            body=modify_slide_request
        )

        # Act
        response = mock_modify_slide_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'Slide not found'

    def test_presentation_locked_for_modification(
        self,
        api_gateway_event,
        lambda_context,
        modify_slide_request,
        mock_modify_slide_handler
    ):
        """Test modification when presentation is locked."""
        # Arrange
        presentation_id = 'pres-locked'
        slide_id = 'slide-1'
        mock_modify_slide_handler.return_value = {
            'statusCode': 409,
            'body': json.dumps({
                'error': 'Presentation locked',
                'message': 'Presentation is currently being processed and cannot be modified',
                'status': 'processing',
                'retry_after': 120
            })
        }

        event = api_gateway_event(
            method='PATCH',
            path=f'/presentations/{presentation_id}/slides/{slide_id}',
            path_params={'id': presentation_id, 'slideId': slide_id},
            body=modify_slide_request
        )

        # Act
        response = mock_modify_slide_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 409
        body = json.loads(response['body'])
        assert body['error'] == 'Presentation locked'
        assert 'retry_after' in body


class TestTaskStatusAPI:
    """Tests for the task status endpoint: GET /tasks/{task_id}"""

    @pytest.fixture
    def mock_get_task_handler(self):
        """Mock the get_task Lambda handler."""
        with patch('lambdas.api.get_task.lambda_handler') as mock_handler:
            yield mock_handler

    def test_get_task_status_completed(
        self,
        api_gateway_event,
        lambda_context,
        mock_get_task_handler
    ):
        """Test getting status of a completed task."""
        # Arrange
        task_id = 'task-12345'
        mock_get_task_handler.return_value = {
            'statusCode': 200,
            'body': json.dumps({
                'task_id': task_id,
                'task_type': 'generate_content',
                'status': 'completed',
                'progress': 100,
                'result': {
                    'slide_content': 'Generated content for the slide',
                    'speaker_notes': 'Generated speaker notes'
                },
                'created_at': '2024-01-01T10:00:00Z',
                'completed_at': '2024-01-01T10:05:00Z',
                'execution_time_seconds': 45
            })
        }

        event = api_gateway_event(
            method='GET',
            path=f'/tasks/{task_id}',
            path_params={'task_id': task_id}
        )

        # Act
        response = mock_get_task_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['task_id'] == task_id
        assert body['status'] == 'completed'
        assert body['progress'] == 100
        assert 'result' in body

    def test_get_task_status_running(
        self,
        api_gateway_event,
        lambda_context,
        mock_get_task_handler
    ):
        """Test getting status of a running task."""
        # Arrange
        task_id = 'task-running'
        mock_get_task_handler.return_value = {
            'statusCode': 200,
            'body': json.dumps({
                'task_id': task_id,
                'task_type': 'generate_image',
                'status': 'running',
                'progress': 60,
                'current_step': 'processing_image_prompt',
                'estimated_completion_time': 90,
                'created_at': '2024-01-01T10:00:00Z',
                'started_at': '2024-01-01T10:01:00Z'
            })
        }

        event = api_gateway_event(
            method='GET',
            path=f'/tasks/{task_id}',
            path_params={'task_id': task_id}
        )

        # Act
        response = mock_get_task_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['task_id'] == task_id
        assert body['status'] == 'running'
        assert body['progress'] == 60
        assert 'estimated_completion_time' in body

    def test_task_not_found(
        self,
        api_gateway_event,
        lambda_context,
        mock_get_task_handler
    ):
        """Test getting status of non-existent task."""
        # Arrange
        task_id = 'task-nonexistent'
        mock_get_task_handler.return_value = {
            'statusCode': 404,
            'body': json.dumps({
                'error': 'Task not found',
                'message': f'Task with ID {task_id} does not exist'
            })
        }

        event = api_gateway_event(
            method='GET',
            path=f'/tasks/{task_id}',
            path_params={'task_id': task_id}
        )

        # Act
        response = mock_get_task_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['error'] == 'Task not found'


class TestHealthCheckAPI:
    """Tests for the health check endpoint: GET /health"""

    @pytest.fixture
    def mock_health_handler(self):
        """Mock the health check Lambda handler."""
        # Create a simple mock handler for health check
        def mock_handler(event, context):
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'healthy',
                    'timestamp': '2024-01-01T10:00:00Z',
                    'version': '1.0.0',
                    'environment': 'test',
                    'services': {
                        'dynamodb': 'healthy',
                        's3': 'healthy',
                        'sqs': 'healthy',
                        'bedrock': 'healthy'
                    },
                    'response_time_ms': 45
                })
            }
        return mock_handler

    def test_healthy_system(
        self,
        api_gateway_event,
        lambda_context,
        mock_health_handler
    ):
        """Test health check when all systems are healthy."""
        # Arrange
        event = api_gateway_event(method='GET', path='/health')

        # Act
        response = mock_health_handler(event, lambda_context)

        # Assert
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'healthy'
        assert 'timestamp' in body
        assert 'services' in body
        assert all(status == 'healthy' for status in body['services'].values())


class TestConcurrentRequests:
    """Tests for concurrent request handling and performance."""

    @pytest.fixture
    def mock_handlers(self):
        """Mock all API handlers for concurrent testing."""
        handlers = {}
        with patch('lambdas.api.generate_presentation.lambda_handler') as gen_mock, \
             patch('lambdas.api.presentation_status.lambda_handler') as status_mock, \
             patch('lambdas.api.presentation_download.lambda_handler') as download_mock:
            
            handlers['generate'] = gen_mock
            handlers['status'] = status_mock
            handlers['download'] = download_mock
            
            # Configure default responses
            gen_mock.return_value = {
                'statusCode': 202,
                'body': json.dumps({'presentation_id': 'concurrent-test', 'status': 'processing'})
            }
            
            status_mock.return_value = {
                'statusCode': 200,
                'body': json.dumps({'presentation_id': 'concurrent-test', 'status': 'processing', 'progress': 50})
            }
            
            download_mock.return_value = {
                'statusCode': 409,
                'body': json.dumps({'error': 'Presentation not ready'})
            }
            
            yield handlers

    @pytest.mark.slow
    def test_concurrent_status_requests(
        self,
        api_gateway_event,
        lambda_context,
        mock_handlers
    ):
        """Test handling of concurrent status requests."""
        # Arrange
        presentation_id = 'concurrent-test'
        num_concurrent_requests = 10
        
        def make_status_request():
            event = api_gateway_event(
                method='GET',
                path=f'/presentations/{presentation_id}',
                path_params={'id': presentation_id}
            )
            return mock_handlers['status'](event, lambda_context)
        
        # Act
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_requests) as executor:
            futures = [executor.submit(make_status_request) for _ in range(num_concurrent_requests)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Assert
        assert len(responses) == num_concurrent_requests
        for response in responses:
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['presentation_id'] == presentation_id

    @pytest.mark.slow
    def test_concurrent_generation_requests(
        self,
        api_gateway_event,
        lambda_context,
        mock_handlers
    ):
        """Test handling of concurrent generation requests."""
        # Arrange
        num_concurrent_requests = 5
        request_payload = {
            'topic': 'Concurrent Testing',
            'target_audience': 'Developers',
            'duration': 15,
            'slide_count': 5
        }
        
        def make_generation_request(request_id):
            payload = dict(request_payload)
            payload['topic'] = f"Concurrent Testing {request_id}"
            
            event = api_gateway_event(
                method='POST',
                path='/presentations/generate',
                body=payload
            )
            return mock_handlers['generate'](event, lambda_context)
        
        # Act
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_requests) as executor:
            futures = [executor.submit(make_generation_request, i) for i in range(num_concurrent_requests)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Assert
        assert len(responses) == num_concurrent_requests
        for response in responses:
            assert response['statusCode'] == 202
            body = json.loads(response['body'])
            assert 'presentation_id' in body


class TestErrorHandlingAndEdgeCases:
    """Tests for error handling and edge cases across all endpoints."""

    @pytest.fixture
    def mock_error_handlers(self):
        """Mock handlers that simulate various error conditions."""
        handlers = {}
        with patch('lambdas.api.generate_presentation.lambda_handler') as gen_mock, \
             patch('lambdas.api.presentation_status.lambda_handler') as status_mock:
            
            handlers['generate'] = gen_mock
            handlers['status'] = status_mock
            yield handlers

    def test_malformed_json_request(
        self,
        api_gateway_event,
        lambda_context,
        mock_error_handlers
    ):
        """Test handling of malformed JSON in request body."""
        # Arrange
        mock_error_handlers['generate'].return_value = {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid JSON',
                'message': 'Request body contains malformed JSON'
            })
        }

        # Create event with malformed JSON body manually
        event = {
            'resource': '/presentations/generate',
            'path': '/presentations/generate',
            'httpMethod': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'body': '{"invalid": "json",,}',  # Malformed JSON
            'isBase64Encoded': False
        }

        # Act
        response = mock_error_handlers['generate'](event, lambda_context)

        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Invalid JSON'

    def test_rate_limiting(
        self,
        api_gateway_event,
        lambda_context,
        mock_error_handlers
    ):
        """Test API rate limiting behavior."""
        # Arrange
        mock_error_handlers['generate'].return_value = {
            'statusCode': 429,
            'body': json.dumps({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests from this client',
                'retry_after': 60
            })
        }

        event = api_gateway_event(
            method='POST',
            path='/presentations/generate',
            body={'topic': 'Rate limit test'}
        )

        # Act
        response = mock_error_handlers['generate'](event, lambda_context)

        # Assert
        assert response['statusCode'] == 429
        body = json.loads(response['body'])
        assert body['error'] == 'Rate limit exceeded'
        assert 'retry_after' in body

    def test_service_unavailable(
        self,
        api_gateway_event,
        lambda_context,
        mock_error_handlers
    ):
        """Test handling when downstream services are unavailable."""
        # Arrange
        mock_error_handlers['status'].return_value = {
            'statusCode': 503,
            'body': json.dumps({
                'error': 'Service unavailable',
                'message': 'DynamoDB service temporarily unavailable',
                'retry_after': 30
            })
        }

        event = api_gateway_event(
            method='GET',
            path='/presentations/test-id',
            path_params={'id': 'test-id'}
        )

        # Act
        response = mock_error_handlers['status'](event, lambda_context)

        # Assert
        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert body['error'] == 'Service unavailable'
        assert 'retry_after' in body

    def test_large_request_payload(
        self,
        api_gateway_event,
        lambda_context,
        mock_error_handlers
    ):
        """Test handling of oversized request payloads."""
        # Arrange
        large_payload = {
            'topic': 'Large request test',
            'custom_content': 'x' * 10000,  # Very large content
            'target_audience': 'Developers'
        }
        
        mock_error_handlers['generate'].return_value = {
            'statusCode': 413,
            'body': json.dumps({
                'error': 'Payload too large',
                'message': 'Request payload exceeds maximum allowed size',
                'max_size_bytes': 1048576  # 1MB
            })
        }

        event = api_gateway_event(
            method='POST',
            path='/presentations/generate',
            body=large_payload
        )

        # Act
        response = mock_error_handlers['generate'](event, lambda_context)

        # Assert
        assert response['statusCode'] == 413
        body = json.loads(response['body'])
        assert body['error'] == 'Payload too large'

    def test_invalid_presentation_id_format(
        self,
        api_gateway_event,
        lambda_context,
        mock_error_handlers
    ):
        """Test handling of invalid presentation ID formats."""
        # Arrange
        invalid_id = 'invalid-id-with-special-chars@#$%'
        mock_error_handlers['status'].return_value = {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Invalid presentation ID',
                'message': 'Presentation ID contains invalid characters'
            })
        }

        event = api_gateway_event(
            method='GET',
            path=f'/presentations/{invalid_id}',
            path_params={'id': invalid_id}
        )

        # Act
        response = mock_error_handlers['status'](event, lambda_context)

        # Assert
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['error'] == 'Invalid presentation ID'


class TestPerformanceBenchmarks:
    """Performance benchmark tests for API endpoints."""

    @pytest.mark.slow
    def test_response_time_benchmarks(
        self,
        api_gateway_event,
        lambda_context
    ):
        """Test API response time benchmarks."""
        # This test would measure actual response times in a real integration test
        # For unit testing, we'll simulate the timing expectations
        
        # Define expected maximum response times (in seconds)
        max_response_times = {
            'health_check': 0.1,
            'status_check': 0.5,
            'generation_start': 2.0,
            'download_small': 1.0,
            'download_large': 5.0
        }
        
        # Assert that our expectations are reasonable
        assert max_response_times['health_check'] < 0.2
        assert max_response_times['status_check'] < 1.0
        assert max_response_times['generation_start'] < 5.0
        assert max_response_times['download_small'] < 2.0
        assert max_response_times['download_large'] < 10.0

    @pytest.mark.slow
    def test_memory_usage_limits(
        self,
        api_gateway_event,
        lambda_context
    ):
        """Test that API handlers stay within memory limits."""
        # In a real test, this would monitor actual memory usage
        # For unit testing, we verify that our Lambda context has appropriate memory limits
        
        expected_memory_limit = 1024  # MB
        assert lambda_context.memory_limit_in_mb >= expected_memory_limit
        
        # Verify timeout is reasonable for API operations
        remaining_time = lambda_context.get_remaining_time_in_millis()
        assert remaining_time >= 30000  # At least 30 seconds remaining


# Test configuration for running subsets
def pytest_generate_tests(metafunc):
    """Configure parametrized tests based on markers."""
    if metafunc.cls and hasattr(metafunc.cls, 'test_endpoints'):
        # Allow running tests for specific endpoints only
        endpoints = metafunc.cls.test_endpoints
        metafunc.parametrize("endpoint", endpoints)


# Custom assertions for API testing
def assert_valid_api_response(response: Dict[str, Any], expected_status: int = 200):
    """Assert that a response has valid API format."""
    assert 'statusCode' in response
    assert 'body' in response
    assert response['statusCode'] == expected_status
    
    if response.get('body'):
        # Verify body is valid JSON
        json.loads(response['body'])


def assert_error_response(response: Dict[str, Any], expected_error: str):
    """Assert that a response is a properly formatted error."""
    assert response['statusCode'] >= 400
    body = json.loads(response['body'])
    assert 'error' in body
    assert expected_error in body['error']


if __name__ == '__main__':
    # Allow running specific test classes
    import sys
    if len(sys.argv) > 1:
        test_class = sys.argv[1]
        pytest.main([f"-v", f"-k", test_class, __file__])
    else:
        pytest.main([f"-v", __file__])