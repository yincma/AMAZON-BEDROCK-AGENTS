#!/bin/bash

# Safe Destroy Script for AI PPT Assistant
# This script ensures clean destruction of all AWS resources

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_NAME="ai-ppt-assistant"
ENVIRONMENT="dev"
AWS_REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Safe Destroy Script for AI PPT Assistant${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to print status
print_status() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Function to print error
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to print success
print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Step 1: Clean S3 Buckets
print_status "Step 1: Cleaning S3 buckets..."

BUCKET_NAME="${PROJECT_NAME}-${ENVIRONMENT}-presentations-${ACCOUNT_ID}"

if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    print_status "Found bucket: $BUCKET_NAME"
    
    # Delete all object versions
    print_status "Deleting all object versions..."
    aws s3api list-object-versions --bucket "$BUCKET_NAME" --output json | \
    jq -r '.Versions[]? | "--key \"\(.Key)\" --version-id \(.VersionId)"' | \
    while read -r line; do
        if [ ! -z "$line" ]; then
            eval "aws s3api delete-object --bucket \"$BUCKET_NAME\" $line" 2>/dev/null || true
        fi
    done
    
    # Delete all delete markers
    print_status "Deleting all delete markers..."
    aws s3api list-object-versions --bucket "$BUCKET_NAME" --output json | \
    jq -r '.DeleteMarkers[]? | "--key \"\(.Key)\" --version-id \(.VersionId)"' | \
    while read -r line; do
        if [ ! -z "$line" ]; then
            eval "aws s3api delete-object --bucket \"$BUCKET_NAME\" $line" 2>/dev/null || true
        fi
    done
    
    # Delete all current objects
    print_status "Deleting all current objects..."
    aws s3 rm "s3://$BUCKET_NAME" --recursive 2>/dev/null || true
    
    print_success "S3 bucket cleaned: $BUCKET_NAME"
else
    print_status "Bucket not found or already deleted: $BUCKET_NAME"
fi

# Step 2: Remove Lambda Function Event Source Mappings
print_status "Step 2: Cleaning Lambda event source mappings..."

for function in $(aws lambda list-functions --region "$AWS_REGION" --query "Functions[?starts_with(FunctionName, '${PROJECT_NAME}')].FunctionName" --output text 2>/dev/null); do
    print_status "Checking function: $function"
    for mapping_uuid in $(aws lambda list-event-source-mappings --function-name "$function" --query "EventSourceMappings[].UUID" --output text 2>/dev/null); do
        print_status "Deleting event source mapping: $mapping_uuid"
        aws lambda delete-event-source-mapping --uuid "$mapping_uuid" 2>/dev/null || true
    done
done

# Step 3: Clean up CloudWatch Log Groups
print_status "Step 3: Cleaning CloudWatch log groups..."

for log_group in $(aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/${PROJECT_NAME}" --query "logGroups[].logGroupName" --output text 2>/dev/null); do
    print_status "Deleting log group: $log_group"
    aws logs delete-log-group --log-group-name "$log_group" 2>/dev/null || true
done

# API Gateway logs
aws logs delete-log-group --log-group-name "/aws/apigateway/${PROJECT_NAME}-${ENVIRONMENT}" 2>/dev/null || true

# Step 4: Run Terraform Destroy
print_status "Step 4: Running Terraform destroy..."

cd "$(dirname "$0")/../infrastructure" || exit 1

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    print_status "Initializing Terraform..."
    terraform init
fi

# Run destroy with auto-approve
print_status "Destroying infrastructure with Terraform..."
terraform destroy \
    -var="project_name=${PROJECT_NAME}" \
    -var="aws_region=${AWS_REGION}" \
    -auto-approve

# Step 5: Final Cleanup
print_status "Step 5: Performing final cleanup..."

# Clean up any remaining API Gateways
for api_id in $(aws apigateway get-rest-apis --query "items[?contains(name, '${PROJECT_NAME}')].id" --output text 2>/dev/null); do
    print_status "Deleting API Gateway: $api_id"
    aws apigateway delete-rest-api --rest-api-id "$api_id" 2>/dev/null || true
done

# Clean up any remaining DynamoDB tables
for table in $(aws dynamodb list-tables --query "TableNames[?contains(@, '${PROJECT_NAME}')]" --output text 2>/dev/null); do
    print_status "Deleting DynamoDB table: $table"
    aws dynamodb delete-table --table-name "$table" 2>/dev/null || true
done

# Clean up any remaining SQS queues
for queue_url in $(aws sqs list-queues --queue-name-prefix "${PROJECT_NAME}" --query "QueueUrls[]" --output text 2>/dev/null); do
    print_status "Deleting SQS queue: $queue_url"
    aws sqs delete-queue --queue-url "$queue_url" 2>/dev/null || true
done

print_success "========================================="
print_success "Destroy process completed successfully!"
print_success "========================================="

# Optional: Show remaining resources
echo ""
print_status "Checking for any remaining resources..."

remaining_resources=0

# Check for Lambda functions
lambda_count=$(aws lambda list-functions --query "Functions[?contains(FunctionName, '${PROJECT_NAME}')] | length(@)" --output text 2>/dev/null || echo "0")
if [ "$lambda_count" -gt 0 ]; then
    print_error "Found $lambda_count remaining Lambda functions"
    remaining_resources=$((remaining_resources + lambda_count))
fi

# Check for S3 buckets
s3_count=$(aws s3api list-buckets --query "Buckets[?contains(Name, '${PROJECT_NAME}')] | length(@)" --output text 2>/dev/null || echo "0")
if [ "$s3_count" -gt 0 ]; then
    print_error "Found $s3_count remaining S3 buckets"
    remaining_resources=$((remaining_resources + s3_count))
fi

if [ $remaining_resources -eq 0 ]; then
    print_success "All resources have been successfully destroyed!"
else
    print_error "Some resources may still exist. Please check the AWS console."
fi