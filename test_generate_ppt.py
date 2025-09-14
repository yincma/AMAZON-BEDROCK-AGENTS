#!/usr/bin/env python3
"""
测试生成一个完整的PPT
"""
import sys
import os
import json
import boto3
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_generate_ppt():
    """测试生成PPT的完整流程"""
    from src.content_generator import ContentGenerator
    from src.ppt_compiler import PPTCompiler

    print("=" * 60)
    print("PPT生成测试")
    print("=" * 60)

    # 配置
    topic = "人工智能在企业数字化转型中的应用"
    page_count = 6
    presentation_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"\n主题: {topic}")
    print(f"页数: {page_count}")
    print(f"演示文稿ID: {presentation_id}")
    print("-" * 60)

    try:
        # 1. 初始化生成器
        print("\n1. 初始化内容生成器...")
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        generator = ContentGenerator(bedrock_client=bedrock_client)
        print("   ✓ 生成器初始化成功")

        # 2. 生成大纲
        print("\n2. 生成PPT大纲...")
        outline = generator.generate_outline(topic, page_count)
        print("   ✓ 大纲生成成功")
        print(f"   - 标题: {outline.get('title')}")
        print(f"   - 幻灯片数: {len(outline.get('slides', []))}")

        # 打印大纲结构
        print("\n   大纲结构:")
        for slide in outline.get('slides', []):
            print(f"   第{slide['slide_number']}页: {slide['title']}")

        # 3. 生成详细内容
        print("\n3. 生成幻灯片详细内容...")
        slides = generator.generate_slide_content(outline, include_speaker_notes=True)
        print(f"   ✓ 内容生成成功 - 共{len(slides)}页")

        # 展示前两页内容
        print("\n   内容预览:")
        for slide in slides[:2]:
            print(f"\n   第{slide['slide_number']}页: {slide['title']}")
            print("   要点:")
            for i, point in enumerate(slide.get('bullet_points', []), 1):
                print(f"     {i}. {point}")
            if slide.get('speaker_notes'):
                print(f"   演讲备注: {slide['speaker_notes'][:100]}...")

        # 4. 编译成PPTX文件
        print("\n4. 编译成PPTX文件...")
        compiler = PPTCompiler()

        # 准备内容数据
        content_data = {
            "title": outline.get("title"),
            "slides": slides,
            "metadata": outline.get("metadata", {})
        }

        # 生成PPTX
        output_path = f"demo_presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
        pptx_path = compiler.create_presentation(content_data, output_path)

        if os.path.exists(pptx_path):
            file_size = os.path.getsize(pptx_path) / 1024  # KB
            print(f"   ✓ PPTX文件生成成功")
            print(f"   - 文件路径: {pptx_path}")
            print(f"   - 文件大小: {file_size:.2f} KB")
        else:
            print("   ✗ PPTX文件生成失败")
            return False

        print("\n" + "=" * 60)
        print("✅ PPT生成测试成功！")
        print(f"📁 生成的文件: {pptx_path}")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 检查AWS凭证
    try:
        sts = boto3.client('sts', region_name='us-east-1')
        caller = sts.get_caller_identity()
        print(f"AWS账户: {caller['Account']}")
        print(f"用户ARN: {caller['Arn']}\n")
    except Exception as e:
        print(f"⚠️  AWS凭证配置错误: {e}")
        print("请确保已配置AWS凭证")
        sys.exit(1)

    # 运行测试
    success = test_generate_ppt()
    sys.exit(0 if success else 1)