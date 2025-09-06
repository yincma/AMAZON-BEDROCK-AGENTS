#!/usr/bin/env python3
"""
AI PPT Assistant - 部署验证脚本
验证新配置系统部署是否成功

验证内容：
1. AWS连接和权限
2. Lambda函数状态
3. Lambda层配置
4. 配置系统运行状态
5. 端到端功能测试
"""

import os
import sys
import json
import boto3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_success(message: str):
    """打印成功消息"""
    print(f"✅ {message}")

def print_error(message: str):
    """打印错误消息"""
    print(f"❌ {message}")

def print_warning(message: str):
    """打印警告消息"""
    print(f"⚠️  {message}")

def print_info(message: str):
    """打印信息消息"""
    print(f"ℹ️  {message}")

class DeploymentVerifier:
    """部署验证器"""
    
    def __init__(self):
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self.environment = os.environ.get('ENVIRONMENT', 'dev')
        self.project_name = "ai-ppt-assistant"
        
        # AWS客户端
        self.lambda_client = None
        self.s3_client = None
        self.dynamodb_client = None
        self.bedrock_client = None
        
        self._init_aws_clients()
    
    def _init_aws_clients(self):
        """初始化AWS客户端"""
        try:
            self.lambda_client = boto3.client('lambda', region_name=self.aws_region)
            self.s3_client = boto3.client('s3', region_name=self.aws_region)
            self.dynamodb_client = boto3.client('dynamodb', region_name=self.aws_region)
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.aws_region)
            print_success(f"AWS客户端初始化成功 (区域: {self.aws_region})")
        except Exception as e:
            print_error(f"AWS客户端初始化失败: {e}")
            sys.exit(1)
    
    def verify_aws_connectivity(self) -> bool:
        """验证AWS连接和权限"""
        print_header("AWS连接和权限验证")
        
        try:
            # 验证STS身份
            sts_client = boto3.client('sts', region_name=self.aws_region)
            identity = sts_client.get_caller_identity()
            print_success(f"AWS身份验证成功")
            print_info(f"账户ID: {identity.get('Account')}")
            print_info(f"用户ARN: {identity.get('Arn')}")
            
            return True
            
        except Exception as e:
            print_error(f"AWS连接验证失败: {e}")
            return False
    
    def verify_lambda_functions(self) -> bool:
        """验证Lambda函数状态"""
        print_header("Lambda函数验证")
        
        # 预期的Lambda函数
        expected_functions = [
            f"{self.project_name}-create-outline",
            f"{self.project_name}-generate-content",
            f"{self.project_name}-generate-image",
            f"{self.project_name}-compile-pptx",
            f"{self.project_name}-find-image",
            f"{self.project_name}-generate-speaker-notes"
        ]
        
        all_functions_ok = True
        
        for function_name in expected_functions:
            try:
                response = self.lambda_client.get_function(FunctionName=function_name)
                
                config = response['Configuration']
                print_success(f"函数 {function_name} 存在")
                print_info(f"  运行时: {config['Runtime']}")
                print_info(f"  内存: {config['MemorySize']}MB")
                print_info(f"  超时: {config['Timeout']}秒")
                print_info(f"  状态: {config['State']}")
                
                # 检查环境变量
                env_vars = config.get('Environment', {}).get('Variables', {})
                if 'ENVIRONMENT' in env_vars:
                    print_info(f"  环境: {env_vars['ENVIRONMENT']}")
                
                # 检查Lambda层
                layers = config.get('Layers', [])
                if layers:
                    print_info(f"  Lambda层: {len(layers)} 个")
                    for layer in layers:
                        layer_name = layer['Arn'].split(':')[-2]
                        print_info(f"    - {layer_name}")
                else:
                    print_warning(f"  未配置Lambda层")
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                print_error(f"函数 {function_name} 不存在")
                all_functions_ok = False
            except Exception as e:
                print_error(f"验证函数 {function_name} 失败: {e}")
                all_functions_ok = False
        
        return all_functions_ok
    
    def verify_lambda_layers(self) -> bool:
        """验证Lambda层"""
        print_header("Lambda层验证")
        
        try:
            # 查找配置层
            layers = self.lambda_client.list_layers()
            config_layer_found = False
            
            for layer in layers.get('Layers', []):
                layer_name = layer['LayerName']
                if 'config' in layer_name.lower() or self.project_name in layer_name:
                    config_layer_found = True
                    print_success(f"找到配置层: {layer_name}")
                    
                    # 获取层的详细信息
                    latest_version = layer['LatestMatchingVersion']
                    print_info(f"  版本: {latest_version['Version']}")
                    print_info(f"  运行时: {latest_version.get('CompatibleRuntimes', [])}")
                    print_info(f"  创建时间: {latest_version['CreatedDate']}")
            
            if not config_layer_found:
                print_warning("未找到配置层，可能需要先部署配置层")
                return False
            
            return True
            
        except Exception as e:
            print_error(f"Lambda层验证失败: {e}")
            return False
    
    def verify_configuration_system(self) -> bool:
        """验证配置系统"""
        print_header("配置系统验证")
        
        try:
            # 添加lambdas目录到路径
            lambdas_path = Path(__file__).parent / "lambdas"
            if str(lambdas_path) not in sys.path:
                sys.path.insert(0, str(lambdas_path))
            
            from utils.enhanced_config_manager import get_enhanced_config_manager
            
            # 测试配置管理器
            config_manager = get_enhanced_config_manager(self.environment)
            print_success(f"配置管理器初始化成功 (环境: {self.environment})")
            
            # 验证关键配置
            aws_config = config_manager.get_aws_config()
            print_info(f"AWS区域: {aws_config.region}")
            
            s3_config = config_manager.get_s3_config()
            if s3_config.bucket:
                print_info(f"S3存储桶: {s3_config.bucket}")
            else:
                print_warning("S3存储桶未配置")
            
            dynamodb_config = config_manager.get_dynamodb_config()
            if dynamodb_config.table:
                print_info(f"DynamoDB表: {dynamodb_config.table}")
            else:
                print_warning("DynamoDB表未配置")
            
            bedrock_config = config_manager.get_bedrock_config()
            print_info(f"Bedrock模型: {bedrock_config.model_id}")
            
            # 运行配置验证
            validation_report = config_manager.validate_configuration()
            print_success(f"配置验证完成")
            print_info(f"  有效配置: {len(validation_report['valid'])} 项")
            
            if validation_report['warnings']:
                print_warning(f"  警告: {len(validation_report['warnings'])} 项")
                for warning in validation_report['warnings']:
                    print_info(f"    - {warning}")
            
            if validation_report['errors']:
                print_error(f"  错误: {len(validation_report['errors'])} 项")
                for error in validation_report['errors']:
                    print_info(f"    - {error}")
                return False
            
            return True
            
        except Exception as e:
            print_error(f"配置系统验证失败: {e}")
            return False
    
    def verify_aws_resources(self) -> bool:
        """验证AWS资源"""
        print_header("AWS资源验证")
        
        all_resources_ok = True
        
        # 验证S3存储桶
        try:
            # 从配置获取存储桶名称
            from utils.enhanced_config_manager import get_enhanced_config_manager
            config_manager = get_enhanced_config_manager(self.environment)
            s3_config = config_manager.get_s3_config()
            
            if s3_config.bucket:
                try:
                    self.s3_client.head_bucket(Bucket=s3_config.bucket)
                    print_success(f"S3存储桶存在: {s3_config.bucket}")
                except Exception as e:
                    print_warning(f"S3存储桶不存在或无权限: {s3_config.bucket}")
            
            # 验证DynamoDB表
            dynamodb_config = config_manager.get_dynamodb_config()
            if dynamodb_config.table:
                try:
                    self.dynamodb_client.describe_table(TableName=dynamodb_config.table)
                    print_success(f"DynamoDB表存在: {dynamodb_config.table}")
                except Exception as e:
                    print_warning(f"DynamoDB表不存在或无权限: {dynamodb_config.table}")
            
        except Exception as e:
            print_error(f"AWS资源验证失败: {e}")
            all_resources_ok = False
        
        return all_resources_ok
    
    def test_lambda_function(self, function_name: str, test_payload: Dict[str, Any]) -> bool:
        """测试Lambda函数"""
        try:
            print_info(f"测试函数: {function_name}")
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_payload)
            )
            
            if response['StatusCode'] == 200:
                payload = json.loads(response['Payload'].read())
                
                # 检查是否有错误
                if 'errorMessage' in payload:
                    print_warning(f"  函数返回错误: {payload['errorMessage']}")
                    return False
                else:
                    print_success(f"  函数执行成功")
                    return True
            else:
                print_error(f"  函数调用失败，状态码: {response['StatusCode']}")
                return False
                
        except Exception as e:
            print_error(f"  测试函数失败: {e}")
            return False
    
    def verify_end_to_end_functionality(self) -> bool:
        """端到端功能测试"""
        print_header("端到端功能测试")
        
        # 测试创建大纲功能
        test_payload = {
            "topic": "测试主题：AI技术发展",
            "audience": "技术团队",
            "slides": 5
        }
        
        function_name = f"{self.project_name}-create-outline"
        
        try:
            result = self.test_lambda_function(function_name, test_payload)
            return result
        except Exception as e:
            print_error(f"端到端测试失败: {e}")
            return False
    
    def run_all_verifications(self) -> bool:
        """运行所有验证"""
        print(f"🔍 AI PPT Assistant - 部署验证")
        print(f"⏰ 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌍 AWS区域: {self.aws_region}")
        print(f"📋 环境: {self.environment}")
        
        verifications = [
            ("AWS连接", self.verify_aws_connectivity),
            ("配置系统", self.verify_configuration_system),
            ("Lambda层", self.verify_lambda_layers),
            ("Lambda函数", self.verify_lambda_functions),
            ("AWS资源", self.verify_aws_resources),
            ("端到端功能", self.verify_end_to_end_functionality)
        ]
        
        results = []
        
        for verification_name, verification_func in verifications:
            try:
                result = verification_func()
                results.append((verification_name, result))
            except Exception as e:
                print_error(f"{verification_name}验证异常: {e}")
                results.append((verification_name, False))
        
        # 打印验证结果摘要
        print("\n" + "="*60)
        print("📊 验证结果摘要")
        print("="*60)
        
        passed = 0
        total = len(results)
        
        for verification_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{verification_name:<20} {status}")
            if result:
                passed += 1
        
        print(f"\n📈 总体结果: {passed}/{total} 项验证通过")
        
        if passed == total:
            print("\n🎉 所有验证通过！部署成功！")
            print("\n📋 系统已就绪:")
            print(f"- 环境: {self.environment}")
            print(f"- 区域: {self.aws_region}")
            print("- 配置系统: ✅ 正常")
            print("- Lambda函数: ✅ 正常")
            print("- AWS资源: ✅ 正常")
            return True
        else:
            print(f"\n⚠️  有 {total - passed} 项验证失败，请检查部署")
            return False

def main():
    """主函数"""
    verifier = DeploymentVerifier()
    success = verifier.run_all_verifications()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()