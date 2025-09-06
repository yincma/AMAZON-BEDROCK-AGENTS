#!/usr/bin/env python3
"""
API Gateway Configuration Script
Configures routes and Lambda integrations for AI PPT Assistant
"""

import boto3
import json
from typing import Dict, List
from datetime import datetime

# Configuration
AWS_REGION = "us-east-1"
PROJECT_NAME = "ai-ppt-assistant"
ENVIRONMENT = "dev"
API_ID = "byih5fsutb"  # From our verification

# Route mappings
ROUTES = {
    "sessions": {
        "path": "/sessions",
        "method": "POST",
        "lambda_function": "session_manager",
        "description": "Manage user sessions"
    },
    "generate": {
        "path": "/generate",
        "method": "POST",
        "lambda_function": "ppt_generator",
        "description": "Generate PowerPoint presentations"
    },
    "enhance": {
        "path": "/enhance",
        "method": "POST",
        "lambda_function": "content_enhancer",
        "description": "Enhance presentation content"
    },
    "auth": {
        "path": "/auth",
        "method": "POST",
        "lambda_function": "auth_handler",
        "description": "Handle authentication"
    },
    "outline": {
        "path": "/outline",
        "method": "POST",
        "lambda_function": "outline_creator",
        "description": "Create presentation outline"
    },
    "images": {
        "path": "/images",
        "method": "POST",
        "lambda_function": "image_finder",
        "description": "Find and retrieve images"
    }
}

class APIGatewayConfigurator:
    """Configures API Gateway with Lambda integrations"""
    
    def __init__(self, region: str = AWS_REGION):
        """Initialize AWS clients"""
        self.api_client = boto3.client('apigateway', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get account ID
        self.account_id = self.sts_client.get_caller_identity()['Account']
        self.region = region
        self.api_id = API_ID
        
    def get_root_resource_id(self) -> str:
        """Get the root resource ID of the API"""
        response = self.api_client.get_resources(restApiId=self.api_id)
        for item in response['items']:
            if item['path'] == '/':
                return item['id']
        raise Exception("Root resource not found")
    
    def create_resource(self, parent_id: str, path_part: str) -> str:
        """Create or get a resource"""
        # Check if resource already exists
        response = self.api_client.get_resources(restApiId=self.api_id)
        for item in response['items']:
            if item.get('pathPart') == path_part:
                print(f"  Resource {path_part} already exists")
                return item['id']
        
        # Create new resource
        response = self.api_client.create_resource(
            restApiId=self.api_id,
            parentId=parent_id,
            pathPart=path_part
        )
        print(f"  Created resource: {path_part}")
        return response['id']
    
    def create_method(self, resource_id: str, http_method: str):
        """Create a method for a resource"""
        try:
            self.api_client.put_method(
                restApiId=self.api_id,
                resourceId=resource_id,
                httpMethod=http_method,
                authorizationType='NONE',
                requestParameters={
                    'method.request.header.Content-Type': False
                }
            )
            print(f"    Created method: {http_method}")
        except self.api_client.exceptions.ConflictException:
            print(f"    Method {http_method} already exists")
    
    def create_lambda_integration(self, resource_id: str, http_method: str, lambda_name: str):
        """Create Lambda integration for a method"""
        lambda_arn = f"arn:aws:lambda:{self.region}:{self.account_id}:function:{PROJECT_NAME}-{ENVIRONMENT}-{lambda_name}"
        
        try:
            self.api_client.put_integration(
                restApiId=self.api_id,
                resourceId=resource_id,
                httpMethod=http_method,
                type='AWS_PROXY',
                integrationHttpMethod='POST',
                uri=f"arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
            )
            print(f"    Created Lambda integration: {lambda_name}")
        except self.api_client.exceptions.ConflictException:
            print(f"    Integration already exists for {lambda_name}")
    
    def add_lambda_permission(self, lambda_name: str):
        """Add API Gateway permission to invoke Lambda"""
        function_name = f"{PROJECT_NAME}-{ENVIRONMENT}-{lambda_name}"
        statement_id = f"apigateway-{self.api_id}-{lambda_name}"
        
        try:
            self.lambda_client.add_permission(
                FunctionName=function_name,
                StatementId=statement_id,
                Action='lambda:InvokeFunction',
                Principal='apigateway.amazonaws.com',
                SourceArn=f"arn:aws:execute-api:{self.region}:{self.account_id}:{self.api_id}/*/*"
            )
            print(f"    Added Lambda permission for {lambda_name}")
        except self.lambda_client.exceptions.ResourceConflictException:
            print(f"    Permission already exists for {lambda_name}")
    
    def create_method_response(self, resource_id: str, http_method: str):
        """Create method response"""
        try:
            self.api_client.put_method_response(
                restApiId=self.api_id,
                resourceId=resource_id,
                httpMethod=http_method,
                statusCode='200',
                responseModels={
                    'application/json': 'Empty'
                },
                responseParameters={
                    'method.response.header.Access-Control-Allow-Origin': False
                }
            )
            print(f"    Created method response")
        except self.api_client.exceptions.ConflictException:
            print(f"    Method response already exists")
    
    def create_integration_response(self, resource_id: str, http_method: str):
        """Create integration response"""
        try:
            self.api_client.put_integration_response(
                restApiId=self.api_id,
                resourceId=resource_id,
                httpMethod=http_method,
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Origin': "'*'"
                }
            )
            print(f"    Created integration response")
        except self.api_client.exceptions.ConflictException:
            print(f"    Integration response already exists")
    
    def configure_cors(self, resource_id: str):
        """Configure CORS for a resource"""
        try:
            self.api_client.put_method(
                restApiId=self.api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                authorizationType='NONE'
            )
            
            self.api_client.put_integration(
                restApiId=self.api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                type='MOCK',
                requestTemplates={
                    'application/json': '{"statusCode": 200}'
                }
            )
            
            self.api_client.put_method_response(
                restApiId=self.api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': False,
                    'method.response.header.Access-Control-Allow-Methods': False,
                    'method.response.header.Access-Control-Allow-Origin': False
                }
            )
            
            self.api_client.put_integration_response(
                restApiId=self.api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
                    'method.response.header.Access-Control-Allow-Origin': "'*'"
                }
            )
            print(f"    Configured CORS")
        except self.api_client.exceptions.ConflictException:
            print(f"    CORS already configured")
    
    def deploy_api(self):
        """Deploy the API to a stage"""
        stage_name = ENVIRONMENT
        
        try:
            self.api_client.create_deployment(
                restApiId=self.api_id,
                stageName=stage_name,
                description=f"Deployment at {datetime.now().isoformat()}"
            )
            print(f"\nDeployed API to stage: {stage_name}")
            print(f"API URL: https://{self.api_id}.execute-api.{self.region}.amazonaws.com/{stage_name}")
        except Exception as e:
            print(f"Error deploying API: {e}")
    
    def configure_all_routes(self):
        """Configure all routes and integrations"""
        print("=" * 50)
        print("Configuring API Gateway Routes")
        print("=" * 50)
        
        root_id = self.get_root_resource_id()
        print(f"Root resource ID: {root_id}\n")
        
        for route_name, config in ROUTES.items():
            print(f"Configuring route: {config['path']}")
            
            # Create resource
            path_part = config['path'].lstrip('/')
            resource_id = self.create_resource(root_id, path_part)
            
            # Create method
            self.create_method(resource_id, config['method'])
            
            # Create Lambda integration
            self.create_lambda_integration(resource_id, config['method'], config['lambda_function'])
            
            # Add Lambda permission
            self.add_lambda_permission(config['lambda_function'])
            
            # Create method response
            self.create_method_response(resource_id, config['method'])
            
            # Create integration response
            self.create_integration_response(resource_id, config['method'])
            
            # Configure CORS
            self.configure_cors(resource_id)
            
            print(f"  Route configured successfully\n")
        
        # Deploy the API
        self.deploy_api()
        
        print("\n" + "=" * 50)
        print("API Gateway Configuration Complete")
        print("=" * 50)
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate configuration summary"""
        print("\nConfiguration Summary:")
        print("-" * 30)
        for route_name, config in ROUTES.items():
            lambda_func = f"{PROJECT_NAME}-{ENVIRONMENT}-{config['lambda_function']}"
            print(f"{config['method']} {config['path']} → {lambda_func}")
        
        print(f"\nAPI Endpoint: https://{self.api_id}.execute-api.{self.region}.amazonaws.com/{ENVIRONMENT}")
        
        # Save summary to file
        summary = {
            'timestamp': datetime.now().isoformat(),
            'api_id': self.api_id,
            'region': self.region,
            'stage': ENVIRONMENT,
            'routes': ROUTES,
            'endpoint': f"https://{self.api_id}.execute-api.{self.region}.amazonaws.com/{ENVIRONMENT}"
        }
        
        with open('api_gateway_configuration.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("\nConfiguration saved to: api_gateway_configuration.json")


def main():
    """Main execution function"""
    try:
        configurator = APIGatewayConfigurator()
        configurator.configure_all_routes()
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())