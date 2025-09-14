# AI-PPT-Assistant 图片生成功能安全审查报告

**审查日期**: 2025-01-14
**审查范围**: 图片生成功能的安全性和最佳实践
**审查人**: Security Auditor
**项目路径**: `/Users/umatoratatsu/Documents/AWS/AWS-Handson/ABA/AMAZON-BEDROCK-AGENTS`

## 执行摘要

本次安全审查重点关注AI-PPT-Assistant项目中图片生成功能的安全性。审查发现了多个需要立即修复的安全问题，包括硬编码配置、IAM权限过度宽泛、缺乏输入验证等。项目整体安全成熟度评级为：**中等风险**。

### 关键发现
- **3个高风险问题** - 需要立即修复
- **5个中风险问题** - 应在下个版本修复
- **8个低风险问题** - 建议改进

## 1. 安全风险评估

### 1.1 高风险问题

#### H1: 硬编码的敏感配置
**位置**: `lambdas/image_config.py`
```python
DEFAULT_BUCKET: str = "ai-ppt-presentations-test"  # 硬编码bucket名称
NOVA_MODEL_ID: str = "amazon.nova-canvas-v1:0"     # 硬编码模型ID
```
**风险**:
- 敏感信息暴露在代码中
- 无法在不同环境间灵活切换
- 违反了配置外部化原则

**影响**: 信息泄露、环境配置混乱

#### H2: IAM权限过度宽泛
**位置**: `infrastructure/main.tf`
```hcl
Resource = "arn:aws:logs:*:*:*"  # 允许访问所有日志
Resource = "arn:aws:bedrock:*:*:foundation-model/amazon.nova-*"  # 过于宽泛
```
**风险**:
- 违反最小权限原则
- 潜在的权限提升风险
- 可能访问未授权资源

**影响**: 权限滥用、数据泄露

#### H3: 缺乏请求签名验证
**位置**: API Gateway配置
```hcl
authorization = "NONE"  # 所有端点都没有认证
```
**风险**:
- API完全开放，无认证机制
- 容易受到DDoS攻击
- 无法追踪API使用情况

**影响**: 服务滥用、成本失控

### 1.2 中风险问题

#### M1: 不充分的输入验证
**位置**: `lambdas/image_processing_service.py`
```python
def generate_prompt(self, slide_content: Dict[str, Any], target_audience: str = "business") -> str:
    title = slide_content.get('title', '').strip()  # 缺乏内容过滤
    # 没有检查恶意内容或注入攻击
```
**风险**: 提示注入攻击、生成不当内容

#### M2: 错误处理中的信息泄露
**位置**: 多个Lambda函数
```python
except Exception as e:
    logger.error(f"处理Nova响应时出错: {str(e)}")  # 可能泄露敏感信息
    raise NovaServiceError(f"处理Nova响应时出错: {str(e)}")
```
**风险**: 详细错误信息可能暴露系统内部结构

#### M3: S3存储缺乏加密配置验证
**位置**: `lambdas/image_s3_service.py`
```python
self.s3_client.put_object(
    Bucket=self.bucket_name,
    Key=key,
    Body=image_data,
    ContentType='image/png'
    # 缺少ServerSideEncryption参数
)
```

#### M4: 缺少速率限制
**位置**: API Gateway配置
- 没有配置API速率限制
- 没有实现请求限流机制

#### M5: 日志中可能包含敏感信息
**位置**: `lambdas/logging_manager.py`
```python
logger.info(f"Nova API调用成功，生成真实AI图片")  # 可能记录敏感参数
```

### 1.3 低风险问题

1. **缺少安全响应头**: API响应缺少安全相关的HTTP头
2. **没有实现审计日志**: 缺乏完整的操作审计跟踪
3. **缺少数据分类标记**: 未对敏感数据进行分类
4. **没有实现密钥轮换**: 缺少自动密钥轮换机制
5. **缺少安全监控告警**: 没有配置安全事件监控
6. **代码依赖未扫描**: 缺少依赖项安全扫描
7. **缺少安全测试**: 没有自动化安全测试
8. **文档中缺少安全指南**: 缺少安全操作文档

## 2. 合规性评估

### 2.1 AWS Well-Architected Framework - 安全支柱

| 要求 | 当前状态 | 合规性 |
|------|---------|--------|
| 身份和访问管理 | IAM权限过于宽泛 | ❌ 不合规 |
| 检测控制 | 缺少安全监控 | ❌ 不合规 |
| 基础设施保护 | 基本配置存在 | ⚠️ 部分合规 |
| 数据保护 | S3加密已启用 | ✅ 合规 |
| 事件响应 | 缺少响应计划 | ❌ 不合规 |

### 2.2 数据保护合规性

| 标准 | 要求 | 当前状态 |
|------|------|---------|
| GDPR | 数据加密 | ⚠️ 传输加密存在，静态加密需验证 |
| GDPR | 访问控制 | ❌ 缺少细粒度访问控制 |
| GDPR | 审计日志 | ❌ 审计不完整 |
| PCI-DSS | 网络隔离 | ⚠️ 未使用VPC |
| SOC 2 | 变更管理 | ⚠️ 缺少正式流程 |

## 3. 安全最佳实践建议

### 3.1 立即修复（P0）

#### 1. 实现API认证和授权
```python
# 建议使用AWS Cognito或API密钥
def validate_api_key(api_key: str) -> bool:
    """验证API密钥"""
    secrets_client = boto3.client('secretsmanager')
    try:
        secret_value = secrets_client.get_secret_value(
            SecretId='ai-ppt-api-keys'
        )
        valid_keys = json.loads(secret_value['SecretString'])
        return api_key in valid_keys.values()
    except Exception:
        return False
```

#### 2. 移除硬编码配置
```python
# image_config.py 改进版本
@dataclass(frozen=True)
class ImageConfig:
    """图片生成配置类"""

    @classmethod
    def from_ssm(cls) -> 'ImageConfig':
        """从AWS Systems Manager Parameter Store加载配置"""
        ssm = boto3.client('ssm')

        def get_parameter(name: str, default: str = None) -> str:
            try:
                response = ssm.get_parameter(
                    Name=f'/ai-ppt/{os.environ["ENVIRONMENT"]}/{name}',
                    WithDecryption=True
                )
                return response['Parameter']['Value']
            except:
                if default:
                    return default
                raise ConfigurationError(f"Missing required parameter: {name}")

        return cls(
            DEFAULT_BUCKET=get_parameter('s3_bucket'),
            NOVA_MODEL_ID=get_parameter('nova_model_id'),
            DEFAULT_IMAGE_WIDTH=int(get_parameter('image_width', '1200')),
            DEFAULT_IMAGE_HEIGHT=int(get_parameter('image_height', '800'))
        )
```

#### 3. 实施最小权限IAM策略
```hcl
# 改进的IAM策略
resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda-policy-least-privilege"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.presentations.arn}/presentations/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-server-side-encryption": "AES256"
          }
        }
      },
      {
        Sid    = "BedrockAccess"
        Effect = "Allow"
        Action = ["bedrock:InvokeModel"]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}:*:foundation-model/amazon.nova-canvas-v1:0"
        ]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.function_name}:*"
      }
    ]
  })
}
```

### 3.2 短期改进（P1）

#### 1. 增强输入验证和内容过滤
```python
import re
from typing import List
import hashlib

class ContentValidator:
    """内容验证和过滤器"""

    # 禁止的关键词列表（应从外部配置加载）
    BLOCKED_KEYWORDS = []

    # 提示注入模式
    INJECTION_PATTERNS = [
        r'ignore previous instructions',
        r'system:',
        r'admin:',
        r'<script',
        r'javascript:',
        r'data:text/html'
    ]

    @classmethod
    def validate_prompt(cls, prompt: str) -> tuple[bool, str]:
        """验证提示词安全性"""
        # 长度检查
        if len(prompt) > 1000:
            return False, "Prompt too long"

        # 注入检测
        prompt_lower = prompt.lower()
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, prompt_lower):
                return False, f"Potential injection detected"

        # 敏感词过滤
        for keyword in cls.BLOCKED_KEYWORDS:
            if keyword in prompt_lower:
                return False, f"Blocked content detected"

        return True, "Valid"

    @classmethod
    def sanitize_input(cls, text: str) -> str:
        """清理输入文本"""
        # 移除控制字符
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        # 移除多余空白
        text = ' '.join(text.split())
        # HTML实体编码
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return text[:500]  # 限制长度
```

#### 2. 实现请求签名和速率限制
```python
import time
import hmac
import hashlib
from functools import wraps

class RateLimiter:
    """API速率限制器"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    def is_allowed(self, client_id: str) -> bool:
        """检查是否允许请求"""
        current_time = time.time()
        window_start = current_time - self.window_seconds

        # 清理过期记录
        if client_id in self.requests:
            self.requests[client_id] = [
                t for t in self.requests[client_id]
                if t > window_start
            ]
        else:
            self.requests[client_id] = []

        # 检查速率
        if len(self.requests[client_id]) >= self.max_requests:
            return False

        self.requests[client_id].append(current_time)
        return True

def verify_request_signature(request_body: str, signature: str, secret: str) -> bool:
    """验证请求签名"""
    expected_signature = hmac.new(
        secret.encode(),
        request_body.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)
```

#### 3. 安全的错误处理
```python
class SecureErrorHandler:
    """安全的错误处理器"""

    ERROR_MAPPINGS = {
        'ValidationError': 'Invalid input provided',
        'NovaServiceError': 'Image generation service unavailable',
        'S3OperationError': 'Storage operation failed',
        'ConfigurationError': 'Service configuration error'
    }

    @classmethod
    def handle_error(cls, error: Exception, context: dict = None) -> dict:
        """安全地处理错误"""
        error_type = type(error).__name__

        # 记录详细错误（仅在内部日志）
        logger.error(
            f"Error occurred",
            extra={
                'error_type': error_type,
                'error_message': str(error),
                'context': context,
                'trace_id': context.get('trace_id') if context else None
            }
        )

        # 返回通用错误消息给客户端
        client_message = cls.ERROR_MAPPINGS.get(
            error_type,
            'An error occurred processing your request'
        )

        return {
            'error': client_message,
            'request_id': context.get('request_id') if context else None,
            'timestamp': datetime.utcnow().isoformat()
        }
```

### 3.3 长期改进（P2）

#### 1. 实现完整的审计系统
```python
class AuditLogger:
    """审计日志系统"""

    def __init__(self, table_name: str = 'audit-logs'):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def log_event(self, event_type: str, details: dict):
        """记录审计事件"""
        self.table.put_item(
            Item={
                'event_id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'user_id': details.get('user_id'),
                'resource': details.get('resource'),
                'action': details.get('action'),
                'result': details.get('result'),
                'ip_address': details.get('ip_address'),
                'user_agent': details.get('user_agent'),
                'details': json.dumps(details)
            }
        )
```

#### 2. 实现安全监控和告警
```python
class SecurityMonitor:
    """安全监控系统"""

    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.sns = boto3.client('sns')

    def check_anomalies(self):
        """检查异常行为"""
        metrics = [
            ('FailedAuthentications', 5, 300),  # 5次失败/5分钟
            ('InvalidInputs', 10, 300),         # 10次无效输入/5分钟
            ('RateLimitExceeded', 20, 3600),    # 20次超限/小时
        ]

        for metric_name, threshold, period in metrics:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AI-PPT-Security',
                MetricName=metric_name,
                Dimensions=[],
                StartTime=datetime.utcnow() - timedelta(seconds=period),
                EndTime=datetime.utcnow(),
                Period=period,
                Statistics=['Sum']
            )

            if response['Datapoints']:
                value = response['Datapoints'][0]['Sum']
                if value > threshold:
                    self.send_alert(metric_name, value, threshold)

    def send_alert(self, metric: str, value: float, threshold: float):
        """发送安全告警"""
        self.sns.publish(
            TopicArn=os.environ['SECURITY_ALERT_TOPIC'],
            Subject=f'Security Alert: {metric}',
            Message=f'Threshold exceeded: {value} > {threshold}'
        )
```

## 4. 安全配置模板

### 4.1 AWS Systems Manager参数配置
```bash
# 创建加密参数
aws ssm put-parameter \
    --name "/ai-ppt/prod/nova_model_id" \
    --value "amazon.nova-canvas-v1:0" \
    --type "SecureString" \
    --key-id "alias/aws/ssm"

aws ssm put-parameter \
    --name "/ai-ppt/prod/s3_bucket" \
    --value "ai-ppt-presentations-prod" \
    --type "SecureString"

aws ssm put-parameter \
    --name "/ai-ppt/prod/api_keys" \
    --value '{"client1": "key1", "client2": "key2"}' \
    --type "SecureString"
```

### 4.2 环境变量配置模板
```yaml
# config/security.yaml
security:
  api:
    rate_limit:
      requests_per_minute: 60
      requests_per_hour: 1000
    authentication:
      enabled: true
      type: "api_key"  # or "cognito", "iam"
    cors:
      allowed_origins:
        - "https://app.example.com"
      allowed_methods:
        - "GET"
        - "POST"
      max_age: 3600

  encryption:
    at_rest:
      enabled: true
      algorithm: "AES256"
    in_transit:
      enabled: true
      tls_version: "1.2"

  logging:
    audit:
      enabled: true
      retention_days: 90
    sensitive_data_masking: true
    log_level: "INFO"

  monitoring:
    cloudwatch:
      enabled: true
      alarm_thresholds:
        error_rate: 0.01
        latency_p99: 3000
    xray:
      enabled: true
      sampling_rate: 0.1
```

### 4.3 安全响应头配置
```python
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'",
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
}
```

## 5. 合规性检查清单

### 5.1 部署前检查
- [ ] 所有敏感配置已外部化
- [ ] IAM权限遵循最小权限原则
- [ ] API认证机制已实施
- [ ] 输入验证和清理已实现
- [ ] 错误处理不泄露敏感信息
- [ ] 所有数据传输使用TLS
- [ ] S3存储启用加密
- [ ] 审计日志已配置
- [ ] 安全监控已启用
- [ ] 依赖项已扫描漏洞

### 5.2 运行时监控
- [ ] API速率限制正常工作
- [ ] 异常行为告警已配置
- [ ] 日志不包含敏感信息
- [ ] 访问控制正常运行
- [ ] 加密密钥定期轮换
- [ ] 安全事件响应流程就绪

### 5.3 定期审查
- [ ] 月度：审查IAM权限
- [ ] 季度：更新依赖项
- [ ] 季度：审查安全配置
- [ ] 半年：渗透测试
- [ ] 年度：完整安全审计

## 6. 修复优先级和时间表

### 阶段1：紧急修复（1周内）
1. 实施API认证 - **2天**
2. 移除硬编码配置 - **1天**
3. 修复IAM权限 - **2天**
4. 增强输入验证 - **2天**

### 阶段2：短期改进（1个月内）
1. 实现速率限制 - **3天**
2. 改进错误处理 - **2天**
3. 配置安全监控 - **3天**
4. 实施审计日志 - **3天**

### 阶段3：长期优化（3个月内）
1. 完整的安全自动化测试 - **1周**
2. 高级威胁检测 - **2周**
3. 合规性自动化 - **2周**
4. 安全培训和文档 - **持续**

## 7. 总结和建议

### 关键行动项
1. **立即**：实施API认证和移除硬编码配置
2. **本周**：修复IAM权限和增强输入验证
3. **本月**：完成所有P1修复项
4. **季度**：实现完整的安全监控和审计体系

### 风险缓解策略
1. 在修复完成前，限制API访问仅限内部网络
2. 增加CloudWatch告警监控异常活动
3. 每日审查日志寻找可疑行为
4. 准备事件响应计划

### 持续改进建议
1. 建立安全评审流程
2. 定期进行安全培训
3. 实施DevSecOps实践
4. 参与AWS Well-Architected评审

## 附录

### A. 安全工具推荐
- **SAST**: SonarQube, Checkmarx
- **DAST**: OWASP ZAP, Burp Suite
- **依赖扫描**: Snyk, GitHub Security
- **合规扫描**: AWS Config, AWS Security Hub
- **日志分析**: AWS CloudWatch Insights, Splunk

### B. 参考资源
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### C. 联系信息
- 安全团队: security@example.com
- 紧急响应: +1-xxx-xxx-xxxx
- AWS Support: Premium Support Plan

---

**文档版本**: 1.0
**最后更新**: 2025-01-14
**下次审查**: 2025-02-14
**分类级别**: 内部机密