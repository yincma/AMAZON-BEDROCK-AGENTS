"""
Pytest configuration and fixtures for test suite.
"""

import pytest
import os
import sys
import json
from unittest.mock import Mock, MagicMock
import boto3
from moto import mock_aws

# Add Lambda directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambdas/controllers'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambdas/models'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambdas/views'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambdas/api'))

# Global test configuration
TEST_REGION = 'us-east-1'
TEST_BUCKET = 'test-presentations-bucket'
TEST_TABLE = 'test-presentations-table'
TEST_QUEUE = 'test-presentations-queue'

@pytest.fixture(scope='function')
def aws_credentials():
    """Mock AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = TEST_REGION

@pytest.fixture(scope='function')
def s3_mock(aws_credentials):
    """Mock S3 service."""
    with mock_aws():
        s3 = boto3.client('s3', region_name=TEST_REGION)
        s3.create_bucket(Bucket=TEST_BUCKET)
        yield s3

@pytest.fixture(scope='function')
def dynamodb_mock(aws_credentials):
    """Mock DynamoDB service."""
    with mock_aws():
        dynamodb = boto3.client('dynamodb', region_name=TEST_REGION)
        
        # Create test table
        dynamodb.create_table(
            TableName=TEST_TABLE,
            KeySchema=[
                {'AttributeName': 'presentation_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'presentation_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield dynamodb

@pytest.fixture(scope='function')
def sqs_mock(aws_credentials):
    """Mock SQS service."""
    with mock_aws():
        sqs = boto3.client('sqs', region_name=TEST_REGION)
        
        # Create test queue
        response = sqs.create_queue(QueueName=TEST_QUEUE)
        queue_url = response['QueueUrl']
        
        yield sqs, queue_url

@pytest.fixture(scope='function')
def lambda_context():
    """Standard Lambda context for testing."""
    context = Mock()
    context.function_name = 'test-function'
    context.function_version = '$LATEST'
    context.invoked_function_arn = f'arn:aws:lambda:{TEST_REGION}:123456789012:function:test-function'
    context.memory_limit_in_mb = 1024
    context.aws_request_id = 'test-request-id-12345'
    context.log_group_name = '/aws/lambda/test-function'
    context.log_stream_name = '2024/01/01/[$LATEST]test-stream'
    context.identity = None
    context.client_context = None
    # Fix: Make this a proper mock method that returns an integer
    context.get_remaining_time_in_millis = Mock(return_value=300000)  # 5 minutes
    
    return context

@pytest.fixture
def mock_bedrock_client():
    """Enhanced Bedrock client mock for comprehensive testing."""
    mock_client = MagicMock()
    
    # Mock response for text generation
    text_response = {
        'body': MagicMock()
    }
    text_response['body'].read.return_value = json.dumps({
        'content': [
            {
                'text': json.dumps({
                    'result': 'success',
                    'data': {
                        'title': 'Test Generated Title',
                        'content': 'Test generated content for slides',
                        'slides': [
                            {'title': 'Slide 1', 'content': 'Content 1'},
                            {'title': 'Slide 2', 'content': 'Content 2'}
                        ]
                    }
                })
            }
        ]
    }).encode('utf-8')
    
    # Mock response for image generation
    image_response = {
        'body': MagicMock()
    }
    image_response['body'].read.return_value = json.dumps({
        'artifacts': [
            {
                'base64': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==',
                'finishReason': 'SUCCESS'
            }
        ]
    }).encode('utf-8')
    
    def mock_invoke_model(ModelId=None, **kwargs):
        # Return different responses based on model type
        if 'nova-canvas' in str(ModelId) or 'image' in str(ModelId).lower():
            return image_response
        else:
            return text_response
    
    mock_client.invoke_model.side_effect = mock_invoke_model
    mock_client.invoke_agent.return_value = {
        'completion': 'Agent task completed successfully'
    }
    
    return mock_client

@pytest.fixture
def sample_presentation():
    """Sample presentation data for testing."""
    return {
        'presentation_id': 'test-pres-123',
        'title': 'Test Presentation',
        'topic': 'Testing and Quality Assurance',
        'target_audience': 'Developers',
        'duration': 30,
        'slide_count': 10,
        'style': 'professional',
        'language': 'en',
        'slides': [
            {
                'slide_id': 'slide-1',
                'title': 'Introduction',
                'content': 'Welcome to the presentation',
                'bullet_points': ['Overview', 'Objectives', 'Agenda'],
                'speaker_notes': 'Start with a warm welcome',
                'image_url': None
            },
            {
                'slide_id': 'slide-2',
                'title': 'Main Content',
                'content': 'Core information and insights',
                'bullet_points': ['Key Point 1', 'Key Point 2', 'Key Point 3'],
                'speaker_notes': 'Explain the main concepts',
                'image_url': 's3://test-bucket/images/slide2.png'
            }
        ],
        'status': 'completed',
        'progress': 100,
        'created_at': '2024-01-01T00:00:00Z',
        'updated_at': '2024-01-01T00:30:00Z',
        'file_key': 'presentations/test-pres-123.pptx'
    }

@pytest.fixture
def api_gateway_event():
    """Standard API Gateway event structure."""
    def _event(method='GET', path='/', body=None, path_params=None, query_params=None):
        event = {
            'resource': path,
            'path': path,
            'httpMethod': method,
            'headers': {
                'Content-Type': 'application/json',
                'User-Agent': 'pytest'
            },
            'multiValueHeaders': {},
            'queryStringParameters': query_params,
            'multiValueQueryStringParameters': None,
            'pathParameters': path_params,
            'stageVariables': None,
            'requestContext': {
                'accountId': '123456789012',
                'apiId': 'test-api-id',
                'protocol': 'HTTP/1.1',
                'httpMethod': method,
                'path': path,
                'stage': 'test',
                'requestId': 'test-request-id',
                'requestTime': '01/Jan/2024:00:00:00 +0000',
                'requestTimeEpoch': 1704067200000,
                'identity': {
                    'sourceIp': '127.0.0.1',
                    'userAgent': 'pytest'
                }
            },
            'body': json.dumps(body) if body else None,
            'isBase64Encoded': False
        }
        return event
    
    return _event

# Environment variable fixtures
@pytest.fixture(autouse=True)
def setup_environment():
    """Set up environment variables for tests."""
    env_vars = {
        # AWS Configuration
        'AWS_REGION': TEST_REGION,
        'AWS_DEFAULT_REGION': TEST_REGION,
        
        # DynamoDB Tables
        'PRESENTATIONS_TABLE': 'test-presentations',
        'CHECKPOINTS_TABLE': 'test-checkpoints', 
        'USERS_TABLE': 'test-users',
        'ANALYTICS_TABLE': 'test-analytics',
        'DYNAMODB_TABLE': TEST_TABLE,  # Legacy compatibility
        
        # S3 Buckets
        'PRESENTATION_BUCKET': 'test-presentation-bucket',
        'IMAGES_BUCKET': 'test-images-bucket',
        'ASSETS_BUCKET': 'test-assets-bucket',
        'S3_BUCKET': TEST_BUCKET,  # Legacy compatibility
        
        # SQS Queues
        'PRESENTATION_QUEUE_URL': f'https://sqs.{TEST_REGION}.amazonaws.com/123456789012/test-presentation-queue',
        'DLQ_URL': f'https://sqs.{TEST_REGION}.amazonaws.com/123456789012/test-dlq',
        'SQS_QUEUE_URL': f'https://sqs.{TEST_REGION}.amazonaws.com/123456789012/{TEST_QUEUE}',  # Legacy
        
        # Bedrock Models
        'BEDROCK_MODEL_ID': 'amazon.titan-text-premier-v1:0',
        'BEDROCK_IMAGE_MODEL_ID': 'amazon.nova-canvas-v1:0',
        'NOVA_MODEL_ID': 'amazon.nova-canvas-v1:0',  # Legacy compatibility
        
        # API Configuration
        'API_GATEWAY_URL': 'https://test-api-gateway.execute-api.us-east-1.amazonaws.com/dev',
        
        # Application Configuration
        'ENVIRONMENT': 'test',
        'DEBUG': 'true',
        'LOG_LEVEL': 'DEBUG',
        
        # Lambda Configuration
        'LAMBDA_TIMEOUT': '300',
        'MAX_RETRIES': '3',
        
        # Performance Configuration
        'MAX_SLIDES': '20',
        'MAX_FILE_SIZE': '52428800',  # 50MB
        'CACHE_TTL': '3600',
        
        # Feature Flags
        'ENABLE_IMAGE_GENERATION': 'true',
        'ENABLE_ANALYTICS': 'true',
        'ENABLE_CACHING': 'true',
        
        # Security Configuration
        'JWT_SECRET': 'test-jwt-secret-key-for-testing-only',
        'ENCRYPTION_KEY': 'test-encryption-key-32-bytes-long',
        
        # PowerTools Configuration
        '_POWERTOOLS_DEV': 'true',
        'POWERTOOLS_SERVICE_NAME': 'ai-ppt-assistant-test',
        'POWERTOOLS_LOG_LEVEL': 'DEBUG',
        'POWERTOOLS_LOGGER_SAMPLE_RATE': '0.1',
        'POWERTOOLS_LOGGER_LOG_EVENT': 'true',
        'POWERTOOLS_METRICS_NAMESPACE': 'test',
        'POWERTOOLS_TRACER_CAPTURE_RESPONSE': 'false',
        'POWERTOOLS_TRACER_CAPTURE_ERROR': 'false',
    }
    
    # Store original values
    original = {}
    for key, value in env_vars.items():
        original[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original values
    for key, value in original.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

# PowerTools Mocking
@pytest.fixture(autouse=True)
def mock_powertools():
    """Mock PowerTools components to prevent initialization issues."""
    from unittest.mock import patch, Mock
    
    with patch('aws_lambda_powertools.Logger') as mock_logger, \
         patch('aws_lambda_powertools.Tracer') as mock_tracer, \
         patch('aws_lambda_powertools.Metrics') as mock_metrics:
        
        # Configure logger mock
        logger_instance = Mock()
        logger_instance.info = Mock()
        logger_instance.error = Mock()
        logger_instance.warning = Mock()
        logger_instance.debug = Mock()
        mock_logger.return_value = logger_instance
        
        # Configure tracer mock  
        tracer_instance = Mock()
        tracer_instance.capture_lambda_handler = lambda func: func
        tracer_instance.capture_method = lambda func: func
        mock_tracer.return_value = tracer_instance
        
        # Configure metrics mock
        metrics_instance = Mock()
        metrics_instance.add_metric = Mock()
        mock_metrics.return_value = metrics_instance
        
        yield {
            'logger': logger_instance,
            'tracer': tracer_instance,
            'metrics': metrics_instance
        }

# Additional AWS Service Mocks
@pytest.fixture
def enhanced_dynamodb_mock(aws_credentials):
    """Enhanced DynamoDB mock with multiple tables."""
    with mock_aws():
        dynamodb = boto3.client('dynamodb', region_name=TEST_REGION)
        
        # Create all test tables
        tables = [
            ('test-presentations', 'presentation_id'),
            ('test-checkpoints', 'checkpoint_id'),
            ('test-users', 'user_id'),
            ('test-analytics', 'event_id')
        ]
        
        for table_name, key_name in tables:
            dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': key_name, 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': key_name, 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
        
        yield dynamodb

# Markers for test categories
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "smoke: mark test as a smoke test"
    )
    config.addinivalue_line(
        "markers", "timeout: mark test with timeout"
    )