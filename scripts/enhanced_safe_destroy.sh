#!/bin/bash

# Enhanced Safe Destroy Script for AI PPT Assistant
# This script intelligently handles CloudFront dependencies before Terraform destroy
# Version: 2.0
# Author: ultrathink

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_NAME="ai-ppt-assistant"
ENVIRONMENT="dev"
AWS_REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
START_TIME=$(date +%s)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Enhanced Safe Destroy Script v2.0${NC}"
echo -e "${GREEN}AI PPT Assistant Infrastructure${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

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

# Function to print info
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to calculate elapsed time
print_elapsed_time() {
    local current_time=$(date +%s)
    local elapsed=$((current_time - START_TIME))
    local minutes=$((elapsed / 60))
    local seconds=$((elapsed % 60))
    print_info "Elapsed time: ${minutes}m ${seconds}s"
}

# Step 0: Pre-flight Check - CloudFront Resources
print_status "Step 0: Pre-flight check for CloudFront resources..."

# Check for CloudFront OAIs
OAI_COUNT=$(aws cloudfront list-cloud-front-origin-access-identities --query "CloudFrontOriginAccessIdentityList.Items | length(@)" --output text 2>/dev/null || echo "0")
if [ "$OAI_COUNT" -gt 0 ]; then
    print_info "Found $OAI_COUNT CloudFront Origin Access Identity(ies)"
    
    # Get all OAI IDs
    OAI_IDS=$(aws cloudfront list-cloud-front-origin-access-identities --query "CloudFrontOriginAccessIdentityList.Items[].Id" --output text 2>/dev/null || echo "")
    
    for OAI_ID in $OAI_IDS; do
        print_status "Processing OAI: $OAI_ID"
        
        # Find distributions using this OAI
        DISTRIBUTIONS=$(aws cloudfront list-distributions --query "DistributionList.Items[?Origins.Items[?S3OriginConfig.OriginAccessIdentity=='origin-access-identity/cloudfront/${OAI_ID}']].Id" --output text 2>/dev/null || echo "")
        
        if [ -n "$DISTRIBUTIONS" ]; then
            print_info "Found distributions using OAI $OAI_ID:"
            for DIST_ID in $DISTRIBUTIONS; do
                echo "  - $DIST_ID"
            done
            
            # Process each distribution
            print_status "Starting CloudFront distribution cleanup..."
            print_info "This process may take 15-30 minutes due to AWS global propagation"
            
            # First pass: Disable all distributions in parallel
            print_status "Phase 1: Disabling all distributions..."
            for DIST_ID in $DISTRIBUTIONS; do
                (
                    print_status "Disabling distribution: $DIST_ID"
                    
                    # Get distribution config
                    aws cloudfront get-distribution-config --id "$DIST_ID" > /tmp/dist-config-$DIST_ID.json 2>&1
                    
                    if [ $? -eq 0 ]; then
                        # Extract ETag
                        ETAG=$(jq -r '.ETag' /tmp/dist-config-$DIST_ID.json)
                        
                        # Check if already disabled
                        ENABLED=$(jq -r '.DistributionConfig.Enabled' /tmp/dist-config-$DIST_ID.json)
                        
                        if [ "$ENABLED" == "true" ]; then
                            # Modify config to disable
                            jq '.DistributionConfig.Enabled = false' /tmp/dist-config-$DIST_ID.json | jq '.DistributionConfig' > /tmp/dist-config-update-$DIST_ID.json
                            
                            # Update distribution
                            aws cloudfront update-distribution \
                                --id "$DIST_ID" \
                                --distribution-config file:///tmp/dist-config-update-$DIST_ID.json \
                                --if-match "$ETAG" > /dev/null 2>&1
                            
                            if [ $? -eq 0 ]; then
                                print_success "Distribution $DIST_ID disabled successfully"
                            else
                                print_error "Failed to disable distribution $DIST_ID"
                            fi
                        else
                            print_info "Distribution $DIST_ID is already disabled"
                        fi
                    fi
                ) &
            done
            
            # Wait for all disable operations to complete
            wait
            print_success "All distributions have been disabled"
            
            # Second pass: Wait for deployment and delete
            print_status "Phase 2: Waiting for deployment and deleting distributions..."
            print_info "Checking distribution status every 30 seconds..."
            
            # Track remaining distributions
            REMAINING_DISTRIBUTIONS="$DISTRIBUTIONS"
            CHECK_COUNTER=0
            MAX_CHECKS=60  # 30 minutes maximum
            
            while [ -n "$REMAINING_DISTRIBUTIONS" ] && [ $CHECK_COUNTER -lt $MAX_CHECKS ]; do
                NEW_REMAINING=""
                
                for DIST_ID in $REMAINING_DISTRIBUTIONS; do
                    STATUS=$(aws cloudfront get-distribution --id "$DIST_ID" --query "Distribution.Status" --output text 2>/dev/null)
                    
                    if [ "$STATUS" == "Deployed" ]; then
                        print_status "Distribution $DIST_ID is ready for deletion"
                        
                        # Get the final ETag
                        aws cloudfront get-distribution-config --id "$DIST_ID" > /tmp/dist-config-$DIST_ID-final.json 2>&1
                        ETAG=$(jq -r '.ETag' /tmp/dist-config-$DIST_ID-final.json)
                        
                        # Delete the distribution
                        aws cloudfront delete-distribution --id "$DIST_ID" --if-match "$ETAG" 2>&1
                        
                        if [ $? -eq 0 ]; then
                            print_success "Distribution $DIST_ID deleted successfully"
                        else
                            print_error "Failed to delete distribution $DIST_ID"
                            NEW_REMAINING="$NEW_REMAINING $DIST_ID"
                        fi
                    elif [ "$STATUS" == "InProgress" ]; then
                        NEW_REMAINING="$NEW_REMAINING $DIST_ID"
                    fi
                done
                
                REMAINING_DISTRIBUTIONS="$NEW_REMAINING"
                
                if [ -n "$REMAINING_DISTRIBUTIONS" ]; then
                    CHECK_COUNTER=$((CHECK_COUNTER + 1))
                    
                    # Print progress every 2 minutes
                    if [ $((CHECK_COUNTER % 4)) -eq 0 ]; then
                        print_info "Still waiting for distributions to deploy... ($(($CHECK_COUNTER / 2)) minutes elapsed)"
                        print_info "Remaining distributions: $REMAINING_DISTRIBUTIONS"
                        print_elapsed_time
                    fi
                    
                    sleep 30
                fi
            done
            
            if [ -z "$REMAINING_DISTRIBUTIONS" ]; then
                print_success "All CloudFront distributions have been deleted"
            else
                print_error "Some distributions could not be deleted: $REMAINING_DISTRIBUTIONS"
                print_error "You may need to manually delete these distributions"
            fi
        fi
    done
else
    print_info "No CloudFront OAIs found"
fi

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
print_elapsed_time

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
    -var="owner=AI-Team" \
    -var="cost_center=Engineering" \
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
print_elapsed_time

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

# Check for CloudFront distributions
cf_count=$(aws cloudfront list-distributions --query "DistributionList.Items | length(@)" --output text 2>/dev/null || echo "0")
if [ "$cf_count" -gt 0 ]; then
    print_error "Found $cf_count remaining CloudFront distributions"
    remaining_resources=$((remaining_resources + cf_count))
fi

if [ $remaining_resources -eq 0 ]; then
    print_success "All resources have been successfully destroyed!"
else
    print_error "Some resources may still exist. Please check the AWS console."
fi

echo ""
print_info "Total execution time:"
print_elapsed_time