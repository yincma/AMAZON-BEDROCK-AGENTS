# AI PPT Assistant

基于Amazon Bedrock的智能PPT生成系统

## 项目结构

```
.
├── .context/                   # 项目上下文和规范文档
│   ├── agent-protocol.md      # Agent通信协议
│   └── execution-blueprint.md  # 执行蓝图
├── infrastructure/             # Terraform基础设施代码
│   ├── main.tf                # 主配置文件
│   ├── variables.tf           # 变量定义
│   ├── outputs.tf             # 输出定义
│   └── deploy.sh              # 部署脚本
└── lambdas/                   # Lambda函数代码
    └── placeholder/           # Phase 1占位代码
        ├── generate_ppt.py    # PPT生成函数
        ├── status_check.py    # 状态检查函数
        └── download_ppt.py    # 下载函数
```

## Phase 1: MVP功能

### 核心功能
- ✅ 基本的API端点设置
- ✅ S3存储桶配置
- ✅ Lambda函数框架
- ✅ IAM权限配置
- 🔄 Bedrock集成（待实现）
- 🔄 PPT生成逻辑（待实现）

### API端点

1. **生成PPT**
   - Endpoint: `POST /generate`
   - Body: `{"topic": "Your presentation topic"}`
   - Response: `{"presentation_id": "uuid", "status": "processing"}`

2. **检查状态**
   - Endpoint: `GET /status/{presentation_id}`
   - Response: `{"status": "processing|completed", "created_at": "timestamp"}`

3. **下载PPT**
   - Endpoint: `GET /download/{presentation_id}`
   - Response: `{"download_url": "presigned_s3_url", "expires_in": 3600}`

## 快速开始

### 前置要求
- AWS CLI 配置完成
- Terraform >= 1.0
- Python 3.11
- AWS账户权限

### 部署步骤

1. **克隆仓库**
```bash
git clone <repository-url>
cd AMAZON-BEDROCK-AGENTS
```

2. **配置AWS凭证**
```bash
aws configure
```

3. **部署基础设施**
```bash
cd infrastructure
./deploy.sh
```

4. **测试API**
```bash
# 获取API Gateway URL
API_URL=$(terraform output -raw api_gateway_url)

# 测试生成PPT
curl -X POST $API_URL/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI and Future"}'
```

## 开发计划

### Phase 1 (当前)
- [x] 基础设施搭建
- [x] API Gateway配置
- [x] Lambda占位函数
- [x] Bedrock集成
- [x] 基本PPT生成

### Phase 2
- [ ] 内容优化
- [ ] 模板系统
- [ ] 批量处理

### Phase 3
- [ ] 图片生成
- [ ] 高级样式
- [ ] 导出选项

## 技术栈

- **云服务**: AWS (Lambda, S3, API Gateway)
- **AI模型**: Amazon Bedrock (Claude)
- **IaC**: Terraform
- **语言**: Python 3.11
- **PPT生成**: python-pptx

## 贡献指南

1. 遵循 `.context/` 中的协议规范
2. 保持代码简洁（KISS原则）
3. 测试覆盖率 > 80%
4. 提交前运行 `terraform validate`

## 许可证

MIT License

## 联系方式

项目维护者: [Your Name]