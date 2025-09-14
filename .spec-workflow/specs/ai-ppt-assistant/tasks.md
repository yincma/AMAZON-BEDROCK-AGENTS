# 任务文档 - TDD分阶段开发

## 开发原则
- **TDD (测试驱动开发)**: 每个功能先写测试，再写实现
- **KISS**: 保持简单，避免过度设计
- **YAGNI**: 只实现当前需要的功能
- **迭代式交付**: 每个阶段都是可运行的产品

---

## Phase 1: MVP - 基础文本PPT生成 (Week 1)

### 目标
实现最简单的文本PPT生成功能，验证核心流程可行性。

### 1.1 环境准备 (Day 1)

- [X] 1.1.1 设置测试环境
  - 文件：tests/conftest.py
  - 配置pytest基础设置
  - 设置moto用于AWS服务模拟
  - 创建测试fixtures
  - TDD：定义测试框架

- [X] 1.1.2 编写基础设施测试
  - 文件：tests/test_infrastructure.py
  - 测试用例：S3桶应该存在
  - 测试用例：Lambda函数应该可调用
  - 测试用例：API端点应该返回200
  - TDD：定义期望的基础设施

- [X] 1.1.3 搭建最小化基础设施
  - 文件：infrastructure/main.tf
  - 创建一个S3桶
  - 创建一个Lambda函数（generate_ppt）
  - 创建API Gateway（POST /generate）
  - 目标：通过基础设施测试

### 1.2 内容生成功能 (Day 2-3)

- [X] 1.2.1 编写内容生成测试
  - 文件：tests/test_content_generator.py
  ```python
  def test_generate_outline():
      # Given: 主题和页数
      # When: 调用生成函数
      # Then: 返回正确格式的大纲

  def test_generate_slide_content():
      # Given: 大纲
      # When: 生成每页内容
      # Then: 返回标题和要点
  ```

- [X] 1.2.2 实现简单内容生成
  - 文件：lambdas/generate_ppt.py
  - 使用Bedrock Claude生成大纲
  - 为每页生成标题和3个要点
  - 保存到S3为单个JSON文件
  - 目标：通过内容生成测试

- [X] 1.2.3 集成测试
  - 文件：tests/test_integration.py
  - 测试完整流程：API → Lambda → S3
  - 验证JSON格式正确
  - 目标：端到端流程工作

### 1.3 PPT文件生成 (Day 4-5)

- [X] 1.3.1 编写PPT生成测试
  - 文件：tests/test_ppt_compiler.py
  ```python
  def test_create_simple_ppt():
      # Given: JSON内容
      # When: 调用编译函数
      # Then: 生成有效的PPTX文件

  def test_ppt_has_correct_slides():
      # Given: 5页内容
      # When: 生成PPT
      # Then: PPT包含5页
  ```

- [X] 1.3.2 实现PPT编译功能
  - 文件：lambdas/compile_ppt.py
  - 使用python-pptx创建简单PPT
  - 只包含标题和文字，无图片
  - 使用默认模板
  - 保存到S3并生成下载链接
  - 目标：通过PPT生成测试

### 1.4 API完善 (Day 5)

- [X] 1.4.1 编写API测试
  - 文件：tests/test_api.py
  ```python
  def test_generate_endpoint():
      # POST /generate
      # 返回 presentation_id

  def test_status_endpoint():
      # GET /status/{id}
      # 返回 进度信息

  def test_download_endpoint():
      # GET /download/{id}
      # 返回 下载链接
  ```

- [X] 1.4.2 实现API端点
  - 文件：lambdas/api_handler.py
  - POST /generate - 触发生成
  - GET /status/{id} - 查询状态
  - GET /download/{id} - 获取下载链接
  - 目标：通过API测试

### Phase 1 验收标准
✅ 能通过API生成简单文本PPT
✅ 包含5-10页内容
✅ 提供下载链接
✅ 所有测试通过（覆盖率>80%）
✅ 响应时间<30秒

---

## Phase 2: 增强功能 - 添加视觉元素 (Week 2)

### 目标
在MVP基础上添加图片生成和样式优化。

### 2.1 图片生成功能 (Day 6-7)

- [x] 2.1.1 编写图片生成测试
  - 文件：tests/test_image_generator.py
  ```python
  def test_generate_image_prompt():
      # Given: 幻灯片内容
      # When: 生成图片提示词
      # Then: 返回合适的提示词

  def test_save_image_to_s3():
      # Given: 图片URL
      # When: 保存到S3
      # Then: 返回S3路径
  ```

- [ ] 2.1.2 实现图片生成
  - 文件：lambdas/image_generator.py
  - 集成Amazon Nova（或使用占位图）
  - 为每页生成一张图片
  - 保存到S3
  - 目标：通过图片测试

### 2.2 PPT样式优化 (Day 8)

- [x] 2.2.1 编写样式测试
  - 文件：tests/test_ppt_styles.py
  ```python
  def test_apply_template():
      # Given: 模板ID
      # When: 应用模板
      # Then: PPT使用正确样式

  def test_add_images_to_slides():
      # Given: 图片路径
      # When: 添加到幻灯片
      # Then: 图片正确显示
  ```

- [ ] 2.2.2 实现样式功能
  - 文件：lambdas/ppt_styler.py
  - 添加2-3个简单模板
  - 将图片添加到幻灯片
  - 调整布局（文字+图片）
  - 目标：通过样式测试

### 2.3 演讲者备注 (Day 9)

- [x] 2.3.1 编写备注测试
  - 文件：tests/test_speaker_notes.py
  ```python
  def test_generate_notes():
      # Given: 幻灯片内容
      # When: 生成备注
      # Then: 返回相关备注
  ```

- [ ] 2.3.2 实现备注生成
  - 文件：lambdas/notes_generator.py
  - 使用Bedrock生成备注
  - 添加到PPT文件
  - 目标：通过备注测试

### Phase 2 验收标准
✅ PPT包含配图
✅ 支持模板选择
✅ 包含演讲者备注
✅ 新功能测试覆盖>80%
✅ 总体响应时间<60秒

---

## Phase 3: 高级功能 - 优化与扩展 (Week 3)

### 目标
添加内容修改、性能优化和监控。

### 3.1 内容修改API (Day 10-11)

- [ ] 3.1.1 编写修改测试
  - 文件：tests/test_content_update.py
  ```python
  def test_update_single_slide():
      # PATCH /presentations/{id}/slides/{n}
      # 更新单页内容

  def test_regenerate_image():
      # POST /presentations/{id}/slides/{n}/image
      # 重新生成图片
  ```

- [ ] 3.1.2 实现修改功能
  - 文件：lambdas/content_updater.py
  - 支持单页内容更新
  - 支持图片重新生成
  - 保持整体一致性
  - 目标：通过修改测试

### 3.2 性能优化 (Day 12)

- [ ] 3.2.1 编写性能测试
  - 文件：tests/test_performance.py
  ```python
  def test_parallel_generation():
      # 测试并行生成多页
      # 验证时间减少

  def test_caching():
      # 测试缓存机制
      # 验证重复请求更快
  ```

- [ ] 3.2.2 实现优化
  - 使用Step Functions编排
  - 并行处理页面生成
  - 添加简单缓存
  - 目标：响应时间<30秒

### 3.3 监控和日志 (Day 13)

- [ ] 3.3.1 编写监控测试
  - 文件：tests/test_monitoring.py
  - 验证日志记录
  - 验证指标上报

- [ ] 3.3.2 实现监控
  - CloudWatch日志组
  - 基础指标和告警
  - 错误追踪
  - 目标：可观测性

### Phase 3 验收标准
✅ 支持内容修改
✅ 性能提升50%
✅ 完整的监控体系
✅ 测试覆盖率>85%

---

## Phase 4: 生产就绪 (Week 4)

### 目标
文档完善、安全加固、部署自动化。

### 4.1 文档编写 (Day 14)

- [ ] 4.1.1 API文档
  - OpenAPI规范
  - 使用示例
  - 错误码说明

- [ ] 4.1.2 部署文档
  - 部署步骤
  - 环境配置
  - 故障排除

### Phase 4 验收标准
✅ 完整文档
✅ 可一键部署

---

## 成功指标

### 技术指标
- 测试覆盖率 > 85%
- 响应时间 < 30秒（10页PPT）
- 可用性 > 99%
- 错误率 < 1%

### 业务指标
- 用户满意度 > 80%
- 生成成功率 > 95%
- 平均生成时间 < 2分钟

### TDD执行标准
- 每个功能必须先有失败的测试
- 实现代码让测试通过
- 重构代码保持测试通过
- 测试代码与实现代码比例约 1:1

---

## 风险管理

### 技术风险
| 风险 | 缓解措施 |
|------|---------|
| Lambda超时 | Phase 3引入Step Functions |
| python-pptx兼容性 | Phase 1先验证，有问题换方案 |
| Bedrock限流 | 实现重试和队列机制 |

### 进度风险
| 风险 | 缓解措施 |
|------|---------|
| Phase 1延期 | 可去掉图片，只保留文本 |
| 测试编写耗时 | 使用测试模板和AI辅助 |
| 集成问题 | 每日集成，尽早发现问题 |

---

## 每日站会模板

```markdown
### 日期：[DATE]
**昨天完成：**
- [ ] 任务名称（测试/实现）

**今天计划：**
- [ ] 任务名称（测试/实现）

**遇到问题：**
- 问题描述和需要的帮助

**测试状态：**
- 通过：X个
- 失败：X个
- 覆盖率：X%
```