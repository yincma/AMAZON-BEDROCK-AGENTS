"""
Placeholder Lambda function for downloading generated PPT
"""
import json
import boto3
import os
from botocore.exceptions import ClientError

s3_client = boto3.client('s3')

def handler(event, context):
    """
    Main handler for PPT download
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

        # Generate presigned URL for S3 object
        s3_bucket = os.environ.get('S3_BUCKET')
        if s3_bucket:
            try:
                ppt_key = f"presentations/{presentation_id}/output/presentation.pptx"

                # Check if file exists
                s3_client.head_object(Bucket=s3_bucket, Key=ppt_key)

                # Generate presigned URL (valid for 1 hour)
                download_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': s3_bucket,
                        'Key': ppt_key,
                        'ResponseContentDisposition': f'attachment; filename="presentation_{presentation_id}.pptx"'
                    },
                    ExpiresIn=3600
                )

                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'presentation_id': presentation_id,
                        'download_url': download_url,
                        'expires_in': 3600,
                        'message': 'Download URL generated successfully'
                    })
                }

            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return {
                        'statusCode': 404,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'error': 'Presentation not found',
                            'message': f'PPT file not found for presentation ID: {presentation_id}'
                        })
                    }
                raise

        # Fallback if S3 bucket not configured
        return {
            'statusCode': 503,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Service unavailable',
                'message': 'S3 bucket not configured'
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
                'message': 'Failed to generate download URL'
            })
        }