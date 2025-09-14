"""
配置文件 - AI-PPT-Assistant项目的全局配置
"""
import os

# AWS配置
S3_BUCKET = os.environ.get('S3_BUCKET', 'ai-ppt-presentations-dev')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Bedrock配置
BEDROCK_MODEL_ID = "anthropic.claude-sonnet-4-20250514-v1:0"
MAX_TOKENS = 20000
TEMPERATURE = 0.7

# 业务配置
DEFAULT_PAGE_COUNT = 5
MIN_PAGE_COUNT = 3
MAX_PAGE_COUNT = 20  # 测试中支持到20页

# 内容验证配置
MIN_BULLET_LENGTH = 10  # 最小要点长度（调整为10以适应中文）
MAX_BULLET_LENGTH = 200  # 最大要点长度
MAX_TITLE_LENGTH = 100  # 最大标题长度