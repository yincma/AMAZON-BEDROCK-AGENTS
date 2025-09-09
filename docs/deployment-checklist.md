# 📋 部署前检查清单 - AI PPT Assistant

## 概览
本文档提供部署前的完整检查清单，确保每次部署都能顺利进行。基于历史问题分析，成功率预期为 85-90%。

## 🔍 部署前必查项目

### 1. 环境准备检查 ✅

#### Python 版本兼容性
```bash
# 检查本地Python版本
python --version  # 应该是 3.12.x

# 如果版本不匹配，使用Docker构建Lambda层
cd lambdas/layers
./docker-build.sh  # 使用Python 3.12容器环境
```

#### AWS CLI 配置
```bash
# 验证AWS凭证
aws sts get-caller-identity

# 检查默认区域
aws configure get region  # 应该是 us-east-1
```

### 2. Terraform 状态检查 ✅

```bash
cd infrastructure

# 初始化Terraform（必须执行）
terraform init

# 验证配置
terraform validate

# 检查计划（不要跳过这一步）
terraform plan -out=tfplan

# 检查资源数量
terraform state list | wc -l  # 当前应该是221个资源
```

### 3. AWS 服务配额检查 ✅

```bash
# 检查Lambda并发限制
aws lambda get-account-settings --query AccountLimit.UnreservedConcurrentExecutions

# 检查现有Lambda函数数量
aws lambda list-functions --query 'length(Functions)'

# 检查S3存储桶配额
aws s3 ls | wc -l

# 检查DynamoDB表数量
aws dynamodb list-tables --query 'length(TableNames)'
```

### 4. Bedrock Agent 状态验证 ✅

```bash
# 运行Bedrock权限测试脚本
python scripts/test_bedrock_permissions.py

# 期望输出：
# - Orchestrator Agent: PREPARED
# - Content Agent: PREPARED  
# - Visual Agent: PREPARED
# - Compiler Agent: PREPARED
```

### 5. 依赖包版本检查 ✅

```bash
# 检查requirements.txt中的版本
cat lambdas/layers/requirements.txt | grep -E "aws-lambda-powertools|boto3|pydantic"

# 确保版本：
# - aws-lambda-powertools==2.38.0 (不要使用2.39.0)
# - boto3==1.35.0
# - pydantic==2.9.2
```

### 6. API Gateway 配置验证 ✅

```bash
# 检查API路由完整性
grep -r "presentation_download" infrastructure/modules/api_gateway/
# 应该找到资源、方法和CORS配置

# 验证Lambda集成
grep -r "download_presentation" infrastructure/main.tf
# 应该找到integration和permission配置
```

## 🚀 部署执行步骤

### 步骤 1: 备份当前状态
```bash
# 备份Terraform状态
cp infrastructure/terraform.tfstate infrastructure/terraform.tfstate.backup.$(date +%Y%m%d_%H%M%S)

# 导出当前配置
cd infrastructure && terraform output -json > current_outputs.json
```

### 步骤 2: 执行部署
```bash
# 使用Makefile部署（推荐）
make deploy

# 或手动部署
cd infrastructure
terraform apply tfplan
```

### 步骤 3: 部署后验证
```bash
# 运行API测试套件
python test_all_apis.py

# 检查所有端点（期望100%通过率）
# - POST /presentations
# - GET /presentations
# - GET /presentations/{id}
# - GET /presentations/{id}/download
# - POST /sessions
# - GET /sessions/{id}
# - POST /agents/{name}/execute
```

### 步骤 4: 监控检查
```bash
# 检查Lambda错误日志
aws logs tail /aws/lambda/ai-ppt-assistant-dev --follow --since 5m

# 检查API Gateway日志
aws logs tail API-Gateway-Execution-Logs_$(cd infrastructure && terraform output -raw api_gateway_id)/legacy --follow --since 5m
```

## ⚠️ 常见问题快速修复

### 问题 1: Lambda函数已存在错误
```bash
# 导入现有函数到Terraform状态
cd infrastructure
terraform import module.lambda.aws_lambda_function.<function_name> <aws_function_name>
```

### 问题 2: API Gateway路由缺失
```bash
# 强制重新部署API Gateway
cd infrastructure
terraform apply -target=module.api_gateway -auto-approve
terraform apply -target=aws_api_gateway_deployment.main -auto-approve
```

### 问题 3: Bedrock权限错误
```bash
# 更新Lambda执行角色
cd infrastructure
terraform apply -target=module.lambda.aws_iam_role_policy.lambda_policy -auto-approve
```

### 问题 4: Python包版本冲突
```bash
# 使用Docker重建Lambda层
cd lambdas/layers
docker run --rm -v "$PWD":/var/task public.ecr.aws/sam/build-python3.12:latest \
  pip install -r requirements.txt -t python/lib/python3.12/site-packages/
zip -r lambda-layer.zip python/
```

### 问题 5: API Gateway下载路由404错误
```bash
# 检查路径参数兼容性
# Lambda函数应同时支持 'id' 和 'presentationId'
grep "path_params.get" lambdas/api/presentation_download.py
# 应该看到: presentation_id = path_params.get("id") or path_params.get("presentationId")
```

## 📊 部署风险评估

| 风险项 | 概率 | 影响 | 缓解措施 |
|--------|------|------|----------|
| Python版本不兼容 | 中 | 高 | 使用Docker构建 |
| Terraform状态冲突 | 低 | 高 | 备份状态文件 |
| AWS配额限制 | 低 | 中 | 提前检查配额 |
| Bedrock Agent未准备 | 低 | 高 | 验证Agent状态 |
| 网络连接问题 | 低 | 中 | 使用稳定网络 |
| API路由配置错误 | 低 | 高 | 运行完整测试套件 |

## 🎯 成功标准

部署成功的标志：
- [ ] 所有Terraform资源成功创建/更新
- [ ] API测试套件100%通过
- [ ] CloudWatch无错误日志
- [ ] Bedrock Agents状态为PREPARED
- [ ] 可以成功创建并下载演示文稿

## 📝 部署记录模板

```markdown
## 部署记录 - [日期]

**部署人员**: [姓名]
**开始时间**: [时间]
**结束时间**: [时间]

### 部署前检查
- [ ] Python版本: 3.12.x
- [ ] Terraform初始化: 完成
- [ ] 配额检查: 通过
- [ ] Bedrock状态: PREPARED

### 部署结果
- [ ] Terraform Apply: 成功
- [ ] API测试: 100%通过
- [ ] 监控状态: 正常

### 问题记录
[记录任何遇到的问题和解决方案]

### 备注
[其他相关信息]
```

## 🔧 自动化脚本

创建 `scripts/pre_deploy_check.sh`:
```bash
#!/bin/bash
echo "🔍 执行部署前检查..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Python版本
python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$python_version" != "3.12" ]; then
    echo -e "${YELLOW}⚠️  警告: Python版本不是3.12，建议使用Docker构建${NC}"
fi

# 检查AWS凭证
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ 错误: AWS凭证未配置${NC}"
    exit 1
fi

# 检查Terraform
cd infrastructure
if ! terraform validate > /dev/null 2>&1; then
    echo -e "${RED}❌ 错误: Terraform配置验证失败${NC}"
    exit 1
fi

# 检查API Gateway路由配置
if ! grep -q "presentation_download" modules/api_gateway/main.tf; then
    echo -e "${YELLOW}⚠️  警告: 下载路由可能未配置${NC}"
fi

# 检查Bedrock权限
if ! grep -q "bedrock:GetAgent" modules/lambda/main.tf; then
    echo -e "${YELLOW}⚠️  警告: Bedrock权限可能不完整${NC}"
fi

echo -e "${GREEN}✅ 部署前检查完成${NC}"
```

## 📈 历史问题总结

### 2025-09-09 解决的问题
1. **Bedrock权限问题**: Lambda缺少GetAgent权限
   - 解决方案: 在IAM策略中添加完整权限集
   
2. **API Gateway下载路由缺失**: /presentations/{id}/download返回403
   - 解决方案: 添加完整的路由配置和Lambda集成

3. **路径参数不兼容**: Lambda期望presentationId但收到id
   - 解决方案: 修改Lambda支持两种参数名

### 2025-09-08 解决的问题
1. **Python包版本问题**: aws-lambda-powertools 2.39.0被撤回
   - 解决方案: 锁定版本到2.38.0

2. **Terraform状态冲突**: Lambda函数存在但不在状态中
   - 解决方案: 使用terraform import导入

## 📞 支持联系

如遇到未列出的问题，请联系：
- **技术支持**: AWS Support
- **项目维护者**: ultrathink
- **文档更新**: 请提交PR到项目仓库

## 🔄 更新日志

- **2025-09-09**: 添加Bedrock权限和API路由检查
- **2025-09-08**: 初始版本，包含基础检查项

---
*最后更新: 2025-09-09*
*版本: 2.0*
*维护者: ultrathink*