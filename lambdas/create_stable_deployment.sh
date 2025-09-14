#!/bin/bash

echo "创建稳定的Lambda部署包..."

BASE_DIR="/Users/umatoratatsu/Documents/AWS/AWS-Handson/ABA/AMAZON-BEDROCK-AGENTS"
TEMP_DIR="/tmp/lambda-stable-deploy"

# 清理并创建临时目录
rm -rf $TEMP_DIR
mkdir -p $TEMP_DIR

# 复制所有源代码
echo "复制源代码..."
cp -r $BASE_DIR/src $TEMP_DIR/
cp -r $BASE_DIR/lambdas/*.py $TEMP_DIR/
cp -r $BASE_DIR/lambdas/exceptions $TEMP_DIR/
cp -r $BASE_DIR/lambdas/placeholder $TEMP_DIR/

# 创建主入口文件（覆盖之前的）
echo "创建Lambda入口文件..."
cat > $TEMP_DIR/lambda_function.py << 'HANDLER'
"""Lambda主入口文件 - 确保所有模块能正确导入"""
import sys
import os

# 添加所有可能的路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'src'))
sys.path.insert(0, '/opt/python')  # Lambda层路径

# 导入实际的处理函数
from generate_ppt_complete import handler

# 使用原始处理函数
lambda_handler = handler
HANDLER

# 创建部署包
echo "创建ZIP部署包..."
cd $TEMP_DIR
zip -r lambda-deployment.zip * -x "*.pyc" "*__pycache__*" "*.DS_Store"

# 移动到lambdas目录
mv lambda-deployment.zip $BASE_DIR/lambdas/

echo "部署包创建完成: lambdas/lambda-deployment.zip"
echo "文件大小: $(ls -lh $BASE_DIR/lambdas/lambda-deployment.zip | awk '{print $5}')"
