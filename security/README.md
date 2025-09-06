# AI PPT Assistant 安全扫描系统

本目录包含了AI PPT Assistant项目的完整安全扫描系统，提供多层次的安全检测和漏洞分析。

## 📋 功能概述

### 🔍 支持的扫描类型

1. **代码安全扫描 (Bandit)**
   - 静态代码分析
   - 常见安全漏洞检测
   - Python安全最佳实践检查

2. **依赖漏洞扫描 (Safety)**
   - 已知漏洞数据库检查
   - CVE漏洞识别
   - 依赖安全评估

3. **敏感信息检测 (detect-secrets)**
   - API密钥检测
   - 密码和令牌识别
   - 敏感配置泄露检查

4. **AWS安全最佳实践 (Checkov)**
   - Infrastructure as Code 安全检查
   - AWS服务配置验证
   - 合规性检查

## 🚀 快速开始

### 1. 安装安全扫描工具

```bash
# 方式1: 使用 Makefile (推荐)
make security-install

# 方式2: 直接运行安装脚本
bash security/install.sh
```

### 2. 运行安全扫描

```bash
# 运行完整安全扫描
make security-scan

# 运行CI/CD安全扫描 (发现高危问题时失败)
make security-scan-ci

# 生成详细HTML报告
make security-report
```

## 📊 命令详解

### Makefile 命令

| 命令 | 描述 | 用途 |
|------|------|------|
| `make security-install` | 安装所有安全扫描工具 | 初始化设置 |
| `make security-scan` | 运行完整安全扫描，控制台输出 | 日常开发检查 |
| `make security-scan-ci` | CI/CD安全扫描，发现高危问题时退出 | 持续集成 |
| `make security-report` | 生成详细HTML报告 | 详细分析和存档 |

### 直接使用扫描脚本

```bash
# 查看所有选项
python3 security/scan.py --help

# 运行特定扫描
python3 security/scan.py --scan bandit
python3 security/scan.py --scan safety
python3 security/scan.py --scan secrets
python3 security/scan.py --scan aws

# 指定输出格式
python3 security/scan.py --format console    # 控制台输出
python3 security/scan.py --format json       # JSON格式
python3 security/scan.py --format html       # HTML报告

# 指定输出目录
python3 security/scan.py --output-dir /path/to/reports

# CI模式 (高危问题时失败)
python3 security/scan.py --fail-on-high
```

## 📁 文件结构

```
security/
├── README.md              # 本文档
├── requirements.txt       # 安全工具依赖
├── install.sh            # 自动安装脚本
├── scan.py               # 主要扫描脚本
├── bandit.yaml           # Bandit配置
├── checkov.yaml          # Checkov配置
├── .secrets.baseline     # secrets检测基线
└── reports/              # 扫描报告目录
    ├── security_report_YYYYMMDD_HHMMSS.html
    └── security_report_YYYYMMDD_HHMMSS.json
```

## 🔧 配置说明

### Bandit 配置 (bandit.yaml)

```yaml
# 排除目录
exclude_dirs:
  - '.venv'
  - 'lambdas/layers/build'
  
# 跳过的检查
skips:
  - B101  # assert_used (测试中的assert是正常的)
```

### Checkov 配置 (checkov.yaml)

```yaml
# AWS安全检查
check:
  - CKV_AWS_20  # S3不允许公共读取
  - CKV_AWS_21  # S3不允许公共写入
  - CKV_AWS_58  # Lambda死信队列配置
```

### Secrets 检测配置 (.secrets.baseline)

- 自动检测各类敏感信息
- 支持自定义忽略规则
- 包含常见的云服务密钥检测

## 📈 严重性级别

| 级别 | 描述 | 示例 |
|------|------|------|
| **Critical** | 严重安全漏洞，需立即修复 | RCE漏洞、数据泄露 |
| **High** | 高风险安全问题 | XSS、CSRF、密钥泄露 |
| **Medium** | 中等风险问题 | 配置错误、弱加密 |
| **Low** | 低风险问题或建议 | 代码质量、最佳实践 |
| **Info** | 信息性提示 | 配置建议、文档问题 |

## 🔄 CI/CD 集成

### GitHub Actions 示例

```yaml
name: Security Scan
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: make install
      - name: Install security tools
        run: make security-install
      - name: Run security scan
        run: make security-scan-ci
```

### GitLab CI 示例

```yaml
security_scan:
  stage: test
  script:
    - make install
    - make security-install
    - make security-scan-ci
  artifacts:
    reports:
      junit: security/reports/security_report_*.json
    expire_in: 1 week
```

## 🛠 自定义配置

### 添加自定义检查

1. **扩展Bandit检查**
   ```bash
   # 编辑 security/bandit.yaml
   tests:
     - B999  # 添加自定义检查ID
   ```

2. **配置Secrets忽略**
   ```bash
   # 更新 security/.secrets.baseline
   detect-secrets scan --update security/.secrets.baseline
   ```

3. **自定义Checkov规则**
   ```bash
   # 编辑 security/checkov.yaml
   check:
     - CKV_CUSTOM_1  # 自定义规则
   ```

## 📊 报告格式

### 控制台报告
- 彩色输出
- 问题汇总
- 前3个高优先级问题详情

### JSON报告
```json
{
  "timestamp": "2024-12-07T12:00:00Z",
  "summary": {
    "total_issues": 5,
    "critical": 1,
    "high": 2,
    "medium": 1,
    "low": 1
  },
  "scans": {
    "bandit": {...},
    "safety": {...}
  }
}
```

### HTML报告
- 完整的Web界面
- 按工具分类的问题
- 可点击的详情
- 导出友好的格式

## 🔧 故障排除

### 常见问题

1. **工具未安装**
   ```bash
   Error: bandit not found
   解决: make security-install
   ```

2. **虚拟环境问题**
   ```bash
   Error: Virtual environment not found
   解决: make install
   ```

3. **权限问题**
   ```bash
   Error: Permission denied
   解决: chmod +x security/install.sh
   ```

### 调试模式

```bash
# 查看详细输出
python3 security/scan.py --scan bandit -v

# 检查工具版本
bandit --version
safety --version
detect-secrets --version
checkov --version
```

## 📝 最佳实践

### 开发流程集成

1. **预提交检查**
   ```bash
   # .pre-commit-config.yaml
   repos:
     - repo: local
       hooks:
         - id: security-scan
           name: Security Scan
           entry: make security-scan-ci
           language: system
   ```

2. **定期扫描**
   - 每日自动扫描
   - 依赖更新后扫描
   - 发布前完整扫描

3. **问题跟踪**
   - 建立安全问题基线
   - 跟踪修复进度
   - 定期安全评审

### 配置管理

1. **环境特定配置**
   - 开发环境: 完整扫描
   - 测试环境: CI模式
   - 生产环境: 严格模式

2. **忽略规则管理**
   - 文档化所有忽略
   - 定期审查忽略规则
   - 设置忽略过期时间

## 🤝 贡献指南

1. **添加新的扫描工具**
   - 更新 `requirements.txt`
   - 在 `scan.py` 中添加扫描方法
   - 更新配置文件

2. **改进报告格式**
   - 编辑报告模板
   - 添加新的输出格式
   - 优化用户体验

3. **测试**
   - 添加单元测试
   - 验证所有扫描工具
   - 测试不同的项目结构

## 📞 支持和反馈

如果遇到问题或有改进建议，请：

1. 查看本文档的故障排除部分
2. 检查 `security/reports/` 目录中的详细日志
3. 提交 Issue 或 Pull Request

---

**注意**: 安全扫描只是安全保障的一部分，还需要结合代码审查、渗透测试和持续监控等措施。