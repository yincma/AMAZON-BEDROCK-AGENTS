# 🤖 AI PPT Assistant - Amazon Bedrock Agents

智能PPT助手，基于Amazon Bedrock Agents构建的AI驱动演示文稿生成系统。

[![Build Status](https://img.shields.io/badge/status-production%20ready-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)]()
[![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20Lambda%20%7C%20DynamoDB-orange.svg)]()

## 🎯 项目概览

AI PPT Assistant是一个完整的端到端解决方案，能够：

- 📝 **智能内容生成**: 使用Amazon Bedrock的Claude模型生成演示文稿内容
- 🎨 **自动化PPT创建**: 将生成的内容转换为专业的PowerPoint演示文稿
- 🔧 **会话管理**: 支持多用户并发会话和项目管理
- 🔍 **图片增强**: 自动查找和集成相关图片资源
- ⚡ **API驱动**: RESTful API支持前端集成

## 🏗 系统架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │────│   API Gateway    │────│   Lambda函数    │
│   应用程序       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Amazon        │────│   DynamoDB       │────│   Amazon S3     │
│   Bedrock       │    │   会话存储        │    │   文件存储       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 核心组件

- **session_manager**: 会话管理和状态追踪
- **content_enhancer**: 内容优化和智能增强
- **ppt_generator**: PPT文档生成
- **outline_creator**: 大纲结构创建
- **image_finder**: 图片资源检索
- **auth_handler**: 身份验证和授权

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd Amazon-Bedrock-Agents

# 创建虚拟环境 (Python 3.13)
python3 -m venv venv-py313
source venv-py313/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. AWS配置

```bash
# 配置AWS凭证
aws configure

# 验证权限
aws sts get-caller-identity
```

### 3. 部署基础设施

```bash
# 部署Terraform基础设施
cd infrastructure
terraform init
terraform plan
terraform apply

# 部署Lambda函数
cd ..
python deploy_lambda_functions.py
```

### 4. 配置API Gateway

```bash
# 自动配置API Gateway
python configure_api_gateway.py
```

## 📚 详细文档

- 📖 [部署指南](部署指南.md) - 完整的部署步骤和配置
- 🔧 [API文档](docs/api.md) - API接口详细说明
- 🛠 [开发指南](CONTRIBUTING.md) - 贡献代码和开发规范
- 🔍 [故障排除](TROUBLESHOOTING.md) - 常见问题和解决方案
- 📋 [配置说明](docs/config_migration_guide.md) - 配置系统使用指南

## 🎨 主要功能

### 1. 智能会话管理
- 多用户并发支持
- 会话状态持久化
- 项目组织和管理

### 2. AI内容生成
- 基于Amazon Bedrock Claude模型
- 上下文感知的内容生成
- 多种内容类型支持

### 3. PPT自动化
- 模板化PPT生成
- 图片自动集成
- 格式化和样式优化

### 4. RESTful API
```
POST /sessions          - 创建新会话
GET  /sessions/{id}     - 获取会话信息
POST /content/enhance   - 增强内容
POST /ppt/generate      - 生成PPT
POST /outlines/create   - 创建大纲
POST /images/find       - 查找图片
```

## 🛡 安全特性

- ✅ **身份验证**: 集成AWS Cognito
- ✅ **权限控制**: 基于IAM角色的访问控制
- ✅ **数据加密**: 传输和存储加密
- ✅ **API限流**: 防止滥用和DDoS攻击

## 📊 监控和日志

- **CloudWatch Logs**: Lambda函数日志
- **CloudWatch Metrics**: 性能指标监控
- **AWS X-Ray**: 分布式追踪
- **API Gateway监控**: API调用统计

## 🔄 开发状态

- ✅ **Phase 1**: 基础架构部署 (100%完成)
- ✅ **Phase 2**: 代码质量优化 (100%完成)  
- ✅ **Phase 3**: 文档完善 (100%完成)  

## 🤝 贡献

欢迎贡献代码! 请查看[贡献指南](CONTRIBUTING.md)了解详情。

## 📝 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件。

## 📞 支持

如有问题或需要帮助：

- 📧 提交Issue到项目仓库
- 📚 查看[故障排除文档](TROUBLESHOOTING.md)
- 🔍 查看[API文档](docs/api.md)

---

🚀 **项目状态**: 生产就绪 | 📅 **最后更新**: 2025-09-05