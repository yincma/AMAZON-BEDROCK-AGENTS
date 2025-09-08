# 🚀 AI PPT Assistant 部署指南

## 📋 部署前准备

### 1. 验证Bedrock Agent配置
```bash
# 获取当前Agent ID
python3 scripts/get_agent_ids.py

# 如果Agent ID发生变化，更新 infrastructure/main.tf:214-215
```

### 2. 检查依赖
```bash
# 确保所有必要的工具都已安装
terraform --version
aws --version
python3 --version
```

## 🔧 标准部署流程

### 步骤1: 打包Lambda函数
```bash
make package-lambdas
```

### 步骤2: 部署基础设施
```bash
cd infrastructure
terraform plan  # 检查变更
terraform apply  # 应用变更
```

### 步骤3: 等待权限传播 
```bash
echo "等待IAM权限传播..." 
sleep 120  # 等待2分钟
```

### 步骤4: 验证部署
```bash
python3 test_all_apis.py
```

## 🚨 常见问题排查

### 问题1: Agent权限错误
**现象**: `AccessDeniedException: bedrock:InvokeAgent`
**解决**: 等待2-3分钟后重试，或检查IAM策略

### 问题2: Agent ID无效
**现象**: `ValidationException: agentId failed to satisfy constraint`
**解决**: 运行 `python3 scripts/get_agent_ids.py` 更新ID

### 问题3: 路由错误  
**现象**: 404或路由到错误的处理函数
**解决**: 检查API Gateway资源配置

## ✅ 部署验证清单

- [ ] 所有6个API测试通过
- [ ] CloudWatch日志没有错误
- [ ] DynamoDB表可以正常读写
- [ ] S3存储桶访问正常

## 🔄 回滚策略

如果部署失败：
```bash
# 回滚到上一个版本
git checkout HEAD~1
make package-lambdas  
terraform apply

# 或使用Terraform历史状态
terraform show terraform.tfstate.backup
```

## 📊 成功指标

- API测试通过率: **≥83.3%** (5/6测试通过)
- 响应时间: **<2秒**
- 错误率: **<5%**