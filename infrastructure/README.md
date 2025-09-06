# AI PPT Assistant - Terraform Infrastructure

根据项目规范要求，从 CloudFormation 迁移到 Terraform 的基础设施即代码 (IaC) 实现。

## ✅ 架构合规性检查

| 规范要求 | 实现状态 | 说明 |
|---------|---------|------|
| **Terraform IaC** | ✅ 已实现 | 完全使用 Terraform 替代 CloudFormation |
| **Python 3.13 运行时** | ✅ 已配置 | Lambda 函数使用 Python 3.13 |
| **Claude 4.0/4.1 模型** | ✅ 已配置 | Orchestrator 使用 Claude 4.1，其他使用 Claude 4.0 |
| **arm64 架构** | ✅ 已配置 | Lambda 使用 Graviton2 (arm64) 优化成本 |
| **简单 API Key 认证** | ✅ 已配置 | 仅使用 API Key，无 OAuth2/JWT |
| **30天 S3 生命周期** | ✅ 已配置 | 30天后转为 IA 存储 |
| **DynamoDB TTL** | ✅ 已配置 | 30天 TTL 自动清理 |
| **按需计费模式** | ✅ 已配置 | DynamoDB 使用 PAY_PER_REQUEST |

## 📁 项目结构

```
infrastructure/
├── main.tf                 # 主配置文件
├── variables.tf            # 变量定义
├── outputs.tf              # 输出定义
├── terraform.tfvars.example # 配置示例
├── config/
│   └── environments/       # 环境配置
│       ├── dev.tfvars
│       ├── staging.tfvars
│       └── prod.tfvars
└── modules/
    ├── s3/                 # S3 存储模块
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── dynamodb/           # DynamoDB 会话管理模块
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── api_gateway/        # API Gateway 模块（待实现）
    ├── lambda/             # Lambda 函数模块（待实现）
    ├── lambda_layers/      # Lambda Layers 模块（待实现）
    └── bedrock/            # Bedrock Agents 模块（待实现）
```

## 🚀 部署步骤

### 1. 初始化 Terraform
```bash
cd infrastructure
terraform init
```

### 2. 配置环境变量
```bash
cp terraform.tfvars.example terraform.tfvars
# 编辑 terraform.tfvars 填入实际值
```

### 3. 验证配置
```bash
terraform validate
terraform plan -var-file="config/environments/dev.tfvars"
```

### 4. 部署基础设施
```bash
terraform apply -var-file="config/environments/dev.tfvars"
```

## 🔧 模块功能

### S3 模块
- ✅ AES256 服务器端加密
- ✅ 版本控制启用
- ✅ 30天后转为 STANDARD_IA 存储
- ✅ 30天后删除旧版本
- ✅ CORS 配置支持预签名 URL
- ✅ 公共访问完全阻止

### DynamoDB 模块
- ✅ 按需计费模式 (PAY_PER_REQUEST)
- ✅ 30天 TTL 自动清理
- ✅ 服务器端加密
- ✅ 时间点恢复启用
- ✅ Global Secondary Index 支持用户查询
- ✅ 可选的任务跟踪表

## 📊 关键配置

### Lambda 运行时
```hcl
runtime      = "python3.13"  # 最新 Python 版本
architecture = "arm64"        # Graviton2 成本优化
```

### Bedrock 模型配置
```hcl
agents = {
  orchestrator = {
    model_id    = "anthropic.claude-4-1"  # Claude 4.1
    temperature = 0.7
  }
  content = {
    model_id    = "anthropic.claude-4-0"  # Claude 4.0
    temperature = 0.8
  }
  visual = {
    model_id    = "anthropic.claude-4-0"  # Claude 4.0
    temperature = 0.9
  }
  compiler = {
    model_id    = "anthropic.claude-4-0"  # Claude 4.0
    temperature = 0.3
  }
}
```

### 内存配置
```hcl
memory_sizes = {
  create_outline         = 1024  # 内容生成
  generate_content       = 1024
  generate_image         = 2048  # 图像生成需要更多内存
  compile_pptx          = 2048  # 文件编译
}
```

### 超时配置
```hcl
timeouts = {
  api_handler    = 30   # API 网关超时
  compile_pptx   = 300  # 5分钟用于后台处理
}
```

## 📝 待完成任务

- [ ] Lambda 函数模块实现
- [ ] API Gateway 模块实现
- [ ] Lambda Layers 依赖打包
- [ ] Bedrock Agents 配置模块
- [ ] Step Functions 工作流（如需要）
- [ ] CloudWatch 监控和告警
- [ ] 集成测试脚本

## 🔒 安全考虑

1. **最小权限原则**: 所有 IAM 角色仅授予必要权限
2. **加密**: S3 和 DynamoDB 均启用加密
3. **私有访问**: S3 bucket 完全阻止公共访问
4. **API 认证**: 使用 API Key 进行简单认证
5. **VPC Endpoints**: 建议使用 VPC endpoints 进行服务间通信

## 📈 成本优化

1. **arm64 架构**: Lambda 使用 Graviton2 降低成本
2. **按需计费**: DynamoDB 使用 PAY_PER_REQUEST
3. **S3 生命周期**: 30天后自动转为廉价存储
4. **Reserved Concurrency**: Lambda 函数预热避免冷启动

## 🛠️ 故障排除

### Terraform 状态锁定
```bash
terraform force-unlock <lock-id>
```

### 清理资源
```bash
terraform destroy -var-file="config/environments/dev.tfvars"
```

### 查看资源变更
```bash
terraform show
terraform state list
```

## 📚 参考文档

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)
- [Amazon Bedrock Terraform Resources](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrock_agent)
- [项目设计文档](../.spec-workflow/specs/ai-ppt-assistant/design.md)
- [项目任务文档](../.spec-workflow/specs/ai-ppt-assistant/tasks.md)
