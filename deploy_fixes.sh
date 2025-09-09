#!/bin/bash

# AI PPT Assistant - Deploy Fixes Script
# This script deploys all fixes for the identified issues

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="${PROJECT_NAME:-ai-ppt-assistant}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo -e "${BOLD}${BLUE}AI PPT Assistant - Deployment Fixes${NC}"
echo -e "${BOLD}Project:${NC} $PROJECT_NAME"
echo -e "${BOLD}Environment:${NC} $ENVIRONMENT"
echo -e "${BOLD}Region:${NC} $AWS_REGION"
echo -e "${BOLD}Timestamp:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Function to print step
print_step() {
    echo -e "\n${BOLD}${BLUE}[$1]${NC} $2"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print error
print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Step 1: Package Lambda functions
print_step "1/8" "Packaging Lambda functions..."

# Package task_processor function
if [ -f "lambdas/api/task_processor.py" ]; then
    cd lambdas/api
    zip -q task_processor.zip task_processor.py
    cd ../..
    print_success "Packaged task_processor.zip"
else
    print_warning "task_processor.py not found, skipping..."
fi

# Re-package generate_presentation with fixes
cd lambdas/api
zip -q generate_presentation.zip generate_presentation.py
cd ../..
print_success "Packaged generate_presentation.zip"

# Re-package presentation_download with fixes
cd lambdas/api
zip -q presentation_download.zip presentation_download.py
cd ../..
print_success "Packaged presentation_download.zip"

# Step 2: Build Lambda layers
print_step "2/8" "Building Lambda layers..."
cd lambdas/layers
if [ -f "build.sh" ]; then
    ./build.sh
    print_success "Lambda layers built"
else
    print_warning "Lambda layer build script not found"
fi
cd ../..

# Step 3: Update Terraform configuration
print_step "3/8" "Updating Terraform configuration..."

# Check if SQS Lambda mapping file needs to be included
if [ -f "infrastructure/sqs_lambda_mapping.tf" ]; then
    print_success "SQS Lambda mapping configuration found"
else
    print_error "SQS Lambda mapping configuration missing!"
fi

# Step 4: Initialize Terraform
print_step "4/8" "Initializing Terraform..."
cd infrastructure
terraform init -upgrade
print_success "Terraform initialized"

# Step 5: Validate Terraform configuration
print_step "5/8" "Validating Terraform configuration..."
if terraform validate; then
    print_success "Terraform configuration is valid"
else
    print_error "Terraform validation failed!"
    exit 1
fi

# Step 6: Plan Terraform changes
print_step "6/8" "Planning infrastructure changes..."
terraform plan -out=tfplan-fixes

echo ""
read -p "Review the plan above. Do you want to apply these changes? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    print_warning "Deployment cancelled by user"
    exit 0
fi

# Step 7: Apply Terraform changes
print_step "7/8" "Applying infrastructure changes..."
if terraform apply tfplan-fixes; then
    print_success "Infrastructure updated successfully"
else
    print_error "Terraform apply failed!"
    exit 1
fi

# Apply environment variable fixes using AWS CLI
print_step "7.5/8" "Applying Lambda environment variable fixes..."

# Update generate_presentation function
aws lambda update-function-configuration \
    --function-name "${PROJECT_NAME}-api-generate-presentation" \
    --environment Variables="{
        DYNAMODB_TASKS_TABLE='${PROJECT_NAME}-${ENVIRONMENT}-tasks',
        DYNAMODB_SESSIONS_TABLE='${PROJECT_NAME}-${ENVIRONMENT}-sessions',
        DYNAMODB_CHECKPOINTS_TABLE='${PROJECT_NAME}-${ENVIRONMENT}-checkpoints',
        S3_BUCKET='${PROJECT_NAME}-${ENVIRONMENT}-presentations',
        SQS_QUEUE_URL='https://sqs.${AWS_REGION}.amazonaws.com/$(aws sts get-caller-identity --query Account --output text)/${PROJECT_NAME}-${ENVIRONMENT}-tasks',
        ORCHESTRATOR_AGENT_ID='LA1D127LSK',
        ORCHESTRATOR_ALIAS_ID='PSQBDUP6KR',
        LOG_LEVEL='INFO'
    }" \
    --region ${AWS_REGION} > /dev/null

print_success "Updated generate_presentation environment variables"

# Update presentation_status function
aws lambda update-function-configuration \
    --function-name "${PROJECT_NAME}-api-presentation-status" \
    --environment Variables="{
        DYNAMODB_TABLE='${PROJECT_NAME}-${ENVIRONMENT}-tasks',
        DYNAMODB_TASKS_TABLE='${PROJECT_NAME}-${ENVIRONMENT}-tasks',
        DYNAMODB_SESSIONS_TABLE='${PROJECT_NAME}-${ENVIRONMENT}-sessions',
        LOG_LEVEL='INFO'
    }" \
    --region ${AWS_REGION} > /dev/null

print_success "Updated presentation_status environment variables"

# Update presentation_download function
aws lambda update-function-configuration \
    --function-name "${PROJECT_NAME}-api-presentation-download" \
    --environment Variables="{
        DYNAMODB_TABLE='${PROJECT_NAME}-${ENVIRONMENT}-tasks',
        DYNAMODB_TASKS_TABLE='${PROJECT_NAME}-${ENVIRONMENT}-tasks',
        S3_BUCKET='${PROJECT_NAME}-${ENVIRONMENT}-presentations',
        DOWNLOAD_EXPIRY_SECONDS='3600',
        LOG_LEVEL='INFO'
    }" \
    --region ${AWS_REGION} > /dev/null

print_success "Updated presentation_download environment variables"

cd ..

# Step 8: Run validation
print_step "8/8" "Running deployment validation..."

# Check if Python validation script exists
if [ -f "scripts/validate_deployment.py" ]; then
    python3 scripts/validate_deployment.py
    if [ $? -eq 0 ]; then
        print_success "Deployment validation passed"
    else
        print_error "Deployment validation failed"
        print_warning "Check the validation output above for details"
    fi
else
    print_warning "Validation script not found, skipping validation"
fi

# Summary
echo ""
echo -e "${BOLD}${GREEN}========================================${NC}"
echo -e "${BOLD}${GREEN}   Deployment Fixes Complete!          ${NC}"
echo -e "${BOLD}${GREEN}========================================${NC}"
echo ""
echo -e "${BOLD}Next Steps:${NC}"
echo "1. Monitor CloudWatch logs for any errors"
echo "2. Test the API endpoints to verify functionality"
echo "3. Check SQS queue processing"
echo "4. Verify tasks are being stored in DynamoDB"
echo ""
echo -e "${BOLD}Monitoring Commands:${NC}"
echo "  # Check SQS queue"
echo "  aws sqs get-queue-attributes --queue-url \$(aws sqs get-queue-url --queue-name ${PROJECT_NAME}-${ENVIRONMENT}-tasks --query QueueUrl --output text) --attribute-names All"
echo ""
echo "  # Check Lambda logs"
echo "  aws logs tail /aws/lambda/${PROJECT_NAME}-task-processor --follow"
echo ""
echo "  # Check DynamoDB tasks"
echo "  aws dynamodb scan --table-name ${PROJECT_NAME}-${ENVIRONMENT}-tasks --max-items 5"
echo ""