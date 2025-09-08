#!/usr/bin/env python3
"""
Integration Test Runner and Analyzer

This script provides a comprehensive solution for running integration tests,
analyzing results, and generating detailed reports for the AI PPT Assistant project.
"""

import os
import sys
import json
import argparse
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import xml.etree.ElementTree as ET


class IntegrationTestRunner:
    """Comprehensive integration test runner with analysis and reporting."""
    
    def __init__(self, project_root: str = None):
        """Initialize with project root directory."""
        self.project_root = Path(project_root or os.getcwd())
        self.test_dir = self.project_root / "tests"
        self.integration_dir = self.test_dir / "integration"
        self.results_dir = self.project_root / "test-results"
        self.logs_dir = self.project_root / "logs" / "integration"
        
        # Ensure directories exist
        self.results_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Test configuration
        self.test_categories = {
            "api": {
                "description": "API endpoint integration tests",
                "path": "tests/integration/api_tests.py",
                "markers": "integration and api",
                "timeout": 300
            },
            "smoke": {
                "description": "Smoke tests for quick validation",
                "path": "tests/integration/",
                "markers": "integration and smoke",
                "timeout": 120
            },
            "workflow": {
                "description": "End-to-end workflow tests",
                "path": "tests/integration/test_workflow.py",
                "markers": "integration and not slow",
                "timeout": 600
            },
            "performance": {
                "description": "Performance and load tests",
                "path": "tests/integration/api_tests.py::TestPerformanceBenchmarks",
                "markers": "integration and slow",
                "timeout": 900
            },
            "concurrent": {
                "description": "Concurrent request handling tests",
                "path": "tests/integration/api_tests.py::TestConcurrentRequests",
                "markers": "integration and concurrent",
                "timeout": 300
            },
            "error": {
                "description": "Error handling and edge case tests",
                "path": "tests/integration/api_tests.py::TestErrorHandlingAndEdgeCases",
                "markers": "integration and error_handling",
                "timeout": 180
            }
        }
    
    def list_available_tests(self) -> None:
        """List all available test categories."""
        print("Available test categories:")
        print("=" * 50)
        
        for category, config in self.test_categories.items():
            print(f"📋 {category.upper()}")
            print(f"   Description: {config['description']}")
            print(f"   Path: {config['path']}")
            print(f"   Markers: {config['markers']}")
            print(f"   Timeout: {config['timeout']}s")
            print()
    
    def run_tests(
        self, 
        categories: List[str] = None, 
        aws_mode: str = "mocked",
        verbose: bool = True,
        fail_fast: bool = False,
        parallel: bool = False
    ) -> Dict[str, Any]:
        """Run integration tests for specified categories."""
        if categories is None:
            categories = list(self.test_categories.keys())
        
        print(f"🚀 Starting integration test execution...")
        print(f"Categories: {', '.join(categories)}")
        print(f"AWS Mode: {aws_mode}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)
        
        results = {
            "start_time": datetime.now().isoformat(),
            "categories": categories,
            "aws_mode": aws_mode,
            "results": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 0,
                "total_duration": 0.0
            }
        }
        
        # Setup environment
        self._setup_test_environment(aws_mode)
        
        # Run tests for each category
        for category in categories:
            if category not in self.test_categories:
                print(f"⚠️ Unknown test category: {category}")
                continue
            
            print(f"\n📊 Running {category.upper()} tests...")
            category_result = self._run_category_tests(
                category, 
                verbose=verbose,
                fail_fast=fail_fast,
                parallel=parallel
            )
            
            results["results"][category] = category_result
            
            # Update summary
            summary = category_result.get("summary", {})
            results["summary"]["total_tests"] += summary.get("total", 0)
            results["summary"]["passed"] += summary.get("passed", 0)
            results["summary"]["failed"] += summary.get("failed", 0)
            results["summary"]["skipped"] += summary.get("skipped", 0)
            results["summary"]["errors"] += summary.get("errors", 0)
            results["summary"]["total_duration"] += summary.get("duration", 0.0)
            
            # Stop on first failure if fail_fast is enabled
            if fail_fast and summary.get("failed", 0) > 0:
                print("🛑 Stopping on first failure (--fail-fast enabled)")
                break
        
        results["end_time"] = datetime.now().isoformat()
        
        # Save results
        self._save_test_results(results)
        
        # Generate reports
        self._generate_test_reports(results)
        
        return results
    
    def _setup_test_environment(self, aws_mode: str) -> None:
        """Setup test environment variables."""
        env_vars = {
            "ENVIRONMENT": "integration_test",
            "LOG_LEVEL": "DEBUG",
            "PYTEST_CURRENT_TEST": "true",
            "TEST_MODE": "integration",
            "AWS_DEFAULT_REGION": "us-east-1"
        }
        
        if aws_mode == "mocked":
            env_vars.update({
                "AWS_ACCESS_KEY_ID": "testing",
                "AWS_SECRET_ACCESS_KEY": "testing",
                "AWS_SECURITY_TOKEN": "testing",
                "AWS_SESSION_TOKEN": "testing",
                "USE_MOCKED_AWS": "true"
            })
        
        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
        
        print(f"✅ Test environment configured for {aws_mode} mode")
    
    def _run_category_tests(
        self, 
        category: str, 
        verbose: bool = True,
        fail_fast: bool = False,
        parallel: bool = False
    ) -> Dict[str, Any]:
        """Run tests for a specific category."""
        config = self.test_categories[category]
        start_time = time.time()
        
        # Build pytest command
        cmd = [
            "python", "-m", "pytest",
            config["path"],
            "-v" if verbose else "-q",
            f"--tb=short",
            f"--timeout={config['timeout']}",
            f"--junitxml={self.results_dir}/junit-{category}.xml",
            f"--html={self.results_dir}/report-{category}.html",
            "--self-contained-html",
            f"--json-report",
            f"--json-report-file={self.results_dir}/json-{category}.json"
        ]
        
        # Add markers if specified
        if config["markers"]:
            cmd.extend(["-m", config["markers"]])
        
        # Add additional options
        if fail_fast:
            cmd.append("--maxfail=1")
        
        if parallel and category in ["api", "concurrent"]:
            cmd.extend(["-n", "auto"])  # Requires pytest-xdist
        
        # Coverage options for detailed analysis
        cmd.extend([
            "--cov=lambdas",
            f"--cov-report=xml:{self.results_dir}/coverage-{category}.xml",
            f"--cov-report=html:{self.results_dir}/htmlcov-{category}",
            "--cov-report=term-missing"
        ])
        
        print(f"🔧 Command: {' '.join(cmd)}")
        
        try:
            # Run the tests
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=config["timeout"] + 60  # Add buffer time
            )
            
            duration = time.time() - start_time
            
            # Parse results
            test_result = self._parse_test_results(category, result, duration)
            
            # Log output
            self._log_test_output(category, result, test_result)
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ Tests timed out after {duration:.2f}s")
            
            return {
                "category": category,
                "status": "timeout",
                "duration": duration,
                "summary": {"total": 0, "passed": 0, "failed": 1, "skipped": 0, "errors": 0},
                "error": f"Tests timed out after {config['timeout'] + 60}s"
            }
        
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 Error running {category} tests: {e}")
            
            return {
                "category": category,
                "status": "error",
                "duration": duration,
                "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 1},
                "error": str(e)
            }
    
    def _parse_test_results(self, category: str, result: subprocess.CompletedProcess, duration: float) -> Dict[str, Any]:
        """Parse test results from subprocess output."""
        test_result = {
            "category": category,
            "duration": duration,
            "exit_code": result.returncode,
            "status": "passed" if result.returncode == 0 else "failed",
            "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}
        }
        
        # Parse JUnit XML if available
        junit_path = self.results_dir / f"junit-{category}.xml"
        if junit_path.exists():
            test_result["summary"] = self._parse_junit_xml(junit_path)
        
        # Parse JSON report if available
        json_path = self.results_dir / f"json-{category}.json"
        if json_path.exists():
            json_data = self._parse_json_report(json_path)
            test_result.update(json_data)
        
        # Extract key information from stdout
        stdout_lines = result.stdout.split('\n') if result.stdout else []
        stderr_lines = result.stderr.split('\n') if result.stderr else []
        
        # Look for pytest summary line
        for line in stdout_lines:
            if "passed" in line and ("failed" in line or "error" in line or "skipped" in line):
                test_result["pytest_summary"] = line.strip()
                break
        
        # Capture important output
        test_result["stdout_sample"] = '\n'.join(stdout_lines[-20:]) if stdout_lines else ""
        test_result["stderr_sample"] = '\n'.join(stderr_lines[-10:]) if stderr_lines else ""
        
        return test_result
    
    def _parse_junit_xml(self, junit_path: Path) -> Dict[str, int]:
        """Parse JUnit XML for test summary."""
        try:
            tree = ET.parse(junit_path)
            root = tree.getroot()
            
            # Get test counts from testsuites or testsuite element
            if root.tag == "testsuites":
                testsuite = root.find("testsuite")
                if testsuite is not None:
                    root = testsuite
            
            return {
                "total": int(root.get("tests", 0)),
                "passed": int(root.get("tests", 0)) - int(root.get("failures", 0)) - int(root.get("errors", 0)) - int(root.get("skipped", 0)),
                "failed": int(root.get("failures", 0)),
                "errors": int(root.get("errors", 0)),
                "skipped": int(root.get("skipped", 0))
            }
            
        except Exception as e:
            print(f"⚠️ Could not parse JUnit XML: {e}")
            return {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    
    def _parse_json_report(self, json_path: Path) -> Dict[str, Any]:
        """Parse JSON test report for additional details."""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Extract useful information
            summary = data.get("summary", {})
            
            return {
                "test_details": {
                    "total_duration": summary.get("duration", 0),
                    "setup_duration": data.get("setup_duration", 0),
                    "teardown_duration": data.get("teardown_duration", 0),
                    "num_tests": summary.get("total", 0),
                    "num_passed": summary.get("passed", 0),
                    "num_failed": summary.get("failed", 0),
                    "num_skipped": summary.get("skipped", 0),
                    "num_errors": summary.get("error", 0)
                },
                "failed_tests": [
                    test["nodeid"] for test in data.get("tests", []) 
                    if test.get("outcome") == "failed"
                ],
                "slow_tests": [
                    {"name": test["nodeid"], "duration": test["duration"]}
                    for test in data.get("tests", [])
                    if test.get("duration", 0) > 10  # Tests taking more than 10 seconds
                ]
            }
            
        except Exception as e:
            print(f"⚠️ Could not parse JSON report: {e}")
            return {}
    
    def _log_test_output(self, category: str, result: subprocess.CompletedProcess, test_result: Dict[str, Any]) -> None:
        """Log test output to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Log stdout
        stdout_path = self.logs_dir / f"{category}-{timestamp}-stdout.log"
        with open(stdout_path, 'w') as f:
            f.write(f"Category: {category}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Exit Code: {result.returncode}\n")
            f.write(f"Duration: {test_result['duration']:.2f}s\n")
            f.write("=" * 80 + "\n")
            f.write(result.stdout or "No stdout")
        
        # Log stderr if present
        if result.stderr:
            stderr_path = self.logs_dir / f"{category}-{timestamp}-stderr.log"
            with open(stderr_path, 'w') as f:
                f.write(f"Category: {category}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n")
                f.write(result.stderr)
        
        # Print summary
        summary = test_result["summary"]
        status = "✅ PASSED" if result.returncode == 0 else "❌ FAILED"
        print(f"{status} | {category.upper()} | "
              f"Total: {summary['total']}, "
              f"Passed: {summary['passed']}, "
              f"Failed: {summary['failed']}, "
              f"Duration: {test_result['duration']:.2f}s")
    
    def _save_test_results(self, results: Dict[str, Any]) -> None:
        """Save comprehensive test results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_path = self.results_dir / f"integration-results-{timestamp}.json"
        
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Also save as latest
        latest_path = self.results_dir / "integration-results-latest.json"
        with open(latest_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"💾 Results saved to {results_path}")
    
    def _generate_test_reports(self, results: Dict[str, Any]) -> None:
        """Generate comprehensive test reports."""
        self._generate_summary_report(results)
        self._generate_detailed_report(results)
        self._generate_failure_analysis(results)
    
    def _generate_summary_report(self, results: Dict[str, Any]) -> None:
        """Generate summary report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"summary-{timestamp}.md"
        
        summary = results["summary"]
        total_tests = summary["total_tests"]
        success_rate = (summary["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        with open(report_path, 'w') as f:
            f.write("# Integration Test Summary Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**Categories:** {', '.join(results['categories'])}\n")
            f.write(f"**AWS Mode:** {results['aws_mode']}\n\n")
            
            # Overall metrics
            f.write("## Overall Results\n\n")
            f.write(f"- **Total Tests:** {total_tests}\n")
            f.write(f"- **Passed:** {summary['passed']} ✅\n")
            f.write(f"- **Failed:** {summary['failed']} ❌\n")
            f.write(f"- **Skipped:** {summary['skipped']} ⏭️\n")
            f.write(f"- **Errors:** {summary['errors']} 💥\n")
            f.write(f"- **Success Rate:** {success_rate:.1f}%\n")
            f.write(f"- **Total Duration:** {summary['total_duration']:.2f}s\n\n")
            
            # Category breakdown
            f.write("## Results by Category\n\n")
            f.write("| Category | Status | Tests | Passed | Failed | Duration |\n")
            f.write("|----------|--------|-------|--------|--------|---------|\n")
            
            for category, result in results["results"].items():
                status_emoji = "✅" if result["status"] == "passed" else "❌"
                cat_summary = result.get("summary", {})
                
                f.write(f"| {category} | {status_emoji} {result['status']} | "
                       f"{cat_summary.get('total', 0)} | "
                       f"{cat_summary.get('passed', 0)} | "
                       f"{cat_summary.get('failed', 0)} | "
                       f"{result.get('duration', 0):.2f}s |\n")
            
            # Recommendations
            f.write("\n## Recommendations\n\n")
            if success_rate >= 95:
                f.write("🎉 **Excellent!** All tests are passing reliably.\n")
            elif success_rate >= 80:
                f.write("👍 **Good!** Most tests are passing. Review failed tests.\n")
            elif success_rate >= 60:
                f.write("⚠️ **Needs Attention!** Significant test failures detected.\n")
            else:
                f.write("🚨 **Critical!** Many tests are failing. Immediate action required.\n")
        
        print(f"📊 Summary report generated: {report_path}")
    
    def _generate_detailed_report(self, results: Dict[str, Any]) -> None:
        """Generate detailed HTML report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"detailed-report-{timestamp}.html"
        
        # Generate HTML content
        html_content = self._build_html_report(results)
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        print(f"📋 Detailed report generated: {report_path}")
    
    def _generate_failure_analysis(self, results: Dict[str, Any]) -> None:
        """Generate failure analysis report."""
        failures = []
        
        for category, result in results["results"].items():
            if result.get("status") != "passed":
                failed_tests = result.get("failed_tests", [])
                for test in failed_tests:
                    failures.append({
                        "category": category,
                        "test": test,
                        "duration": result.get("duration", 0)
                    })
        
        if not failures:
            print("🎉 No failures to analyze!")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_path = self.results_dir / f"failure-analysis-{timestamp}.md"
        
        with open(analysis_path, 'w') as f:
            f.write("# Test Failure Analysis\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n")
            f.write(f"**Total Failures:** {len(failures)}\n\n")
            
            f.write("## Failed Tests\n\n")
            for failure in failures:
                f.write(f"### {failure['category']}: {failure['test']}\n")
                f.write(f"- Duration: {failure['duration']:.2f}s\n")
                f.write("- Recommended Actions:\n")
                f.write("  - Check test logs for detailed error messages\n")
                f.write("  - Verify test environment setup\n")
                f.write("  - Review recent code changes\n\n")
        
        print(f"🔍 Failure analysis generated: {analysis_path}")
    
    def _build_html_report(self, results: Dict[str, Any]) -> str:
        """Build comprehensive HTML report."""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Integration Test Results - AI PPT Assistant</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .metrics {{ display: flex; justify-content: space-around; margin: 30px 0; }}
        .metric {{ text-align: center; padding: 20px; background: #f8f9fa; border-radius: 10px; }}
        .metric-value {{ font-size: 2.5em; font-weight: bold; margin-bottom: 10px; }}
        .metric-label {{ color: #666; text-transform: uppercase; font-size: 0.9em; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .error {{ color: #dc3545; }}
        .category-results {{ margin: 30px 0; }}
        .category {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        .category-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
        .status-badge {{ padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; }}
        .status-passed {{ background-color: #28a745; }}
        .status-failed {{ background-color: #dc3545; }}
        .progress-bar {{ width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin: 10px 0; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #28a745 0%, #ffc107 80%, #dc3545 100%); }}
        .timestamp {{ text-align: center; margin-top: 30px; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Integration Test Results</h1>
            <p>AI PPT Assistant - Comprehensive Test Analysis</p>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value success">{results['summary']['passed']}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric">
                <div class="metric-value error">{results['summary']['failed']}</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric">
                <div class="metric-value warning">{results['summary']['skipped']}</div>
                <div class="metric-label">Skipped</div>
            </div>
            <div class="metric">
                <div class="metric-value">{results['summary']['total_tests']}</div>
                <div class="metric-label">Total Tests</div>
            </div>
        </div>
        
        <div class="category-results">
            <h2>Results by Category</h2>
            {''.join(self._build_category_html(cat, res) for cat, res in results['results'].items())}
        </div>
        
        <div class="timestamp">
            Generated: {datetime.now().isoformat()}
        </div>
    </div>
</body>
</html>
        """
    
    def _build_category_html(self, category: str, result: Dict[str, Any]) -> str:
        """Build HTML for a test category."""
        summary = result.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        status_class = "status-passed" if result["status"] == "passed" else "status-failed"
        
        return f"""
        <div class="category">
            <div class="category-header">
                <h3>{category.upper()}</h3>
                <span class="status-badge {status_class}">{result['status'].upper()}</span>
            </div>
            <p>{self.test_categories[category]['description']}</p>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {success_rate}%;"></div>
            </div>
            <p>
                <strong>Tests:</strong> {total} | 
                <strong>Passed:</strong> {passed} | 
                <strong>Failed:</strong> {summary.get('failed', 0)} | 
                <strong>Duration:</strong> {result.get('duration', 0):.2f}s
            </p>
        </div>
        """
    
    def analyze_trends(self, days: int = 7) -> Dict[str, Any]:
        """Analyze test result trends over time."""
        print(f"📈 Analyzing test trends over the last {days} days...")
        
        # Find all result files within the time range
        cutoff_date = datetime.now() - timedelta(days=days)
        result_files = []
        
        for file_path in self.results_dir.glob("integration-results-*.json"):
            try:
                # Extract timestamp from filename
                timestamp_str = file_path.stem.split("-")[-2:]  # Get last two parts
                if len(timestamp_str) == 2:
                    file_date = datetime.strptime(f"{timestamp_str[0]}_{timestamp_str[1]}", "%Y%m%d_%H%M%S")
                    if file_date >= cutoff_date:
                        result_files.append((file_date, file_path))
            except (ValueError, IndexError):
                continue
        
        if not result_files:
            print("⚠️ No recent test results found for trend analysis")
            return {"error": "No data available"}
        
        # Sort by date
        result_files.sort(key=lambda x: x[0])
        
        # Analyze trends
        trend_data = {
            "period": f"Last {days} days",
            "total_runs": len(result_files),
            "success_rates": [],
            "duration_trends": [],
            "failure_patterns": {}
        }
        
        for file_date, file_path in result_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                summary = data.get("summary", {})
                total = summary.get("total_tests", 0)
                passed = summary.get("passed", 0)
                success_rate = (passed / total * 100) if total > 0 else 0
                
                trend_data["success_rates"].append({
                    "date": file_date.isoformat(),
                    "success_rate": success_rate,
                    "total_tests": total
                })
                
                trend_data["duration_trends"].append({
                    "date": file_date.isoformat(),
                    "duration": summary.get("total_duration", 0)
                })
                
            except Exception as e:
                print(f"⚠️ Could not parse {file_path}: {e}")
        
        self._save_trend_analysis(trend_data)
        return trend_data
    
    def _save_trend_analysis(self, trend_data: Dict[str, Any]) -> None:
        """Save trend analysis results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trend_path = self.results_dir / f"trend-analysis-{timestamp}.json"
        
        with open(trend_path, 'w') as f:
            json.dump(trend_data, f, indent=2, default=str)
        
        print(f"📊 Trend analysis saved to {trend_path}")


def main():
    """Main entry point for the integration test runner."""
    parser = argparse.ArgumentParser(
        description="Run and analyze integration tests for AI PPT Assistant"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available test categories')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run integration tests')
    run_parser.add_argument(
        '--categories', '-c',
        nargs='+',
        help='Test categories to run (default: all)'
    )
    run_parser.add_argument(
        '--aws-mode',
        choices=['mocked', 'real'],
        default='mocked',
        help='AWS services mode (default: mocked)'
    )
    run_parser.add_argument(
        '--fail-fast',
        action='store_true',
        help='Stop on first failure'
    )
    run_parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run tests in parallel where possible'
    )
    run_parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Reduce output verbosity'
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze test trends')
    analyze_parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )
    
    # Common arguments
    parser.add_argument(
        '--project-root',
        help='Project root directory (default: current directory)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        # Initialize runner
        runner = IntegrationTestRunner(args.project_root)
        
        if args.command == 'list':
            runner.list_available_tests()
        
        elif args.command == 'run':
            print("🚀 AI PPT Assistant - Integration Test Runner")
            print("=" * 60)
            
            results = runner.run_tests(
                categories=args.categories,
                aws_mode=args.aws_mode,
                verbose=not args.quiet,
                fail_fast=args.fail_fast,
                parallel=args.parallel
            )
            
            # Print final summary
            summary = results["summary"]
            total = summary["total_tests"]
            passed = summary["passed"]
            success_rate = (passed / total * 100) if total > 0 else 0
            
            print("\n" + "=" * 60)
            print("📊 FINAL RESULTS")
            print("=" * 60)
            print(f"Total Tests: {total}")
            print(f"Passed: {passed} ✅")
            print(f"Failed: {summary['failed']} ❌")
            print(f"Success Rate: {success_rate:.1f}%")
            print(f"Duration: {summary['total_duration']:.2f}s")
            
            # Exit with appropriate code
            if summary["failed"] > 0 or summary["errors"] > 0:
                print("\n❌ Some tests failed!")
                sys.exit(1)
            else:
                print("\n✅ All tests passed!")
        
        elif args.command == 'analyze':
            trend_data = runner.analyze_trends(args.days)
            
            if "error" not in trend_data:
                print(f"📈 Trend analysis complete:")
                print(f"   - Total runs: {trend_data['total_runs']}")
                print(f"   - Period: {trend_data['period']}")
                
                if trend_data['success_rates']:
                    latest_rate = trend_data['success_rates'][-1]['success_rate']
                    print(f"   - Latest success rate: {latest_rate:.1f}%")
    
    except KeyboardInterrupt:
        print("\n⏹️ Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()