#!/usr/bin/env python3
"""
简化的API测试 - 验证核心API逻辑而不依赖AWS服务
"""
import json
import sys
import os
import uuid
from unittest.mock import Mock, MagicMock

# 添加路径
sys.path.append('.')

def test_api_request_validation():
    """测试API请求验证逻辑"""
    print("=" * 50)
    print("测试API请求验证逻辑")
    print("=" * 50)

    from src.validators import RequestValidator

    test_cases = [
        # 有效请求
        ({'topic': '人工智能的未来', 'page_count': 5}, True, "有效的标准请求"),
        ({'topic': '区块链技术详解', 'slides_count': 8}, True, "使用slides_count的请求"),
        ({'topic': '云计算架构', 'page_count': 10, 'style': 'professional'}, True, "包含style的请求"),

        # 无效请求
        ({}, False, "空请求"),
        ({'topic': ''}, False, "空主题"),
        ({'topic': 'ab'}, False, "主题太短"),
        ({'topic': 'valid', 'page_count': 0}, False, "页数为0"),
        ({'topic': 'valid', 'page_count': 25}, False, "页数过多"),
        ({'topic': '<script>alert("xss")</script>'}, False, "包含恶意内容"),
    ]

    passed = 0
    failed = 0

    for request_data, expected_valid, description in test_cases:
        is_valid, error = RequestValidator.validate_generate_request(request_data)

        if is_valid == expected_valid:
            print(f"   ✅ {description}: {is_valid}")
            passed += 1
        else:
            print(f"   ❌ {description}: 期望 {expected_valid}, 实际 {is_valid} (错误: {error})")
            failed += 1

    print(f"\n请求验证测试: 通过 {passed}, 失败 {failed}")
    return failed == 0

def test_presentation_id_validation():
    """测试presentation_id验证"""
    print("\n" + "=" * 50)
    print("测试presentation_id验证")
    print("=" * 50)

    from src.validators import RequestValidator

    # 有效UUID
    valid_ids = [
        str(uuid.uuid4()),
        "123e4567-e89b-12d3-a456-426614174000",
        "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    ]

    # 无效UUID
    invalid_ids = [
        "invalid-uuid",
        "123e4567-e89b-12d3-a456",  # 太短
        "",
        "not-a-uuid-at-all"
    ]

    passed = 0
    failed = 0

    for uuid_str in valid_ids:
        if RequestValidator.validate_presentation_id(uuid_str):
            print(f"   ✅ 有效UUID: {uuid_str[:8]}...")
            passed += 1
        else:
            print(f"   ❌ 应该有效的UUID被拒绝: {uuid_str}")
            failed += 1

    for uuid_str in invalid_ids:
        if not RequestValidator.validate_presentation_id(uuid_str):
            print(f"   ✅ 无效UUID被正确拒绝: '{uuid_str}'")
            passed += 1
        else:
            print(f"   ❌ 无效UUID被错误接受: '{uuid_str}'")
            failed += 1

    print(f"\nUUID验证测试: 通过 {passed}, 失败 {failed}")
    return failed == 0

def test_api_response_format():
    """测试API响应格式"""
    print("\n" + "=" * 50)
    print("测试API响应格式")
    print("=" * 50)

    from lambdas.api_handler import APIHandler

    # 创建模拟S3客户端
    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock()

    # 创建API处理器实例
    api_handler = APIHandler(s3_client=mock_s3)

    # 测试成功响应格式 - 使用ResponseBuilder
    from src.common.response_builder import ResponseBuilder
    from src.constants import Config

    success_data = {'test': 'data'}
    response = ResponseBuilder.success_response(
        Config.API.HTTP_OK,
        success_data
    )

    required_fields = ['statusCode', 'headers', 'body']
    for field in required_fields:
        if field not in response:
            print(f"   ❌ 响应缺少必需字段: {field}")
            return False

    if response['statusCode'] != 200:
        print(f"   ❌ 状态码不正确: {response['statusCode']}")
        return False

    # 验证CORS头部
    headers = response['headers']
    cors_headers = ['Access-Control-Allow-Origin', 'Access-Control-Allow-Headers']
    for header in cors_headers:
        if header not in headers:
            print(f"   ❌ 缺少CORS头部: {header}")
            return False

    # 验证body是有效JSON
    try:
        body_data = json.loads(response['body'])
        if body_data != success_data:
            print(f"   ❌ Body数据不匹配")
            return False
    except json.JSONDecodeError:
        print(f"   ❌ Body不是有效JSON")
        return False

    print("   ✅ 成功响应格式正确")

    # 测试错误响应格式 - 使用ResponseBuilder
    error_response = ResponseBuilder.error_response(
        Config.API.HTTP_BAD_REQUEST,
        "Test error",
        Config.Error.VALIDATION_ERROR
    )

    if error_response['statusCode'] != 400:
        print(f"   ❌ 错误状态码不正确: {error_response['statusCode']}")
        return False

    try:
        error_body = json.loads(error_response['body'])
        if 'error' not in error_body:
            print(f"   ❌ 错误响应缺少error字段")
            return False
    except json.JSONDecodeError:
        print(f"   ❌ 错误响应Body不是有效JSON")
        return False

    print("   ✅ 错误响应格式正确")
    return True

def test_endpoint_routing():
    """测试端点路由"""
    print("\n" + "=" * 50)
    print("测试端点路由")
    print("=" * 50)

    from lambdas.api_handler import handler

    os.environ['S3_BUCKET'] = 'test-bucket'

    # 测试OPTIONS请求
    options_event = {
        'httpMethod': 'OPTIONS',
        'path': '/generate'
    }

    response = handler(options_event, None)
    if response['statusCode'] != 200:
        print(f"   ❌ OPTIONS请求失败: {response['statusCode']}")
        return False
    print("   ✅ OPTIONS请求路由正确")

    # 测试无效路径
    invalid_event = {
        'httpMethod': 'GET',
        'path': '/invalid-path'
    }

    response = handler(invalid_event, None)
    if response['statusCode'] != 404:
        print(f"   ❌ 无效路径应返回404，实际: {response['statusCode']}")
        return False
    print("   ✅ 无效路径处理正确")

    return True

def test_error_scenarios():
    """测试错误场景"""
    print("\n" + "=" * 50)
    print("测试错误场景")
    print("=" * 50)

    from lambdas.api_handler import handler

    error_scenarios = [
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
        }
    ]

    passed = 0
    failed = 0

    for scenario in error_scenarios:
        response = handler(scenario['event'], None)
        actual_status = response['statusCode']
        expected_status = scenario['expected_status']

        if actual_status == expected_status:
            print(f"   ✅ {scenario['name']}: {actual_status}")
            passed += 1
        else:
            print(f"   ❌ {scenario['name']}: 期望 {expected_status}, 实际 {actual_status}")
            failed += 1

    print(f"\n错误场景测试: 通过 {passed}, 失败 {failed}")
    return failed == 0

def test_ppt_generation_logic():
    """测试PPT生成逻辑（不调用实际服务）"""
    print("\n" + "=" * 50)
    print("测试PPT生成逻辑")
    print("=" * 50)

    from src.ppt_compiler import create_pptx_from_content

    # 测试基础PPT生成
    test_content = {
        'slides': [
            {
                'slide_number': 1,
                'title': '测试标题页',
                'bullet_points': [
                    '这是第一个要点',
                    '这是第二个要点',
                    '这是第三个要点'
                ],
                'speaker_notes': '这是演讲者备注'
            },
            {
                'slide_number': 2,
                'title': '第二页标题',
                'bullet_points': [
                    '第二页第一个要点',
                    '第二页第二个要点'
                ]
            }
        ]
    }

    try:
        pptx_bytes = create_pptx_from_content(test_content)

        if not pptx_bytes or len(pptx_bytes) == 0:
            print("   ❌ PPT生成失败，返回空内容")
            return False

        print(f"   ✅ PPT生成成功，大小: {len(pptx_bytes)} bytes")

        # 验证PPT结构（简单测试）
        if len(pptx_bytes) < 1000:  # PPT文件应该至少几KB
            print("   ❌ PPT文件过小，可能生成不完整")
            return False

        print("   ✅ PPT文件大小合理")
        return True

    except Exception as e:
        print(f"   ❌ PPT生成出错: {e}")
        return False

def run_simple_tests():
    """运行所有简化测试"""
    print("开始简化API测试")
    print("=" * 60)

    tests = [
        ("请求验证", test_api_request_validation),
        ("UUID验证", test_presentation_id_validation),
        ("响应格式", test_api_response_format),
        ("端点路由", test_endpoint_routing),
        ("错误处理", test_error_scenarios),
        ("PPT生成", test_ppt_generation_logic)
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n{'='*60}")
            print(f"运行测试: {test_name}")
            print(f"{'='*60}")

            if test_func():
                print(f"✅ {test_name} 测试通过")
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
                failed += 1

        except Exception as e:
            print(f"❌ {test_name} 测试出错: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print("简化API测试结果汇总")
    print(f"{'='*60}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")

    if failed == 0:
        print("\n🎉 所有核心API功能测试通过！")
        print("✅ 请求验证逻辑正确")
        print("✅ UUID验证功能正常")
        print("✅ API响应格式标准")
        print("✅ 端点路由工作正常")
        print("✅ 错误处理完善")
        print("✅ PPT生成逻辑可用")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，需要修复")
        return False

if __name__ == "__main__":
    success = run_simple_tests()
    sys.exit(0 if success else 1)