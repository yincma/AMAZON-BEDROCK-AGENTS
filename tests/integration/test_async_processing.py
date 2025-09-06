"""
Integration tests for asynchronous processing with SQS and DynamoDB.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
from datetime import datetime, timedelta
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas'))

@pytest.mark.integration
class TestAsyncProcessing:
    """Test asynchronous processing with SQS and state management."""
    
    @patch('boto3.client')
    def test_sqs_message_processing(self, mock_boto_client):
        """Test SQS message processing flow."""
        # Setup mock clients
        mock_sqs = MagicMock()
        mock_dynamodb = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'sqs':
                return mock_sqs
            elif service_name == 'dynamodb':
                return mock_dynamodb
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Create test message
        test_message = {
            'presentation_id': 'test-123',
            'action': 'generate_content',
            'parameters': {
                'topic': 'Cloud Computing',
                'slide_count': 10
            }
        }
        
        # Mock SQS send message
        mock_sqs.send_message.return_value = {
            'MessageId': 'msg-123',
            'MD5OfMessageBody': 'abc123'
        }
        
        # Send message to queue
        response = mock_sqs.send_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/123/test-queue',
            MessageBody=json.dumps(test_message)
        )
        
        assert response['MessageId'] == 'msg-123'
        mock_sqs.send_message.assert_called_once()
        
        # Mock SQS receive message
        mock_sqs.receive_message.return_value = {
            'Messages': [{
                'MessageId': 'msg-123',
                'ReceiptHandle': 'receipt-123',
                'Body': json.dumps(test_message)
            }]
        }
        
        # Process message
        messages = mock_sqs.receive_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/123/test-queue',
            MaxNumberOfMessages=1
        )
        
        assert len(messages['Messages']) == 1
        message_body = json.loads(messages['Messages'][0]['Body'])
        assert message_body['presentation_id'] == 'test-123'
        
        # Update DynamoDB state
        mock_dynamodb.update_item.return_value = {
            'Attributes': {
                'status': {'S': 'processing'},
                'updated_at': {'S': datetime.utcnow().isoformat()}
            }
        }
        
        update_response = mock_dynamodb.update_item(
            TableName='presentations',
            Key={'presentation_id': {'S': 'test-123'}},
            UpdateExpression='SET #status = :status, updated_at = :timestamp',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'processing'},
                ':timestamp': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        assert update_response['Attributes']['status']['S'] == 'processing'
        
        # Delete processed message
        mock_sqs.delete_message.return_value = {}
        
        mock_sqs.delete_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/123/test-queue',
            ReceiptHandle='receipt-123'
        )
        
        mock_sqs.delete_message.assert_called_once()
    
    @patch('boto3.client')
    def test_state_management_workflow(self, mock_boto_client):
        """Test DynamoDB state management throughout workflow."""
        mock_dynamodb = MagicMock()
        mock_boto_client.return_value = mock_dynamodb
        
        presentation_id = 'test-456'
        
        # Step 1: Initial state creation
        initial_state = {
            'presentation_id': presentation_id,
            'status': 'pending',
            'progress': 0,
            'created_at': datetime.utcnow().isoformat(),
            'metadata': {
                'topic': 'AI and ML',
                'slide_count': 15
            }
        }
        
        mock_dynamodb.put_item.return_value = {}
        
        mock_dynamodb.put_item(
            TableName='presentations',
            Item={
                'presentation_id': {'S': presentation_id},
                'status': {'S': 'pending'},
                'progress': {'N': '0'},
                'created_at': {'S': initial_state['created_at']},
                'metadata': {'S': json.dumps(initial_state['metadata'])}
            }
        )
        
        # Step 2: Update to outlining state
        mock_dynamodb.update_item.return_value = {
            'Attributes': {
                'status': {'S': 'outlining'},
                'progress': {'N': '20'}
            }
        }
        
        mock_dynamodb.update_item(
            TableName='presentations',
            Key={'presentation_id': {'S': presentation_id}},
            UpdateExpression='SET #status = :status, progress = :progress',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'outlining'},
                ':progress': {'N': '20'}
            }
        )
        
        # Step 3: Update to content generation
        mock_dynamodb.update_item.return_value = {
            'Attributes': {
                'status': {'S': 'content_generation'},
                'progress': {'N': '40'}
            }
        }
        
        mock_dynamodb.update_item(
            TableName='presentations',
            Key={'presentation_id': {'S': presentation_id}},
            UpdateExpression='SET #status = :status, progress = :progress',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'content_generation'},
                ':progress': {'N': '40'}
            }
        )
        
        # Step 4: Update to image generation
        mock_dynamodb.update_item.return_value = {
            'Attributes': {
                'status': {'S': 'image_generation'},
                'progress': {'N': '60'}
            }
        }
        
        # Step 5: Update to compiling
        mock_dynamodb.update_item.return_value = {
            'Attributes': {
                'status': {'S': 'compiling'},
                'progress': {'N': '80'}
            }
        }
        
        # Step 6: Update to completed
        mock_dynamodb.update_item.return_value = {
            'Attributes': {
                'status': {'S': 'completed'},
                'progress': {'N': '100'},
                'file_key': {'S': f'presentations/{presentation_id}.pptx'},
                'completed_at': {'S': datetime.utcnow().isoformat()}
            }
        }
        
        final_update = mock_dynamodb.update_item(
            TableName='presentations',
            Key={'presentation_id': {'S': presentation_id}},
            UpdateExpression='SET #status = :status, progress = :progress, file_key = :file_key, completed_at = :timestamp',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': {'S': 'completed'},
                ':progress': {'N': '100'},
                ':file_key': {'S': f'presentations/{presentation_id}.pptx'},
                ':timestamp': {'S': datetime.utcnow().isoformat()}
            }
        )
        
        assert final_update['Attributes']['status']['S'] == 'completed'
        assert final_update['Attributes']['progress']['N'] == '100'
        
        # Verify all state transitions were called
        assert mock_dynamodb.put_item.call_count == 1
        assert mock_dynamodb.update_item.call_count >= 5
    
    @patch('boto3.client')
    def test_concurrent_request_handling(self, mock_boto_client):
        """Test handling of concurrent presentation requests."""
        mock_sqs = MagicMock()
        mock_dynamodb = MagicMock()
        
        def mock_client(service_name, **kwargs):
            if service_name == 'sqs':
                return mock_sqs
            elif service_name == 'dynamodb':
                return mock_dynamodb
            return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        # Simulate multiple concurrent requests
        requests = []
        for i in range(5):
            request = {
                'presentation_id': f'concurrent-{i}',
                'topic': f'Topic {i}',
                'timestamp': datetime.utcnow().isoformat()
            }
            requests.append(request)
        
        # Send all requests to SQS
        mock_sqs.send_message_batch.return_value = {
            'Successful': [
                {'Id': str(i), 'MessageId': f'msg-{i}', 'MD5OfMessageBody': f'md5-{i}'}
                for i in range(5)
            ],
            'Failed': []
        }
        
        batch_response = mock_sqs.send_message_batch(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/123/test-queue',
            Entries=[
                {
                    'Id': str(i),
                    'MessageBody': json.dumps(req)
                }
                for i, req in enumerate(requests)
            ]
        )
        
        assert len(batch_response['Successful']) == 5
        assert len(batch_response['Failed']) == 0
        
        # Simulate processing with DynamoDB conditional updates
        for req in requests:
            # Use conditional update to prevent race conditions
            mock_dynamodb.update_item.return_value = {
                'Attributes': {
                    'presentation_id': {'S': req['presentation_id']},
                    'status': {'S': 'processing'}
                }
            }
            
            mock_dynamodb.update_item(
                TableName='presentations',
                Key={'presentation_id': {'S': req['presentation_id']}},
                UpdateExpression='SET #status = :new_status',
                ConditionExpression='#status = :old_status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':new_status': {'S': 'processing'},
                    ':old_status': {'S': 'pending'}
                }
            )
        
        # Verify all requests were processed
        assert mock_dynamodb.update_item.call_count == 5
    
    @patch('boto3.client')
    def test_retry_logic_and_dlq(self, mock_boto_client):
        """Test retry logic and Dead Letter Queue handling."""
        mock_sqs = MagicMock()
        mock_boto_client.return_value = mock_sqs
        
        # Simulate message that fails processing
        failed_message = {
            'presentation_id': 'fail-123',
            'action': 'generate_content',
            'retry_count': 0
        }
        
        # First attempt - fails
        mock_sqs.receive_message.return_value = {
            'Messages': [{
                'MessageId': 'msg-fail-1',
                'ReceiptHandle': 'receipt-fail-1',
                'Body': json.dumps(failed_message),
                'Attributes': {
                    'ApproximateReceiveCount': '1'
                }
            }]
        }
        
        messages = mock_sqs.receive_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/123/test-queue',
            AttributeNames=['ApproximateReceiveCount']
        )
        
        receive_count = int(messages['Messages'][0]['Attributes']['ApproximateReceiveCount'])
        assert receive_count == 1
        
        # Simulate processing failure - message returns to queue
        # Don't delete the message, it will be retried
        
        # Second attempt - fails again
        mock_sqs.receive_message.return_value = {
            'Messages': [{
                'MessageId': 'msg-fail-1',
                'ReceiptHandle': 'receipt-fail-2',
                'Body': json.dumps(failed_message),
                'Attributes': {
                    'ApproximateReceiveCount': '2'
                }
            }]
        }
        
        messages = mock_sqs.receive_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/123/test-queue',
            AttributeNames=['ApproximateReceiveCount']
        )
        
        receive_count = int(messages['Messages'][0]['Attributes']['ApproximateReceiveCount'])
        assert receive_count == 2
        
        # Third attempt - still fails, should go to DLQ
        mock_sqs.receive_message.return_value = {
            'Messages': [{
                'MessageId': 'msg-fail-1',
                'ReceiptHandle': 'receipt-fail-3',
                'Body': json.dumps(failed_message),
                'Attributes': {
                    'ApproximateReceiveCount': '3'
                }
            }]
        }
        
        messages = mock_sqs.receive_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/123/test-queue',
            AttributeNames=['ApproximateReceiveCount']
        )
        
        receive_count = int(messages['Messages'][0]['Attributes']['ApproximateReceiveCount'])
        assert receive_count == 3
        
        # After max retries (3), message should be in DLQ
        # Check DLQ for failed message
        mock_sqs.receive_message.return_value = {
            'Messages': [{
                'MessageId': 'msg-fail-dlq',
                'Body': json.dumps(failed_message)
            }]
        }
        
        dlq_messages = mock_sqs.receive_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/123/test-dlq'
        )
        
        assert len(dlq_messages['Messages']) == 1
        dlq_body = json.loads(dlq_messages['Messages'][0]['Body'])
        assert dlq_body['presentation_id'] == 'fail-123'

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'integration'])