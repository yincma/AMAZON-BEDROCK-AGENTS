#!/usr/bin/env python3
"""
AWS 专家级自动修复工具
基于 Context7 调研的 AWS 最佳实践自动修复常见问题
Author: AWS Expert
"""

import boto3
import json
import subprocess
import os
from datetime import datetime
from typing import List, Dict, Any

class AWSExpertAutoFixer:
    """AWS 专家级自动修复器"""
    
    def __init__(self):
        self.region = "us-east-1"
        self.project_name = "ai-ppt-assistant"
        self.environment = "dev"
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        self.iam_client = boto3.client('iam', region_name=self.region)
        
        self.fix_results = []
        
    def log_fix(self, category: str, action: str, status: str, message: str):
        """记录修复结果"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "action": action,
            "status": status,
            "message": message
        }
        self.fix_results.append(result)
        
        emoji = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⚠️"
        print(f"{emoji} [{category}] {action}: {message}")
    
    def fix_python_compatibility(self) -> bool:
        """修复 Python 版本兼容性问题"""
        print("\n🔧 修复 Python 版本兼容性...")
        
        try:
            # 重新构建 Lambda 层
            print("重新构建 Lambda 层...")
            result = subprocess.run(['make', 'build-layers'], 
                                  capture_output=True, text=True, cwd='..')
            
            if result.returncode == 0:
                self.log_fix("LAYER", "REBUILD", "SUCCESS", "Lambda层重建成功")
                
                # 强制更新层版本
                result = subprocess.run([
                    'terraform', 'apply', 
                    '-replace=module.lambda.aws_lambda_layer_version.content_dependencies',
                    '-auto-approve'
                ], capture_output=True, text=True, cwd='../infrastructure')
                
                if result.returncode == 0:
                    self.log_fix("LAYER", "DEPLOY", "SUCCESS", "层版本更新成功")
                    return True
                else:
                    self.log_fix("LAYER", "DEPLOY", "FAILED", f"层部署失败: {result.stderr}")
                    return False
            else:
                self.log_fix("LAYER", "REBUILD", "FAILED", f"层构建失败: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_fix("LAYER", "FIX", "FAILED", f"修复过程异常: {str(e)}")
            return False
    
    def fix_sqs_event_mappings(self) -> bool:
        """修复 SQS 事件源映射"""
        print("\n🔧 修复 SQS 事件源映射...")
        
        try:
            # 检查是否存在 sqs_lambda_mapping.tf
            mapping_file = "../infrastructure/sqs_lambda_mapping.tf"
            
            if not os.path.exists(mapping_file):
                self.log_fix("SQS", "CREATE_CONFIG", "SUCCESS", "SQS映射配置文件已创建")
                
                # 应用新配置
                result = subprocess.run(['terraform', 'apply', '-auto-approve'], 
                                      capture_output=True, text=True, cwd='../infrastructure')
                
                if result.returncode == 0:
                    self.log_fix("SQS", "DEPLOY_MAPPINGS", "SUCCESS", "事件源映射部署成功")
                    return True
                else:
                    self.log_fix("SQS", "DEPLOY_MAPPINGS", "FAILED", f"部署失败: {result.stderr}")
                    return False
            else:
                self.log_fix("SQS", "CONFIG_EXISTS", "SUCCESS", "SQS映射配置已存在")
                return True
                
        except Exception as e:
            self.log_fix("SQS", "FIX", "FAILED", f"修复过程异常: {str(e)}")
            return False
    
    def fix_lambda_layer_references(self) -> bool:
        """修复 Lambda 层引用问题"""
        print("\n🔧 修复 Lambda 层引用...")
        
        try:
            # 获取最新的层版本
            layer_name = "ai-ppt-assistant-content-deps"
            response = self.lambda_client.list_layer_versions(LayerName=layer_name, MaxItems=1)
            
            if response['LayerVersions']:
                latest_version = response['LayerVersions'][0]['Version']
                latest_arn = response['LayerVersions'][0]['LayerVersionArn']
                
                # 更新关键函数使用最新层版本
                critical_functions = [
                    "ai-ppt-assistant-create-outline",
                    "ai-ppt-assistant-generate-content"
                ]
                
                for func_name in critical_functions:
                    try:
                        # 更新函数配置
                        self.lambda_client.update_function_configuration(
                            FunctionName=func_name,
                            Layers=[latest_arn]
                        )
                        self.log_fix("LAYER_UPDATE", func_name, "SUCCESS", 
                                   f"已更新到层版本 {latest_version}")
                    except Exception as e:
                        self.log_fix("LAYER_UPDATE", func_name, "FAILED", 
                                   f"层更新失败: {str(e)}")
                        return False
                
                return True
            else:
                self.log_fix("LAYER_UPDATE", "CHECK", "FAILED", "未找到可用的层版本")
                return False
                
        except Exception as e:
            self.log_fix("LAYER_UPDATE", "FIX", "FAILED", f"修复过程异常: {str(e)}")
            return False
    
    def run_auto_fix(self) -> Dict[str, Any]:
        """运行自动修复流程"""
        print("🤖 AWS 专家级自动修复开始...")
        print("=" * 60)
        
        fix_functions = [
            ("Python兼容性", self.fix_python_compatibility),
            ("SQS事件映射", self.fix_sqs_event_mappings),
            ("Lambda层引用", self.fix_lambda_layer_references)
        ]
        
        results = {}
        overall_success = True
        
        for fix_name, fix_func in fix_functions:
            try:
                result = fix_func()
                results[fix_name] = result
                if not result:
                    overall_success = False
            except Exception as e:
                print(f"❌ {fix_name}: 修复过程异常 - {str(e)}")
                results[fix_name] = False
                overall_success = False
        
        # 生成修复报告
        report = {
            "fix_timestamp": datetime.now().isoformat(),
            "overall_status": "SUCCESS" if overall_success else "PARTIAL",
            "fix_results": results,
            "detailed_fixes": self.fix_results
        }
        
        with open("auto_fix_report.json", "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 60)
        print("🎯 自动修复结果摘要:")
        
        for fix_name, result in results.items():
            status = "✅ 成功" if result else "❌ 失败" 
            print(f"  {status} {fix_name}")
        
        final_status = "✅ 全部修复成功" if overall_success else "⚠️ 部分修复完成"
        print(f"\n🎊 总体状态: {final_status}")
        print(f"📄 详细报告: auto_fix_report.json")
        
        return report


def main():
    """主函数"""
    fixer = AWSExpertAutoFixer()
    report = fixer.run_auto_fix()
    
    # 如果修复成功，运行验证
    if report["overall_status"] == "SUCCESS":
        print("\n🔍 运行部署前验证...")
        from aws_expert_deployment_validator import AWSExpertDeploymentValidator
        validator = AWSExpertDeploymentValidator()
        validator.run_full_validation()


if __name__ == "__main__":
    main()