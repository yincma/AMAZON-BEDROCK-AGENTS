#!/usr/bin/env python3
"""
安全扫描系统验证脚本
验证所有组件是否正确安装和配置
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple

# 颜色定义
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[0;37m'
    RESET = '\033[0m'

def log_info(message: str):
    """记录信息日志"""
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {message}")

def log_success(message: str):
    """记录成功日志"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.RESET} {message}")

def log_warning(message: str):
    """记录警告日志"""
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {message}")

def log_error(message: str):
    """记录错误日志"""
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {message}")

def check_python_version() -> bool:
    """检查Python版本"""
    log_info("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        log_success(f"Python {version.major}.{version.minor}.{version.micro} ✓")
        return True
    else:
        log_error(f"Python {version.major}.{version.minor}.{version.micro} is too old. Requires Python 3.8+")
        return False

def check_virtual_environment() -> bool:
    """检查虚拟环境"""
    log_info("Checking virtual environment...")
    
    project_root = Path(__file__).parent.parent
    venv_path = project_root / ".venv"
    
    if venv_path.exists():
        log_success(f"Virtual environment found at {venv_path} ✓")
        return True
    else:
        log_error(f"Virtual environment not found at {venv_path}")
        log_info("Run 'make install' to create virtual environment")
        return False

def check_file_exists(file_path: Path, description: str) -> bool:
    """检查文件是否存在"""
    if file_path.exists():
        log_success(f"{description}: {file_path} ✓")
        return True
    else:
        log_error(f"{description}: {file_path} not found")
        return False

def check_security_files() -> bool:
    """检查安全扫描相关文件"""
    log_info("Checking security scan files...")
    
    security_dir = Path(__file__).parent
    files_to_check = [
        (security_dir / "requirements.txt", "Security requirements"),
        (security_dir / "scan.py", "Main scan script"),
        (security_dir / "install.sh", "Install script"),
        (security_dir / "bandit.yaml", "Bandit configuration"),
        (security_dir / "checkov.yaml", "Checkov configuration"),
        (security_dir / ".secrets.baseline", "Secrets baseline"),
        (security_dir / "README.md", "Documentation"),
    ]
    
    all_exist = True
    for file_path, description in files_to_check:
        if not check_file_exists(file_path, description):
            all_exist = False
    
    return all_exist

def check_tool_installation(tool_name: str, version_cmd: List[str]) -> Tuple[bool, str]:
    """检查工具是否安装"""
    try:
        result = subprocess.run(version_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            return True, version
        else:
            return False, f"Command failed with return code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except FileNotFoundError:
        return False, "Command not found"
    except Exception as e:
        return False, str(e)

def check_security_tools() -> Dict[str, bool]:
    """检查安全扫描工具"""
    log_info("Checking security tools installation...")
    
    tools = {
        'bandit': ['bandit', '--version'],
        'safety': ['safety', '--version'],
        'detect-secrets': ['detect-secrets', '--version'],
        'checkov': ['checkov', '--version'],
        'pip-audit': ['pip-audit', '--version'],
    }
    
    results = {}
    for tool_name, version_cmd in tools.items():
        installed, info = check_tool_installation(tool_name, version_cmd)
        if installed:
            log_success(f"{tool_name}: {info.split()[0] if info else 'installed'} ✓")
        else:
            log_error(f"{tool_name}: {info}")
        results[tool_name] = installed
    
    return results

def test_scan_script() -> bool:
    """测试扫描脚本是否可以运行"""
    log_info("Testing scan script...")
    
    scan_script = Path(__file__).parent / "scan.py"
    
    try:
        # 测试帮助命令
        result = subprocess.run([
            sys.executable, str(scan_script), '--help'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            log_success("Scan script help command works ✓")
            return True
        else:
            log_error(f"Scan script failed: {result.stderr}")
            return False
    except Exception as e:
        log_error(f"Failed to test scan script: {e}")
        return False

def check_makefile_targets() -> bool:
    """检查Makefile目标"""
    log_info("Checking Makefile targets...")
    
    project_root = Path(__file__).parent.parent
    makefile_path = project_root / "Makefile"
    
    if not makefile_path.exists():
        log_error("Makefile not found")
        return False
    
    try:
        with open(makefile_path, 'r') as f:
            content = f.read()
        
        required_targets = [
            'security-install',
            'security-scan',
            'security-scan-ci',
            'security-report'
        ]
        
        all_found = True
        for target in required_targets:
            if target in content:
                log_success(f"Makefile target '{target}' found ✓")
            else:
                log_error(f"Makefile target '{target}' not found")
                all_found = False
        
        return all_found
    except Exception as e:
        log_error(f"Failed to check Makefile: {e}")
        return False

def check_github_actions() -> bool:
    """检查GitHub Actions工作流"""
    log_info("Checking GitHub Actions workflow...")
    
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "security.yml"
    
    return check_file_exists(workflow_path, "GitHub Actions security workflow")

def generate_validation_report() -> Dict:
    """生成验证报告"""
    log_info("Generating validation report...")
    
    # 运行所有检查
    checks = {
        'python_version': check_python_version(),
        'virtual_environment': check_virtual_environment(),
        'security_files': check_security_files(),
        'makefile_targets': check_makefile_targets(),
        'github_actions': check_github_actions(),
        'scan_script_test': False,  # 如果工具未安装，先跳过
    }
    
    # 检查工具安装
    tool_results = check_security_tools()
    checks.update({f'tool_{tool}': result for tool, result in tool_results.items()})
    
    # 如果基本工具安装了，测试扫描脚本
    if tool_results.get('bandit', False):
        checks['scan_script_test'] = test_scan_script()
    
    # 计算总体状态
    total_checks = len(checks)
    passed_checks = sum(checks.values())
    
    report = {
        'total_checks': total_checks,
        'passed_checks': passed_checks,
        'success_rate': (passed_checks / total_checks) * 100,
        'checks': checks
    }
    
    return report

def print_summary(report: Dict):
    """打印验证摘要"""
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"{Colors.CYAN}SECURITY SCAN SYSTEM VALIDATION REPORT")
    print(f"{Colors.CYAN}{'='*60}")
    
    success_rate = report['success_rate']
    passed = report['passed_checks']
    total = report['total_checks']
    
    if success_rate >= 90:
        status_color = Colors.GREEN
        status = "EXCELLENT"
    elif success_rate >= 75:
        status_color = Colors.YELLOW
        status = "GOOD"
    elif success_rate >= 50:
        status_color = Colors.YELLOW
        status = "PARTIAL"
    else:
        status_color = Colors.RED
        status = "FAILED"
    
    print(f"\nOverall Status: {status_color}{status}{Colors.RESET}")
    print(f"Checks Passed: {Colors.GREEN}{passed}{Colors.RESET}/{total} ({success_rate:.1f}%)")
    
    # 详细结果
    print(f"\n{Colors.CYAN}Detailed Results:")
    print(f"{Colors.CYAN}-" * 40)
    
    categories = {
        'Environment': ['python_version', 'virtual_environment'],
        'Configuration Files': ['security_files', 'makefile_targets', 'github_actions'],
        'Security Tools': [k for k in report['checks'].keys() if k.startswith('tool_')],
        'Functionality': ['scan_script_test']
    }
    
    for category, check_keys in categories.items():
        print(f"\n{Colors.WHITE}{category}:{Colors.RESET}")
        for key in check_keys:
            if key in report['checks']:
                status = report['checks'][key]
                icon = "✓" if status else "✗"
                color = Colors.GREEN if status else Colors.RED
                display_name = key.replace('tool_', '').replace('_', ' ').title()
                print(f"  {color}{icon} {display_name}{Colors.RESET}")
    
    # 推荐下一步
    print(f"\n{Colors.CYAN}Next Steps:")
    print(f"{Colors.CYAN}-" * 40)
    
    if success_rate < 50:
        print(f"{Colors.RED}• Run setup: make install{Colors.RESET}")
        print(f"{Colors.RED}• Install security tools: make security-install{Colors.RESET}")
    elif success_rate < 90:
        print(f"{Colors.YELLOW}• Install missing tools: make security-install{Colors.RESET}")
        print(f"{Colors.YELLOW}• Check specific failed components{Colors.RESET}")
    else:
        print(f"{Colors.GREEN}• System ready! Try: make security-scan{Colors.RESET}")
        print(f"{Colors.GREEN}• Generate report: make security-report{Colors.RESET}")
    
    print()

def main():
    """主函数"""
    print(f"{Colors.GREEN}AI PPT Assistant Security Scan System Validator{Colors.RESET}")
    print(f"Validating security scanning system installation and configuration...\n")
    
    report = generate_validation_report()
    print_summary(report)
    
    # 根据成功率设置退出码
    if report['success_rate'] >= 75:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()