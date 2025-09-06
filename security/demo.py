#!/usr/bin/env python3
"""
安全扫描系统演示脚本
模拟扫描功能，展示完整的安全扫描系统工作流程
"""

import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# 模拟的安全问题数据
MOCK_BANDIT_ISSUES = [
    {
        'file': 'lambdas/controllers/generate_content.py',
        'line': 45,
        'severity': 'medium',
        'test_id': 'B101',
        'issue': 'Use of assert detected. The enclosed code will be removed when compiling to optimised byte code.',
        'confidence': 'high'
    },
    {
        'file': 'lambdas/utils/aws_service_utils.py',
        'line': 123,
        'severity': 'high',
        'test_id': 'B105',
        'issue': 'Possible hardcoded password: \'default_password\'',
        'confidence': 'medium'
    }
]

MOCK_SAFETY_ISSUES = [
    {
        'file': 'tests/requirements.txt',
        'package': 'urllib3',
        'version': '1.26.5',
        'vulnerability_id': 'PYSEC-2021-59',
        'severity': 'high',
        'advisory': 'urllib3 before 1.26.5 does not remove the HTTP request body when an HTTP redirect response is received with a 303, 307, or 308 status code.',
        'cve': 'CVE-2021-33503'
    }
]

MOCK_SECRETS_ISSUES = [
    {
        'file': 'config/example.env',
        'line': 12,
        'severity': 'high',
        'type': 'AWS Access Key',
        'hashed_secret': 'a1b2c3d4e5f6g7h8i9j0'
    }
]

MOCK_AWS_ISSUES = [
    {
        'file': 'infrastructure/main.tf',
        'resource': 'aws_s3_bucket.example',
        'check_id': 'CKV_AWS_21',
        'severity': 'critical',
        'description': 'Ensure S3 bucket does not allow public read-write access',
        'guideline': 'https://docs.bridgecrew.io/docs/s3_2-acl-read-write-permissions-everyone'
    }
]

def simulate_scan_delay(tool_name: str):
    """模拟扫描延时"""
    print(f"  🔍 Scanning with {tool_name}...")
    delay = random.uniform(0.5, 2.0)
    time.sleep(delay)

def create_mock_report() -> Dict:
    """创建模拟的安全扫描报告"""
    
    # 随机选择要包含的问题
    bandit_issues = random.sample(MOCK_BANDIT_ISSUES, random.randint(0, len(MOCK_BANDIT_ISSUES)))
    safety_issues = random.sample(MOCK_SAFETY_ISSUES, random.randint(0, len(MOCK_SAFETY_ISSUES)))
    secrets_issues = random.sample(MOCK_SECRETS_ISSUES, random.randint(0, len(MOCK_SECRETS_ISSUES)))
    aws_issues = random.sample(MOCK_AWS_ISSUES, random.randint(0, len(MOCK_AWS_ISSUES)))
    
    # 计算严重性统计
    summary = {'total_issues': 0, 'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
    
    all_issues = bandit_issues + safety_issues + secrets_issues + aws_issues
    for issue in all_issues:
        severity = issue.get('severity', 'low')
        summary[severity] = summary.get(severity, 0) + 1
        summary['total_issues'] += 1
    
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'project_root': str(Path.cwd()),
        'summary': summary,
        'scans': {
            'bandit': {
                'tool': 'bandit',
                'status': 'completed',
                'issues_count': len(bandit_issues),
                'issues': bandit_issues
            },
            'safety': {
                'tool': 'safety',
                'status': 'completed',
                'issues_count': len(safety_issues),
                'issues': safety_issues
            },
            'secrets': {
                'tool': 'detect-secrets',
                'status': 'completed',
                'issues_count': len(secrets_issues),
                'issues': secrets_issues
            },
            'aws': {
                'tool': 'checkov',
                'status': 'completed',
                'issues_count': len(aws_issues),
                'issues': aws_issues
            }
        }
    }

def display_console_report(report: Dict):
    """显示控制台格式的报告"""
    
    # 颜色定义
    class Colors:
        RED = '\033[0;31m'
        GREEN = '\033[0;32m'
        YELLOW = '\033[0;33m'
        BLUE = '\033[0;34m'
        CYAN = '\033[0;36m'
        WHITE = '\033[0;37m'
        BOLD = '\033[1m'
        RESET = '\033[0m'
    
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"{Colors.BLUE}SECURITY SCAN REPORT (DEMO)")
    print(f"{Colors.BLUE}{'='*60}")
    print(f"Project: {report['project_root']}")
    print(f"Timestamp: {report['timestamp']}")
    print()
    
    # 汇总信息
    summary = report['summary']
    print(f"{Colors.CYAN}SUMMARY:")
    print(f"Total Issues: {summary['total_issues']}")
    print(f"  {Colors.RED}Critical: {summary['critical']}")
    print(f"  {Colors.YELLOW}High: {summary['high']}")
    print(f"  {Colors.BLUE}Medium: {summary['medium']}")
    print(f"  {Colors.GREEN}Low: {summary['low']}")
    print(f"  Info: {summary['info']}")
    print()
    
    # 各扫描工具结果
    for scan_name, scan_data in report['scans'].items():
        print(f"{Colors.CYAN}{scan_name.upper()} SCAN:")
        print(f"Status: {scan_data['status']}")
        print(f"Issues: {scan_data['issues_count']}")
        
        if scan_data.get('issues') and len(scan_data['issues']) > 0:
            print("Top Issues:")
            for i, issue in enumerate(scan_data['issues'][:3]):  # Show top 3 issues
                severity_color = {
                    'critical': Colors.RED,
                    'high': Colors.YELLOW,
                    'medium': Colors.BLUE,
                    'low': Colors.GREEN
                }.get(issue.get('severity', 'low'), Colors.WHITE)
                
                file_path = issue.get('file', 'Unknown')
                line = issue.get('line', issue.get('line_number', 'N/A'))
                description = (issue.get('issue') or issue.get('description') or 
                             issue.get('type') or issue.get('advisory', '')[:50] + '...' 
                             if issue.get('advisory', '') else 'No description')
                
                print(f"  {i+1}. {severity_color}{issue.get('severity', 'unknown').upper()}{Colors.RESET} "
                      f"in {file_path}:{line}")
                print(f"     {description}")
        print()

def save_html_report(report: Dict, output_dir: Path) -> str:
    """保存HTML格式报告"""
    
    html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Security Scan Report (Demo)</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .demo-badge {{ background: #ff6b6b; color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px; display: inline-block; margin-bottom: 10px; }}
        .summary {{ margin: 20px 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
        .critical {{ border-left-color: #dc3545 !important; }}
        .high {{ border-left-color: #fd7e14 !important; }}
        .medium {{ border-left-color: #ffc107 !important; }}
        .low {{ border-left-color: #28a745 !important; }}
        .critical-text {{ color: #dc3545; font-weight: bold; }}
        .high-text {{ color: #fd7e14; font-weight: bold; }}
        .medium-text {{ color: #ffc107; font-weight: bold; }}
        .low-text {{ color: #28a745; font-weight: bold; }}
        .section {{ margin: 30px 0; background: white; border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden; }}
        .section-header {{ background: #f8f9fa; padding: 15px 20px; border-bottom: 1px solid #e9ecef; font-weight: bold; }}
        .section-content {{ padding: 20px; }}
        .issues {{ margin: 10px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #dee2e6; padding: 12px 8px; text-align: left; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        .status-completed {{ color: #28a745; font-weight: bold; }}
        .status-failed {{ color: #dc3545; font-weight: bold; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 2px solid #e9ecef; color: #6c757d; text-align: center; }}
        .recommendation {{ background: #e7f3ff; border: 1px solid #b8daff; border-radius: 5px; padding: 15px; margin: 15px 0; }}
        .recommendation h4 {{ color: #0066cc; margin-top: 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="demo-badge">DEMO VERSION</div>
            <h1>Security Scan Report</h1>
            <p><strong>Project:</strong> AI PPT Assistant</p>
            <p><strong>Timestamp:</strong> {timestamp}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Issues</h3>
                <h2>{total_issues}</h2>
            </div>
            <div class="summary-card critical">
                <h3>Critical</h3>
                <h2 class="critical-text">{critical}</h2>
            </div>
            <div class="summary-card high">
                <h3>High</h3>
                <h2 class="high-text">{high}</h2>
            </div>
            <div class="summary-card medium">
                <h3>Medium</h3>
                <h2 class="medium-text">{medium}</h2>
            </div>
            <div class="summary-card low">
                <h3>Low</h3>
                <h2 class="low-text">{low}</h2>
            </div>
        </div>
        
        <div class="recommendation">
            <h4>🛡️ Security Recommendations</h4>
            <ul>
                <li><strong>Critical & High Issues:</strong> Address immediately before deployment</li>
                <li><strong>Medium Issues:</strong> Fix in the next development cycle</li>
                <li><strong>Low Issues:</strong> Address during routine maintenance</li>
                <li><strong>Best Practice:</strong> Run security scans regularly and integrate into CI/CD pipeline</li>
            </ul>
        </div>
        
        {scan_sections}
        
        <div class="footer">
            <p><strong>Note:</strong> This is a demonstration report showing the capabilities of the AI PPT Assistant security scanning system.</p>
            <p>Powered by: Bandit, Safety, detect-secrets, Checkov</p>
        </div>
    </div>
</body>
</html>
    """
    
    # 生成扫描结果部分
    scan_sections = ""
    for scan_name, scan_data in report['scans'].items():
        issues_html = ""
        if scan_data.get('issues'):
            issues_html = "<table><thead><tr><th>File</th><th>Line</th><th>Severity</th><th>Issue</th></tr></thead><tbody>"
            for issue in scan_data['issues'][:10]:  # 显示前10个问题
                file_path = issue.get('file', 'Unknown')
                line = issue.get('line', issue.get('line_number', 'N/A'))
                severity = issue.get('severity', 'unknown')
                description = (issue.get('issue') or issue.get('description') or 
                             issue.get('type') or issue.get('advisory', ''))[:100] + '...' if len(str(issue.get('issue') or issue.get('description') or issue.get('type') or issue.get('advisory', ''))) > 100 else (issue.get('issue') or issue.get('description') or issue.get('type') or issue.get('advisory', 'No description'))
                
                severity_class = f"{severity}-text"
                issues_html += f"""
                <tr>
                    <td>{file_path}</td>
                    <td>{line}</td>
                    <td><span class="{severity_class}">{severity.upper()}</span></td>
                    <td>{description}</td>
                </tr>
                """
            issues_html += "</tbody></table>"
        else:
            issues_html = "<p style='color: #28a745;'>✅ No issues found</p>"
        
        scan_sections += f"""
        <div class="section">
            <div class="section-header">
                {scan_name.title()} Scan Results
            </div>
            <div class="section-content">
                <p><strong>Status:</strong> <span class="status-{scan_data['status']}">{scan_data['status'].title()}</span></p>
                <p><strong>Issues Found:</strong> {scan_data['issues_count']}</p>
                {issues_html}
            </div>
        </div>
        """
    
    # 填充模板
    html_content = html_template.format(
        timestamp=report['timestamp'],
        total_issues=report['summary']['total_issues'],
        critical=report['summary']['critical'],
        high=report['summary']['high'],
        medium=report['summary']['medium'],
        low=report['summary']['low'],
        scan_sections=scan_sections
    )
    
    # 保存文件
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = output_dir / f"security_demo_report_{timestamp}.html"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return str(report_file)

def main():
    """主演示函数"""
    
    # 颜色定义
    class Colors:
        RED = '\033[0;31m'
        GREEN = '\033[0;32m'
        YELLOW = '\033[0;33m'
        BLUE = '\033[0;34m'
        CYAN = '\033[0;36m'
        MAGENTA = '\033[0;35m'
        WHITE = '\033[0;37m'
        BOLD = '\033[1m'
        RESET = '\033[0m'
    
    print(f"{Colors.GREEN}{Colors.BOLD}🛡️  AI PPT Assistant Security Scan System DEMO{Colors.RESET}")
    print(f"{Colors.BLUE}This demo shows the complete security scanning workflow{Colors.RESET}\n")
    
    # 创建输出目录
    output_dir = Path(__file__).parent / "reports"
    output_dir.mkdir(exist_ok=True)
    
    print(f"{Colors.CYAN}📋 Starting comprehensive security scan...{Colors.RESET}")
    print()
    
    # 模拟各个扫描步骤
    print("🔍 Running security scans:")
    
    simulate_scan_delay("Bandit (Code Security)")
    print("  ✅ Code security scan completed")
    
    simulate_scan_delay("Safety (Dependency Vulnerabilities)")  
    print("  ✅ Dependency vulnerability scan completed")
    
    simulate_scan_delay("detect-secrets (Secrets Detection)")
    print("  ✅ Secrets detection completed")
    
    simulate_scan_delay("Checkov (AWS Security)")
    print("  ✅ AWS security best practices scan completed")
    
    print()
    print(f"{Colors.GREEN}✅ All scans completed successfully!{Colors.RESET}")
    print()
    
    # 生成模拟报告
    report = create_mock_report()
    
    # 显示控制台报告
    display_console_report(report)
    
    # 保存JSON报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = output_dir / f"security_demo_report_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # 保存HTML报告
    html_file = save_html_report(report, output_dir)
    
    print(f"{Colors.CYAN}📊 Reports generated:")
    print(f"  📄 JSON Report: {json_file}")
    print(f"  🌐 HTML Report: {html_file}")
    print()
    
    # 显示使用指南
    print(f"{Colors.MAGENTA}🚀 Ready to use the real security scanning system:{Colors.RESET}")
    print()
    print(f"  {Colors.BLUE}1. Install security tools:{Colors.RESET}")
    print(f"     make security-install")
    print()
    print(f"  {Colors.BLUE}2. Run security scan:{Colors.RESET}")
    print(f"     make security-scan")
    print()
    print(f"  {Colors.BLUE}3. Generate HTML report:{Colors.RESET}")
    print(f"     make security-report")
    print()
    print(f"  {Colors.BLUE}4. CI/CD integration:{Colors.RESET}")
    print(f"     make security-scan-ci")
    print()
    
    if report['summary']['critical'] > 0 or report['summary']['high'] > 0:
        print(f"{Colors.RED}⚠️  WARNING: Critical or high-severity issues found in demo!{Colors.RESET}")
        print(f"{Colors.RED}   In a real scenario, these should be addressed immediately.{Colors.RESET}")
    else:
        print(f"{Colors.GREEN}✅ Demo shows a clean security posture!{Colors.RESET}")
    
    print()
    print(f"{Colors.WHITE}For more information, see: security/README.md{Colors.RESET}")

if __name__ == '__main__':
    main()