#!/usr/bin/env python3
"""
系统健康状态检查脚本
检查各个AWS组件的状态
"""

import boto3
import json
import time
from datetime import datetime, timedelta
import requests

# 配置信息
API_BASE_URL = "https://5vkle9t89e.execute-api.us-east-1.amazonaws.com/legacy"
API_KEY = "JVuEiLVBtlaXN8ctsNIJIaPi3eROzEgc6Y3lb4gM"
REGION = "us-east-1"

# AWS客户端
try:
    lambda_client = boto3.client('lambda', region_name=REGION)
    logs_client = boto3.client('logs', region_name=REGION)
    apigateway_client = boto3.client('apigateway', region_name=REGION)
    dynamodb_client = boto3.client('dynamodb', region_name=REGION)
    cloudwatch_client = boto3.client('cloudwatch', region_name=REGION)
except Exception as e:
    print(f"❌ AWS客户端初始化失败: {e}")
    lambda_client = logs_client = apigateway_client = dynamodb_client = cloudwatch_client = None

def check_lambda_functions():
    """检查Lambda函数状态"""
    print("\n🔍 检查Lambda函数状态...")
    
    function_names = [
        "ai-ppt-assistant-api-generate-presentation",
        "ai-ppt-assistant-api-presentation-status",
        "ai-ppt-assistant-api-presentation-download",
        "ai-ppt-assistant-api-modify-slide",
        "ai-ppt-assistant-list-presentations",
        "ai-ppt-assistant-get-task",
        "ai-ppt-assistant-create-outline",
        "ai-ppt-assistant-generate-content",
        "ai-ppt-assistant-generate-image",
        "ai-ppt-assistant-compile-pptx",
        "ai-ppt-assistant-find-image",
        "ai-ppt-assistant-generate-speaker-notes"
    ]
    
    if not lambda_client:
        print("❌ Lambda客户端不可用")
        return []
    
    results = []
    for func_name in function_names:
        try:
            response = lambda_client.get_function(FunctionName=func_name)
            state = response['Configuration'].get('State', 'Unknown')
            last_modified = response['Configuration'].get('LastModified', '')
            runtime = response['Configuration'].get('Runtime', 'Unknown')
            memory = response['Configuration'].get('MemorySize', 0)
            timeout = response['Configuration'].get('Timeout', 0)
            
            status = "✅" if state == "Active" else "❌"
            print(f"{status} {func_name}: {state} (Runtime: {runtime}, Memory: {memory}MB, Timeout: {timeout}s)")
            
            results.append({
                "function_name": func_name,
                "state": state,
                "runtime": runtime,
                "memory_size": memory,
                "timeout": timeout,
                "last_modified": last_modified,
                "status": "healthy" if state == "Active" else "unhealthy"
            })
            
        except Exception as e:
            print(f"❌ {func_name}: 错误 - {str(e)}")
            results.append({
                "function_name": func_name,
                "error": str(e),
                "status": "error"
            })
    
    return results

def check_api_gateway():
    """检查API Gateway状态"""
    print("\n🔍 检查API Gateway状态...")
    
    # 通过HTTP请求检查API健康状态
    try:
        health_url = f"{API_BASE_URL}/health"
        response = requests.get(health_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ API Gateway健康检查通过")
            return {"status": "healthy", "response_code": response.status_code}
        else:
            print(f"⚠️ API Gateway健康检查异常: HTTP {response.status_code}")
            return {"status": "warning", "response_code": response.status_code}
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API Gateway不可达: {str(e)}")
        return {"status": "error", "error": str(e)}

def check_dynamodb_tables():
    """检查DynamoDB表状态"""
    print("\n🔍 检查DynamoDB表状态...")
    
    if not dynamodb_client:
        print("❌ DynamoDB客户端不可用")
        return []
        
    table_names = [
        "ai-ppt-assistant-dev-sessions",
        "ai-ppt-assistant-dev-tasks",
        "ai-ppt-assistant-dev-checkpoints"
    ]
    
    results = []
    for table_name in table_names:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            item_count = response['Table'].get('ItemCount', 0)
            
            status_icon = "✅" if status == "ACTIVE" else "❌"
            print(f"{status_icon} {table_name}: {status} ({item_count} items)")
            
            results.append({
                "table_name": table_name,
                "status": status,
                "item_count": item_count,
                "health": "healthy" if status == "ACTIVE" else "unhealthy"
            })
            
        except Exception as e:
            print(f"❌ {table_name}: 错误 - {str(e)}")
            results.append({
                "table_name": table_name,
                "error": str(e),
                "health": "error"
            })
    
    return results

def check_cloudwatch_alarms():
    """检查CloudWatch告警状态"""
    print("\n🔍 检查CloudWatch告警状态...")
    
    if not cloudwatch_client:
        print("❌ CloudWatch客户端不可用")
        return []
    
    try:
        response = cloudwatch_client.describe_alarms(
            AlarmNamePrefix="ai-ppt-assistant",
            MaxRecords=50
        )
        
        alarms = response.get('MetricAlarms', [])
        alarm_states = {}
        
        for alarm in alarms:
            state = alarm['StateValue']
            alarm_states[state] = alarm_states.get(state, 0) + 1
            
            if state == 'ALARM':
                print(f"🚨 告警: {alarm['AlarmName']} - {alarm['StateReason']}")
            elif state == 'INSUFFICIENT_DATA':
                print(f"⚠️ 数据不足: {alarm['AlarmName']}")
            else:
                print(f"✅ 正常: {alarm['AlarmName']}")
        
        print(f"📊 告警统计: {alarm_states}")
        return {"total_alarms": len(alarms), "states": alarm_states}
        
    except Exception as e:
        print(f"❌ CloudWatch告警检查失败: {str(e)}")
        return {"error": str(e)}

def generate_health_report():
    """生成系统健康报告"""
    print("\n" + "="*60)
    print("🏥 系统健康状态报告")
    print("="*60)
    
    # 执行各项检查
    lambda_results = check_lambda_functions()
    api_gateway_result = check_api_gateway()
    dynamodb_results = check_dynamodb_tables()
    cloudwatch_result = check_cloudwatch_alarms()
    
    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "components": {
            "lambda_functions": {
                "total": len(lambda_results),
                "healthy": sum(1 for r in lambda_results if r.get("status") == "healthy"),
                "details": lambda_results
            },
            "api_gateway": api_gateway_result,
            "dynamodb": {
                "total_tables": len(dynamodb_results),
                "healthy_tables": sum(1 for r in dynamodb_results if r.get("health") == "healthy"),
                "details": dynamodb_results
            },
            "cloudwatch": cloudwatch_result
        }
    }
    
    # 计算总体健康状态
    issues = []
    
    # Lambda函数问题
    unhealthy_lambdas = sum(1 for r in lambda_results if r.get("status") != "healthy")
    if unhealthy_lambdas > 0:
        issues.append(f"{unhealthy_lambdas} Lambda函数状态异常")
    
    # API Gateway问题
    if api_gateway_result.get("status") != "healthy":
        issues.append("API Gateway状态异常")
    
    # DynamoDB问题
    unhealthy_tables = sum(1 for r in dynamodb_results if r.get("health") != "healthy")
    if unhealthy_tables > 0:
        issues.append(f"{unhealthy_tables} DynamoDB表状态异常")
    
    # 设置总体状态
    if len(issues) == 0:
        report["overall_status"] = "healthy"
    elif len(issues) <= 2:
        report["overall_status"] = "warning"
    else:
        report["overall_status"] = "critical"
    
    report["issues"] = issues
    
    # 输出总结
    print("\n📋 健康状态总结:")
    status_icon = {"healthy": "✅", "warning": "⚠️", "critical": "❌"}[report["overall_status"]]
    print(f"{status_icon} 总体状态: {report['overall_status'].upper()}")
    
    if issues:
        print("\n🚨 发现的问题:")
        for issue in issues:
            print(f"  - {issue}")
    
    # 保存报告
    with open("system_health_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 健康报告已保存到: system_health_report.json")
    return report

def main():
    """主函数"""
    print("🔍 开始系统健康状态检查...")
    print(f"🕒 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        report = generate_health_report()
        return report
    except KeyboardInterrupt:
        print("\n⚠️ 检查被用户中断")
        return None
    except Exception as e:
        print(f"\n❌ 检查过程中发生错误: {str(e)}")
        return None

if __name__ == "__main__":
    main()