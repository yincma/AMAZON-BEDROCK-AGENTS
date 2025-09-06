#!/bin/bash
# Migration script to transition from minimal to modular Terraform configuration
# This script helps preserve existing resources while moving to modular architecture

set -e

echo "========================================="
echo "Terraform Configuration Migration Script"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if we're in the infrastructure directory
if [[ ! -f "main.tf" ]]; then
    print_error "Please run this script from the infrastructure directory"
    exit 1
fi

# Step 1: Backup current state and configuration
print_status "Step 1: Creating backups..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/${TIMESTAMP}"
mkdir -p ${BACKUP_DIR}

# Backup files
cp terraform.tfstate ${BACKUP_DIR}/terraform.tfstate.backup 2>/dev/null || true
cp main.tf ${BACKUP_DIR}/main.tf.backup
cp *.tf ${BACKUP_DIR}/ 2>/dev/null || true

print_status "Backups created in ${BACKUP_DIR}/"

# Step 2: Import existing resources to new configuration
print_status "Step 2: Preparing for resource import..."

# Create import commands file
cat > import_commands.sh << 'EOF'
#!/bin/bash
# Import existing resources to modular configuration

echo "Importing existing resources..."

# Import S3 bucket
terraform import module.s3.aws_s3_bucket.presentations ai-ppt-assistant-dev-presentations-52de98b4

# Import DynamoDB tables  
terraform import module.dynamodb.aws_dynamodb_table.sessions ai-ppt-assistant-dev-sessions
terraform import module.dynamodb.aws_dynamodb_table.checkpoints ai-ppt-assistant-dev-checkpoints

# Import SQS queues
terraform import aws_sqs_queue.task_queue ai-ppt-assistant-dev-tasks
terraform import aws_sqs_queue.dlq ai-ppt-assistant-dev-dlq

# Import API Gateway
terraform import module.api_gateway.aws_api_gateway_rest_api.api [API_ID]

# Import Lambda layer
terraform import module.lambda.aws_lambda_layer_version.dependencies [LAYER_ARN]

# Import Random ID
terraform import random_id.bucket_suffix [BASE64_ID]

echo "Import complete!"
EOF

chmod +x import_commands.sh
print_status "Import commands prepared in import_commands.sh"

# Step 3: Check module directories
print_status "Step 3: Checking module structure..."

MODULES=("vpc" "s3" "dynamodb" "api_gateway" "lambda" "bedrock")
MISSING_MODULES=()

for module in "${MODULES[@]}"; do
    if [[ ! -d "modules/$module" ]]; then
        MISSING_MODULES+=($module)
        print_warning "Module directory missing: modules/$module"
    else
        print_status "Module found: modules/$module"
    fi
done

# Step 4: Validate variables
print_status "Step 4: Checking variables.tf..."

if [[ ! -f "variables.tf" ]]; then
    print_error "variables.tf not found!"
    exit 1
fi

# Step 5: Migration plan
echo ""
echo "========================================="
echo "Migration Plan"
echo "========================================="
echo ""
echo "1. Review the refactored configuration in main_refactored.tf"
echo "2. Ensure all module directories exist in modules/"
echo "3. Review and update variables.tf with required values"
echo "4. Run the following commands:"
echo ""
echo "   # Initialize with new configuration"
echo "   mv main.tf main.tf.minimal"
echo "   cp main_refactored.tf main.tf"
echo "   terraform init -upgrade"
echo ""
echo "   # Import existing resources (edit import_commands.sh first)"
echo "   ./import_commands.sh"
echo ""
echo "   # Plan to see what changes"
echo "   terraform plan -out=migration.tfplan"
echo ""
echo "   # Review the plan carefully"
echo "   terraform show migration.tfplan"
echo ""
echo "   # Apply if everything looks good"
echo "   terraform apply migration.tfplan"
echo ""

# Step 6: Check current resources
print_status "Step 6: Current resources in state:"
terraform state list | head -20

echo ""
print_warning "IMPORTANT: Review and update import_commands.sh with actual resource IDs"
print_warning "IMPORTANT: Test in a non-production environment first!"

# Step 7: Generate terraform.tfvars.example
print_status "Step 7: Generating terraform.tfvars.example..."

cat > terraform.tfvars.example << 'EOF'
# Project Configuration
project_name = "ai-ppt-assistant"
environment  = "dev"
aws_region   = "us-east-1"
owner        = "team@example.com"
cost_center  = "engineering"

# VPC Configuration  
vpc_cidr = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]
enable_vpc_endpoints = true
enable_nat_gateway = false
enable_vpc_flow_logs = true
vpc_flow_log_retention_days = 7

# Lambda Configuration
lambda_architecture = "x86_64"
enable_lambda_vpc_config = false
log_level = "INFO"

# DynamoDB Configuration
dynamodb_billing_mode = "PAY_PER_REQUEST"

# API Gateway Configuration
api_throttle_rate_limit = 1000
api_throttle_burst_limit = 2000

# Bedrock Configuration
bedrock_region = "us-east-1"
bedrock_model_id = "anthropic.claude-v2"
bedrock_model_version = "latest"

# S3 Lifecycle Rules
s3_lifecycle_rules = []
s3_cors_configuration = {
  cors_rules = [{
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }]
}

# Lambda Functions Configuration
lambda_functions = {
  session_manager = {
    handler     = "handler.lambda_handler"
    timeout     = 30
    memory_size = 512
    reserved_concurrent_executions = 5
  }
  ppt_generator = {
    handler     = "handler.lambda_handler"
    timeout     = 300
    memory_size = 2048
    reserved_concurrent_executions = 2
  }
  content_enhancer = {
    handler     = "handler.lambda_handler"  
    timeout     = 60
    memory_size = 1024
    reserved_concurrent_executions = 3
  }
  auth_handler = {
    handler     = "handler.lambda_handler"
    timeout     = 10
    memory_size = 256
    reserved_concurrent_executions = 10
  }
}

# Bedrock Agents Configuration
bedrock_agents = {
  orchestrator = {
    description = "Main workflow orchestration agent"
    temperature = 0.7
    model_id    = "anthropic.claude-v2"
  }
  content = {
    description = "Content generation and optimization agent"
    temperature = 0.8
    model_id    = "anthropic.claude-v2"
  }
  design = {
    description = "Design and layout agent"
    temperature = 0.8
    model_id    = "anthropic.claude-v2"
  }
}

# Additional Tags
additional_tags = {
  Terraform = "true"
  Repository = "ai-ppt-assistant"
}
EOF

print_status "terraform.tfvars.example created"

echo ""
echo "========================================="
echo "Migration preparation complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Review main_refactored.tf"
echo "2. Update terraform.tfvars with your values"
echo "3. Update import_commands.sh with actual resource IDs"
echo "4. Run the migration commands shown above"
echo ""
print_warning "Remember to test in a safe environment first!"