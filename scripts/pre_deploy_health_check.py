#!/usr/bin/env python3
"""
AI PPT Assistant - 预部署健康检查脚本
在部署前检查常见问题，防止部署失败

使用方法：
python3 scripts/pre_deploy_health_check.py
"""

import subprocess
import json
import sys
import os
from datetime import datetime

def run_command(command, description="", capture_output=True):
    """执行命令并返回结果"""
    print(f"🔍 检查: {description}")
    try:
        if capture_output:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(command, shell=True, timeout=30)
            return result.returncode == 0, "", ""
    except subprocess.TimeoutExpired:
        print("⏰ 命令执行超时")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ 命令执行错误: {e}")
        return False, "", str(e)

def check_terraform_state():
    """检查Terraform状态是否同步"""
    print("\n📋 检查Terraform状态同步")
    
    # 检查terraform状态文件是否存在
    if not os.path.exists("infrastructure/terraform.tfstate"):
        print("❌ terraform.tfstate文件不存在")
        return False
    
    # 检查terraform validate
    os.chdir("infrastructure")
    success, stdout, stderr = run_command("terraform validate", "Terraform配置验证")
    if not success:
        print(f"❌ Terraform配置验证失败: {stderr}")
        os.chdir("..")
        return False
    
    print("✅ Terraform配置验证通过")
    os.chdir("..")
    return True

def check_duplicate_lambda_functions():
    """检查重复的Lambda函数"""
    print("\n📋 检查重复的Lambda函数")
    
    success, stdout, stderr = run_command(
        "aws lambda list-functions --region us-east-1 --query 'Functions[?contains(FunctionName, `dev`)].FunctionName' --output json",
        "检查dev-*前缀的Lambda函数"
    )
    
    if success:
        try:
            functions = json.loads(stdout)
            if functions:
                print(f"⚠️  发现{len(functions)}个dev-*前缀的Lambda函数:")
                for func in functions:
                    print(f"  - {func}")
                return False
            else:
                print("✅ 未发现重复的dev-*Lambda函数")
                return True
        except json.JSONDecodeError:
            print("❌ 无法解析AWS CLI响应")
            return False
    else:
        print(f"❌ AWS CLI命令失败: {stderr}")
        return False

def check_api_gateway_stages():
    """检查API Gateway stages"""
    print("\n📋 检查API Gateway配置")
    
    # 首先获取API Gateway ID
    os.chdir("infrastructure")
    success, stdout, stderr = run_command(
        "terraform output -raw api_gateway_url 2>/dev/null || echo 'NO_OUTPUT'",
        "获取API Gateway URL"
    )
    
    if not success or "NO_OUTPUT" in stdout:
        print("⚠️  无法获取API Gateway URL，可能尚未部署")
        os.chdir("..")
        return False
    
    # 提取API Gateway ID
    try:
        api_url = stdout.strip().strip('"')
        if "execute-api" in api_url:
            api_id = api_url.split("//")[1].split(".")[0]
            
            # 检查stages
            success, stdout, stderr = run_command(
                f"aws apigateway get-stages --rest-api-id {api_id} --region us-east-1 --query 'item[].stageName' --output json",
                f"检查API Gateway {api_id} 的stages"
            )
            
            if success:
                stages = json.loads(stdout)
                if stages:
                    print(f"✅ API Gateway stages存在: {', '.join(stages)}")
                    os.chdir("..")
                    return True
                else:
                    print("❌ API Gateway没有可用的stages")
                    os.chdir("..")
                    return False
            else:
                print(f"❌ 无法检查API Gateway stages: {stderr}")
                os.chdir("..")
                return False
        else:
            print("❌ 无效的API Gateway URL格式")
            os.chdir("..")
            return False
    except Exception as e:
        print(f"❌ 解析API Gateway URL失败: {e}")
        os.chdir("..")
        return False

def check_sqs_lambda_mappings():
    """检查SQS Lambda事件源映射"""
    print("\n📋 检查SQS Lambda事件源映射配置")
    
    # 检查sqs_lambda_mapping.tf文件是否存在硬编码
    config_file = "infrastructure/sqs_lambda_mapping.tf"
    if not os.path.exists(config_file):
        print("⚠️  sqs_lambda_mapping.tf文件不存在")
        return True
    
    with open(config_file, 'r') as f:
        content = f.read()
        
    # 检查硬编码的函数名
    hardcoded_patterns = [
        '"ai-ppt-assistant-api-',
        '"ai-ppt-assistant-generate-',
        '"ai-ppt-assistant-create-',
    ]
    
    found_hardcoded = False
    for pattern in hardcoded_patterns:
        if pattern in content:
            print(f"❌ 发现硬编码函数名模式: {pattern}")
            found_hardcoded = True
    
    if found_hardcoded:
        print("❌ SQS映射配置包含硬编码函数名")
        return False
    else:
        print("✅ SQS映射配置使用模块引用")
        return True

def check_lambda_layers():
    """检查Lambda层是否存在"""
    print("\n📋 检查Lambda层")
    
    success, stdout, stderr = run_command(
        "aws lambda list-layers --region us-east-1 --query 'Layers[?contains(LayerName, `ai-ppt-assistant`)].LayerName' --output json",
        "检查AI PPT Assistant Lambda层"
    )
    
    if success:
        try:
            layers = json.loads(stdout)
            if layers and len(layers) >= 3:
                print(f"✅ 发现{len(layers)}个Lambda层: {', '.join(layers)}")
                return True
            else:
                print(f"⚠️  只发现{len(layers) if layers else 0}个Lambda层，预期至少3个")
                return False
        except json.JSONDecodeError:
            print("❌ 无法解析Lambda层响应")
            return False
    else:
        print(f"❌ 检查Lambda层失败: {stderr}")
        return False

def main():
    print("🔧 AI PPT Assistant - 预部署健康检查")
    print("=" * 60)
    print(f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 检查当前目录
    if not os.path.exists("infrastructure"):
        print("❌ 请在项目根目录运行此脚本")
        return 1
    
    checks = [
        ("Terraform状态", check_terraform_state),
        ("重复Lambda函数", check_duplicate_lambda_functions),
        ("API Gateway配置", check_api_gateway_stages),
        ("SQS Lambda映射", check_sqs_lambda_mappings),
        ("Lambda层", check_lambda_layers),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ 检查 {check_name} 时发生异常: {e}")
            results.append((check_name, False))
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📊 预部署检查结果")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{check_name}: {status}")
    
    print("-" * 40)
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有检查通过！可以安全地进行部署。")
        return 0
    else:
        print(f"\n⚠️  {total-passed} 个检查失败，建议修复后再部署。")
        return 1

if __name__ == "__main__":
    sys.exit(main())