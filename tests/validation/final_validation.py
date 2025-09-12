#!/usr/bin/env python3
"""
最终验证脚本 - 确认所有修复是否生效
"""
import boto3
import json
import requests
from datetime import datetime

def validate_all_fixes():
    print("\n" + "="*60)
    print("🔍 最终修复验证")
    print("="*60 + "\n")
    
    results = {
        'passed': 0,
        'failed': 0,
        'details': []
    }
    
    # 1. 检查API密钥配置文件
    print("1️⃣ 检查API密钥配置文件...")
    try:
        with open('api_config_info.json', 'r') as f:
            config = json.load(f)
            if 'api_key' in config:
                results['failed'] += 1
                results['details'].append("❌ api_config_info.json仍包含明文密钥")
            else:
                results['passed'] += 1
                results['details'].append("✅ api_config_info.json已清理明文密钥")
    except Exception as e:
        results['failed'] += 1
        results['details'].append(f"❌ 无法读取api_config_info.json: {e}")
    
    # 2. 检查Makefile
    print("2️⃣ 检查Makefile...")
    try:
        with open('Makefile', 'r') as f:
            content = f.read()
            if 'deploy-with-config: deploy update-api-config' in content:
                results['failed'] += 1
                results['details'].append("❌ Makefile仍包含自动覆盖配置")
            else:
                results['passed'] += 1
                results['details'].append("✅ Makefile已修复自动覆盖问题")
    except Exception as e:
        results['failed'] += 1
        results['details'].append(f"❌ 无法读取Makefile: {e}")
    
    # 3. 检查Lambda函数环境变量
    print("3️⃣ 检查Lambda函数环境变量...")
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    functions_to_check = [
        'ai-ppt-assistant-api-generate-presentation',
        'ai-ppt-assistant-generate-content',
        'ai-ppt-assistant-generate-image',
        'ai-ppt-assistant-compile-pptx'
    ]
    
    lambda_ok = True
    for func_name in functions_to_check:
        try:
            config = lambda_client.get_function_configuration(FunctionName=func_name)
            env_vars = config.get('Environment', {}).get('Variables', {})
            
            # 检查是否还有占位符
            if 'placeholder' in str(env_vars).lower():
                lambda_ok = False
                results['details'].append(f"❌ {func_name}: 仍使用占位符")
            
            # 检查DynamoDB表
            if env_vars.get('DYNAMODB_TABLE') != 'ai-ppt-assistant-dev-sessions':
                lambda_ok = False
                results['details'].append(f"❌ {func_name}: DynamoDB表配置错误")
                
        except Exception as e:
            lambda_ok = False
            results['details'].append(f"❌ {func_name}: {e}")
    
    if lambda_ok:
        results['passed'] += 1
        results['details'].append("✅ 所有Lambda函数环境变量已修复")
    else:
        results['failed'] += 1
    
    # 4. 检查API Gateway stages
    print("4️⃣ 检查API Gateway...")
    apigateway = boto3.client('apigateway', region_name='us-east-1')
    try:
        apis = apigateway.get_rest_apis()
        if len(apis['items']) == 1:
            api_id = apis['items'][0]['id']
            stages = apigateway.get_stages(restApiId=api_id)
            stage_names = [s['stageName'] for s in stages['item']]
            
            if 'legacy' in stage_names:
                results['failed'] += 1
                results['details'].append("❌ API Gateway仍有legacy stage")
            else:
                results['passed'] += 1
                results['details'].append("✅ API Gateway已清理legacy stage")
        else:
            results['failed'] += 1
            results['details'].append(f"❌ 存在{len(apis['items'])}个API Gateway")
    except Exception as e:
        results['failed'] += 1
        results['details'].append(f"❌ API Gateway检查失败: {e}")
    
    # 5. 检查SSM参数
    print("5️⃣ 检查SSM配置中心...")
    ssm = boto3.client('ssm', region_name='us-east-1')
    try:
        # 使用paginator来获取所有参数
        paginator = ssm.get_paginator('get_parameters_by_path')
        param_count = 0
        params_list = []
        
        for page in paginator.paginate(
            Path='/ai-ppt-assistant/dev/',
            Recursive=True
        ):
            params_list.extend(page['Parameters'])
            param_count += len(page['Parameters'])
        
        if param_count >= 30:
            results['passed'] += 1
            results['details'].append(f"✅ SSM配置完整（{param_count}个参数）")
        else:
            results['failed'] += 1
            results['details'].append(f"❌ SSM参数不足（{param_count}个，预期30+）")
    except Exception as e:
        results['failed'] += 1
        results['details'].append(f"❌ SSM检查失败: {e}")
    
    # 6. 检查Bedrock Agent别名
    print("6️⃣ 检查Bedrock Agent别名...")
    bedrock = boto3.client('bedrock-agent', region_name='us-east-1')
    agent_ids = {
        'compiler': 'B02XIGCUKI',
        'content': 'L0ZQHJSU4X',
        'orchestrator': 'Q6RODNGFYR',
        'visual': 'FO53FNXIRL'
    }
    
    agent_ok = True
    for agent_type, agent_id in agent_ids.items():
        try:
            aliases = bedrock.list_agent_aliases(agentId=agent_id)
            alias_names = [a['agentAliasName'] for a in aliases.get('agentAliasSummaries', [])]
            
            if 'dev' not in alias_names:
                agent_ok = False
                results['details'].append(f"❌ {agent_type} Agent缺少dev别名")
                
        except Exception as e:
            agent_ok = False
            results['details'].append(f"❌ {agent_type} Agent检查失败: {e}")
    
    if agent_ok:
        results['passed'] += 1
        results['details'].append("✅ 所有Bedrock Agent别名配置正确")
    else:
        results['failed'] += 1
    
    # 打印结果
    print("\n" + "="*60)
    print("📊 最终验证结果")
    print("="*60)
    
    for detail in results['details']:
        print(detail)
    
    total = results['passed'] + results['failed']
    health = (results['passed'] / total * 100) if total > 0 else 0
    
    print("\n" + "-"*60)
    print(f"✅ 通过: {results['passed']}/{total}")
    print(f"❌ 失败: {results['failed']}/{total}")
    print(f"📈 系统健康度: {health:.1f}%")
    print("-"*60)
    
    # 保存报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'health_score': health,
        'passed': results['passed'],
        'failed': results['failed'],
        'total_checks': total,
        'details': results['details']
    }
    
    with open('final_validation_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 报告已保存: final_validation_report.json")
    
    if health >= 80:
        print("\n✅ 系统已准备就绪，可以安全部署！")
        return 0
    elif health >= 60:
        print("\n⚠️ 系统基本可用，但建议继续优化")
        return 1
    else:
        print("\n❌ 系统健康度过低，需要继续修复")
        return 2

if __name__ == "__main__":
    exit(validate_all_fixes())