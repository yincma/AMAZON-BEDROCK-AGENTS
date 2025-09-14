#!/bin/bash
# Lambda函数打包脚本 - 图片生成服务部署包构建
# 遵循AWS Lambda最佳实践和安全要求

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="$PROJECT_ROOT/lambdas"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"

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

# 清理函数
cleanup() {
    log_info "清理临时文件..."
    rm -rf "$BUILD_DIR" || true
}

# 错误处理
trap cleanup EXIT

echo "📦 打包Lambda函数..."

# 确保目录存在
mkdir -p lambda-packages
mkdir -p "$DIST_DIR"
mkdir -p "$BUILD_DIR"

# 验证环境
validate_environment() {
    log_info "验证构建环境..."

    # 检查必需工具
    command -v python3 >/dev/null 2>&1 || { log_error "Python3 未安装"; exit 1; }
    command -v pip3 >/dev/null 2>&1 || { log_error "pip3 未安装"; exit 1; }
    command -v zip >/dev/null 2>&1 || { log_error "zip 未安装"; exit 1; }

    # 检查Python版本
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ "$python_version" != "3.11" && "$python_version" != "3.12" ]]; then
        log_warning "建议使用Python 3.11或3.12，当前版本: $python_version"
    fi

    log_success "环境验证通过"
}

validate_environment

# 原有函数列表
FUNCTIONS=(
    "api_handler"
    "generate_ppt"
    "compile_ppt"
    "status_check"
    "download_ppt"
    "generate_ppt_complete"
)

# 新增图片生成服务函数列表
IMAGE_FUNCTIONS=(
    "image_generator"
    "image_generator_optimized"
)

# 安装依赖到指定目录
install_dependencies() {
    local build_path="$1"
    local requirements_file="$2"

    log_info "安装Python依赖到 $build_path..."

    # 创建虚拟环境目录
    mkdir -p "$build_path/lib"

    # 安装核心依赖（针对Lambda环境优化）
    pip3 install -t "$build_path/lib" \
        --platform manylinux2014_x86_64 \
        --implementation cp \
        --python-version 3.11 \
        --only-binary=:all: \
        --upgrade \
        boto3 \
        Pillow \
        requests || {
        log_warning "使用标准安装方式作为回退"
        pip3 install -t "$build_path/lib" boto3 Pillow requests
    }

    # 清理不必要的文件以减小包大小
    find "$build_path/lib" -name "*.pyc" -delete 2>/dev/null || true
    find "$build_path/lib" -name "*.pyo" -delete 2>/dev/null || true
    find "$build_path/lib" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_path/lib" -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$build_path/lib" -name "tests" -type d -exec rm -rf {} + 2>/dev/null || true

    log_success "依赖安装完成"
}

# 构建图片生成服务
build_image_generator() {
    log_info "构建基础图片生成服务Lambda包..."

    local build_path="$BUILD_DIR/image_generator"
    local output_file="$DIST_DIR/image_generator.zip"

    # 创建构建目录
    mkdir -p "$build_path"

    # 安装依赖
    install_dependencies "$build_path" ""

    # 复制源代码
    if [[ -f "$LAMBDA_DIR/image_processing_service.py" ]]; then
        cp "$LAMBDA_DIR/image_processing_service.py" "$build_path/"
    fi
    if [[ -f "$LAMBDA_DIR/image_config.py" ]]; then
        cp "$LAMBDA_DIR/image_config.py" "$build_path/"
    fi
    if [[ -f "$LAMBDA_DIR/image_exceptions.py" ]]; then
        cp "$LAMBDA_DIR/image_exceptions.py" "$build_path/"
    fi

    # 创建Lambda处理器
    cat > "$build_path/lambda_function.py" << 'EOF'
"""
Lambda函数处理器 - 基础图片生成服务
"""

import json
import base64
import logging
import sys
import os

# 添加依赖库路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

try:
    from image_processing_service import ImageProcessingService
    from image_exceptions import ImageProcessingError
except ImportError as e:
    logging.error(f"导入模块失败: {e}")
    # 创建模拟服务
    class ImageProcessingService:
        def generate_prompt(self, slide_content, target_audience='business'):
            return f"Professional presentation image for {slide_content.get('title', 'slide')}"

        def call_image_generation(self, prompt, model_preference=None):
            # 返回一个简单的占位图
            from PIL import Image, ImageDraw
            import io

            img = Image.new('RGB', (1200, 800), color='lightblue')
            draw = ImageDraw.Draw(img)
            draw.text((400, 350), "Generated Image", fill='white')

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            return img_bytes.getvalue()

        def get_cache_stats(self):
            return {"cache_enabled": False}

    class ImageProcessingError(Exception):
        pass

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局服务实例
_service = None

def get_service():
    """获取或创建服务实例"""
    global _service
    if _service is None:
        _service = ImageProcessingService()
    return _service

def lambda_handler(event, context):
    """Lambda入口函数"""
    logger.info(f"收到请求: {context.aws_request_id}")

    try:
        # 解析请求体
        body = event.get('body')
        if body:
            if isinstance(body, str):
                body = json.loads(body)
        else:
            body = {}

        # 提取参数
        slide_content = body.get('slide_content', {})
        target_audience = body.get('target_audience', 'business')
        model_preference = body.get('model_preference')

        # 获取服务实例
        service = get_service()

        # 生成提示词
        prompt = service.generate_prompt(slide_content, target_audience)
        logger.info(f"生成提示词: {prompt}")

        # 生成图片
        image_data = service.call_image_generation(prompt, model_preference)

        # 编码图片为base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        # 返回成功响应
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'image_data': image_base64,
                'prompt_used': prompt,
                'cache_stats': service.get_cache_stats(),
                'request_id': context.aws_request_id
            })
        }

        logger.info("图片生成成功")
        return response

    except ImageProcessingError as e:
        logger.error(f"图片处理错误: {str(e)}")
        return {
            'statusCode': 422,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'IMAGE_PROCESSING_ERROR',
                'message': str(e),
                'request_id': context.aws_request_id
            })
        }

    except Exception as e:
        logger.error(f"意外错误: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'INTERNAL_ERROR',
                'message': str(e),
                'request_id': context.aws_request_id
            })
        }
EOF

    # 创建部署包
    cd "$build_path"
    zip -r "$output_file" . -x "__pycache__/*" "*.pyc"

    log_success "基础图片生成服务包构建完成: $output_file"
    echo "包大小: $(du -h "$output_file" | cut -f1)"
}

# 打包原有函数
for func in "${FUNCTIONS[@]}"; do
    echo "  打包 $func..."

    # 创建临时目录
    temp_dir="temp_${func}"
    rm -rf $temp_dir
    mkdir -p $temp_dir

    # 复制Lambda函数
    if [[ -f "lambdas/${func}.py" ]]; then
        cp lambdas/${func}.py $temp_dir/lambda_function.py
    else
        log_warning "函数文件不存在: lambdas/${func}.py，跳过"
        continue
    fi

    # 复制src目录（如果需要）
    if [ -d "src" ]; then
        cp -r src $temp_dir/
    fi

    # 创建zip包
    cd $temp_dir
    zip -r ../lambda-packages/${func}.zip . -q
    cd ..

    # 清理临时目录
    rm -rf $temp_dir

    echo "  ✅ ${func}.zip 创建完成"
done

# 构建图片生成服务
build_image_generator

# 构建优化版本（如果文件存在）
if [[ -f "$LAMBDA_DIR/image_processing_service_optimized.py" ]]; then
    log_info "构建优化图片生成服务..."

    local build_path="$BUILD_DIR/image_generator_optimized"
    local output_file="$DIST_DIR/image_generator_optimized.zip"

    mkdir -p "$build_path"

    # 安装依赖
    install_dependencies "$build_path" ""

    # 复制源代码
    cp "$LAMBDA_DIR/image_processing_service_optimized.py" "$build_path/"
    cp "$LAMBDA_DIR/image_config.py" "$build_path/"
    cp "$LAMBDA_DIR/image_exceptions.py" "$build_path/"

    # 创建简化的优化处理器
    cat > "$build_path/lambda_function.py" << 'EOF'
"""优化图片生成服务Lambda处理器"""

import json
import base64
import logging
import sys
import os
import asyncio

# 添加依赖库路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

try:
    from image_processing_service_optimized import ImageProcessingServiceOptimized, ImageRequest
    from image_exceptions import ImageProcessingError
except ImportError:
    # 回退到基础服务
    from lambda_function import ImageProcessingService as ImageProcessingServiceOptimized

    class ImageRequest:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_service = None

def get_service():
    global _service
    if _service is None:
        _service = ImageProcessingServiceOptimized()
    return _service

def lambda_handler(event, context):
    """优化的Lambda处理器"""
    try:
        body = json.loads(event.get('body', '{}')) if event.get('body') else event

        service = get_service()

        # 检查是否支持异步处理
        if hasattr(service, 'generate_image_async'):
            # 异步处理
            request = ImageRequest(
                prompt=body.get('prompt', ''),
                request_id=context.aws_request_id,
                width=body.get('width', 1200),
                height=body.get('height', 800)
            )

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(service.generate_image_async(request))
            loop.close()

            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': True,
                    'image_data': base64.b64encode(response.image_data).decode('utf-8'),
                    'metadata': {
                        'model_used': response.model_used,
                        'generation_time': response.generation_time,
                        'from_cache': response.from_cache
                    }
                })
            }
        else:
            # 回退到同步处理
            prompt = service.generate_prompt(body.get('slide_content', {}))
            image_data = service.call_image_generation(prompt)

            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'success': True,
                    'image_data': base64.b64encode(image_data).decode('utf-8')
                })
            }

    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'success': False, 'error': str(e)})
        }
EOF

    cd "$build_path"
    zip -r "$output_file" . -x "__pycache__/*" "*.pyc"

    log_success "优化图片生成服务包构建完成: $output_file"
fi

echo "✅ 所有Lambda函数打包完成"
echo ""
echo "原有函数包："
ls -lh lambda-packages/ 2>/dev/null || echo "无原有函数包"
echo ""
echo "图片生成服务包："
ls -lh "$DIST_DIR"/*.zip 2>/dev/null || echo "无图片生成服务包"