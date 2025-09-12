#!/bin/bash

# 根目录清理预览脚本 V2
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
CURRENT_COUNT=$(ls -1a | grep -v '^\.\.$' | grep -v '^\.$' | wc -l)
echo -e "当前根目录文件和目录总数: ${CURRENT_COUNT}\n"

# 使用数组存储要删除/移动的文件
declare -a DELETE_FILES
declare -a MOVE_TEST_FILES
declare -a MOVE_TOOL_FILES
declare -a MOVE_DEPLOY_FILES
declare -a MOVE_DOC_FILES
declare -a MOVE_REPORT_FILES

# ========================================
# 第一优先级：收集要删除的文件
# ========================================
echo -e "${RED}🔴 第一优先级 - 将要删除的文件：${NC}"
echo "----------------------------------------"

# API测试报告（保留最新3个）
echo -e "${RED}旧的API测试报告 (保留最新3个):${NC}"
for f in $(ls -t api_test_report_*.json 2>/dev/null | tail -n +4); do
    [ -f "$f" ] && DELETE_FILES+=("$f") && echo "  - $f ($(ls -lh "$f" | awk '{print $5}'))"
done

# 其他时间戳报告（保留最新1个）
for pattern in agent_config_fix_report config_center_report deployment_validation_report regression_test_report; do
    FILES=$(ls -t ${pattern}_*.json 2>/dev/null | tail -n +2)
    if [ -n "$FILES" ]; then
        echo -e "${RED}旧的${pattern}:${NC}"
        for f in $FILES; do
            [ -f "$f" ] && DELETE_FILES+=("$f") && echo "  - $f ($(ls -lh "$f" | awk '{print $5}'))"
        done
    fi
done

# 备份文件
echo -e "${RED}备份文件:${NC}"
for f in *.backup Makefile.backup.* comprehensive_backend_test.py.backup* system_health_check.py.backup test_all_backend_apis.py.backup; do
    [ -f "$f" ] && DELETE_FILES+=("$f") && echo "  - $f ($(ls -lh "$f" | awk '{print $5}'))"
done

# 日志文件
echo -e "${RED}日志文件:${NC}"
for f in deploy_output.log deployment_log_*.log regression_test_*.log destroy_output.log test_output_comparison.sh; do
    [ -f "$f" ] && DELETE_FILES+=("$f") && echo "  - $f ($(ls -lh "$f" | awk '{print $5}'))"
done

# 其他临时文件
echo -e "${RED}其他临时文件:${NC}"
for f in response-claude*.json presentation_response.json terraform.tfstate \
         presentation_status.zip dynamodb_backup_*.json migration_report_*.json \
         api_test_results.json pre_deploy_check_*.txt deployment_validation_20*.json; do
    [ -f "$f" ] && DELETE_FILES+=("$f") && echo "  - $f ($(ls -lh "$f" | awk '{print $5}'))"
done

# ========================================
# 第二优先级：收集要移动的文件
# ========================================
echo -e "\n${YELLOW}🟡 第二优先级 - 将要移动到子目录的文件：${NC}"
echo "----------------------------------------"

# 测试脚本 -> tests/validation/
echo -e "${YELLOW}移动到 tests/validation/:${NC}"
for f in test_backend_apis.py test_all_backend_apis.py test_all_apis.py test_api_comprehensive.py \
         comprehensive_backend_test.py comprehensive_api_test.py comprehensive_validation.py \
         regression_test.py final_validation.py deployment_validation.py \
         post_deploy_validation.py system_health_check.py; do
    [ -f "$f" ] && MOVE_TEST_FILES+=("$f") && echo "  - $f"
done

# 工具脚本 -> scripts/tools/
echo -e "${YELLOW}移动到 scripts/tools/:${NC}"
for f in fix_data_issue.py lambda_config_helper.py get_api_key.sh; do
    [ -f "$f" ] && MOVE_TOOL_FILES+=("$f") && echo "  - $f"
done

# 部署脚本 -> scripts/
echo -e "${YELLOW}移动到 scripts/:${NC}"
for f in deploy deploy.sh deploy_fixes.sh deploy_lambdas.sh configure_gateway.sh \
         verify_deploy.sh delete_cloudfront_distributions.sh delete_remaining_distributions.sh; do
    [ -f "$f" ] && MOVE_DEPLOY_FILES+=("$f") && echo "  - $f"
done

# ========================================
# 第三优先级：文档整理
# ========================================
echo -e "\n${GREEN}🟢 第三优先级 - 将要整理的文档：${NC}"
echo "----------------------------------------"

# 文档 -> docs/reports/
echo -e "${GREEN}移动到 docs/reports/:${NC}"
for f in 修复成功报告.md 工作记录.md 覆盖问题分析报告.md \
         API_TEST_REPORT.md deployment_regression_report.md; do
    [ -f "$f" ] && MOVE_DOC_FILES+=("$f") && echo "  - $f"
done

# 移动到 docs/
echo -e "${GREEN}移动到 docs/:${NC}"
for f in deployment-optimization-guide.md DEPLOYMENT_GUIDE.md Makefile.enhanced Makefile.optimized; do
    [ -f "$f" ] && MOVE_DOC_FILES+=("$f") && echo "  - $f"
done

# JSON报告 -> docs/reports/latest/
echo -e "${GREEN}移动到 docs/reports/latest/:${NC}"
for f in api_config_info.json api_gateway_config.json backend_test_report.json \
         comprehensive_validation_report.json deployment_validation_report.json \
         final_validation_report.json system_health_report.json test_results_api.json; do
    [ -f "$f" ] && MOVE_REPORT_FILES+=("$f") && echo "  - $f"
done

# 保留最新的API测试报告
LATEST_API=$(ls -t api_test_report_*.json 2>/dev/null | head -1)
if [ -n "$LATEST_API" ] && [ -f "$LATEST_API" ]; then
    MOVE_REPORT_FILES+=("$LATEST_API")
    echo "  - $LATEST_API (最新版本)"
fi

# ========================================
# 统计汇总
# ========================================
DELETE_COUNT=${#DELETE_FILES[@]}
MOVE_COUNT=$((${#MOVE_TEST_FILES[@]} + ${#MOVE_TOOL_FILES[@]} + ${#MOVE_DEPLOY_FILES[@]}))
DOC_COUNT=$((${#MOVE_DOC_FILES[@]} + ${#MOVE_REPORT_FILES[@]}))

echo -e "\n=========================================="
echo -e "${BLUE}📊 清理统计：${NC}"
echo "----------------------------------------"
echo -e "当前文件总数: ${CURRENT_COUNT}"
echo -e "${RED}将要删除: ${DELETE_COUNT} 个文件${NC}"
echo -e "${YELLOW}将要移动: ${MOVE_COUNT} 个文件${NC}"
echo -e "${GREEN}将要整理: ${DOC_COUNT} 个文档${NC}"

TOTAL_CLEANUP=$((DELETE_COUNT + MOVE_COUNT + DOC_COUNT))
echo -e "\n总计将处理: ${TOTAL_CLEANUP} 个文件"
echo -e "预计清理后根目录项目数: $((CURRENT_COUNT - TOTAL_CLEANUP))"

# ========================================
# 空间统计
# ========================================
if [ ${DELETE_COUNT} -gt 0 ]; then
    echo -e "\n${RED}删除文件将释放空间:${NC}"
    total_size=0
    for f in "${DELETE_FILES[@]}"; do
        if [ -f "$f" ]; then
            size=$(du -k "$f" | cut -f1)
            total_size=$((total_size + size))
        fi
    done
    echo "  约 ${total_size} KB"
fi

# ========================================
# 保留的核心文件
# ========================================
echo -e "\n${BLUE}⚪ 将保留在根目录的核心文件和目录：${NC}"
echo "----------------------------------------"
echo "配置文件: .gitignore, .flake8, CLAUDE.md, README.md, Makefile, requirements.txt"
echo "核心目录: agents/, api/, artifacts/, config/, docs/, frontend/"
echo "         infrastructure/, lambdas/, lambda-layers/, scripts/"
echo "         security/, tests/, test-data/, test-results/"
echo "隐藏目录: .git/, .github/, .venv/, .mypy_cache/, .spec-workflow/, .layer-cache/, .claude/"

echo -e "\n=========================================="
echo -e "${BLUE}📝 执行清理的选项：${NC}"
echo "----------------------------------------"
echo "1. ${GREEN}bash scripts/cleanup_root_directory.sh${NC}"
echo "   - 执行实际清理操作"
echo ""
echo "2. ${YELLOW}bash scripts/cleanup_root_directory.sh --dry-run${NC}"
echo "   - 模拟运行，不实际删除或移动文件"
echo ""
echo "3. ${RED}不执行清理${NC}"
echo "   - 保持现状"
echo "=========================================="