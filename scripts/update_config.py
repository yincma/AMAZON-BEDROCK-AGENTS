#!/usr/bin/env python3
"""
API Configuration Updater
AWS Expert: 更安全可靠的配置文件更新脚本
"""
import sys
import re
import argparse
from pathlib import Path


def update_python_config(file_path: Path, api_url: str, api_key: str) -> bool:
    """更新Python文件中的API配置"""
    if not file_path.exists():
        print(f"⚠️ 文件不存在，跳过: {file_path.name}")
        return False
    
    print(f"📝 更新文件: {file_path.name}")
    
    # 读取原文件
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return False
    
    # 创建备份
    backup_path = file_path.with_suffix(f'{file_path.suffix}.backup')
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        print(f"⚠️ 创建备份失败: {e}")
    
    # 更新API_BASE_URL
    updated = False
    if 'API_BASE_URL' in content:
        # 匹配 API_BASE_URL = "..." 或 API_BASE_URL="..."
        pattern = r'API_BASE_URL\s*=\s*["\'][^"\']*["\']'
        replacement = f'API_BASE_URL = "{api_url}"'
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            updated = True
            print(f"  ✓ 已更新 API_BASE_URL ({count} 处)")
    
    # 更新API_KEY
    if 'API_KEY' in content:
        # 匹配 API_KEY = "..." 或 API_KEY="..."
        pattern = r'API_KEY\s*=\s*["\'][^"\']*["\']'
        replacement = f'API_KEY = "{api_key}"'
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            updated = True
            print(f"  ✓ 已更新 API_KEY ({count} 处)")
    
    # 写入更新后的内容
    if updated:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✅ 文件更新成功")
            return True
        except Exception as e:
            print(f"❌ 写入文件失败: {e}")
            return False
    else:
        print(f"  ℹ️ 无需更新")
        return True


def main():
    parser = argparse.ArgumentParser(description='Update API configuration in Python files')
    parser.add_argument('--api-url', required=True, help='API Gateway URL')
    parser.add_argument('--api-key', required=True, help='API Key')
    parser.add_argument('files', nargs='+', help='Python files to update')
    
    args = parser.parse_args()
    
    success_count = 0
    for file_path_str in args.files:
        file_path = Path(file_path_str)
        if update_python_config(file_path, args.api_url, args.api_key):
            success_count += 1
    
    print(f"\n📊 更新结果: {success_count}/{len(args.files)} 个文件成功更新")
    return 0 if success_count == len(args.files) else 1


if __name__ == '__main__':
    sys.exit(main())