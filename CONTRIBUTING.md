# 🤝 贡献指南 - AI PPT Assistant

感谢您对AI PPT Assistant项目的关注！本指南将帮助您了解如何为项目做出贡献。

## 📋 目录

- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [提交流程](#提交流程)
- [测试要求](#测试要求)
- [文档标准](#文档标准)
- [问题报告](#问题报告)

## 🛠 开发环境设置

### 1. 克隆项目

```bash
git clone <repository-url>
cd Amazon-Bedrock-Agents
```

### 2. Python环境

```bash
# 创建虚拟环境 (必须使用Python 3.13)
python3 -m venv venv-py313
source venv-py313/bin/activate

# 验证Python版本
python --version  # 应显示Python 3.13.x

# 安装开发依赖
pip install -r requirements.txt
pip install pytest black isort flake8 coverage
```

### 3. 配置AWS环境

```bash
# 配置AWS CLI
aws configure

# 验证权限
aws sts get-caller-identity
```

### 4. 设置开发配置

```bash
# 复制配置模板
cp config/environments/dev.yaml.example config/environments/dev.yaml

# 编辑配置文件
vim config/environments/dev.yaml
```

## 📝 代码规范

### Python代码风格

我们使用以下工具确保代码质量：

- **Black**: 代码格式化
- **isort**: 导入语句排序
- **flake8**: 代码检查
- **pytest**: 单元测试

### 格式化命令

```bash
# 自动格式化代码
black lambdas/ --line-length 100
isort lambdas/ --profile black

# 代码检查
flake8 lambdas/ --max-line-length 100 --ignore E203,W503

# 运行测试
pytest tests/ -v --cov=lambdas
```

### 命名规范

- **文件名**: snake_case
- **函数名**: snake_case
- **类名**: PascalCase
- **常量**: UPPER_CASE
- **变量**: snake_case

### 代码质量标准

```python
# ✅ 良好示例
class SessionManager:
    """会话管理器"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.config = get_config()
    
    def create_session(self, user_id: str, project_name: str) -> dict:
        """创建新会话"""
        session_id = self._generate_session_id()
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'project_name': project_name,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        return self._save_session(session_data)

# ❌ 避免的写法
def createSession(userId, projectName):
    sessionId = "session123"  # 硬编码
    # 没有类型提示和文档
    return {"id": sessionId}
```

## 🔄 提交流程

### 1. 分支管理

```bash
# 从main分支创建功能分支
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 或者从dev分支创建
git checkout dev
git pull origin dev
git checkout -b feature/your-feature-name
```

### 2. 提交规范

使用[约定式提交](https://www.conventionalcommits.org/)格式：

```
<类型>(<范围>): <描述>

[可选的正文]

[可选的脚注]
```

**类型**:
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建工具或辅助工具的变动

**示例**:
```bash
git commit -m "feat(session): 添加会话管理功能"
git commit -m "fix(api): 修复API Gateway CORS配置问题"
git commit -m "docs(readme): 更新部署说明"
```

### 3. Pull Request流程

1. **确保代码质量**:
```bash
# 运行所有检查
make lint      # 或手动运行格式化工具
make test      # 或 pytest tests/
```

2. **创建Pull Request**:
- 清晰的标题和描述
- 关联相关的Issue
- 包含测试证据
- 更新相关文档

3. **PR模板**:
```markdown
## 📝 变更描述
简要描述此PR的变更内容

## 🎯 变更类型
- [ ] 新功能
- [ ] Bug修复
- [ ] 文档更新
- [ ] 重构
- [ ] 性能优化

## 🧪 测试
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试完成

## 📋 检查清单
- [ ] 代码已格式化
- [ ] 测试覆盖率满足要求
- [ ] 文档已更新
- [ ] 没有硬编码值
```

## 🧪 测试要求

### 测试金字塔

```
     E2E (10%)
    ─────────────
   集成测试 (20%)
  ─────────────────
 单元测试 (70%)
───────────────────
```

### 测试覆盖率标准

- **单元测试**: ≥80%覆盖率
- **集成测试**: 核心API流程100%覆盖
- **E2E测试**: 主要用户流程覆盖

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 生成覆盖率报告
pytest tests/ --cov=lambdas --cov-report=html

# 运行特定测试
pytest tests/test_session_manager.py -v
```

### 测试示例

```python
import pytest
from unittest.mock import Mock, patch
from lambdas.session_manager.handler import SessionManager

class TestSessionManager:
    @pytest.fixture
    def session_manager(self):
        return SessionManager("test-table")
    
    def test_create_session_success(self, session_manager):
        """测试成功创建会话"""
        # Given
        user_id = "test_user"
        project_name = "test_project"
        
        # When
        result = session_manager.create_session(user_id, project_name)
        
        # Then
        assert result['statusCode'] == 200
        assert 'session_id' in result['body']
    
    @patch('boto3.client')
    def test_create_session_with_dynamodb_error(self, mock_boto, session_manager):
        """测试DynamoDB错误处理"""
        # Given
        mock_boto.return_value.put_item.side_effect = Exception("DynamoDB Error")
        
        # When & Then
        with pytest.raises(Exception):
            session_manager.create_session("user", "project")
```

## 📚 文档标准

### 代码文档

```python
class ContentEnhancer:
    """内容增强器
    
    使用Amazon Bedrock优化和增强PPT内容。
    
    Attributes:
        model_id: Bedrock模型ID
        config: 配置管理器实例
        
    Example:
        enhancer = ContentEnhancer()
        result = enhancer.enhance_content("原始内容")
    """
    
    def enhance_content(self, content: str, context: dict = None) -> dict:
        """增强内容质量
        
        Args:
            content: 原始内容文本
            context: 可选的上下文信息
            
        Returns:
            dict: 包含增强后内容的响应
            
        Raises:
            BedrockError: 当Bedrock服务调用失败时
            ValidationError: 当输入参数无效时
        """
        pass
```

### 文档结构

- **README.md**: 项目概述和快速开始
- **API.md**: API接口文档
- **DEPLOYMENT.md**: 部署指南
- **TROUBLESHOOTING.md**: 故障排除
- **CONTRIBUTING.md**: 本文档

## 🐛 问题报告

### 报告Bug

使用以下模板创建Issue:

```markdown
## 🐛 Bug描述
简要描述遇到的问题

## 🔄 重现步骤
1. 
2. 
3. 

## 🎯 期望行为
描述期望的正确行为

## 📱 环境信息
- OS: 
- Python版本: 
- AWS Region: 
- Lambda运行时: 

## 📸 截图/日志
如果适用，添加截图或错误日志
```

### 功能请求

```markdown
## ✨ 功能描述
清楚描述您希望的功能

## 🎯 使用场景
解释为什么需要这个功能

## 💡 替代方案
描述您考虑过的其他解决方案
```

## 🚀 发布流程

### 版本号规则

使用[语义化版本](https://semver.org/)：`MAJOR.MINOR.PATCH`

- **MAJOR**: 不兼容的API变更
- **MINOR**: 向后兼容的功能性新增
- **PATCH**: 向后兼容的错误修正

### 发布检查清单

- [ ] 所有测试通过
- [ ] 代码审查完成
- [ ] 文档已更新
- [ ] 版本号已更新
- [ ] 变更日志已更新
- [ ] 部署测试完成

## 📞 获取帮助

- 💬 **讨论**: 在GitHub Discussions中提问
- 🐛 **Bug报告**: 创建GitHub Issue
- 📧 **私人咨询**: 联系项目维护者

---

感谢您的贡献！🎉