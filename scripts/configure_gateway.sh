#!/bin/bash
# 便捷脚本：配置API Gateway
# 使用方法: ./configure_gateway.sh [参数]

# 确保从项目根目录执行
cd "$(dirname "$0")"
python scripts/deployment/configure_api_gateway.py "$@"