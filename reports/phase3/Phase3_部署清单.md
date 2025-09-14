# AI PPT Assistant Phase 3 部署清单

**生成日期**: 2025-09-13
**版本**: Phase 3
**目标环境**: AWS Cloud

## 1. 基础设施组件 (Terraform)

### 核心Terraform文件
- ✅ `main.tf` - 主要资源配置（S3、DynamoDB、IAM等）
- ✅ `lambda_optimized.tf` - 优化后的Lambda函数配置
- ✅ `monitoring.tf` - CloudWatch监控和告警配置
- ✅ `xray.tf` - X-Ray追踪配置

### AWS资源清单

#### 存储服务
```hcl
# S3 Bucket
- ai-ppt-presentations-{env}-{account_id}
  - 版本控制: 启用
  - 生命周期: 90天删除旧版本
  - 公共访问: 阻止

# DynamoDB Tables
- ai-ppt-presentations
  - 主键: presentation_id
  - 读/写容量: 按需计费
  - 全局二级索引支持
```

#### 计算服务
```hcl
# Lambda Functions (详见第2节)
- 运行时: Python 3.9
- 内存: 512MB - 2048MB
- 超时: 30秒 - 15分钟
- 层: ai-ppt-dependencies-layer
```

#### 网络服务
```hcl
# API Gateway
- REST API类型
- 区域端点
- CORS配置
- 自定义域名支持
```

#### 监控服务
```hcl
# CloudWatch
- 日志组: /aws/lambda/{function_name}
- 指标: 自定义业务指标
- 告警: 错误率和延迟阈值

# X-Ray
- 追踪启用
- 采样规则配置
- 服务地图支持
```

## 2. Lambda函数清单

### 核心API函数
```yaml
api_handler.py:
  描述: 主API处理器，路由请求到具体处理函数
  内存: 512MB
  超时: 30秒
  触发器: API Gateway

generate_ppt.py:
  描述: 基础PPT生成函数
  内存: 1024MB
  超时: 5分钟
  触发器: API Gateway / SQS

generate_ppt_complete.py:
  描述: 完整PPT生成流程，包含内容和图片
  内存: 2048MB
  超时: 10分钟
  触发器: SQS

generate_ppt_optimized.py:
  描述: 优化版PPT生成，性能提升版本
  内存: 1536MB
  超时: 8分钟
  触发器: SQS
```

### 内容处理函数
```yaml
compile_ppt.py:
  描述: 编译最终PPT文件
  内存: 1024MB
  超时: 5分钟
  依赖: python-pptx层

download_ppt.py:
  描述: 处理PPT下载请求
  内存: 512MB
  超时: 30秒
  输出: S3预签名URL

status_check.py:
  描述: 检查PPT生成状态
  内存: 256MB
  超时: 10秒
  查询: DynamoDB状态表
```

### 图像处理函数
```yaml
image_generator.py:
  描述: 使用Bedrock Titan生成图片
  内存: 1024MB
  超时: 5分钟
  服务: Amazon Bedrock

image_processing_service.py:
  描述: 图片处理和优化服务
  内存: 1536MB
  超时: 3分钟
  输出: S3存储

image_s3_service.py:
  描述: 图片S3上传和管理
  内存: 512MB
  超时: 2分钟
  权限: S3读写
```

### 辅助和演讲者备注函数
```yaml
notes_generator.py:
  描述: 生成演讲者备注
  内存: 1024MB
  超时: 3分钟
  服务: Amazon Bedrock

ppt_styler.py:
  描述: PPT样式和主题应用
  内存: 768MB
  超时: 2分钟
  模板: 预定义样式库

update_slide.py:
  描述: 更新单个幻灯片内容
  内存: 512MB
  超时: 1分钟
  范围: 单幻灯片操作
```

### 工作流和管理函数
```yaml
consistency_manager.py:
  描述: 确保内容一致性
  内存: 512MB
  超时: 2分钟
  检查: 跨幻灯片一致性

alert_manager.py:
  描述: 系统告警和通知管理
  内存: 256MB
  超时: 30秒
  输出: SNS/CloudWatch

logging_manager.py:
  描述: 统一日志管理
  内存: 256MB
  超时: 10秒
  输出: CloudWatch Logs

content_updater.py:
  描述: 内容更新和版本管理
  内存: 768MB
  超时: 2分钟
  版本: 支持历史记录
```

## 3. 专业模块和服务

### 异常处理模块
```yaml
lambdas/exceptions/:
  - speaker_notes_exceptions.py: 演讲者备注异常
  - 自定义异常类型和错误处理
```

### 服务层模块
```yaml
lambdas/services/:
  - bedrock_speaker_notes_service.py: Bedrock演讲者备注服务
  - pptx_integration_service.py: PowerPoint集成服务
```

### 工作流模块
```yaml
lambdas/workflows/:
  - presentation_workflow.py: 演示文稿工作流管理
```

### 工具和验证器
```yaml
lambdas/utils/:
  - content_relevance_checker.py: 内容相关性检查
  - speaker_notes_validator.py: 演讲者备注验证
```

## 4. API端点映射

### REST API端点
```yaml
POST /generate:
  Lambda: api_handler.py → generate_ppt.py
  描述: 创建新的PPT生成任务

GET /status/{id}:
  Lambda: api_handler.py → status_check.py
  描述: 查询PPT生成状态

GET /download/{id}:
  Lambda: api_handler.py → download_ppt.py
  描述: 获取PPT下载链接

PUT /update/{id}/slide/{slide_id}:
  Lambda: api_handler.py → update_slide.py
  描述: 更新特定幻灯片

DELETE /presentation/{id}:
  Lambda: api_handler.py → delete_presentation.py
  描述: 删除演示文稿

POST /regenerate/image/{id}:
  Lambda: api_handler.py → image_regenerator.py
  描述: 重新生成图片
```

## 5. 依赖和配置

### Lambda层依赖
```yaml
ai-ppt-dependencies-layer:
  包含:
    - python-pptx: PPT操作库
    - boto3: AWS SDK
    - Pillow: 图像处理
    - pydantic: 数据验证
    - 其他Python依赖
  大小: ~23MB
  兼容: Python 3.9
```

### 环境变量配置
```yaml
通用环境变量:
  - ENVIRONMENT: dev/staging/prod
  - AWS_REGION: us-east-1
  - PRESENTATIONS_BUCKET: S3桶名称
  - DYNAMODB_TABLE: DynamoDB表名
  - BEDROCK_REGION: Bedrock服务区域

函数特定变量:
  - IMAGE_TIMEOUT: 图片生成超时时间
  - MAX_SLIDES: 最大幻灯片数量
  - DEFAULT_TEMPLATE: 默认模板名称
```

### IAM权限矩阵
```yaml
Lambda执行角色权限:
  S3:
    - GetObject, PutObject (演示文稿桶)
    - ListBucket

  DynamoDB:
    - GetItem, PutItem, UpdateItem, DeleteItem
    - Query, Scan (限制表)

  Bedrock:
    - InvokeModel (Titan, Claude模型)

  CloudWatch:
    - CreateLogGroup, CreateLogStream
    - PutLogEvents, PutMetricData

  X-Ray:
    - PutTraceSegments, PutTelemetryRecords
```

## 6. 部署前检查清单

### 代码准备
- ✅ 所有Python文件语法正确
- ⚠️ 代码风格问题需修复（351个问题）
- ✅ 无硬编码凭据
- ✅ 模块结构规范化

### 配置验证
- ✅ Terraform配置文件存在
- ⚠️ 需验证所有环境变量配置
- ⚠️ 需确认IAM权限最小化原则
- ⚠️ 需测试Bedrock模型可用性

### 测试状态
- ✅ 基础单元测试通过
- ⚠️ 需要端到端集成测试
- ⚠️ 负载测试待完成
- ⚠️ 安全扫描建议执行

## 7. 部署顺序建议

### 阶段1: 基础设施
1. 部署S3存储桶和DynamoDB表
2. 创建IAM角色和策略
3. 配置CloudWatch日志组

### 阶段2: 核心服务
1. 打包并部署Lambda层
2. 部署API处理函数
3. 部署状态检查和下载函数

### 阶段3: 功能增强
1. 部署PPT生成函数（基础版）
2. 部署图像生成函数
3. 部署内容更新函数

### 阶段4: 高级功能
1. 部署优化版生成函数
2. 部署工作流管理函数
3. 部署监控和告警函数

### 阶段5: 前端和集成
1. 配置API Gateway
2. 设置CORS和域名
3. 部署前端应用（如有）

## 8. 监控和维护

### 关键指标
- Lambda函数调用次数和错误率
- API Gateway响应时间和4xx/5xx错误
- DynamoDB读写容量使用率
- S3存储使用量和请求数
- Bedrock模型调用次数和成本

### 告警配置
- Lambda函数错误率 > 5%
- API延迟 > 30秒
- DynamoDB限流错误
- S3上传失败率 > 1%

### 成本优化
- 定期review Lambda内存配置
- S3对象生命周期管理
- DynamoDB容量模式优化
- Bedrock调用频率监控

## 总结

本部署清单涵盖了AI PPT Assistant Phase 3的所有组件。项目包含43个Lambda函数，支持完整的PPT生成、编辑和管理功能。建议按阶段部署，先验证核心功能，再逐步添加高级特性。部署前需要解决代码质量问题，确保安全配置到位。