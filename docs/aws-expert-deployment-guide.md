# 🚀 AWS 专家级部署指南

## 概述
本指南基于 Context7 调研的 AWS 官方最佳实践，确保 AI PPT Assistant 项目的企业级稳定部署。

## ⚡ 快速部署检查清单

### 部署前必须检查 (5 分钟)
```bash
# 1. 运行 AWS 专家验证器
python scripts/aws_expert_deployment_validator.py

# 2. 验证 Terraform 配置
cd infrastructure && terraform validate

# 3. 检查 Python 版本兼容性
python --version  # 应该是 3.12.x 或使用 Docker

# 4. 验证 AWS 凭证
aws sts get-caller-identity

# 5. 检查关键文件存在
ls lambdas/layers/dist/ai-ppt-assistant-*.zip
ls infrastructure/sqs_lambda_mapping.tf
```

### 安全部署命令序列
```bash
# 1. 清理环境
make clean

# 2. 构建 Python 3.12 兼容层
make build-layers

# 3. 打包 Lambda 函数
make package-lambdas

# 4. 部署基础设施 
cd infrastructure && terraform apply

# 5. 验证部署结果
python ../test_all_apis.py
```

## 🔧 关键架构组件

### Lambda 层管理
**最佳实践**: 使用 Docker 确保精确的 Python 版本兼容性

```dockerfile
# 正确的 Dockerfile.layer 配置
FROM public.ecr.aws/lambda/python:3.12-arm64
RUN pip install --target /opt/python/lib/python3.12/site-packages \
    --platform linux_aarch64 \
    --python-version 3.12 \
    --only-binary=:all: \
    -r requirements.txt
```

### SQS 事件源映射
**关键文件**: `infrastructure/sqs_lambda_mapping.tf`

**必须配置**:
```hcl
resource "aws_lambda_event_source_mapping" "presentation_processor" {
  event_source_arn = aws_sqs_queue.task_queue.arn
  function_name    = "ai-ppt-assistant-api-generate-presentation"
  enabled          = true
  batch_size       = 1
  function_response_types = ["ReportBatchItemFailures"]
}
```

### IAM 权限配置
**必需权限**:
- `bedrock:InvokeModel` 
- `bedrock:InvokeAgent`
- `dynamodb:GetItem`, `dynamodb:PutItem`
- `sqs:ReceiveMessage`, `sqs:DeleteMessage`

## 🚨 常见问题和解决方案

### 1. Python 依赖兼容性错误
**症状**: `No module named 'pydantic_core._pydantic_core'`

**根本原因**: Lambda 层使用错误的 Python 版本构建

**解决方案**:
```bash
# 自动修复
python scripts/aws_expert_auto_fixer.py

# 手动修复
cd lambdas/layers
./build.sh --docker  # 确保 Python 3.12
cd ../../infrastructure
terraform apply -replace=module.lambda.aws_lambda_layer_version.content_dependencies
```

### 2. SQS 事件源映射缺失
**症状**: 任务永远停留在 "pending" 状态

**根本原因**: 缺少 SQS 到 Lambda 的事件源映射

**解决方案**:
```bash
# 检查映射状态
aws lambda list-event-source-mappings --region us-east-1

# 自动创建映射
python scripts/aws_expert_auto_fixer.py
```

### 3. IAM 权限不足
**症状**: AccessDeniedException 错误

**解决方案**:
```bash
# 检查 IAM 角色
aws iam get-role --role-name ai-ppt-assistant-lambda-execution-role

# 更新权限策略
terraform apply -target=module.lambda.aws_iam_policy.lambda_policy
```

## 📊 监控和验证

### 健康检查命令
```bash
# API 端点测试
curl -H "x-api-key: YOUR_API_KEY" \
     "https://YOUR_API_GATEWAY_URL/legacy/health"

# Lambda 函数状态
aws lambda list-functions --query \
    "Functions[?contains(FunctionName,'ai-ppt-assistant')].{Name:FunctionName,State:State}"

# SQS 队列状态  
aws sqs get-queue-attributes \
    --queue-url "https://sqs.us-east-1.amazonaws.com/375004070918/ai-ppt-assistant-dev-tasks" \
    --attribute-names ApproximateNumberOfMessages
```

### CloudWatch 监控仪表板
- **URL**: https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=ai-ppt-assistant-dev-dashboard
- **关键指标**: Lambda 错误率、API Gateway 延迟、DynamoDB 节流

## 🎯 预防措施

### 1. 部署前自动验证
将以下命令添加到 CI/CD 流程：
```bash
# 强制部署前验证
python scripts/aws_expert_deployment_validator.py || exit 1
```

### 2. Makefile 最佳实践
```makefile
# 添加到 Makefile
validate-deploy: 
	@python scripts/aws_expert_deployment_validator.py
	@echo "✅ 部署验证通过"

safe-deploy: validate-deploy build-layers package-lambdas tf-apply
	@echo "✅ 安全部署完成"
```

### 3. Git Pre-commit Hooks
```bash
# .git/hooks/pre-commit
#!/bin/bash
python scripts/aws_expert_deployment_validator.py
```

## 📈 性能优化建议

### Lambda 函数优化
- **内存配置**: API函数512MB，处理函数1536-2048MB
- **预置并发**: 为高频API函数配置预置并发
- **层优化**: 最小化层大小，分离核心依赖

### 成本优化
- **ARM64 架构**: 使用 Graviton2 处理器降低成本
- **按需扩展**: 配置合理的超时和内存限制
- **监控优化**: 设置精确的告警阈值

## 🔒 安全最佳实践

### IAM 最小权限原则
- 为每个组件配置最小必需权限
- 定期审查和更新权限策略
- 使用资源级权限而非通配符

### 加密和访问控制
- S3 桶启用服务端加密
- API Gateway 启用请求验证
- CloudWatch 日志加密

## 🎊 成功部署验证

### 验收标准
- [ ] API 端点 100% 测试通过
- [ ] 后台处理链路正常工作
- [ ] 监控告警全部配置
- [ ] 文档和日志完整

### 部署后验证命令
```bash
# 运行完整测试套件
python test_all_apis.py

# 检查系统健康状态
python scripts/aws_expert_deployment_validator.py

# 验证端到端功能
# 创建测试任务 → 等待处理 → 验证状态更新
```

## 📞 故障排除

### 紧急修复流程
1. **立即诊断**: `python scripts/aws_expert_deployment_validator.py`
2. **自动修复**: `python scripts/aws_expert_auto_fixer.py`  
3. **手动干预**: 参考本指南的具体解决方案
4. **验证修复**: 重新运行验证和测试

### 联系支持
- **技术文档**: 本仓库 docs/ 目录
- **监控仪表板**: CloudWatch Dashboard
- **日志查看**: CloudWatch Logs

---

## ✅ 质量保证

遵循本指南，您的部署将达到：
- **🔒 安全性**: AWS 专家级权限配置
- **⚡ 性能**: 优化的资源配置和监控
- **🔧 可维护性**: 完整的自动化工具链
- **📊 可观察性**: 全面的监控和告警

**部署成功率预期**: 95-99%

---
*创建时间: 2025-09-09*  
*基于: AWS 官方最佳实践 + Context7 技术调研*  
*维护: AWS 专家团队*