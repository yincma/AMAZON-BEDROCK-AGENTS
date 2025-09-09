# AI PPT Assistant - Troubleshooting Guide

## 🔍 Common Issues and Solutions

### 1. Tasks Stuck in "Pending" Status

**Symptoms:**
- Tasks remain in pending status indefinitely
- No progress updates in DynamoDB
- API returns 202 but nothing happens

**Root Causes:**
- SQS Lambda trigger not configured
- Lambda function not processing messages
- Bedrock Agent invocation failing

**Solutions:**

```bash
# Check SQS queue for unprocessed messages
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name ai-ppt-assistant-dev-tasks --query QueueUrl --output text) \
  --attribute-names ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible

# Check Lambda event source mappings
aws lambda list-event-source-mappings \
  --function-name ai-ppt-assistant-task-processor

# View Lambda logs for errors
aws logs tail /aws/lambda/ai-ppt-assistant-task-processor --follow

# Check dead letter queue for failed messages
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name ai-ppt-assistant-dev-dlq --query QueueUrl --output text) \
  --max-number-of-messages 10
```

### 2. DynamoDB Data Not Persisting

**Symptoms:**
- Tasks created but not found in DynamoDB
- 404 errors when querying task status
- Data inconsistency

**Root Causes:**
- Wrong table name in environment variables
- IAM permissions missing for DynamoDB
- Table key mismatch (task_id vs presentation_id)

**Solutions:**

```bash
# Verify Lambda environment variables
aws lambda get-function-configuration \
  --function-name ai-ppt-assistant-api-generate-presentation \
  --query 'Environment.Variables'

# Check DynamoDB tables
aws dynamodb scan \
  --table-name ai-ppt-assistant-dev-tasks \
  --max-items 5

# Update environment variables if needed
aws lambda update-function-configuration \
  --function-name ai-ppt-assistant-api-generate-presentation \
  --environment Variables='{
    "DYNAMODB_TASKS_TABLE":"ai-ppt-assistant-dev-tasks",
    "DYNAMODB_SESSIONS_TABLE":"ai-ppt-assistant-dev-sessions"
  }'
```

### 3. File Download Returns 403 Forbidden

**Symptoms:**
- GET /presentations/{id}/download returns 403
- S3 presigned URL generation fails
- Files exist but can't be accessed

**Root Causes:**
- S3 bucket permissions incorrect
- Lambda missing S3 permissions
- Presigned URL expired or invalid

**Solutions:**

```bash
# Check S3 bucket policy
aws s3api get-bucket-policy --bucket ai-ppt-assistant-dev-presentations

# Verify Lambda IAM role permissions
aws iam get-role-policy \
  --role-name ai-ppt-assistant-lambda-execution-role \
  --policy-name ai-ppt-assistant-lambda-policy

# Test S3 access directly
aws s3 ls s3://ai-ppt-assistant-dev-presentations/

# Generate test presigned URL
aws s3 presign s3://ai-ppt-assistant-dev-presentations/test.pptx \
  --expires-in 3600
```

### 4. Bedrock Agent Invocation Fails

**Symptoms:**
- AccessDeniedException when calling Bedrock
- Agent not responding
- Invalid model identifier errors

**Root Causes:**
- Agent ID or Alias ID incorrect
- IAM permissions missing for bedrock:InvokeAgent
- Model ID using wrong format

**Solutions:**

```bash
# List available agents
aws bedrock-agent list-agents --region us-east-1

# Get agent details
aws bedrock-agent get-agent \
  --agent-id LA1D127LSK \
  --region us-east-1

# Check agent alias
aws bedrock-agent get-agent-alias \
  --agent-id LA1D127LSK \
  --agent-alias-id PSQBDUP6KR \
  --region us-east-1

# Test agent invocation
aws bedrock-agent-runtime invoke-agent \
  --agent-id LA1D127LSK \
  --agent-alias-id PSQBDUP6KR \
  --session-id test-session \
  --input-text "Test message" \
  --region us-east-1
```

### 5. Lambda Cold Start Issues

**Symptoms:**
- First request takes very long
- Timeouts on initial invocations
- Performance degrades after idle periods

**Solutions:**

```bash
# Enable provisioned concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name ai-ppt-assistant-api-generate-presentation \
  --provisioned-concurrent-executions 2 \
  --qualifier $LATEST

# Increase memory allocation for better CPU
aws lambda update-function-configuration \
  --function-name ai-ppt-assistant-api-generate-presentation \
  --memory-size 1024

# Set reserved concurrent executions
aws lambda put-function-concurrency \
  --function-name ai-ppt-assistant-task-processor \
  --reserved-concurrent-executions 10
```

## 📊 Monitoring Commands

### Check System Health

```bash
# Overall system status
python3 scripts/validate_deployment.py

# Check all Lambda functions
for func in $(aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `ai-ppt-assistant`)].FunctionName' --output text); do
  echo "Function: $func"
  aws lambda get-function --function-name $func --query 'Configuration.State'
done

# Check all DynamoDB tables
for table in sessions tasks checkpoints; do
  echo "Table: ai-ppt-assistant-dev-$table"
  aws dynamodb describe-table --table-name ai-ppt-assistant-dev-$table --query 'Table.TableStatus'
done
```

### View Real-time Logs

```bash
# API Lambda logs
aws logs tail /aws/lambda/ai-ppt-assistant-api-generate-presentation --follow

# Task processor logs
aws logs tail /aws/lambda/ai-ppt-assistant-task-processor --follow

# Filter for errors only
aws logs filter-log-events \
  --log-group-name /aws/lambda/ai-ppt-assistant-api-generate-presentation \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"
```

### Check Queue Status

```bash
# Main task queue
QUEUE_URL=$(aws sqs get-queue-url --queue-name ai-ppt-assistant-dev-tasks --query QueueUrl --output text)
aws sqs get-queue-attributes --queue-url $QUEUE_URL --attribute-names All

# Dead letter queue
DLQ_URL=$(aws sqs get-queue-url --queue-name ai-ppt-assistant-dev-dlq --query QueueUrl --output text)
aws sqs get-queue-attributes --queue-url $DLQ_URL --attribute-names All
```

## 🔧 Quick Fixes

### Reset Stuck Task

```python
import boto3
import json

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ai-ppt-assistant-dev-tasks')

# Reset task to pending
table.update_item(
    Key={'task_id': 'YOUR_TASK_ID'},
    UpdateExpression='SET #status = :status, #progress = :progress',
    ExpressionAttributeNames={
        '#status': 'status',
        '#progress': 'progress'
    },
    ExpressionAttributeValues={
        ':status': 'pending',
        ':progress': 0
    }
)
```

### Manually Process SQS Message

```python
import boto3
import json

sqs = boto3.client('sqs')
lambda_client = boto3.client('lambda')

# Receive message from queue
queue_url = 'YOUR_QUEUE_URL'
response = sqs.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=1
)

if 'Messages' in response:
    message = response['Messages'][0]
    
    # Process with Lambda
    lambda_client.invoke(
        FunctionName='ai-ppt-assistant-task-processor',
        InvocationType='Event',
        Payload=json.dumps({
            'Records': [message]
        })
    )
    
    # Delete from queue
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=message['ReceiptHandle']
    )
```

### Force Redeployment

```bash
# Force Lambda update
aws lambda update-function-code \
  --function-name ai-ppt-assistant-api-generate-presentation \
  --zip-file fileb://lambdas/api/generate_presentation.zip

# Force API Gateway deployment
aws apigateway create-deployment \
  --rest-api-id YOUR_API_ID \
  --stage-name dev \
  --description "Force redeployment"
```

## 🚨 Emergency Procedures

### Complete System Reset

```bash
# 1. Clear all queues
aws sqs purge-queue --queue-url $(aws sqs get-queue-url --queue-name ai-ppt-assistant-dev-tasks --query QueueUrl --output text)
aws sqs purge-queue --queue-url $(aws sqs get-queue-url --queue-name ai-ppt-assistant-dev-dlq --query QueueUrl --output text)

# 2. Clear DynamoDB tables (BE CAREFUL!)
# This will delete all data
aws dynamodb scan --table-name ai-ppt-assistant-dev-tasks --query 'Items[].task_id.S' --output text | \
  xargs -I {} aws dynamodb delete-item --table-name ai-ppt-assistant-dev-tasks --key '{"task_id":{"S":"{}"}}'

# 3. Restart Lambda functions
for func in $(aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `ai-ppt-assistant`)].FunctionName' --output text); do
  aws lambda update-function-configuration --function-name $func --description "Reset $(date)"
done
```

### Rollback Deployment

```bash
# Using Terraform
cd infrastructure
terraform workspace select prod  # Switch to last known good
terraform apply

# Manual rollback
git checkout HEAD~1  # Previous commit
./deploy_fixes.sh
```

## 📞 Support Escalation

If issues persist after trying these solutions:

1. **Check AWS Service Health Dashboard**
   - https://status.aws.amazon.com/

2. **Review CloudWatch Insights**
   ```
   fields @timestamp, @message
   | filter @message like /ERROR/
   | sort @timestamp desc
   | limit 50
   ```

3. **Enable Enhanced Monitoring**
   ```bash
   aws lambda update-function-configuration \
     --function-name ai-ppt-assistant-task-processor \
     --tracing-config Mode=Active
   ```

4. **Contact AWS Support**
   - Include deployment validation output
   - Provide CloudWatch log excerpts
   - Share specific error messages

## 🔄 Preventive Measures

### Daily Health Checks

```bash
# Create cron job for daily validation
0 9 * * * /path/to/scripts/validate_deployment.py > /var/log/ai-ppt-health.log 2>&1
```

### Monitoring Alerts

```bash
# Set up CloudWatch alarm for DLQ
aws cloudwatch put-metric-alarm \
  --alarm-name ai-ppt-dlq-messages \
  --alarm-description "Alert when messages in DLQ" \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=ai-ppt-assistant-dev-dlq
```

### Regular Backups

```bash
# Backup DynamoDB tables
aws dynamodb create-backup \
  --table-name ai-ppt-assistant-dev-tasks \
  --backup-name tasks-backup-$(date +%Y%m%d)
```

---

**Last Updated:** 2025-09-08
**Version:** 1.0