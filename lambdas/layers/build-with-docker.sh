#!/bin/bash
# Docker构建Lambda层脚本 - ARM64架构
# Version: 3.0

echo "🐳 Building Lambda layers with Docker (ARM64 architecture)..."
echo "================================================"

# 确保目录结构
mkdir -p dist
rm -rf python

# 构建content层（包含Pillow）
echo ""
echo "📦 Building content layer (with Pillow)..."
docker run --rm \
    --platform linux/arm64 \
    --entrypoint "" \
    -v "$(pwd):/var/task" \
    -w /var/task \
    public.ecr.aws/lambda/python:3.12 \
    /bin/bash -c "
        echo 'Installing Python dependencies...' &&
        pip install --target python/lib/python3.12/site-packages -r requirements-content.txt --quiet &&
        echo 'Creating zip archive...' &&
        python3 -c \"
import zipfile
import os
import pathlib

def create_zip(source_dir, output_file):
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)

pathlib.Path('dist').mkdir(exist_ok=True)
create_zip('python', 'dist/ai-ppt-assistant-content.zip')
print('✅ Zip archive created successfully')
\"
    "

if [ $? -eq 0 ]; then
    echo "✅ Content layer built successfully"
else
    echo "❌ Failed to build content layer"
    exit 1
fi

# 清理
rm -rf python

# 构建minimal层
echo ""
echo "📦 Building minimal layer..."
docker run --rm \
    --platform linux/arm64 \
    --entrypoint "" \
    -v "$(pwd):/var/task" \
    -w /var/task \
    public.ecr.aws/lambda/python:3.12 \
    /bin/bash -c "
        echo 'Installing Python dependencies...' &&
        pip install --target python/lib/python3.12/site-packages \
            boto3==1.35.0 \
            aws-lambda-powertools==2.38.0 --quiet &&
        echo 'Creating zip archive...' &&
        python3 -c \"
import zipfile
import os
import pathlib

def create_zip(source_dir, output_file):
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)

pathlib.Path('dist').mkdir(exist_ok=True)
create_zip('python', 'dist/ai-ppt-assistant-minimal.zip')
print('✅ Zip archive created successfully')
\"
    "

if [ $? -eq 0 ]; then
    echo "✅ Minimal layer built successfully"
else
    echo "❌ Failed to build minimal layer"
    exit 1
fi

# 清理
rm -rf python

# 构建主层（如果存在requirements.txt）
if [ -f "requirements.txt" ]; then
    echo ""
    echo "📦 Building main layer..."
    docker run --rm \
        --platform linux/arm64 \
        --entrypoint "" \
        -v "$(pwd):/var/task" \
        -w /var/task \
        public.ecr.aws/lambda/python:3.12 \
        /bin/bash -c "
            echo 'Installing Python dependencies...' &&
            pip install --target python/lib/python3.12/site-packages -r requirements.txt --quiet &&
            echo 'Creating zip archive...' &&
            python3 -c \"
import zipfile
import os
import pathlib

def create_zip(source_dir, output_file):
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)

pathlib.Path('dist').mkdir(exist_ok=True)
create_zip('python', 'dist/ai-ppt-assistant-dependencies.zip')
print('✅ Zip archive created successfully')
\"
        "
    
    if [ $? -eq 0 ]; then
        echo "✅ Main layer built successfully"
    else
        echo "⚠️ Warning: Failed to build main layer"
    fi
    
    rm -rf python
fi

# 显示构建结果
echo ""
echo "📊 Build results:"
ls -lh dist/*.zip 2>/dev/null || echo "No zip files found"

echo ""
echo "✅ All Lambda layers built successfully for ARM64 architecture!"
