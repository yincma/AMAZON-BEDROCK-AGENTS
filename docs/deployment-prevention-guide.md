# AI PPT Assistant - 部署问题预防指南

## 文档信息
- **创建时间**: 2025-09-08
- **作者**: Claude Code Assistant
- **版本**: 1.0
- **目的**: 防止部署问题再次发生的最佳实践指南

## 已解决的问题总结

### 1. Bedrock IAM权限配置错误 ✅ 已解决 (2025-09-08)
**问题描述**:
- Bedrock Agent调用失败，返回`AccessDeniedException`
- 错误信息: `User is not authorized to perform: bedrock:InvokeAgent on resource: arn:aws:bedrock:us-east-1:375004070918:agent-alias/LA1D127LSK/PSQBDUP6KR`

**根本原因**:
- IAM策略中的Resource ARN格式不完整
- 缺少对agent-alias资源的显式权限

**解决方案**:
```hcl
# infrastructure/modules/lambda/main.tf
{
  Effect = "Allow"
  Action = [
    "bedrock:InvokeAgent"
  ]
  Resource = [
    "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent/*",
    "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:agent-alias/*/*"
  ]
}
```

### 2. Bedrock模型ID无效 ✅ 已解决 (2025-09-08)
**问题描述**:
- Lambda函数调用Bedrock时返回`ValidationException`
- 错误信息: `The provided model identifier is invalid`
- 所有演示文稿卡在pending状态超过13小时

**根本原因**:
- 使用了无效的模型ID: `anthropic.claude-4-0`
- Claude 4.0尚未发布，应使用现有的3.5版本

**解决方案**:
```hcl
# infrastructure/variables.tf
variable "bedrock_model_id" {
  description = "Bedrock model ID"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}
```

```python
# lambdas/utils/enhanced_config_manager.py
@dataclass
class BedrockConfig:
    model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    nova_model_id: str = "amazon.nova-canvas-v1:0"
```

### 3. Lambda层依赖缺失问题 ✅ 已解决
**问题描述**: 
- 6个控制器函数缺少pydantic等关键依赖
- 导致所有核心PPT生成功能无法使用

**根本原因**:
- requirements.txt文件缺少pydantic依赖
- Lambda层构建过程未包含所有必需的依赖项

**解决方案**:
1. 更新requirements.txt添加pydantic==2.9.2和pydantic-core==2.23.4
2. 重新构建Lambda层并部署到AWS
3. 更新所有Lambda函数使用新的层版本

### 2. API Gateway 403 Forbidden错误 ⚠️ 部分解决
**问题描述**:
- 所有API端点返回403错误
- 前端完全无法访问后端服务

**根本原因**:
- API Gateway缺少有效的部署
- Lambda集成配置不完整
- API密钥使用计划未正确配置

**解决方案**:
1. 导入已存在的API Gateway资源到Terraform状态
2. 修复Lambda集成配置
3. 创建新的API部署

### 3. Terraform资源冲突 ✅ 已解决
**问题描述**:
- API Gateway模型和Request Validator名称冲突
- Lambda预留并发配置错误

**根本原因**:
- 增量部署导致资源已存在但未在Terraform状态中
- 预留并发需要发布的Lambda版本而非$LATEST

**解决方案**:
1. 使用terraform import导入已存在的资源
2. 注释掉预留并发配置，待创建发布版本后再启用

## 预防措施和最佳实践

### 1. Bedrock配置最佳实践

#### 1.1 模型ID验证
```bash
# 部署前验证模型可用性
aws bedrock list-foundation-models \
  --region us-east-1 \
  --query "modelSummaries[?contains(modelId, 'claude')].[modelId,modelName]" \
  --output table

# 测试模型调用
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --body '{"anthropic_version": "bedrock-2023-05-31", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 100}' \
  --cli-binary-format raw-in-base64-out \
  --region us-east-1 \
  output.json
```

#### 1.2 IAM权限验证
```bash
# 验证IAM角色权限
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ai-ppt-assistant-lambda-role \
  --action-names bedrock:InvokeModel bedrock:InvokeAgent \
  --resource-arns "arn:aws:bedrock:us-east-1:*:*"
```

#### 1.3 Agent配置检查
```bash
# 列出所有Bedrock Agents
aws bedrock list-agents --region us-east-1

# 获取特定Agent详情
aws bedrock get-agent \
  --agent-id <agent-id> \
  --region us-east-1

# 列出Agent别名
aws bedrock list-agent-aliases \
  --agent-id <agent-id> \
  --region us-east-1
```

### 2. 依赖管理最佳实践

#### 1.1 Lambda层构建流程
```bash
# 推荐的构建流程
cd lambdas/layers

# 1. 更新requirements.txt前先备份
cp requirements.txt requirements.txt.backup

# 2. 使用Docker构建以确保兼容性
make build-docker

# 3. 验证层内容
make verify

# 4. 部署前测试
make test

# 5. 部署到AWS
make deploy-layer
```

#### 1.2 依赖版本管理
- **始终指定精确版本**：避免使用>=或~=
- **定期更新依赖**：每月检查并更新依赖版本
- **测试兼容性**：更新前在开发环境充分测试

### 2. Terraform部署最佳实践

#### 2.1 状态管理
```bash
# 部署前检查
terraform init -upgrade
terraform plan -out=tfplan

# 查看计划详情
terraform show tfplan

# 应用计划
terraform apply tfplan
```

#### 2.2 资源导入流程
```bash
# 当遇到资源已存在错误时
# 1. 获取资源ID
aws apigateway get-models --rest-api-id <api-id> --query "items[].id"

# 2. 导入到Terraform状态
terraform import <resource_type>.<resource_name> <resource_id>

# 3. 验证导入
terraform plan
```

### 3. API Gateway部署最佳实践

#### 3.1 部署前检查清单
- [ ] 所有方法都有有效的集成
- [ ] Lambda权限已正确配置
- [ ] API密钥和使用计划已关联
- [ ] CORS配置正确
- [ ] 错误响应模型已定义

#### 3.2 部署脚本
```python
# 安全的部署脚本示例
import boto3

def safe_deploy_api(api_id, stage_name):
    client = boto3.client('apigateway')
    
    # 1. 验证所有资源和方法
    resources = client.get_resources(restApiId=api_id)
    for resource in resources['items']:
        if 'resourceMethods' in resource:
            for method in resource['resourceMethods']:
                # 检查集成是否存在
                try:
                    client.get_integration(
                        restApiId=api_id,
                        resourceId=resource['id'],
                        httpMethod=method
                    )
                except:
                    print(f"Missing integration: {resource['path']} {method}")
                    return False
    
    # 2. 创建部署
    response = client.create_deployment(
        restApiId=api_id,
        stageName=stage_name
    )
    return response['id']
```

### 4. 监控和告警配置

#### 4.1 关键指标监控
```terraform
# CloudWatch告警配置
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "lambda-function-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors lambda errors"
}
```

#### 4.2 日志聚合
```bash
# 查看Lambda日志
aws logs tail /aws/lambda/<function-name> --follow

# 搜索错误
aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --filter-pattern "ERROR"
```

### 5. 部署前检查清单

#### 5.1 代码检查
- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 代码审查完成
- [ ] 安全扫描通过

#### 5.2 依赖检查
- [ ] requirements.txt包含所有必需依赖
- [ ] Lambda层已构建并测试
- [ ] 层大小在限制内（<250MB解压后）

#### 5.3 基础设施检查
- [ ] Terraform plan无错误
- [ ] 资源命名符合规范
- [ ] 标签正确设置
- [ ] IAM权限最小化

#### 5.4 部署后验证
- [ ] API端点可访问
- [ ] Lambda函数无错误
- [ ] 监控指标正常
- [ ] 日志记录正常

### 6. 回滚策略

#### 6.1 快速回滚流程
```bash
# 1. 保存当前状态
terraform state pull > terraform.state.backup

# 2. 回滚到上一个版本
git checkout <previous-commit>
terraform apply

# 3. 验证回滚
./validate_deployment.sh
```

#### 6.2 Lambda版本管理
```bash
# 创建版本别名
aws lambda publish-version \
  --function-name <function-name> \
  --description "Stable version before deployment"

# 创建别名指向稳定版本
aws lambda create-alias \
  --function-name <function-name> \
  --name STABLE \
  --function-version <version-number>
```

### 7. 自动化测试脚本

#### 7.1 部署后自动测试
```bash
#!/bin/bash
# post_deployment_test.sh

API_URL="https://your-api.execute-api.region.amazonaws.com/stage"
API_KEY="your-api-key"

# 测试健康检查
echo "Testing health endpoint..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "x-api-key: $API_KEY" \
  "$API_URL/health")

if [ "$response" -eq 200 ]; then
  echo "✅ Health check passed"
else
  echo "❌ Health check failed with status: $response"
  exit 1
fi

# 测试其他端点...
```

### 8. 文档维护

#### 8.1 必需文档清单
- [ ] API文档（OpenAPI/Swagger）
- [ ] 部署指南
- [ ] 故障排除指南
- [ ] 架构图
- [ ] 数据流图

#### 8.2 文档更新流程
1. 每次部署后更新版本号
2. 记录所有配置更改
3. 更新依赖列表
4. 记录已知问题和解决方案

## 紧急联系和资源

### 支持资源
- AWS Support: https://console.aws.amazon.com/support
- CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home#logs
- Lambda Console: https://console.aws.amazon.com/lambda
- API Gateway Console: https://console.aws.amazon.com/apigateway

### 故障排除命令
```bash
# 查看Lambda函数配置
aws lambda get-function --function-name <name>

# 查看最近的日志
aws logs tail /aws/lambda/<function-name> --since 1h

# 查看API Gateway配置
aws apigateway get-rest-api --rest-api-id <api-id>

# 测试Lambda函数
aws lambda invoke --function-name <name> \
  --payload '{"test": true}' \
  response.json
```

## 总结

通过实施这些预防措施和最佳实践，可以显著减少部署问题的发生：

1. **依赖管理**：始终使用Docker构建Lambda层，确保环境一致性
2. **状态管理**：使用Terraform import处理已存在的资源
3. **部署验证**：每次部署后运行自动化测试
4. **监控告警**：配置全面的监控和告警系统
5. **文档维护**：保持文档与代码同步更新

记住：**预防胜于治疗**。花时间建立良好的部署流程和测试机制，可以节省大量的故障排除时间。

---
*最后更新: 2025-09-08*
*下次审查: 2025-10-08*