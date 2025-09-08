"""
Integration Test Configuration

This module provides configuration settings and utilities specifically
for integration tests, including API endpoint configuration, test data
generation, and environment setup.
"""

import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from unittest.mock import Mock
import boto3
from moto import mock_aws


@dataclass
class TestAPIConfig:
    """Configuration for API integration tests."""
    base_url: str = "https://test-api-gateway.execute-api.us-east-1.amazonaws.com/dev"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # API Endpoints
    generate_endpoint: str = "/presentations/generate"
    status_endpoint: str = "/presentations/{id}"
    download_endpoint: str = "/presentations/{id}/download"
    modify_slide_endpoint: str = "/presentations/{id}/slides/{slideId}"
    task_endpoint: str = "/tasks/{task_id}"
    health_endpoint: str = "/health"
    
    # Request limits
    max_payload_size: int = 1048576  # 1MB
    max_slide_count: int = 50
    max_duration: int = 180  # minutes
    
    # Response expectations
    max_response_time_ms: int = 30000  # 30 seconds
    max_generation_time_ms: int = 600000  # 10 minutes
    
    def get_endpoint_url(self, endpoint: str, **kwargs) -> str:
        """Format endpoint URL with parameters."""
        formatted_endpoint = endpoint.format(**kwargs)
        return f"{self.base_url}{formatted_endpoint}"


@dataclass
class TestAWSConfig:
    """Configuration for AWS services in tests."""
    region: str = "us-east-1"
    
    # DynamoDB Tables
    presentations_table: str = "test-presentations"
    checkpoints_table: str = "test-checkpoints"
    users_table: str = "test-users"
    analytics_table: str = "test-analytics"
    
    # S3 Buckets
    presentations_bucket: str = "test-presentations-bucket"
    images_bucket: str = "test-images-bucket"
    assets_bucket: str = "test-assets-bucket"
    
    # SQS Queues
    presentation_queue: str = "test-presentation-queue"
    dlq_queue: str = "test-dlq"
    
    # Bedrock Models
    text_model: str = "amazon.titan-text-premier-v1:0"
    image_model: str = "amazon.nova-canvas-v1:0"
    
    # Lambda Functions
    lambda_timeout: int = 300
    lambda_memory: int = 1024


@dataclass
class TestDataConfig:
    """Configuration for test data generation."""
    
    # Presentation Templates
    sample_presentations: Dict[str, Dict[str, Any]] = None
    
    # Request Templates
    sample_requests: Dict[str, Dict[str, Any]] = None
    
    # Error Scenarios
    error_scenarios: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize default test data."""
        if self.sample_presentations is None:
            self.sample_presentations = self._get_default_presentations()
        
        if self.sample_requests is None:
            self.sample_requests = self._get_default_requests()
        
        if self.error_scenarios is None:
            self.error_scenarios = self._get_default_error_scenarios()
    
    def _get_default_presentations(self) -> Dict[str, Dict[str, Any]]:
        """Get default presentation test data."""
        return {
            "simple": {
                "presentation_id": "test-simple",
                "title": "Simple Test Presentation",
                "topic": "Testing Basics",
                "target_audience": "Developers",
                "duration": 15,
                "slide_count": 5,
                "style": "professional",
                "language": "en",
                "status": "completed",
                "progress": 100
            },
            "complex": {
                "presentation_id": "test-complex",
                "title": "Complex Test Presentation",
                "topic": "Advanced AI and Machine Learning in Healthcare",
                "target_audience": "Healthcare professionals and data scientists",
                "duration": 60,
                "slide_count": 25,
                "style": "academic",
                "language": "en",
                "include_images": True,
                "status": "processing",
                "progress": 45
            },
            "failed": {
                "presentation_id": "test-failed",
                "title": "Failed Test Presentation",
                "topic": "Test Failure Scenarios",
                "target_audience": "QA Engineers",
                "duration": 30,
                "slide_count": 10,
                "status": "failed",
                "progress": 25,
                "error": "Content generation failed"
            }
        }
    
    def _get_default_requests(self) -> Dict[str, Dict[str, Any]]:
        """Get default request templates."""
        return {
            "minimal": {
                "topic": "Test Topic",
                "target_audience": "Developers",
                "duration": 15,
                "slide_count": 5
            },
            "standard": {
                "topic": "AI and Machine Learning",
                "target_audience": "Business stakeholders",
                "duration": 30,
                "slide_count": 10,
                "style": "professional",
                "language": "en",
                "include_images": True
            },
            "detailed": {
                "topic": "Enterprise Data Architecture",
                "target_audience": "Technical architects and senior developers",
                "duration": 60,
                "slide_count": 20,
                "style": "technical",
                "language": "en",
                "include_images": True,
                "custom_template": "enterprise",
                "branding": {
                    "company": "Test Corp",
                    "logo_url": "https://example.com/logo.png",
                    "colors": ["#1f77b4", "#ff7f0e", "#2ca02c"]
                }
            },
            "slide_modification": {
                "title": "Updated Slide Title",
                "content": "Updated slide content with comprehensive information",
                "bullet_points": [
                    "First updated point with details",
                    "Second updated point with examples",
                    "Third new point with insights"
                ],
                "speaker_notes": "Detailed speaker notes for the updated slide",
                "regenerate_image": True,
                "image_prompt": "Professional business meeting with diverse team"
            }
        }
    
    def _get_default_error_scenarios(self) -> List[Dict[str, Any]]:
        """Get default error test scenarios."""
        return [
            {
                "name": "missing_topic",
                "request": {"target_audience": "Developers", "duration": 15},
                "expected_status": 400,
                "expected_error": "Required field missing: topic"
            },
            {
                "name": "invalid_duration",
                "request": {"topic": "Test", "target_audience": "Developers", "duration": -5},
                "expected_status": 400,
                "expected_error": "Invalid duration"
            },
            {
                "name": "too_many_slides",
                "request": {
                    "topic": "Test", 
                    "target_audience": "Developers", 
                    "duration": 30, 
                    "slide_count": 100
                },
                "expected_status": 400,
                "expected_error": "Slide count exceeds maximum"
            },
            {
                "name": "invalid_language",
                "request": {
                    "topic": "Test", 
                    "target_audience": "Developers", 
                    "duration": 15, 
                    "language": "invalid-lang"
                },
                "expected_status": 400,
                "expected_error": "Unsupported language"
            },
            {
                "name": "oversized_payload",
                "request": {
                    "topic": "Test", 
                    "target_audience": "Developers", 
                    "duration": 15,
                    "custom_content": "x" * 2000000  # 2MB of content
                },
                "expected_status": 413,
                "expected_error": "Payload too large"
            }
        ]


class TestEnvironmentManager:
    """Manages test environment setup and teardown."""
    
    def __init__(self, config: Optional[TestAWSConfig] = None):
        """Initialize with AWS configuration."""
        self.config = config or TestAWSConfig()
        self.moto_mocks = {}
        self.created_resources = {
            'tables': [],
            'buckets': [],
            'queues': []
        }
    
    def setup_aws_environment(self) -> Dict[str, Any]:
        """Set up AWS environment for testing."""
        # Start moto mocks
        self.moto_mocks['aws'] = mock_aws()
        self.moto_mocks['aws'].start()
        
        # Set up AWS credentials
        os.environ.update({
            'AWS_ACCESS_KEY_ID': 'testing',
            'AWS_SECRET_ACCESS_KEY': 'testing',
            'AWS_SECURITY_TOKEN': 'testing',
            'AWS_SESSION_TOKEN': 'testing',
            'AWS_DEFAULT_REGION': self.config.region
        })
        
        # Create AWS clients
        clients = {
            'dynamodb': boto3.client('dynamodb', region_name=self.config.region),
            's3': boto3.client('s3', region_name=self.config.region),
            'sqs': boto3.client('sqs', region_name=self.config.region)
        }
        
        # Set up resources
        self._create_dynamodb_tables(clients['dynamodb'])
        self._create_s3_buckets(clients['s3'])
        self._create_sqs_queues(clients['sqs'])
        
        return clients
    
    def _create_dynamodb_tables(self, client) -> None:
        """Create DynamoDB tables for testing."""
        tables = [
            (self.config.presentations_table, 'presentation_id'),
            (self.config.checkpoints_table, 'checkpoint_id'),
            (self.config.users_table, 'user_id'),
            (self.config.analytics_table, 'event_id')
        ]
        
        for table_name, key_name in tables:
            try:
                client.create_table(
                    TableName=table_name,
                    KeySchema=[{'AttributeName': key_name, 'KeyType': 'HASH'}],
                    AttributeDefinitions=[{'AttributeName': key_name, 'AttributeType': 'S'}],
                    BillingMode='PAY_PER_REQUEST'
                )
                self.created_resources['tables'].append(table_name)
            except Exception as e:
                print(f"Warning: Could not create table {table_name}: {e}")
    
    def _create_s3_buckets(self, client) -> None:
        """Create S3 buckets for testing."""
        buckets = [
            self.config.presentations_bucket,
            self.config.images_bucket,
            self.config.assets_bucket
        ]
        
        for bucket_name in buckets:
            try:
                client.create_bucket(Bucket=bucket_name)
                self.created_resources['buckets'].append(bucket_name)
            except Exception as e:
                print(f"Warning: Could not create bucket {bucket_name}: {e}")
    
    def _create_sqs_queues(self, client) -> None:
        """Create SQS queues for testing."""
        queues = [self.config.presentation_queue, self.config.dlq_queue]
        
        for queue_name in queues:
            try:
                response = client.create_queue(QueueName=queue_name)
                self.created_resources['queues'].append(response['QueueUrl'])
            except Exception as e:
                print(f"Warning: Could not create queue {queue_name}: {e}")
    
    def populate_test_data(self, clients: Dict[str, Any]) -> None:
        """Populate test data in AWS resources."""
        data_config = TestDataConfig()
        dynamodb = clients['dynamodb']
        
        # Add sample presentations to DynamoDB
        for presentation_data in data_config.sample_presentations.values():
            try:
                item = {
                    k: {'S': str(v)} if isinstance(v, (str, int)) else {'S': json.dumps(v)}
                    for k, v in presentation_data.items()
                }
                
                dynamodb.put_item(
                    TableName=self.config.presentations_table,
                    Item=item
                )
            except Exception as e:
                print(f"Warning: Could not add test presentation: {e}")
    
    def cleanup(self) -> None:
        """Clean up test environment."""
        # Stop moto mocks
        for mock in self.moto_mocks.values():
            mock.stop()
        
        # Reset environment variables
        env_vars = [
            'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 
            'AWS_SECURITY_TOKEN', 'AWS_SESSION_TOKEN',
            'AWS_DEFAULT_REGION'
        ]
        for var in env_vars:
            os.environ.pop(var, None)


class TestDataGenerator:
    """Generates test data for various scenarios."""
    
    @staticmethod
    def generate_presentation_request(
        template: str = "standard",
        overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a presentation request based on template."""
        config = TestDataConfig()
        base_request = config.sample_requests.get(template, config.sample_requests["standard"])
        
        if overrides:
            request = base_request.copy()
            request.update(overrides)
            return request
        
        return base_request.copy()
    
    @staticmethod
    def generate_invalid_requests() -> List[Dict[str, Any]]:
        """Generate a list of invalid requests for error testing."""
        config = TestDataConfig()
        return config.error_scenarios
    
    @staticmethod
    def generate_large_request(size_mb: float = 1.0) -> Dict[str, Any]:
        """Generate a request with large payload for testing limits."""
        base_request = TestDataGenerator.generate_presentation_request()
        
        # Add large content to reach desired size
        content_size = int(size_mb * 1024 * 1024)  # Convert MB to bytes
        large_content = "x" * content_size
        
        base_request["custom_content"] = large_content
        return base_request
    
    @staticmethod
    def generate_concurrent_requests(count: int = 10) -> List[Dict[str, Any]]:
        """Generate multiple requests for concurrent testing."""
        requests = []
        for i in range(count):
            request = TestDataGenerator.generate_presentation_request()
            request["topic"] = f"Concurrent Test Topic {i+1}"
            requests.append(request)
        return requests


class TestAssertions:
    """Custom assertions for integration tests."""
    
    @staticmethod
    def assert_valid_api_response(
        response: Dict[str, Any], 
        expected_status: int = 200
    ) -> None:
        """Assert response has valid API format."""
        assert "statusCode" in response, "Response missing statusCode"
        assert "body" in response, "Response missing body"
        assert response["statusCode"] == expected_status, \
            f"Expected status {expected_status}, got {response['statusCode']}"
        
        if response.get("body"):
            try:
                json.loads(response["body"])
            except json.JSONDecodeError:
                assert False, "Response body is not valid JSON"
    
    @staticmethod
    def assert_error_response(
        response: Dict[str, Any],
        expected_error_type: str,
        expected_status: int = 400
    ) -> None:
        """Assert response is a properly formatted error."""
        TestAssertions.assert_valid_api_response(response, expected_status)
        
        body = json.loads(response["body"])
        assert "error" in body, "Error response missing error field"
        assert expected_error_type.lower() in body["error"].lower(), \
            f"Expected error type '{expected_error_type}' not found in '{body['error']}'"
    
    @staticmethod
    def assert_presentation_response(
        response: Dict[str, Any],
        expected_fields: List[str] = None
    ) -> None:
        """Assert response contains valid presentation data."""
        TestAssertions.assert_valid_api_response(response)
        
        body = json.loads(response["body"])
        
        # Default expected fields for presentation responses
        if expected_fields is None:
            expected_fields = ["presentation_id", "status"]
        
        for field in expected_fields:
            assert field in body, f"Presentation response missing field: {field}"
    
    @staticmethod
    def assert_task_response(
        response: Dict[str, Any],
        expected_fields: List[str] = None
    ) -> None:
        """Assert response contains valid task data."""
        TestAssertions.assert_valid_api_response(response)
        
        body = json.loads(response["body"])
        
        # Default expected fields for task responses
        if expected_fields is None:
            expected_fields = ["task_id", "status", "progress"]
        
        for field in expected_fields:
            assert field in body, f"Task response missing field: {field}"
    
    @staticmethod
    def assert_response_time(actual_time_ms: int, max_time_ms: int = 30000) -> None:
        """Assert response time is within acceptable limits."""
        assert actual_time_ms <= max_time_ms, \
            f"Response time {actual_time_ms}ms exceeds maximum {max_time_ms}ms"
    
    @staticmethod
    def assert_concurrent_responses(
        responses: List[Dict[str, Any]],
        expected_count: int,
        expected_status: int = 200
    ) -> None:
        """Assert all concurrent responses are valid."""
        assert len(responses) == expected_count, \
            f"Expected {expected_count} responses, got {len(responses)}"
        
        for i, response in enumerate(responses):
            try:
                TestAssertions.assert_valid_api_response(response, expected_status)
            except AssertionError as e:
                assert False, f"Response {i+1} failed validation: {e}"


# Global test configuration instances
TEST_API_CONFIG = TestAPIConfig()
TEST_AWS_CONFIG = TestAWSConfig()
TEST_DATA_CONFIG = TestDataConfig()

# Environment setup functions for pytest fixtures
def setup_test_environment() -> TestEnvironmentManager:
    """Create and setup test environment."""
    env_manager = TestEnvironmentManager()
    return env_manager

def get_test_configuration() -> Dict[str, Any]:
    """Get complete test configuration."""
    return {
        "api": asdict(TEST_API_CONFIG),
        "aws": asdict(TEST_AWS_CONFIG),
        "data": asdict(TEST_DATA_CONFIG)
    }


if __name__ == "__main__":
    # Configuration validation and testing
    print("Integration Test Configuration")
    print("=" * 40)
    
    config = get_test_configuration()
    print(f"API Base URL: {config['api']['base_url']}")
    print(f"AWS Region: {config['aws']['region']}")
    print(f"Test Presentations: {len(config['data']['sample_presentations'])}")
    print(f"Test Requests: {len(config['data']['sample_requests'])}")
    print(f"Error Scenarios: {len(config['data']['error_scenarios'])}")
    
    # Test environment setup
    print("\nTesting Environment Setup...")
    env_manager = setup_test_environment()
    try:
        clients = env_manager.setup_aws_environment()
        print(f"✓ Created {len(env_manager.created_resources['tables'])} DynamoDB tables")
        print(f"✓ Created {len(env_manager.created_resources['buckets'])} S3 buckets")
        print(f"✓ Created {len(env_manager.created_resources['queues'])} SQS queues")
        
        env_manager.populate_test_data(clients)
        print("✓ Populated test data")
    finally:
        env_manager.cleanup()
        print("✓ Cleaned up test environment")
    
    print("\nConfiguration validation complete!")