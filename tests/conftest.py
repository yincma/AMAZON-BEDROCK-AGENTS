"""
pytest配置文件和全局fixtures
测试框架配置 - 支持AWS服务模拟和通用测试工具
"""

import pytest
import json
import boto3
from moto import mock_aws
from uuid import uuid4
from datetime import datetime
import os
from unittest.mock import Mock, patch
import responses
from test_utils import AWSMockHelper, TestDataFactory

# 测试常量
TEST_BUCKET_NAME = "ai-ppt-presentations-test"
TEST_REGION = "us-east-1"
TEST_PRESENTATION_ID = "test-presentation-123"

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """设置测试环境变量"""
    test_env = {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SECURITY_TOKEN": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": TEST_REGION,
        "ENVIRONMENT": "test",
        "DEBUG": "true",
        "CACHE_ENABLED": "true",
        "PARALLEL_PROCESSING": "true"
    }

    for key, value in test_env.items():
        os.environ[key] = value

    yield test_env

    # 清理环境变量
    for key in test_env.keys():
        os.environ.pop(key, None)

@pytest.fixture(scope="session")
def aws_credentials():
    """模拟AWS凭证"""
    return {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SECURITY_TOKEN": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": TEST_REGION
    }

@pytest.fixture
def mock_s3_bucket(aws_credentials):
    """创建模拟S3桶和客户端"""
    with mock_aws():
        s3_client = boto3.client("s3", region_name=TEST_REGION)
        s3_client.create_bucket(Bucket=TEST_BUCKET_NAME)
        yield s3_client

@pytest.fixture
def mock_lambda_client(aws_credentials):
    """创建模拟Lambda客户端"""
    with mock_aws():
        # 先创建IAM角色
        iam_client = boto3.client("iam", region_name=TEST_REGION)
        assume_role_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        iam_client.create_role(
            RoleName="lambda-role",
            AssumeRolePolicyDocument=json.dumps(assume_role_policy_document),
            Description="Test Lambda execution role",
        )

        lambda_client = boto3.client("lambda", region_name=TEST_REGION)

        # 创建测试Lambda函数
        lambda_client.create_function(
            FunctionName="generate_ppt",
            Runtime="python3.13",
            Role="arn:aws:iam::123456789012:role/lambda-role",
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": b"fake code"},
            Description="测试PPT生成函数",
            Timeout=30,
            MemorySize=1024,
        )

        lambda_client.create_function(
            FunctionName="content_generator",
            Runtime="python3.13",
            Role="arn:aws:iam::123456789012:role/lambda-role",
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": b"fake code"},
            Description="测试内容生成函数",
            Timeout=60,
            MemorySize=2048,
        )

        # Phase 2: 添加演讲者备注Lambda函数
        lambda_client.create_function(
            FunctionName="generate_speaker_notes",
            Runtime="python3.13",
            Role="arn:aws:iam::123456789012:role/lambda-role",
            Handler="notes_generator.handler",
            Code={"ZipFile": b"fake code"},
            Description="测试演讲者备注生成函数",
            Timeout=30,
            MemorySize=1024,
        )

        # Phase 2: 添加图片生成Lambda函数
        lambda_client.create_function(
            FunctionName="image_generator",
            Runtime="python3.13",
            Role="arn:aws:iam::123456789012:role/lambda-role",
            Handler="image_generator.handler",
            Code={"ZipFile": b"fake code"},
            Description="测试图片生成函数",
            Timeout=45,
            MemorySize=1024,
        )

        # Phase 2: 添加PPT样式Lambda函数
        lambda_client.create_function(
            FunctionName="ppt_styler",
            Runtime="python3.13",
            Role="arn:aws:iam::123456789012:role/lambda-role",
            Handler="ppt_styler.handler",
            Code={"ZipFile": b"fake code"},
            Description="测试PPT样式应用函数",
            Timeout=30,
            MemorySize=1024,
        )

        yield lambda_client

# Phase 3 特定的fixtures

@pytest.fixture
def responses_mock():
    """HTTP响应Mock"""
    with responses.RequestsMock() as rsps:
        yield rsps

@pytest.fixture
def test_presentation_data():
    """测试演示文稿数据"""
    return TestDataFactory.create_presentation_request(
        topic="测试演示文稿",
        page_count=10,
        template="modern",
        parallel_processing=True,
        use_cache=True
    )

@pytest.fixture
def mock_performance_components():
    """性能测试组件Mock集合"""
    from test_utils import MockPerformanceComponents
    return {
        "cache_manager": MockPerformanceComponents.create_cache_manager(),
        "parallel_processor": MockPerformanceComponents.create_parallel_processor(),
        "performance_monitor": MockPerformanceComponents.create_performance_monitor()
    }

@pytest.fixture
def mock_redis_cache():
    """模拟Redis缓存"""
    cache = Mock()
    cache.get.return_value = None
    cache.set.return_value = True
    cache.delete.return_value = 1
    cache.exists.return_value = False
    cache.expire.return_value = True
    cache.ttl.return_value = -1
    cache.keys.return_value = []
    cache.flushdb.return_value = True
    return cache

@pytest.fixture
def mock_api_gateway():
    """模拟API Gateway"""
    from test_utils import MockAPIGateway
    return MockAPIGateway

@pytest.fixture(scope="function")
def isolated_test():
    """隔离测试环境"""
    # 每个测试开始前的设置
    test_id = str(uuid4())
    test_context = {
        "test_id": test_id,
        "start_time": datetime.now(),
        "test_data": {}
    }

    yield test_context

    # 每个测试结束后的清理
    # 这里可以添加清理逻辑

@pytest.fixture
def mock_bedrock_client():
    """模拟Bedrock客户端"""
    with mock_aws():
        client = boto3.client("bedrock-runtime", region_name=TEST_REGION)

        # Mock invoke_model方法
        def mock_invoke_model(**kwargs):
            model_id = kwargs.get("modelId", "")
            body = json.loads(kwargs.get("body", "{}"))

            # 根据模型ID返回不同的响应
            if "claude" in model_id:
                response_body = {
                    "completion": "这是一个Claude模型生成的测试内容",
                    "stop_reason": "end_turn"
                }
            elif "titan" in model_id:
                response_body = {
                    "results": [{
                        "outputText": "这是Titan模型生成的测试内容"
                    }]
                }
            else:
                response_body = {
                    "generated_text": "默认测试内容"
                }

            return {
                "body": json.dumps(response_body).encode("utf-8"),
                "contentType": "application/json"
            }

        client.invoke_model = Mock(side_effect=mock_invoke_model)
        yield client

@pytest.fixture
def performance_test_config():
    """性能测试配置"""
    return {
        "max_generation_time": 30.0,
        "min_efficiency_gain": 0.5,
        "max_parallel_tasks": 8,
        "cache_ttl": 3600,
        "rate_limit": 100,
        "concurrent_requests": 10
    }

@pytest.fixture
def mock_bedrock_runtime():
    mock_client = Mock()

    # 模拟Claude响应
    mock_response = {
        "body": Mock(),
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }

    # 模拟流式响应
    mock_response["body"].read.return_value = json.dumps({
        "completion": "这是生成的大纲内容",
        "stop_reason": "end_turn"
    }).encode()

    mock_client.invoke_model.return_value = mock_response

    return mock_client

@pytest.fixture
def mock_apigateway_client(aws_credentials):
    """创建模拟API Gateway客户端"""
    with mock_aws():
        api_client = boto3.client("apigateway", region_name=TEST_REGION)

        # 创建测试API
        api_response = api_client.create_rest_api(
            name="ai-ppt-api-test",
            description="测试API"
        )
        api_id = api_response["id"]

        # 获取根资源
        resources = api_client.get_resources(restApiId=api_id)
        root_id = resources["items"][0]["id"]

        # 创建/generate资源
        generate_resource = api_client.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart="generate"
        )

        # 创建POST方法
        api_client.put_method(
            restApiId=api_id,
            resourceId=generate_resource["id"],
            httpMethod="POST",
            authorizationType="NONE"
        )

        yield api_client, api_id

@pytest.fixture
def test_presentation_id():
    """生成测试用的presentation ID"""
    return f"test-{uuid4().hex[:8]}"

@pytest.fixture
def sample_outline():
    """示例大纲数据"""
    return {
        "title": "人工智能的未来",
        "slides": [
            {
                "slide_number": 1,
                "title": "人工智能概述",
                "content": [
                    "AI的定义和发展历程",
                    "当前AI技术的主要应用领域",
                    "AI对社会的影响和意义"
                ]
            },
            {
                "slide_number": 2,
                "title": "机器学习核心技术",
                "content": [
                    "深度学习和神经网络",
                    "自然语言处理技术",
                    "计算机视觉技术"
                ]
            },
            {
                "slide_number": 3,
                "title": "AI在各行业的应用",
                "content": [
                    "医疗健康领域的AI应用",
                    "金融科技中的智能化",
                    "自动驾驶和交通运输"
                ]
            },
            {
                "slide_number": 4,
                "title": "AI发展的挑战和机遇",
                "content": [
                    "技术瓶颈和突破方向",
                    "伦理和隐私问题",
                    "人才培养和产业发展"
                ]
            },
            {
                "slide_number": 5,
                "title": "未来展望",
                "content": [
                    "AGI（通用人工智能）的可能性",
                    "AI与人类的协作模式",
                    "技术发展的社会责任"
                ]
            }
        ],
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "total_slides": 5,
            "estimated_duration": "10-15分钟"
        }
    }

@pytest.fixture
def sample_slide_content():
    """示例幻灯片详细内容"""
    return {
        "presentation_id": TEST_PRESENTATION_ID,
        "slides": [
            {
                "slide_number": 1,
                "title": "人工智能概述",
                "bullet_points": [
                    "AI是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统",
                    "从1950年代至今，AI经历了多次发展浪潮，当前正处于深度学习时代",
                    "AI正在改变我们的工作方式、生活方式和思维方式"
                ],
                "speaker_notes": "介绍AI的基本概念，为后续内容奠定基础"
            }
        ]
    }

@pytest.fixture
def mock_pptx_file():
    """模拟生成的PPTX文件内容"""
    return b"\\x50\\x4b\\x03\\x04"  # PPTX文件头的简化版本

@pytest.fixture
def api_test_client():
    """API测试客户端配置"""
    return {
        "base_url": "https://api.ai-ppt-assistant.com",
        "api_key": "test-api-key-123",
        "timeout": 30
    }

@pytest.fixture
def performance_thresholds():
    """性能测试阈值"""
    return {
        "max_generation_time": 30,  # 秒
        "max_memory_usage": 1024,   # MB
        "max_concurrent_requests": 10
    }

# 测试工具函数
def create_test_s3_object(s3_client, bucket, key, content):
    """创建测试用S3对象"""
    if isinstance(content, dict):
        content = json.dumps(content)
    if isinstance(content, str):
        content = content.encode('utf-8')

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content,
        ContentType='application/json'
    )

def assert_s3_object_exists(s3_client, bucket, key):
    """断言S3对象存在"""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except s3_client.exceptions.NoSuchKey:
        return False

def assert_valid_presentation_id(presentation_id):
    """断言presentation_id格式正确"""
    assert isinstance(presentation_id, str)
    assert len(presentation_id) > 0
    # 可以添加更多格式验证

# 测试标记
pytest_marks = {
    "unit": pytest.mark.unit,
    "integration": pytest.mark.integration,
    "e2e": pytest.mark.e2e,
    "slow": pytest.mark.slow,
    "aws": pytest.mark.aws
}

# pytest配置
def pytest_configure(config):
    """pytest启动配置"""
    config.addinivalue_line("markers", "unit: 单元测试标记")
    config.addinivalue_line("markers", "integration: 集成测试标记")
    config.addinivalue_line("markers", "e2e: 端到端测试标记")
    config.addinivalue_line("markers", "slow: 慢测试标记")
    config.addinivalue_line("markers", "aws: AWS服务测试标记")

def pytest_collection_modifyitems(config, items):
    """动态修改测试项目"""
    for item in items:
        # 为所有test_文件添加相应标记
        if "test_infrastructure" in item.nodeid:
            item.add_marker(pytest.mark.aws)
        elif "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_api" in item.nodeid:
            item.add_marker(pytest.mark.e2e)