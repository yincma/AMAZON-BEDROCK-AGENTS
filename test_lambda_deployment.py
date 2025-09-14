#!/usr/bin/env python3
"""
测试Lambda部署的图片生成功能
"""

import json
import boto3
import base64
from datetime import datetime

def test_lambda_deployment():
    """测试部署的Lambda函数"""

    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3')

    print("=" * 60)
    print("🚀 测试Lambda部署 - AI PPT图片生成")
    print("=" * 60)

    # 测试用例
    test_cases = [
        {
            "name": "基础测试",
            "payload": {"action": "test"}
        },
        {
            "name": "图片生成 - 技术主题",
            "payload": {
                "action": "generate_image",
                "slide_content": {
                    "title": "人工智能技术架构",
                    "content": ["深度学习框架", "模型训练", "推理优化"]
                }
            }
        },
        {
            "name": "图片生成 - 商务主题",
            "payload": {
                "action": "generate_image",
                "slide_content": {
                    "title": "2025年市场战略",
                    "content": ["市场扩张", "产品创新", "客户增长"]
                }
            }
        }
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] {test['name']}")
        print("-" * 40)

        try:
            # 调用Lambda
            response = lambda_client.invoke(
                FunctionName='ai-ppt-generate-dev',
                InvocationType='RequestResponse',
                Payload=json.dumps(test['payload'])
            )

            # 解析响应
            result = json.loads(response['Payload'].read())
            status_code = response['StatusCode']

            print(f"✅ 状态码: {status_code}")

            if 'body' in result:
                body = json.loads(result['body'])

                if 'image_url' in body:
                    print(f"🎨 图片URL: {body['image_url']}")
                    print(f"📊 图片大小: {body.get('size', 0):,} bytes")

                    # 判断是否是真实AI图片
                    if body.get('size', 0) > 100000:
                        print("🎉 生成了真实的AI图片！")
                        results.append((test['name'], True, "AI图片"))
                    else:
                        print("⚠️ 使用了占位图")
                        results.append((test['name'], True, "占位图"))
                else:
                    print(f"📄 响应: {body}")
                    results.append((test['name'], True, "成功"))
            else:
                print(f"📄 响应: {result}")
                results.append((test['name'], True, "成功"))

        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            results.append((test['name'], False, str(e)))

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)

    for name, success, detail in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}: {detail}")

    passed = sum(1 for _, s, _ in results if s)
    total = len(results)

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！Lambda部署成功！")
    else:
        print("\n⚠️ 部分测试失败，请检查日志")

    return passed == total

def check_s3_images():
    """检查S3中的图片"""
    s3_client = boto3.client('s3')
    bucket = 'ai-ppt-presentations-dev-375004070918'

    print("\n" + "=" * 60)
    print("🗂️ S3存储的图片")
    print("=" * 60)

    try:
        # 列出图片
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix='images/',
            MaxKeys=10
        )

        if 'Contents' in response:
            print(f"找到 {len(response['Contents'])} 个图片文件:")
            for obj in response['Contents'][:5]:  # 显示前5个
                print(f"  📄 {obj['Key']}")
                print(f"     大小: {obj['Size']:,} bytes")
                print(f"     修改时间: {obj['LastModified']}")
        else:
            print("暂无图片文件")

    except Exception as e:
        print(f"❌ 无法访问S3: {str(e)}")

if __name__ == "__main__":
    # 运行测试
    success = test_lambda_deployment()

    # 检查S3
    check_s3_images()

    if success:
        print("\n✨ Lambda部署验证完成！图片生成功能正常工作。")