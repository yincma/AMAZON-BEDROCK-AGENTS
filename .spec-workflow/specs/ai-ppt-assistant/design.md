# Design Document

## Overview

AI PPT Assistant 是一个基于 Amazon Bedrock 的演示文稿生成系统，采用**分阶段渐进式架构**和**TDD开发模式**。系统从最简单的文本生成开始，逐步增加功能，每个阶段都是可运行的产品。

## Development Principles

- **TDD (Test-Driven Development)**: 每个功能先写测试，再实现
- **KISS**: 保持简单，避免过度设计
- **YAGNI**: 只实现当前需要的功能
- **Incremental Delivery**: 每个阶段都是可交付的产品

## Phased Architecture Evolution

### Phase 1: MVP Architecture (Week 1)
```
User → API Gateway → Lambda (generate_ppt) → S3
                         ↓
                     Bedrock Claude
```
- **1个Lambda函数**: 处理所有逻辑
- **1个S3桶**: 存储生成的内容和PPT
- **极简API**: 3个端点（生成/状态/下载）

### Phase 2: Enhanced Architecture (Week 2)
```
User → API Gateway → Lambda (api_handler)
                         ↓
                   ┌─────┼─────┐
            content_gen  image_gen  ppt_compiler
                   ↓        ↓           ↓
               Bedrock    Nova         S3
```
- **3个Lambda函数**: 职责分离
- **添加图片生成**: Amazon Nova集成
- **模板支持**: 2-3个简单模板

### Phase 3: Optimized Architecture (Week 3)
```
User → API Gateway → Step Functions
                         ↓
              [并行处理工作流]
                         ↓
                   Lambda函数组
                         ↓
                    S3 + Cache
```
- **Step Functions编排**: 并行处理
- **缓存层**: 提升性能
- **监控告警**: CloudWatch集成

### Phase 4: Production Architecture (Week 4)
- **CI/CD流水线**: 自动化部署
- **多环境支持**: dev/staging/prod
- **安全加固**: IAM认证替代API Key

## Code Reuse Analysis

### Existing Components to Leverage
- **AWS SDK (Boto3)**: 用于所有 AWS 服务交互
- **python-pptx**: PowerPoint 文件生成库
- **Pillow**: 图像处理和优化
- **langchain**: Agent 协调和链式调用

### Integration Points
- **Amazon Bedrock**: Claude 4.0 用于文本生成
- **Amazon Nova**: AI 图像生成
- **S3**: 文件存储、状态管理和检索
- **API Gateway**: RESTful API 接口

## Project Structure (Phased)

### Phase 1: MVP Structure
```
/ai-ppt-assistant/
├── /tests/                # TDD测试优先
│   ├── conftest.py
│   ├── test_infrastructure.py
│   └── test_generate_ppt.py
├── /lambdas/
│   └── generate_ppt.py    # 单一Lambda函数
└── /infrastructure/
    └── main.tf            # 最小化配置
```

### Phase 2: Enhanced Structure
```
/ai-ppt-assistant/
├── /tests/                # 更多测试
│   ├── test_content_generator.py
│   ├── test_image_generator.py
│   └── test_ppt_compiler.py
├── /lambdas/
│   ├── api_handler.py     # API处理
│   ├── content_generator.py
│   ├── image_generator.py
│   └── ppt_compiler.py
└── /infrastructure/
    └── modules/           # 模块化
```

### Phase 3-4: Production Structure
```
/ai-ppt-assistant/
├── /tests/                # 完整测试套件
├── /lambdas/              # 全部功能
├── /infrastructure/       # 完整IaC
├── /.github/workflows/    # CI/CD
└── /docs/                 # 文档
```

## Components and Interfaces

### Lambda: presentation_handler
- **Purpose:** API入口，协调整个生成流程
- **Interfaces:**
  ```python
  def handler(event, context):
      # Input: API Gateway event
      # Output: {"presentation_id": "uuid", "status": "processing"}
      # 1. 验证请求
      # 2. 生成 presentation_id
      # 3. 调用其他 Lambda 函数
      # 4. 返回响应
  ```
- **Dependencies:** S3, 其他 Lambda 函数

### Lambda: content_generator
- **Purpose:** 生成大纲和幻灯片内容
- **Interfaces:**
  ```python
  def handler(event, context):
      # Input: {"topic": "str", "page_count": int, "presentation_id": "str"}
      # Output: S3 路径 /presentations/{id}/outline.json
      # 使用 Bedrock Claude 生成内容
      # 保存到 S3
  ```
- **Dependencies:** Bedrock Claude 4.0, S3

### Lambda: visual_processor
- **Purpose:** 处理图片生成和搜索
- **Interfaces:**
  ```python
  def handler(event, context):
      # Input: {"slides": [...], "presentation_id": "str"}
      # Output: S3 路径 /presentations/{id}/images/
      # 为每个幻灯片生成或查找图片
  ```
- **Dependencies:** Amazon Nova, S3

### Lambda: file_compiler
- **Purpose:** 编译最终的 PPTX 文件
- **Runtime:** Python 3.13
- **Interfaces:**
  ```python
  def handler(event, context):
      # Input: {"presentation_id": "str"}
      # Output: S3 路径 /presentations/{id}/output/presentation.pptx
      # 1. 从 S3 读取内容和图片
      # 2. 使用 python-pptx 生成文件
      # 3. 上传到 S3
      # 4. 生成预签名下载 URL
  ```
- **Dependencies:** python-pptx, S3

## Data Models (Phased)

### Phase 1: MVP Data Model
```python
# 极简请求模型
{
    "topic": "string",
    "page_count": 5,  # 固定5页
    "presentation_id": "uuid"
}

# 极简内容模型
{
    "slides": [
        {
            "title": "string",
            "points": ["point1", "point2", "point3"]
        }
    ]
}

# S3存储：单一JSON文件
/presentations/{id}/content.json
/presentations/{id}/presentation.pptx
```

### Phase 2: Enhanced Data Model
```python
# 增加模板和图片
{
    "topic": "string",
    "page_count": "5-10",
    "template": "default|modern|classic",
    "with_images": true
}

# 增加图片和备注
{
    "slides": [
        {
            "title": "string",
            "points": ["..."],
            "image_url": "s3://...",
            "speaker_notes": "..."
        }
    ]
}
```

### Phase 3: Production Data Model
```python
# 完整请求模型
{
    "request_id": "uuid",
    "user_id": "string",
    "parameters": {
        "topic": "string",
        "page_count": "5-30",
        "audience": "string",
        "template_id": "string",
        "language": "zh|en"
    },
    "status": "pending|processing|completed|failed",
    "metadata": {
        "created_at": "iso8601",
        "updated_at": "iso8601",
        "version": "1.0"
    }
}
```

### S3 Storage Evolution

#### Phase 1: 最简存储
```
/presentations/{id}/
  ├── content.json       # 所有内容
  └── presentation.pptx  # 最终文件
```

#### Phase 2: 分离存储
```
/presentations/{id}/
  ├── content.json       # 文本内容
  ├── images/           # 图片文件夹
  └── presentation.pptx
```

#### Phase 3: 完整存储
```
/presentations/{id}/
  ├── metadata.json     # 元数据
  ├── content/         # 内容文件夹
  ├── images/          # 图片文件夹
  ├── versions/        # 版本管理
  └── output/          # 输出文件
```

## Error Handling

### Error Scenarios

1. **LLM Generation Timeout**
   - **Handling:** Implement exponential backoff retry (max 3 attempts)
   - **User Impact:** "正在处理您的请求，请稍候..." 消息
   - **Fallback:** 使用简化的提示词重试

2. **Image Generation Failure**
   - **Handling:** 先尝试图库检索，失败后使用占位图
   - **User Impact:** 使用默认图片，允许用户后续替换
   - **Recovery:** 记录失败，提供手动上传选项

3. **File Compilation Error**
   - **Handling:** 保存中间状态，允许从断点恢复
   - **User Impact:** "文件生成遇到问题，正在重试..."
   - **Logging:** 详细错误日志到 CloudWatch

4. **S3 Upload Failure**
   - **Handling:** 重试 3 次，使用不同的 S3 区域
   - **User Impact:** 延迟通知，提供替代下载方式
   - **Backup:** 临时存储在 Lambda /tmp

5. **Request Validation Error**
   - **Handling:** 返回详细的验证错误信息
   - **User Impact:** 明确指出哪个参数有问题
   - **Prevention:** 前端预验证

## API Design (Phased)

### Phase 1: MVP API (3 endpoints)

```yaml
POST /generate
  Request:
    - topic: string
  Response:
    - presentation_id: string
    - message: "Processing"

GET /status/{id}
  Response:
    - status: pending|processing|completed
    - progress: number (0-100)

GET /download/{id}
  Response:
    - download_url: string (S3 presigned URL, 1小时有效)
```

### Phase 2: Enhanced API (+2 endpoints)

```yaml
POST /generate (enhanced)
  Request:
    - topic: string
    - page_count?: number (5-10)
    - template?: string (default|modern|classic)
  Response:
    - presentation_id: string
    - estimated_time: number

GET /presentations/{id}/preview
  Response:
    - slides: array (缩略图预览)
```

### Phase 3: Advanced API (+3 endpoints)

```yaml
PATCH /presentations/{id}/slides/{n}
  Request:
    - content?: object
    - regenerate_image?: boolean
  Response:
    - slide: object
    - status: string

POST /presentations/{id}/regenerate
  Request:
    - slides?: array (指定页面)
  Response:
    - status: string

DELETE /presentations/{id}
  Response:
    - message: "Deleted"
```

### Phase 4: Production API (完整版)
- 添加认证: API Key → IAM
- 添加限流: Rate limiting
- 添加版本: /v1/presentations
- 添加批量操作: Batch API

## Security Considerations (Simplified)

### Authentication & Authorization
- API Gateway 使用简单的 API Key 验证
- IAM 角色最小权限原则
- Agent 执行角色限制在必要的 AWS 服务

### Data Protection
- S3 bucket 加密 (SSE-S3)
- DynamoDB 加密
- VPC endpoints 用于服务间通信
- 敏感数据不记录在日志中

### Input Validation
- 所有输入参数严格验证
- 防止提示词注入攻击
- 文件大小和类型限制

## Performance Optimization

### Performance Strategy
- Lambda 内存配置：2048MB 保证性能
- S3 Transfer Acceleration 加速大文件上传

### Parallel Processing
- 多页幻灯片内容并行生成
- 图片生成与内容生成并行
- 使用 Step Functions 编排复杂流程

### Resource Management
- Lambda 内存配置：统一 2048MB
- 超时设置：30秒 (API handler), 5分钟 (生成函数)
- S3 生命周期策略：30天后转 IA 存储
- Python Runtime: 3.13 (最新版本，性能优化)

## Infrastructure as Code

### Terraform Configuration
```hcl
# main.tf 示例
provider "aws" {
  region = "us-east-1"
}

# 简化的 Lambda 函数定义
resource "aws_lambda_function" "presentation_handler" {
  function_name = "presentation-handler"
  runtime       = "python3.13"
  handler       = "presentation_handler.handler"
  memory_size   = 2048
  timeout       = 30
}

resource "aws_lambda_function" "content_generator" {
  function_name = "content-generator"
  runtime       = "python3.13"
  handler       = "content_generator.handler"
  memory_size   = 2048
  timeout       = 300
}

resource "aws_s3_bucket" "presentations" {
  bucket = "ai-ppt-presentations"

  lifecycle_rule {
    enabled = true
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }
}
```

## TDD Testing Strategy

### Test-First Development Process
```
1. Write Test (RED) → 2. Write Code (GREEN) → 3. Refactor (REFACTOR)
```

### Phase 1: MVP Testing
```python
# tests/test_mvp.py
def test_generate_simple_ppt():
    """测试基础PPT生成"""
    # Given: 一个主题
    # When: 调用生成API
    # Then: 返回5页内容的PPT

def test_s3_storage():
    """测试S3存储"""
    # Given: PPT内容
    # When: 保存到S3
    # Then: 可以下载

def test_api_endpoints():
    """测试3个基础API"""
    # POST /generate
    # GET /status/{id}
    # GET /download/{id}
```

### Phase 2: Enhanced Testing
```python
# tests/test_enhanced.py
def test_with_images():
    """测试图片生成"""
    # 验证每页都有图片

def test_templates():
    """测试模板应用"""
    # 验证3种模板

def test_speaker_notes():
    """测试演讲备注"""
    # 验证备注生成
```

### Phase 3: Advanced Testing
```python
# tests/test_performance.py
def test_parallel_processing():
    """测试并行处理"""
    # 验证性能提升

def test_content_modification():
    """测试内容修改"""
    # 验证单页更新

def test_caching():
    """测试缓存机制"""
    # 验证响应加速
```

### Testing Tools & Coverage
- **Phase 1**: pytest + moto (目标覆盖率 80%)
- **Phase 2**: + LocalStack (目标覆盖率 85%)
- **Phase 3**: + 性能测试 (目标覆盖率 90%)
- **Phase 4**: + 安全测试 (目标覆盖率 95%)

### Continuous Testing
```yaml
# .github/workflows/test.yml
on: [push, pull_request]
jobs:
  test:
    steps:
      - Run unit tests
      - Check coverage
      - Run integration tests
      - Deploy to staging
      - Run E2E tests
```