#!/bin/bash
# 快速部署脚本 - 使用最小化配置避免超时

set -e

echo "====================================="
echo "⚡ 快速部署 - 最小化配置"
echo "====================================="

# 检查Lambda层文件是否存在
if [ ! -f "../lambdas/layers/python.zip" ]; then
    echo "⚠️  Lambda层文件不存在，创建空文件..."
    mkdir -p ../lambdas/layers
    echo '# placeholder' > ../lambdas/layers/requirements.txt
    cd ../lambdas/layers
    zip python.zip requirements.txt
    cd ../../infrastructure
    echo "✅ Lambda层文件已创建"
fi

echo ""
echo "📋 步骤 1/4: 备份现有配置"
mv main.tf main.tf.backup 2>/dev/null || true
mv minimal_deploy.tf main.tf
echo "✅ 配置已切换到最小化模式"

echo ""
echo "📋 步骤 2/4: 初始化Terraform"
terraform init -upgrade=false -backend=false
echo "✅ 初始化完成"

echo ""
echo "📋 步骤 3/4: 执行Plan（快速模式）"
terraform plan -out=minimal.tfplan -parallelism=10
echo "✅ Plan生成成功"

echo ""
echo "📋 步骤 4/4: 执行部署"
echo "开始创建AWS资源..."
terraform apply -auto-approve minimal.tfplan

echo ""
echo "====================================="
echo "✅ 部署完成！"
echo "====================================="

# 显示输出
echo ""
echo "📊 资源信息："
terraform output

echo ""
echo "====================================="
echo "📝 后续步骤"
echo "====================================="
echo "1. 基础资源已创建（S3、DynamoDB、SQS、API Gateway）"
echo "2. Lambda函数需要手动部署或使用AWS CLI"
echo "3. Bedrock Agents需要在AWS控制台配置"
echo ""
echo "恢复完整配置："
echo "  mv main.tf minimal_deploy.tf"
echo "  mv main.tf.backup main.tf"
echo ""