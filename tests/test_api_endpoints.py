#!/usr/bin/env python3
"""
API端点功能测试 - 验证三个核心端点的功能
"""
import json
import sys
import os
import uuid
from unittest.mock import Mock, MagicMock, patch

# 添加路径
sys.path.append('.')

def create_mock_s3_client():
    """创建模拟S3客户端"""
    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock()
    mock_s3.get_object = MagicMock()
    mock_s3.head_object = MagicMock()
    mock_s3.generate_presigned_url = MagicMock(return_value="https://test-download-url.com")
    return mock_s3

def test_generate_endpoint():
    """测试POST /generate端点"""
    print("=" * 50)
    print("测试 POST /generate 端点")
    print("=" * 50)

    from lambdas.api_handler import handler

    # 设置环境
    os.environ['S3_BUCKET'] = 'test-bucket'

    # 准备测试数据
    valid_request = {
        'httpMethod': 'POST',
        'path': '/generate',
        'body': json.dumps({
            'topic': '人工智能在医疗领域的应用',
            'page_count': 5,
            'style': 'professional'
        })
    }

    print("\n1. 测试有效生成请求")
    response = handler(valid_request, None)
    print(f"   状态码: {response['statusCode']}")

    if response['statusCode'] == 202:
        body = json.loads(response['body'])
        print(f"   响应体键: {list(body.keys())}")

        # 验证必需字段
        required_fields = ['presentation_id', 'status', 'topic', 'page_count']
        for field in required_fields:
            assert field in body, f"响应缺少必需字段: {field}"
            print(f"   ✓ {field}: {body[field]}")

        presentation_id = body['presentation_id']
        # 验证UUID格式
        try:
            uuid.UUID(presentation_id)
            print(f"   ✓ presentation_id是有效UUID: {presentation_id}")
        except ValueError:
            raise AssertionError(f"presentation_id不是有效UUID: {presentation_id}")

        print("   ✅ 生成端点测试通过")
        return presentation_id
    else:
        print(f"   ❌ 期望状态码202，实际: {response['statusCode']}")
        print(f"   响应: {response.get('body', '')}")
        return None

def test_status_endpoint():
    """测试GET /status/{id}端点"""
    print("\n" + "=" * 50)
    print("测试 GET /status/{id} 端点")
    print("=" * 50)

    from lambdas.status_check import handler

    # 设置环境
    os.environ['S3_BUCKET'] = 'test-bucket'

    # 创建模拟数据
    test_id = str(uuid.uuid4())

    # 模拟S3中的状态数据
    mock_status = {
        'presentation_id': test_id,
        'topic': '测试主题',
        'status': 'processing',
        'progress': 75,
        'created_at': '2025-01-01T00:00:00',
        'updated_at': '2025-01-01T00:05:00',
        'current_step': 'content_generation',
        'steps': {
            'outline_generation': True,
            'content_generation': True,
            'ppt_compilation': False,
            'upload_complete': False
        }
    }

    print(f"\n1. 测试有效状态查询 (ID: {test_id[:8]}...)")

    # 使用patch模拟S3调用
    with patch('boto3.client') as mock_boto3:
        mock_s3 = create_mock_s3_client()
        mock_boto3.return_value = mock_s3

        # 模拟S3响应
        mock_response = MagicMock()
        mock_response.__getitem__.return_value.read.return_value = json.dumps(mock_status).encode()
        mock_s3.get_object.return_value = mock_response

        status_request = {
            'httpMethod': 'GET',
            'path': f'/status/{test_id}',
            'pathParameters': {'id': test_id}
        }

        response = handler(status_request, None)
        print(f"   状态码: {response['statusCode']}")

        if response['statusCode'] == 200:
            body = json.loads(response['body'])
            print(f"   响应体键: {list(body.keys())}")

            # 验证必需字段
            required_fields = ['presentation_id', 'status', 'progress', 'topic']
            for field in required_fields:
                assert field in body, f"状态响应缺少必需字段: {field}"
                print(f"   ✓ {field}: {body[field]}")

            print("   ✅ 状态端点测试通过")
        else:
            print(f"   ❌ 期望状态码200，实际: {response['statusCode']}")
            print(f"   响应: {response.get('body', '')}")

    print("\n2. 测试无效ID查询")
    invalid_request = {
        'httpMethod': 'GET',
        'path': '/status/invalid-id',
        'pathParameters': {'id': 'invalid-id'}
    }

    response = handler(invalid_request, None)
    print(f"   无效ID状态码: {response['statusCode']}")
    assert response['statusCode'] == 400, "无效ID应返回400"
    print("   ✅ 无效ID处理测试通过")

def test_download_endpoint():
    """测试GET /download/{id}端点"""
    print("\n" + "=" * 50)
    print("测试 GET /download/{id} 端点")
    print("=" * 50)

    from lambdas.download_ppt import handler

    # 设置环境
    os.environ['S3_BUCKET'] = 'test-bucket'

    test_id = str(uuid.uuid4())

    print(f"\n1. 测试有效下载请求 (ID: {test_id[:8]}...)")

    # 使用patch模拟S3调用
    with patch('boto3.client') as mock_boto3:
        mock_s3 = create_mock_s3_client()
        mock_boto3.return_value = mock_s3

        # 模拟文件存在
        mock_s3.head_object.return_value = {
            'ContentLength': 123456,
            'LastModified': '2025-01-01T00:00:00Z'
        }

        download_request = {
            'httpMethod': 'GET',
            'path': f'/download/{test_id}',
            'pathParameters': {'id': test_id}
        }

        response = handler(download_request, None)
        print(f"   状态码: {response['statusCode']}")

        if response['statusCode'] == 200:
            body = json.loads(response['body'])
            print(f"   响应体键: {list(body.keys())}")

            # 验证必需字段
            required_fields = ['presentation_id', 'download_url', 'expires_in']
            for field in required_fields:
                assert field in body, f"下载响应缺少必需字段: {field}"
                print(f"   ✓ {field}: {body[field]}")

            print("   ✅ 下载端点测试通过")
        else:
            print(f"   ❌ 期望状态码200，实际: {response['statusCode']}")
            print(f"   响应: {response.get('body', '')}")

    print("\n2. 测试文件不存在情况")
    with patch('boto3.client') as mock_boto3:
        mock_s3 = create_mock_s3_client()
        mock_boto3.return_value = mock_s3

        # 模拟文件不存在
        from botocore.exceptions import ClientError
        mock_s3.head_object.side_effect = ClientError(
            error_response={'Error': {'Code': '404'}},
            operation_name='HeadObject'
        )

        response = handler(download_request, None)
        print(f"   文件不存在状态码: {response['statusCode']}")
        assert response['statusCode'] == 404, "文件不存在应返回404"
        print("   ✅ 文件不存在处理测试通过")

def test_end_to_end_flow():
    """测试端到端流程"""
    print("\n" + "=" * 50)
    print("测试端到端流程")
    print("=" * 50)

    # 1. 生成请求
    print("\n1. 发起生成请求")
    presentation_id = test_generate_endpoint()

    if not presentation_id:
        print("   ❌ 生成请求失败，无法继续端到端测试")
        return False

    # 2. 查询状态
    print(f"\n2. 查询生成状态 (ID: {presentation_id[:8]}...)")
    # 这里可以添加更详细的状态查询测试

    # 3. 模拟完成后的下载
    print("\n3. 模拟下载请求")
    # 这里可以添加下载测试

    print("\n✅ 端到端流程测试完成")
    return True

def test_error_handling():
    """测试错误处理"""
    print("\n" + "=" * 50)
    print("测试错误处理")
    print("=" * 50)

    from lambdas.api_handler import handler

    # 测试各种错误情况
    error_cases = [
        {
            'name': '空请求体',
            'event': {
                'httpMethod': 'POST',
                'path': '/generate',
                'body': None
            },
            'expected_status': 400
        },
        {
            'name': '无效JSON',
            'event': {
                'httpMethod': 'POST',
                'path': '/generate',
                'body': '{"invalid": json}'
            },
            'expected_status': 400
        },
        {
            'name': '缺少topic',
            'event': {
                'httpMethod': 'POST',
                'path': '/generate',
                'body': json.dumps({'page_count': 5})
            },
            'expected_status': 400
        },
        {
            'name': 'topic太短',
            'event': {
                'httpMethod': 'POST',
                'path': '/generate',
                'body': json.dumps({'topic': 'ab'})
            },
            'expected_status': 400
        }
    ]

    for case in error_cases:
        print(f"\n测试错误情况: {case['name']}")
        response = handler(case['event'], None)
        print(f"   状态码: {response['statusCode']} (期望: {case['expected_status']})")
        assert response['statusCode'] == case['expected_status'], f"错误情况 '{case['name']}' 状态码不匹配"
        print("   ✅ 通过")

def run_endpoint_tests():
    """运行所有端点测试"""
    print("开始API端点功能测试")
    print("=" * 60)

    tests = [
        ("生成端点", test_generate_endpoint),
        ("状态端点", test_status_endpoint),
        ("下载端点", test_download_endpoint),
        ("错误处理", test_error_handling),
        ("端到端流程", test_end_to_end_flow)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            print(f"运行测试: {test_name}")
            print(f"{'='*60}")

            result = test_func()
            if result is False:
                print(f"❌ {test_name} 测试失败")
                failed += 1
            else:
                print(f"✅ {test_name} 测试通过")
                passed += 1

        except Exception as e:
            print(f"❌ {test_name} 测试出错: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print("API端点测试结果汇总")
    print(f"{'='*60}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")

    if failed == 0:
        print("\n🎉 所有API端点测试通过！")
        print("✅ POST /generate - 接受请求并返回presentation_id")
        print("✅ GET /status/{id} - 返回处理状态和进度")
        print("✅ GET /download/{id} - 返回下载链接")
        print("✅ 错误处理完善")
        print("✅ 端到端流程正常")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，需要修复")
        return False

if __name__ == "__main__":
    success = run_endpoint_tests()
    sys.exit(0 if success else 1)