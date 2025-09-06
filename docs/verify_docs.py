#!/usr/bin/env python3
"""
验证文档生成是否成功的脚本
"""

import os
from pathlib import Path


def verify_documentation():
    """验证文档生成是否成功"""
    
    docs_build_path = Path("docs/build/html")
    
    # 检查基本文件存在
    required_files = [
        "index.html",
        "genindex.html", 
        "py-modindex.html",
        "search.html"
    ]
    
    print("🔍 检查文档基本文件...")
    for file in required_files:
        file_path = docs_build_path / file
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✅ {file} ({size:,} bytes)")
        else:
            print(f"❌ {file} - 文件不存在")
    
    # 检查API文档目录
    api_path = docs_build_path / "api"
    if api_path.exists():
        api_files = list(api_path.glob("*.html"))
        print(f"\n📚 API文档: {len(api_files)} 个文件")
        for file in sorted(api_files)[:5]:  # 显示前5个
            size = file.stat().st_size
            print(f"   📄 {file.name} ({size:,} bytes)")
        if len(api_files) > 5:
            print(f"   ... 以及其他 {len(api_files) - 5} 个文件")
    else:
        print("❌ API文档目录不存在")
    
    # 检查指南文档
    guides_path = docs_build_path / "guides"
    if guides_path.exists():
        guide_files = list(guides_path.glob("*.html"))
        print(f"\n📖 指南文档: {len(guide_files)} 个文件")
        for file in sorted(guide_files):
            size = file.stat().st_size
            print(f"   📄 {file.name} ({size:,} bytes)")
    else:
        print("❌ 指南文档目录不存在")
    
    # 检查现有文档
    existing_path = docs_build_path / "existing"
    if existing_path.exists():
        existing_files = list(existing_path.glob("*.html"))
        print(f"\n📋 现有文档: {len(existing_files)} 个文件")
        for file in sorted(existing_files):
            size = file.stat().st_size
            print(f"   📄 {file.name} ({size:,} bytes)")
    
    # 计算总体统计
    total_html_files = len(list(docs_build_path.rglob("*.html")))
    total_size = sum(f.stat().st_size for f in docs_build_path.rglob("*") if f.is_file())
    
    print(f"\n📊 文档统计:")
    print(f"   总HTML文件数: {total_html_files}")
    print(f"   总大小: {total_size / (1024*1024):.2f} MB")
    
    # 检查文档是否可以在浏览器中打开
    index_file = docs_build_path / "index.html"
    if index_file.exists():
        abs_path = index_file.resolve()
        print(f"\n🌐 文档可通过以下路径访问:")
        print(f"   file://{abs_path}")
    
    print(f"\n✅ 文档验证完成!")
    return True


if __name__ == "__main__":
    verify_documentation()