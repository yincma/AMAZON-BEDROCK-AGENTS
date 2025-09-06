#!/bin/bash
# 安全扫描工具安装脚本
# 为AI PPT Assistant项目安装和配置安全扫描工具

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info "Installing security scanning tools for AI PPT Assistant..."
log_info "Project root: $PROJECT_ROOT"
log_info "Security directory: $SCRIPT_DIR"

# 检查Python版本
PYTHON_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2 | cut -d'.' -f1,2)
if [[ -z "$PYTHON_VERSION" ]]; then
    log_error "Python 3 is not installed or not in PATH"
    exit 1
fi

log_info "Using Python version: $PYTHON_VERSION"

# 检查虚拟环境
VENV_DIR="$PROJECT_ROOT/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    log_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# 激活虚拟环境
log_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# 检查pip版本并升级
log_info "Upgrading pip..."
pip install --upgrade pip

# 安装安全扫描工具依赖
log_info "Installing security scanning dependencies..."
if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
    pip install -r "$SCRIPT_DIR/requirements.txt"
    log_success "Security dependencies installed successfully"
else
    log_error "Security requirements.txt not found at $SCRIPT_DIR/requirements.txt"
    exit 1
fi

# 创建必要的目录
log_info "Creating necessary directories..."
mkdir -p "$SCRIPT_DIR/reports"
mkdir -p "$SCRIPT_DIR/config"

# 设置脚本权限
log_info "Setting script permissions..."
chmod +x "$SCRIPT_DIR/scan.py"

# 验证工具安装
log_info "Verifying security tool installations..."

# 检查bandit
if command -v bandit &> /dev/null; then
    BANDIT_VERSION=$(bandit --version 2>/dev/null | head -1 | cut -d' ' -f2)
    log_success "Bandit installed: $BANDIT_VERSION"
else
    log_warning "Bandit installation verification failed"
fi

# 检查safety
if command -v safety &> /dev/null; then
    SAFETY_VERSION=$(safety --version 2>/dev/null | cut -d' ' -f2)
    log_success "Safety installed: $SAFETY_VERSION"
else
    log_warning "Safety installation verification failed"
fi

# 检查detect-secrets
if command -v detect-secrets &> /dev/null; then
    SECRETS_VERSION=$(detect-secrets --version 2>/dev/null)
    log_success "detect-secrets installed: $SECRETS_VERSION"
else
    log_warning "detect-secrets installation verification failed"
fi

# 检查checkov
if command -v checkov &> /dev/null; then
    CHECKOV_VERSION=$(checkov --version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
    log_success "Checkov installed: $CHECKOV_VERSION"
else
    log_warning "Checkov installation verification failed"
fi

# 创建符号链接到项目根目录（可选）
if [[ ! -L "$PROJECT_ROOT/security-scan" ]]; then
    log_info "Creating security-scan symlink..."
    ln -s "$SCRIPT_DIR/scan.py" "$PROJECT_ROOT/security-scan"
    log_success "Created security-scan symlink at project root"
fi

# 初始化detect-secrets baseline
log_info "Initializing detect-secrets baseline..."
cd "$PROJECT_ROOT"
if [[ -f "$SCRIPT_DIR/.secrets.baseline" ]]; then
    log_info "Using existing secrets baseline configuration"
else
    log_info "Creating new secrets baseline..."
    detect-secrets scan --all-files --baseline "$SCRIPT_DIR/.secrets.baseline" || true
fi

# 创建安全扫描配置的符号链接
log_info "Setting up configuration files..."
if [[ ! -f "$PROJECT_ROOT/.bandit" ]]; then
    ln -s "security/bandit.yaml" "$PROJECT_ROOT/.bandit"
    log_success "Created .bandit symlink"
fi

if [[ ! -f "$PROJECT_ROOT/.checkov.yaml" ]]; then
    ln -s "security/checkov.yaml" "$PROJECT_ROOT/.checkov.yaml"
    log_success "Created .checkov.yaml symlink"
fi

# 运行测试扫描
log_info "Running test security scan to verify installation..."
python3 "$SCRIPT_DIR/scan.py" --scan bandit --format console || {
    log_warning "Test scan had some issues, but installation appears successful"
}

log_success "Security scanning tools installation completed!"
echo
log_info "Usage examples:"
echo "  # Run all scans:"
echo "  make security-scan"
echo
echo "  # Run specific scan:"
echo "  python3 security/scan.py --scan bandit"
echo
echo "  # Generate HTML report:"
echo "  python3 security/scan.py --format html"
echo
echo "  # Run scan with CI mode (fail on high/critical):"
echo "  python3 security/scan.py --fail-on-high"
echo
log_info "Reports will be saved to: $SCRIPT_DIR/reports/"