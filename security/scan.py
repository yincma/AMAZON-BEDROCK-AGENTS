#!/usr/bin/env python3
"""
完整的安全扫描系统
支持代码安全、依赖漏洞、敏感信息检测和AWS安全最佳实践检查
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from colorama import Fore, Style, init
from jinja2 import Template
from tabulate import tabulate

# Initialize colorama for cross-platform colored output
init(autoreset=True)

class SecurityScanner:
    """完整的安全扫描器"""
    
    def __init__(self, project_root: Path, output_dir: Path = None):
        self.project_root = Path(project_root).resolve()
        self.output_dir = output_dir or self.project_root / "security" / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 扫描结果存储
        self.results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'project_root': str(self.project_root),
            'summary': {
                'total_issues': 0,
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'info': 0
            },
            'scans': {}
        }
    
    def log_info(self, message: str):
        """记录信息日志"""
        click.echo(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} {message}")
    
    def log_warning(self, message: str):
        """记录警告日志"""
        click.echo(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {message}")
    
    def log_error(self, message: str):
        """记录错误日志"""
        click.echo(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}")
    
    def log_success(self, message: str):
        """记录成功日志"""
        click.echo(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}")
    
    def run_bandit_scan(self) -> Dict:
        """运行Bandit代码安全扫描"""
        self.log_info("Running Bandit code security scan...")
        
        try:
            # 创建bandit配置
            config_content = """
[bandit]
exclude_dirs = ['.venv', 'venv', 'node_modules', '.git', '__pycache__', 'lambdas/layers/build']
skips = ['B101']  # Skip assert_used test

[bandit.formatters]
json = bandit.formatters.json:JsonFormatter
"""
            config_file = self.project_root / ".bandit"
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            # 运行bandit
            cmd = [
                'bandit', '-r', str(self.project_root),
                '-f', 'json',
                '-c', str(config_file),
                '--severity-level', 'low'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                try:
                    bandit_data = json.loads(result.stdout) if result.stdout.strip() else {"results": []}
                except json.JSONDecodeError:
                    self.log_warning("Failed to parse Bandit JSON output")
                    bandit_data = {"results": []}
                
                # 处理结果
                issues = []
                for issue in bandit_data.get('results', []):
                    severity = issue.get('issue_severity', 'UNKNOWN').lower()
                    if severity == 'high':
                        self.results['summary']['high'] += 1
                    elif severity == 'medium':
                        self.results['summary']['medium'] += 1  
                    elif severity == 'low':
                        self.results['summary']['low'] += 1
                    
                    issues.append({
                        'file': issue.get('filename', 'Unknown'),
                        'line': issue.get('line_number', 0),
                        'severity': severity,
                        'test_id': issue.get('test_id', 'Unknown'),
                        'issue': issue.get('issue_text', 'No description'),
                        'confidence': issue.get('issue_confidence', 'Unknown')
                    })
                
                self.log_success(f"Bandit scan completed: {len(issues)} issues found")
                return {
                    'tool': 'bandit',
                    'status': 'completed',
                    'issues_count': len(issues),
                    'issues': issues,
                    'raw_output': result.stdout
                }
            else:
                self.log_error(f"Bandit scan failed: {result.stderr}")
                return {
                    'tool': 'bandit',
                    'status': 'failed',
                    'error': result.stderr,
                    'issues_count': 0,
                    'issues': []
                }
                
        except FileNotFoundError:
            self.log_error("Bandit not found. Please install security requirements.")
            return {
                'tool': 'bandit',
                'status': 'not_installed',
                'error': 'Bandit not found in PATH',
                'issues_count': 0,
                'issues': []
            }
    
    def run_safety_scan(self) -> Dict:
        """运行Safety依赖漏洞扫描"""
        self.log_info("Running Safety dependency vulnerability scan...")
        
        try:
            # 查找所有requirements文件
            req_files = list(self.project_root.rglob("requirements.txt"))
            req_files.extend(list(self.project_root.rglob("requirements-*.txt")))
            
            all_issues = []
            
            for req_file in req_files:
                if 'layers/build' in str(req_file):
                    continue
                    
                self.log_info(f"Scanning {req_file}")
                
                cmd = ['safety', 'check', '-r', str(req_file), '--json']
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode in [0, 64]:  # 0 = no vulnerabilities, 64 = vulnerabilities found
                    try:
                        if result.stdout.strip():
                            safety_data = json.loads(result.stdout)
                            for vuln in safety_data:
                                severity = self._get_safety_severity(vuln.get('vulnerability_id', ''))
                                if severity == 'critical':
                                    self.results['summary']['critical'] += 1
                                elif severity == 'high':
                                    self.results['summary']['high'] += 1
                                elif severity == 'medium':
                                    self.results['summary']['medium'] += 1
                                elif severity == 'low':
                                    self.results['summary']['low'] += 1
                                
                                all_issues.append({
                                    'file': str(req_file.relative_to(self.project_root)),
                                    'package': vuln.get('package_name', 'Unknown'),
                                    'version': vuln.get('installed_version', 'Unknown'),
                                    'vulnerability_id': vuln.get('vulnerability_id', 'Unknown'),
                                    'severity': severity,
                                    'advisory': vuln.get('advisory', 'No advisory'),
                                    'cve': vuln.get('cve', 'N/A')
                                })
                    except json.JSONDecodeError:
                        self.log_warning(f"Failed to parse Safety JSON output for {req_file}")
            
            self.log_success(f"Safety scan completed: {len(all_issues)} vulnerabilities found")
            return {
                'tool': 'safety',
                'status': 'completed',
                'issues_count': len(all_issues),
                'issues': all_issues,
                'files_scanned': [str(f.relative_to(self.project_root)) for f in req_files]
            }
            
        except FileNotFoundError:
            self.log_error("Safety not found. Please install security requirements.")
            return {
                'tool': 'safety',
                'status': 'not_installed',
                'error': 'Safety not found in PATH',
                'issues_count': 0,
                'issues': []
            }
    
    def run_secrets_scan(self) -> Dict:
        """运行敏感信息检测扫描"""
        self.log_info("Running secrets detection scan...")
        
        try:
            # 创建detect-secrets配置
            secrets_config = {
                "version": "1.4.0",
                "plugins_used": [
                    {"name": "ArtifactoryDetector"},
                    {"name": "AWSKeyDetector"},
                    {"name": "AzureStorageKeyDetector"},
                    {"name": "Base64HighEntropyString", "limit": 4.5},
                    {"name": "BasicAuthDetector"},
                    {"name": "CloudantDetector"},
                    {"name": "HexHighEntropyString", "limit": 3.0},
                    {"name": "IbmCloudIamDetector"},
                    {"name": "IbmCosHmacDetector"},
                    {"name": "JwtTokenDetector"},
                    {"name": "KeywordDetector", "keyword_exclude": ""},
                    {"name": "MailchimpDetector"},
                    {"name": "NpmDetector"},
                    {"name": "PrivateKeyDetector"},
                    {"name": "SlackDetector"},
                    {"name": "SoftlayerDetector"},
                    {"name": "SquareOAuthDetector"},
                    {"name": "StripeDetector"},
                    {"name": "TwilioKeyDetector"}
                ],
                "filters_used": [
                    {"path": "detect_secrets.filters.allowlist.is_line_allowlisted"},
                    {"path": "detect_secrets.filters.common.is_ignored_due_to_verification_policies",
                     "min_level": 2},
                    {"path": "detect_secrets.filters.heuristic.is_indirect_reference"},
                    {"path": "detect_secrets.filters.heuristic.is_likely_id_string"},
                    {"path": "detect_secrets.filters.heuristic.is_templated_secret"}
                ],
                "exclude": {
                    "files": "^(\\.venv/|venv/|node_modules/|\\.git/|__pycache__/|lambdas/layers/build/)",
                    "lines": null
                },
                "word_list": {
                    "file": null,
                    "hash": null
                }
            }
            
            config_file = self.project_root / ".secrets.baseline"
            
            # 运行detect-secrets scan
            cmd = ['detect-secrets', 'scan', '--all-files', '--force-use-all-plugins']
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                try:
                    secrets_data = json.loads(result.stdout) if result.stdout.strip() else {"results": {}}
                    
                    issues = []
                    for file_path, secrets in secrets_data.get('results', {}).items():
                        for secret in secrets:
                            self.results['summary']['high'] += 1  # Secrets are high severity
                            issues.append({
                                'file': file_path,
                                'line': secret.get('line_number', 0),
                                'severity': 'high',
                                'type': secret.get('type', 'Unknown'),
                                'hashed_secret': secret.get('hashed_secret', 'N/A')
                            })
                    
                    self.log_success(f"Secrets scan completed: {len(issues)} potential secrets found")
                    return {
                        'tool': 'detect-secrets',
                        'status': 'completed',
                        'issues_count': len(issues),
                        'issues': issues
                    }
                except json.JSONDecodeError:
                    self.log_warning("Failed to parse detect-secrets JSON output")
                    return {
                        'tool': 'detect-secrets',
                        'status': 'completed',
                        'issues_count': 0,
                        'issues': []
                    }
            else:
                self.log_error(f"Secrets scan failed: {result.stderr}")
                return {
                    'tool': 'detect-secrets',
                    'status': 'failed',
                    'error': result.stderr,
                    'issues_count': 0,
                    'issues': []
                }
                
        except FileNotFoundError:
            self.log_error("detect-secrets not found. Please install security requirements.")
            return {
                'tool': 'detect-secrets',
                'status': 'not_installed',
                'error': 'detect-secrets not found in PATH',
                'issues_count': 0,
                'issues': []
            }
    
    def run_aws_security_scan(self) -> Dict:
        """运行AWS安全最佳实践检查"""
        self.log_info("Running AWS security best practices scan...")
        
        try:
            # 查找Terraform和CloudFormation文件
            tf_files = list(self.project_root.rglob("*.tf"))
            cfn_files = list(self.project_root.rglob("*.yaml"))
            cfn_files.extend(list(self.project_root.rglob("*.yml")))
            
            all_issues = []
            
            # 扫描Terraform文件 (使用Checkov)
            if tf_files:
                self.log_info("Scanning Terraform files with Checkov...")
                cmd = [
                    'checkov', '-d', str(self.project_root),
                    '--framework', 'terraform',
                    '--output', 'json',
                    '--quiet'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode in [0, 1]:  # 0 = no issues, 1 = issues found
                    try:
                        if result.stdout.strip():
                            checkov_data = json.loads(result.stdout)
                            failed_checks = checkov_data.get('results', {}).get('failed_checks', [])
                            
                            for check in failed_checks:
                                severity = self._get_checkov_severity(check.get('check_id', ''))
                                if severity == 'critical':
                                    self.results['summary']['critical'] += 1
                                elif severity == 'high':
                                    self.results['summary']['high'] += 1
                                elif severity == 'medium':
                                    self.results['summary']['medium'] += 1
                                elif severity == 'low':
                                    self.results['summary']['low'] += 1
                                
                                all_issues.append({
                                    'file': check.get('file_path', 'Unknown'),
                                    'resource': check.get('resource', 'Unknown'),
                                    'check_id': check.get('check_id', 'Unknown'),
                                    'severity': severity,
                                    'description': check.get('check_name', 'No description'),
                                    'guideline': check.get('guideline', 'N/A')
                                })
                    except json.JSONDecodeError:
                        self.log_warning("Failed to parse Checkov JSON output")
            
            self.log_success(f"AWS security scan completed: {len(all_issues)} issues found")
            return {
                'tool': 'checkov',
                'status': 'completed',
                'issues_count': len(all_issues),
                'issues': all_issues,
                'files_scanned': len(tf_files + cfn_files)
            }
            
        except FileNotFoundError:
            self.log_error("Checkov not found. Please install security requirements.")
            return {
                'tool': 'checkov',
                'status': 'not_installed',
                'error': 'Checkov not found in PATH',
                'issues_count': 0,
                'issues': []
            }
    
    def _get_safety_severity(self, vuln_id: str) -> str:
        """根据漏洞ID确定Safety扫描的严重性级别"""
        # 简化的严重性映射，实际项目中可能需要更复杂的逻辑
        if any(term in vuln_id.lower() for term in ['critical', 'rce', 'sql']):
            return 'critical'
        elif any(term in vuln_id.lower() for term in ['high', 'xss', 'csrf']):
            return 'high'
        elif any(term in vuln_id.lower() for term in ['medium', 'dos']):
            return 'medium'
        else:
            return 'low'
    
    def _get_checkov_severity(self, check_id: str) -> str:
        """根据检查ID确定Checkov扫描的严重性级别"""
        # AWS安全检查严重性映射
        critical_checks = ['CKV_AWS_20', 'CKV_AWS_21', 'CKV_AWS_58']  # S3公共访问等
        high_checks = ['CKV_AWS_23', 'CKV_AWS_39', 'CKV_AWS_40']      # 加密相关
        medium_checks = ['CKV_AWS_24', 'CKV_AWS_33', 'CKV_AWS_34']    # 访问控制
        
        if check_id in critical_checks:
            return 'critical'
        elif check_id in high_checks:
            return 'high'
        elif check_id in medium_checks:
            return 'medium'
        else:
            return 'low'
    
    def run_all_scans(self) -> Dict:
        """运行所有安全扫描"""
        self.log_info("Starting comprehensive security scan...")
        
        # 运行各项扫描
        self.results['scans']['bandit'] = self.run_bandit_scan()
        self.results['scans']['safety'] = self.run_safety_scan()
        self.results['scans']['secrets'] = self.run_secrets_scan()
        self.results['scans']['aws'] = self.run_aws_security_scan()
        
        # 计算总问题数
        self.results['summary']['total_issues'] = (
            self.results['summary']['critical'] +
            self.results['summary']['high'] +
            self.results['summary']['medium'] +
            self.results['summary']['low'] +
            self.results['summary']['info']
        )
        
        return self.results
    
    def generate_report(self, format: str = 'html') -> str:
        """生成安全扫描报告"""
        if format == 'json':
            return self.generate_json_report()
        elif format == 'html':
            return self.generate_html_report()
        else:
            return self.generate_console_report()
    
    def generate_json_report(self) -> str:
        """生成JSON格式报告"""
        report_file = self.output_dir / f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        return str(report_file)
    
    def generate_html_report(self) -> str:
        """生成HTML格式报告"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Security Scan Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; }
        .summary { margin: 20px 0; }
        .critical { color: #d32f2f; font-weight: bold; }
        .high { color: #f57c00; font-weight: bold; }
        .medium { color: #fbc02d; font-weight: bold; }
        .low { color: #388e3c; }
        .section { margin: 30px 0; }
        .issues { margin: 10px 0; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .status-completed { color: green; }
        .status-failed { color: red; }
        .status-not_installed { color: orange; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Security Scan Report</h1>
        <p><strong>Project:</strong> {{ project_root }}</p>
        <p><strong>Timestamp:</strong> {{ timestamp }}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p><strong>Total Issues:</strong> {{ summary.total_issues }}</p>
        <ul>
            <li><span class="critical">Critical: {{ summary.critical }}</span></li>
            <li><span class="high">High: {{ summary.high }}</span></li>
            <li><span class="medium">Medium: {{ summary.medium }}</span></li>
            <li><span class="low">Low: {{ summary.low }}</span></li>
            <li>Info: {{ summary.info }}</li>
        </ul>
    </div>
    
    {% for scan_name, scan_data in scans.items() %}
    <div class="section">
        <h2>{{ scan_name.title() }} Scan Results</h2>
        <p><strong>Status:</strong> <span class="status-{{ scan_data.status }}">{{ scan_data.status }}</span></p>
        <p><strong>Issues Found:</strong> {{ scan_data.issues_count }}</p>
        
        {% if scan_data.issues %}
        <table>
            <thead>
                <tr>
                    <th>File</th>
                    <th>Line</th>
                    <th>Severity</th>
                    <th>Issue</th>
                </tr>
            </thead>
            <tbody>
                {% for issue in scan_data.issues[:10] %}  <!-- Show first 10 issues -->
                <tr>
                    <td>{{ issue.file }}</td>
                    <td>{{ issue.line or issue.get('line_number', 'N/A') }}</td>
                    <td><span class="{{ issue.severity }}">{{ issue.severity.upper() }}</span></td>
                    <td>{{ issue.issue or issue.description or issue.type or 'No description' }}</td>
                </tr>
                {% endfor %}
                {% if scan_data.issues|length > 10 %}
                <tr>
                    <td colspan="4"><em>... and {{ scan_data.issues|length - 10 }} more issues</em></td>
                </tr>
                {% endif %}
            </tbody>
        </table>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
        """
        
        template = Template(html_template)
        html_content = template.render(**self.results)
        
        report_file = self.output_dir / f"security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        return str(report_file)
    
    def generate_console_report(self) -> str:
        """生成控制台报告"""
        report = []
        report.append(f"\n{Fore.BLUE}{'='*60}")
        report.append(f"{Fore.BLUE}SECURITY SCAN REPORT")
        report.append(f"{Fore.BLUE}{'='*60}")
        report.append(f"Project: {self.results['project_root']}")
        report.append(f"Timestamp: {self.results['timestamp']}")
        report.append("")
        
        # 汇总信息
        summary = self.results['summary']
        report.append(f"{Fore.CYAN}SUMMARY:")
        report.append(f"Total Issues: {summary['total_issues']}")
        report.append(f"  {Fore.RED}Critical: {summary['critical']}")
        report.append(f"  {Fore.YELLOW}High: {summary['high']}")  
        report.append(f"  {Fore.BLUE}Medium: {summary['medium']}")
        report.append(f"  {Fore.GREEN}Low: {summary['low']}")
        report.append(f"  Info: {summary['info']}")
        report.append("")
        
        # 各扫描工具结果
        for scan_name, scan_data in self.results['scans'].items():
            report.append(f"{Fore.CYAN}{scan_name.upper()} SCAN:")
            report.append(f"Status: {scan_data['status']}")
            report.append(f"Issues: {scan_data['issues_count']}")
            
            if scan_data.get('issues') and len(scan_data['issues']) > 0:
                report.append("Top Issues:")
                for i, issue in enumerate(scan_data['issues'][:3]):  # Show top 3 issues
                    severity_color = {
                        'critical': Fore.RED,
                        'high': Fore.YELLOW,
                        'medium': Fore.BLUE,
                        'low': Fore.GREEN
                    }.get(issue.get('severity', 'low'), Fore.WHITE)
                    
                    file_path = issue.get('file', 'Unknown')
                    line = issue.get('line', issue.get('line_number', 'N/A'))
                    description = (issue.get('issue') or issue.get('description') or 
                                 issue.get('type') or 'No description')
                    
                    report.append(f"  {i+1}. {severity_color}{issue.get('severity', 'unknown').upper()}{Style.RESET_ALL} "
                                f"in {file_path}:{line} - {description}")
            report.append("")
        
        console_report = '\n'.join(report)
        click.echo(console_report)
        return console_report


@click.command()
@click.option('--project-root', '-p', type=click.Path(exists=True, path_type=Path), 
              default='.', help='Project root directory')
@click.option('--output-dir', '-o', type=click.Path(path_type=Path), 
              help='Output directory for reports')
@click.option('--format', '-f', type=click.Choice(['console', 'json', 'html']), 
              default='console', help='Report format')
@click.option('--scan', '-s', multiple=True, 
              type=click.Choice(['bandit', 'safety', 'secrets', 'aws', 'all']),
              default=['all'], help='Specific scans to run')
@click.option('--fail-on-high', is_flag=True, default=False, 
              help='Exit with non-zero code if high/critical issues found')
def main(project_root: Path, output_dir: Optional[Path], format: str, 
         scan: List[str], fail_on_high: bool):
    """
    AI PPT Assistant 安全扫描工具
    
    运行多种安全扫描并生成综合报告
    """
    click.echo(f"{Fore.GREEN}AI PPT Assistant Security Scanner{Style.RESET_ALL}")
    click.echo(f"Scanning project: {project_root.resolve()}")
    
    scanner = SecurityScanner(project_root, output_dir)
    
    # 运行指定的扫描
    if 'all' in scan:
        results = scanner.run_all_scans()
    else:
        scanner.log_info("Running selected scans...")
        if 'bandit' in scan:
            scanner.results['scans']['bandit'] = scanner.run_bandit_scan()
        if 'safety' in scan:
            scanner.results['scans']['safety'] = scanner.run_safety_scan()
        if 'secrets' in scan:
            scanner.results['scans']['secrets'] = scanner.run_secrets_scan()
        if 'aws' in scan:
            scanner.results['scans']['aws'] = scanner.run_aws_security_scan()
        
        results = scanner.results
    
    # 生成报告
    report_file = scanner.generate_report(format)
    
    if format in ['json', 'html']:
        scanner.log_success(f"Report generated: {report_file}")
    
    # 检查是否需要因高危问题失败
    if fail_on_high:
        high_critical_count = results['summary']['critical'] + results['summary']['high']
        if high_critical_count > 0:
            scanner.log_error(f"Found {high_critical_count} high/critical security issues!")
            sys.exit(1)
    
    scanner.log_success("Security scan completed!")


if __name__ == '__main__':
    main()