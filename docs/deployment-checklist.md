# 部署检查清单 - 避免重复问题

## 🔍 部署前检查

### 1. Terraform状态同步
```bash
# 在部署前始终执行
cd infrastructure
terraform refresh
terraform plan
```

### 2. 依赖版本锁定
- ✅ `lambdas/layers/requirements.txt` 中已锁定 `aws-lambda-powertools==2.38.0`
- ⚠️ 避免使用 `latest` 或未锁定的版本

### 3. Python版本兼容性
- **本地开发**: Python 3.13
- **Lambda运行时**: Python 3.12
- **解决方案**: 使用Docker构建Lambda层以确保兼容性

## 🚀 标准部署流程

### 步骤1: 清理和准备
```bash
make clean
```

### 步骤2: 构建Lambda层
```bash
cd lambdas/layers
./build.sh  # 使用本地Python
# 或
./docker-build.sh  # 使用Docker（推荐）
```

### 步骤3: Terraform部署
```bash
cd infrastructure
terraform init -upgrade  # 如果需要更新providers
terraform refresh        # 同步状态
terraform plan          # 检查变更
terraform apply         # 应用变更
```

### 步骤4: 验证部署
```bash
# 检查Lambda函数
aws lambda list-functions --region us-east-1 | grep ai-ppt-assistant

# 测试API端点
curl -X GET https://1mivrhr3w7.execute-api.us-east-1.amazonaws.com/legacy/health \
  -H "x-api-key: $(terraform output -raw api_gateway_api_key)"
```

## ⚠️ 常见问题预防

### 问题1: Terraform状态不同步
**预防措施**:
- 使用远程状态后端（S3 + DynamoDB）
- 定期执行 `terraform refresh`
- 团队协作时使用状态锁

### 问题2: API Gateway资源冲突
**预防措施**:
- 不要手动在AWS控制台修改Terraform管理的资源
- 如果必须手动修改，记得导入到Terraform状态：
```bash
terraform import <resource_type>.<resource_name> <aws_resource_id>
```

### 问题3: Lambda层版本问题
**预防措施**:
- 在 `requirements.txt` 中明确指定版本号
- 定期检查依赖更新但谨慎升级
- 使用 `pip freeze > requirements.lock` 锁定所有依赖版本

### 问题4: 请求验证失败
**预防措施**:
- API Gateway模型定义要与Lambda函数期望的输入格式一致
- 使用最小化的必填字段（如只要求title和topic）
- 在Lambda函数中进行额外的验证而不是在API Gateway

## 📋 部署后验证清单

- [ ] 所有Lambda函数部署成功
- [ ] API Gateway端点可访问
- [ ] CloudWatch日志组创建完成
- [ ] 监控警报配置正确
- [ ] API文档站点可访问
- [ ] 测试创建演示文稿功能
- [ ] 测试列出演示文稿功能

## 🔧 故障排查命令

### 查看Lambda函数日志
```bash
aws logs tail /aws/lambda/ai-ppt-assistant-api-generate-presentation --follow
```

### 查看API Gateway日志
```bash
aws logs tail /aws/apigateway/ai-ppt-assistant-dev-stage --follow
```

### 检查DynamoDB表
```bash
aws dynamodb scan --table-name ai-ppt-assistant-dev-sessions --max-items 1
```

### 检查SQS队列
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/375004070918/ai-ppt-assistant-dev-tasks \
  --attribute-names All
```

## 📝 维护建议

1. **定期备份Terraform状态**
   ```bash
   cp terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d)
   ```

2. **使用Terraform工作空间**
   ```bash
   terraform workspace new dev
   terraform workspace new staging
   terraform workspace new prod
   ```

3. **实施CI/CD流程**
   - 使用GitHub Actions或Jenkins
   - 自动运行 `terraform plan` 在PR中
   - 仅在合并到主分支后执行 `terraform apply`

4. **监控和告警**
   - 定期检查CloudWatch Dashboard
   - 设置关键指标的告警阈值
   - 配置SNS通知到团队邮箱

---
*最后更新: 2025-09-08*
*维护者: DevOps Team*
