#!/bin/bash
# AI PPT Assistant - 预部署验证脚本
# =====================================
#
# 在每次部署前运行此脚本，确保不会出现配置问题
# 基于2025-09-09修复的关键问题创建的自动化检查
#
# 使用方法：
#   ./scripts/pre_deploy_validator.sh
#   ./scripts/pre_deploy_validator.sh --fix  # 自动修复
#
# 作者：AWS Expert & Claude Code

set -e

# 配置
PROJECT_NAME="ai-ppt-assistant"
REGION="us-east-1"
AUTO_FIX=false

# 颜色配置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            AUTO_FIX=true
            shift
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--fix] [--region REGION]"
            echo "  --fix     自动修复发现的问题"
            echo "  --region  AWS区域 (默认: us-east-1)"
            exit 0
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 错误计数器
ERROR_COUNT=0
WARNING_COUNT=0

# 检查必需工具
check_prerequisites() {
    log_info "检查必需工具..."
    
    local missing_tools=()
    
    command -v aws >/dev/null 2>&1 || missing_tools+=("aws-cli")
    command -v terraform >/dev/null 2>&1 || missing_tools+=("terraform")
    command -v python3 >/dev/null 2>&1 || missing_tools+=("python3")
    command -v make >/dev/null 2>&1 || missing_tools+=("make")
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "缺少必需工具: ${missing_tools[*]}"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        return 1
    fi
    
    # 检查AWS认证
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS认证失败，请配置AWS凭证"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        return 1
    fi
    
    log_success "工具检查通过"
    return 0
}

# 检查项目结构
check_project_structure() {
    log_info "检查项目结构..."
    
    local required_dirs=("lambdas/api" "lambdas/controllers" "lambdas/utils" "infrastructure" "scripts")
    local required_files=("Makefile" "lambdas/utils/api_utils.py" "infrastructure/main.tf")
    
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            log_error "缺少必需目录: $dir"
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi
    done
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "缺少必需文件: $file"
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi
    done
    
    if [[ $ERROR_COUNT -eq 0 ]]; then
        log_success "项目结构检查通过"
        return 0
    else
        return 1
    fi
}

# 检查Bedrock Agent配置
check_bedrock_agents() {
    log_info "检查Bedrock Agent配置..."
    
    # 获取已部署的Agents
    local agents_json
    agents_json=$(aws bedrock-agent list-agents --region "$REGION" --query 'agentSummaries[?contains(agentName, `'"$PROJECT_NAME"'`)]' 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        log_warning "无法获取Bedrock Agents信息，可能还未部署"
        WARNING_COUNT=$((WARNING_COUNT + 1))
        return 0
    fi
    
    local agent_count
    agent_count=$(echo "$agents_json" | python3 -c "import json, sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    
    if [[ "$agent_count" -lt 4 ]]; then
        log_warning "期望4个Bedrock Agents，但只找到$agent_count个"
        WARNING_COUNT=$((WARNING_COUNT + 1))
    fi
    
    # 检查Terraform配置中的Agent IDs
    if [[ -f "infrastructure/main.tf" ]]; then
        local terraform_agents
        terraform_agents=$(grep -E "(orchestrator|content|visual|compiler)_agent_id.*=" infrastructure/main.tf | wc -l)
        
        if [[ "$terraform_agents" -lt 4 ]]; then
            log_error "Terraform配置中Agent ID配置不完整"
            ERROR_COUNT=$((ERROR_COUNT + 1))
            
            if [[ "$AUTO_FIX" == "true" ]]; then
                log_info "尝试自动修复Agent ID配置..."
                if python3 scripts/deployment_health_validator.py --fix; then
                    log_success "Agent ID配置已修复"
                else
                    log_error "自动修复失败"
                fi
            fi
        fi
    fi
    
    log_success "Bedrock Agent配置检查完成"
    return 0
}

# 检查Lambda依赖打包
check_lambda_packaging() {
    log_info "检查Lambda依赖打包..."
    
    # 检查utils模块是否存在
    if [[ ! -f "lambdas/utils/api_utils.py" ]]; then
        log_error "lambdas/utils/api_utils.py 不存在"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
    
    # 检查requirements.txt
    if [[ ! -f "lambdas/layers/requirements.txt" ]]; then
        log_error "lambdas/layers/requirements.txt 不存在"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        # 检查关键依赖
        if ! grep -q "aws-lambda-powertools" lambdas/layers/requirements.txt; then
            log_error "requirements.txt 中缺少 aws-lambda-powertools"
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi
        
        if ! grep -q "boto3" lambdas/layers/requirements.txt; then
            log_error "requirements.txt 中缺少 boto3"
            ERROR_COUNT=$((ERROR_COUNT + 1))
        fi
    fi
    
    # 检查是否需要重新打包
    local needs_repack=false
    
    # 检查API Lambda函数
    for py_file in lambdas/api/*.py; do
        [[ ! -f "$py_file" ]] && continue
        
        local zip_file="${py_file%.py}.zip"
        
        if [[ ! -f "$zip_file" ]]; then
            log_warning "缺少Lambda包: $(basename "$zip_file")"
            needs_repack=true
        elif [[ "$py_file" -nt "$zip_file" ]]; then
            log_warning "Lambda源码比包文件新: $(basename "$py_file")"
            needs_repack=true
        fi
    done
    
    # 检查utils模块是否比zip文件新
    if find lambdas/utils -name "*.py" -newer lambdas/api/*.zip 2>/dev/null | head -1 | grep -q .; then
        log_warning "utils模块有更新，需要重新打包Lambda函数"
        needs_repack=true
    fi
    
    if [[ "$needs_repack" == "true" ]]; then
        WARNING_COUNT=$((WARNING_COUNT + 1))
        
        if [[ "$AUTO_FIX" == "true" ]]; then
            log_info "自动重新打包Lambda函数..."
            if make package-lambdas; then
                log_success "Lambda函数重新打包完成"
            else
                log_error "Lambda函数打包失败"
                ERROR_COUNT=$((ERROR_COUNT + 1))
            fi
        else
            log_warning "建议运行 'make package-lambdas' 重新打包"
        fi
    fi
    
    log_success "Lambda依赖打包检查完成"
    return 0
}

# 检查Terraform状态
check_terraform_state() {
    log_info "检查Terraform状态..."
    
    if [[ ! -d "infrastructure" ]]; then
        log_error "infrastructure目录不存在"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        return 1
    fi
    
    cd infrastructure
    
    # 检查Terraform初始化
    if [[ ! -d ".terraform" ]]; then
        log_warning "Terraform未初始化"
        
        if [[ "$AUTO_FIX" == "true" ]]; then
            log_info "自动初始化Terraform..."
            if terraform init; then
                log_success "Terraform初始化完成"
            else
                log_error "Terraform初始化失败"
                ERROR_COUNT=$((ERROR_COUNT + 1))
                cd ..
                return 1
            fi
        else
            WARNING_COUNT=$((WARNING_COUNT + 1))
        fi
    fi
    
    # 检查Terraform配置语法
    if ! terraform validate >/dev/null 2>&1; then
        log_error "Terraform配置验证失败"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        cd ..
        return 1
    fi
    
    cd ..
    log_success "Terraform状态检查通过"
    return 0
}

# 生成部署报告
generate_report() {
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    local report_file="pre_deploy_report_$(date +%Y%m%d_%H%M%S).json"
    
    cat > "$report_file" << EOF
{
    "timestamp": "$timestamp",
    "project": "$PROJECT_NAME",
    "region": "$REGION",
    "validation_results": {
        "errors": $ERROR_COUNT,
        "warnings": $WARNING_COUNT,
        "auto_fix_enabled": $AUTO_FIX
    },
    "checks_performed": [
        "prerequisites",
        "project_structure",
        "bedrock_agents",
        "lambda_packaging",
        "terraform_state"
    ],
    "ready_for_deployment": $([ $ERROR_COUNT -eq 0 ] && echo "true" || echo "false")
}
EOF
    
    log_info "部署报告已生成: $report_file"
}

# 主函数
main() {
    echo "=================================="
    echo "AI PPT Assistant 预部署验证"
    echo "时间: $(date)"
    echo "项目: $PROJECT_NAME"
    echo "区域: $REGION"
    echo "自动修复: $AUTO_FIX"
    echo "=================================="
    
    # 执行检查
    check_prerequisites
    check_project_structure
    check_bedrock_agents
    check_lambda_packaging
    check_terraform_state
    
    # 生成报告
    generate_report
    
    # 输出结果
    echo "=================================="
    if [[ $ERROR_COUNT -eq 0 ]]; then
        log_success "✅ 预部署验证通过！可以安全部署。"
        if [[ $WARNING_COUNT -gt 0 ]]; then
            log_warning "发现 $WARNING_COUNT 个警告，但不影响部署"
        fi
        exit 0
    else
        log_error "❌ 预部署验证失败！发现 $ERROR_COUNT 个错误需要修复。"
        if [[ $WARNING_COUNT -gt 0 ]]; then
            log_warning "另外发现 $WARNING_COUNT 个警告"
        fi
        
        echo ""
        echo "建议修复措施："
        echo "1. 检查上述错误信息并手动修复"
        echo "2. 运行 './scripts/pre_deploy_validator.sh --fix' 尝试自动修复"
        echo "3. 运行 'python3 scripts/deployment_health_validator.py --fix' 进行深度检查"
        
        exit 1
    fi
}

# 执行主函数
main