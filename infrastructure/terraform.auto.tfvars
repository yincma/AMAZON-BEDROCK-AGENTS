# Auto-loaded Terraform Variables for Quick Deployment
# This file provides default values for required variables

# Required variables
owner       = "dev-team"
cost_center = "development"

# API Gateway variables
api_throttle_rate_limit  = 100
api_throttle_burst_limit = 200
api_keys                 = []

# DynamoDB billing mode
dynamodb_billing_mode = "PAY_PER_REQUEST"

# Lambda architecture
lambda_architecture = "x86_64"

# Lambda functions configuration
lambda_functions = {}

# Log retention
log_retention_days = 7

# S3 lifecycle rules
s3_lifecycle_rules = []

# S3 CORS configuration
s3_cors_configuration = [
  {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
]

# Bedrock configuration
bedrock_region = "us-east-1"

# VPC configuration
enable_lambda_vpc_config    = false
vpc_cidr                    = "10.0.0.0/16"
availability_zones          = ["us-east-1a", "us-east-1b"]
enable_vpc_endpoints        = false
enable_sqs_endpoint         = false
enable_nat_gateway          = false
enable_vpc_flow_logs        = false
vpc_flow_log_retention_days = 7

# Logging
log_level = "INFO"