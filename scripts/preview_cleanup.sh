#!/bin/bash

# 根目录清理预览脚本
# 作者：Claude
# 日期：2025-09-12
# 描述：预览将要清理的文件，不执行实际操作

set -e

echo "=========================================="
echo "🔍 根目录清理方案预览"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 统计当前文件数量
CURRENT_COUNT=$(ls -1 | wc -l)
echo -e "当前根目录文件数量: ${CURRENT_COUNT}\n"

# ========================================
# 第一优先级：将要删除的文件
# ========================================
echo -e "${RED}🔴 第一优先级 - 将要删除的文件：${NC}"
echo "----------------------------------------"

DELETE_COUNT=0

# API测试报告（保留最新3个）
OLD_API_REPORTS=$(ls -t api_test_report_*.json 2>/dev/null | tail -n +4)
if [ -n "$OLD_API_REPORTS" ]; then
    echo -e "${RED}旧的API测试报告:${NC}"
    for f in $OLD_API_REPORTS; do
        echo "  - $f ($(ls -lh "$f" | awk '{print $5}'))"
        DELETE_COUNT=$((DELETE_COUNT + 1))
    done
fi

# 其他时间戳报告
for pattern in "agent_config_fix_report_*.json" "config_center_report_*.json" \
               "deployment_validation_report_*.json" "regression_test_report_*.json"; do
    if ls -t $pattern 2>/dev/null | tail -n +2 | grep -q .; then
        echo -e "${RED}旧的$(echo $pattern | cut -d'_' -f1-3)报告:${NC}"
        ls -t $pattern 2>/dev/null | tail -n +2 | while read f; do
            echo "  - $f ($(ls -lh "$f" | awk '{print $5}'))"
            ((DELETE_COUNT++))
        done
    fi
done

# 备份文件
echo -e "${RED}备份文件:${NC}"
for f in *.backup Makefile.backup.* *.py.backup*; do
    [ -f "$f" ] && echo "  - $f ($(ls -lh "$f" | awk '{print $5}'))" && ((DELETE_COUNT++))
done

# 日志文件
echo -e "${RED}日志文件:${NC}"
for f in deploy_output.log deployment_log_*.log regression_test_*.log destroy_output.log; do
    [ -f "$f" ] && echo "  - $f ($(ls -lh "$f" | awk '{print $5}'))" && ((DELETE_COUNT++))
done

# 其他临时文件
echo -e "${RED}其他临时文件:${NC}"
for f in response-claude*.json presentation_response.json terraform.tfstate \
         presentation_status.zip dynamodb_backup_*.json migration_report_*.json \
         api_test_results.json pre_deploy_check_*.txt deployment_validation_20*.json; do
    [ -f "$f" ] && echo "  - $f ($(ls -lh "$f" | awk '{print $5}'))" && ((DELETE_COUNT++))
done

# ========================================
# 第二优先级：将要移动的文件
# ========================================
echo -e "\n${YELLOW}🟡 第二优先级 - 将要移动到子目录的文件：${NC}"
echo "----------------------------------------"

MOVE_COUNT=0

# 测试脚本 -> tests/validation/
echo -e "${YELLOW}移动到 tests/validation/:${NC}"
for f in test_*.py comprehensive_*.py regression_test.py final_validation.py \
         deployment_validation.py post_deploy_validation.py system_health_check.py; do
    [ -f "$f" ] && echo "  - $f" && ((MOVE_COUNT++))
done

# 工具脚本 -> scripts/tools/
echo -e "${YELLOW}移动到 scripts/tools/:${NC}"
for f in fix_data_issue.py lambda_config_helper.py get_api_key.sh; do
    [ -f "$f" ] && echo "  - $f" && ((MOVE_COUNT++))
done

# 部署脚本 -> scripts/
echo -e "${YELLOW}移动到 scripts/:${NC}"
for f in deploy deploy.sh deploy_fixes.sh deploy_lambdas.sh configure_gateway.sh \
         verify_deploy.sh delete_cloudfront_distributions.sh delete_remaining_distributions.sh; do
    [ -f "$f" ] && echo "  - $f" && ((MOVE_COUNT++))
done

# ========================================
# 第三优先级：文档整理
# ========================================
echo -e "\n${GREEN}🟢 第三优先级 - 将要整理的文档：${NC}"
echo "----------------------------------------"

DOC_COUNT=0

# 中文文档 -> docs/reports/
echo -e "${GREEN}移动到 docs/reports/:${NC}"
for f in 修复成功报告.md 工作记录.md 覆盖问题分析报告.md; do
    [ -f "$f" ] && echo "  - $f" && ((DOC_COUNT++))
done

# 英文文档
for f in API_TEST_REPORT.md deployment_regression_report.md; do
    [ -f "$f" ] && echo "  - $f" && ((DOC_COUNT++))
done

# 移动到 docs/
echo -e "${GREEN}移动到 docs/:${NC}"
for f in deployment-optimization-guide.md DEPLOYMENT_GUIDE.md Makefile.enhanced Makefile.optimized; do
    [ -f "$f" ] && echo "  - $f" && ((DOC_COUNT++))
done

# JSON报告 -> docs/reports/latest/
echo -e "${GREEN}移动到 docs/reports/latest/:${NC}"
for f in api_config_info.json api_gateway_config.json backend_test_report.json \
         comprehensive_validation_report.json deployment_validation_report.json \
         final_validation_report.json system_health_report.json test_results_api.json; do
    [ -f "$f" ] && echo "  - $f" && ((DOC_COUNT++))
done

# 保留最新的API测试报告
if ls api_test_report_*.json 1> /dev/null 2>&1; then
    LATEST=$(ls -t api_test_report_*.json | head -1)
    [ -f "$LATEST" ] && echo "  - $LATEST (最新)" && ((DOC_COUNT++))
fi

# ========================================
# 统计汇总
# ========================================
echo -e "\n=========================================="
echo -e "${BLUE}📊 清理统计：${NC}"
echo "----------------------------------------"
echo -e "当前文件总数: ${CURRENT_COUNT}"
echo -e "${RED}将要删除: ${DELETE_COUNT} 个文件${NC}"
echo -e "${YELLOW}将要移动: ${MOVE_COUNT} 个文件${NC}"
echo -e "${GREEN}将要整理: ${DOC_COUNT} 个文档${NC}"

REMAIN_COUNT=$((CURRENT_COUNT - DELETE_COUNT - MOVE_COUNT - DOC_COUNT))
echo -e "\n预计清理后根目录文件数: ${REMAIN_COUNT}"

# ========================================
# 保留的核心文件
# ========================================
echo -e "\n${BLUE}⚪ 将保留在根目录的核心文件：${NC}"
echo "----------------------------------------"
echo "配置文件: .gitignore, .flake8, CLAUDE.md, README.md, Makefile"
echo "核心目录: agents/, api/, artifacts/, config/, docs/, frontend/"
echo "         infrastructure/, lambdas/, lambda-layers/, scripts/"
echo "         security/, tests/, test-data/, test-results/"

echo -e "\n=========================================="
echo -e "${BLUE}执行清理操作？${NC}"
echo "1. 运行 ${GREEN}bash scripts/cleanup_root_directory.sh${NC} 执行实际清理"
echo "2. 运行 ${YELLOW}bash scripts/cleanup_root_directory.sh --dry-run${NC} 进行模拟运行"
echo "=========================================="