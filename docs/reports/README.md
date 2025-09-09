# 📚 AI PPT Assistant 文档索引

## 📊 报告文档

### 当前活跃报告
- **[问题报告.md](./问题报告.md)** - 🔴 最新问题跟踪（简洁版）
  - 当前状态总览
  - 最新问题详情
  - 历史问题摘要
  - 可用工具列表

### 历史归档
- **问题报告_完整历史_*.md** - 📜 完整历史问题记录
  - 包含所有历史问题的详细信息
  - 按日期时间戳命名
  - 用于审计和回溯

### 专项报告
- **[问题解决报告.md](./问题解决报告.md)** - ✅ 问题解决方案汇总
- **[后台功能测试报告.md](./后台功能测试报告.md)** - 🧪 后台功能测试结果
- **[API_TEST_REPORT.md](./API_TEST_REPORT.md)** - 🔌 API测试报告
- **[TEST_REPAIR_REPORT.md](./TEST_REPAIR_REPORT.md)** - 🔧 测试修复报告

## 📖 技术文档

### 部署与运维
- **[aws-expert-deployment-guide.md](../aws-expert-deployment-guide.md)** - 🚀 AWS专家部署指南
- **[deployment-checklist.md](../deployment-checklist.md)** - ✔️ 部署检查清单
- **[troubleshooting-guide.md](../troubleshooting-guide.md)** - 🔍 故障排查指南

### 改进文档
- **[enhanced-destroy-improvements.md](../enhanced-destroy-improvements.md)** - 💪 增强版销毁改进说明
- **[lambda-layer-analysis.md](../lambda-layer-analysis.md)** - 📦 Lambda层分析

## 🛠️ 脚本工具

### 销毁管理
- `scripts/enhanced_safe_destroy.sh` - 增强版安全销毁（v2.0）
- `scripts/safe_destroy.sh` - 传统安全销毁
- `scripts/check_cloudfront_resources.sh` - CloudFront资源检查

### 部署验证
- `scripts/validate_deployment.py` - 部署验证工具
- `scripts/aws_expert_deployment_validator.py` - AWS专家验证器
- `scripts/aws_expert_auto_fixer.py` - 自动修复工具

### 修复工具
- `scripts/fix_bedrock_agent_role.py` - Bedrock角色修复
- `scripts/fix_lambda_dynamodb_permissions.py` - Lambda权限修复
- `scripts/update_bedrock_policy.py` - Bedrock策略更新

### 测试工具
- `test_api_comprehensive.py` - API综合测试
- `system_health_check.py` - 系统健康检查
- `comprehensive_backend_test.py` - 后台综合测试

## 📌 快速导航

### 遇到问题？
1. 查看 **[问题报告.md](./问题报告.md)** 了解是否为已知问题
2. 参考 **[troubleshooting-guide.md](../troubleshooting-guide.md)** 进行故障排查
3. 运行 `make check-cloudfront` 检查CloudFront状态

### 需要部署？
1. 阅读 **[aws-expert-deployment-guide.md](../aws-expert-deployment-guide.md)**
2. 使用 **[deployment-checklist.md](../deployment-checklist.md)** 确认准备就绪
3. 运行 `make deploy` 开始部署

### 需要销毁？
1. 运行 `make check-cloudfront` 预检查资源
2. 执行 `make destroy` 智能销毁
3. 查看 **[enhanced-destroy-improvements.md](../enhanced-destroy-improvements.md)** 了解工作原理

## 📅 更新记录

| 日期 | 更新内容 |
|------|---------|
| 2025-09-09 | 创建文档索引，整理报告结构 |
| 2025-09-09 | 备份完整历史，创建简洁版问题报告 |
| 2025-09-09 | 实施增强版销毁流程 |

## 📝 维护说明

- **问题报告**: 保持简洁，定期归档历史
- **测试报告**: 每次重要测试后更新
- **部署文档**: 随基础设施变化同步更新
- **脚本工具**: 版本化管理，保留向后兼容

---

*最后更新: 2025-09-09 by ultrathink*