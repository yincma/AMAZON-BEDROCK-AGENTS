#!/usr/bin/env python3
"""
AI PPT Assistant 回归测试脚本
验证修复后的系统功能
"""

import json
import time
import requests
import boto3
from datetime import datetime

def get_ssm_parameter(parameter_name):
    """从SSM获取参数值"""
    ssm = boto3.client('ssm', region_name='us-east-1')
    try:
        response = ssm.get_parameter(
            Name=parameter_name,
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except Exception as e:
        print(f"⚠️ 无法获取参数 {parameter_name}: {e}")
        return None

def test_api_endpoints():
    """测试API端点"""
    print("\n" + "="*60)
    print("🔍 开始API端点测试")
    print("="*60)
    
    # 从SSM获取配置
    api_url = get_ssm_parameter('/ai-ppt-assistant/dev/api-gateway-url')
    api_key = get_ssm_parameter('/ai-ppt-assistant/dev/api-key')
    
    if not api_url or not api_key:
        print("❌ 无法获取API配置")
        return False
    
    print(f"📍 API URL: {api_url}")
    print(f"🔑 API密钥: {api_key[:8]}...")
    
    headers = {'x-api-key': api_key}
    test_results = []
    
    # 测试1: 创建演示文稿
    print("\n[1/4] 测试创建演示文稿...")
    try:
        response = requests.post(
            f"{api_url}/presentation",
            headers=headers,
            json={
                "title": "回归测试演示",
                "topic": "系统健康度验证",
                "pages": 3
            },
            timeout=10
        )
        if response.status_code in [200, 201]:
            print(f"✅ 创建演示文稿成功 (HTTP {response.status_code})")
            test_results.append({"test": "创建演示文稿", "status": "PASS"})
            presentation_id = response.json().get('presentation_id')
        else:
            print(f"❌ 创建演示文稿失败 (HTTP {response.status_code})")
            test_results.append({"test": "创建演示文稿", "status": "FAIL", "error": f"HTTP {response.status_code}"})
            presentation_id = None
    except Exception as e:
        print(f"❌ 创建演示文稿异常: {e}")
        test_results.append({"test": "创建演示文稿", "status": "FAIL", "error": str(e)})
        presentation_id = None
    
    # 测试2: 列出演示文稿
    print("\n[2/4] 测试列出演示文稿...")
    try:
        response = requests.get(
            f"{api_url}/presentations",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            presentations = response.json()
            print(f"✅ 列出演示文稿成功 (找到 {len(presentations)} 个)")
            test_results.append({"test": "列出演示文稿", "status": "PASS"})
        else:
            print(f"❌ 列出演示文稿失败 (HTTP {response.status_code})")
            test_results.append({"test": "列出演示文稿", "status": "FAIL", "error": f"HTTP {response.status_code}"})
    except Exception as e:
        print(f"❌ 列出演示文稿异常: {e}")
        test_results.append({"test": "列出演示文稿", "status": "FAIL", "error": str(e)})
    
    # 测试3: 获取演示文稿状态
    if presentation_id:
        print(f"\n[3/4] 测试获取演示文稿状态 (ID: {presentation_id})...")
        try:
            response = requests.get(
                f"{api_url}/presentation/{presentation_id}/status",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                status = response.json()
                print(f"✅ 获取状态成功: {status.get('status', 'UNKNOWN')}")
                test_results.append({"test": "获取演示文稿状态", "status": "PASS"})
            else:
                print(f"❌ 获取状态失败 (HTTP {response.status_code})")
                test_results.append({"test": "获取状态失败", "status": "FAIL", "error": f"HTTP {response.status_code}"})
        except Exception as e:
            print(f"❌ 获取状态异常: {e}")
            test_results.append({"test": "获取演示文稿状态", "status": "FAIL", "error": str(e)})
    else:
        print("\n[3/4] ⏭️ 跳过获取演示文稿状态测试（无可用ID）")
        test_results.append({"test": "获取演示文稿状态", "status": "SKIP"})
    
    # 测试4: 测试错误处理
    print("\n[4/4] 测试错误处理...")
    try:
        response = requests.get(
            f"{api_url}/presentation/invalid-id/status",
            headers=headers,
            timeout=10
        )
        if response.status_code in [400, 404]:
            print(f"✅ 错误处理正确 (HTTP {response.status_code})")
            test_results.append({"test": "错误处理", "status": "PASS"})
        else:
            print(f"⚠️ 错误处理异常 (HTTP {response.status_code})")
            test_results.append({"test": "错误处理", "status": "WARN", "error": f"HTTP {response.status_code}"})
    except Exception as e:
        print(f"❌ 错误处理测试异常: {e}")
        test_results.append({"test": "错误处理", "status": "FAIL", "error": str(e)})
    
    return test_results

def check_infrastructure():
    """检查基础设施状态"""
    print("\n" + "="*60)
    print("🔍 检查基础设施状态")
    print("="*60)
    
    infra_results = []
    
    # 检查Lambda函数
    print("\n检查Lambda函数...")
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    try:
        functions = lambda_client.list_functions(
            FunctionVersion='ALL',
            MaxItems=50
        )
        ppt_functions = [f for f in functions['Functions'] 
                        if 'ai-ppt-assistant' in f['FunctionName']]
        print(f"✅ 找到 {len(ppt_functions)} 个Lambda函数")
        infra_results.append({"component": "Lambda函数", "count": len(ppt_functions), "status": "OK"})
    except Exception as e:
        print(f"❌ 检查Lambda失败: {e}")
        infra_results.append({"component": "Lambda函数", "status": "ERROR", "error": str(e)})
    
    # 检查DynamoDB表
    print("\n检查DynamoDB表...")
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    try:
        tables = dynamodb.list_tables()
        ppt_tables = [t for t in tables['TableNames'] 
                     if 'ai-ppt-assistant' in t]
        print(f"✅ 找到 {len(ppt_tables)} 个DynamoDB表")
        for table in ppt_tables:
            print(f"   - {table}")
        infra_results.append({"component": "DynamoDB表", "count": len(ppt_tables), "status": "OK"})
    except Exception as e:
        print(f"❌ 检查DynamoDB失败: {e}")
        infra_results.append({"component": "DynamoDB表", "status": "ERROR", "error": str(e)})
    
    # 检查SSM参数
    print("\n检查SSM参数...")
    ssm = boto3.client('ssm', region_name='us-east-1')
    try:
        parameters = ssm.describe_parameters(
            Filters=[
                {
                    'Key': 'Name',
                    'Option': 'Contains',
                    'Values': ['ai-ppt-assistant']
                }
            ],
            MaxResults=50
        )
        print(f"✅ 找到 {len(parameters['Parameters'])} 个SSM参数")
        infra_results.append({"component": "SSM参数", "count": len(parameters['Parameters']), "status": "OK"})
    except Exception as e:
        print(f"❌ 检查SSM失败: {e}")
        infra_results.append({"component": "SSM参数", "status": "ERROR", "error": str(e)})
    
    return infra_results

def generate_report(api_results, infra_results):
    """生成回归测试报告"""
    print("\n" + "="*60)
    print("📊 生成回归测试报告")
    print("="*60)
    
    # 统计API测试结果
    api_pass = sum(1 for r in api_results if r['status'] == 'PASS')
    api_fail = sum(1 for r in api_results if r['status'] == 'FAIL')
    api_skip = sum(1 for r in api_results if r['status'] == 'SKIP')
    api_warn = sum(1 for r in api_results if r['status'] == 'WARN')
    
    # 统计基础设施结果
    infra_ok = sum(1 for r in infra_results if r['status'] == 'OK')
    infra_error = sum(1 for r in infra_results if r['status'] == 'ERROR')
    
    # 计算健康度
    total_checks = len(api_results) + len(infra_results)
    passed_checks = api_pass + infra_ok
    health_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0
    
    report = {
        "test_time": datetime.now().isoformat(),
        "summary": {
            "health_score": f"{health_score:.1f}%",
            "total_tests": total_checks,
            "passed": passed_checks,
            "failed": api_fail + infra_error,
            "skipped": api_skip,
            "warnings": api_warn
        },
        "api_tests": api_results,
        "infrastructure": infra_results,
        "conclusion": "系统正常运行" if health_score >= 80 else "需要关注"
    }
    
    # 保存报告
    report_file = f"regression_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'✅' if health_score >= 80 else '⚠️'} 系统健康度: {health_score:.1f}%")
    print(f"📋 测试总结:")
    print(f"   - API测试: {api_pass}/{len(api_results)} 通过")
    print(f"   - 基础设施: {infra_ok}/{len(infra_results)} 正常")
    print(f"   - 报告保存: {report_file}")
    
    return health_score

def main():
    """主函数"""
    print("🚀 AI PPT Assistant 回归测试")
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 执行测试
    api_results = test_api_endpoints()
    infra_results = check_infrastructure()
    
    # 生成报告
    health_score = generate_report(api_results, infra_results)
    
    print("\n" + "="*60)
    if health_score >= 80:
        print("✅ 回归测试通过！系统状态良好。")
    else:
        print("⚠️ 回归测试发现问题，请检查详细报告。")
    print("="*60)

if __name__ == "__main__":
    main()