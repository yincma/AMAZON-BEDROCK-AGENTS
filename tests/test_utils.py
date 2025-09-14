"""
测试工具模块 - 提供统一的Mock设置和测试数据工厂
"""

import json
import uuid
import time
import random
import base64
import hashlib
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock
import responses
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from moto import mock_aws
from PIL import Image
import io
import concurrent.futures


class MockAPIGateway:
    """API Gateway Mock工具类"""

    BASE_URL = "https://api.ai-ppt-assistant.com/v2"

    @classmethod
    def setup_responses(cls) -> responses.RequestsMock:
        """设置HTTP响应Mock"""
        mock = responses.RequestsMock()

        # 生成演示文稿
        mock.add(
            responses.POST,
            f"{cls.BASE_URL}/presentations/generate",
            json={"presentation_id": "test-ppt-123", "status": "processing"},
            status=202
        )

        # 演示文稿状态查询
        mock.add(
            responses.GET,
            f"{cls.BASE_URL}/presentations/test-ppt-123/status",
            json={"status": "completed", "progress": 100},
            status=200
        )

        # 更新幻灯片内容
        mock.add(
            responses.PATCH,
            f"{cls.BASE_URL}/presentations/test-ppt-123/slides/2",
            json={
                "presentation_id": "test-ppt-123",
                "slide_number": 2,
                "etag": "abc123",
                "updated_at": datetime.now().isoformat(),
                "preview_url": "https://test.com/preview.png"
            },
            status=200
        )

        # 删除演示文稿
        mock.add(
            responses.DELETE,
            f"{cls.BASE_URL}/presentations/test-ppt-123",
            status=204
        )

        # 健康检查
        mock.add(
            responses.GET,
            f"{cls.BASE_URL}/health",
            json={
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0",
                "services": {
                    "database": "healthy",
                    "storage": "healthy",
                    "cache": "healthy"
                }
            },
            status=200
        )

        return mock

    @classmethod
    def add_etag_responses(cls, mock: responses.RequestsMock):
        """添加ETag相关的响应"""
        # 第一次更新
        mock.add(
            responses.PATCH,
            f"{cls.BASE_URL}/presentations/test-ppt-123/slides/3",
            json={
                "presentation_id": "test-ppt-123",
                "slide_number": 3,
                "etag": "etag1",
                "updated_at": datetime.now().isoformat()
            },
            status=200
        )

        # 第二次更新（新的ETag）
        mock.add(
            responses.PATCH,
            f"{cls.BASE_URL}/presentations/test-ppt-123/slides/3",
            json={
                "presentation_id": "test-ppt-123",
                "slide_number": 3,
                "etag": "etag2",
                "updated_at": datetime.now().isoformat()
            },
            status=200
        )

        # 冲突响应（ETag不匹配）
        mock.add(
            responses.PATCH,
            f"{cls.BASE_URL}/presentations/test-ppt-123/slides/3",
            json={"error": "PRECONDITION_FAILED", "message": "ETag mismatch"},
            status=412
        )

    @classmethod
    def add_image_generation_responses(cls, mock: responses.RequestsMock):
        """添加图片生成相关响应"""
        mock.add(
            responses.POST,
            f"{cls.BASE_URL}/presentations/test-ppt-123/slides/1/image",
            json={
                "task_id": "img-task-123",
                "status": "pending",
                "estimated_time": 30,
                "status_url": f"{cls.BASE_URL}/tasks/img-task-123"
            },
            status=202
        )

    @classmethod
    def add_regeneration_responses(cls, mock: responses.RequestsMock):
        """添加重新生成相关响应"""
        # 重新生成指定幻灯片
        mock.add(
            responses.POST,
            f"{cls.BASE_URL}/presentations/test-ppt-123/regenerate",
            json={
                "task_id": "regen-task-123",
                "scope": "slides",
                "affected_slides": [2, 4],
                "status_url": f"{cls.BASE_URL}/tasks/regen-task-123"
            },
            status=202
        )

    @classmethod
    def add_validation_error_responses(cls, mock: responses.RequestsMock):
        """添加验证错误响应"""
        # 无效ID
        mock.add(
            responses.PATCH,
            f"{cls.BASE_URL}/presentations/invalid-id/slides/1",
            json={"error": "INVALID_PRESENTATION_ID", "message": "Invalid presentation ID format"},
            status=400
        )

        # 无效幻灯片编号
        mock.add(
            responses.PATCH,
            f"{cls.BASE_URL}/presentations/test-ppt-123/slides/999",
            json={"error": "INVALID_SLIDE_NUMBER", "message": "Slide number out of range"},
            status=400
        )

        # 空请求体
        mock.add(
            responses.PATCH,
            f"{cls.BASE_URL}/presentations/test-ppt-123/slides/1",
            json={"error": "EMPTY_REQUEST", "message": "Request body cannot be empty"},
            status=400
        )

        # 内容过长
        mock.add(
            responses.PATCH,
            f"{cls.BASE_URL}/presentations/test-ppt-123/slides/1",
            json={"error": "CONTENT_TOO_LONG", "message": "Content exceeds maximum length"},
            status=400
        )

    @classmethod
    def add_rate_limiting_responses(cls, mock: responses.RequestsMock):
        """添加限流响应"""
        # 正常响应前19次，第20次返回限流
        for i in range(19):
            mock.add(
                responses.PATCH,
                f"{cls.BASE_URL}/presentations/test-ppt-123/slides/1",
                json={
                    "presentation_id": "test-ppt-123",
                    "slide_number": 1,
                    "etag": f"etag-{i}",
                    "updated_at": datetime.now().isoformat()
                },
                status=200
            )

        # 限流响应
        mock.add(
            responses.PATCH,
            f"{cls.BASE_URL}/presentations/test-ppt-123/slides/1",
            json={
                "error": "RATE_LIMITED",
                "message": "Too many requests",
                "retry_after": 60
            },
            status=429,
            headers={
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + 60)
            }
        )


class TestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_presentation_request(
        topic: str = "Test Presentation",
        page_count: int = 5,
        template: str = "professional",
        with_images: bool = True,
        parallel_processing: bool = False,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """创建演示文稿请求数据"""
        return {
            "presentation_id": f"test-{uuid.uuid4()}",
            "topic": topic,
            "page_count": page_count,
            "template": template,
            "with_images": with_images,
            "parallel_processing": parallel_processing,
            "use_cache": use_cache,
            "created_at": datetime.now().isoformat()
        }

    @staticmethod
    def create_slide_update_request(
        title: Optional[str] = None,
        content: Optional[str] = None,
        speaker_notes: Optional[str] = None,
        layout: str = "standard"
    ) -> Dict[str, Any]:
        """创建幻灯片更新请求数据"""
        data = {"layout": layout}
        if title:
            data["title"] = title
        if content:
            data["content"] = content
        if speaker_notes:
            data["speaker_notes"] = speaker_notes
        return data

    @staticmethod
    def create_performance_test_data(count: int = 10) -> List[Dict[str, Any]]:
        """创建性能测试数据"""
        return [
            TestDataFactory.create_presentation_request(
                topic=f"Performance Test {i}",
                page_count=10,
                parallel_processing=True,
                use_cache=True
            )
            for i in range(count)
        ]

    @staticmethod
    def create_mock_aws_response(
        function_name: str,
        status_code: int = 200,
        payload: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """创建模拟AWS Lambda响应"""
        return {
            "StatusCode": status_code,
            "Payload": json.dumps(payload or {"status": "success"}),
            "FunctionName": function_name,
            "ExecutedVersion": "$LATEST"
        }


class MockPerformanceComponents:
    """性能测试组件Mock"""

    @staticmethod
    def create_cache_manager() -> Mock:
        """创建缓存管理器Mock"""
        cache = Mock()
        cache.get.return_value = None  # 默认缓存未命中
        cache.set.return_value = True
        cache.exists.return_value = False
        cache.clear.return_value = True
        cache.stats.return_value = {
            "hits": 0,
            "misses": 0,
            "hit_rate": 0.0
        }
        return cache

    @staticmethod
    def create_parallel_processor() -> Mock:
        """创建并行处理器Mock"""
        processor = Mock()
        processor.generate_slides_parallel.return_value = {
            "status": "success",
            "parallel_tasks": 4,
            "total_time": 18.5,
            "slides_generated": 10,
            "time_saved": 12.3,
            "efficiency_gain": 0.52
        }
        processor.process_concurrent_requests.return_value = {
            "processed": 10,
            "failed": 0,
            "avg_response_time": 2.5,
            "max_concurrent": 10
        }
        return processor

    @staticmethod
    def create_performance_monitor() -> Mock:
        """创建性能监控器Mock"""
        monitor = Mock()
        monitor.start_timing.return_value = time.time()
        monitor.end_timing.return_value = 15.5
        monitor.record_metric.return_value = True
        monitor.get_metrics.return_value = {
            "avg_generation_time": 18.5,
            "min_generation_time": 12.0,
            "max_generation_time": 25.0,
            "cache_hit_rate": 0.75,
            "parallel_efficiency": 0.85
        }
        return monitor


class AWSMockHelper:
    """AWS服务Mock助手"""

    @staticmethod
    @mock_aws
    def setup_lambda_mocks() -> boto3.client:
        """设置Lambda客户端Mock"""
        client = boto3.client("lambda", region_name="us-east-1")

        # 创建测试函数
        test_functions = [
            "generate_ppt",
            "content_generator",
            "image_generator",
            "generate_speaker_notes"
        ]

        for func_name in test_functions:
            client.create_function(
                FunctionName=func_name,
                Runtime="python3.13",
                Role="arn:aws:iam::123456789012:role/lambda-role",
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": b"fake code"},
                Timeout=300,
                MemorySize=1024
            )

        return client

    @staticmethod
    @mock_aws
    def setup_s3_mocks() -> boto3.client:
        """设置S3客户端Mock"""
        client = boto3.client("s3", region_name="us-east-1")

        # 创建测试桶
        test_buckets = [
            "ai-ppt-presentations-test",
            "ai-ppt-images-test",
            "ai-ppt-cache-test"
        ]

        for bucket in test_buckets:
            client.create_bucket(Bucket=bucket)

        return client

    @staticmethod
    @mock_aws
    def setup_dynamodb_mocks() -> boto3.client:
        """设置DynamoDB客户端Mock"""
        client = boto3.client("dynamodb", region_name="us-east-1")

        # 创建测试表
        client.create_table(
            TableName="presentations",
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )

        return client


def assert_response_structure(response: Dict[str, Any], required_fields: List[str]):
    """验证响应结构"""
    for field in required_fields:
        assert field in response, f"Missing required field: {field}"


def assert_performance_requirements(
    execution_time: float,
    max_time: float = 30.0,
    min_efficiency_gain: float = 0.5
):
    """验证性能要求"""
    assert execution_time < max_time, f"Execution time {execution_time}s exceeds limit {max_time}s"


def wait_for_mock_completion(mock_func, timeout: int = 5):
    """等待Mock函数完成（用于模拟异步操作）"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if mock_func.call_count > 0:
            return True
        time.sleep(0.1)
    return False


class EnhancedAWSMockHelper:
    """增强的AWS服务Mock助手"""

    @staticmethod
    def create_bedrock_client_mock(response_delay: float = 0.1,
                                   failure_rate: float = 0.0,
                                   models_config: Dict[str, Any] = None) -> Mock:
        """
        创建高级Bedrock客户端Mock

        Args:
            response_delay: 响应延迟（秒）
            failure_rate: 失败率（0.0-1.0）
            models_config: 模型配置
        """
        client = Mock()
        call_count = {'count': 0}

        def mock_invoke_model(**kwargs):
            call_count['count'] += 1
            model_id = kwargs.get('modelId', '')
            body = json.loads(kwargs.get('body', '{}'))

            # 模拟延迟
            if response_delay > 0:
                time.sleep(response_delay)

            # 模拟失败
            if random.random() < failure_rate:
                error_types = [
                    ('ThrottlingException', '请求过于频繁'),
                    ('ModelNotReadyException', '模型未准备就绪'),
                    ('ValidationException', '请求参数无效'),
                    ('ServiceQuotaExceededException', '超出服务限额')
                ]
                error_code, error_message = random.choice(error_types)
                raise ClientError(
                    {'Error': {'Code': error_code, 'Message': error_message}},
                    'InvokeModel'
                )

            # 根据模型返回不同响应
            if 'nova' in model_id.lower():
                response_body = EnhancedAWSMockHelper._create_nova_response(body)
            elif 'stability' in model_id.lower():
                response_body = EnhancedAWSMockHelper._create_stability_response(body)
            elif 'claude' in model_id.lower():
                response_body = EnhancedAWSMockHelper._create_claude_response(body)
            else:
                response_body = {"error": f"不支持的模型: {model_id}"}

            mock_response = Mock()
            mock_response.read.return_value = json.dumps(response_body).encode('utf-8')

            return {
                'body': mock_response,
                'ResponseMetadata': {'HTTPStatusCode': 200}
            }

        client.invoke_model.side_effect = mock_invoke_model
        client.get_call_count = lambda: call_count['count']
        return client

    @staticmethod
    def _create_nova_response(request_body: Dict) -> Dict:
        """创建Nova模型响应"""
        # 创建1x1像素的PNG图片base64
        image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hRqYEAAAAABJRU5ErkJggg=="

        return {
            "images": [image_base64],
            "seed": random.randint(1, 1000000),
            "finishReason": "SUCCESS"
        }

    @staticmethod
    def _create_stability_response(request_body: Dict) -> Dict:
        """创建Stability AI响应"""
        image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hRqYEAAAAABJRU5ErkJggg=="

        return {
            "artifacts": [{
                "base64": image_base64,
                "seed": random.randint(1, 1000000),
                "finishReason": "SUCCESS"
            }]
        }

    @staticmethod
    def _create_claude_response(request_body: Dict) -> Dict:
        """创建Claude响应"""
        return {
            "completion": "这是Claude生成的测试内容",
            "stop_reason": "end_turn"
        }

    @staticmethod
    def create_s3_client_mock(enable_cache: bool = True,
                             cache_hit_rate: float = 0.3,
                             operation_delay: float = 0.01) -> Mock:
        """
        创建S3客户端Mock

        Args:
            enable_cache: 是否启用缓存模拟
            cache_hit_rate: 缓存命中率
            operation_delay: 操作延迟
        """
        client = Mock()
        storage = {}  # 模拟S3存储

        def mock_get_object(Bucket, Key, **kwargs):
            time.sleep(operation_delay)

            if enable_cache and random.random() < cache_hit_rate:
                # 模拟缓存命中
                image_data = base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI/hRqYEAAAAABJRU5ErkJggg=="
                )
                mock_body = Mock()
                mock_body.read.return_value = image_data
                return {'Body': mock_body}
            else:
                # 模拟缓存未命中
                raise ClientError(
                    {'Error': {'Code': 'NoSuchKey'}},
                    'GetObject'
                )

        def mock_put_object(Bucket, Key, Body, **kwargs):
            time.sleep(operation_delay)
            storage[f"{Bucket}/{Key}"] = Body
            return {'ETag': hashlib.md5(str(time.time()).encode()).hexdigest()}

        def mock_head_object(Bucket, Key, **kwargs):
            time.sleep(operation_delay)
            if f"{Bucket}/{Key}" in storage:
                return {'ResponseMetadata': {'HTTPStatusCode': 200}}
            else:
                raise ClientError(
                    {'Error': {'Code': 'NoSuchKey'}},
                    'HeadObject'
                )

        client.get_object.side_effect = mock_get_object
        client.put_object.side_effect = mock_put_object
        client.head_object.side_effect = mock_head_object
        client.get_storage = lambda: storage.copy()

        return client


class ConcurrencyTester:
    """并发测试工具"""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.results = []
        self.errors = []

    def run_concurrent_test(self, test_func, test_data: List,
                           timeout: float = 30.0) -> Dict[str, Any]:
        """
        运行并发测试

        Args:
            test_func: 测试函数
            test_data: 测试数据列表
            timeout: 超时时间

        Returns:
            测试结果统计
        """
        start_time = time.time()
        success_count = 0
        error_count = 0
        response_times = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_data = {
                executor.submit(self._execute_with_timing, test_func, data): data
                for data in test_data
            }

            for future in concurrent.futures.as_completed(future_to_data, timeout=timeout):
                data = future_to_data[future]
                try:
                    result, response_time = future.result()
                    self.results.append({
                        'data': data,
                        'result': result,
                        'response_time': response_time
                    })
                    success_count += 1
                    response_times.append(response_time)
                except Exception as e:
                    self.errors.append({
                        'data': data,
                        'error': str(e)
                    })
                    error_count += 1

        total_time = time.time() - start_time

        return {
            'total_requests': len(test_data),
            'successful_requests': success_count,
            'failed_requests': error_count,
            'success_rate': success_count / len(test_data),
            'total_time': total_time,
            'avg_response_time': statistics.mean(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'throughput': success_count / total_time
        }

    def _execute_with_timing(self, func, data):
        """执行函数并记录时间"""
        start_time = time.perf_counter()
        result = func(data)
        end_time = time.perf_counter()
        return result, end_time - start_time


class TestReportGenerator:
    """测试报告生成器"""

    def __init__(self):
        self.test_results = []
        self.performance_metrics = {}
        self.error_logs = []

    def add_test_result(self, test_name: str, result: Dict[str, Any]):
        """添加测试结果"""
        self.test_results.append({
            'test_name': test_name,
            'timestamp': time.time(),
            'result': result
        })

    def add_performance_metric(self, metric_name: str, value: float, unit: str = ''):
        """添加性能指标"""
        if metric_name not in self.performance_metrics:
            self.performance_metrics[metric_name] = []

        self.performance_metrics[metric_name].append({
            'value': value,
            'unit': unit,
            'timestamp': time.time()
        })

    def add_error_log(self, error: str, context: Dict[str, Any] = None):
        """添加错误日志"""
        self.error_logs.append({
            'error': error,
            'context': context or {},
            'timestamp': time.time()
        })

    def generate_summary_report(self) -> Dict[str, Any]:
        """生成汇总报告"""
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['result'].get('success', False)])

        performance_summary = {}
        for metric_name, values in self.performance_metrics.items():
            numeric_values = [v['value'] for v in values]
            performance_summary[metric_name] = {
                'count': len(numeric_values),
                'avg': statistics.mean(numeric_values),
                'min': min(numeric_values),
                'max': max(numeric_values),
                'std': statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0
            }

        return {
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': successful_tests / total_tests if total_tests > 0 else 0,
                'total_errors': len(self.error_logs)
            },
            'performance_metrics': performance_summary,
            'test_details': self.test_results,
            'error_logs': self.error_logs,
            'generated_at': time.time()
        }

    def save_report(self, filename: str):
        """保存报告到文件"""
        report = self.generate_summary_report()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


# 全局测试工具实例
test_report_generator = TestReportGenerator()


def setup_comprehensive_mocks():
    """设置综合Mock环境"""
    mocks = {
        'bedrock_client': EnhancedAWSMockHelper.create_bedrock_client_mock(
            response_delay=0.1,
            failure_rate=0.05
        ),
        's3_client': EnhancedAWSMockHelper.create_s3_client_mock(
            enable_cache=True,
            cache_hit_rate=0.3
        ),
        'cache_manager': MockPerformanceComponents.create_cache_manager(),
        'performance_monitor': MockPerformanceComponents.create_performance_monitor(),
        'api_gateway': MockAPIGateway()
    }

    return mocks


# 测试装饰器
def performance_test(threshold_seconds: float = 1.0):
    """性能测试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()

            execution_time = end_time - start_time

            # 记录性能指标
            test_report_generator.add_performance_metric(
                f"{func.__name__}_execution_time",
                execution_time,
                "seconds"
            )

            # 检查性能阈值
            if execution_time > threshold_seconds:
                test_report_generator.add_error_log(
                    f"性能测试失败: {func.__name__} 执行时间 {execution_time:.3f}s 超过阈值 {threshold_seconds}s"
                )

            return result
        return wrapper
    return decorator


def create_test_image_data(width: int = 800, height: int = 600, format: str = 'PNG') -> bytes:
    """创建测试图片数据"""
    # 创建随机颜色的图片
    color = (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )

    image = Image.new('RGB', (width, height), color)
    img_bytes = io.BytesIO()
    image.save(img_bytes, format=format)
    return img_bytes.getvalue()