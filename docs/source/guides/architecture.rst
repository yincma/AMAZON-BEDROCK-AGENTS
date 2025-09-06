系统架构
========

AI PPT Assistant采用云原生的微服务架构，充分利用AWS的无服务器服务来实现高可扩展性和高可靠性。

整体架构
--------

.. mermaid::

   graph TB
       A[用户] --> B[API Gateway]
       B --> C[Lambda API层]
       C --> D[Bedrock Agent]
       C --> E[DynamoDB]
       C --> F[S3存储]
       D --> G[Lambda控制器]
       G --> H[内容生成]
       G --> I[图片搜索]
       G --> J[PPT生成]
       H --> K[Bedrock模型]
       I --> L[图片服务]
       J --> F
       C --> M[SQS队列]
       M --> N[异步处理]

核心组件
--------

API层
~~~~~

* **API Gateway**: 统一的API入口点，处理认证、限流和路由
* **Lambda API Functions**: 轻量级的API处理函数

  * ``generate_presentation.py`` - 创建演示文稿任务
  * ``presentation_status.py`` - 查询生成状态
  * ``presentation_download.py`` - 下载完成的演示文稿
  * ``modify_slide.py`` - 修改特定幻灯片

业务逻辑层
~~~~~~~~~~

* **Bedrock Orchestrator Agent**: 核心编排代理，协调整个生成流程
* **Lambda Controllers**: 专门的业务逻辑处理函数

  * ``generate_content.py`` - 内容生成控制器
  * ``find_image.py`` - 图片搜索控制器
  * ``generate_speaker_notes.py`` - 演讲备注生成

数据层
~~~~~~

* **DynamoDB**: 存储演示文稿元数据和状态信息
* **S3**: 存储生成的演示文稿文件和图片资源
* **SQS**: 异步任务队列，处理长时间运行的生成任务

AI服务层
~~~~~~~~

* **Amazon Bedrock**: 提供多种AI模型支持
* **Claude/GPT模型**: 用于内容生成和优化
* **图片生成模型**: 创建自定义图片内容

数据流
------

1. **请求处理流程**:

   .. mermaid::

      sequenceDiagram
          participant U as 用户
          participant AG as API Gateway
          participant L as Lambda API
          participant D as DynamoDB
          participant BA as Bedrock Agent
          participant S as S3

          U->>AG: POST /presentations/generate
          AG->>L: 转发请求
          L->>D: 存储任务状态
          L->>BA: 启动生成流程
          L->>U: 返回任务ID
          BA->>BA: 异步生成内容
          BA->>S: 存储演示文稿
          BA->>D: 更新完成状态

2. **内容生成流程**:

   a. 解析用户需求和参数
   b. 生成演示文稿大纲
   c. 为每页幻灯片生成内容
   d. 搜索和添加相关图片
   e. 生成演讲者备注
   f. 组装最终演示文稿
   g. 上传到S3并更新状态

扩展性设计
----------

**水平扩展**:
- Lambda函数自动扩展，支持高并发
- DynamoDB按需计费，支持大量读写
- S3无限存储容量

**容错设计**:
- 多个Lambda函数实例确保高可用性
- DynamoDB多AZ部署
- S3的99.999999999%数据持久性

**监控和日志**:
- CloudWatch集成监控所有组件
- 详细的错误日志和性能指标
- 自动告警机制

安全架构
--------

**认证和授权**:
- API Gateway集成IAM或Cognito
- Lambda函数最小权限原则
- 所有服务间通信使用IAM角色

**数据安全**:
- 传输层TLS加密
- S3数据静态加密
- DynamoDB表加密

**网络安全**:
- VPC端点减少公网暴露
- 安全组精确控制访问
- WAF保护API Gateway

性能优化
--------

**缓存策略**:
- API Gateway缓存常用响应
- Lambda保持连接池复用
- S3 CloudFront分发加速

**异步处理**:
- SQS解耦长时间任务
- 批量处理提高效率
- 优雅的错误重试机制

成本优化
--------

**按需付费**:
- Lambda按执行时间计费
- DynamoDB按读写请求计费
- S3按存储和传输计费

**资源优化**:
- Lambda内存和超时时间调优
- DynamoDB读写容量自动调节
- S3生命周期管理自动清理

部署架构
--------

使用Infrastructure as Code (IaC)实现：

* **Terraform**: 管理AWS资源
* **自动化部署**: 通过Makefile和脚本
* **多环境支持**: dev、test、prod环境隔离
* **CI/CD集成**: GitHub Actions自动部署

监控和运维
----------

**关键指标监控**:
- API响应时间和错误率
- Lambda函数执行时间和内存使用
- DynamoDB读写容量使用率
- S3存储使用量

**告警配置**:
- 错误率超过阈值告警
- 资源使用量异常告警
- 成本超预算告警

**日志管理**:
- 结构化日志记录
- 集中式日志查询
- 错误追踪和分析

这种架构设计确保了系统的高性能、高可用性和成本效益，同时支持未来的功能扩展和业务增长。