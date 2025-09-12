#!/bin/bash
echo '❌ 此脚本已被禁用！'
echo '⚠️ 原因：会覆盖安全配置并泄露API密钥'
echo '✅ 请使用SSM Parameter Store管理API密钥'
echo '📖 参考：aws ssm get-parameter --name /ai-ppt-assistant/dev/api-key --with-decryption'
exit 1
