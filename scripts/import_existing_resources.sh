#!/bin/bash

# ====================================================================
# 导入已存在的AWS资源到Terraform状态
# 解决 "EntityAlreadyExists" 错误
# ====================================================================

set -euo pipefail

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 获取AWS账户ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

log_info "AWS账户ID: $ACCOUNT_ID"
log_info "区域: $REGION"

# 切换到infrastructure目录
cd infrastructure

# 初始化Terraform
log_info "初始化Terraform..."
terraform init

# 导入IAM角色
import_iam_roles() {
    log_info "导入IAM角色..."
    
    local roles=(
        "aws_iam_role.compiler_agent:ai-ppt-assistant-compiler-agent-role"
        "aws_iam_role.orchestrator_agent:ai-ppt-assistant-orchestrator-agent-role"
        "aws_iam_role.visual_agent:ai-ppt-assistant-visual-agent-role"
        "aws_iam_role.content_agent:ai-ppt-assistant-content-agent-role"
    )
    
    for role_spec in "${roles[@]}"; do
        IFS=':' read -r resource_addr role_name <<< "$role_spec"
        
        # 检查资源是否已在状态中
        if terraform state show "$resource_addr" &>/dev/null; then
            log_warning "资源 $resource_addr 已在Terraform状态中"
        else
            # 检查角色是否存在于AWS
            if aws iam get-role --role-name "$role_name" &>/dev/null; then
                log_info "导入角色: $role_name"
                terraform import "$resource_addr" "$role_name" || {
                    log_error "无法导入角色 $role_name"
                }
            else
                log_warning "角色 $role_name 在AWS中不存在"
            fi
        fi
    done
}

# 导入IAM策略
import_iam_policies() {
    log_info "导入IAM策略..."
    
    local policies=(
        "aws_iam_policy.compiler_agent:ai-ppt-assistant-compiler-agent-policy"
        "aws_iam_policy.orchestrator_agent:ai-ppt-assistant-orchestrator-agent-policy"
        "aws_iam_policy.visual_agent:ai-ppt-assistant-visual-agent-policy"
        "aws_iam_policy.content_agent:ai-ppt-assistant-content-agent-policy"
    )
    
    for policy_spec in "${policies[@]}"; do
        IFS=':' read -r resource_addr policy_name <<< "$policy_spec"
        policy_arn="arn:aws:iam::${ACCOUNT_ID}:policy/${policy_name}"
        
        # 检查资源是否已在状态中
        if terraform state show "$resource_addr" &>/dev/null; then
            log_warning "资源 $resource_addr 已在Terraform状态中"
        else
            # 检查策略是否存在于AWS
            if aws iam get-policy --policy-arn "$policy_arn" &>/dev/null; then
                log_info "导入策略: $policy_name"
                terraform import "$resource_addr" "$policy_arn" || {
                    log_error "无法导入策略 $policy_name"
                }
            else
                log_warning "策略 $policy_name 在AWS中不存在"
            fi
        fi
    done
}

# 导入KMS别名
import_kms_alias() {
    log_info "导入KMS别名..."
    
    local alias_name="alias/ai-ppt-assistant-dev-sns-key"
    local resource_addr="module.monitoring[0].aws_kms_alias.sns_key"
    
    # 检查资源是否已在状态中
    if terraform state show "$resource_addr" &>/dev/null; then
        log_warning "KMS别名已在Terraform状态中"
    else
        # 检查别名是否存在
        if aws kms describe-alias --alias-name "$alias_name" &>/dev/null; then
            log_info "导入KMS别名: $alias_name"
            terraform import "$resource_addr" "$alias_name" || {
                log_error "无法导入KMS别名"
            }
        else
            log_warning "KMS别名 $alias_name 不存在"
        fi
    fi
}

# 导入CloudWatch日志组
import_cloudwatch_log_group() {
    log_info "导入CloudWatch日志组..."
    
    local log_group="/aws/cloudwatch/insights/ai-ppt-assistant-dev"
    local resource_addr="module.monitoring[0].aws_cloudwatch_log_group.insights"
    
    # 检查资源是否已在状态中
    if terraform state show "$resource_addr" &>/dev/null; then
        log_warning "CloudWatch日志组已在Terraform状态中"
    else
        # 检查日志组是否存在
        if aws logs describe-log-groups --log-group-name-prefix "$log_group" --query "logGroups[?logGroupName=='$log_group']" --output text | grep -q "$log_group"; then
            log_info "导入日志组: $log_group"
            terraform import "$resource_addr" "$log_group" || {
                log_error "无法导入日志组"
            }
        else
            log_warning "日志组 $log_group 不存在"
        fi
    fi
}

# 验证导入结果
verify_imports() {
    log_info "验证导入结果..."
    
    # 运行terraform plan查看是否还有冲突
    terraform plan -detailed-exitcode &>/dev/null
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_success "✅ 所有资源已同步，无需更改"
        return 0
    elif [ $exit_code -eq 2 ]; then
        log_warning "⚠️ 还有待应用的更改"
        return 0
    else
        log_error "❌ 验证失败"
        return 1
    fi
}

# 主函数
main() {
    echo "======================================================================"
    echo "🔧 开始导入已存在的资源到Terraform状态"
    echo "======================================================================"
    
    # 执行导入
    import_iam_roles
    import_iam_policies
    import_kms_alias
    import_cloudwatch_log_group
    
    echo ""
    echo "======================================================================"
    echo "📊 导入完成，验证状态..."
    echo "======================================================================"
    
    if verify_imports; then
        echo ""
        log_success "✅ 资源导入成功完成！"
        echo ""
        echo "下一步："
        echo "1. 运行 'terraform plan' 查看待应用的更改"
        echo "2. 运行 'terraform apply' 应用更改"
        echo "3. 或直接运行 'make deploy-with-config' 完成完整部署"
    else
        echo ""
        log_error "❌ 导入过程中出现问题，请检查错误信息"
    fi
    
    cd ..
}

# 运行主函数
main "$@"