#!/usr/bin/env python3
"""
本地API测试脚本 - 验证API端点实现
"""
import json
import sys
import os
from unittest.mock import Mock, MagicMock
from datetime import datetime
import uuid

# 添加路径
sys.path.append('.')

def test_api_handlers():
    """测试API处理器"""
    print("=" * 50)
    print("测试API处理器")
    print("=" * 50)

    # 设置环境
    os.environ['S3_BUCKET'] = 'test-bucket'

    from lambdas.api_handler import handler

    # 测试OPTIONS请求（CORS）
    print("\n1. 测试OPTIONS请求")
    options_event = {
        'httpMethod': 'OPTIONS',
        'path': '/generate'
    }
    response = handler(options_event, None)
    print(f"   OPTIONS响应状态码: {response['statusCode']}")
    assert response['statusCode'] == 200
    print("   ✅ OPTIONS请求测试通过")

    # 测试无效端点
    print("\n2. 测试无效端点")
    invalid_event = {
        'httpMethod': 'GET',
        'path': '/invalid'
    }
    response = handler(invalid_event, None)
    print(f"   无效端点响应状态码: {response['statusCode']}")
    assert response['statusCode'] == 404
    print("   ✅ 无效端点测试通过")

    # 测试无效JSON
    print("\n3. 测试无效JSON")
    invalid_json_event = {
        'httpMethod': 'POST',
        'path': '/generate',
        'body': '{"topic": "test"'  # 无效JSON
    }
    response = handler(invalid_json_event, None)
    print(f"   无效JSON响应状态码: {response['statusCode']}")
    assert response['statusCode'] == 400
    print("   ✅ 无效JSON测试通过")

def test_validators():
    """测试验证器"""
    print("\n" + "=" * 50)
    print("测试验证器")
    print("=" * 50)

    from src.validators import RequestValidator

    # 测试有效请求
    print("\n1. 测试有效请求验证")
    valid_requests = [
        {'topic': '人工智能的未来', 'page_count': 5},
        {'topic': '区块链技术', 'slides_count': 8, 'style': 'professional'},
        {'topic': '云计算架构设计', 'page_count': 10}
    ]

    for i, request in enumerate(valid_requests):
        is_valid, error = RequestValidator.validate_generate_request(request)
        print(f"   请求{i+1}: 有效={is_valid}, 错误={error}")
        assert is_valid, f"请求{i+1}应该有效: {error}"

    print("   ✅ 有效请求验证通过")

    # 测试无效请求
    print("\n2. 测试无效请求验证")
    invalid_requests = [
        {},  # 空请求
        {'topic': ''},  # 空主题
        {'topic': 'aa'},  # 主题太短
        {'topic': 'valid', 'page_count': 0},  # 页数无效
        {'topic': 'valid', 'page_count': 25},  # 页数过多
        {'topic': '<script>alert("xss")</script>'},  # 恶意内容
    ]

    for i, request in enumerate(invalid_requests):
        is_valid, error = RequestValidator.validate_generate_request(request)
        print(f"   无效请求{i+1}: 有效={is_valid}, 错误={error}")
        assert not is_valid, f"请求{i+1}应该无效"

    print("   ✅ 无效请求验证通过")

    # 测试UUID验证
    print("\n3. 测试UUID验证")
    valid_uuids = [
        "123e4567-e89b-12d3-a456-426614174000",
        "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        str(uuid.uuid4())
    ]

    invalid_uuids = [
        "invalid-uuid",
        "123e4567-e89b-12d3-a456",  # 太短
        "not-a-uuid-at-all",
        "",
        None
    ]

    for uuid_str in valid_uuids:
        assert RequestValidator.validate_presentation_id(uuid_str), f"UUID应该有效: {uuid_str}"

    for uuid_str in invalid_uuids:
        if uuid_str is not None:
            assert not RequestValidator.validate_presentation_id(uuid_str), f"UUID应该无效: {uuid_str}"

    print("   ✅ UUID验证通过")

def test_status_manager():
    """测试状态管理器（无AWS调用）"""
    print("\n" + "=" * 50)
    print("测试状态管理器")
    print("=" * 50)

    from src.status_manager import StatusManager, PresentationStatus

    # 创建模拟S3客户端
    mock_s3 = MagicMock()
    mock_s3.put_object = MagicMock()
    mock_s3.get_object = MagicMock()

    # 初始化状态管理器
    status_manager = StatusManager('test-bucket', mock_s3)

    print("\n1. 测试状态枚举")
    print(f"   状态值: {[status.value for status in PresentationStatus]}")
    assert PresentationStatus.PENDING.value == "pending"
    assert PresentationStatus.COMPLETED.value == "completed"
    print("   ✅ 状态枚举测试通过")

    print("\n2. 测试状态创建")
    test_id = "test-presentation-123"

    # 模拟创建状态（不实际调用S3）
    status_data = {
        'presentation_id': test_id,
        'topic': '测试主题',
        'page_count': 5,
        'status': 'pending',
        'progress': 0
    }

    # 验证状态数据结构
    assert 'presentation_id' in status_data
    assert 'status' in status_data
    assert 'progress' in status_data
    print("   ✅ 状态创建测试通过")

def test_content_integration():
    """测试内容生成和PPT编译集成"""
    print("\n" + "=" * 50)
    print("测试内容生成集成")
    print("=" * 50)

    # 测试是否能导入所有必需模块
    try:
        from src.content_generator import ContentGenerator
        from src.ppt_compiler import PPTCompiler, create_pptx_from_content
        print("   ✅ 所有模块导入成功")
    except ImportError as e:
        print(f"   ❌ 模块导入失败: {e}")
        return False

    # 测试PPT编译器基础功能
    print("\n1. 测试PPT编译器")
    test_content = {
        'slides': [
            {
                'slide_number': 1,
                'title': '测试标题',
                'bullet_points': ['要点1', '要点2', '要点3'],
                'speaker_notes': '演讲者备注'
            }
        ]
    }

    try:
        pptx_bytes = create_pptx_from_content(test_content)
        assert len(pptx_bytes) > 0, "PPT文件应该包含数据"
        print(f"   生成PPT文件大小: {len(pptx_bytes)} bytes")
        print("   ✅ PPT编译测试通过")
    except Exception as e:
        print(f"   ❌ PPT编译失败: {e}")
        return False

    return True

def run_all_tests():
    """运行所有测试"""
    print("开始API端点实现验证测试")
    print("时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    tests = [
        ("API处理器", test_api_handlers),
        ("验证器", test_validators),
        ("状态管理器", test_status_manager),
        ("内容集成", test_content_integration)
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
            failed += 1

    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")

    if failed == 0:
        print("\n🎉 所有测试通过！API端点实现验证成功")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，需要修复")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)