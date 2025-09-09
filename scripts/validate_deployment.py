#!/usr/bin/env python3
"""
AI PPT Assistant Deployment Validation Script
Validates that all infrastructure components are correctly deployed and functional
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Tuple

import boto3
import requests
from botocore.exceptions import ClientError

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Configuration
PROJECT_NAME = os.environ.get("PROJECT_NAME", "ai-ppt-assistant")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
API_BASE_URL = os.environ.get("API_BASE_URL", "")

# AWS Clients
session = boto3.Session(region_name=AWS_REGION)
lambda_client = session.client('lambda')
dynamodb_client = session.client('dynamodb')
sqs_client = session.client('sqs')
s3_client = session.client('s3')
logs_client = session.client('logs')
bedrock_agent_client = session.client('bedrock-agent')
api_gateway_client = session.client('apigateway')
cloudwatch_client = session.client('cloudwatch')


class DeploymentValidator:
    def __init__(self):
        self.results = []
        self.critical_failures = []
        self.warnings = []
        self.passed_tests = 0
        self.failed_tests = 0
        
    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{title:^60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    def print_result(self, test_name: str, passed: bool, message: str = ""):
        """Print test result"""
        if passed:
            status = f"{Colors.GREEN}✓ PASS{Colors.END}"
            self.passed_tests += 1
        else:
            status = f"{Colors.RED}✗ FAIL{Colors.END}"
            self.failed_tests += 1
            
        print(f"{status} {test_name}")
        if message:
            print(f"  └─ {message}")
    
    def validate_lambda_functions(self) -> bool:
        """Validate Lambda functions are deployed and configured correctly"""
        self.print_header("Lambda Functions Validation")
        
        all_passed = True
        required_functions = [
            f"{PROJECT_NAME}-api-generate-presentation",
            f"{PROJECT_NAME}-api-presentation-status",
            f"{PROJECT_NAME}-api-presentation-download",
            f"{PROJECT_NAME}-api-modify-slide",
            f"{PROJECT_NAME}-create-outline",
            f"{PROJECT_NAME}-generate-content",
            f"{PROJECT_NAME}-generate-image",
            f"{PROJECT_NAME}-find-image",
            f"{PROJECT_NAME}-generate-speaker-notes",
            f"{PROJECT_NAME}-compile-pptx",
            f"{PROJECT_NAME}-task-processor",  # New task processor
        ]
        
        for function_name in required_functions:
            try:
                response = lambda_client.get_function(FunctionName=function_name)
                config = response['Configuration']
                
                # Check function state
                if config['State'] == 'Active':
                    self.print_result(f"Lambda: {function_name}", True, 
                                    f"Runtime: {config['Runtime']}, Memory: {config['MemorySize']}MB")
                else:
                    self.print_result(f"Lambda: {function_name}", False, 
                                    f"Function state: {config['State']}")
                    all_passed = False
                
                # Validate environment variables
                env_vars = config.get('Environment', {}).get('Variables', {})
                
                # Check critical environment variables
                if 'generate-presentation' in function_name:
                    required_env = ['DYNAMODB_TASKS_TABLE', 'SQS_QUEUE_URL', 
                                  'ORCHESTRATOR_AGENT_ID', 'ORCHESTRATOR_ALIAS_ID']
                    for env in required_env:
                        if env not in env_vars:
                            self.warnings.append(f"{function_name} missing env var: {env}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    self.print_result(f"Lambda: {function_name}", False, "Function not found")
                    self.critical_failures.append(f"Lambda function {function_name} not deployed")
                    all_passed = False
                else:
                    self.print_result(f"Lambda: {function_name}", False, str(e))
                    all_passed = False
        
        return all_passed
    
    def validate_sqs_configuration(self) -> bool:
        """Validate SQS queues and event source mappings"""
        self.print_header("SQS Queue Validation")
        
        all_passed = True
        
        # Check main task queue
        queue_name = f"{PROJECT_NAME}-{ENVIRONMENT}-tasks"
        try:
            queue_url = sqs_client.get_queue_url(QueueName=queue_name)['QueueUrl']
            
            # Get queue attributes
            attrs = sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['All']
            )['Attributes']
            
            self.print_result(f"SQS Queue: {queue_name}", True,
                            f"Messages: {attrs.get('ApproximateNumberOfMessages', 0)}, "
                            f"In-flight: {attrs.get('ApproximateNumberOfMessagesNotVisible', 0)}")
            
            # Check for dead letter queue
            if 'RedrivePolicy' in attrs:
                self.print_result("Dead Letter Queue configured", True)
            else:
                self.print_result("Dead Letter Queue configured", False, "No DLQ configured")
                self.warnings.append("SQS queue has no dead letter queue")
            
            # Check Lambda event source mapping
            try:
                mappings = lambda_client.list_event_source_mappings(
                    EventSourceArn=f"arn:aws:sqs:{AWS_REGION}:*:{queue_name}"
                )
                
                if mappings['EventSourceMappings']:
                    mapping = mappings['EventSourceMappings'][0]
                    if mapping['State'] == 'Enabled':
                        self.print_result("SQS-Lambda Trigger", True,
                                        f"Function: {mapping['FunctionArn'].split(':')[-1]}")
                    else:
                        self.print_result("SQS-Lambda Trigger", False,
                                        f"Trigger state: {mapping['State']}")
                        self.critical_failures.append("SQS-Lambda trigger is not enabled")
                        all_passed = False
                else:
                    self.print_result("SQS-Lambda Trigger", False, "No Lambda trigger configured")
                    self.critical_failures.append("No Lambda function processing SQS messages")
                    all_passed = False
                    
            except Exception as e:
                self.print_result("SQS-Lambda Trigger", False, str(e))
                all_passed = False
                
        except ClientError as e:
            self.print_result(f"SQS Queue: {queue_name}", False, str(e))
            self.critical_failures.append(f"SQS queue {queue_name} not found")
            all_passed = False
        
        return all_passed
    
    def validate_dynamodb_tables(self) -> bool:
        """Validate DynamoDB tables"""
        self.print_header("DynamoDB Tables Validation")
        
        all_passed = True
        required_tables = [
            f"{PROJECT_NAME}-{ENVIRONMENT}-sessions",
            f"{PROJECT_NAME}-{ENVIRONMENT}-tasks",
            f"{PROJECT_NAME}-{ENVIRONMENT}-checkpoints",
        ]
        
        for table_name in required_tables:
            try:
                response = dynamodb_client.describe_table(TableName=table_name)
                table = response['Table']
                
                if table['TableStatus'] == 'ACTIVE':
                    self.print_result(f"DynamoDB: {table_name}", True,
                                    f"Items: {table['ItemCount']}, "
                                    f"Size: {table['TableSizeBytes']} bytes")
                else:
                    self.print_result(f"DynamoDB: {table_name}", False,
                                    f"Table status: {table['TableStatus']}")
                    all_passed = False
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    self.print_result(f"DynamoDB: {table_name}", False, "Table not found")
                    self.critical_failures.append(f"DynamoDB table {table_name} not found")
                    all_passed = False
                else:
                    self.print_result(f"DynamoDB: {table_name}", False, str(e))
                    all_passed = False
        
        return all_passed
    
    def validate_bedrock_agents(self) -> bool:
        """Validate Bedrock Agent configuration"""
        self.print_header("Bedrock Agent Validation")
        
        all_passed = True
        
        # Get agent IDs from environment or configuration
        agent_configs = [
            ("Orchestrator Agent", os.environ.get("ORCHESTRATOR_AGENT_ID", "LA1D127LSK")),
        ]
        
        for agent_name, agent_id in agent_configs:
            if agent_id and not agent_id.startswith("placeholder"):
                try:
                    response = bedrock_agent_client.get_agent(agentId=agent_id)
                    agent = response['agent']
                    
                    if agent['agentStatus'] == 'PREPARED':
                        self.print_result(f"Bedrock: {agent_name}", True,
                                        f"ID: {agent_id}, Model: {agent.get('foundationModel', 'N/A')}")
                    else:
                        self.print_result(f"Bedrock: {agent_name}", False,
                                        f"Agent status: {agent['agentStatus']}")
                        all_passed = False
                        
                except ClientError as e:
                    self.print_result(f"Bedrock: {agent_name}", False, str(e))
                    self.warnings.append(f"Bedrock agent {agent_id} not accessible")
            else:
                self.print_result(f"Bedrock: {agent_name}", False, "Not configured")
                self.warnings.append(f"{agent_name} not configured")
        
        return all_passed
    
    def validate_api_gateway(self) -> bool:
        """Validate API Gateway configuration"""
        self.print_header("API Gateway Validation")
        
        all_passed = True
        
        try:
            # Get API by name
            apis = api_gateway_client.get_rest_apis()['items']
            target_api = None
            
            for api in apis:
                if PROJECT_NAME in api['name']:
                    target_api = api
                    break
            
            if target_api:
                self.print_result(f"API Gateway: {target_api['name']}", True,
                                f"ID: {target_api['id']}")
                
                # Check resources
                resources = api_gateway_client.get_resources(restApiId=target_api['id'])
                resource_count = len(resources['items'])
                
                self.print_result("API Resources", True,
                                f"Total resources: {resource_count}")
                
                # Check for deployments
                deployments = api_gateway_client.get_deployments(restApiId=target_api['id'])
                if deployments['items']:
                    self.print_result("API Deployment", True,
                                    f"Deployments: {len(deployments['items'])}")
                else:
                    self.print_result("API Deployment", False, "No deployments found")
                    self.warnings.append("API Gateway has no deployments")
                    
            else:
                self.print_result("API Gateway", False, "API not found")
                self.critical_failures.append("API Gateway not found")
                all_passed = False
                
        except Exception as e:
            self.print_result("API Gateway", False, str(e))
            all_passed = False
        
        return all_passed
    
    def validate_monitoring(self) -> bool:
        """Validate CloudWatch alarms and monitoring"""
        self.print_header("Monitoring & Alarms Validation")
        
        all_passed = True
        
        try:
            # List all alarms for the project
            alarms = cloudwatch_client.describe_alarms(
                AlarmNamePrefix=PROJECT_NAME
            )['MetricAlarms']
            
            if alarms:
                ok_count = sum(1 for a in alarms if a['StateValue'] == 'OK')
                alarm_count = sum(1 for a in alarms if a['StateValue'] == 'ALARM')
                insufficient_count = sum(1 for a in alarms if a['StateValue'] == 'INSUFFICIENT_DATA')
                
                self.print_result("CloudWatch Alarms", True,
                                f"Total: {len(alarms)}, OK: {ok_count}, "
                                f"ALARM: {alarm_count}, INSUFFICIENT: {insufficient_count}")
                
                if alarm_count > 0:
                    self.warnings.append(f"{alarm_count} alarms in ALARM state")
                    
            else:
                self.print_result("CloudWatch Alarms", False, "No alarms configured")
                self.warnings.append("No CloudWatch alarms configured")
                
        except Exception as e:
            self.print_result("CloudWatch Alarms", False, str(e))
            all_passed = False
        
        return all_passed
    
    def run_integration_test(self) -> bool:
        """Run a simple integration test"""
        self.print_header("Integration Test")
        
        test_passed = True
        test_id = str(uuid.uuid4())[:8]
        
        try:
            # Create a test task by invoking Lambda directly
            test_payload = {
                "httpMethod": "POST",
                "path": "/presentations",
                "body": json.dumps({
                    "title": f"Validation Test {test_id}",
                    "topic": "System validation test",
                    "slide_count": 3,
                    "language": "en",
                    "style": "professional"
                }),
                "pathParameters": {},
                "queryStringParameters": {}
            }
            
            # Invoke generate_presentation Lambda
            response = lambda_client.invoke(
                FunctionName=f"{PROJECT_NAME}-api-generate-presentation",
                InvocationType='RequestResponse',
                Payload=json.dumps(test_payload)
            )
            
            result = json.loads(response['Payload'].read())
            
            if result.get('statusCode') == 202:
                body = json.loads(result.get('body', '{}'))
                task_id = body.get('task_id')
                
                if task_id:
                    self.print_result("Task Creation", True, f"Task ID: {task_id}")
                    
                    # Wait a moment for processing
                    time.sleep(2)
                    
                    # Check if task was stored in DynamoDB
                    try:
                        table_name = f"{PROJECT_NAME}-{ENVIRONMENT}-tasks"
                        db_response = dynamodb_client.get_item(
                            TableName=table_name,
                            Key={'task_id': {'S': task_id}}
                        )
                        
                        if 'Item' in db_response:
                            self.print_result("Task Storage", True, "Task found in DynamoDB")
                        else:
                            self.print_result("Task Storage", False, "Task not found in DynamoDB")
                            self.critical_failures.append("Tasks not being stored in DynamoDB")
                            test_passed = False
                            
                    except Exception as e:
                        self.print_result("Task Storage", False, str(e))
                        test_passed = False
                    
                    # Check SQS for message
                    try:
                        queue_url = sqs_client.get_queue_url(
                            QueueName=f"{PROJECT_NAME}-{ENVIRONMENT}-tasks"
                        )['QueueUrl']
                        
                        attrs = sqs_client.get_queue_attributes(
                            QueueUrl=queue_url,
                            AttributeNames=['ApproximateNumberOfMessages']
                        )['Attributes']
                        
                        msg_count = int(attrs.get('ApproximateNumberOfMessages', 0))
                        if msg_count > 0:
                            self.print_result("Task Queuing", True, 
                                            f"Messages in queue: {msg_count}")
                        else:
                            self.print_result("Task Queuing", False, 
                                            "No messages in queue (might be processed already)")
                            
                    except Exception as e:
                        self.print_result("Task Queuing", False, str(e))
                        
                else:
                    self.print_result("Task Creation", False, "No task_id returned")
                    test_passed = False
                    
            else:
                self.print_result("Task Creation", False, 
                                f"Status code: {result.get('statusCode')}")
                test_passed = False
                
        except Exception as e:
            self.print_result("Integration Test", False, str(e))
            test_passed = False
        
        return test_passed
    
    def generate_report(self):
        """Generate final validation report"""
        self.print_header("Validation Summary")
        
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"{Colors.BOLD}Test Results:{Colors.END}")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {Colors.GREEN}{self.passed_tests}{Colors.END}")
        print(f"  Failed: {Colors.RED}{self.failed_tests}{Colors.END}")
        print(f"  Pass Rate: {pass_rate:.1f}%")
        
        if self.critical_failures:
            print(f"\n{Colors.BOLD}{Colors.RED}Critical Failures:{Colors.END}")
            for failure in self.critical_failures:
                print(f"  • {failure}")
        
        if self.warnings:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}Warnings:{Colors.END}")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        # Overall status
        print(f"\n{Colors.BOLD}Overall Status:{Colors.END}")
        if self.critical_failures:
            print(f"  {Colors.RED}✗ DEPLOYMENT FAILED - Critical issues found{Colors.END}")
            return False
        elif self.warnings:
            print(f"  {Colors.YELLOW}⚠ DEPLOYMENT SUCCESSFUL WITH WARNINGS{Colors.END}")
            return True
        else:
            print(f"  {Colors.GREEN}✓ DEPLOYMENT SUCCESSFUL - All tests passed{Colors.END}")
            return True
    
    def run_all_validations(self) -> bool:
        """Run all validation tests"""
        print(f"\n{Colors.BOLD}AI PPT Assistant Deployment Validation{Colors.END}")
        print(f"Project: {PROJECT_NAME}")
        print(f"Environment: {ENVIRONMENT}")
        print(f"Region: {AWS_REGION}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        # Run all validations
        self.validate_lambda_functions()
        self.validate_sqs_configuration()
        self.validate_dynamodb_tables()
        self.validate_bedrock_agents()
        self.validate_api_gateway()
        self.validate_monitoring()
        self.run_integration_test()
        
        # Generate report
        return self.generate_report()


def main():
    """Main execution function"""
    validator = DeploymentValidator()
    success = validator.run_all_validations()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()