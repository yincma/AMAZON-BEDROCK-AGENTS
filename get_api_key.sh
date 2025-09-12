#!/bin/bash
# 从SSM安全获取API密钥

aws ssm get-parameter \
  --name "/ai-ppt-assistant/dev/api-key" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text \
  --region us-east-1
