#!/usr/bin/env python3
"""准备第二批文件上传"""

import json
import os

# 第二批重要文件列表
batch2_files = [
    '.gitignore',
    'Makefile', 
    'deploy.sh',
    'requirements.txt',
    'CONTRIBUTING.md',
    'TROUBLESHOOTING.md',
    'api/openapi.yaml',
    'frontend/package.json',
    'infrastructure/variables.tf',
    'config/default.yaml'
]

files_to_upload = []

for file_path in batch2_files:
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                files_to_upload.append({
                    'path': file_path,
                    'content': content
                })
                print(f"已准备: {file_path} ({len(content)} 字符)")
        except Exception as e:
            print(f"跳过 {file_path}: {e}")

# 输出准备好的文件内容
print(f"\n共准备 {len(files_to_upload)} 个文件")
print("\n文件内容预览:")

for file in files_to_upload:
    print(f"\n{'='*50}")
    print(f"文件: {file['path']}")
    print(f"大小: {len(file['content'])} 字符")
    if len(file['content']) < 500:
        print(f"内容:\n{file['content']}")
    else:
        print(f"内容预览:\n{file['content'][:300]}...")

# 保存为 JSON
with open('batch2_files.json', 'w', encoding='utf-8') as f:
    json.dump(files_to_upload, f, ensure_ascii=False, indent=2)
    print(f"\n\n文件已保存到 batch2_files.json")