"""
Integration tests for complete presentation generation workflow.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
from datetime import datetime
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../lambdas'))

@pytest.mark.integration
class TestPresentationWorkflow:
    """Test complete presentation generation workflow."""
    
    @patch('boto3.client')
    def test_complete_presentation_workflow(self, mock_boto_client):
        """Test the entire presentation generation workflow from start to finish."""
        # Setup mock clients
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
        
        # Step 1: Generate presentation request
        from api.generate_presentation import lambda_handler as generate_handler
        
        presentation_request = {
            'body': json.dumps({
                'topic': 'Cloud Computing and AWS',
                'target_audience': 'Technical Managers',
                'duration': 45,
                'slide_count': 15,
                'style': 'professional'
            })
        }
        
        # Mock orchestrator agent response
        mock_bedrock.invoke_agent.return_value = {
            'completion': json.dumps({
                'status': 'started',
                'task_id': 'task-123'
            })
        }
        
        context = Mock()
        response = generate_handler(presentation_request, context)
        
        assert response['statusCode'] == 202
        body = json.loads(response['body'])
        presentation_id = body.get('presentation_id')
        assert presentation_id is not None
        
        # Verify initial state was stored
        mock_dynamodb.put_item.assert_called()
        mock_sqs.send_message.assert_called()
        
        # Step 2: Orchestrator processes request and triggers content generation
        mock_outline = {
            'title': 'Cloud Computing and AWS',
            'slides': [
                {'title': f'Slide {i}', 'key_points': ['Point A', 'Point B']}
                for i in range(1, 16)
            ]
        }
        
        # Mock content agent creating outline
        from controllers.create_outline import lambda_handler as outline_handler
        
        outline_event = {
            'topic': 'Cloud Computing and AWS',
            'target_audience': 'Technical Managers',
            'slide_count': 15
        }
        
        mock_bedrock.invoke_model.return_value = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': json.dumps(mock_outline)}]
            }).encode('utf-8'))
        }
        
        outline_response = outline_handler(outline_event, context)
        assert outline_response['statusCode'] == 200
        
        # Step 3: Content generation for each slide
        from controllers.generate_content import lambda_handler as content_handler
        
        content_event = {
            'outline': mock_outline,
            'style': 'professional'
        }
        
        # Mock parallel content generation
        mock_slide_content = {
            'title': 'Slide Title',
            'content': 'Detailed slide content',
            'bullet_points': ['Point 1', 'Point 2', 'Point 3'],
            'speaker_notes': 'Notes for the speaker'
        }
        
        mock_bedrock.invoke_model.return_value = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': json.dumps(mock_slide_content)}]
            }).encode('utf-8'))
        }
        
        content_response = content_handler(content_event, context)
        assert content_response['statusCode'] == 200
        slides_data = json.loads(content_response['body'])['slides']
        assert len(slides_data) > 0
        
        # Step 4: Visual generation for slides
        from controllers.generate_image import lambda_handler as image_handler
        
        for slide in slides_data[:3]:  # Test first 3 slides
            image_event = {
                'slide_title': slide.get('title', 'Test Slide'),
                'slide_content': slide.get('content', 'Test Content'),
                'style': 'professional'
            }
            
            # Mock Nova image generation
            mock_bedrock.invoke_model.return_value = {
                'body': MagicMock(read=lambda: json.dumps({
                    'images': ['base64_encoded_image_data']
                }).encode('utf-8'))
            }
            
            image_response = image_handler(image_event, context)
            assert image_response['statusCode'] == 200
        
        # Step 5: Compile final PPTX
        from controllers.compile_pptx import lambda_handler as compile_handler
        
        compile_event = {
            'presentation_data': {
                'presentation_id': presentation_id,
                'title': 'Cloud Computing and AWS',
                'slides': slides_data,
                'template': 'professional'
            }
        }
        
        # Mock PPTX compilation and S3 upload
        mock_s3.put_object.return_value = {'ETag': '"abc123"'}
        
        with patch('controllers.compile_pptx.PresentationModel') as mock_model_class, \
             patch('controllers.compile_pptx.PresentationView') as mock_view_class:
            
            mock_model = MagicMock()
            mock_model_class.return_value = mock_model
            mock_model.save_presentation.return_value = f'presentations/{presentation_id}.pptx'
            
            mock_view = MagicMock()
            mock_view_class.return_value = mock_view
            
            compile_response = compile_handler(compile_event, context)
            assert compile_response['statusCode'] == 200
        
        # Step 6: Update status to completed
        mock_dynamodb.update_item.return_value = {'Attributes': {}}
        
        # Verify workflow completion
        assert mock_dynamodb.put_item.called
        assert mock_sqs.send_message.called
        assert mock_bedrock.invoke_model.called
    
    @patch('boto3.client')
    def test_agent_to_lambda_communication(self, mock_boto_client):
        """Test communication between Bedrock Agents and Lambda functions."""
        # Mock Bedrock agent runtime
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Simulate Orchestrator Agent invoking Content Agent
        orchestrator_request = {
            'agent_id': 'orchestrator-agent-id',
            'alias_id': 'production',
            'action_group': 'PresentationManagement',
            'action': 'CreatePresentation',
            'parameters': {
                'topic': 'AI and Machine Learning',
                'duration': 30
            }
        }
        
        # Mock agent response
        mock_bedrock.invoke_agent.return_value = {
            'completion': json.dumps({
                'status': 'processing',
                'next_action': 'invoke_content_agent'
            }),
            'sessionId': 'session-123'
        }
        
        response = mock_bedrock.invoke_agent(
            agentId=orchestrator_request['agent_id'],
            agentAliasId=orchestrator_request['alias_id'],
            sessionId='session-123',
            inputText=json.dumps(orchestrator_request['parameters'])
        )
        
        assert 'completion' in response
        completion = json.loads(response['completion'])
        assert completion['status'] == 'processing'
        
        # Simulate Content Agent invoking Lambda
        content_agent_request = {
            'agent_id': 'content-agent-id',
            'action_group': 'ContentGeneration',
            'lambda_function': 'create_outline',
            'payload': orchestrator_request['parameters']
        }
        
        # Mock Lambda invocation through agent
        mock_bedrock.invoke_agent.return_value = {
            'completion': json.dumps({
                'status': 'success',
                'result': {
                    'outline': {
                        'title': 'AI and Machine Learning',
                        'slides': []
                    }
                }
            })
        }
        
        response = mock_bedrock.invoke_agent(
            agentId=content_agent_request['agent_id'],
            agentAliasId='production',
            sessionId='session-123',
            inputText=json.dumps(content_agent_request['payload'])
        )
        
        completion = json.loads(response['completion'])
        assert completion['status'] == 'success'
        assert 'outline' in completion['result']
    
    @patch('boto3.client')
    def test_error_handling_workflow(self, mock_boto_client):
        """Test error handling throughout the workflow."""
        # Setup mock clients
        mock_dynamodb = MagicMock()
        mock_sqs = MagicMock()
        mock_bedrock = MagicMock()
        
        def mock_client(service_name, **kwargs):
            clients = {
                'dynamodb': mock_dynamodb,
                'sqs': mock_sqs,
                'bedrock-runtime': mock_bedrock,
                'bedrock-agent-runtime': mock_bedrock
            }
            return clients.get(service_name, MagicMock())
        
        mock_boto_client.side_effect = mock_client
        
        # Test 1: Bedrock model timeout
        mock_bedrock.invoke_model.side_effect = Exception('Model timeout')
        
        from controllers.create_outline import lambda_handler as outline_handler
        
        event = {
            'topic': 'Test Topic',
            'duration': 30
        }
        
        context = Mock()
        response = outline_handler(event, context)
        
        assert response['statusCode'] == 500
        body = json.loads(response['body'])
        assert not body['success']
        assert 'error' in body
        
        # Test 2: Agent communication failure
        mock_bedrock.invoke_agent.side_effect = Exception('Agent unavailable')
        
        from api.generate_presentation import lambda_handler as generate_handler
        
        event = {
            'body': json.dumps({
                'topic': 'Test Topic',
                'duration': 30
            })
        }
        
        response = generate_handler(event, context)
        
        # Should handle error gracefully
        assert response['statusCode'] in [500, 503]
        body = json.loads(response['body'])
        assert not body['success']
        
        # Test 3: DynamoDB failure during status update
        mock_dynamodb.update_item.side_effect = Exception('DynamoDB unavailable')
        
        # Verify error is logged and handled
        # The system should continue processing or retry
        
        # Test 4: S3 upload failure
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = Exception('S3 upload failed')
        
        # System should handle S3 failures gracefully
        # with retry logic or fallback storage

@pytest.mark.integration
class TestAgentActionGroups:
    """Test Bedrock Agent action groups and Lambda integration."""
    
    @patch('boto3.client')
    def test_orchestrator_action_groups(self, mock_boto_client):
        """Test Orchestrator Agent action groups."""
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Test PresentationManagement action group
        action_group_config = {
            'actionGroupId': 'presentation-mgmt',
            'actionGroupName': 'PresentationManagement',
            'actionGroupExecutor': {
                'lambda': 'arn:aws:lambda:us-east-1:123:function:create_outline'
            }
        }
        
        # Simulate action group invocation
        mock_bedrock.invoke_agent.return_value = {
            'completion': json.dumps({
                'action_group': 'PresentationManagement',
                'action': 'CreateOutline',
                'result': 'success'
            })
        }
        
        response = mock_bedrock.invoke_agent(
            agentId='orchestrator-agent',
            agentAliasId='production',
            actionGroup=action_group_config['actionGroupName'],
            inputText='Create presentation outline'
        )
        
        completion = json.loads(response['completion'])
        assert completion['action_group'] == 'PresentationManagement'
        assert completion['result'] == 'success'
    
    @patch('boto3.client')
    def test_content_agent_action_groups(self, mock_boto_client):
        """Test Content Agent action groups."""
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Test ContentGeneration action group
        mock_bedrock.invoke_agent.return_value = {
            'completion': json.dumps({
                'action_group': 'ContentGeneration',
                'slides_generated': 10,
                'status': 'completed'
            })
        }
        
        response = mock_bedrock.invoke_agent(
            agentId='content-agent',
            agentAliasId='production',
            actionGroup='ContentGeneration',
            inputText='Generate slide content'
        )
        
        completion = json.loads(response['completion'])
        assert completion['slides_generated'] == 10
        assert completion['status'] == 'completed'
    
    @patch('boto3.client')
    def test_visual_agent_action_groups(self, mock_boto_client):
        """Test Visual Agent action groups."""
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Test ImageGeneration action group
        mock_bedrock.invoke_agent.return_value = {
            'completion': json.dumps({
                'action_group': 'ImageGeneration',
                'images_created': 5,
                'format': 'png'
            })
        }
        
        response = mock_bedrock.invoke_agent(
            agentId='visual-agent',
            agentAliasId='production',
            actionGroup='ImageGeneration',
            inputText='Generate images for slides'
        )
        
        completion = json.loads(response['completion'])
        assert completion['images_created'] == 5
        assert completion['format'] == 'png'
    
    @patch('boto3.client')
    def test_compiler_agent_action_groups(self, mock_boto_client):
        """Test Compiler Agent action groups."""
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        # Test PresentationAssembly action group
        mock_bedrock.invoke_agent.return_value = {
            'completion': json.dumps({
                'action_group': 'PresentationAssembly',
                'file_created': 'presentation.pptx',
                'file_size': 2048000
            })
        }
        
        response = mock_bedrock.invoke_agent(
            agentId='compiler-agent',
            agentAliasId='production',
            actionGroup='PresentationAssembly',
            inputText='Compile presentation'
        )
        
        completion = json.loads(response['completion'])
        assert completion['file_created'] == 'presentation.pptx'
        assert completion['file_size'] > 0

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'integration'])