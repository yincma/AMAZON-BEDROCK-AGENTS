# 🔧 环境变量到Config文件迁移指南

## 📋 概述

本指南提供了从环境变量配置模式迁移到YAML配置文件的完整方案。新的配置系统提供更好的可维护性、版本控制支持和环境管理。

## 🎯 迁移优势

### 为什么要迁移？

| 方面 | 环境变量 | Config文件 | 改进 |
|------|----------|------------|------|
| **可维护性** | 分散在42个文件中 | 集中化配置 | ✅ 90%减少维护复杂度 |
| **版本控制** | 不易追踪变更 | Git友好的YAML | ✅ 完整的变更历史 |
| **环境管理** | 手动设置差异 | 环境特定文件 | ✅ 一键环境切换 |
| **类型安全** | 字符串类型 | 强类型验证 | ✅ 运行时错误减少 |
| **文档化** | 注释困难 | 内置注释支持 | ✅ 自文档化配置 |
| **敏感信息** | 明文存储 | SSM/Secrets集成 | ✅ 安全性提升 |

`★ Insight ─────────────────────────────────────`
关键架构改进：
• **渐进式迁移**：向后兼容，零停机时间迁移
• **智能回退**：Config文件 → 环境变量 → 默认值
• **变量插值**：支持 ${ENV:VAR}、${SSM:path}、${SECRET:name}
`─────────────────────────────────────────────────`

## 🏗️ 新配置架构

### 目录结构

```
config/
├── default.yaml              # 基础配置模板
├── environments/
│   ├── dev.yaml              # 开发环境配置  
│   ├── staging.yaml          # 预发布环境配置
│   └── prod.yaml             # 生产环境配置
└── migration_report.md       # 迁移报告
```

### 配置层次结构

```yaml
# 配置优先级：环境特定 > 默认配置 > 环境变量 > 硬编码默认值
aws:                          # AWS基础设施配置
  region: "us-east-1"
  profile: null

services:                     # 核心服务配置
  s3:
    bucket: "ai-ppt-assistant-dev-presentations"
    lifecycle:
      transition_to_ia_days: 30
  
  dynamodb:
    table: "ai-ppt-assistant-dev-sessions"
    ttl_days: 7
  
  bedrock:
    model_id: "anthropic.claude-4-0"
    orchestrator_agent_id: "${SSM:/ai-ppt/agent/orchestrator-id}"

performance:                  # 性能配置
  lambda:
    memory_sizes:
      create_outline: 1024
      compile_pptx: 3008
  max_concurrent_downloads: 5
  cache_ttl_seconds: 3600

security:                     # 安全配置
  vpc_enabled: true
  encryption_enabled: true
  external_apis:
    pexels_api_key: "${SECRET:ai-ppt/pexels-key}"

features:                     # 功能开关
  enable_speaker_notes: true
  enable_image_generation: true
```

## 🚀 迁移步骤

### Phase 1: 环境准备

**1. 安装依赖**
```bash
# 添加PyYAML支持
pip install PyYAML==6.0.1

# 更新Lambda层依赖
cd lambdas/layers
echo "PyYAML==6.0.1" >> requirements.txt
./build.sh
```

**2. 运行迁移脚本**
```bash
# 自动发现并迁移环境变量
cd scripts
python migrate_to_config.py --dry-run  # 预览迁移结果

# 执行实际迁移
python migrate_to_config.py --environments dev staging prod
```

**3. 验证生成的配置**
```bash
# 检查生成的配置文件
ls -la config/environments/
cat config/dev.yaml  # 查看开发环境配置
```

### Phase 2: 代码更新

**更新Lambda函数示例**

**旧版本（环境变量）：**
```python
# 旧方式 - 分散的环境变量
import os
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-4-0')
S3_BUCKET = os.environ.get('S3_BUCKET', 'default-bucket')
MAX_SLIDES = int(os.environ.get('MAX_SLIDES', '20'))
```

**新版本（Config文件）：**
```python
# 新方式 - 统一配置管理
from utils.enhanced_config_manager import get_enhanced_config_manager

config_manager = get_enhanced_config_manager()
bedrock_config = config_manager.get_bedrock_config()
s3_config = config_manager.get_s3_config()
performance_config = config_manager.get_performance_config()

MODEL_ID = bedrock_config.model_id
S3_BUCKET = s3_config.bucket
MAX_SLIDES = performance_config.max_slides
```

### Phase 3: 逐步替换

**示例：更新 create_outline.py**

```python
# 在文件顶部添加
from utils.enhanced_config_manager import (
    get_enhanced_config_manager,
    get_enhanced_service_config,
    get_enhanced_performance_config
)

# 替换环境变量获取
def lambda_handler(event, context):
    # 获取配置管理器
    config_manager = get_enhanced_config_manager(
        environment=os.environ.get('ENVIRONMENT', 'dev')
    )
    
    # 获取各类配置
    bedrock_config = config_manager.get_bedrock_config()
    s3_config = config_manager.get_s3_config()
    performance_config = config_manager.get_performance_config()
    
    # 使用类型化配置
    MODEL_ID = bedrock_config.model_id
    BUCKET_NAME = s3_config.bucket
    MAX_SLIDES = performance_config.max_slides
    
    # 配置验证
    validation_report = config_manager.validate_configuration()
    if validation_report['errors']:
        logger.error("Configuration validation failed", 
                    extra={"errors": validation_report['errors']})
        return create_error_response(500, "Configuration error")
```

### Phase 4: 部署更新

**1. 更新Terraform配置**
```hcl
# infrastructure/main.tf
# 添加配置文件支持
resource "aws_s3_object" "config_files" {
  for_each = fileset("${path.module}/../config/environments/", "*.yaml")
  
  bucket = aws_s3_bucket.config_bucket.bucket
  key    = "config/${each.value}"
  source = "${path.module}/../config/environments/${each.value}"
  
  etag = filemd5("${path.module}/../config/environments/${each.value}")
}

# 环境变量传递配置文件位置
resource "aws_lambda_function" "functions" {
  for_each = var.lambda_functions
  
  environment {
    variables = {
      ENVIRONMENT = var.environment
      CONFIG_S3_BUCKET = aws_s3_bucket.config_bucket.bucket
      CONFIG_S3_KEY = "config/${var.environment}.yaml"
    }
  }
}
```

**2. 更新部署脚本**
```bash
#!/bin/bash
# 更新deploy.sh添加配置文件同步

# 同步配置文件到S3
echo "📝 Uploading configuration files..."
aws s3 sync config/ s3://${PROJECT_NAME}-config-bucket/config/ \
  --exclude "*.md" \
  --exclude "migration_report.md"

# 验证配置文件
echo "✅ Validating configuration..."
python scripts/validate_config.py --environment ${ENVIRONMENT}
```

## 🔧 高级特性

### 1. 变量插值

**环境变量引用**
```yaml
aws:
  region: "${ENV:AWS_REGION}"  # 从环境变量获取
  
services:
  s3:
    bucket: "${ENV:PROJECT_NAME}-${ENV:ENVIRONMENT}-presentations"
```

**SSM参数引用**
```yaml
services:
  bedrock:
    orchestrator_agent_id: "${SSM:/ai-ppt-assistant/prod/bedrock/orchestrator-id}"
    content_agent_id: "${SSM:/ai-ppt-assistant/prod/bedrock/content-id}"
```

**Secrets Manager引用**
```yaml
security:
  external_apis:
    pexels_api_key: "${SECRET:ai-ppt-assistant/pexels-api-key}"
    unsplash_access_key: "${SECRET:ai-ppt-assistant/unsplash-key}"
```

### 2. 环境特定配置覆盖

**开发环境优化**
```yaml
# dev.yaml - 开发环境特定设置
performance:
  lambda:
    memory_sizes:
      create_outline: 512      # 降低内存使用
      compile_pptx: 1024      # 降低成本
  
  cache_ttl_seconds: 300       # 更短的缓存时间
  max_slides: 10               # 限制功能范围

development:
  enable_debug_mode: true
  mock_bedrock_calls: true     # 避免AI调用成本
  fast_mode: true              # 跳过某些验证
```

**生产环境优化**
```yaml
# prod.yaml - 生产环境特定设置
performance:
  lambda:
    memory_sizes:
      compile_pptx: 3008       # 最大内存支持复杂PPT
    reserved_concurrency:
      create_outline: 10       # 更高并发
  
security:
  vpc_enabled: true
  encryption_enabled: true
  enable_monitoring: true

production:
  backup_enabled: true
  auto_scaling:
    target_utilization: 70
    max_capacity: 100
```

### 3. 配置验证和类型安全

```python
# 自动配置验证
def lambda_handler(event, context):
    config_manager = get_enhanced_config_manager()
    
    # 验证配置完整性
    validation_report = config_manager.validate_configuration()
    
    if validation_report['errors']:
        logger.error("Critical configuration errors found", 
                    extra={"errors": validation_report['errors']})
        raise RuntimeError("Configuration validation failed")
    
    if validation_report['warnings']:
        logger.warning("Configuration warnings", 
                      extra={"warnings": validation_report['warnings']})
    
    # 获取类型化配置
    performance_config = config_manager.get_performance_config()
    
    # IDE自动补全和类型检查
    max_memory = performance_config.lambda.memory_sizes["compile_pptx"]  # 类型：int
    timeout = performance_config.lambda.timeouts["compile_pptx"]         # 类型：int
```

## 📊 迁移验证和测试

### 验证清单

```bash
# 1. 配置文件语法验证
python -c "import yaml; yaml.safe_load(open('config/environments/prod.yaml'))"

# 2. 配置完整性验证
python scripts/validate_config.py --environment prod --strict

# 3. 向后兼容性测试
ENV_VAR_MODE=true python test_lambda_function.py
CONFIG_FILE_MODE=true python test_lambda_function.py

# 4. 端到端功能测试
make test-e2e ENVIRONMENT=dev CONFIG_MODE=file
```

### A/B测试部署

```python
# 支持A/B测试的配置加载
def get_config_with_fallback():
    """支持渐进式迁移的配置获取"""
    
    try:
        # 尝试加载配置文件
        if os.environ.get('USE_CONFIG_FILE', 'true').lower() == 'true':
            return get_enhanced_config_manager()
    except Exception as e:
        logger.warning(f"Config file loading failed, falling back to env vars: {e}")
    
    # 回退到原有的ConfigManager
    from utils.config_manager import get_config_manager
    return get_config_manager()
```

## 🔒 安全考虑

### 敏感信息管理

**1. Secrets Manager集成**
```yaml
# 生产环境配置
security:
  external_apis:
    pexels_api_key: "${SECRET:ai-ppt-assistant/prod/pexels-api-key}"
    openai_api_key: "${SECRET:ai-ppt-assistant/prod/openai-api-key}"
    
  database:
    password: "${SECRET:ai-ppt-assistant/prod/db-password}"
```

**2. IAM权限更新**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/ai-ppt-assistant/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:ai-ppt-assistant/*"
    }
  ]
}
```

**3. 配置文件加密**
```bash
# 使用AWS KMS加密敏感配置
aws kms encrypt \
  --key-id arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012 \
  --plaintext fileb://config/environments/prod.yaml \
  --output text --query CiphertextBlob | base64 -d > config/environments/prod.yaml.encrypted
```

## 🚨 故障排除

### 常见问题和解决方案

**1. PyYAML导入失败**
```bash
# 症状：ImportError: No module named 'yaml'
# 解决方案：
pip install PyYAML==6.0.1
# 或者在Lambda层中确保包含PyYAML
```

**2. 配置文件路径问题**
```python
# 症状：FileNotFoundError: config file not found
# 解决方案：显式指定配置目录
config_manager = get_enhanced_config_manager(
    environment='prod',
    config_dir='/opt/python/config'  # Lambda层中的路径
)
```

**3. 变量插值失败**
```bash
# 症状：配置值仍为 ${SSM:...} 字符串
# 解决方案：检查IAM权限和参数存在性
aws ssm get-parameter --name "/ai-ppt-assistant/prod/bedrock/agent-id" --with-decryption
```

**4. 类型转换错误**
```yaml
# 症状：Expected int but got str
# 解决方案：确保YAML类型正确
performance:
  max_slides: 20          # ✅ 正确：整数
  max_slides: "20"        # ❌ 错误：字符串
  enable_cache: true      # ✅ 正确：布尔值
  enable_cache: "true"    # ❌ 错误：字符串
```

## 📈 性能优化

### 配置缓存策略

```python
class EnhancedConfigManager:
    def __init__(self):
        self._cache_ttl = 300  # 5分钟缓存
        self._config_cache = {}
        self._last_loaded = None
    
    def get_config_with_cache(self, force_reload=False):
        now = datetime.now()
        
        if (force_reload or 
            self._last_loaded is None or 
            (now - self._last_loaded).seconds > self._cache_ttl):
            
            self._load_configuration()
            self._last_loaded = now
        
        return self._config_cache
```

### Lambda冷启动优化

```python
# 全局初始化配置管理器
config_manager = None

def get_global_config_manager():
    """复用配置管理器实例，减少冷启动时间"""
    global config_manager
    if config_manager is None:
        config_manager = get_enhanced_config_manager()
    return config_manager

def lambda_handler(event, context):
    # 复用全局配置管理器
    config = get_global_config_manager()
    
    # ... Lambda函数逻辑
```

## 🎯 迁移时间线

| 阶段 | 持续时间 | 主要任务 | 风险级别 |
|------|----------|----------|----------|
| **Phase 1** | 1-2天 | 环境准备、脚本执行、配置生成 | 低 |
| **Phase 2** | 3-5天 | 代码更新、单元测试、集成测试 | 中 |
| **Phase 3** | 2-3天 | 部署更新、A/B测试、监控设置 | 中高 |
| **Phase 4** | 1-2天 | 全量切换、验证、清理 | 低 |

**总计：7-12天**

## ✅ 迁移完成验证

### 最终检查清单

- [ ] 所有环境的配置文件已生成并验证
- [ ] PyYAML依赖已添加到Lambda层
- [ ] 至少2个Lambda函数已迁移并测试
- [ ] A/B测试显示新配置系统工作正常  
- [ ] 敏感信息已迁移到Secrets Manager
- [ ] 监控和告警正常工作
- [ ] 部署脚本已更新
- [ ] 团队成员已培训新配置系统
- [ ] 回退方案已准备并测试
- [ ] 文档已更新

恭喜！你已成功完成从环境变量到Config文件的迁移。新的配置系统将为你的项目带来更好的可维护性、安全性和可扩展性。