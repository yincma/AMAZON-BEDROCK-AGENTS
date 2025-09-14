#!/bin/bash

# Lambda层创建脚本
set -e

echo "🔧 创建Lambda层..."

# 创建临时目录
LAYER_DIR="lambda-layer"
rm -rf $LAYER_DIR
mkdir -p $LAYER_DIR/python

# 创建requirements文件
cat > $LAYER_DIR/requirements.txt << EOF
boto3==1.34.14
python-pptx==0.6.23
Pillow==10.2.0
EOF

# 安装依赖到层目录
echo "📦 安装Python依赖..."
pip install -r $LAYER_DIR/requirements.txt -t $LAYER_DIR/python/ --platform manylinux2014_x86_64 --implementation cp --python-version 3.11 --only-binary=:all: --upgrade

# 打包层
echo "📦 打包Lambda层..."
cd $LAYER_DIR
zip -r ../ai-ppt-dependencies-layer.zip python/
cd ..

# 清理
rm -rf $LAYER_DIR

echo "✅ Lambda层创建完成: ai-ppt-dependencies-layer.zip"
echo "   文件大小: $(du -h ai-ppt-dependencies-layer.zip | cut -f1)"