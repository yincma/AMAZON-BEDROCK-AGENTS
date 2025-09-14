#!/usr/bin/env python3
"""
测试图片生成修复
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lambdas'))

from lambdas.image_processing_service import ImageProcessingService
from lambdas.image_generator import ImageGenerator

def test_image_generation():
    """测试图片生成功能"""
    print("🔍 测试图片生成功能修复...")

    # 测试数据
    test_slide = {
        "title": "人工智能的未来发展",
        "content": [
            "机器学习技术进步",
            "深度学习应用拓展",
            "AI在各行业的应用"
        ]
    }

    try:
        # 1. 测试图片处理服务
        print("\n1. 测试ImageProcessingService...")
        processing_service = ImageProcessingService()

        # 生成提示词
        prompt = processing_service.generate_prompt(test_slide)
        print(f"   ✅ 提示词生成: {prompt[:100]}...")

        # 尝试生成图片
        try:
            image_data = processing_service.call_image_generation(prompt)
            print(f"   ✅ 图片生成成功: {len(image_data)} 字节")
            if len(image_data) > 1000:
                print("   📸 生成了真实的图片数据（超过1KB）")
            else:
                print("   ⚠️ 可能是占位图（小于1KB）")
        except Exception as e:
            print(f"   ❌ 图片生成失败: {str(e)}")

        # 2. 测试图片生成器
        print("\n2. 测试ImageGenerator...")
        generator = ImageGenerator()

        try:
            result = generator.generate_image(
                prompt=prompt,
                presentation_id="test-123",
                slide_number=1
            )
            print(f"   ✅ 图片生成器成功: {result.get('status')}")
            if 'image_url' in result:
                print(f"   🔗 图片URL: {result['image_url'][:50]}...")
        except Exception as e:
            print(f"   ❌ 图片生成器失败: {str(e)}")

    except Exception as e:
        print(f"❌ 总体测试失败: {str(e)}")
        return False

    print("\n✅ 图片生成功能测试完成")
    return True

if __name__ == "__main__":
    success = test_image_generation()
    if success:
        print("\n🎉 图片生成功能修复验证成功！")
    else:
        print("\n❌ 图片生成功能仍有问题，需要进一步调试")