#!/bin/bash
# AI PPT Assistant 完整部署脚本
# 包含图片生成服务的自动化部署和验证

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TF_VAR_FILE="${TF_VAR_FILE:-terraform.tfvars}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🚀 开始部署 AI-PPT-Assistant..."

# 解析命令行参数
ACTION="${1:-apply}"
FORCE="${2:-false}"

# 显示帮助信息
show_help() {
    cat << EOF
AI PPT Assistant 部署脚本

用法: $0 [操作] [选项]

操作:
    plan        生成部署计划（默认）
    apply       执行部署
    destroy     销毁资源
    validate    验证部署状态
    test        运行集成测试

选项:
    -f, --force    强制执行，跳过确认

示例:
    $0 plan                 # 生成部署计划
    $0 apply                # 执行部署
    $0 destroy -f           # 强制销毁资源
    $0 validate             # 验证部署状态

环境变量:
    AWS_REGION              AWS区域
    AWS_PROFILE             AWS配置文件
    ENVIRONMENT             环境名称 (默认: dev)

EOF
}

# 验证环境
validate_environment() {
    log_info "验证部署环境..."

    # 检查必需工具
    local required_tools=("terraform" "aws" "python3" "zip" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "缺少必需工具: $tool"
            exit 1
        fi
    done

    # 检查AWS凭证
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS凭证配置错误或已过期"
        exit 1
    fi

    # 检查变量文件
    if [[ ! -f "$TF_VAR_FILE" ]]; then
        log_warning "变量文件 $TF_VAR_FILE 不存在，将使用默认值"
        if [[ -f "terraform.tfvars.example" ]]; then
            log_info "创建默认变量文件..."
            cp terraform.tfvars.example "$TF_VAR_FILE"
            log_warning "请编辑 $TF_VAR_FILE 并设置适当的值"
        fi
    fi

    log_success "环境验证通过"
}

# 构建Lambda包
build_lambda_packages() {
    log_info "构建Lambda部署包..."

    cd "$PROJECT_ROOT"

    # 执行打包脚本
    if [[ -x "scripts/package_lambdas.sh" ]]; then
        ./scripts/package_lambdas.sh
    else
        log_error "打包脚本不存在或不可执行"
        exit 1
    fi

    log_success "Lambda包构建完成"
}

# 处理不同操作
case "$ACTION" in
    "help"|"-h"|"--help")
        show_help
        exit 0
        ;;
    "plan")
        validate_environment
        build_lambda_packages
        echo "📋 生成部署计划..."
        terraform plan -var-file="$TF_VAR_FILE" -var="environment=$ENVIRONMENT"
        exit 0
        ;;
    "validate")
        log_info "验证部署状态..."
        # 这里添加验证逻辑
        terraform show &> /dev/null && log_success "部署验证通过" || log_error "部署验证失败"
        exit 0
        ;;
    "destroy")
        if [[ "$FORCE" != "-f" && "$FORCE" != "--force" ]]; then
            echo ""
            log_error "⚠️  即将销毁所有资源！"
            echo "这将永久删除以下资源："
            echo "  - Lambda函数和层"
            echo "  - S3存储桶及所有内容"
            echo "  - DynamoDB表及所有数据"
            echo "  - CloudWatch日志和指标"
            echo "  - IAM角色和策略"
            echo ""
            read -p "确认销毁？请输入 'DELETE' 确认: " confirm
            if [[ "$confirm" != "DELETE" ]]; then
                log_info "销毁已取消"
                exit 0
            fi
        fi
        terraform destroy -var-file="$TF_VAR_FILE" -var="environment=$ENVIRONMENT" -auto-approve
        log_success "资源销毁完成"
        exit 0
        ;;
esac

# 默认执行部署
validate_environment
build_lambda_packages

# 确认部署
echo "即将创建以下资源："
echo "  - 图片生成Lambda函数（基础版 + 优化版）"
echo "  - Lambda依赖层"
echo "  - S3存储桶（PPT存储 + 图片缓存）"
echo "  - DynamoDB表（演示文稿元数据）"
echo "  - IAM角色和策略（Bedrock、S3、DynamoDB访问权限）"
echo "  - CloudWatch监控和告警"
echo "  - X-Ray追踪配置"
echo ""
echo "环境: $ENVIRONMENT"
if [[ "$FORCE" != "-f" && "$FORCE" != "--force" ]]; then
    read -p "确认部署？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 部署已取消"
        exit 1
    fi
fi

# 执行部署
echo "📦 执行Terraform部署..."
terraform apply -var-file="$TF_VAR_FILE" -var="environment=$ENVIRONMENT" -auto-approve

# 获取输出
echo ""
echo "✅ 部署成功！"
echo ""
echo "📋 部署信息："
echo "================================"

# 安全地获取输出
get_output() {
    terraform output -raw "$1" 2>/dev/null || echo "N/A"
}

# 显示核心信息
BUCKET=$(get_output "presentations_bucket_name")
IMAGE_FUNC=$(get_output "image_generator_function_name")
IMAGE_URL=$(get_output "image_generator_function_url")
DASHBOARD_URL=$(get_output "cloudwatch_dashboard_url")

echo "S3存储桶: $BUCKET"
echo "图片生成函数: $IMAGE_FUNC"
if [[ "$IMAGE_URL" != "N/A" ]]; then
    echo "Lambda函数URL: $IMAGE_URL"
fi
if [[ "$DASHBOARD_URL" != "N/A" ]]; then
    echo "监控仪表板: $DASHBOARD_URL"
fi

echo ""
echo "📝 图片生成API使用示例："
if [[ "$IMAGE_URL" != "N/A" ]]; then
    echo "curl -X POST '$IMAGE_URL' \\"
    echo "  -H 'Content-Type: application/json' \\"
    echo "  -d '{\"slide_content\": {\"title\": \"示例标题\", \"content\": [\"内容1\", \"内容2\"]}}'"
else
    echo "通过AWS CLI调用Lambda函数:"
    echo "aws lambda invoke --function-name $IMAGE_FUNC --payload '{\"slide_content\":{\"title\":\"示例\"}}' response.json"
fi

echo ""
echo "================================"

# 保存部署信息
DEPLOY_INFO="deployment_info_$ENVIRONMENT.json"
cat > "$DEPLOY_INFO" << EOF
{
  "environment": "$ENVIRONMENT",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "s3_bucket": "$BUCKET",
  "image_generator": {
    "function_name": "$IMAGE_FUNC",
    "function_url": "$IMAGE_URL"
  },
  "monitoring": {
    "dashboard_url": "$DASHBOARD_URL"
  }
}
EOF

log_success "部署信息已保存到: $DEPLOY_INFO"

# 运行基础验证
log_info "运行部署后验证..."
sleep 5  # 等待资源就绪

# 验证Lambda函数状态
if [[ "$IMAGE_FUNC" != "N/A" ]]; then
    FUNC_STATUS=$(aws lambda get-function --function-name "$IMAGE_FUNC" --query 'Configuration.State' --output text 2>/dev/null || echo "Unknown")
    if [[ "$FUNC_STATUS" == "Active" ]]; then
        log_success "Lambda函数状态正常: $FUNC_STATUS"
    else
        log_warning "Lambda函数状态: $FUNC_STATUS"
    fi
fi

# 验证S3存储桶
if [[ "$BUCKET" != "N/A" ]] && aws s3api head-bucket --bucket "$BUCKET" &>/dev/null; then
    log_success "S3存储桶访问正常"
else
    log_warning "S3存储桶验证失败"
fi

echo ""
log_success "🎉 AI PPT Assistant 部署完成！"

echo ""
echo "📚 后续步骤："
echo "1. 检查CloudWatch仪表板查看系统状态"
echo "2. 使用提供的API示例测试图片生成功能"
echo "3. 配置邮件告警（如果设置了alert_email）"
echo "4. 运行完整的集成测试"
echo ""
echo "如需帮助，请参考文档或运行: $0 help"