#!/usr/bin/env python3
"""收集所有项目文件用于 GitHub 上传"""

import os
import json
from pathlib import Path

def should_ignore(file_path):
    """判断文件是否应该被忽略"""
    ignore_patterns = [
        '.git/',
        '.venv/',
        'venv/',
        'venv-py313/',
        '__pycache__/',
        'node_modules/',
        '.pyc',
        '.pyo',
        '.DS_Store',
        '.terraform/',
        'terraform.tfstate',
        '.tfstate',
        '.zip',
        'build/',
        'dist/',
        '.pytest_cache/',
        '.coverage',
        'htmlcov/',
        '.env',
        '.env.local',
        '*.log',
        'deployment_*.log',
        'lambda-layers/',
        '.spec-workflow/',
    ]
    
    str_path = str(file_path)
    for pattern in ignore_patterns:
        if pattern in str_path:
            return True
    
    # 忽略二进制文件和大文件
    if file_path.is_file():
        try:
            # 跳过大于 1MB 的文件
            if file_path.stat().st_size > 1024 * 1024:
                return True
            
            # 检查是否为文本文件
            with open(file_path, 'rb') as f:
                chunk = f.read(512)
                if b'\0' in chunk:  # 二进制文件
                    return True
        except:
            return True
    
    return False

def collect_files(root_dir='.'):
    """收集所有需要上传的文件"""
    files = []
    root_path = Path(root_dir).resolve()
    
    for file_path in root_path.rglob('*'):
        if file_path.is_file() and not should_ignore(file_path):
            relative_path = file_path.relative_to(root_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    files.append({
                        'path': str(relative_path),
                        'content': content
                    })
                    print(f"已收集: {relative_path}")
            except Exception as e:
                print(f"跳过文件 {relative_path}: {e}")
    
    return files

def save_files_json(files, output_file='files_to_upload.json'):
    """保存文件列表到 JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(files, f, ensure_ascii=False, indent=2)
    print(f"\n已保存 {len(files)} 个文件到 {output_file}")
    
    # 统计信息
    total_size = sum(len(f['content']) for f in files)
    print(f"总大小: {total_size / 1024 / 1024:.2f} MB")
    
    # 按扩展名分类
    extensions = {}
    for f in files:
        ext = Path(f['path']).suffix or 'no_extension'
        extensions[ext] = extensions.get(ext, 0) + 1
    
    print("\n文件类型分布:")
    for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ext}: {count} 个文件")

if __name__ == '__main__':
    print("开始收集项目文件...")
    files = collect_files()
    
    if files:
        save_files_json(files)
        
        # 如果文件太多，分批保存
        if len(files) > 100:
            batch_size = 50
            for i in range(0, len(files), batch_size):
                batch = files[i:i+batch_size]
                batch_file = f'files_batch_{i//batch_size + 1}.json'
                save_files_json(batch, batch_file)
    else:
        print("没有找到需要上传的文件")