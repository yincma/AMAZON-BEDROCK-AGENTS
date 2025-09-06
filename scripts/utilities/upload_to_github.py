#!/usr/bin/env python3
"""使用 GitHub MCP API 上传文件"""

import json
import os
from pathlib import Path

def prepare_files_for_upload(max_files=10):
    """准备一小批文件用于上传"""
    files_to_upload = []
    
    # 选择最重要的项目文件
    important_files = [
        'README.md',
        'Makefile',
        '.gitignore',
        'requirements.txt',
        'deploy.sh',
        'api/openapi.yaml',
        'frontend/package.json',
        'infrastructure/main.tf',
        'lambdas/api/generate_presentation.py',
        'agents/orchestrator/agent_config.json'
    ]
    
    for file_path in important_files[:max_files]:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    files_to_upload.append({
                        'path': file_path,
                        'content': content
                    })
                    print(f"准备上传: {file_path}")
            except Exception as e:
                print(f"跳过文件 {file_path}: {e}")
    
    return files_to_upload

def main():
    # 准备文件
    files = prepare_files_for_upload()
    
    # 保存为 JSON 供 MCP 使用
    with open('github_upload_batch.json', 'w', encoding='utf-8') as f:
        json.dump(files, f, ensure_ascii=False, indent=2)
    
    print(f"\n已准备 {len(files)} 个文件")
    print("文件已保存到 github_upload_batch.json")
    
    # 输出 MCP 命令提示
    print("\n现在可以使用 GitHub MCP push_files 命令上传这些文件")
    print("owner: yincma")
    print("repo: AMAZON-BEDROCK-AGENTS")
    print("branch: main 或 dev")

if __name__ == '__main__':
    main()