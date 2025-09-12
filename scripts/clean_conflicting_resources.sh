#!/bin/bash

# ====================================================================
# 清理冲突的AWS资源
# 删除已存在但不在Terraform状态中的资源
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

echo "======================================================================"
echo "🧹 清理冲突的AWS资源"
echo "======================================================================"
echo "AWS账户: $ACCOUNT_ID"
echo ""

# 清理IAM角色
clean_iam_roles() {
    log_info "清理IAM角色..."
    
    local roles=(
        "ai-ppt-assistant-compiler-agent-role"
        "ai-ppt-assistant-orchestrator-agent-role"
        "ai-ppt-assistant-visual-agent-role"
        "ai-ppt-assistant-content-agent-role"
    )
    
    for role_name in "${roles[@]}"; do
        if aws iam get-role --role-name "$role_name" &>/dev/null; then
            log_warning "发现角色: $role_name，清理中..."
            
            # 先分离所有策略
            attached_policies=$(aws iam list-attached-role-policies --role-name "$role_name" --query 'AttachedPolicies[*].PolicyArn' --output text 2>/dev/null || echo "")
            for policy_arn in $attached_policies; do
                log_info "  分离策略: $policy_arn"
                aws iam detach-role-policy --role-name "$role_name" --policy-arn "$policy_arn" 2>/dev/null || true
            done
            
            # 删除内联策略
            inline_policies=$(aws iam list-role-policies --role-name "$role_name" --query 'PolicyNames[]' --output text 2>/dev/null || echo "")
            for policy_name in $inline_policies; do
                log_info "  删除内联策略: $policy_name"
                aws iam delete-role-policy --role-name "$role_name" --policy-name "$policy_name" 2>/dev/null || true
            done
            
            # 删除角色
            if aws iam delete-role --role-name "$role_name" 2>/dev/null; then
                log_success "✅ 已删除角色: $role_name"
            else
                log_error "❌ 无法删除角色: $role_name"
            fi
        else
            log_info "角色 $role_name 不存在，跳过"
        fi
    done
}

# 清理IAM策略
clean_iam_policies() {
    log_info "清理IAM策略..."
    
    local policies=(
        "ai-ppt-assistant-compiler-agent-policy"
        "ai-ppt-assistant-orchestrator-agent-policy"
        "ai-ppt-assistant-visual-agent-policy"
        "ai-ppt-assistant-content-agent-policy"
    )
    
    for policy_name in "${policies[@]}"; do
        policy_arn="arn:aws:iam::${ACCOUNT_ID}:policy/${policy_name}"
        
        if aws iam get-policy --policy-arn "$policy_arn" &>/dev/null; then
            log_warning "发现策略: $policy_name，清理中..."
            
            # 先分离所有实体
            # 获取附加到此策略的所有角色
            attached_roles=$(aws iam list-entities-for-policy --policy-arn "$policy_arn" --entity-filter Role --query 'PolicyRoles[*].RoleName' --output text 2>/dev/null || echo "")
            for role in $attached_roles; do
                log_info "  从角色分离: $role"
                aws iam detach-role-policy --role-name "$role" --policy-arn "$policy_arn" 2>/dev/null || true
            done
            
            # 删除非默认版本
            versions=$(aws iam list-policy-versions --policy-arn "$policy_arn" --query 'Versions[?IsDefaultVersion==`false`].VersionId' --output text 2>/dev/null || echo "")
            for version in $versions; do
                log_info "  删除策略版本: $version"
                aws iam delete-policy-version --policy-arn "$policy_arn" --version-id "$version" 2>/dev/null || true
            done
            
            # 删除策略
            if aws iam delete-policy --policy-arn "$policy_arn" 2>/dev/null; then
                log_success "✅ 已删除策略: $policy_name"
            else
                log_error "❌ 无法删除策略: $policy_name"
            fi
        else
            log_info "策略 $policy_name 不存在，跳过"
        fi
    done
}

# 清理KMS别名
clean_kms_alias() {
    log_info "清理KMS别名..."
    
    local alias_name="alias/ai-ppt-assistant-dev-sns-key"
    
    if aws kms describe-alias --alias-name "$alias_name" &>/dev/null; then
        log_warning "发现KMS别名: $alias_name，清理中..."
        
        if aws kms delete-alias --alias-name "$alias_name" 2>/dev/null; then
            log_success "✅ 已删除KMS别名: $alias_name"
        else
            log_error "❌ 无法删除KMS别名: $alias_name"
        fi
    else
        log_info "KMS别名 $alias_name 不存在，跳过"
    fi
}

# 清理CloudWatch日志组
clean_cloudwatch_log_group() {
    log_info "清理CloudWatch日志组..."
    
    local log_group="/aws/cloudwatch/insights/ai-ppt-assistant-dev"
    
    if aws logs describe-log-groups --log-group-name-prefix "$log_group" --query "logGroups[?logGroupName=='$log_group']" --output text 2>/dev/null | grep -q "$log_group"; then
        log_warning "发现日志组: $log_group，清理中..."
        
        if aws logs delete-log-group --log-group-name "$log_group" 2>/dev/null; then
            log_success "✅ 已删除日志组: $log_group"
        else
            log_error "❌ 无法删除日志组: $log_group"
        fi
    else
        log_info "日志组 $log_group 不存在，跳过"
    fi
}

# 确认操作
confirm_action() {
    echo ""
    echo "⚠️  警告：此操作将删除以下AWS资源："
    echo "  - 4个IAM角色"
    echo "  - 4个IAM策略"
    echo "  - 1个KMS别名"
    echo "  - 1个CloudWatch日志组"
    echo ""
    read -p "确定要继续吗？(yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log_warning "操作已取消"
        exit 0
    fi
}

# 主函数
main() {
    # 确认操作
    confirm_action
    
    echo ""
    echo "开始清理..."
    echo ""
    
    # 执行清理
    clean_iam_roles
    clean_iam_policies
    clean_kms_alias
    clean_cloudwatch_log_group
    
    echo ""
    echo "======================================================================"
    log_success "✅ 资源清理完成！"
    echo "======================================================================"
    echo ""
    echo "下一步："
    echo "1. 运行 'cd infrastructure && terraform plan' 查看计划"
    echo "2. 运行 'make deploy-with-config' 重新部署"
    echo ""
}

# 运行主函数
main "$@"