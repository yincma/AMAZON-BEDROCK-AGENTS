#!/usr/bin/env python3
"""
AI PPT Assistant 部署验证脚本
验证图片生成服务的完整功能和性能
"""

import json
import time
import base64
import argparse
import os
import sys
from typing import Dict, Any, Optional
import logging
from datetime import datetime

import boto3
import requests
from botocore.exceptions import ClientError, NoCredentialsError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentValidator:
    """部署验证器类"""

    def __init__(self, environment: str = "dev"):
        """初始化验证器"""
        self.environment = environment
        self.aws_session = boto3.Session()
        self.lambda_client = self.aws_session.client('lambda')
        self.s3_client = self.aws_session.client('s3')
        self.dynamodb_client = self.aws_session.client('dynamodb')
        self.cloudwatch_client = self.aws_session.client('cloudwatch')

        # 存储验证结果
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'environment': environment,
            'tests': []
        }

    def add_test_result(self, test_name: str, status: str, details: str = "", duration: float = 0):
        """添加测试结果"""
        result = {
            'name': test_name,
            'status': status,  # PASS, FAIL, SKIP, WARNING
            'details': details,
            'duration_seconds': round(duration, 2),
            'timestamp': datetime.now().isoformat()
        }
        self.validation_results['tests'].append(result)

        # 记录日志
        if status == 'PASS':
            logger.info(f"✅ {test_name}: {details}")
        elif status == 'FAIL':
            logger.error(f"❌ {test_name}: {details}")
        elif status == 'WARNING':
            logger.warning(f"⚠️  {test_name}: {details}")
        else:
            logger.info(f"⏭️  {test_name}: {details}")

    def validate_aws_credentials(self) -> bool:
        """验证AWS凭证"""
        start_time = time.time()
        try:
            identity = self.aws_session.client('sts').get_caller_identity()
            account_id = identity['Account']
            user_arn = identity['Arn']

            self.add_test_result(
                'AWS凭证验证',
                'PASS',
                f'账户: {account_id}, 身份: {user_arn}',
                time.time() - start_time
            )
            return True

        except (ClientError, NoCredentialsError) as e:
            self.add_test_result(
                'AWS凭证验证',
                'FAIL',
                f'凭证验证失败: {str(e)}',
                time.time() - start_time
            )
            return False

    def get_terraform_outputs(self) -> Dict[str, Any]:
        """获取Terraform输出"""
        try:
            # 尝试从当前目录读取terraform输出
            import subprocess
            result = subprocess.run(
                ['terraform', 'output', '-json'],
                cwd=os.path.join(os.path.dirname(__file__), '..', 'infrastructure'),
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.warning("无法获取Terraform输出，将尝试其他方式")
                return {}

        except Exception as e:
            logger.warning(f"获取Terraform输出失败: {str(e)}")
            return {}

    def validate_lambda_functions(self, outputs: Dict[str, Any]) -> bool:
        """验证Lambda函数"""
        success = True

        # 基础图片生成函数
        function_name = outputs.get('image_generator_function_name', {}).get('value')
        if function_name:
            success &= self._validate_single_lambda(function_name, "基础图片生成Lambda")
        else:
            self.add_test_result('基础图片生成Lambda', 'SKIP', '未找到函数名')
            success = False

        # 优化图片生成函数
        optimized_function_name = outputs.get('image_generator_optimized_function_name', {}).get('value')
        if optimized_function_name:
            success &= self._validate_single_lambda(optimized_function_name, "优化图片生成Lambda")

        return success

    def _validate_single_lambda(self, function_name: str, test_name: str) -> bool:
        """验证单个Lambda函数"""
        start_time = time.time()
        try:
            # 获取函数配置
            response = self.lambda_client.get_function(FunctionName=function_name)
            config = response['Configuration']

            # 检查函数状态
            state = config.get('State', 'Unknown')
            if state != 'Active':
                self.add_test_result(
                    test_name,
                    'WARNING',
                    f'函数状态: {state}',
                    time.time() - start_time
                )
                return False

            # 检查配置
            runtime = config.get('Runtime')
            timeout = config.get('Timeout')
            memory = config.get('MemorySize')

            self.add_test_result(
                test_name,
                'PASS',
                f'状态: {state}, 运行时: {runtime}, 超时: {timeout}s, 内存: {memory}MB',
                time.time() - start_time
            )
            return True

        except ClientError as e:
            self.add_test_result(
                test_name,
                'FAIL',
                f'函数验证失败: {str(e)}',
                time.time() - start_time
            )
            return False

    def validate_s3_bucket(self, outputs: Dict[str, Any]) -> bool:
        """验证S3存储桶"""
        start_time = time.time()

        # 从输出或推断获取桶名
        bucket_name = outputs.get('presentations_bucket_name', {}).get('value')
        if not bucket_name:
            bucket_name = outputs.get('s3_bucket_name', {}).get('value')

        if not bucket_name:
            self.add_test_result('S3存储桶验证', 'SKIP', '未找到存储桶名')
            return False

        try:
            # 检查桶是否存在
            self.s3_client.head_bucket(Bucket=bucket_name)

            # 检查桶配置
            versioning = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
            encryption = self.s3_client.get_bucket_encryption(Bucket=bucket_name)

            version_status = versioning.get('Status', 'Disabled')
            encryption_rules = len(encryption.get('ServerSideEncryptionConfiguration', {}).get('Rules', []))

            self.add_test_result(
                'S3存储桶验证',
                'PASS',
                f'桶: {bucket_name}, 版本控制: {version_status}, 加密规则: {encryption_rules}个',
                time.time() - start_time
            )
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            self.add_test_result(
                'S3存储桶验证',
                'FAIL',
                f'桶验证失败: {error_code}',
                time.time() - start_time
            )
            return False

    def validate_dynamodb_table(self, outputs: Dict[str, Any]) -> bool:
        """验证DynamoDB表"""
        start_time = time.time()

        # 从输出获取表名
        table_name = outputs.get('presentations_table_name', {}).get('value')
        if not table_name:
            table_name = outputs.get('dynamodb_table_name', {}).get('value')

        if not table_name:
            self.add_test_result('DynamoDB表验证', 'SKIP', '未找到表名')
            return False

        try:
            # 检查表状态
            response = self.dynamodb_client.describe_table(TableName=table_name)
            table_status = response['Table']['TableStatus']

            if table_status != 'ACTIVE':
                self.add_test_result(
                    'DynamoDB表验证',
                    'WARNING',
                    f'表状态: {table_status}',
                    time.time() - start_time
                )
                return False

            # 获取表信息
            billing_mode = response['Table']['BillingModeSummary']['BillingMode']
            item_count = response['Table']['ItemCount']

            self.add_test_result(
                'DynamoDB表验证',
                'PASS',
                f'表: {table_name}, 状态: {table_status}, 计费: {billing_mode}, 项目数: {item_count}',
                time.time() - start_time
            )
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            self.add_test_result(
                'DynamoDB表验证',
                'FAIL',
                f'表验证失败: {error_code}',
                time.time() - start_time
            )
            return False

    def test_lambda_function_direct(self, function_name: str) -> bool:
        """直接测试Lambda函数"""
        start_time = time.time()

        test_payload = {
            'slide_content': {
                'title': '验证测试',
                'content': ['这是一个部署验证测试']
            },
            'target_audience': 'business'
        }

        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_payload)
            )

            # 解析响应
            payload = json.loads(response['Payload'].read())
            status_code = payload.get('statusCode', 500)

            if status_code == 200:
                body = json.loads(payload.get('body', '{}'))
                if body.get('success'):
                    # 验证返回的图片数据
                    image_data = body.get('image_data')
                    if image_data:
                        # 验证base64图片数据
                        try:
                            decoded_data = base64.b64decode(image_data)
                            if len(decoded_data) > 100:  # 简单验证
                                self.add_test_result(
                                    'Lambda函数直接调用测试',
                                    'PASS',
                                    f'成功生成图片，大小: {len(decoded_data)} 字节',
                                    time.time() - start_time
                                )
                                return True
                        except Exception:
                            pass

                self.add_test_result(
                    'Lambda函数直接调用测试',
                    'WARNING',
                    f'函数返回成功但图片数据验证失败',
                    time.time() - start_time
                )
                return False
            else:
                error_msg = json.loads(payload.get('body', '{}')).get('message', '未知错误')
                self.add_test_result(
                    'Lambda函数直接调用测试',
                    'FAIL',
                    f'函数返回错误 ({status_code}): {error_msg}',
                    time.time() - start_time
                )
                return False

        except Exception as e:
            self.add_test_result(
                'Lambda函数直接调用测试',
                'FAIL',
                f'调用失败: {str(e)}',
                time.time() - start_time
            )
            return False

    def test_lambda_function_url(self, function_url: str) -> bool:
        """通过函数URL测试Lambda"""
        start_time = time.time()

        test_payload = {
            'slide_content': {
                'title': 'URL验证测试',
                'content': ['这是一个函数URL验证测试']
            }
        }

        try:
            response = requests.post(
                function_url,
                json=test_payload,
                timeout=60,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('image_data'):
                    self.add_test_result(
                        'Lambda函数URL测试',
                        'PASS',
                        f'URL响应正常，生成时间: {data.get("generation_time", 0):.2f}s',
                        time.time() - start_time
                    )
                    return True
                else:
                    self.add_test_result(
                        'Lambda函数URL测试',
                        'WARNING',
                        'URL响应但数据格式异常',
                        time.time() - start_time
                    )
                    return False
            else:
                self.add_test_result(
                    'Lambda函数URL测试',
                    'FAIL',
                    f'URL返回错误: {response.status_code}',
                    time.time() - start_time
                )
                return False

        except Exception as e:
            self.add_test_result(
                'Lambda函数URL测试',
                'FAIL',
                f'URL调用失败: {str(e)}',
                time.time() - start_time
            )
            return False

    def validate_monitoring(self, outputs: Dict[str, Any]) -> bool:
        """验证监控配置"""
        start_time = time.time()

        try:
            # 检查CloudWatch告警
            alarms = self.cloudwatch_client.describe_alarms(
                AlarmNamePrefix=f'ai-ppt-assistant-image-generator-{self.environment}'
            )

            alarm_count = len(alarms['MetricAlarms'])

            # 检查仪表板
            dashboard_name = f'ai-ppt-assistant-image-processing-{self.environment}'
            try:
                self.cloudwatch_client.get_dashboard(DashboardName=dashboard_name)
                dashboard_exists = True
            except ClientError:
                dashboard_exists = False

            status = 'PASS' if alarm_count > 0 and dashboard_exists else 'WARNING'
            self.add_test_result(
                '监控配置验证',
                status,
                f'告警数: {alarm_count}, 仪表板: {"存在" if dashboard_exists else "不存在"}',
                time.time() - start_time
            )

            return status == 'PASS'

        except Exception as e:
            self.add_test_result(
                '监控配置验证',
                'FAIL',
                f'监控验证失败: {str(e)}',
                time.time() - start_time
            )
            return False

    def run_full_validation(self) -> Dict[str, Any]:
        """运行完整验证"""
        logger.info("开始部署验证...")

        # 验证AWS凭证
        if not self.validate_aws_credentials():
            logger.error("AWS凭证验证失败，终止验证")
            return self.validation_results

        # 获取Terraform输出
        outputs = self.get_terraform_outputs()

        # 验证核心组件
        self.validate_lambda_functions(outputs)
        self.validate_s3_bucket(outputs)
        self.validate_dynamodb_table(outputs)
        self.validate_monitoring(outputs)

        # 功能测试
        function_name = outputs.get('image_generator_function_name', {}).get('value')
        if function_name:
            self.test_lambda_function_direct(function_name)

        function_url = outputs.get('image_generator_function_url', {}).get('value')
        if function_url:
            self.test_lambda_function_url(function_url)

        # 统计结果
        total_tests = len(self.validation_results['tests'])
        passed_tests = sum(1 for test in self.validation_results['tests'] if test['status'] == 'PASS')
        failed_tests = sum(1 for test in self.validation_results['tests'] if test['status'] == 'FAIL')

        self.validation_results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': round((passed_tests / total_tests * 100) if total_tests > 0 else 0, 1)
        }

        return self.validation_results

    def save_results(self, output_file: str):
        """保存验证结果"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, indent=2, ensure_ascii=False)

        logger.info(f"验证结果已保存到: {output_file}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI PPT Assistant 部署验证')
    parser.add_argument('-e', '--environment', default='dev', help='环境名称')
    parser.add_argument('-o', '--output', default='validation_report.json', help='输出文件')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 运行验证
    validator = DeploymentValidator(args.environment)
    results = validator.run_full_validation()

    # 保存结果
    validator.save_results(args.output)

    # 显示摘要
    summary = results.get('summary', {})
    logger.info(f"验证完成: {summary.get('passed_tests', 0)}/{summary.get('total_tests', 0)} 通过 "
                f"(成功率: {summary.get('success_rate', 0)}%)")

    # 根据结果设置退出码
    if summary.get('failed_tests', 0) > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == '__main__':
    main()