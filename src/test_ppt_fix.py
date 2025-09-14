#!/usr/bin/env python3
"""
测试PPT生成功能是否正常
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 模拟AWS服务
class MockBedrockClient:
    def invoke_model(self, **kwargs):
        import json
        # 返回符合原始格式的响应
        if "大纲" in json.loads(kwargs['body'])['messages'][0]['content']:
            response_text = json.dumps({
                "title": "测试主题",
                "slides": [
                    {"slide_number": 1, "title": "标题页", "content": ["介绍", "概述", "目标"]},
                    {"slide_number": 2, "title": "第二页", "content": ["要点1", "要点2", "要点3"]},
                    {"slide_number": 3, "title": "第三页", "content": ["内容1", "内容2", "内容3"]},
                    {"slide_number": 4, "title": "第四页", "content": ["分析1", "分析2", "分析3"]},
                    {"slide_number": 5, "title": "总结", "content": ["回顾", "建议", "Q&A"]}
                ],
                "metadata": {
                    "total_slides": 5,
                    "estimated_duration": "10-15分钟",
                    "created_at": "2024-01-14"
                }
            })
        else:
            response_text = json.dumps({
                "slide_number": 1,
                "title": "测试标题",
                "bullet_points": ["要点1", "要点2", "要点3"],
                "speaker_notes": "这是演讲备注"
            })

        return {
            'body': type('obj', (object,), {
                'read': lambda: json.dumps({
                    'content': [{'text': response_text}]
                }).encode()
            })()
        }

def test_ppt_generation():
    """测试PPT生成功能"""
    from content_generator import ContentGenerator

    # 使用模拟客户端
    generator = ContentGenerator(bedrock_client=MockBedrockClient())

    print("=" * 50)
    print("测试PPT生成功能")
    print("=" * 50)

    # 1. 测试生成大纲
    print("\n1. 测试生成大纲...")
    try:
        outline = generator.generate_outline('企业数字化转型战略', 5)
        print("✓ 大纲生成成功")
        print(f"  - 标题: {outline.get('title')}")
        print(f"  - 幻灯片数: {len(outline.get('slides', []))}")
        print(f"  - 元数据: {outline.get('metadata', {}).get('total_slides')} 页")
    except Exception as e:
        print(f"✗ 大纲生成失败: {e}")
        return False

    # 2. 测试生成内容
    print("\n2. 测试生成幻灯片内容...")
    try:
        slides = generator.generate_slide_content(outline, include_speaker_notes=True)
        print("✓ 内容生成成功")
        print(f"  - 生成了 {len(slides)} 页幻灯片")

        # 验证每页的结构
        for i, slide in enumerate(slides[:2], 1):  # 只检查前两页
            print(f"\n  第{i}页验证:")
            print(f"    - 标题: {slide.get('title', '无')}")
            print(f"    - 要点数: {len(slide.get('bullet_points', []))}")
            print(f"    - 有演讲备注: {'是' if slide.get('speaker_notes') else '否'}")
    except Exception as e:
        print(f"✗ 内容生成失败: {e}")
        return False

    print("\n" + "=" * 50)
    print("✅ 所有测试通过 - PPT生成功能正常")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = test_ppt_generation()
    sys.exit(0 if success else 1)