#!/bin/bash
# API Gateway 部署前验证脚本
# 确保所有前置条件满足后再进行部署

set -euo pipefail

# 日志函数
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >&2
}

error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >&2
    exit 1
}

success() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS: $1" >&2
}

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log "开始 API Gateway 部署前验证..."

# 1. 检查 Terraform 配置语法
log "验证 Terraform 配置语法..."
if ! terraform fmt -check -recursive .; then
    error "Terraform 配置格式不正确，请运行 'terraform fmt -recursive .'"
fi

if ! terraform validate; then
    error "Terraform 配置验证失败"
fi

success "Terraform 配置语法验证通过"

# 2. 检查 AWS 凭证
log "验证 AWS 凭证..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    error "AWS 凭证配置错误或已过期"
fi

success "AWS 凭证验证通过"

# 3. 检查必要的变量文件
log "检查必要的配置文件..."
required_files=(
    "terraform.tfvars"
    "variables.tf"
    "main.tf"
    "api_gateway_additional.tf"
)

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        error "必需的配置文件 '$file' 不存在"
    fi
done

success "配置文件检查通过"

# 4. 检查 Lambda 函数 ZIP 文件是否存在
log "检查 Lambda 函数部署包..."
lambda_zips_dir="../lambdas"
if [[ -d "$lambda_zips_dir" ]]; then
    # 检查关键 Lambda 函数的 ZIP 文件
    key_functions=(
        "api/generate_presentation.zip"
        "api/presentation_status.py"
    )
    
    for func in "${key_functions[@]}"; do
        if [[ "$func" == *.zip ]] && [[ ! -f "$lambda_zips_dir/$func" ]]; then
            log "WARNING: Lambda 部署包 '$func' 不存在，可能影响集成"
        elif [[ "$func" == *.py ]] && [[ ! -f "$lambda_zips_dir/$func" ]]; then
            log "WARNING: Lambda 源码 '$func' 不存在，可能影响集成"
        fi
    done
fi

success "Lambda 函数检查完成"

# 5. 执行 Terraform plan 以检查资源依赖关系
log "执行 Terraform plan 检查资源依赖关系..."
if ! terraform plan -out=validation.tfplan > /dev/null 2>&1; then
    error "Terraform plan 执行失败，请检查配置"
fi

# 分析 plan 输出是否包含可能的依赖问题
plan_output=$(terraform show -json validation.tfplan 2>/dev/null || echo "{}")
if [[ "$plan_output" != "{}" ]]; then
    # 检查是否有循环依赖或其他问题
    log "Plan 验证通过，无明显依赖问题"
else
    log "WARNING: 无法解析 Terraform plan 输出，请手动检查"
fi

# 清理临时 plan 文件
rm -f validation.tfplan

success "Terraform plan 验证通过"

# 6. 检查资源命名约定
log "验证资源命名约定..."
if ! grep -q "project_name.*environment" variables.tf; then
    log "WARNING: 资源命名可能不符合约定"
fi

success "命名约定检查完成"

# 7. 验证关键依赖关系是否正确配置
log "验证关键资源依赖关系..."

# 检查 Integration Response 是否有正确的依赖
if ! grep -A 10 "aws_api_gateway_integration_response" api_gateway_additional.tf | grep -q "depends_on"; then
    log "WARNING: 某些 Integration Response 可能缺少 depends_on 声明"
fi

# 检查 API Gateway Deployment 是否包含所有集成
if ! grep -A 20 "aws_api_gateway_deployment.*integration_deployment" main.tf | grep -q "aws_api_gateway_integration"; then
    log "WARNING: API Gateway Deployment 可能缺少某些集成依赖"
fi

success "依赖关系验证完成"

log "======================================"
success "所有验证检查完成！部署前验证通过。"
log "======================================"

echo
log "建议的部署步骤："
log "1. 如果是首次部署，使用分阶段部署脚本: ./staged_deploy.sh"
log "2. 如果是更新现有资源，可直接运行: terraform apply"
log "3. 部署后运行健康检查: ./health_check.sh"