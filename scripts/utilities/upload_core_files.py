#!/usr/bin/env python3
"""直接生成用于 GitHub MCP 的核心文件列表"""

import os

# 生成一个精简的文件列表，只包含最核心的文件
core_files = []

# .gitignore
if os.path.exists('.gitignore'):
    with open('.gitignore', 'r') as f:
        gitignore_content = f.read()
        core_files.append({
            'path': '.gitignore',
            'content': gitignore_content
        })

# 问题管理表
if os.path.exists('问题管理表.md'):
    with open('问题管理表.md', 'r', encoding='utf-8') as f:
        issue_content = f.read()
        core_files.append({
            'path': '问题管理表.md', 
            'content': issue_content
        })

# API 测试报告
if os.path.exists('API_TEST_REPORT.md'):
    with open('API_TEST_REPORT.md', 'r') as f:
        api_report = f.read()
        core_files.append({
            'path': 'API_TEST_REPORT.md',
            'content': api_report
        })

print(f"准备了 {len(core_files)} 个文件")
print("文件列表：")
for f in core_files:
    print(f"- {f['path']} ({len(f['content'])} 字符)")

# 输出可直接用于 MCP 的 JSON
import json
print("\n可用于 GitHub MCP push_files 的文件数组：")
print(json.dumps(core_files, ensure_ascii=False))