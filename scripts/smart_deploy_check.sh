#!/bin/bash

# 智能部署检查脚本
# 检测变化类型，推荐最优部署策略

set -euo pipefail

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_suggest() { echo -e "${GREEN}[推荐]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[注意]${NC} $1"; }

# 检查Git状态
check_git_changes() {
    log_info "检查代码变化..."
    
    # 检查Lambda代码变化
    LAMBDA_CHANGES=$(git diff --name-only HEAD^ HEAD 2>/dev/null | grep -E "^lambdas/.*\.py$" | wc -l || echo "0")
    
    # 检查Terraform配置变化
    TF_CHANGES=$(git diff --name-only HEAD^ HEAD 2>/dev/null | grep -E "^infrastructure/.*\.tf$" | wc -l || echo "0")
    
    # 检查依赖变化
    DEPS_CHANGES=$(git diff --name-only HEAD^ HEAD 2>/dev/null | grep -E "requirements.*\.txt$" | wc -l || echo "0")
    
    echo "Lambda代码变化: $LAMBDA_CHANGES 个文件"
    echo "Terraform变化: $TF_CHANGES 个文件"
    echo "依赖变化: $DEPS_CHANGES 个文件"
    
    # 返回变化类型
    if [ "$DEPS_CHANGES" -gt 0 ]; then
        echo "FULL"
    elif [ "$LAMBDA_CHANGES" -gt 0 ]; then
        echo "LAMBDA"
    elif [ "$TF_CHANGES" -gt 0 ]; then
        echo "INFRA"
    else
        echo "NONE"
    fi
}

# 检查当前部署状态
check_deployment_status() {
    log_info "检查当前部署状态..."
    
    # 检查API健康
    if command -v terraform &>/dev/null; then
        cd infrastructure
        API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
        API_KEY=$(terraform output -raw api_gateway_api_key 2>/dev/null || echo "")
        cd ..
        
        if [ -n "$API_URL" ] && [ -n "$API_KEY" ]; then
            response=$(curl -s -o /dev/null -w "%{http_code}" \
                -H "x-api-key: ${API_KEY}" \
                "${API_URL}/health" 2>/dev/null || echo "000")
            
            if [ "$response" = "200" ]; then
                log_info "✅ 当前部署健康"
                return 0
            else
                log_warning "⚠️ 当前部署不健康 (响应码: $response)"
                return 1
            fi
        else
            log_warning "⚠️ 无法获取部署信息"
            return 1
        fi
    fi
    
    return 1
}

# 主逻辑
main() {
    echo "======================================================================"
    echo "🔍 智能部署分析"
    echo "======================================================================"
    
    # 检查变化类型
    CHANGE_TYPE=$(check_git_changes | tail -n 1)
    
    echo ""
    echo "======================================================================"
    echo "📊 分析结果"
    echo "======================================================================"
    
    case "$CHANGE_TYPE" in
        "FULL")
            log_suggest "使用 'make deploy-with-config'"
            echo "原因: 依赖文件已更改，需要重新构建Lambda层"
            echo ""
            echo "执行命令:"
            echo "  make deploy-with-config"
            ;;
        
        "LAMBDA")
            log_suggest "使用 'make deploy-with-config'"
            echo "原因: Lambda代码已更改，需要重新打包和部署"
            echo ""
            echo "执行命令:"
            echo "  make deploy-with-config"
            ;;
        
        "INFRA")
            log_suggest "使用快速部署"
            echo "原因: 只有Terraform配置更改"
            echo ""
            echo "执行命令:"
            echo "  cd infrastructure && terraform apply"
            echo "  bash scripts/sync_config.sh"
            ;;
        
        "NONE")
            log_info "没有检测到重要变化"
            
            # 检查部署健康状态
            if check_deployment_status; then
                echo "当前部署正常运行，无需重新部署"
            else
                log_suggest "建议运行配置同步"
                echo ""
                echo "执行命令:"
                echo "  bash scripts/sync_config.sh"
            fi
            ;;
    esac
    
    echo ""
    echo "======================================================================"
    echo "💡 提示"
    echo "======================================================================"
    echo "• 生产环境始终使用: make deploy-with-config"
    echo "• 快速测试可以用: terraform apply + sync_config.sh"
    echo "• 不确定时选择: make deploy-with-config (更安全)"
    echo "======================================================================"
}

main "$@"