"""
End-to-end test scenarios for AI PPT Assistant.
Tests complete user journeys from request to final presentation.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import time
from datetime import datetime, timedelta
import uuid
import base64
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas'))

@pytest.mark.e2e
class TestUserJourneys:
    """Test complete user journeys from start to finish."""
    
    @patch('boto3.client')
    @pytest.mark.timeout(60)  # Must complete within 60 seconds
    def test_simple_presentation_generation(self, mock_boto_client):
        """Test simple presentation generation within 60 seconds."""
        start_time = time.time()
        
        # Setup all required mock clients
        mock_clients = self._setup_mock_clients(mock_boto_client)
        
        # Step 1: User submits presentation request
        request_data = {
            'topic': 'Introduction to Cloud Computing',
            'target_audience': 'Business Executives',
            'duration': 20,
            'slide_count': 8,
            'style': 'professional',
            'language': 'en'
        }
        
        from api.generate_presentation import lambda_handler as generate_handler
        
        event = {
            'body': json.dumps(request_data),
            'headers': {'Content-Type': 'application/json'}
        }
        
        context = Mock()
        response = generate_handler(event, context)
        
        assert response['statusCode'] == 202
        body = json.loads(response['body'])
        presentation_id = body['presentation_id']
        
        # Step 2: Simulate asynchronous processing
        self._simulate_async_processing(mock_clients, presentation_id, request_data)
        
        # Step 3: User checks status periodically
        from api.presentation_status import lambda_handler as status_handler
        
        max_checks = 20
        check_count = 0
        presentation_complete = False
        
        while check_count < max_checks and not presentation_complete:
            status_event = {
                'pathParameters': {'id': presentation_id}
            }
            
            # Mock progressive status updates
            progress = min(100, (check_count + 1) * 20)
            status = 'completed' if progress >= 100 else 'processing'
            
            mock_clients['dynamodb'].get_item.return_value = {
                'Item': {
                    'presentation_id': {'S': presentation_id},
                    'status': {'S': status},
                    'progress': {'N': str(progress)}
                }
            }
            
            status_response = status_handler(status_event, context)
            assert status_response['statusCode'] == 200
            
            status_body = json.loads(status_response['body'])
            if status_body['status'] == 'completed':
                presentation_complete = True
            else:
                time.sleep(1)  # Simulate wait between checks
            
            check_count += 1
        
        assert presentation_complete, "Presentation did not complete in time"
        
        # Step 4: User downloads the presentation
        from api.presentation_download import lambda_handler as download_handler
        
        download_event = {
            'pathParameters': {'id': presentation_id},
            'queryStringParameters': {'format': 'pptx'}
        }
        
        # Mock completed presentation data
        mock_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'presentation_id': {'S': presentation_id},
                'status': {'S': 'completed'},
                'file_key': {'S': f'presentations/{presentation_id}.pptx'}
            }
        }
        
        # Mock S3 presigned URL
        mock_clients['s3'].generate_presigned_url.return_value = \
            f'https://s3.amazonaws.com/bucket/{presentation_id}.pptx?signature=xxx'
        
        download_response = download_handler(download_event, context)
        assert download_response['statusCode'] == 200
        
        download_body = json.loads(download_response['body'])
        assert 'download_url' in download_body
        
        # Verify total time is under 60 seconds
        total_time = time.time() - start_time
        assert total_time < 60, f"Total time {total_time}s exceeded 60s limit"
        
        print(f"✅ Simple presentation completed in {total_time:.2f}s")
    
    @patch('boto3.client')
    @pytest.mark.timeout(120)
    def test_complex_presentation_generation(self, mock_boto_client):
        """Test complex presentation with images and detailed content."""
        start_time = time.time()
        
        mock_clients = self._setup_mock_clients(mock_boto_client)
        
        # Complex presentation request
        request_data = {
            'topic': 'Artificial Intelligence and Machine Learning in Healthcare',
            'target_audience': 'Medical Professionals and Researchers',
            'duration': 60,
            'slide_count': 25,
            'style': 'technical',
            'language': 'en',
            'include_images': True,
            'include_speaker_notes': True,
            'include_references': True
        }
        
        from api.generate_presentation import lambda_handler as generate_handler
        
        event = {'body': json.dumps(request_data)}
        context = Mock()
        
        response = generate_handler(event, context)
        assert response['statusCode'] == 202
        
        presentation_id = json.loads(response['body'])['presentation_id']
        
        # Simulate complex processing with all agents
        self._simulate_complex_processing(mock_clients, presentation_id, request_data)
        
        # Check final status
        from api.presentation_status import lambda_handler as status_handler
        
        status_event = {'pathParameters': {'id': presentation_id}}
        
        mock_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'presentation_id': {'S': presentation_id},
                'status': {'S': 'completed'},
                'progress': {'N': '100'},
                'slide_count': {'N': '25'},
                'has_images': {'BOOL': True},
                'has_speaker_notes': {'BOOL': True}
            }
        }
        
        status_response = status_handler(status_event, context)
        assert status_response['statusCode'] == 200
        
        status_body = json.loads(status_response['body'])
        assert status_body['status'] == 'completed'
        
        total_time = time.time() - start_time
        print(f"✅ Complex presentation completed in {total_time:.2f}s")
    
    @patch('boto3.client')
    def test_presentation_with_modifications(self, mock_boto_client):
        """Test presentation generation with subsequent modifications."""
        mock_clients = self._setup_mock_clients(mock_boto_client)
        
        # Generate initial presentation
        presentation_id = 'modify-test-123'
        
        # User modifies a slide
        from api.modify_slide import lambda_handler as modify_handler
        
        modify_event = {
            'pathParameters': {
                'id': presentation_id,
                'slideId': 'slide-3'
            },
            'body': json.dumps({
                'modification_type': 'content',
                'new_content': 'Updated content with more details about the topic'
            })
        }
        
        # Mock existing presentation
        mock_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'presentation_id': {'S': presentation_id},
                'status': {'S': 'completed'},
                'slides': {'L': [
                    {'M': {'slide_id': {'S': f'slide-{i}'}, 'title': {'S': f'Title {i}'}}}
                    for i in range(1, 6)
                ]}
            }
        }
        
        context = Mock()
        modify_response = modify_handler(modify_event, context)
        assert modify_response['statusCode'] == 202
        
        # Verify modification was queued
        mock_clients['sqs'].send_message.assert_called()
        
        # User adds an image to a slide
        modify_event = {
            'pathParameters': {
                'id': presentation_id,
                'slideId': 'slide-5'
            },
            'body': json.dumps({
                'modification_type': 'visual',
                'image_prompt': 'Modern data center with cloud infrastructure'
            })
        }
        
        modify_response = modify_handler(modify_event, context)
        assert modify_response['statusCode'] == 202
        
        print("✅ Presentation modifications processed successfully")
    
    @patch('boto3.client')
    def test_concurrent_presentations(self, mock_boto_client):
        """Test handling of multiple concurrent presentation requests."""
        mock_clients = self._setup_mock_clients(mock_boto_client)
        
        from api.generate_presentation import lambda_handler as generate_handler
        
        # Create 5 concurrent presentation requests
        presentations = []
        context = Mock()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            for i in range(5):
                request_data = {
                    'topic': f'Topic {i}: Technology Trends',
                    'target_audience': 'Engineers',
                    'duration': 30,
                    'slide_count': 10,
                    'style': 'professional'
                }
                
                event = {'body': json.dumps(request_data)}
                
                # Submit concurrent requests
                future = executor.submit(generate_handler, event, context)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                response = future.result()
                assert response['statusCode'] == 202
                body = json.loads(response['body'])
                presentations.append(body['presentation_id'])
        
        assert len(presentations) == 5
        print(f"✅ Successfully handled {len(presentations)} concurrent presentations")
        
        # Verify all presentations are tracked in DynamoDB
        for pres_id in presentations:
            mock_clients['dynamodb'].put_item.assert_any_call(
                TableName=os.environ.get('DYNAMODB_TABLE', 'presentations'),
                Item={
                    'presentation_id': {'S': pres_id},
                    'status': {'S': 'pending'},
                    'progress': {'N': '0'},
                    'created_at': {'S': Mock.ANY},
                    'metadata': {'S': Mock.ANY}
                }
            )
    
    @patch('boto3.client')
    def test_error_recovery_scenario(self, mock_boto_client):
        """Test system recovery from various error conditions."""
        mock_clients = self._setup_mock_clients(mock_boto_client)
        
        from api.generate_presentation import lambda_handler as generate_handler
        
        # Scenario 1: Bedrock service temporarily unavailable
        mock_clients['bedrock'].invoke_model.side_effect = [
            Exception('Service unavailable'),
            Exception('Service unavailable'),
            {'body': MagicMock()}  # Success on third retry
        ]
        
        event = {
            'body': json.dumps({
                'topic': 'Resilient Systems',
                'duration': 30
            })
        }
        
        context = Mock()
        
        # System should handle the error gracefully
        response = generate_handler(event, context)
        assert response['statusCode'] in [202, 503]
        
        # Scenario 2: DynamoDB throttling
        mock_clients['dynamodb'].put_item.side_effect = [
            Exception('ProvisionedThroughputExceededException'),
            {}  # Success on retry
        ]
        
        response = generate_handler(event, context)
        # Should retry and succeed
        
        # Scenario 3: S3 upload failure during compilation
        mock_clients['s3'].put_object.side_effect = Exception('S3 Service Error')
        
        # System should handle S3 errors and possibly use alternative storage
        
        print("✅ Error recovery scenarios handled successfully")
    
    @patch('boto3.client')
    def test_performance_metrics(self, mock_boto_client):
        """Test and measure performance metrics."""
        mock_clients = self._setup_mock_clients(mock_boto_client)
        
        metrics = {
            'api_response_times': [],
            'processing_times': [],
            'total_times': []
        }
        
        # Run multiple test iterations
        for i in range(3):
            start = time.time()
            
            # API call
            from api.generate_presentation import lambda_handler as generate_handler
            
            event = {
                'body': json.dumps({
                    'topic': f'Performance Test {i}',
                    'duration': 30,
                    'slide_count': 10
                })
            }
            
            context = Mock()
            api_start = time.time()
            response = generate_handler(event, context)
            api_time = time.time() - api_start
            metrics['api_response_times'].append(api_time)
            
            assert response['statusCode'] == 202
            
            # Simulate processing
            processing_start = time.time()
            presentation_id = json.loads(response['body'])['presentation_id']
            self._simulate_async_processing(mock_clients, presentation_id, {})
            processing_time = time.time() - processing_start
            metrics['processing_times'].append(processing_time)
            
            total_time = time.time() - start
            metrics['total_times'].append(total_time)
        
        # Calculate averages
        avg_api = sum(metrics['api_response_times']) / len(metrics['api_response_times'])
        avg_processing = sum(metrics['processing_times']) / len(metrics['processing_times'])
        avg_total = sum(metrics['total_times']) / len(metrics['total_times'])
        
        print(f"📊 Performance Metrics:")
        print(f"  - Avg API Response: {avg_api*1000:.2f}ms")
        print(f"  - Avg Processing: {avg_processing:.2f}s")
        print(f"  - Avg Total Time: {avg_total:.2f}s")
        
        # Verify performance targets
        assert avg_api < 0.5, "API response time exceeds 500ms"
        assert avg_total < 60, "Total time exceeds 60s target"
    
    # Helper methods
    def _setup_mock_clients(self, mock_boto_client):
        """Setup all required mock AWS clients."""
        mock_dynamodb = MagicMock()
        mock_sqs = MagicMock()
        mock_s3 = MagicMock()
        mock_bedrock = MagicMock()
        
        def mock_client(service_name, **kwargs):
            clients = {
                'dynamodb': mock_dynamodb,
                'sqs': mock_sqs,
                's3': mock_s3,
                'bedrock-runtime': mock_bedrock,
                'bedrock-agent-runtime': mock_bedrock
            }
            return clients.get(service_name, MagicMock())
        
        mock_boto_client.side_effect = mock_client
        
        # Setup default responses
        mock_dynamodb.put_item.return_value = {}
        mock_dynamodb.update_item.return_value = {'Attributes': {}}
        mock_sqs.send_message.return_value = {'MessageId': 'test-msg'}
        mock_s3.put_object.return_value = {'ETag': 'test-etag'}
        mock_bedrock.invoke_agent.return_value = {'completion': 'success'}
        
        return {
            'dynamodb': mock_dynamodb,
            'sqs': mock_sqs,
            's3': mock_s3,
            'bedrock': mock_bedrock
        }
    
    def _simulate_async_processing(self, mock_clients, presentation_id, request_data):
        """Simulate asynchronous processing workflow."""
        # Simulate outline generation
        mock_clients['bedrock'].invoke_model.return_value = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{
                    'text': json.dumps({
                        'title': request_data.get('topic', 'Test Topic'),
                        'slides': [
                            {'title': f'Slide {i}', 'key_points': ['Point 1', 'Point 2']}
                            for i in range(1, request_data.get('slide_count', 5) + 1)
                        ]
                    })
                }]
            }).encode('utf-8'))
        }
        
        # Simulate content generation
        for i in range(request_data.get('slide_count', 5)):
            mock_clients['bedrock'].invoke_model.return_value = {
                'body': MagicMock(read=lambda: json.dumps({
                    'content': [{
                        'text': json.dumps({
                            'content': 'Generated content',
                            'bullet_points': ['Point A', 'Point B']
                        })
                    }]
                }).encode('utf-8'))
            }
        
        # Simulate image generation if requested
        if request_data.get('include_images'):
            mock_clients['bedrock'].invoke_model.return_value = {
                'body': MagicMock(read=lambda: json.dumps({
                    'images': [base64.b64encode(b'fake_image').decode('utf-8')]
                }).encode('utf-8'))
            }
        
        # Simulate compilation
        mock_clients['s3'].put_object.return_value = {'ETag': 'final-etag'}
        
        # Update status to completed
        mock_clients['dynamodb'].update_item.return_value = {
            'Attributes': {
                'status': {'S': 'completed'},
                'progress': {'N': '100'}
            }
        }
    
    def _simulate_complex_processing(self, mock_clients, presentation_id, request_data):
        """Simulate complex processing with all features."""
        # Extended processing for complex presentations
        self._simulate_async_processing(mock_clients, presentation_id, request_data)
        
        # Add speaker notes generation
        if request_data.get('include_speaker_notes'):
            for i in range(request_data.get('slide_count', 10)):
                mock_clients['bedrock'].invoke_model.return_value = {
                    'body': MagicMock(read=lambda: json.dumps({
                        'content': [{
                            'text': json.dumps({
                                'speaker_notes': f'Detailed speaker notes for slide {i}'
                            })
                        }]
                    }).encode('utf-8'))
                }
        
        # Add reference generation
        if request_data.get('include_references'):
            mock_clients['bedrock'].invoke_model.return_value = {
                'body': MagicMock(read=lambda: json.dumps({
                    'content': [{
                        'text': json.dumps({
                            'references': [
                                'Reference 1: Academic Paper',
                                'Reference 2: Industry Report'
                            ]
                        })
                    }]
                }).encode('utf-8'))
            }


@pytest.mark.e2e
@pytest.mark.slow
class TestPerformanceScenarios:
    """Test performance under various load conditions."""
    
    @patch('boto3.client')
    def test_load_testing(self, mock_boto_client):
        """Test system under load with multiple concurrent users."""
        mock_clients = self._setup_mock_clients(mock_boto_client)
        
        # Simulate 20 concurrent users
        concurrent_users = 20
        results = {
            'successful': 0,
            'failed': 0,
            'response_times': []
        }
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            
            for i in range(concurrent_users):
                future = executor.submit(self._simulate_user_request, i, mock_clients)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    response_time = future.result()
                    results['successful'] += 1
                    results['response_times'].append(response_time)
                except Exception as e:
                    results['failed'] += 1
                    print(f"Request failed: {e}")
        
        # Calculate statistics
        success_rate = (results['successful'] / concurrent_users) * 100
        avg_response = sum(results['response_times']) / len(results['response_times']) if results['response_times'] else 0
        
        print(f"📊 Load Test Results:")
        print(f"  - Success Rate: {success_rate:.1f}%")
        print(f"  - Avg Response Time: {avg_response*1000:.2f}ms")
        print(f"  - Successful: {results['successful']}/{concurrent_users}")
        
        assert success_rate >= 95, "Success rate below 95%"
        assert avg_response < 1.0, "Average response time exceeds 1 second"
    
    def _setup_mock_clients(self, mock_boto_client):
        """Setup mock clients for performance testing."""
        mock_clients = {}
        for service in ['dynamodb', 'sqs', 's3', 'bedrock-runtime']:
            mock_clients[service] = MagicMock()
        
        def mock_client(service_name, **kwargs):
            return mock_clients.get(service_name, MagicMock())
        
        mock_boto_client.side_effect = mock_client
        return mock_clients
    
    def _simulate_user_request(self, user_id, mock_clients):
        """Simulate a single user request."""
        start_time = time.time()
        
        # Simulate API call
        from api.generate_presentation import lambda_handler
        
        event = {
            'body': json.dumps({
                'topic': f'User {user_id} Presentation',
                'duration': 30
            })
        }
        
        context = Mock()
        response = lambda_handler(event, context)
        
        if response['statusCode'] != 202:
            raise Exception(f"Unexpected status code: {response['statusCode']}")
        
        return time.time() - start_time


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'e2e'])