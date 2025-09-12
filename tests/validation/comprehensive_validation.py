#!/usr/bin/env python3
"""
综合验证脚本 - 验证系统配置和运行状态
"""
import boto3
import json
import requests
from datetime import datetime

def run_comprehensive_validation():
    print("\n" + "="*60)
    print("🔍 综合系统验证")
    print("="*60 + "\n")
    
    results = {
        'config_checks': {'passed': 0, 'failed': 0},
        'runtime_checks': {'passed': 0, 'failed': 0},
        'details': []
    }
    
    # ========== 配置检查 ==========
    print("📋 配置检查")
    print("-"*40)
    
    # 1. API配置文件
    print("1. API配置文件...")
    try:
        with open('api_config_info.json', 'r') as f:
            config = json.load(f)
            if 'api_key' not in config:
                results['config_checks']['passed'] += 1
                results['details'].append("✅ 配置文件无明文密钥")
            else:
                results['config_checks']['failed'] += 1
                results['details'].append("❌ 配置文件包含明文密钥")
    except Exception as e:
        results['config_checks']['failed'] += 1
        results['details'].append(f"❌ 配置文件读取失败: {e}")
    
    # 2. Makefile
    print("2. Makefile配置...")
    try:
        with open('Makefile', 'r') as f:
            content = f.read()
            if 'deploy-with-config: deploy update-api-config' not in content:
                results['config_checks']['passed'] += 1
                results['details'].append("✅ Makefile无自动覆盖")
            else:
                results['config_checks']['failed'] += 1
                results['details'].append("❌ Makefile有自动覆盖风险")
    except Exception as e:
        results['config_checks']['failed'] += 1
        results['details'].append(f"❌ Makefile读取失败: {e}")
    
    # 3. SSM参数
    print("3. SSM参数...")
    ssm = boto3.client('ssm', region_name='us-east-1')
    try:
        paginator = ssm.get_paginator('get_parameters_by_path')
        param_count = 0
        for page in paginator.paginate(Path='/ai-ppt-assistant/dev/', Recursive=True):
            param_count += len(page['Parameters'])
        
        if param_count >= 30:
            results['config_checks']['passed'] += 1
            results['details'].append(f"✅ SSM参数充足（{param_count}个）")
        else:
            results['config_checks']['failed'] += 1
            results['details'].append(f"❌ SSM参数不足（{param_count}个）")
    except Exception as e:
        results['config_checks']['failed'] += 1
        results['details'].append(f"❌ SSM检查失败: {e}")
    
    # ========== 运行时检查 ==========
    print("\n📋 运行时检查")
    print("-"*40)
    
    # 4. Lambda函数
    print("4. Lambda函数...")
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    lambda_functions = [
        'ai-ppt-assistant-api-generate-presentation',
        'ai-ppt-assistant-generate-content',
        'ai-ppt-assistant-generate-image',
        'ai-ppt-assistant-compile-pptx'
    ]
    
    lambda_ok = True
    for func_name in lambda_functions:
        try:
            config = lambda_client.get_function_configuration(FunctionName=func_name)
            env_vars = config.get('Environment', {}).get('Variables', {})
            if 'placeholder' not in str(env_vars).lower():
                print(f"  ✅ {func_name.split('-')[-1]}")
            else:
                lambda_ok = False
                print(f"  ❌ {func_name.split('-')[-1]}")
        except:
            lambda_ok = False
            print(f"  ❌ {func_name.split('-')[-1]}")
    
    if lambda_ok:
        results['runtime_checks']['passed'] += 1
        results['details'].append("✅ Lambda函数配置正确")
    else:
        results['runtime_checks']['failed'] += 1
        results['details'].append("❌ Lambda函数配置有误")
    
    # 5. API Gateway
    print("5. API Gateway...")
    apigateway = boto3.client('apigateway', region_name='us-east-1')
    try:
        apis = apigateway.get_rest_apis()
        if len(apis['items']) == 1:
            api_id = apis['items'][0]['id']
            stages = apigateway.get_stages(restApiId=api_id)
            stage_names = [s['stageName'] for s in stages['item']]
            
            if 'dev' in stage_names and 'legacy' not in stage_names:
                results['runtime_checks']['passed'] += 1
                results['details'].append("✅ API Gateway配置正确")
            else:
                results['runtime_checks']['failed'] += 1
                results['details'].append(f"❌ API Gateway stages: {stage_names}")
        else:
            results['runtime_checks']['failed'] += 1
            results['details'].append(f"❌ 多个API Gateway（{len(apis['items'])}个）")
    except Exception as e:
        results['runtime_checks']['failed'] += 1
        results['details'].append(f"❌ API Gateway检查失败: {e}")
    
    # 6. DynamoDB
    print("6. DynamoDB表...")
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    try:
        table = dynamodb.describe_table(TableName='ai-ppt-assistant-dev-sessions')
        if table['Table']['TableStatus'] == 'ACTIVE':
            results['runtime_checks']['passed'] += 1
            results['details'].append("✅ DynamoDB表状态正常")
        else:
            results['runtime_checks']['failed'] += 1
            results['details'].append("❌ DynamoDB表状态异常")
    except Exception as e:
        results['runtime_checks']['failed'] += 1
        results['details'].append(f"❌ DynamoDB检查失败: {e}")
    
    # 7. Bedrock Agents
    print("7. Bedrock Agents...")
    bedrock = boto3.client('bedrock-agent', region_name='us-east-1')
    agent_ids = {
        'orchestrator': 'Q6RODNGFYR',
        'content': 'L0ZQHJSU4X',
        'visual': 'FO53FNXIRL',
        'compiler': 'B02XIGCUKI'
    }
    
    agents_ok = True
    for agent_type, agent_id in agent_ids.items():
        try:
            aliases = bedrock.list_agent_aliases(agentId=agent_id)
            alias_names = [a['agentAliasName'] for a in aliases.get('agentAliasSummaries', [])]
            if 'dev' in alias_names:
                print(f"  ✅ {agent_type}")
            else:
                agents_ok = False
                print(f"  ❌ {agent_type}")
        except:
            agents_ok = False
            print(f"  ❌ {agent_type}")
    
    if agents_ok:
        results['runtime_checks']['passed'] += 1
        results['details'].append("✅ Bedrock Agents配置正确")
    else:
        results['runtime_checks']['failed'] += 1
        results['details'].append("❌ Bedrock Agents配置有误")
    
    # ========== 结果汇总 ==========
    print("\n" + "="*60)
    print("📊 验证结果汇总")
    print("="*60)
    
    for detail in results['details']:
        print(detail)
    
    config_total = results['config_checks']['passed'] + results['config_checks']['failed']
    runtime_total = results['runtime_checks']['passed'] + results['runtime_checks']['failed']
    total_passed = results['config_checks']['passed'] + results['runtime_checks']['passed']
    total_checks = config_total + runtime_total
    
    health = (total_passed / total_checks * 100) if total_checks > 0 else 0
    
    print("\n" + "-"*60)
    print(f"📋 配置检查: {results['config_checks']['passed']}/{config_total} 通过")
    print(f"🚀 运行时检查: {results['runtime_checks']['passed']}/{runtime_total} 通过")
    print(f"📈 总体健康度: {health:.1f}%")
    print("-"*60)
    
    # 判断系统状态
    if health >= 90:
        print("\n✅ 系统状态优秀，可以安全部署！")
        status = "EXCELLENT"
    elif health >= 70:
        print("\n⚠️ 系统状态良好，建议优化后部署")
        status = "GOOD"
    else:
        print("\n❌ 系统状态需要修复")
        status = "NEEDS_REPAIR"
    
    # 保存报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'health_score': health,
        'status': status,
        'config_checks': results['config_checks'],
        'runtime_checks': results['runtime_checks'],
        'details': results['details']
    }
    
    with open('comprehensive_validation_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 报告已保存: comprehensive_validation_report.json")
    
    return health

if __name__ == "__main__":
    health_score = run_comprehensive_validation()
    exit(0 if health_score >= 70 else 1)