# AI PPT Assistant - Deployment Checklist

## 📋 Pre-Deployment Checklist

### Environment Preparation
- [ ] AWS credentials configured
- [ ] Correct AWS region selected (us-east-1)
- [ ] Terraform installed (v1.6.0+)
- [ ] Python 3.13 installed
- [ ] All required tools available (aws-cli, make, git)

### Code Quality
- [ ] All unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] No critical linting errors
- [ ] Security scan completed
- [ ] Dependencies updated

### Configuration
- [ ] terraform.tfvars created with correct values
- [ ] API keys generated
- [ ] Environment variables documented
- [ ] Bedrock model access enabled
- [ ] Service quotas verified

## 🚀 Deployment Steps

### 1. Infrastructure Deployment
```bash
# Run the automated deployment script
./deploy.sh

# Or manual steps:
cd infrastructure
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

**Verification Points:**
- [ ] Terraform init successful
- [ ] Terraform plan shows expected resources
- [ ] Terraform apply completed without errors
- [ ] All resources created in correct region

### 2. Lambda Functions
- [ ] Lambda layers built successfully
- [ ] All Lambda functions packaged
- [ ] Functions deployed to AWS
- [ ] Correct runtime (Python 3.13) configured
- [ ] Environment variables set
- [ ] IAM roles attached

**Verification Commands:**
```bash
# List Lambda functions
aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'ai-ppt-assistant')].[FunctionName,Runtime,State]" --output table

# Test a Lambda function
aws lambda invoke \
  --function-name ai-ppt-assistant-create-outline \
  --payload '{"topic":"Test"}' \
  response.json
```

### 3. API Gateway
- [ ] REST API created
- [ ] All endpoints configured
- [ ] API key authentication enabled
- [ ] Request validation configured
- [ ] CORS settings applied
- [ ] Rate limiting configured

**Verification Commands:**
```bash
# Get API information
aws apigateway get-rest-apis --query "items[?name=='ai-ppt-assistant-api']"

# Test API endpoint
curl -X GET https://your-api-url/health \
  -H "x-api-key: your-api-key"
```

### 4. DynamoDB
- [ ] Table created with correct schema
- [ ] TTL enabled (30 days)
- [ ] On-demand billing mode set
- [ ] Point-in-time recovery enabled
- [ ] Encryption at rest enabled

**Verification Commands:**
```bash
# Describe table
aws dynamodb describe-table --table-name ai-ppt-assistant-presentations

# Check table status
aws dynamodb describe-table \
  --table-name ai-ppt-assistant-presentations \
  --query "Table.TableStatus"
```

### 5. S3 Buckets
- [ ] Presentation storage bucket created
- [ ] Agent configuration bucket created
- [ ] Encryption enabled
- [ ] Lifecycle policies configured
- [ ] CORS configured for presigned URLs
- [ ] Versioning enabled

**Verification Commands:**
```bash
# List buckets
aws s3 ls | grep ai-ppt-assistant

# Check bucket encryption
aws s3api get-bucket-encryption --bucket ai-ppt-assistant-presentations
```

### 6. SQS Queues
- [ ] Main processing queue created
- [ ] Dead letter queue created
- [ ] Redrive policy configured
- [ ] Message retention set
- [ ] Encryption enabled

**Verification Commands:**
```bash
# List queues
aws sqs list-queues --queue-name-prefix ai-ppt-assistant

# Get queue attributes
aws sqs get-queue-attributes \
  --queue-url https://sqs.region.amazonaws.com/account/ai-ppt-assistant-queue \
  --attribute-names All
```

### 7. Bedrock Agents
- [ ] Orchestrator Agent deployed
- [ ] Content Agent deployed
- [ ] Visual Agent deployed
- [ ] Compiler Agent deployed
- [ ] Agent instructions uploaded
- [ ] Action groups configured
- [ ] Model permissions granted

**Verification Commands:**
```bash
# List Bedrock agents
aws bedrock-agent list-agents \
  --query "agentSummaries[?contains(agentName, 'ai-ppt-assistant')]"

# Get agent details
aws bedrock-agent get-agent \
  --agent-id <agent-id>
```

### 8. Monitoring & Alarms
- [ ] CloudWatch log groups created
- [ ] CloudWatch dashboard configured
- [ ] Lambda error alarms set
- [ ] API Gateway 4xx/5xx alarms set
- [ ] DynamoDB throttle alarms set
- [ ] SQS DLQ alarms set

**Verification Commands:**
```bash
# List dashboards
aws cloudwatch list-dashboards --dashboard-name-prefix ai-ppt-assistant

# List alarms
aws cloudwatch describe-alarms --alarm-name-prefix ai-ppt-assistant
```

## ✅ Post-Deployment Verification

### Functional Tests
- [ ] Create a test presentation request
- [ ] Monitor status updates
- [ ] Download generated presentation
- [ ] Verify file integrity
- [ ] Test slide modification
- [ ] Check error handling

**Test Script:**
```bash
# Test presentation generation
curl -X POST https://api-url/presentations/generate \
  -H "Content-Type: application/json" \
  -H "x-api-key: your-api-key" \
  -d '{
    "topic": "Deployment Test Presentation",
    "slide_count": 5,
    "duration": 10
  }'

# Save the presentation_id and check status
presentation_id="returned-id"

# Check status
curl -X GET https://api-url/presentations/$presentation_id/status \
  -H "x-api-key: your-api-key"
```

### Performance Tests
- [ ] API response time < 500ms
- [ ] Lambda cold start < 3s
- [ ] Total generation time < 60s
- [ ] Concurrent request handling works
- [ ] Rate limiting works correctly

### Security Verification
- [ ] API key authentication required
- [ ] Invalid requests rejected
- [ ] Rate limiting enforced
- [ ] Encryption in transit verified
- [ ] Encryption at rest verified
- [ ] IAM permissions follow least privilege

## 🔄 Rollback Plan

If issues are encountered:

### Quick Rollback
```bash
cd infrastructure
terraform destroy -var-file="terraform.tfvars"
```

### Gradual Rollback
1. Disable API Gateway stage
2. Set Lambda concurrency to 0
3. Investigate issues
4. Fix and redeploy

## 📊 Success Criteria

The deployment is considered successful when:

- [ ] All infrastructure resources are created
- [ ] All Lambda functions are responding
- [ ] API endpoints are accessible
- [ ] Test presentation can be generated
- [ ] Monitoring shows no errors
- [ ] Performance meets requirements
- [ ] Security checks pass

## 🎯 Final Steps

1. **Documentation Review**
   - [ ] Update README with deployment details
   - [ ] Document any custom configurations
   - [ ] Update API documentation if needed

2. **Team Communication**
   - [ ] Notify team of deployment completion
   - [ ] Share API endpoints and keys
   - [ ] Schedule deployment review meeting

3. **Monitoring Setup**
   - [ ] Configure alert notifications
   - [ ] Set up on-call rotation
   - [ ] Create runbook for common issues

4. **Backup Configuration**
   - [ ] Enable DynamoDB backups
   - [ ] Configure S3 cross-region replication
   - [ ] Document disaster recovery plan

## 📝 Notes

**Deployment Date**: _______________  
**Deployed By**: _______________  
**Environment**: _______________  
**Version**: _______________  

**Issues Encountered**:
_________________________________
_________________________________
_________________________________

**Resolution**:
_________________________________
_________________________________
_________________________________

---

✅ **Sign-off**: I confirm that all items in this checklist have been completed and verified.

**Name**: _______________  
**Date**: _______________  
**Signature**: _______________