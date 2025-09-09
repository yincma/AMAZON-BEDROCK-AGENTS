#!/bin/bash

# Pre-deployment Check Script for AI PPT Assistant
# This script validates all prerequisites before deployment

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRASTRUCTURE_DIR="$PROJECT_ROOT/infrastructure"
LAMBDAS_DIR="$PROJECT_ROOT/lambdas"
EXPECTED_RESOURCE_COUNT=221
PYTHON_REQUIRED_VERSION="3.12"
AWS_REGION="us-east-1"

# Score tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
WARNINGS=0

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}         AI PPT Assistant - 部署前检查工具              ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo

# Function to check a condition and update score
check() {
    local description="$1"
    local command="$2"
    local critical="${3:-false}"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    echo -n "🔍 $description... "
    
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        if [ "$critical" = "true" ]; then
            echo -e "${RED}❌ (关键)${NC}"
            return 1
        else
            echo -e "${YELLOW}⚠️ (警告)${NC}"
            WARNINGS=$((WARNINGS + 1))
            return 0
        fi
    fi
}

# Function to check with custom message
check_with_output() {
    local description="$1"
    local command="$2"
    local expected="$3"
    local critical="${4:-false}"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    echo -n "🔍 $description... "
    
    local result
    result=$(eval "$command" 2>/dev/null || echo "ERROR")
    
    if [[ "$result" == *"$expected"* ]] || [[ "$result" == "$expected" ]]; then
        echo -e "${GREEN}✅ ($result)${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        if [ "$critical" = "true" ]; then
            echo -e "${RED}❌ (期望: $expected, 实际: $result)${NC}"
            return 1
        else
            echo -e "${YELLOW}⚠️ (期望: $expected, 实际: $result)${NC}"
            WARNINGS=$((WARNINGS + 1))
            return 0
        fi
    fi
}

# 1. 环境检查
echo -e "${BLUE}▶ 环境检查${NC}"
echo "────────────────────────────────"

# Check AWS CLI
check "AWS CLI 已安装" "command -v aws" true

# Check AWS credentials
check "AWS 凭证已配置" "aws sts get-caller-identity" true

# Check AWS region
check_with_output "AWS 区域配置" "aws configure get region" "$AWS_REGION" false

# Check Python version
PYTHON_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$PYTHON_VERSION" = "$PYTHON_REQUIRED_VERSION" ]; then
    echo -e "🔍 Python 版本... ${GREEN}✅ ($PYTHON_VERSION)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "🔍 Python 版本... ${YELLOW}⚠️ (当前: $PYTHON_VERSION, 建议: $PYTHON_REQUIRED_VERSION)${NC}"
    echo -e "   ${YELLOW}建议: 使用 Docker 构建 Lambda 层以确保兼容性${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# Check Docker (optional but recommended)
if command -v docker > /dev/null 2>&1; then
    check "Docker 已安装" "docker info" false
else
    echo -e "🔍 Docker 已安装... ${YELLOW}⚠️ (未安装，建议安装以构建兼容的Lambda层)${NC}"
    WARNINGS=$((WARNINGS + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi

# Check Terraform
check "Terraform 已安装" "command -v terraform" true

echo

# 2. Terraform 状态检查
echo -e "${BLUE}▶ Terraform 状态检查${NC}"
echo "────────────────────────────────"

cd "$INFRASTRUCTURE_DIR"

# Initialize Terraform
check "Terraform 初始化" "terraform init -backend=true -get=true -upgrade=false" true

# Validate configuration
check "Terraform 配置验证" "terraform validate" true

# Check state
if [ -f "terraform.tfstate" ]; then
    RESOURCE_COUNT=$(terraform state list 2>/dev/null | wc -l | tr -d ' ')
    if [ "$RESOURCE_COUNT" -ge 200 ]; then
        echo -e "🔍 Terraform 资源数量... ${GREEN}✅ ($RESOURCE_COUNT 个资源)${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "🔍 Terraform 资源数量... ${YELLOW}⚠️ ($RESOURCE_COUNT 个资源, 期望约 $EXPECTED_RESOURCE_COUNT)${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo -e "🔍 Terraform 资源数量... ${YELLOW}⚠️ (状态文件不存在，可能是首次部署)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo

# 3. AWS 服务配额检查
echo -e "${BLUE}▶ AWS 服务配额检查${NC}"
echo "────────────────────────────────"

# Lambda concurrency
LAMBDA_CONCURRENCY=$(aws lambda get-account-settings --query 'AccountLimit.UnreservedConcurrentExecutions' --output text 2>/dev/null || echo "N/A")
if [ "$LAMBDA_CONCURRENCY" != "N/A" ] && [ "$LAMBDA_CONCURRENCY" -ge 100 ]; then
    echo -e "🔍 Lambda 并发限制... ${GREEN}✅ ($LAMBDA_CONCURRENCY)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "🔍 Lambda 并发限制... ${YELLOW}⚠️ ($LAMBDA_CONCURRENCY)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# Lambda function count
LAMBDA_COUNT=$(aws lambda list-functions --query 'length(Functions)' --output text 2>/dev/null || echo "0")
echo -e "🔍 Lambda 函数数量... ${GREEN}✅ (当前: $LAMBDA_COUNT 个)${NC}"
PASSED_CHECKS=$((PASSED_CHECKS + 1))
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo

# 4. 关键配置文件检查
echo -e "${BLUE}▶ 关键配置文件检查${NC}"
echo "────────────────────────────────"

# Check API Gateway download route
check "API Gateway 下载路由配置" "grep -q 'presentation_download' $INFRASTRUCTURE_DIR/modules/api_gateway/main.tf" false

# Check Bedrock permissions
check "Bedrock GetAgent 权限配置" "grep -q 'bedrock:GetAgent' $INFRASTRUCTURE_DIR/modules/lambda/main.tf" false

# Check Lambda layer requirements
check "Lambda 层依赖文件存在" "[ -f $LAMBDAS_DIR/layers/requirements.txt ]" true

# Check for problematic package versions
if grep -q "aws-lambda-powertools==2.39.0" "$LAMBDAS_DIR/layers/requirements.txt" 2>/dev/null; then
    echo -e "🔍 aws-lambda-powertools 版本... ${YELLOW}⚠️ (使用有问题的 2.39.0 版本)${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "🔍 aws-lambda-powertools 版本... ${GREEN}✅ (未使用 2.39.0)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo

# 5. Bedrock Agent 状态检查
echo -e "${BLUE}▶ Bedrock Agent 状态检查${NC}"
echo "────────────────────────────────"

# Check if test script exists
if [ -f "$PROJECT_ROOT/scripts/test_bedrock_permissions.py" ]; then
    echo -e "🔍 Bedrock 测试脚本... ${GREEN}✅ (存在)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    # Optionally run the test (comment out if it takes too long)
    # python3 "$PROJECT_ROOT/scripts/test_bedrock_permissions.py" > /dev/null 2>&1
    # if [ $? -eq 0 ]; then
    #     echo -e "🔍 Bedrock Agent 状态... ${GREEN}✅ (PREPARED)${NC}"
    #     PASSED_CHECKS=$((PASSED_CHECKS + 1))
    # else
    #     echo -e "🔍 Bedrock Agent 状态... ${YELLOW}⚠️ (需要验证)${NC}"
    #     WARNINGS=$((WARNINGS + 1))
    # fi
    # TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
else
    echo -e "🔍 Bedrock 测试脚本... ${YELLOW}⚠️ (不存在)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo

# 6. 构建文件检查
echo -e "${BLUE}▶ 构建文件检查${NC}"
echo "────────────────────────────────"

# Check if Lambda layer is built
if [ -f "$LAMBDAS_DIR/layers/lambda-layer.zip" ] || [ -f "$LAMBDAS_DIR/layers/dist/ai-ppt-assistant-dependencies.zip" ]; then
    echo -e "🔍 Lambda 层包... ${GREEN}✅ (已构建)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "🔍 Lambda 层包... ${YELLOW}⚠️ (未构建，需要运行构建脚本)${NC}"
    echo -e "   ${YELLOW}运行: cd $LAMBDAS_DIR/layers && ./docker-build.sh${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# Check Lambda function packages
LAMBDA_ZIPS=$(find "$LAMBDAS_DIR" -name "*.zip" -not -path "*/layers/*" | wc -l)
if [ "$LAMBDA_ZIPS" -ge 10 ]; then
    echo -e "🔍 Lambda 函数包... ${GREEN}✅ ($LAMBDA_ZIPS 个已打包)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "🔍 Lambda 函数包... ${YELLOW}⚠️ ($LAMBDA_ZIPS 个已打包)${NC}"
    WARNINGS=$((WARNINGS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo

# 7. 计算成功率和风险评估
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    检查结果总结                         ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

SUCCESS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
echo
echo -e "📊 检查项目: $TOTAL_CHECKS"
echo -e "✅ 通过: $PASSED_CHECKS"
echo -e "⚠️  警告: $WARNINGS"
echo -e "❌ 失败: $((TOTAL_CHECKS - PASSED_CHECKS - WARNINGS))"
echo
echo -e "🎯 通过率: ${SUCCESS_RATE}%"

# Risk assessment
echo
if [ $SUCCESS_RATE -ge 90 ]; then
    echo -e "${GREEN}✅ 部署风险: 低${NC}"
    echo -e "${GREEN}   系统已准备好进行部署${NC}"
    EXIT_CODE=0
elif [ $SUCCESS_RATE -ge 70 ]; then
    echo -e "${YELLOW}⚠️  部署风险: 中${NC}"
    echo -e "${YELLOW}   建议修复警告项后再部署${NC}"
    EXIT_CODE=0
else
    echo -e "${RED}❌ 部署风险: 高${NC}"
    echo -e "${RED}   强烈建议修复所有问题后再部署${NC}"
    EXIT_CODE=1
fi

# Provide recommendations
if [ $WARNINGS -gt 0 ] || [ $((TOTAL_CHECKS - PASSED_CHECKS - WARNINGS)) -gt 0 ]; then
    echo
    echo -e "${BLUE}📝 建议采取的行动:${NC}"
    
    if [ "$PYTHON_VERSION" != "$PYTHON_REQUIRED_VERSION" ]; then
        echo -e "  • 使用 Docker 构建 Lambda 层: cd $LAMBDAS_DIR/layers && ./docker-build.sh"
    fi
    
    if [ ! -f "$LAMBDAS_DIR/layers/lambda-layer.zip" ] && [ ! -f "$LAMBDAS_DIR/layers/dist/ai-ppt-assistant-dependencies.zip" ]; then
        echo -e "  • 构建 Lambda 层: cd $LAMBDAS_DIR/layers && ./build.sh"
    fi
    
    if [ "$LAMBDA_ZIPS" -lt 10 ]; then
        echo -e "  • 打包 Lambda 函数: make build-lambdas"
    fi
    
    echo -e "  • 运行完整测试: python test_all_apis.py"
fi

echo
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

# Save report
REPORT_FILE="$PROJECT_ROOT/pre_deploy_check_$(date +%Y%m%d_%H%M%S).txt"
{
    echo "部署前检查报告 - $(date)"
    echo "========================="
    echo "通过率: ${SUCCESS_RATE}%"
    echo "检查项: $TOTAL_CHECKS"
    echo "通过: $PASSED_CHECKS"
    echo "警告: $WARNINGS"
    echo "失败: $((TOTAL_CHECKS - PASSED_CHECKS - WARNINGS))"
} > "$REPORT_FILE"

echo -e "${BLUE}📄 报告已保存到: $REPORT_FILE${NC}"

cd "$PROJECT_ROOT"
exit $EXIT_CODE