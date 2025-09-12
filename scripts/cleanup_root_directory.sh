#!/bin/bash

# 根目录清理脚本
# 作者：Claude
# 日期：2025-09-12
# 描述：按优先级清理项目根目录文件

set -e

echo "=========================================="
echo "🧹 开始清理根目录文件"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# 创建必要的目录
echo -e "${GREEN}📁 创建必要的目录...${NC}"
mkdir -p docs/reports/archive
mkdir -p docs/reports/latest
mkdir -p scripts/tools
mkdir -p tests/validation

# 统计清理前的文件数量
BEFORE_COUNT=$(ls -1 | wc -l)
echo -e "清理前根目录文件数量: ${BEFORE_COUNT}"

# ========================================
# 第一优先级：删除临时文件和过期报告
# ========================================
echo -e "\n${RED}🔴 第一优先级：删除临时文件和过期报告${NC}"

# 删除旧的API测试报告（保留最新的3个）
echo "删除旧的API测试报告..."
ls -t api_test_report_*.json 2>/dev/null | tail -n +4 | xargs -r rm -f

# 删除其他带时间戳的报告（保留最新的）
echo "删除旧的agent配置报告..."
ls -t agent_config_fix_report_*.json 2>/dev/null | tail -n +2 | xargs -r rm -f

echo "删除旧的config center报告..."
ls -t config_center_report_*.json 2>/dev/null | tail -n +2 | xargs -r rm -f

echo "删除旧的部署验证报告..."
ls -t deployment_validation_report_*.json 2>/dev/null | tail -n +2 | xargs -r rm -f
rm -f deployment_validation_20*.json

echo "删除旧的回归测试报告..."
ls -t regression_test_report_*.json 2>/dev/null | tail -n +2 | xargs -r rm -f

# 删除备份文件
echo "删除备份文件..."
rm -f *.backup
rm -f Makefile.backup.*
rm -f comprehensive_backend_test.py.backup*
rm -f system_health_check.py.backup
rm -f test_all_backend_apis.py.backup

# 删除日志文件
echo "删除临时日志文件..."
rm -f deploy_output.log
rm -f deployment_log_*.log
rm -f regression_test_*.log
rm -f destroy_output.log
rm -f test_output_comparison.sh

# 删除响应示例文件
echo "删除响应示例文件..."
rm -f response-claude*.json
rm -f presentation_response.json

# 删除旧的测试结果
echo "删除旧的测试结果..."
rm -f api_test_results.json
rm -f pre_deploy_check_*.txt

# 删除其他临时文件
rm -f terraform.tfstate
rm -f presentation_status.zip
rm -f dynamodb_backup_*.json
rm -f migration_report_*.json

# ========================================
# 第二优先级：移动测试和工具脚本
# ========================================
echo -e "\n${YELLOW}🟡 第二优先级：移动测试和工具脚本${NC}"

# 移动测试脚本到 tests/validation/
echo "移动测试脚本..."
[ -f test_backend_apis.py ] && mv test_backend_apis.py tests/validation/
[ -f test_all_backend_apis.py ] && mv test_all_backend_apis.py tests/validation/
[ -f test_all_apis.py ] && mv test_all_apis.py tests/validation/
[ -f test_api_comprehensive.py ] && mv test_api_comprehensive.py tests/validation/
[ -f comprehensive_backend_test.py ] && mv comprehensive_backend_test.py tests/validation/
[ -f comprehensive_api_test.py ] && mv comprehensive_api_test.py tests/validation/
[ -f comprehensive_validation.py ] && mv comprehensive_validation.py tests/validation/
[ -f regression_test.py ] && mv regression_test.py tests/validation/
[ -f final_validation.py ] && mv final_validation.py tests/validation/
[ -f deployment_validation.py ] && mv deployment_validation.py tests/validation/
[ -f post_deploy_validation.py ] && mv post_deploy_validation.py tests/validation/
[ -f system_health_check.py ] && mv system_health_check.py tests/validation/

# 移动工具脚本到 scripts/tools/
echo "移动工具脚本..."
[ -f fix_data_issue.py ] && mv fix_data_issue.py scripts/tools/
[ -f lambda_config_helper.py ] && mv lambda_config_helper.py scripts/tools/
[ -f get_api_key.sh ] && mv get_api_key.sh scripts/tools/

# 移动部署相关脚本
echo "移动部署脚本..."
[ -f deploy ] && mv deploy scripts/
[ -f deploy.sh ] && mv deploy.sh scripts/
[ -f deploy_fixes.sh ] && mv deploy_fixes.sh scripts/
[ -f deploy_lambdas.sh ] && mv deploy_lambdas.sh scripts/
[ -f configure_gateway.sh ] && mv configure_gateway.sh scripts/
[ -f verify_deploy.sh ] && mv verify_deploy.sh scripts/
[ -f delete_cloudfront_distributions.sh ] && mv delete_cloudfront_distributions.sh scripts/
[ -f delete_remaining_distributions.sh ] && mv delete_remaining_distributions.sh scripts/

# ========================================
# 第三优先级：整理文档和报告
# ========================================
echo -e "\n${GREEN}🟢 第三优先级：整理文档和报告${NC}"

# 移动中文文档
echo "移动文档到 docs/reports/..."
[ -f 修复成功报告.md ] && mv 修复成功报告.md docs/reports/
[ -f 工作记录.md ] && mv 工作记录.md docs/reports/
[ -f 覆盖问题分析报告.md ] && mv 覆盖问题分析报告.md docs/reports/

# 移动英文文档
[ -f API_TEST_REPORT.md ] && mv API_TEST_REPORT.md docs/reports/
[ -f deployment-optimization-guide.md ] && mv deployment-optimization-guide.md docs/
[ -f DEPLOYMENT_GUIDE.md ] && mv DEPLOYMENT_GUIDE.md docs/
[ -f deployment_regression_report.md ] && mv deployment_regression_report.md docs/reports/

# 移动最新的JSON报告到 latest 目录
echo "保存最新的JSON报告..."
if ls api_test_report_*.json 1> /dev/null 2>&1; then
    LATEST_API_REPORT=$(ls -t api_test_report_*.json | head -1)
    [ -f "$LATEST_API_REPORT" ] && mv "$LATEST_API_REPORT" docs/reports/latest/
fi

for pattern in "api_config_info.json" "api_gateway_config.json" "backend_test_report.json" \
               "comprehensive_validation_report.json" "deployment_validation_report.json" \
               "final_validation_report.json" "system_health_report.json" "test_results_api.json"; do
    [ -f "$pattern" ] && mv "$pattern" docs/reports/latest/
done

# 移动额外的Makefile版本
echo "整理Makefile..."
[ -f Makefile.enhanced ] && mv Makefile.enhanced docs/
[ -f Makefile.optimized ] && mv Makefile.optimized docs/

# ========================================
# 清理完成
# ========================================
AFTER_COUNT=$(ls -1 | wc -l)
CLEANED_COUNT=$((BEFORE_COUNT - AFTER_COUNT))

echo -e "\n=========================================="
echo -e "${GREEN}✅ 清理完成！${NC}"
echo -e "清理前文件数量: ${BEFORE_COUNT}"
echo -e "清理后文件数量: ${AFTER_COUNT}"
echo -e "共清理/移动文件: ${CLEANED_COUNT}"
echo "=========================================="

# 显示当前根目录内容
echo -e "\n📂 当前根目录内容："
ls -la | head -20
echo "..."
echo -e "\n如需查看完整列表，请运行: ls -la"