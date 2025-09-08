#!/bin/bash
# API Gateway 分阶段部署脚本
# 使用 terraform apply -target 方式，按依赖关系分阶段部署资源

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

# 检查参数
AUTO_APPROVE=${1:-""}
if [[ "$AUTO_APPROVE" == "--auto-approve" ]]; then
    APPROVE_FLAG="--auto-approve"
    log "使用自动批准模式"
else
    APPROVE_FLAG=""
    log "使用交互式部署模式"
fi

log "开始 API Gateway 分阶段部署..."

# 运行部署前验证
log "执行部署前验证..."
if [[ -x "./validate_deployment.sh" ]]; then
    if ! ./validate_deployment.sh; then
        error "部署前验证失败，停止部署"
    fi
else
    log "WARNING: 验证脚本不存在或不可执行，跳过验证"
fi

# 阶段 1: 基础设施层（无依赖）
log "======================================"
log "阶段 1: 部署基础设施层（VPC, S3, DynamoDB, SQS）"
log "======================================"

stage1_targets=(
    "module.vpc"
    "module.s3"
    "module.dynamodb"
    "aws_sqs_queue.task_queue"
    "aws_sqs_queue.dlq"
    "random_id.bucket_suffix"
    "aws_cloudwatch_log_group.api_gateway_stage"
)

for target in "${stage1_targets[@]}"; do
    log "部署: $target"
    if ! terraform apply $APPROVE_FLAG -target="$target"; then
        error "部署 $target 失败"
    fi
done

success "阶段 1 部署完成"

# 阶段 2: API Gateway 基础结构（无 Lambda 集成）
log "======================================"
log "阶段 2: 部署 API Gateway 基础结构"
log "======================================"

stage2_targets=(
    "module.api_gateway"
    # API Gateway 额外资源
    "aws_api_gateway_resource.tasks"
    "aws_api_gateway_resource.task_id"
    "aws_api_gateway_resource.templates"
    "aws_api_gateway_resource.health"
    "aws_api_gateway_resource.health_ready"
    # Methods（不包括集成）
    "aws_api_gateway_method.get_task"
    "aws_api_gateway_method.get_templates"
    "aws_api_gateway_method.templates_options"
    "aws_api_gateway_method.task_options"
    "aws_api_gateway_method.health_get"
    "aws_api_gateway_method.health_ready_get"
)

for target in "${stage2_targets[@]}"; do
    log "部署: $target"
    if ! terraform apply $APPROVE_FLAG -target="$target"; then
        error "部署 $target 失败"
    fi
done

success "阶段 2 部署完成"

# 阶段 3: Lambda 函数
log "======================================"
log "阶段 3: 部署 Lambda 函数"
log "======================================"

stage3_targets=(
    "module.lambda"
    # 单独的 Lambda 函数（如果存在）
    "aws_lambda_function.list_presentations"
)

for target in "${stage3_targets[@]}"; do
    log "部署: $target"
    if ! terraform apply $APPROVE_FLAG -target="$target"; then
        # 某些目标可能不存在，继续执行
        log "WARNING: 部署 $target 失败或资源不存在，继续执行..."
    fi
done

success "阶段 3 部署完成"

# 阶段 4: Method Responses
log "======================================"
log "阶段 4: 部署 Method Responses"
log "======================================"

stage4_targets=(
    "aws_api_gateway_method_response.get_task_200"
    "aws_api_gateway_method_response.get_templates_200"
    "aws_api_gateway_method_response.templates_options_200"
    "aws_api_gateway_method_response.task_options_200"
    "aws_api_gateway_method_response.health_200"
    "aws_api_gateway_method_response.health_ready_200"
)

for target in "${stage4_targets[@]}"; do
    log "部署: $target"
    if ! terraform apply $APPROVE_FLAG -target="$target"; then
        error "部署 $target 失败"
    fi
done

success "阶段 4 部署完成"

# 阶段 5: API Gateway Integrations
log "======================================"
log "阶段 5: 部署 API Gateway Integrations"
log "======================================"

stage5_targets=(
    "aws_api_gateway_integration.create_presentation"
    "aws_api_gateway_integration.get_presentation"
    "aws_api_gateway_integration.list_presentations"
    "aws_api_gateway_integration.create_session"
    "aws_api_gateway_integration.get_session"
    "aws_api_gateway_integration.execute_agent"
    "aws_api_gateway_integration.get_task"
    "aws_api_gateway_integration.get_templates"
    "aws_api_gateway_integration.templates_options"
    "aws_api_gateway_integration.task_options"
    "aws_api_gateway_integration.health"
    "aws_api_gateway_integration.health_ready"
)

for target in "${stage5_targets[@]}"; do
    log "部署: $target"
    if ! terraform apply $APPROVE_FLAG -target="$target"; then
        log "WARNING: 部署 $target 失败，可能是资源不存在，继续执行..."
    fi
done

success "阶段 5 部署完成"

# 阶段 6: Integration Responses
log "======================================"
log "阶段 6: 部署 Integration Responses"
log "======================================"

stage6_targets=(
    "aws_api_gateway_integration_response.get_templates_200"
    "aws_api_gateway_integration_response.templates_options_200"
    "aws_api_gateway_integration_response.task_options_200"
    "aws_api_gateway_integration_response.health_200"
    "aws_api_gateway_integration_response.health_ready_200"
)

for target in "${stage6_targets[@]}"; do
    log "部署: $target"
    if ! terraform apply $APPROVE_FLAG -target="$target"; then
        log "WARNING: 部署 $target 失败，可能是资源不存在，继续执行..."
    fi
done

success "阶段 6 部署完成"

# 阶段 7: Lambda Permissions
log "======================================"
log "阶段 7: 部署 Lambda Permissions"
log "======================================"

stage7_targets=(
    "aws_lambda_permission.generate_presentation_permission"
    "aws_lambda_permission.presentation_status_permission"
)

for target in "${stage7_targets[@]}"; do
    log "部署: $target"
    if ! terraform apply $APPROVE_FLAG -target="$target"; then
        log "WARNING: 部署 $target 失败，可能是资源不存在，继续执行..."
    fi
done

success "阶段 7 部署完成"

# 阶段 8: API Gateway Deployment & Stage
log "======================================"
log "阶段 8: 部署 API Gateway Deployment 和 Stage"
log "======================================"

stage8_targets=(
    "aws_api_gateway_deployment.integration_deployment"
    "aws_api_gateway_stage.main"
    "aws_api_gateway_usage_plan.main"
    "aws_api_gateway_usage_plan_key.main"
)

for target in "${stage8_targets[@]}"; do
    log "部署: $target"
    if ! terraform apply $APPROVE_FLAG -target="$target"; then
        error "部署 $target 失败"
    fi
done

success "阶段 8 部署完成"

# 最终完整部署检查
log "======================================"
log "执行最终完整部署检查..."
log "======================================"

log "运行完整 terraform apply 确保所有资源同步..."
if ! terraform apply $APPROVE_FLAG; then
    error "最终完整部署检查失败"
fi

success "分阶段部署成功完成！"

# 显示重要输出信息
log "======================================"
log "部署完成信息:"
log "======================================"

# 获取 API Gateway URL
api_url=$(terraform output -raw api_gateway_url 2>/dev/null || echo "未找到")
log "API Gateway URL: $api_url"

# 获取 API Key（敏感信息，不显示具体值）
if terraform output api_gateway_api_key >/dev/null 2>&1; then
    log "API Key: 已创建（使用 'terraform output api_gateway_api_key' 查看）"
else
    log "API Key: 未创建或不可用"
fi

log ""
log "建议后续操作："
log "1. 运行健康检查: ./health_check.sh"
log "2. 测试 API 端点功能"
log "3. 检查 CloudWatch 日志以确认正常运行"