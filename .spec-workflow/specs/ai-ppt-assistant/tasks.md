# 任务文档

## 基础设施配置（Terraform）

- [x] 1. 初始化 Terraform 项目结构
  - 文件: infrastructure/main.tf, variables.tf, outputs.tf, terraform.tfvars.example, config/environments/
  - 配置 AWS provider，从配置文件读取区域设置（使用 var.aws_region）
  - 定义环境配置的变量结构，支持多环境部署（dev/staging/prod）
  - 创建示例配置文件，不包含任何硬编码的值
  - 目的：建立基础设施即代码的基础，支持灵活配置
  - _需求来源: 设计文档 - 基础设施即代码_

- [x] 2. 创建 S3 存储桶配置
  - 文件: infrastructure/modules/s3/main.tf
  - 定义用于演示文稿存储的 S3 存储桶，启用加密
  - 配置生命周期策略（30天后转为 IA 存储）
  - 设置 CORS 以支持预签名 URL
  - 目的：文件存储基础设施
  - _需求来源: R1, R2 - 文件存储需求_

- [x] 3. 配置 DynamoDB 数据表
  - 文件: infrastructure/modules/dynamodb/main.tf
  - 创建用于会话状态管理的数据表
  - 配置 TTL 设置（30天）
  - 设置按需计费模式
  - 目的：会话和状态持久化
  - _需求来源: 设计文档 - 会话状态模型_

- [x] 4. 设置 API Gateway
  - 文件: infrastructure/modules/api_gateway/main.tf
  - 配置 REST API，使用 API 密钥认证
  - 定义资源路径和方法
  - 设置限流和配额
  - 目的：API 端点基础设施
  - _需求来源: 设计文档 - API 设计_

## Lambda 函数开发

- [x] 5. 创建 Lambda 基础层
  - 文件: lambdas/layers/requirements.txt, build.sh
  - 打包共享依赖（boto3、python-pptx、pillow）
  - 配置 Python 3.13 运行时兼容性
  - 目的：共享依赖管理
  - _需求来源: 设计文档 - Python 3.13 运行时_

- [x] 6. 实现创建大纲 Lambda 函数
  - 文件: lambdas/controllers/create_outline.py
  - 集成 Bedrock Claude 4.0 API
  - 实现大纲生成的提示词模板
  - 添加输入验证和错误处理
  - 目的：生成演示文稿结构
  - _需求来源: R1 - 主题式演示文稿生成_

- [x] 7. 实现生成内容 Lambda 函数
  - 文件: lambdas/controllers/generate_content.py
  - 将大纲扩展为详细的幻灯片内容
  - 集成 Claude 4.0 进行内容生成
  - 实现多页并行处理
  - 目的：生成详细的幻灯片内容
  - _需求来源: R1 - 主题式演示文稿生成_

- [x] 8. 实现生成图片 Lambda 函数
  - 文件: lambdas/controllers/generate_image.py
  - 集成 Amazon Nova 进行图片生成
  - 实现图片提示词优化
  - 添加占位图片的降级方案
  - 目的：创建 AI 生成的图片
  - _需求来源: R3 - 智能配图生成_

- [x] 9. 实现查找图片 Lambda 函数
  - 文件: lambdas/controllers/find_image.py
  - 搜索相关图片（暂时使用占位功能）
  - 实现图片元数据提取
  - 目的：为幻灯片查找现有图片
  - _需求来源: R3 - 智能配图生成_

- [x] 10. 实现演讲备注 Lambda 函数
  - 文件: lambdas/controllers/generate_speaker_notes.py
  - 使用 Claude 4.0 生成上下文相关的演讲备注
  - 根据演示时长调整备注内容
  - 目的：创建演讲者指导
  - _需求来源: R4 - 演讲者备注生成_

## 文件编译的 MVC 实现

- [x] 11. 创建 compile_pptx 的模型层
  - 文件: lambdas/models/presentation_model.py
  - 实现文件存储的 S3 操作
  - 处理模板检索逻辑
  - 添加 DynamoDB 会话管理
  - 目的：演示文稿编译的数据访问层
  - _需求来源: 设计文档 - MVC 架构_

- [x] 12. 创建 compile_pptx 的视图层
  - 文件: lambdas/views/presentation_view.py
  - 使用 python-pptx 实现 PPTX 生成
  - 创建幻灯片布局和样式
  - 处理图片嵌入
  - 目的：演示文稿渲染层
  - _需求来源: 设计文档 - MVC 架构_

- [x] 13. 创建 compile_pptx 的控制器层
  - 文件: lambdas/controllers/compile_pptx.py
  - 协调模型层和视图层
  - 实现编译的业务逻辑
  - 添加全面的错误处理
  - 目的：业务逻辑协调
  - _需求来源: 设计文档 - MVC 架构_

## Bedrock Agents 配置

- [x] 14. 配置编排代理（Orchestrator Agent）
  - 文件: agents/orchestrator/agent_config.json, instructions.txt
  - 定义代理角色和职责
  - 配置动作组和权限
  - 设置 Claude 4.1 模型集成
  - 目的：主工作流协调
  - _需求来源: 设计文档 - Orchestrator Agent_

- [x] 15. 配置内容代理（Content Agent）
  - 文件: agents/content/agent_config.json, action_groups.json
  - 链接到 create_outline 和 generate_content Lambda 函数
  - 定义内容生成工作流
  - 配置 Claude 4.0 参数
  - 目的：内容生成编排
  - _需求来源: R1, R4 - 内容生成_

- [x] 16. 配置视觉代理（Visual Agent）
  - 文件: agents/visual/agent_config.json, action_groups.json
  - 链接到 generate_image 和 find_image Lambda 函数
  - 定义图片生成工作流
  - 配置 Nova 集成参数
  - 目的：视觉内容编排
  - _需求来源: R3 - 智能配图生成_

- [x] 17. 配置文件编译代理（File Compiler Agent）
  - 文件: agents/compiler/agent_config.json, action_groups.json
  - 链接到 compile_pptx Lambda 函数
  - 定义文件编译工作流
  - 配置 S3 集成
  - 目的：最终文件生成
  - _需求来源: 所有需求 - 文件输出_

## API 实现

- [x] 18. 实现演示文稿生成端点
  - 文件: lambdas/api/generate_presentation.py
  - 处理 POST /presentations/generate 请求
  - 验证输入参数
  - 触发编排代理
  - 目的：主 API 入口点
  - _需求来源: 设计文档 - API 设计_

- [x] 19. 实现状态查询和下载端点
  - 文件: lambdas/api/presentation_status.py, presentation_download.py
  - 处理状态和下载的 GET 请求
  - 生成 S3 预签名 URL
  - 实现进度跟踪
  - 目的：状态监控和文件获取
  - _需求来源: 设计文档 - API 设计_

- [x] 20. 实现幻灯片修改端点
  - 文件: lambdas/api/modify_slide.py
  - 处理 PATCH /presentations/{id}/slides/{slideId} 请求
  - 实现部分内容更新
  - 保持演示文稿一致性
  - 目的：支持迭代修改
  - _需求来源: R5 - 迭代修改支持_

## Terraform 部署配置

- [x] 21. 在 Terraform 中配置 Lambda 函数
  - 文件: infrastructure/modules/lambda/main.tf
  - 定义所有 Lambda 函数，使用 Python 3.13 运行时
  - 配置内存、超时和环境变量
  - 附加 IAM 角色和策略
  - 目的：Lambda 基础设施部署
  - _需求来源: 设计文档 - Lambda 配置_

- [x] 22. 在 Terraform 中配置 Bedrock Agents
  - 文件: infrastructure/modules/bedrock/main.tf
  - 定义代理配置
  - 设置动作组映射
  - 配置模型权限
  - 目的：Bedrock 代理基础设施
  - _需求来源: 设计文档 - Bedrock Agents_

## 测试实现

- [x] 23. 创建 Lambda 函数的单元测试
  - 文件: tests/unit/test_*.py
  - 独立测试每个 Lambda 函数
  - 模拟 AWS 服务调用
  - 达到 >80% 的代码覆盖率
  - 目的：单元测试覆盖
  - _需求来源: 设计文档 - 测试策略_

- [x] 24. 创建集成测试
  - 文件: tests/integration/test_workflow.py
  - 测试代理到 Lambda 的通信
  - 测试完整生成工作流
  - 验证错误处理路径
  - 目的：集成测试
  - _需求来源: 设计文档 - 测试策略_

- [x] 25. 创建端到端测试场景
  - 文件: tests/e2e/test_scenarios.py
  - 测试完整的用户旅程
  - 验证性能指标（<60秒）
  - 测试并发请求处理
  - 目的：端到端验证
  - _需求来源: 设计文档 - 测试策略_

## 文档和最终设置

- [x] 26. 创建部署文档
  - 文件: docs/deployment.md
  - 记录 Terraform 部署步骤
  - 包含环境配置指南
  - 添加故障排查部分
  - 目的：部署指导
  - _需求来源: 项目文档_

- [x] 27. 创建 API 文档
  - 文件: docs/api.md
  - 记录所有 API 端点
  - 包含请求/响应示例
  - 添加错误代码参考
  - 目的：API 使用文档
  - _需求来源: 设计文档 - API 设计_

- [x] 28. 最终集成和部署
  - 执行 Terraform apply
  - 验证所有组件正常工作
  - 运行完整测试套件
  - 配置监控和告警
  - 目的：生产环境部署
  - _需求来源: 所有需求_

## 任务汇总

任务总数：28 个
预计时间：单人开发需要 4-5 周

优先级顺序：
1. 基础设施设置（任务 1-4）
2. Lambda 开发（任务 5-13）
3. 代理配置（任务 14-17）
4. API 实现（任务 18-20）
5. 部署和测试（任务 21-28）

依赖关系：
- Lambda 函数依赖于基础设施设置
- 代理依赖于 Lambda 函数
- API 依赖于代理
- 测试依赖于所有组件