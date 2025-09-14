"""
Placeholder Lambda function for checking PPT generation status
"""
import json
import boto3
import os

s3_client = boto3.client('s3')

def handler(event, context):
    """
    Main handler for status checking
    """
    try:
        # Get presentation ID from path parameters
        presentation_id = event.get('pathParameters', {}).get('id')

        if not presentation_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing presentation ID',
                    'message': 'Please provide a valid presentation ID'
                })
            }

        # Try to fetch metadata from S3
        s3_bucket = os.environ.get('S3_BUCKET')
        if s3_bucket:
            try:
                s3_key = f"presentations/{presentation_id}/metadata.json"
                response = s3_client.get_object(
                    Bucket=s3_bucket,
                    Key=s3_key
                )
                metadata = json.loads(response['Body'].read().decode('utf-8'))

                # Check if PPT file exists
                ppt_key = f"presentations/{presentation_id}/output/presentation.pptx"
                try:
                    s3_client.head_object(Bucket=s3_bucket, Key=ppt_key)
                    metadata['status'] = 'completed'
                except:
                    metadata['status'] = 'processing'

                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps(metadata)
                }
            except s3_client.exceptions.NoSuchKey:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Presentation not found',
                        'message': f'No presentation found with ID: {presentation_id}'
                    })
                }

        # Fallback response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'presentation_id': presentation_id,
                'status': 'unknown',
                'message': 'Unable to retrieve status'
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to check status'
            })
        }