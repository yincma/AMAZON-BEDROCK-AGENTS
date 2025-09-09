#!/usr/bin/env python3
"""
AWS 专家级部署验证器
确保部署前所有关键配置正确，预防生产问题
Author: AWS Expert (基于 Context7 调研的最佳实践)
"""

import boto3
import json
import sys
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional

class AWSExpertDeploymentValidator:
    """AWS 专家级部署验证器"""
    
    def __init__(self):
        self.region = "us-east-1"
        self.project_name = "ai-ppt-assistant"
        self.environment = "dev"
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        self.iam_client = boto3.client('iam', region_name=self.region)
        self.sqs_client = boto3.client('sqs', region_name=self.region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=self.region)
        
        self.validation_results = []
        
    def log_result(self, category: str, item: str, status: str, message: str, details: Any = None):
        """记录验证结果"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "item": item,
            "status": status,
            "message": message,
            "details": details
        }
        self.validation_results.append(result)
        
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{emoji} [{category}] {item}: {message}")
        
    def validate_lambda_layer_compatibility(self) -> bool:
        """验证 Lambda 层 Python 版本兼容性"""
        print("\n🔍 验证 Lambda 层兼容性...")
        
        try:
            # 检查层版本
            layers_to_check = [
                "ai-ppt-assistant-content-deps",
                "ai-ppt-assistant-minimal-deps", 
                "ai-ppt-assistant-shared-deps"
            ]
            
            all_compatible = True
            
            for layer_name in layers_to_check:
                try:
                    response = self.lambda_client.list_layer_versions(LayerName=layer_name, MaxItems=1)
                    if response['LayerVersions']:
                        layer_arn = response['LayerVersions'][0]['LayerVersionArn']
                        compatible_runtimes = response['LayerVersions'][0]['CompatibleRuntimes']
                        
                        if 'python3.12' in compatible_runtimes:
                            self.log_result("LAYER", layer_name, "PASS", 
                                          f"Python 3.12 兼容 (ARN: {layer_arn})")
                        else:
                            self.log_result("LAYER", layer_name, "FAIL", 
                                          f"不兼容 Python 3.12. 兼容运行时: {compatible_runtimes}")
                            all_compatible = False
                except Exception as e:
                    self.log_result("LAYER", layer_name, "FAIL", f"层不存在或无法访问: {str(e)}")
                    all_compatible = False
                    
            return all_compatible
            
        except Exception as e:
            self.log_result("LAYER", "VALIDATION", "FAIL", f"层验证失败: {str(e)}")
            return False
    
    def validate_sqs_event_source_mappings(self) -> bool:
        """验证 SQS 事件源映射配置"""
        print("\n🔍 验证 SQS 事件源映射...")
        
        try:
            # 获取所有事件源映射
            response = self.lambda_client.list_event_source_mappings()
            
            sqs_mappings = [
                mapping for mapping in response['EventSourceMappings']
                if 'sqs' in mapping.get('EventSourceArn', '') 
                and self.project_name in mapping.get('EventSourceArn', '')
            ]
            
            if len(sqs_mappings) >= 2:  # 至少需要2个映射
                for mapping in sqs_mappings:
                    function_name = mapping.get('FunctionName', 'Unknown')
                    state = mapping.get('State', 'Unknown')
                    
                    if state == 'Enabled':
                        self.log_result("SQS_MAPPING", function_name, "PASS", 
                                      f"映射状态: {state}")
                    else:
                        self.log_result("SQS_MAPPING", function_name, "FAIL", 
                                      f"映射状态: {state}")
                        return False
                return True
            else:
                self.log_result("SQS_MAPPING", "COUNT", "FAIL", 
                              f"事件源映射不足: {len(sqs_mappings)} (需要至少2个)")
                return False
                
        except Exception as e:
            self.log_result("SQS_MAPPING", "VALIDATION", "FAIL", f"映射验证失败: {str(e)}")
            return False
    
    def validate_iam_permissions(self) -> bool:
        """验证 IAM 权限配置"""
        print("\n🔍 验证 IAM 权限配置...")
        
        try:
            # 检查 Lambda 执行角色
            role_name = f"{self.project_name}-lambda-execution-role"
            
            try:
                role = self.iam_client.get_role(RoleName=role_name)
                self.log_result("IAM", role_name, "PASS", "Lambda执行角色存在")
                
                # 检查信任策略
                assume_policy = role['Role']['AssumeRolePolicyDocument']
                if 'lambda.amazonaws.com' in str(assume_policy):
                    self.log_result("IAM", "TRUST_POLICY", "PASS", "Lambda信任策略正确")
                else:
                    self.log_result("IAM", "TRUST_POLICY", "FAIL", "Lambda信任策略缺失")
                    return False
                    
            except self.iam_client.exceptions.NoSuchEntityException:
                self.log_result("IAM", role_name, "FAIL", "Lambda执行角色不存在")
                return False
                
            return True
            
        except Exception as e:
            self.log_result("IAM", "VALIDATION", "FAIL", f"IAM验证失败: {str(e)}")
            return False
    
    def validate_infrastructure_state(self) -> bool:
        """验证基础设施状态一致性"""
        print("\n🔍 验证基础设施状态...")
        
        try:
            # 检查 DynamoDB 表
            required_tables = [
                f"{self.project_name}-{self.environment}-tasks",
                f"{self.project_name}-{self.environment}-sessions", 
                f"{self.project_name}-{self.environment}-checkpoints"
            ]
            
            for table_name in required_tables:
                try:
                    response = self.dynamodb_client.describe_table(TableName=table_name)
                    status = response['Table']['TableStatus']
                    
                    if status == 'ACTIVE':
                        self.log_result("DYNAMODB", table_name, "PASS", f"表状态: {status}")
                    else:
                        self.log_result("DYNAMODB", table_name, "FAIL", f"表状态: {status}")
                        return False
                        
                except self.dynamodb_client.exceptions.ResourceNotFoundException:
                    self.log_result("DYNAMODB", table_name, "FAIL", "表不存在")
                    return False
            
            # 检查 SQS 队列
            queue_url = f"https://sqs.{self.region}.amazonaws.com/375004070918/{self.project_name}-{self.environment}-tasks"
            try:
                self.sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['ApproximateNumberOfMessages'])
                self.log_result("SQS", "task_queue", "PASS", "队列可访问")
            except Exception:
                self.log_result("SQS", "task_queue", "FAIL", "队列不存在或无法访问")
                return False
                
            return True
            
        except Exception as e:
            self.log_result("INFRASTRUCTURE", "VALIDATION", "FAIL", f"基础设施验证失败: {str(e)}")
            return False
    
    def validate_lambda_functions(self) -> bool:
        """验证 Lambda 函数状态"""
        print("\n🔍 验证 Lambda 函数状态...")
        
        try:
            # 获取所有项目相关的 Lambda 函数
            response = self.lambda_client.list_functions()
            project_functions = [
                func for func in response['Functions']
                if self.project_name in func['FunctionName']
            ]
            
            if len(project_functions) < 10:  # 预期至少10个函数
                self.log_result("LAMBDA", "COUNT", "FAIL", 
                              f"函数数量不足: {len(project_functions)} (预期至少10个)")
                return False
            
            # 检查关键函数
            critical_functions = [
                "ai-ppt-assistant-api-generate-presentation",
                "ai-ppt-assistant-generate-content", 
                "ai-ppt-assistant-create-outline"
            ]
            
            all_healthy = True
            for func_name in critical_functions:
                try:
                    func_config = self.lambda_client.get_function(FunctionName=func_name)
                    state = func_config['Configuration']['State']
                    runtime = func_config['Configuration']['Runtime']
                    
                    if state == 'Active' and runtime == 'python3.12':
                        self.log_result("LAMBDA", func_name, "PASS", 
                                      f"状态: {state}, 运行时: {runtime}")
                    else:
                        self.log_result("LAMBDA", func_name, "FAIL", 
                                      f"状态: {state}, 运行时: {runtime}")
                        all_healthy = False
                        
                except Exception as e:
                    self.log_result("LAMBDA", func_name, "FAIL", f"函数不存在: {str(e)}")
                    all_healthy = False
            
            return all_healthy
            
        except Exception as e:
            self.log_result("LAMBDA", "VALIDATION", "FAIL", f"Lambda验证失败: {str(e)}")
            return False
    
    def validate_terraform_state(self) -> bool:
        """验证 Terraform 状态一致性"""
        print("\n🔍 验证 Terraform 状态...")
        
        try:
            # 检查 Terraform 配置文件
            tf_files = ['main.tf', 'variables.tf', 'outputs.tf']
            missing_files = []
            
            for tf_file in tf_files:
                if not os.path.exists(tf_file):
                    missing_files.append(tf_file)
            
            if missing_files:
                self.log_result("TERRAFORM", "CONFIG_FILES", "FAIL", 
                              f"缺少配置文件: {missing_files}")
                return False
            else:
                self.log_result("TERRAFORM", "CONFIG_FILES", "PASS", "所有配置文件存在")
            
            # 运行 Terraform validate
            result = subprocess.run(['terraform', 'validate'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_result("TERRAFORM", "VALIDATE", "PASS", "配置验证通过")
                return True
            else:
                self.log_result("TERRAFORM", "VALIDATE", "FAIL", 
                              f"配置验证失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_result("TERRAFORM", "VALIDATION", "FAIL", f"Terraform验证失败: {str(e)}")
            return False
    
    def run_full_validation(self) -> Dict[str, Any]:
        """运行完整的部署前验证"""
        print("🚀 AWS 专家级部署验证开始...")
        print("=" * 60)
        
        validation_checks = [
            ("Lambda层兼容性", self.validate_lambda_layer_compatibility),
            ("SQS事件源映射", self.validate_sqs_event_source_mappings),  
            ("IAM权限配置", self.validate_iam_permissions),
            ("基础设施状态", self.validate_infrastructure_state),
            ("Lambda函数状态", self.validate_lambda_functions),
            ("Terraform状态", self.validate_terraform_state)
        ]
        
        results = {}
        all_passed = True
        
        for check_name, check_func in validation_checks:
            try:
                result = check_func()
                results[check_name] = result
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ {check_name}: 验证过程异常 - {str(e)}")
                results[check_name] = False
                all_passed = False
        
        print("\n" + "=" * 60)
        print("🎯 验证结果摘要:")
        
        for check_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {status} {check_name}")
        
        print(f"\n🎊 总体结果: {'✅ 所有验证通过' if all_passed else '❌ 部分验证失败'}")
        
        # 保存详细结果
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "overall_status": "PASS" if all_passed else "FAIL",
            "summary": results,
            "detailed_results": self.validation_results,
            "recommendations": self.generate_recommendations(results)
        }
        
        with open("deployment_validation_report.json", "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📄 详细报告已保存到: deployment_validation_report.json")
        
        return report
    
    def generate_recommendations(self, results: Dict[str, bool]) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        if not results.get("Lambda层兼容性", True):
            recommendations.append("重新构建 Lambda 层，确保 Python 3.12 兼容性")
            
        if not results.get("SQS事件源映射", True):
            recommendations.append("创建或修复 SQS 到 Lambda 的事件源映射")
            
        if not results.get("IAM权限配置", True):
            recommendations.append("更新 IAM 角色和策略，确保权限完整")
            
        if not results.get("基础设施状态", True):
            recommendations.append("修复 DynamoDB 表或 SQS 队列配置")
            
        if not results.get("Lambda函数状态", True):
            recommendations.append("重新部署 Lambda 函数或检查配置")
            
        if not results.get("Terraform状态", True):
            recommendations.append("修复 Terraform 配置文件或运行 terraform init")
        
        if not recommendations:
            recommendations.append("系统状态良好，可以安全部署")
            
        return recommendations


def main():
    """主函数"""
    validator = AWSExpertDeploymentValidator()
    
    # 运行完整验证
    report = validator.run_full_validation()
    
    # 根据结果设置退出码
    exit_code = 0 if report["overall_status"] == "PASS" else 1
    
    print(f"\n🔚 验证完成，退出码: {exit_code}")
    
    # 显示建议
    if report["recommendations"]:
        print("\n📋 修复建议:")
        for i, rec in enumerate(report["recommendations"], 1):
            print(f"  {i}. {rec}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()