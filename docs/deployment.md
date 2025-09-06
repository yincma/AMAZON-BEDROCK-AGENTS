# AI PPT Assistant - Deployment Guide

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Configuration](#configuration)
- [Deployment Steps](#deployment-steps)
- [Post-Deployment Verification](#post-deployment-verification)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)
- [Security Considerations](#security-considerations)

## Prerequisites

### Required Tools

| Tool | Minimum Version | Installation Guide |
|------|----------------|-------------------|
| AWS CLI | 2.x | `brew install awscli` or [AWS Documentation](https://aws.amazon.com/cli/) |
| Terraform | 1.6.0+ | `brew install terraform` or [Terraform Downloads](https://www.terraform.io/downloads) |
| Python | 3.13 | `brew install python@3.13` or [Python Downloads](https://www.python.org/downloads/) |
| Git | 2.x | `brew install git` |
| Make | 3.x | Pre-installed on Unix systems |

### AWS Account Requirements

1. **AWS Account**: Active AWS account with appropriate permissions
2. **IAM Permissions**: Administrator access or custom policy with permissions for:
   - Lambda
   - API Gateway
   - S3
   - DynamoDB
   - SQS
   - Bedrock
   - IAM (for role creation)
   - CloudWatch
3. **Bedrock Access**: Ensure Bedrock is enabled in your region with access to:
   - Claude 4.0
   - Claude 4.1
   - Amazon Nova Canvas

### Resource Quotas

Verify the following AWS service quotas in your account:

| Service | Resource | Required Quota |
|---------|----------|---------------|
| Lambda | Concurrent executions | 100+ |
| Lambda | Function and layer storage | 10 GB |
| API Gateway | REST APIs | 5+ |
| DynamoDB | On-demand tables | 5+ |
| S3 | Buckets | 5+ |
| SQS | Queues | 5+ |

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/ai-ppt-assistant.git
cd ai-ppt-assistant
```

### 2. Configure AWS Credentials

```bash
# Option 1: Using AWS CLI
aws configure
# Enter your AWS Access Key ID, Secret Access Key, Region (us-east-1), and output format

# Option 2: Using environment variables
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"

# Option 3: Using AWS SSO
aws sso login --profile your-profile
export AWS_PROFILE=your-profile
```

### 3. Create Virtual Environment

```bash
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

### 1. Terraform Variables

Create `infrastructure/terraform.tfvars`:

```hcl
# Project Configuration
project_name = "ai-ppt-assistant"
environment  = "production"
aws_region   = "us-east-1"

# Lambda Configuration
lambda_memory_size = {
  create_outline     = 1024
  generate_content   = 2048
  generate_image     = 1024
  compile_pptx       = 3008
  api_endpoints      = 512
}

lambda_timeout = {
  create_outline     = 60
  generate_content   = 120
  generate_image     = 90
  compile_pptx       = 180
  api_endpoints      = 30
}

# Bedrock Configuration
bedrock_models = {
  orchestrator = "anthropic.claude-4-1"
  content      = "anthropic.claude-4-0"
  visual       = "anthropic.claude-4-0"
  compiler     = "anthropic.claude-4-0"
}

# S3 Configuration
s3_lifecycle_rules = {
  transition_to_ia_days           = 30
  transition_to_glacier_days      = 90
  expiration_days                 = 365
}

# DynamoDB Configuration
dynamodb_ttl_days = 30

# API Gateway Configuration
api_throttle_burst_limit = 100
api_throttle_rate_limit  = 50

# Tags
tags = {
  Project     = "AI PPT Assistant"
  Environment = "production"
  ManagedBy   = "Terraform"
  Owner       = "your-team"
  CostCenter  = "your-cost-center"
}
```

### 2. Environment-Specific Configuration

For different environments, create separate variable files:

- `terraform.dev.tfvars` - Development environment
- `terraform.staging.tfvars` - Staging environment
- `terraform.prod.tfvars` - Production environment

## Deployment Steps

### 1. Build Lambda Layers

```bash
# Build Python dependencies layer
cd lambdas/layers
./build.sh
cd ../..
```

### 2. Package Lambda Functions

```bash
# Package all Lambda functions
make package-lambdas
```

### 3. Initialize Terraform

```bash
cd infrastructure
terraform init
```

### 4. Plan Deployment

```bash
# Review the deployment plan
terraform plan -var-file="terraform.tfvars"

# Save the plan for later execution
terraform plan -var-file="terraform.tfvars" -out=tfplan
```

### 5. Deploy Infrastructure

```bash
# Apply the Terraform configuration
terraform apply -var-file="terraform.tfvars"

# Or apply the saved plan
terraform apply tfplan
```

### 6. Create Agent Configuration Files

After infrastructure deployment, create agent configuration files:

```bash
# Create agent instruction files
for agent in orchestrator content visual compiler; do
  aws s3 cp agents/$agent/instructions.txt \
    s3://${PROJECT_NAME}-bedrock-agent-configs/$agent/
  
  aws s3 cp agents/$agent/action_groups.json \
    s3://${PROJECT_NAME}-bedrock-agent-configs/$agent/
done
```

### 7. Deploy API Keys

```bash
# Create API key for authentication
aws apigateway create-api-key \
  --name "ai-ppt-assistant-key" \
  --enabled \
  --region us-east-1

# Associate with usage plan
aws apigateway create-usage-plan-key \
  --usage-plan-id <usage-plan-id> \
  --key-id <api-key-id> \
  --key-type API_KEY
```

## Post-Deployment Verification

### 1. Verify Infrastructure

```bash
# Check Lambda functions
aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'ai-ppt-assistant')]"

# Check API Gateway
aws apigateway get-rest-apis --query "items[?name=='ai-ppt-assistant-api']"

# Check DynamoDB tables
aws dynamodb list-tables --query "TableNames[?contains(@, 'ai-ppt-assistant')]"

# Check S3 buckets
aws s3 ls | grep ai-ppt-assistant

# Check Bedrock agents
aws bedrock-agent list-agents --query "agentSummaries[?contains(agentName, 'ai-ppt-assistant')]"
```

### 2. Run Smoke Tests

```bash
# Run smoke tests to verify basic functionality
make test-smoke

# Or manually test the API
curl -X POST https://api.example.com/presentations/generate \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "topic": "Test Presentation",
    "duration": 30,
    "slide_count": 5
  }'
```

### 3. Verify Monitoring

```bash
# Check CloudWatch logs
aws logs describe-log-groups \
  --query "logGroups[?contains(logGroupName, 'ai-ppt-assistant')]"

# Check metrics
aws cloudwatch list-metrics \
  --namespace "AWS/Lambda" \
  --dimensions Name=FunctionName,Value=ai-ppt-assistant-create-outline
```

## Monitoring & Maintenance

### CloudWatch Dashboards

Create CloudWatch dashboards for monitoring:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
          ["...", "Errors", {"stat": "Sum"}],
          ["...", "Duration", {"stat": "Average"}],
          ["...", "ConcurrentExecutions", {"stat": "Maximum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Performance"
      }
    }
  ]
}
```

### Alarms Configuration

Set up CloudWatch alarms:

```bash
# Lambda error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "ai-ppt-assistant-lambda-errors" \
  --alarm-description "Alert when Lambda error rate is high" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# API Gateway 4xx errors
aws cloudwatch put-metric-alarm \
  --alarm-name "ai-ppt-assistant-api-4xx" \
  --alarm-description "Alert on high 4xx error rate" \
  --metric-name 4XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

### Regular Maintenance Tasks

| Task | Frequency | Command/Action |
|------|-----------|---------------|
| Check Lambda logs | Daily | `aws logs tail /aws/lambda/ai-ppt-assistant --follow` |
| Monitor costs | Weekly | AWS Cost Explorer |
| Update dependencies | Monthly | `pip-audit` and update requirements.txt |
| Review security | Monthly | `aws accessanalyzer list-findings` |
| Backup DynamoDB | Weekly | Enable point-in-time recovery |
| Clean S3 old files | Monthly | Review lifecycle policies |

## Troubleshooting

### Common Issues and Solutions

#### 1. Lambda Timeout Errors

**Symptom**: Lambda functions timing out
**Solution**:
```bash
# Increase timeout in terraform.tfvars
lambda_timeout = {
  compile_pptx = 300  # Increase from 180 to 300
}

# Reapply configuration
terraform apply -var-file="terraform.tfvars"
```

#### 2. Bedrock Model Access Issues

**Symptom**: "Model not found" or "Access denied" errors
**Solution**:
```bash
# Check model access
aws bedrock list-foundation-models --region us-east-1

# Request model access if needed
# Go to AWS Console > Bedrock > Model access
```

#### 3. API Gateway 429 Errors

**Symptom**: Too many requests errors
**Solution**:
```bash
# Increase throttle limits
api_throttle_burst_limit = 200  # Increase from 100
api_throttle_rate_limit  = 100  # Increase from 50
```

#### 4. DynamoDB Throttling

**Symptom**: ProvisionedThroughputExceededException
**Solution**:
```bash
# Switch to on-demand billing mode
# Already configured in our setup, but verify:
aws dynamodb describe-table \
  --table-name ai-ppt-assistant-presentations \
  --query "Table.BillingModeSummary"
```

#### 5. SQS Message Processing Failures

**Symptom**: Messages ending up in DLQ
**Solution**:
```bash
# Check DLQ for failed messages
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/account/ai-ppt-assistant-dlq

# Redrive messages from DLQ
aws sqs start-message-move-task \
  --source-arn arn:aws:sqs:region:account:ai-ppt-assistant-dlq
```

### Debug Commands

```bash
# View Lambda logs
aws logs tail /aws/lambda/ai-ppt-assistant-create-outline --follow

# Test Lambda function
aws lambda invoke \
  --function-name ai-ppt-assistant-create-outline \
  --payload '{"topic":"Test"}' \
  response.json

# Check API Gateway logs
aws logs get-log-events \
  --log-group-name API-Gateway-Execution-Logs_<api-id>/prod

# Monitor SQS queue
watch -n 5 'aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names All'
```

## Rollback Procedures

### Quick Rollback

```bash
# Revert to previous Terraform state
cd infrastructure
terraform plan -destroy
terraform destroy -auto-approve

# Restore from backup
terraform apply -var-file="terraform.tfvars.backup"
```

### Gradual Rollback

1. **Disable API Gateway stages**
```bash
aws apigateway update-stage \
  --rest-api-id <api-id> \
  --stage-name prod \
  --patch-operations op=replace,path=/*/throttle/rateLimit,value=0
```

2. **Stop Lambda invocations**
```bash
# Set concurrency to 0
for func in $(aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'ai-ppt-assistant')].FunctionName" --output text); do
  aws lambda put-function-concurrency \
    --function-name $func \
    --reserved-concurrent-executions 0
done
```

3. **Restore previous version**
```bash
# Deploy previous Lambda versions
aws lambda update-function-code \
  --function-name ai-ppt-assistant-create-outline \
  --s3-bucket deployment-bucket \
  --s3-key lambdas/previous/create_outline.zip
```

## Security Considerations

### Best Practices

1. **IAM Roles**: Follow least privilege principle
2. **Encryption**: Enable encryption at rest for S3, DynamoDB
3. **API Keys**: Rotate API keys regularly
4. **VPC**: Consider deploying Lambda functions in VPC for additional security
5. **Secrets Manager**: Store sensitive configuration in AWS Secrets Manager

### Security Checklist

- [ ] Enable S3 bucket encryption
- [ ] Enable DynamoDB encryption
- [ ] Configure API Gateway request validation
- [ ] Enable CloudTrail logging
- [ ] Set up AWS WAF for API Gateway
- [ ] Enable GuardDuty for threat detection
- [ ] Configure VPC endpoints for AWS services
- [ ] Implement API rate limiting
- [ ] Enable X-Ray tracing for debugging
- [ ] Regular security audits with AWS Security Hub

### Compliance

Ensure compliance with:
- GDPR (if handling EU data)
- HIPAA (if handling healthcare data)
- SOC 2
- ISO 27001

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review CloudWatch logs
3. Contact the development team
4. Create an issue in the project repository

## Appendix

### Useful Scripts

```bash
# Full deployment script
#!/bin/bash
set -e

echo "Starting deployment..."
make clean
make build-layers
make package-lambdas
cd infrastructure
terraform init
terraform apply -var-file="terraform.tfvars" -auto-approve
cd ..
make test-smoke
echo "Deployment complete!"
```

### Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| AWS_REGION | AWS region for deployment | us-east-1 |
| PROJECT_NAME | Project identifier | ai-ppt-assistant |
| ENVIRONMENT | Deployment environment | production |
| LOG_LEVEL | Logging verbosity | INFO |
| BEDROCK_MODEL_ID | Default Bedrock model | anthropic.claude-4-0 |
| NOVA_MODEL_ID | Nova model for images | amazon.nova-canvas-v1:0 |