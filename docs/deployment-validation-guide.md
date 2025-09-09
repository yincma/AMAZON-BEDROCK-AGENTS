# AI PPT Assistant - 部署验证指南

## 概述

本指南介绍了为防止常见部署问题而创建的自动化验证工具。这些工具基于 2025-09-09 修复的关键问题开发，能够主动检测和预防：

1. **Lambda权限不足问题**
2. **Bedrock Agent ID配置错误**  
3. **Lambda依赖打包缺失**
4. **系统健康状态异常**

## 验证工具

### 1. 预部署验证脚本

**文件位置**: `scripts/pre_deploy_validator.sh`

**功能**: 在部署前快速检查关键配置，防止常见错误

**使用方法**:
```bash
# 基础检查
./scripts/pre_deploy_validator.sh

# 自动修复模式
./scripts/pre_deploy_validator.sh --fix

# 指定区域
./scripts/pre_deploy_validator.sh --region us-west-2
```

**检查项目**:
- ✅ 必需工具和AWS认证
- ✅ 项目结构完整性
- ✅ Bedrock Agent配置
- ✅ Lambda依赖打包
- ✅ Terraform状态

### 2. 部署健康验证器

**文件位置**: `scripts/deployment_health_validator.py`

**功能**: 深度验证部署状态，包括AWS资源检查

**使用方法**:
```bash
# 完整健康检查
python3 scripts/deployment_health_validator.py

# 自动修复模式
python3 scripts/deployment_health_validator.py --fix

# 指定项目和区域
python3 scripts/deployment_health_validator.py --project my-project --region us-west-2
```

**验证功能**:
- 🔍 IAM权限策略验证
- 🔍 Bedrock Agent状态检查
- 🔍 Lambda函数配置验证
- 🔍 环境变量匹配检查
- 🔧 自动生成修复脚本

## Makefile集成

### 新增命令

```bash
# 预部署检查
make pre-deploy-check

# 完整健康检查
make deployment-health-check

# 自动修复
make deployment-health-fix

# 安全部署（包含全面验证）
make deploy-safe
```

### 更新的部署流程

现在所有部署命令都会自动进行预部署验证：

```bash
# 标准部署（现在包含预检查）
make deploy

# 遗留部署（现在包含预检查）
make deploy-legacy

# 推荐：最安全的部署方式
make deploy-safe
```

## 常见问题修复

### 1. Agent ID不匹配

**问题症状**:
```
[ERROR] 函数 ai-ppt-assistant-api-generate-presentation 的ORCHESTRATOR_AGENT_ID不匹配
```

**自动修复**:
```bash
make deployment-health-fix
```

**手动修复**:
```bash
# 生成同步脚本
python3 scripts/deployment_health_validator.py --fix
# 运行生成的脚本
./scripts/sync_agent_ids.sh
```

### 2. Lambda依赖缺失

**问题症状**:
```
[ERROR] Runtime.ImportModuleError: No module named 'utils'
```

**自动修复**:
```bash
make package-lambdas
```

**验证修复**:
```bash
unzip -l lambdas/api/generate_presentation.zip | grep utils/
```

### 3. 权限不足

**问题症状**:
```
[ERROR] Access denied when calling Bedrock
[ERROR] User is not authorized to perform: dynamodb:PutItem
```

**检查权限**:
```bash
python3 scripts/deployment_health_validator.py
```

**手动修复**:
1. 检查 IAM 角色: `ai-ppt-assistant-lambda-execution-role`
2. 验证附加策略包含所需权限
3. 重新部署 Terraform 配置

## 最佳实践

### 1. 部署前检查

**始终**在部署前运行验证：
```bash
make pre-deploy-check
```

### 2. 使用安全部署

对于生产环境，使用：
```bash
make deploy-safe
```

### 3. 定期健康检查

定期运行健康检查：
```bash
make deployment-health-check
```

### 4. 监控部署报告

检查生成的报告文件：
- `pre_deploy_report_*.json`
- 查看错误和警告数量
- 跟踪修复历史

## 故障排除

### 验证脚本失败

1. **检查AWS认证**:
   ```bash
   aws sts get-caller-identity
   ```

2. **检查区域设置**:
   ```bash
   echo $AWS_DEFAULT_REGION
   ```

3. **检查工具版本**:
   ```bash
   aws --version
   terraform --version
   python3 --version
   ```

### Agent配置问题

1. **列出现有Agents**:
   ```bash
   aws bedrock-agent list-agents --region us-east-1
   ```

2. **检查Terraform状态**:
   ```bash
   cd infrastructure
   terraform show | grep agent_id
   ```

### Lambda函数问题

1. **检查函数状态**:
   ```bash
   aws lambda list-functions --query 'Functions[?contains(FunctionName, `ai-ppt-assistant`)]'
   ```

2. **查看日志**:
   ```bash
   aws logs describe-log-groups --log-group-name-prefix '/aws/lambda/ai-ppt-assistant'
   ```

## 支持

如果遇到问题：

1. 查看生成的报告文件中的详细错误信息
2. 运行 `make deployment-health-fix` 尝试自动修复
3. 检查 CloudWatch 日志获取运行时错误
4. 参考原始问题报告: `docs/reports/问题报告.md`

---

**创建时间**: 2025-09-09  
**版本**: 1.0  
**维护者**: AWS Expert & Claude Code