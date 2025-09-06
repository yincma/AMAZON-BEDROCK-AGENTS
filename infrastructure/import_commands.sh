#!/bin/bash
# Import existing resources to modular configuration
# Updated with actual resource IDs from current state

echo "==========================================="
echo "Starting resource import to modular config"
echo "==========================================="

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Import counter
IMPORTED=0
FAILED=0

# Function to run import and track status
run_import() {
    echo -n "Importing $1... "
    if terraform import $2 $3 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        ((IMPORTED++))
    else
        echo -e "${RED}✗${NC}"
        ((FAILED++))
        echo "  Failed command: terraform import $2 $3"
    fi
}

echo ""
echo "Importing resources..."
echo ""

# Import S3 bucket
run_import "S3 bucket" \
    "module.s3.aws_s3_bucket.presentations" \
    "ai-ppt-assistant-dev-presentations-52de98b4"

# Import DynamoDB tables  
run_import "DynamoDB sessions table" \
    "module.dynamodb.aws_dynamodb_table.sessions" \
    "ai-ppt-assistant-dev-sessions"

run_import "DynamoDB checkpoints table" \
    "module.dynamodb.aws_dynamodb_table.checkpoints" \
    "ai-ppt-assistant-dev-checkpoints"

# Import SQS queues
run_import "SQS task queue" \
    "aws_sqs_queue.task_queue" \
    "ai-ppt-assistant-dev-tasks"

run_import "SQS DLQ" \
    "aws_sqs_queue.dlq" \
    "ai-ppt-assistant-dev-dlq"

# Import API Gateway
run_import "API Gateway" \
    "module.api_gateway.aws_api_gateway_rest_api.api" \
    "byih5fsutb"

# Import Lambda layer
run_import "Lambda dependencies layer" \
    "module.lambda.aws_lambda_layer_version.dependencies" \
    "arn:aws:lambda:us-east-1:375004070918:layer:ai-ppt-assistant-dev-dependencies:1"

# Import Random ID (base64 standard encoding)
run_import "Random ID for bucket suffix" \
    "random_id.bucket_suffix" \
    "Ut6YtA=="

echo ""
echo "==========================================="
echo "Import Summary"
echo "==========================================="
echo -e "Successfully imported: ${GREEN}$IMPORTED${NC}"
echo -e "Failed imports: ${RED}$FAILED${NC}"

if [ $FAILED -gt 0 ]; then
    echo ""
    echo "⚠️  Some imports failed. Please review the errors above."
    echo "You may need to manually adjust the import commands."
else
    echo ""
    echo "✅ All resources imported successfully!"
    echo "Next step: Run 'terraform plan' to verify the configuration."
fi
