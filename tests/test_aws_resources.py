"""
Simple test script to verify AWS resources created by Terraform
"""

import boto3
import sys
from datetime import datetime


def test_s3_bucket():
    """Test S3 bucket existence and configuration"""
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'ai-ppt-assistant-dev-presentations-52de98b4'
    
    try:
        # Check if bucket exists
        response = s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ S3 Bucket '{bucket_name}' exists")
        
        # Check versioning
        versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
        if versioning.get('Status') == 'Enabled':
            print(f"✅ S3 Bucket versioning is enabled")
        else:
            print(f"⚠️  S3 Bucket versioning status: {versioning.get('Status')}")
        
        # Check encryption
        encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
        print(f"✅ S3 Bucket encryption is configured")
        
        return True
    except Exception as e:
        print(f"❌ S3 Bucket test failed: {e}")
        return False


def test_dynamodb_tables():
    """Test DynamoDB tables existence and configuration"""
    dynamodb_client = boto3.client('dynamodb', region_name='us-east-1')
    tables = ['ai-ppt-assistant-dev-sessions', 'ai-ppt-assistant-dev-checkpoints']
    
    results = []
    for table_name in tables:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            table = response['Table']
            
            print(f"✅ DynamoDB table '{table_name}' exists")
            print(f"   - Status: {table['TableStatus']}")
            print(f"   - Billing Mode: {table.get('BillingModeSummary', {}).get('BillingMode', 'N/A')}")
            
            # Check TTL
            ttl_response = dynamodb_client.describe_time_to_live(TableName=table_name)
            ttl_status = ttl_response['TimeToLiveDescription']['TimeToLiveStatus']
            print(f"   - TTL Status: {ttl_status}")
            
            results.append(True)
        except Exception as e:
            print(f"❌ DynamoDB table '{table_name}' test failed: {e}")
            results.append(False)
    
    return all(results)


def test_lambda_layer():
    """Test Lambda layer existence"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    layer_name = 'ai-ppt-assistant-dev-dependencies'
    
    try:
        response = lambda_client.list_layer_versions(LayerName=layer_name)
        if response['LayerVersions']:
            latest = response['LayerVersions'][0]
            print(f"✅ Lambda layer '{layer_name}' exists")
            print(f"   - Version: {latest['Version']}")
            print(f"   - Compatible Runtimes: {latest['CompatibleRuntimes']}")
            print(f"   - ARN: {latest['LayerVersionArn']}")
            return True
        else:
            print(f"⚠️  Lambda layer '{layer_name}' has no versions")
            return False
    except Exception as e:
        print(f"❌ Lambda layer test failed: {e}")
        return False


def test_sqs_queues():
    """Test SQS queues existence"""
    sqs_client = boto3.client('sqs', region_name='us-east-1')
    queue_names = ['ai-ppt-assistant-dev-tasks', 'ai-ppt-assistant-dev-tasks-dlq']
    
    results = []
    for queue_name in queue_names:
        try:
            response = sqs_client.get_queue_url(QueueName=queue_name)
            queue_url = response['QueueUrl']
            
            # Get queue attributes
            attrs = sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['All']
            )
            
            print(f"✅ SQS Queue '{queue_name}' exists")
            print(f"   - URL: {queue_url}")
            print(f"   - Message Retention: {attrs['Attributes'].get('MessageRetentionPeriod')} seconds")
            
            results.append(True)
        except Exception as e:
            print(f"❌ SQS Queue '{queue_name}' test failed: {e}")
            results.append(False)
    
    return all(results)


def test_iam_role():
    """Test IAM role existence"""
    iam_client = boto3.client('iam', region_name='us-east-1')
    role_name = 'ai-ppt-assistant-dev-lambda-role'
    
    try:
        response = iam_client.get_role(RoleName=role_name)
        role = response['Role']
        
        print(f"✅ IAM Role '{role_name}' exists")
        print(f"   - ARN: {role['Arn']}")
        print(f"   - Created: {role['CreateDate']}")
        
        # Check attached policies
        policies = iam_client.list_attached_role_policies(RoleName=role_name)
        print(f"   - Attached Policies: {len(policies['AttachedPolicies'])}")
        
        return True
    except Exception as e:
        print(f"❌ IAM Role test failed: {e}")
        return False


def test_api_gateway():
    """Test API Gateway existence"""
    api_client = boto3.client('apigateway', region_name='us-east-1')
    api_name = 'ai-ppt-assistant-dev-api'
    
    try:
        # List all REST APIs
        response = api_client.get_rest_apis()
        
        # Find our API
        our_api = None
        for api in response['items']:
            if api['name'] == api_name:
                our_api = api
                break
        
        if our_api:
            print(f"✅ API Gateway '{api_name}' exists")
            print(f"   - ID: {our_api['id']}")
            print(f"   - Created: {our_api.get('createdDate', 'N/A')}")
            
            # Check for methods (this is why deployment failed)
            resources = api_client.get_resources(restApiId=our_api['id'])
            method_count = 0
            for resource in resources['items']:
                if 'resourceMethods' in resource:
                    method_count += len(resource['resourceMethods'])
            
            if method_count == 0:
                print(f"   ⚠️  No methods configured (this is why deployment failed)")
            else:
                print(f"   - Methods: {method_count}")
            
            return True
        else:
            print(f"❌ API Gateway '{api_name}' not found")
            return False
    except Exception as e:
        print(f"❌ API Gateway test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🔍 AWS Resources Verification Test")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    tests = [
        ("S3 Bucket", test_s3_bucket),
        ("DynamoDB Tables", test_dynamodb_tables),
        ("Lambda Layer", test_lambda_layer),
        ("SQS Queues", test_sqs_queues),
        ("IAM Role", test_iam_role),
        ("API Gateway", test_api_gateway),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        print("-" * 40)
        result = test_func()
        results.append(result)
        print()
    
    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All AWS resources verified successfully!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())