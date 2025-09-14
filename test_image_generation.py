#!/usr/bin/env python3
"""
测试AI-PPT图片生成功能
"""

import json
import boto3
import base64
from datetime import datetime

def test_lambda_image_generation():
    """测试Lambda函数的图片生成"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')

    # 测试数据
    test_payload = {
        "action": "generate_image",
        "slide_content": {
            "title": "人工智能技术趋势",
            "content": [
                "机器学习的发展",
                "深度学习应用",
                "自然语言处理"
            ]
        },
        "presentation_id": f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }

    print("🚀 测试Lambda图片生成功能...")
    print(f"📝 测试内容: {test_payload['slide_content']['title']}")

    try:
        # 调用Lambda函数
        response = lambda_client.invoke(
            FunctionName='ai-ppt-generate-dev',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )

        # 解析响应
        result = json.loads(response['Payload'].read())
        print("\n✅ Lambda调用成功!")
        print(f"📊 响应状态码: {response['StatusCode']}")
        print(f"📄 响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")

        if 'image_url' in result:
            print(f"\n🎨 生成的图片URL: {result['image_url']}")
            return True
        else:
            print("\n⚠️ 未生成图片URL，可能使用了占位图")
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return False

def test_direct_bedrock():
    """直接测试Bedrock图片生成"""
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

    prompt = "A modern business presentation slide about artificial intelligence trends, professional style, clean design, technology theme"

    print("\n🎨 直接测试Bedrock Nova Canvas...")
    print(f"📝 提示词: {prompt}")

    try:
        # 调用Nova Canvas
        response = bedrock_client.invoke_model(
            modelId='amazon.nova-canvas-v1:0',
            body=json.dumps({
                "taskType": "TEXT_IMAGE",
                "textToImageParams": {
                    "text": prompt
                },
                "imageGenerationConfig": {
                    "numberOfImages": 1,
                    "height": 768,
                    "width": 1024,
                    "cfgScale": 8.0
                }
            }),
            contentType='application/json'
        )

        # 解析响应
        result = json.loads(response['body'].read())

        if 'images' in result and len(result['images']) > 0:
            print("\n✅ Bedrock图片生成成功!")

            # 保存图片
            image_data = base64.b64decode(result['images'][0])
            filename = f"test_image_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"

            with open(filename, 'wb') as f:
                f.write(image_data)

            print(f"💾 图片已保存到: {filename}")
            return True
        else:
            print("\n⚠️ Bedrock返回了响应但没有图片")
            return False

    except Exception as e:
        print(f"\n❌ Bedrock测试失败: {str(e)}")
        if "no access" in str(e).lower():
            print("💡 提示: 需要在AWS控制台启用Nova Canvas模型访问权限")
        return False

def test_local_service():
    """测试本地图片生成服务"""
    import sys
    sys.path.append('/Users/umatoratatsu/Documents/AWS/AWS-Handson/ABA/AMAZON-BEDROCK-AGENTS/lambdas')

    try:
        from image_processing_service import ImageProcessingService

        print("\n🔧 测试本地图片处理服务...")

        service = ImageProcessingService()

        # 测试提示词生成
        slide_content = {
            "title": "AI技术革新",
            "content": ["大语言模型", "计算机视觉", "强化学习"]
        }

        prompt = service.generate_prompt(slide_content, "business")
        print(f"✅ 生成的提示词: {prompt}")

        # 测试图片生成（会尝试调用Bedrock或返回占位图）
        image_data = service.call_image_generation(prompt)

        if image_data:
            print(f"✅ 图片生成成功，大小: {len(image_data)} bytes")

            # 保存图片
            filename = f"test_local_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            with open(filename, 'wb') as f:
                f.write(image_data)
            print(f"💾 图片已保存到: {filename}")
            return True
        else:
            print("❌ 未生成图片")
            return False

    except ImportError as e:
        print(f"❌ 导入错误: {str(e)}")
        print("💡 提示: 请确保已安装所需依赖")
        return False
    except Exception as e:
        print(f"❌ 本地测试失败: {str(e)}")
        return False

def main():
    """运行所有测试"""
    print("=" * 60)
    print("🎨 AI-PPT Assistant 图片生成功能测试")
    print("=" * 60)

    results = []

    # 1. 测试本地服务
    print("\n[1/3] 本地服务测试")
    results.append(("本地服务", test_local_service()))

    # 2. 测试Lambda函数
    print("\n[2/3] Lambda函数测试")
    results.append(("Lambda函数", test_lambda_image_generation()))

    # 3. 直接测试Bedrock
    print("\n[3/3] Bedrock直接测试")
    results.append(("Bedrock API", test_direct_bedrock()))

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)

    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")

    total_passed = sum(1 for _, s in results if s)
    print(f"\n总计: {total_passed}/{len(results)} 测试通过")

    if total_passed == len(results):
        print("\n🎉 所有测试通过！图片生成功能正常工作")
    elif total_passed > 0:
        print("\n⚠️ 部分测试通过，请检查失败的组件")
    else:
        print("\n❌ 所有测试失败，请检查配置和权限")

if __name__ == "__main__":
    main()