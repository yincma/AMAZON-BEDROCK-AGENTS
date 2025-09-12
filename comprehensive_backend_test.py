#!/usr/bin/env python3
"""
全面的后端系统测试脚本
测试所有API端点、Bedrock Agent集成、DynamoDB操作和Lambda函数
"""

import requests
import json
import time
import boto3
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import sys
import os

# 配置信息
API_GATEWAY_URL = "https://zkag5thhk8.execute-api.us-east-1.amazonaws.com/legacy"
API_KEY = "IEa6uJXJad1ayONgRugGU19GJ3vONHXa9ndkrri0"
REGION = "us-east-1"

# 初始化AWS客户端
dynamodb = boto3.client('dynamodb', region_name=REGION)
lambda_client = boto3.client('lambda', region_name=REGION)
bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)
bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)
logs_client = boto3.client('logs', region_name=REGION)

# 测试结果存储
test_results = {
    "timestamp": datetime.now().isoformat(),
    "api_tests": {},
    "lambda_tests": {},
    "dynamodb_tests": {},
    "bedrock_tests": {},
    "integration_tests": {},
    "errors": [],
    "warnings": []
}

def log_test(category: str, test_name: str, status: str, details: Dict = None):
    """记录测试结果"""
    if category not in test_results:
        test_results[category] = {}
    
    test_results[category][test_name] = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "details": details or {}
    }
    
    status_symbol = "✅" if status == "PASS" else "❌"
    print(f"{status_symbol} {category} - {test_name}: {status}")
    if details:
        print(f"   Details: {json.dumps(details, indent=2)}")

def test_api_endpoint(endpoint: str, method: str = "GET", data: Dict = None, 
                     headers: Dict = None, expected_status: List[int] = [200]) -> Tuple[bool, Dict]:
    """测试单个API端点"""
    url = f"{API_GATEWAY_URL}{endpoint}"
    default_headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        if method == "GET":
            response = requests.get(url, headers=default_headers)
        elif method == "POST":
            response = requests.post(url, json=data, headers=default_headers)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=default_headers)
        elif method == "DELETE":
            response = requests.delete(url, headers=default_headers)
        else:
            return False, {"error": f"Unsupported method: {method}"}
        
        success = response.status_code in expected_status
        
        result = {
            "status_code": response.status_code,
            "success": success,
            "headers": dict(response.headers),
            "response_time": response.elapsed.total_seconds()
        }
        
        try:
            result["response_body"] = response.json()
        except:
            result["response_body"] = response.text[:500]
        
        return success, result
        
    except Exception as e:
        return False, {"error": str(e)}

def test_lambda_function(function_name: str, payload: Dict = None) -> Tuple[bool, Dict]:
    """测试Lambda函数"""
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload or {})
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        return response['StatusCode'] == 200, {
            "status_code": response['StatusCode'],
            "response": response_payload,
            "function_error": response.get('FunctionError')
        }
    except Exception as e:
        return False, {"error": str(e)}

def test_dynamodb_table(table_name: str) -> Tuple[bool, Dict]:
    """测试DynamoDB表"""
    try:
        response = dynamodb.describe_table(TableName=table_name)
        table_status = response['Table']['TableStatus']
        item_count = response['Table'].get('ItemCount', 0)
        
        # 尝试写入测试数据
        test_item = {
            'id': {'S': f'test_{uuid.uuid4()}'},
            'timestamp': {'S': datetime.now().isoformat()},
            'test_field': {'S': 'backend_test'}
        }
        
        put_success = False
        try:
            dynamodb.put_item(
                TableName=table_name,
                Item=test_item
            )
            put_success = True
            
            # 清理测试数据
            dynamodb.delete_item(
                TableName=table_name,
                Key={'id': test_item['id']}
            )
        except:
            pass
        
        return table_status == 'ACTIVE', {
            "status": table_status,
            "item_count": item_count,
            "write_test": put_success
        }
    except Exception as e:
        return False, {"error": str(e)}

def test_bedrock_agent(agent_id: str, agent_alias_id: str = "TSTALIASID") -> Tuple[bool, Dict]:
    """测试Bedrock Agent"""
    try:
        # 获取Agent信息
        agent_info = bedrock_agent.get_agent(
            agentId=agent_id
        )
        
        agent_status = agent_info['agent']['agentStatus']
        
        # 尝试调用Agent
        test_session_id = f"test_session_{uuid.uuid4()}"
        invoke_success = False
        
        try:
            response = bedrock_runtime.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=test_session_id,
                inputText="Test query"
            )
            invoke_success = True
        except Exception as e:
            pass
        
        return agent_status == 'PREPARED', {
            "agent_status": agent_status,
            "agent_name": agent_info['agent']['agentName'],
            "invoke_test": invoke_success
        }
    except Exception as e:
        return False, {"error": str(e)}

def run_api_tests():
    """运行API端点测试"""
    print("\n" + "="*60)
    print("🧪 开始API端点测试")
    print("="*60)
    
    # 测试健康检查
    success, result = test_api_endpoint("/health", "GET")
    log_test("api_tests", "health_check", "PASS" if success else "FAIL", result)
    
    # 测试PPT生成流程
    test_data = {
        "topic": "AI Technology",
        "pages": 5,
        "language": "en"
    }
    
    # 1. 创建PPT任务
    success, result = test_api_endpoint("/presentations", "POST", data=test_data)
    log_test("api_tests", "create_presentation", "PASS" if success else "FAIL", result)
    
    if success and result.get("response_body"):
        presentation_id = result["response_body"].get("presentation_id") or \
                         result["response_body"].get("presentationId")
        
        if presentation_id:
            test_results["test_presentation_id"] = presentation_id
            
            # 2. 获取任务状态
            time.sleep(2)
            success, result = test_api_endpoint(f"/presentations/{presentation_id}/status", "GET")
            log_test("api_tests", "get_presentation_status", "PASS" if success else "FAIL", result)
            
            # 3. 获取任务详情
            success, result = test_api_endpoint(f"/tasks/{presentation_id}", "GET")
            log_test("api_tests", "get_task_details", "PASS" if success else "FAIL", result)
    
    # 测试演示文稿列表
    success, result = test_api_endpoint("/presentations", "GET")
    log_test("api_tests", "list_presentations", "PASS" if success else "FAIL", result)
    
    # 测试修改幻灯片
    modify_data = {
        "presentationId": test_results.get("test_presentation_id", "test-id"),
        "slideNumber": 1,
        "content": "Updated content"
    }
    success, result = test_api_endpoint("/presentations/slides", "PUT", data=modify_data)
    log_test("api_tests", "modify_slide", "PASS" if success else "FAIL", result)

def run_lambda_tests():
    """运行Lambda函数测试"""
    print("\n" + "="*60)
    print("🔧 开始Lambda函数测试")
    print("="*60)
    
    lambda_functions = [
        "ai-ppt-assistant-api-generate-presentation",
        "ai-ppt-assistant-api-get-task",
        "ai-ppt-assistant-api-list-presentations",
        "ai-ppt-assistant-api-modify-slide",
        "ai-ppt-assistant-api-presentation-download",
        "ai-ppt-assistant-api-presentation-status",
        "ai-ppt-assistant-api-task-processor",
        "ai-ppt-assistant-controllers-compile-pptx",
        "ai-ppt-assistant-controllers-create-outline",
        "ai-ppt-assistant-controllers-find-image",
        "ai-ppt-assistant-controllers-generate-content",
        "ai-ppt-assistant-controllers-generate-image",
        "ai-ppt-assistant-controllers-generate-speaker-notes"
    ]
    
    for func_name in lambda_functions:
        success, result = test_lambda_function(func_name, {"test": True})
        log_test("lambda_tests", func_name, "PASS" if success else "FAIL", result)

def run_dynamodb_tests():
    """运行DynamoDB测试"""
    print("\n" + "="*60)
    print("💾 开始DynamoDB测试")
    print("="*60)
    
    tables = [
        "ai-ppt-assistant-dev-sessions",
        "ai-ppt-assistant-dev-tasks",
        "ai-ppt-assistant-dev-checkpoints"
    ]
    
    for table in tables:
        success, result = test_dynamodb_table(table)
        log_test("dynamodb_tests", table, "PASS" if success else "FAIL", result)

def run_bedrock_tests():
    """运行Bedrock Agent测试"""
    print("\n" + "="*60)
    print("🤖 开始Bedrock Agent测试")
    print("="*60)
    
    agents = [
        ("RJXRVZQWYF", "compiler-agent"),
        ("QICZKP62N4", "content-agent"),
        ("GHQCGPA61R", "orchestrator-agent"),
        ("K38P9DHTZJ", "visual-agent")
    ]
    
    for agent_id, agent_name in agents:
        success, result = test_bedrock_agent(agent_id)
        log_test("bedrock_tests", agent_name, "PASS" if success else "FAIL", result)

def run_integration_tests():
    """运行集成测试"""
    print("\n" + "="*60)
    print("🔗 开始集成测试")
    print("="*60)
    
    # 测试完整的PPT生成流程
    test_data = {
        "topic": "Integration Test - Cloud Computing",
        "pages": 3,
        "language": "en",
        "style": "professional"
    }
    
    print("📝 创建PPT任务...")
    success, result = test_api_endpoint("/presentations", "POST", data=test_data)
    
    if success and result.get("response_body"):
        presentation_id = result["response_body"].get("presentation_id") or \
                         result["response_body"].get("presentationId")
        
        if presentation_id:
            print(f"   任务ID: {presentation_id}")
            
            # 等待处理
            max_attempts = 30
            attempt = 0
            processing_complete = False
            
            while attempt < max_attempts and not processing_complete:
                time.sleep(5)
                attempt += 1
                
                success, status_result = test_api_endpoint(
                    f"/presentations/{presentation_id}/status", "GET"
                )
                
                if success and status_result.get("response_body"):
                    status = status_result["response_body"].get("status", "unknown")
                    print(f"   尝试 {attempt}/{max_attempts}: 状态 = {status}")
                    
                    if status in ["completed", "failed", "error"]:
                        processing_complete = True
                        log_test("integration_tests", "ppt_generation_flow", 
                                "PASS" if status == "completed" else "FAIL",
                                {"presentation_id": presentation_id, "final_status": status})
                        break
            
            if not processing_complete:
                log_test("integration_tests", "ppt_generation_flow", "FAIL",
                        {"error": "Timeout waiting for completion"})
    else:
        log_test("integration_tests", "ppt_generation_flow", "FAIL",
                {"error": "Failed to create presentation"})

def check_lambda_logs(function_name: str, start_time: int) -> Dict:
    """检查Lambda函数日志"""
    try:
        log_group = f"/aws/lambda/{function_name}"
        
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            limit=50
        )
        
        errors = []
        warnings = []
        
        for event in response.get('events', []):
            message = event['message']
            if 'ERROR' in message or 'Exception' in message:
                errors.append(message[:200])
            elif 'WARNING' in message:
                warnings.append(message[:200])
        
        return {
            "errors": errors[:5],
            "warnings": warnings[:5],
            "total_events": len(response.get('events', []))
        }
    except:
        return {}

def generate_summary():
    """生成测试摘要"""
    print("\n" + "="*60)
    print("📊 测试摘要")
    print("="*60)
    
    # 统计结果
    categories = ["api_tests", "lambda_tests", "dynamodb_tests", "bedrock_tests", "integration_tests"]
    
    for category in categories:
        if category in test_results:
            tests = test_results[category]
            total = len(tests)
            passed = len([t for t in tests.values() if t["status"] == "PASS"])
            failed = total - passed
            
            print(f"\n{category.upper()}:")
            print(f"  总计: {total}")
            print(f"  通过: {passed} ✅")
            print(f"  失败: {failed} ❌")
            print(f"  成功率: {(passed/total*100):.1f}%" if total > 0 else "N/A")

def save_results():
    """保存测试结果"""
    # 保存JSON格式结果
    with open("backend_test_report.json", "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    # 生成Markdown报告
    markdown_content = generate_markdown_report()
    with open("测试报告.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"\n📁 测试报告已保存到: 测试报告.md")
    print(f"📁 详细JSON报告已保存到: backend_test_report.json")

def generate_markdown_report() -> str:
    """生成Markdown格式的测试报告"""
    report = []
    report.append("# AI PPT Assistant 后端系统测试报告\n")
    report.append(f"**测试时间**: {test_results['timestamp']}\n")
    report.append(f"**环境**: Production (us-east-1)\n")
    report.append(f"**API Gateway**: {API_GATEWAY_URL}\n")
    
    # 执行摘要
    report.append("\n## 执行摘要\n")
    
    categories = ["api_tests", "lambda_tests", "dynamodb_tests", "bedrock_tests", "integration_tests"]
    summary_table = ["| 测试类别 | 总计 | 通过 | 失败 | 成功率 |"]
    summary_table.append("|---------|------|------|------|--------|")
    
    total_all = 0
    passed_all = 0
    
    for category in categories:
        if category in test_results:
            tests = test_results[category]
            total = len(tests)
            passed = len([t for t in tests.values() if t["status"] == "PASS"])
            failed = total - passed
            rate = f"{(passed/total*100):.1f}%" if total > 0 else "N/A"
            
            total_all += total
            passed_all += passed
            
            category_name = category.replace("_", " ").title()
            summary_table.append(f"| {category_name} | {total} | {passed} | {failed} | {rate} |")
    
    overall_rate = f"{(passed_all/total_all*100):.1f}%" if total_all > 0 else "N/A"
    summary_table.append(f"| **总计** | **{total_all}** | **{passed_all}** | **{total_all-passed_all}** | **{overall_rate}** |")
    
    report.extend(summary_table)
    
    # API测试详情
    report.append("\n## API测试详情\n")
    if "api_tests" in test_results:
        for test_name, result in test_results["api_tests"].items():
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            report.append(f"\n### {status_icon} {test_name}\n")
            report.append(f"- **状态**: {result['status']}\n")
            report.append(f"- **时间**: {result['timestamp']}\n")
            
            if result.get("details"):
                if "status_code" in result["details"]:
                    report.append(f"- **HTTP状态码**: {result['details']['status_code']}\n")
                if "response_time" in result["details"]:
                    report.append(f"- **响应时间**: {result['details']['response_time']:.3f}秒\n")
                if "error" in result["details"]:
                    report.append(f"- **错误信息**: `{result['details']['error']}`\n")
    
    # Lambda函数测试详情
    report.append("\n## Lambda函数测试详情\n")
    if "lambda_tests" in test_results:
        lambda_table = ["| 函数名称 | 状态 | 响应码 | 错误 |"]
        lambda_table.append("|---------|------|--------|------|")
        
        for test_name, result in test_results["lambda_tests"].items():
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            status_code = result.get("details", {}).get("status_code", "N/A")
            error = result.get("details", {}).get("function_error", "-")
            
            # 简化函数名称显示
            short_name = test_name.replace("ai-ppt-assistant-", "")
            lambda_table.append(f"| {short_name} | {status_icon} | {status_code} | {error} |")
        
        report.extend(lambda_table)
    
    # DynamoDB测试详情
    report.append("\n## DynamoDB测试详情\n")
    if "dynamodb_tests" in test_results:
        db_table = ["| 表名 | 状态 | 表状态 | 写入测试 | 记录数 |"]
        db_table.append("|------|------|--------|----------|--------|")
        
        for test_name, result in test_results["dynamodb_tests"].items():
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            details = result.get("details", {})
            table_status = details.get("status", "N/A")
            write_test = "✅" if details.get("write_test") else "❌"
            item_count = details.get("item_count", "N/A")
            
            # 简化表名显示
            short_name = test_name.replace("ai-ppt-assistant-dev-", "")
            db_table.append(f"| {short_name} | {status_icon} | {table_status} | {write_test} | {item_count} |")
        
        report.extend(db_table)
    
    # Bedrock Agent测试详情
    report.append("\n## Bedrock Agent测试详情\n")
    if "bedrock_tests" in test_results:
        agent_table = ["| Agent名称 | 状态 | Agent状态 | 调用测试 |"]
        agent_table.append("|-----------|------|-----------|----------|")
        
        for test_name, result in test_results["bedrock_tests"].items():
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            details = result.get("details", {})
            agent_status = details.get("agent_status", "N/A")
            invoke_test = "✅" if details.get("invoke_test") else "❌"
            
            agent_table.append(f"| {test_name} | {status_icon} | {agent_status} | {invoke_test} |")
        
        report.extend(agent_table)
    
    # 集成测试详情
    report.append("\n## 集成测试详情\n")
    if "integration_tests" in test_results:
        for test_name, result in test_results["integration_tests"].items():
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            report.append(f"\n### {status_icon} {test_name}\n")
            report.append(f"- **状态**: {result['status']}\n")
            
            if result.get("details"):
                for key, value in result["details"].items():
                    report.append(f"- **{key}**: {value}\n")
    
    # 问题和建议
    report.append("\n## 问题和建议\n")
    
    # 收集所有失败的测试
    failed_tests = []
    for category in categories:
        if category in test_results:
            for test_name, result in test_results[category].items():
                if result["status"] == "FAIL":
                    failed_tests.append(f"- {category}: {test_name}")
    
    if failed_tests:
        report.append("\n### ❌ 失败的测试\n")
        report.extend(failed_tests)
    else:
        report.append("\n### ✅ 所有测试通过\n")
        report.append("恭喜！所有后端测试都已通过。\n")
    
    # 建议
    report.append("\n### 💡 建议\n")
    
    suggestions = []
    
    # 基于测试结果提供建议
    if "lambda_tests" in test_results:
        failed_lambdas = [name for name, result in test_results["lambda_tests"].items() 
                         if result["status"] == "FAIL"]
        if failed_lambdas:
            suggestions.append("- 检查失败的Lambda函数日志，查看具体错误信息")
            suggestions.append("- 确认Lambda函数的IAM权限配置正确")
    
    if "bedrock_tests" in test_results:
        unprepared_agents = [name for name, result in test_results["bedrock_tests"].items()
                           if result.get("details", {}).get("agent_status") != "PREPARED"]
        if unprepared_agents:
            suggestions.append("- 某些Bedrock Agent未处于PREPARED状态，需要检查配置")
    
    if "integration_tests" in test_results:
        integration_failures = [name for name, result in test_results["integration_tests"].items()
                              if result["status"] == "FAIL"]
        if integration_failures:
            suggestions.append("- 集成测试失败，检查组件间的连接和数据流")
    
    if not suggestions:
        suggestions.append("- 系统运行正常，建议定期进行性能测试")
        suggestions.append("- 考虑添加更多的边界条件测试")
        suggestions.append("- 监控生产环境的错误率和响应时间")
    
    report.extend(suggestions)
    
    # 测试覆盖率
    report.append("\n## 测试覆盖率\n")
    report.append("- **API端点覆盖**: 核心端点已覆盖\n")
    report.append("- **Lambda函数覆盖**: 13个函数已测试\n")
    report.append("- **DynamoDB表覆盖**: 3个表已测试\n")
    report.append("- **Bedrock Agent覆盖**: 4个Agent已测试\n")
    report.append("- **集成测试**: PPT生成流程已测试\n")
    
    return "\n".join(report)

def main():
    """主函数"""
    print("🚀 开始AI PPT Assistant后端系统全面测试")
    print(f"   API Gateway: {API_GATEWAY_URL}")
    print(f"   Region: {REGION}")
    
    # 运行各类测试
    run_api_tests()
    run_lambda_tests()
    run_dynamodb_tests()
    run_bedrock_tests()
    run_integration_tests()
    
    # 生成摘要
    generate_summary()
    
    # 保存结果
    save_results()
    
    print("\n✅ 测试完成！")

if __name__ == "__main__":
    main()