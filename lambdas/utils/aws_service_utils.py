"""
AWS Service Utilities - AI PPT Assistant
Shared utilities for AWS service interactions to eliminate code duplication
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from aws_lambda_powertools import Logger, Tracer
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configuration management
from utils.enhanced_config_manager import get_enhanced_config_manager

logger = Logger(__name__)
tracer = Tracer()


class AWSServiceManager:
    """Base class for AWS service managers"""

    def __init__(self):
        config_manager = get_enhanced_config_manager()
        aws_config = config_manager.get_aws_config()
        self.aws_region = aws_config.region
        self.s3_config = config_manager.get_s3_config()
        self.dynamodb_config = config_manager.get_dynamodb_config()
        self.security_config = config_manager.get_security_config()

    def _get_client(self, service_name: str) -> Any:
        """Get AWS service client with standard configuration"""
        return boto3.client(service_name, region_name=self.aws_region)

    def _get_resource(self, service_name: str) -> Any:
        """Get AWS service resource with standard configuration"""
        return boto3.resource(service_name, region_name=self.aws_region)


class S3ServiceManager(AWSServiceManager):
    """Standardized S3 operations"""

    def __init__(self):
        super().__init__()
        self.s3_client = self._get_client("s3")
        self.bucket_name = self.s3_config.bucket

    @tracer.capture_method
    def upload_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Upload object to S3 with standardized error handling"""

        try:
            upload_params = {
                "Bucket": self.bucket_name,
                "Key": key,
                "Body": data,
                "ContentType": content_type,
            }

            if metadata:
                upload_params["Metadata"] = metadata

            if self.security_config.encryption_enabled:
                upload_params["ServerSideEncryption"] = "AES256"

            self.s3_client.put_object(**upload_params)

            return {
                "success": True,
                "s3_key": key,
                "s3_url": f"s3://{self.bucket_name}/{key}",
                "bucket": self.bucket_name,
            }

        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.response["Error"]["Code"],
            }

    @tracer.capture_method
    def download_object(self, key: str) -> Dict[str, Any]:
        """Download object from S3"""

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)

            return {
                "success": True,
                "data": response["Body"].read(),
                "content_type": response.get("ContentType"),
                "metadata": response.get("Metadata", {}),
            }

        except ClientError as e:
            logger.error(f"S3 download error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.response["Error"]["Code"],
            }

    @tracer.capture_method
    def generate_presigned_url(
        self, key: str, expiration: int = 3600, http_method: str = "GET"
    ) -> Dict[str, Any]:
        """Generate presigned URL for S3 object"""

        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object" if http_method == "GET" else "put_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )

            return {
                "success": True,
                "url": url,
                "expires_in": expiration,
                "expires_at": datetime.now(timezone.utc).timestamp() + expiration,
            }

        except ClientError as e:
            logger.error(f"S3 presigned URL error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.response["Error"]["Code"],
            }


class DynamoDBServiceManager(AWSServiceManager):
    """Standardized DynamoDB operations"""

    def __init__(self):
        super().__init__()
        self.dynamodb = self._get_resource("dynamodb")
        self.sessions_table = self.dynamodb.Table(self.dynamodb_config.table)
        self.checkpoints_table = self.dynamodb.Table(
            self.dynamodb_config.checkpoints_table
        )

    @tracer.capture_method
    def put_item(
        self,
        table_name: str,
        item: Dict[str, Any],
        condition_expression: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Put item to DynamoDB table with standardized error handling"""

        try:
            table = self.dynamodb.Table(table_name)

            put_params = {"Item": item}
            if condition_expression:
                put_params["ConditionExpression"] = condition_expression

            table.put_item(**put_params)

            return {
                "success": True,
                "table": table_name,
                "item_key": item.get("id") or item.get("session_id") or "unknown",
            }

        except ClientError as e:
            logger.error(f"DynamoDB put error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.response["Error"]["Code"],
            }

    @tracer.capture_method
    def get_item(self, table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
        """Get item from DynamoDB table"""

        try:
            table = self.dynamodb.Table(table_name)
            response = table.get_item(Key=key)

            if "Item" in response:
                return {"success": True, "item": response["Item"]}
            else:
                return {
                    "success": False,
                    "error": "Item not found",
                    "error_code": "ITEM_NOT_FOUND",
                }

        except ClientError as e:
            logger.error(f"DynamoDB get error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.response["Error"]["Code"],
            }

    @tracer.capture_method
    def update_item(
        self,
        table_name: str,
        key: Dict[str, Any],
        update_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Update item in DynamoDB table"""

        try:
            table = self.dynamodb.Table(table_name)

            update_params = {
                "Key": key,
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": expression_attribute_values,
            }

            if expression_attribute_names:
                update_params["ExpressionAttributeNames"] = expression_attribute_names

            table.update_item(**update_params)

            return {"success": True}

        except ClientError as e:
            logger.error(f"DynamoDB update error: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": e.response["Error"]["Code"],
            }


class BedrockServiceManager(AWSServiceManager):
    """Standardized Bedrock operations"""

    def __init__(self):
        super().__init__()
        config_manager = get_enhanced_config_manager()
        bedrock_config = config_manager.get_bedrock_config()
        self.bedrock_runtime = self._get_client("bedrock-runtime")
        self.bedrock_agent_runtime = self._get_client("bedrock-agent-runtime")
        self.model_id = bedrock_config.model_id
        self.nova_model_id = bedrock_config.nova_model_id

    @tracer.capture_method
    def invoke_claude_model(
        self,
        prompt: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        """Invoke Claude model with standardized parameters"""

        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "messages": [{"role": "user", "content": prompt}],
            }

            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())
            content = response_body.get("content", [{}])[0].get("text", "{}")

            # Extract JSON from markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return {
                "success": True,
                "content": content,
                "model_id": self.model_id,
                "usage": response_body.get("usage", {}),
            }

        except Exception as e:
            logger.error(f"Bedrock Claude invocation error: {e}")
            return {"success": False, "error": str(e)}

    @tracer.capture_method
    def invoke_nova_canvas(
        self, prompt: str, width: int = 1920, height: int = 1080, cfg_scale: float = 8.0
    ) -> Dict[str, Any]:
        """Invoke Nova Canvas model for image generation"""

        try:
            request_body = {
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {
                    "text": prompt,
                    "width": width,
                    "height": height,
                    "cfgScale": cfg_scale,
                    "numberOfImages": 1,
                },
            }

            response = self.bedrock_runtime.invoke_model(
                modelId=self.nova_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body),
            )

            response_body = json.loads(response["body"].read())

            if "images" not in response_body or not response_body["images"]:
                return {"success": False, "error": "No images generated"}

            return {
                "success": True,
                "images": response_body["images"],
                "model_id": self.nova_model_id,
                "prompt": prompt,
                "dimensions": {"width": width, "height": height},
            }

        except Exception as e:
            logger.error(f"Bedrock Nova invocation error: {e}")
            return {"success": False, "error": str(e)}

    @tracer.capture_method
    def invoke_agent(
        self,
        agent_id: str,
        alias_id: str,
        session_id: str,
        input_text: str,
        enable_trace: bool = True,
    ) -> Dict[str, Any]:
        """Invoke Bedrock agent with standardized parameters"""

        try:
            response = self.bedrock_agent_runtime.invoke_agent(
                agentId=agent_id,
                agentAliasId=alias_id,
                sessionId=session_id,
                inputText=input_text,
                enableTrace=enable_trace,
            )

            # Process streaming response
            event_stream = response.get("completion", [])
            result = ""

            for event in event_stream:
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        result += chunk["bytes"].decode("utf-8")

            return {
                "success": True,
                "response": result,
                "agent_id": agent_id,
                "session_id": session_id,
            }

        except Exception as e:
            logger.error(f"Bedrock agent invocation error: {e}")
            return {"success": False, "error": str(e)}


class SQSServiceManager(AWSServiceManager):
    """Standardized SQS operations"""

    def __init__(self):
        super().__init__()
        self.sqs_client = self._get_client("sqs")
        # Get queue URL from environment variables
        self.queue_url = os.getenv("PRESENTATION_QUEUE_URL") or os.getenv(
            "SQS_QUEUE_URL"
        )

    @tracer.capture_method
    def send_message(
        self,
        message_body: Dict[str, Any],
        message_attributes: Optional[Dict[str, Dict[str, str]]] = None,
        delay_seconds: int = 0,
    ) -> Dict[str, Any]:
        """Send message to SQS queue"""

        if not self.queue_url:
            logger.warning("SQS queue URL not configured")
            return {"success": False, "error": "SQS queue not configured"}

        try:
            params = {
                "QueueUrl": self.queue_url,
                "MessageBody": json.dumps(message_body),
                "DelaySeconds": delay_seconds,
            }

            if message_attributes:
                params["MessageAttributes"] = message_attributes

            response = self.sqs_client.send_message(**params)

            return {
                "success": True,
                "message_id": response["MessageId"],
                "md5": response["MD5OfBody"],
            }

        except Exception as e:
            logger.error(f"SQS send message error: {e}")
            return {"success": False, "error": str(e)}


# Global service manager instances
_s3_manager: Optional[S3ServiceManager] = None
_dynamodb_manager: Optional[DynamoDBServiceManager] = None
_bedrock_manager: Optional[BedrockServiceManager] = None
_sqs_manager: Optional[SQSServiceManager] = None


def get_s3_manager() -> S3ServiceManager:
    """Get global S3 service manager"""
    global _s3_manager
    if _s3_manager is None:
        _s3_manager = S3ServiceManager()
    return _s3_manager


def get_dynamodb_manager() -> DynamoDBServiceManager:
    """Get global DynamoDB service manager"""
    global _dynamodb_manager
    if _dynamodb_manager is None:
        _dynamodb_manager = DynamoDBServiceManager()
    return _dynamodb_manager


def get_bedrock_manager() -> BedrockServiceManager:
    """Get global Bedrock service manager"""
    global _bedrock_manager
    if _bedrock_manager is None:
        _bedrock_manager = BedrockServiceManager()
    return _bedrock_manager


def get_sqs_manager() -> SQSServiceManager:
    """Get global SQS service manager"""
    global _sqs_manager
    if _sqs_manager is None:
        _sqs_manager = SQSServiceManager()
    return _sqs_manager


# Convenience functions for common operations


def upload_to_s3(
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Convenience function for S3 upload"""
    return get_s3_manager().upload_object(key, data, content_type, metadata)


def download_from_s3(key: str) -> Dict[str, Any]:
    """Convenience function for S3 download"""
    return get_s3_manager().download_object(key)


def generate_s3_presigned_url(
    key: str, expiration: int = 3600, method: str = "GET"
) -> Dict[str, Any]:
    """Convenience function for S3 presigned URL generation"""
    return get_s3_manager().generate_presigned_url(key, expiration, method)


def save_to_dynamodb(
    table_name: str, item: Dict[str, Any], condition_expression: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function for DynamoDB put operation"""
    return get_dynamodb_manager().put_item(table_name, item, condition_expression)


def get_from_dynamodb(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for DynamoDB get operation"""
    return get_dynamodb_manager().get_item(table_name, key)


def invoke_claude_model(
    prompt: str, max_tokens: int = 4000, temperature: float = 0.7
) -> Dict[str, Any]:
    """Convenience function for Claude model invocation"""
    return get_bedrock_manager().invoke_claude_model(prompt, max_tokens, temperature)


def generate_image_with_nova(
    prompt: str, width: int = 1920, height: int = 1080
) -> Dict[str, Any]:
    """Convenience function for Nova Canvas image generation"""
    return get_bedrock_manager().invoke_nova_canvas(prompt, width, height)


def send_to_sqs(
    message: Dict[str, Any],
    attributes: Optional[Dict[str, Dict[str, str]]] = None,
    delay: int = 0,
) -> Dict[str, Any]:
    """Convenience function for SQS message sending"""
    return get_sqs_manager().send_message(message, attributes, delay)
