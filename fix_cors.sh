#!/bin/bash

# CORS修复部署脚本
# 此脚本将部署更新后的API Gateway配置以修复CORS问题

set -e

echo "🚀 开始CORS修复部署..."

# 进入infrastructure目录
cd /Users/umatoratatsu/Documents/AWS/AWS-Handson/ABA/AMAZON-BEDROCK-AGENTS/infrastructure

# 检查Terraform初始化状态
if [ ! -d ".terraform" ]; then
    echo "📦 初始化Terraform..."
    terraform init
fi

# 验证Terraform配置
echo "🔍 验证Terraform配置..."
terraform validate

# 计划部署
echo "📋 生成部署计划..."
terraform plan -out=cors-fix.tfplan

# 显示将要进行的更改
echo "📝 将要进行的更改："
echo "✅ 为 /generate 端点添加 OPTIONS 方法和CORS响应"
echo "✅ 为 /status/{id} 端点添加 OPTIONS 方法和CORS响应"
echo "✅ 为 /download/{id} 端点添加 OPTIONS 方法和CORS响应"
echo "✅ 配置所有端点的CORS响应头"

# 询问用户确认
read -p "🤔 是否继续部署CORS修复？(y/N): " confirm
if [[ $confirm =~ ^[Yy]$ ]]; then
    echo "🔧 应用CORS修复..."
    terraform apply cors-fix.tfplan

    # 清理计划文件
    rm -f cors-fix.tfplan

    echo "✅ CORS修复部署完成!"
    echo ""
    echo "📡 API Gateway URL:"
    terraform output -raw api_gateway_url
    echo ""
    echo "🧪 现在可以测试前端是否能成功调用API:"
    echo "curl -X OPTIONS https://\$(terraform output -raw api_gateway_url | cut -d'/' -f3)/dev/generate -v"
    echo ""
    echo "🎉 CORS问题应该已经解决!"
else
    echo "❌ 部署已取消"
    rm -f cors-fix.tfplan
fi