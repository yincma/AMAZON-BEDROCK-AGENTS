"""
Workflow Orchestrator Lambda Function
Manages Step Functions execution for PPT generation with performance optimization
"""

import json
import boto3
import os
import uuid
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
stepfunctions = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Environment variables
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
S3_BUCKET = os.environ.get('S3_BUCKET')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')

# Performance configuration
MAX_CONCURRENT_EXECUTIONS = 50
DEFAULT_SLIDE_COUNT = 10
MAX_SLIDES = 20
EXECUTION_TIMEOUT_SECONDS = 300  # 5 minutes

class WorkflowOrchestrator:
    """Orchestrates PPT generation workflow with performance optimization"""

    def __init__(self):
        self.table = dynamodb.Table(DYNAMODB_TABLE) if DYNAMODB_TABLE else None
        self.metrics = {
            'started_at': None,
            'completed_at': None,
            'total_slides': 0,
            'parallel_batches': 0
        }

    def start_workflow(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new Step Functions execution for PPT generation

        Args:
            request_data: Request parameters for PPT generation

        Returns:
            Response with execution details
        """
        try:
            # Generate unique task ID
            task_id = str(uuid.uuid4())
            timestamp = int(time.time())

            # Extract and validate parameters
            title = request_data.get('title', 'Untitled Presentation')
            num_slides = min(
                int(request_data.get('num_slides', DEFAULT_SLIDE_COUNT)),
                MAX_SLIDES
            )
            style = request_data.get('style', 'professional')
            language = request_data.get('language', 'en')
            user_id = request_data.get('user_id', 'anonymous')
            priority = request_data.get('priority', 'normal')

            # Calculate optimal parallel processing parameters
            parallel_config = self._calculate_parallel_config(num_slides, priority)

            # Prepare execution input
            execution_input = {
                'task_id': task_id,
                'timestamp': str(timestamp),
                'title': title,
                'num_slides': str(num_slides),
                'style': style,
                'language': language,
                'user_id': user_id,
                'priority': priority,
                's3_bucket': S3_BUCKET,
                'dynamodb_table': DYNAMODB_TABLE,
                'ttl': str(timestamp + 86400),  # 24 hours TTL
                'parallel_config': parallel_config,
                'content_generator_function': f"ai-ppt-content-generator-{ENVIRONMENT}",
                'image_generator_function': f"ai-ppt-image-generator-{ENVIRONMENT}",
                'compile_ppt_function': f"ai-ppt-compiler-{ENVIRONMENT}"
            }

            # Start Step Functions execution
            execution_name = f"ppt-gen-{task_id}-{timestamp}"
            response = stepfunctions.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=execution_name,
                input=json.dumps(execution_input)
            )

            # Log metrics
            self._log_metrics({
                'action': 'workflow_started',
                'task_id': task_id,
                'num_slides': num_slides,
                'parallel_batches': parallel_config['batch_size']
            })

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'task_id': task_id,
                    'status': 'started',
                    'execution_arn': response['executionArn'],
                    'estimated_time': self._estimate_completion_time(num_slides, priority),
                    'message': f'PPT generation started for {num_slides} slides'
                })
            }

        except Exception as e:
            logger.error(f"Error starting workflow: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to start workflow',
                    'message': str(e)
                })
            }

    def check_execution_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check the status of a workflow execution

        Args:
            task_id: Task ID to check

        Returns:
            Execution status details
        """
        try:
            # Query DynamoDB for task status
            if self.table:
                response = self.table.query(
                    KeyConditionExpression='task_id = :tid',
                    ExpressionAttributeValues={
                        ':tid': task_id
                    },
                    ScanIndexForward=False,
                    Limit=1
                )

                if response['Items']:
                    item = response['Items'][0]
                    status = item.get('status', 'unknown')
                    progress = int(item.get('progress', 0))

                    result = {
                        'task_id': task_id,
                        'status': status,
                        'progress': progress,
                        'title': item.get('title', ''),
                        'created_at': item.get('created_at', 0)
                    }

                    if status == 'completed':
                        result['ppt_url'] = item.get('ppt_url', '')
                        result['completed_at'] = item.get('completed_at', 0)

                        # Calculate processing time
                        if 'created_at' in item and 'completed_at' in item:
                            processing_time = int(item['completed_at']) - int(item['created_at'])
                            result['processing_time_seconds'] = processing_time

                    elif status == 'failed':
                        result['error_message'] = item.get('error_message', 'Unknown error')

                    return {
                        'statusCode': 200,
                        'body': json.dumps(result)
                    }

            # Task not found
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Task not found',
                    'task_id': task_id
                })
            }

        except Exception as e:
            logger.error(f"Error checking execution status: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to check status',
                    'message': str(e)
                })
            }

    def list_executions(self, user_id: Optional[str] = None,
                       status: Optional[str] = None,
                       limit: int = 10) -> Dict[str, Any]:
        """
        List workflow executions with optional filtering

        Args:
            user_id: Filter by user ID
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of executions
        """
        try:
            if not self.table:
                return {
                    'statusCode': 503,
                    'body': json.dumps({
                        'error': 'Database not available'
                    })
                }

            # Build query parameters
            if user_id:
                response = self.table.query(
                    IndexName='user-index',
                    KeyConditionExpression='user_id = :uid',
                    ExpressionAttributeValues={
                        ':uid': user_id
                    },
                    ScanIndexForward=False,
                    Limit=limit
                )
            elif status:
                response = self.table.query(
                    IndexName='status-index',
                    KeyConditionExpression='#s = :status',
                    ExpressionAttributeNames={
                        '#s': 'status'
                    },
                    ExpressionAttributeValues={
                        ':status': status
                    },
                    ScanIndexForward=False,
                    Limit=limit
                )
            else:
                # Scan with limit (less efficient but works for small datasets)
                response = self.table.scan(Limit=limit)

            # Format results
            executions = []
            for item in response.get('Items', []):
                execution = {
                    'task_id': item.get('task_id'),
                    'title': item.get('title'),
                    'status': item.get('status'),
                    'progress': int(item.get('progress', 0)),
                    'created_at': int(item.get('created_at', 0)),
                    'user_id': item.get('user_id')
                }

                if item.get('status') == 'completed':
                    execution['ppt_url'] = item.get('ppt_url')

                executions.append(execution)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'executions': executions,
                    'count': len(executions)
                })
            }

        except Exception as e:
            logger.error(f"Error listing executions: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to list executions',
                    'message': str(e)
                })
            }

    def cancel_execution(self, task_id: str) -> Dict[str, Any]:
        """
        Cancel a running workflow execution

        Args:
            task_id: Task ID to cancel

        Returns:
            Cancellation result
        """
        try:
            # Find execution ARN by task ID
            execution_name_prefix = f"ppt-gen-{task_id}"

            # List executions with the prefix
            response = stepfunctions.list_executions(
                stateMachineArn=STATE_MACHINE_ARN,
                statusFilter='RUNNING',
                maxResults=10
            )

            # Find matching execution
            execution_arn = None
            for execution in response.get('executions', []):
                if execution_name_prefix in execution['name']:
                    execution_arn = execution['executionArn']
                    break

            if execution_arn:
                # Stop the execution
                stepfunctions.stop_execution(
                    executionArn=execution_arn,
                    cause='User requested cancellation'
                )

                # Update DynamoDB status
                if self.table:
                    self.table.update_item(
                        Key={'task_id': task_id},
                        UpdateExpression='SET #s = :status, cancelled_at = :now',
                        ExpressionAttributeNames={'#s': 'status'},
                        ExpressionAttributeValues={
                            ':status': 'cancelled',
                            ':now': int(time.time())
                        }
                    )

                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'task_id': task_id,
                        'status': 'cancelled',
                        'message': 'Execution cancelled successfully'
                    })
                }
            else:
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': 'Execution not found',
                        'task_id': task_id
                    })
                }

        except Exception as e:
            logger.error(f"Error cancelling execution: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to cancel execution',
                    'message': str(e)
                })
            }

    def _calculate_parallel_config(self, num_slides: int, priority: str) -> Dict[str, Any]:
        """
        Calculate optimal parallel processing configuration

        Args:
            num_slides: Number of slides to generate
            priority: Processing priority (low/normal/high)

        Returns:
            Parallel processing configuration
        """
        # Base configuration
        config = {
            'batch_size': 5,
            'max_concurrency': 10,
            'timeout_seconds': 30,
            'retry_attempts': 3
        }

        # Adjust based on priority
        if priority == 'high':
            config['batch_size'] = min(10, num_slides)
            config['max_concurrency'] = 20
            config['timeout_seconds'] = 45
        elif priority == 'low':
            config['batch_size'] = 3
            config['max_concurrency'] = 5
            config['timeout_seconds'] = 20

        # Optimize for slide count
        if num_slides <= 5:
            config['batch_size'] = num_slides
            config['max_concurrency'] = num_slides
        elif num_slides > 15:
            config['batch_size'] = 8
            config['max_concurrency'] = 15

        return config

    def _estimate_completion_time(self, num_slides: int, priority: str) -> int:
        """
        Estimate completion time in seconds

        Args:
            num_slides: Number of slides
            priority: Processing priority

        Returns:
            Estimated seconds to completion
        """
        # Base time per slide (seconds)
        base_time_per_slide = 3

        # Adjust for priority
        if priority == 'high':
            base_time_per_slide = 2
        elif priority == 'low':
            base_time_per_slide = 4

        # Account for parallel processing
        parallel_factor = 0.4  # 60% reduction due to parallelization

        estimated_time = num_slides * base_time_per_slide * parallel_factor

        # Add overhead for compilation and S3 operations
        overhead = 5

        return int(estimated_time + overhead)

    def _log_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Log performance metrics for monitoring

        Args:
            metrics: Metrics to log
        """
        logger.info(json.dumps({
            'type': 'performance_metrics',
            'timestamp': datetime.utcnow().isoformat(),
            'environment': ENVIRONMENT,
            **metrics
        }))


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for workflow orchestration

    Args:
        event: Lambda event
        context: Lambda context

    Returns:
        API response
    """
    orchestrator = WorkflowOrchestrator()

    # Parse request
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '')
    path_parameters = event.get('pathParameters', {})
    body = json.loads(event.get('body', '{}')) if event.get('body') else {}
    query_parameters = event.get('queryStringParameters', {}) or {}

    # Add CORS headers to all responses
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS'
    }

    try:
        # Route request based on path and method
        if path == '/workflow/start' and http_method == 'POST':
            response = orchestrator.start_workflow(body)

        elif path.startswith('/workflow/status/') and http_method == 'GET':
            task_id = path_parameters.get('task_id', path.split('/')[-1])
            response = orchestrator.check_execution_status(task_id)

        elif path == '/workflow/list' and http_method == 'GET':
            user_id = query_parameters.get('user_id')
            status = query_parameters.get('status')
            limit = int(query_parameters.get('limit', 10))
            response = orchestrator.list_executions(user_id, status, limit)

        elif path.startswith('/workflow/cancel/') and http_method == 'DELETE':
            task_id = path_parameters.get('task_id', path.split('/')[-1])
            response = orchestrator.cancel_execution(task_id)

        else:
            response = {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'Not Found',
                    'message': f'Path {path} with method {http_method} not found'
                })
            }

        # Add CORS headers to response
        if 'headers' not in response:
            response['headers'] = {}
        response['headers'].update(cors_headers)

        return response

    except Exception as e:
        logger.error(f"Unexpected error in handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e)
            })
        }


# Performance monitoring decorator
def monitor_performance(func):
    """Decorator to monitor function performance"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time

        logger.info(f"Function {func.__name__} executed in {execution_time:.2f} seconds")

        return result
    return wrapper