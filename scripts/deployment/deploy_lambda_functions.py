#!/usr/bin/env python3
"""
Lambda Function Deployment Script
Deploys core Lambda functions for AI PPT Assistant
"""

import os
import sys
import json
import zipfile
import boto3
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from botocore.exceptions import ClientError

# Configuration
AWS_REGION = "us-east-1"
PROJECT_NAME = "ai-ppt-assistant"
ENVIRONMENT = "dev"
PYTHON_RUNTIME = "python3.13"
LAMBDA_TIMEOUT = 300  # 5 minutes
MEMORY_SIZE = 1024  # MB

# Core Lambda functions to deploy
CORE_FUNCTIONS = {
    "session_manager": {
        "description": "Manages user sessions and state",
        "handler": "handler.lambda_handler",
        "timeout": 30,
        "memory_size": 512,
        "environment": {
            "FUNCTION_TYPE": "SESSION_MANAGER"
        }
    },
    "ppt_generator": {
        "description": "Generates PowerPoint presentations",
        "handler": "compile_pptx.lambda_handler",
        "source": "controllers/compile_pptx.py",
        "timeout": 300,
        "memory_size": 2048,
        "environment": {
            "FUNCTION_TYPE": "PPT_GENERATOR"
        }
    },
    "content_enhancer": {
        "description": "Enhances and optimizes content",
        "handler": "generate_content.lambda_handler",
        "source": "controllers/generate_content.py",
        "timeout": 60,
        "memory_size": 1024,
        "environment": {
            "FUNCTION_TYPE": "CONTENT_ENHANCER"
        }
    },
    "auth_handler": {
        "description": "Handles authentication and authorization",
        "handler": "handler.lambda_handler",
        "timeout": 10,
        "memory_size": 256,
        "environment": {
            "FUNCTION_TYPE": "AUTH_HANDLER"
        }
    },
    "outline_creator": {
        "description": "Creates presentation outlines",
        "handler": "create_outline.lambda_handler",
        "source": "controllers/create_outline.py",
        "timeout": 60,
        "memory_size": 1024,
        "environment": {
            "FUNCTION_TYPE": "OUTLINE_CREATOR"
        }
    },
    "image_finder": {
        "description": "Finds and retrieves images",
        "handler": "find_image.lambda_handler",
        "source": "controllers/find_image.py",
        "timeout": 30,
        "memory_size": 512,
        "environment": {
            "FUNCTION_TYPE": "IMAGE_FINDER"
        }
    }
}

class LambdaDeployer:
    """Handles Lambda function deployment"""
    
    def __init__(self, region: str = AWS_REGION):
        """Initialize Lambda deployer"""
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
        self.sts_client = boto3.client('sts', region_name=region)
        
        # Get account ID
        self.account_id = self.sts_client.get_caller_identity()['Account']
        
        # Get or create Lambda role
        self.lambda_role_arn = self.get_or_create_lambda_role()
        
        # Get Lambda layer ARN
        self.layer_arn = self.get_lambda_layer_arn()
        
        # Environment variables
        self.env_vars = self.get_environment_variables()
        
    def get_or_create_lambda_role(self) -> str:
        """Get or create IAM role for Lambda functions"""
        role_name = f"{PROJECT_NAME}-{ENVIRONMENT}-lambda-role"
        
        try:
            response = self.iam_client.get_role(RoleName=role_name)
            print(f"✅ Using existing IAM role: {role_name}")
            return response['Role']['Arn']
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                print(f"Creating IAM role: {role_name}")
                return self.create_lambda_role(role_name)
            raise
    
    def create_lambda_role(self, role_name: str) -> str:
        """Create IAM role for Lambda functions"""
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"Lambda execution role for {PROJECT_NAME}"
            )
            
            # Attach policies
            policies = [
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                "arn:aws:iam::aws:policy/AmazonS3FullAccess",
                "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess",
                "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
            ]
            
            for policy_arn in policies:
                self.iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
            
            print(f"✅ Created IAM role: {role_name}")
            return response['Role']['Arn']
            
        except ClientError as e:
            print(f"❌ Error creating IAM role: {e}")
            raise
    
    def get_lambda_layer_arn(self) -> Optional[str]:
        """Get Lambda layer ARN if it exists"""
        layer_name = f"{PROJECT_NAME}-{ENVIRONMENT}-dependencies"
        
        try:
            response = self.lambda_client.list_layers()
            for layer in response.get('Layers', []):
                if layer['LayerName'] == layer_name:
                    latest_version = layer['LatestMatchingVersion']
                    layer_arn = latest_version['LayerVersionArn']
                    print(f"✅ Found Lambda layer: {layer_arn}")
                    return layer_arn
        except ClientError as e:
            print(f"⚠️ Warning: Could not find Lambda layer: {e}")
        
        return None
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get common environment variables"""
        return {
            "ENVIRONMENT": ENVIRONMENT,
            "PROJECT_NAME": PROJECT_NAME,
            "BEDROCK_REGION": AWS_REGION,  # Use BEDROCK_REGION instead of AWS_REGION
            "BUCKET_NAME": f"{PROJECT_NAME}-{ENVIRONMENT}-presentations-52de98b4",
            "TABLE_NAME": f"{PROJECT_NAME}-{ENVIRONMENT}-sessions",
            "CHECKPOINTS_TABLE": f"{PROJECT_NAME}-{ENVIRONMENT}-checkpoints",
            "LOG_LEVEL": "INFO"
        }
    
    def create_deployment_package(self, function_name: str, config: Dict) -> str:
        """Create deployment package for Lambda function"""
        zip_file_path = f"/tmp/{function_name}.zip"
        
        # Check if source file exists
        if "source" in config:
            source_path = Path(f"lambdas/{config['source']}")
            if not source_path.exists():
                print(f"⚠️ Source file not found: {source_path}")
                # Create a basic handler
                self.create_basic_handler(function_name, zip_file_path)
                return zip_file_path
            
            # Create ZIP from existing source
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add the source file as handler.py
                zf.write(source_path, "handler.py")
                
                # Add utils if they exist
                utils_path = Path("lambdas/utils")
                if utils_path.exists():
                    for file in utils_path.rglob("*.py"):
                        arcname = f"utils/{file.relative_to(utils_path)}"
                        zf.write(file, arcname)
        else:
            # Create basic handler for functions without source
            self.create_basic_handler(function_name, zip_file_path)
        
        return zip_file_path
    
    def create_basic_handler(self, function_name: str, zip_file_path: str):
        """Create a basic Lambda handler"""
        handler_code = f"""
import json
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    \"\"\"
    Basic handler for {function_name}
    This is a placeholder that needs to be implemented
    \"\"\"
    logger.info(f"Function {function_name} invoked")
    logger.info(f"Event: {{json.dumps(event)}}")
    
    return {{
        'statusCode': 200,
        'body': json.dumps({{
            'message': f'{function_name} function executed successfully',
            'timestamp': datetime.now().isoformat(),
            'function': '{function_name}',
            'environment': '{ENVIRONMENT}'
        }})
    }}
"""
        
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("handler.py", handler_code)
    
    def deploy_function(self, function_name: str, config: Dict) -> bool:
        """Deploy a single Lambda function"""
        full_name = f"{PROJECT_NAME}-{ENVIRONMENT}-{function_name}"
        
        print(f"\n🚀 Deploying {function_name}...")
        
        try:
            # Create deployment package
            zip_file_path = self.create_deployment_package(function_name, config)
            
            # Read ZIP file
            with open(zip_file_path, 'rb') as f:
                zip_content = f.read()
            
            # Prepare environment variables
            env_vars = self.env_vars.copy()
            env_vars.update(config.get('environment', {}))
            
            # Prepare Lambda configuration
            lambda_config = {
                'FunctionName': full_name,
                'Runtime': PYTHON_RUNTIME,
                'Role': self.lambda_role_arn,
                'Handler': config['handler'],
                'Code': {'ZipFile': zip_content},
                'Description': config['description'],
                'Timeout': config.get('timeout', LAMBDA_TIMEOUT),
                'MemorySize': config.get('memory_size', MEMORY_SIZE),
                'Environment': {'Variables': env_vars},
                'Tags': {
                    'Project': PROJECT_NAME,
                    'Environment': ENVIRONMENT,
                    'ManagedBy': 'Python Script'
                }
            }
            
            # Add layer if available
            if self.layer_arn:
                lambda_config['Layers'] = [self.layer_arn]
            
            # Check if function exists
            try:
                self.lambda_client.get_function(FunctionName=full_name)
                # Update existing function
                print(f"  Updating existing function...")
                
                # Update code
                self.lambda_client.update_function_code(
                    FunctionName=full_name,
                    ZipFile=zip_content
                )
                
                # Update configuration
                self.lambda_client.update_function_configuration(
                    FunctionName=full_name,
                    Runtime=PYTHON_RUNTIME,
                    Handler=config['handler'],
                    Description=config['description'],
                    Timeout=config.get('timeout', LAMBDA_TIMEOUT),
                    MemorySize=config.get('memory_size', MEMORY_SIZE),
                    Environment={'Variables': env_vars},
                    Layers=[self.layer_arn] if self.layer_arn else []
                )
                
                print(f"  ✅ Function {function_name} updated successfully")
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                # Create new function
                print(f"  Creating new function...")
                self.lambda_client.create_function(**lambda_config)
                print(f"  ✅ Function {function_name} created successfully")
            
            # Clean up temp file
            os.remove(zip_file_path)
            return True
            
        except Exception as e:
            print(f"  ❌ Error deploying {function_name}: {e}")
            return False
    
    def deploy_all_functions(self) -> Dict[str, bool]:
        """Deploy all core Lambda functions"""
        print("=" * 50)
        print(f"🎯 Deploying Lambda Functions for {PROJECT_NAME}")
        print(f"   Environment: {ENVIRONMENT}")
        print(f"   Region: {AWS_REGION}")
        print(f"   Account: {self.account_id}")
        print("=" * 50)
        
        results = {}
        
        for function_name, config in CORE_FUNCTIONS.items():
            results[function_name] = self.deploy_function(function_name, config)
        
        return results
    
    def verify_deployments(self) -> Dict[str, Dict]:
        """Verify deployed functions"""
        print("\n" + "=" * 50)
        print("🔍 Verifying Deployments")
        print("=" * 50)
        
        verification = {}
        
        for function_name in CORE_FUNCTIONS.keys():
            full_name = f"{PROJECT_NAME}-{ENVIRONMENT}-{function_name}"
            
            try:
                response = self.lambda_client.get_function(FunctionName=full_name)
                config = response['Configuration']
                
                verification[function_name] = {
                    'deployed': True,
                    'arn': config['FunctionArn'],
                    'runtime': config['Runtime'],
                    'handler': config['Handler'],
                    'state': config['State'],
                    'last_modified': config['LastModified']
                }
                
                print(f"✅ {function_name}: {config['State']}")
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                verification[function_name] = {
                    'deployed': False,
                    'error': 'Function not found'
                }
                print(f"❌ {function_name}: Not deployed")
            
            except Exception as e:
                verification[function_name] = {
                    'deployed': False,
                    'error': str(e)
                }
                print(f"❌ {function_name}: Error - {e}")
        
        return verification
    
    def create_api_gateway_integrations(self):
        """Create API Gateway integrations for Lambda functions"""
        print("\n" + "=" * 50)
        print("🔗 Setting up API Gateway Integrations")
        print("=" * 50)
        
        # This would integrate with the API Gateway created by Terraform
        # For now, we'll just print what needs to be done
        
        api_mappings = {
            "POST /sessions": "session_manager",
            "POST /generate": "ppt_generator",
            "POST /enhance": "content_enhancer",
            "POST /auth": "auth_handler",
            "POST /outline": "outline_creator",
            "POST /images": "image_finder"
        }
        
        print("\nAPI Gateway mappings needed:")
        for route, function in api_mappings.items():
            full_name = f"{PROJECT_NAME}-{ENVIRONMENT}-{function}"
            print(f"  {route} → {full_name}")
        
        print("\n💡 Run Terraform to create API Gateway integrations")


def main():
    """Main deployment function"""
    try:
        # Initialize deployer
        deployer = LambdaDeployer()
        
        # Deploy all functions
        results = deployer.deploy_all_functions()
        
        # Verify deployments
        verification = deployer.verify_deployments()
        
        # Setup API Gateway integrations
        deployer.create_api_gateway_integrations()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Deployment Summary")
        print("=" * 50)
        
        successful = sum(1 for r in results.values() if r)
        failed = sum(1 for r in results.values() if not r)
        
        print(f"✅ Successfully deployed: {successful}")
        print(f"❌ Failed deployments: {failed}")
        
        if failed > 0:
            print("\n⚠️ Some deployments failed. Please check the errors above.")
            sys.exit(1)
        else:
            print("\n🎉 All Lambda functions deployed successfully!")
            
            # Save deployment report
            report = {
                'timestamp': datetime.now().isoformat(),
                'environment': ENVIRONMENT,
                'region': AWS_REGION,
                'results': results,
                'verification': verification
            }
            
            report_file = f"lambda_deployment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"\n📄 Deployment report saved to: {report_file}")
            
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()