#!/bin/bash
# 便捷脚本：验证部署
# 使用方法: ./verify_deploy.sh [参数]

# 确保从项目根目录执行
cd "$(dirname "$0")"
python scripts/deployment/verify_deployment.py "$@"