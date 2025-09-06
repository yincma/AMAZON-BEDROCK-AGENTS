"""
Lambda function for listing presentations
Handles GET /presentations requests
"""

import json
import logging
import os
from typing import Any, Dict
from datetime import datetime
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key

# Helper function to convert Decimal to float for JSON serialization
def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: decimal_to_float(value) for key, value in obj.items()}
    return obj

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Environment variables
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "ai-ppt-assistant-dev-sessions")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    List all presentations from DynamoDB
    
    Args:
        event: API Gateway event
        context: Lambda context
    
    Returns:
        API Gateway response
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Get query parameters
        query_params = event.get("queryStringParameters") or {}
        page_size = int(query_params.get("page_size", "20"))
        status_filter = query_params.get("status")
        
        # For now, return mock data since DynamoDB might not have presentations yet
        # In production, you would query DynamoDB here
        mock_presentations = []
        
        # Try to query DynamoDB (but handle if table doesn't exist or is empty)
        try:
            table = dynamodb.Table(TABLE_NAME)
            
            # Scan the table (in production, use query with proper indexes)
            scan_params = {
                "Limit": page_size
            }
            
            if status_filter:
                scan_params["FilterExpression"] = Key("status").eq(status_filter)
            
            response = table.scan(**scan_params)
            
            # Format presentations
            for item in response.get("Items", []):
                if item.get("presentation_id"):  # Only include actual presentations
                    presentation = {
                        "presentation_id": item.get("presentation_id"),
                        "title": item.get("title", "Untitled"),
                        "status": item.get("status", "unknown"),
                        "created_at": item.get("created_at", datetime.utcnow().isoformat()),
                        "metadata": {
                            "total_slides": item.get("slide_count", 0),
                            "language": item.get("language", "zh-CN"),
                            "style": item.get("style", "modern")
                        }
                    }
                    # Convert any Decimal values to float
                    mock_presentations.append(decimal_to_float(presentation))
        except Exception as e:
            logger.warning(f"Could not query DynamoDB: {str(e)}")
            # Return empty list if DynamoDB query fails
        
        # Return response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
            },
            "body": json.dumps(decimal_to_float({
                "presentations": mock_presentations,
                "count": len(mock_presentations),
                "next_page_token": None
            }))
        }
        
    except Exception as e:
        logger.error(f"Error listing presentations: {str(e)}")
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(decimal_to_float({
                "error": "INTERNAL_ERROR",
                "message": f"Failed to list presentations: {str(e)}"
            }))
        }