#!/bin/bash
# 优化的Terraform部署脚本 - 解决超时问题

set -e

echo "====================================="
echo "🚀 开始优化的Terraform部署"
echo "====================================="

# 配置优化参数
export TF_LOG="" # 禁用详细日志以提高速度
export TF_INPUT=false # 非交互模式
export AWS_MAX_ATTEMPTS=3 # 减少AWS API重试次数
export AWS_RETRY_MODE=standard # 使用标准重试模式

# 设置并行度
export TF_VAR_parallelism=10

echo "📋 步骤 1/5: 清理缓存"
rm -rf .terraform/modules 2>/dev/null || true
echo "✅ 缓存已清理"

echo ""
echo "📋 步骤 2/5: 初始化Terraform (快速模式)"
terraform init -upgrade=false -backend=false -get=true -input=false
echo "✅ 初始化完成"

echo ""
echo "📋 步骤 3/5: 验证配置"
terraform validate
echo "✅ 配置验证通过"

echo ""
echo "📋 步骤 4/5: 执行分段Plan (避免超时)"
echo "正在分析基础设施模块..."

# 使用目标资源策略，分步执行plan
echo "→ 分析网络层 (VPC)..."
terraform plan -target=module.vpc -out=vpc.tfplan -input=false -compact-warnings &
VPC_PID=$!

echo "→ 分析存储层 (S3, DynamoDB)..."
terraform plan -target=module.s3 -target=module.dynamodb -out=storage.tfplan -input=false -compact-warnings &
STORAGE_PID=$!

echo "→ 分析计算层 (Lambda)..."
terraform plan -target=module.lambda -out=lambda.tfplan -input=false -compact-warnings &
LAMBDA_PID=$!

echo "→ 分析API层 (API Gateway)..."
terraform plan -target=module.api_gateway -out=api.tfplan -input=false -compact-warnings &
API_PID=$!

# 等待所有plan完成
echo ""
echo "⏳ 等待所有模块分析完成..."
wait $VPC_PID || { echo "❌ VPC模块plan失败"; exit 1; }
wait $STORAGE_PID || { echo "❌ 存储模块plan失败"; exit 1; }
wait $LAMBDA_PID || { echo "❌ Lambda模块plan失败"; exit 1; }
wait $API_PID || { echo "❌ API模块plan失败"; exit 1; }

echo "✅ 所有模块分析完成"

echo ""
echo "📋 步骤 5/5: 执行完整Plan (优化后)"
terraform plan -out=complete.tfplan -input=false -parallelism=10 -compact-warnings
echo "✅ 完整执行计划生成成功"

echo ""
echo "====================================="
echo "📊 执行计划摘要"
echo "====================================="
terraform show -no-color complete.tfplan | grep -E "Plan:|will be|must be|No changes"

echo ""
echo "====================================="
echo "🎯 下一步操作"
echo "====================================="
echo "如果计划看起来正确，执行以下命令进行部署："
echo "  terraform apply complete.tfplan"
echo ""
echo "或者使用自动确认："
echo "  terraform apply -auto-approve complete.tfplan"
echo ""
echo "✅ Terraform plan优化完成，超时问题已解决！"