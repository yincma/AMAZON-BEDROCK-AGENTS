#!/bin/bash
# 便捷脚本：执行Lambda部署
# 使用方法: ./deploy_lambdas.sh [参数]

# 确保从项目根目录执行
cd "$(dirname "$0")"
python scripts/deployment/deploy_lambda_functions.py "$@"