#!/bin/bash
# Lambda函数构建脚本 - 专门用于generate_ppt_complete
# 确保每次部署前自动创建正确的部署包

set -euo pipefail

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 获取脚本和项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info "开始构建Lambda部署包..."
log_info "项目根目录: $PROJECT_ROOT"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 确保目录存在
mkdir -p lambda-packages

# 检查必要文件是否存在
REQUIRED_FILES=(
    "lambdas/generate_ppt_complete.py"
    "lambdas/image_generator.py"
    "lambdas/image_processing_service.py"
    "lambdas/image_s3_service.py"
    "lambdas/image_config.py"
    "lambdas/image_exceptions.py"
)

log_info "检查必要文件..."
for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        log_error "缺失文件: $file"
        exit 1
    fi
done

# 检查src目录
if [[ ! -d "src" ]]; then
    log_error "缺失src目录"
    exit 1
fi

# 备份旧的部署包（如果存在）
if [[ -f "lambda-packages/generate_ppt_complete.zip" ]]; then
    backup_file="lambda-packages/generate_ppt_complete.zip.backup_$(date +%Y%m%d_%H%M%S)"
    log_info "备份现有部署包到: $backup_file"
    mv "lambda-packages/generate_ppt_complete.zip" "$backup_file"
fi

# 创建临时构建目录
BUILD_DIR="build_temp_$$"
mkdir -p "$BUILD_DIR"

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    rm -rf "$BUILD_DIR"
}
trap cleanup EXIT

log_info "复制Lambda函数文件..."
# 复制主要的Lambda文件
cp "lambdas/generate_ppt_complete.py" "$BUILD_DIR/"

# 复制图片生成相关文件
cp "lambdas/image_generator.py" "$BUILD_DIR/"
cp "lambdas/image_processing_service.py" "$BUILD_DIR/"
cp "lambdas/image_s3_service.py" "$BUILD_DIR/"
cp "lambdas/image_config.py" "$BUILD_DIR/"
cp "lambdas/image_exceptions.py" "$BUILD_DIR/"

# 复制其他可能需要的Lambda文件
for file in lambdas/*.py; do
    filename=$(basename "$file")
    # 跳过已复制的文件和测试文件
    if [[ ! -f "$BUILD_DIR/$filename" ]] && [[ ! "$filename" =~ test ]]; then
        cp "$file" "$BUILD_DIR/" 2>/dev/null || true
    fi
done

log_info "复制src目录..."
# 复制整个src目录
cp -r "src" "$BUILD_DIR/"

# 清理不必要的文件
log_info "清理不必要的文件..."
find "$BUILD_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*.backup" -delete 2>/dev/null || true
find "$BUILD_DIR" -type f -name "test_*.py" -delete 2>/dev/null || true
find "$BUILD_DIR" -type f -name "*_test.py" -delete 2>/dev/null || true

# 创建ZIP包
log_info "创建部署包..."
cd "$BUILD_DIR"
zip -r "../lambda-packages/generate_ppt_complete.zip" . -q

# 返回到项目根目录
cd "$PROJECT_ROOT"

# 验证部署包
if [[ -f "lambda-packages/generate_ppt_complete.zip" ]]; then
    FILE_SIZE=$(ls -lh "lambda-packages/generate_ppt_complete.zip" | awk '{print $5}')
    FILE_COUNT=$(unzip -l "lambda-packages/generate_ppt_complete.zip" 2>/dev/null | tail -1 | awk '{print $2}')

    log_success "部署包创建成功!"
    log_info "文件: lambda-packages/generate_ppt_complete.zip"
    log_info "大小: $FILE_SIZE"
    log_info "包含文件数: $FILE_COUNT"

    # 显示部分内容用于验证
    log_info "部署包内容预览:"
    unzip -l "lambda-packages/generate_ppt_complete.zip" | head -20
else
    log_error "部署包创建失败!"
    exit 1
fi

log_success "Lambda部署包构建完成！"
echo ""
echo "下一步:"
echo "1. 运行 'cd infrastructure && terraform plan' 检查更改"
echo "2. 运行 'terraform apply' 部署到AWS"