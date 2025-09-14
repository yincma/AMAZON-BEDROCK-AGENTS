#!/usr/bin/env python3
"""
本地测试Lambda处理器
"""
import json
import sys
import os
from unittest.mock import Mock

# 添加src目录到Python路径
sys.path.insert(0, os.path.dirname(__file__))

def test_lambda_handler():
    """测试Lambda处理器"""
    print("=" * 60)
    print("测试Lambda处理器")
    print("=" * 60)

    # 导入处理器
    from lambdas.generate_ppt import handler

    # 创建测试事件
    test_event = {
        'body': json.dumps({
            'topic': '人工智能的未来',
            'page_count': 5
        })
    }

    # Mock Bedrock和S3
    import src.content_generator as content_gen_module

    # Mock Bedrock客户端
    mock_bedrock = Mock()
    mock_response = {
        "body": Mock(),
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }

    # 创建测试大纲
    test_outline = {
        "title": "人工智能的未来",
        "slides": [
            {"slide_number": 1, "title": "引言", "content": ["AI概述", "发展历程", "重要性"]},
            {"slide_number": 2, "title": "核心技术", "content": ["机器学习", "深度学习", "自然语言处理"]},
            {"slide_number": 3, "title": "应用领域", "content": ["医疗", "金融", "教育"]},
            {"slide_number": 4, "title": "挑战与机遇", "content": ["技术挑战", "伦理问题", "发展机会"]},
            {"slide_number": 5, "title": "总结", "content": ["关键要点", "未来展望", "行动建议"]}
        ],
        "metadata": {"total_slides": 5}
    }

    # 创建测试内容
    test_content = {
        "slide_number": 1,
        "title": "测试标题",
        "bullet_points": [
            "这是第一个要点，包含足够的内容",
            "这是第二个要点，同样有充实的信息",
            "这是第三个要点，内容也很完整"
        ],
        "speaker_notes": "这是演讲者备注，提供演讲时的提示和补充信息"
    }

    # 设置mock响应
    responses = []
    # 第一次调用返回大纲
    response1 = {"body": Mock(), "ResponseMetadata": {"HTTPStatusCode": 200}}
    response1["body"].read.return_value = json.dumps({
        "completion": json.dumps(test_outline)
    }).encode()
    responses.append(response1)

    # 后续调用返回内容
    for _ in range(5):  # 5个幻灯片
        response = {"body": Mock(), "ResponseMetadata": {"HTTPStatusCode": 200}}
        response["body"].read.return_value = json.dumps({
            "completion": json.dumps(test_content)
        }).encode()
        responses.append(response)

    mock_bedrock.invoke_model.side_effect = responses

    # Mock S3客户端
    mock_s3 = Mock()

    # 替换boto3客户端
    original_boto3 = content_gen_module.boto3
    mock_boto3 = Mock()
    mock_boto3.client.side_effect = lambda service, **kwargs: mock_bedrock if service == 'bedrock-runtime' else mock_s3
    content_gen_module.boto3 = mock_boto3

    # 调用处理器
    print("\n调用Lambda处理器...")
    try:
        result = handler(test_event, {})

        # 解析响应
        response_body = json.loads(result['body'])

        # 打印结果
        print(f"\n状态码: {result['statusCode']}")
        print(f"响应内容:")
        print(json.dumps(response_body, indent=2, ensure_ascii=False))

        # 验证结果
        assert result['statusCode'] == 200, f"期望状态码200，实际: {result['statusCode']}"
        assert 'presentation_id' in response_body, "响应中缺少presentation_id"
        assert response_body['status'] == 'completed', f"期望状态completed，实际: {response_body['status']}"

        print("\n✅ Lambda处理器测试通过!")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # 恢复原始boto3
        content_gen_module.boto3 = original_boto3

if __name__ == "__main__":
    test_lambda_handler()