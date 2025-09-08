#!/usr/bin/env python3
"""
Coverage Report Generator

This script generates comprehensive coverage reports with badges and summaries
for the AI PPT Assistant project. It supports multiple output formats and
provides detailed analysis of test coverage.
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET


class CoverageReportGenerator:
    """Generates comprehensive coverage reports and badges."""
    
    def __init__(self, project_root: str = None):
        """Initialize with project root directory."""
        self.project_root = Path(project_root or os.getcwd())
        self.coverage_dir = self.project_root / "htmlcov"
        self.reports_dir = self.project_root / "test-results"
        self.badges_dir = self.reports_dir / "badges"
        
        # Ensure directories exist
        self.coverage_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        self.badges_dir.mkdir(exist_ok=True)
    
    def run_coverage_analysis(self, test_type: str = "all") -> Dict[str, Any]:
        """Run coverage analysis and generate reports."""
        print(f"🔍 Running coverage analysis for: {test_type}")
        
        # Coverage commands based on test type
        coverage_commands = {
            "unit": [
                "coverage", "run", "--rcfile=tests/coverage.ini", 
                "-m", "pytest", "tests/unit", "-v"
            ],
            "integration": [
                "coverage", "run", "--rcfile=tests/coverage.ini", 
                "-m", "pytest", "tests/integration", "-v"
            ],
            "api": [
                "coverage", "run", "--rcfile=tests/coverage.ini",
                "-m", "pytest", "tests/integration/api_tests.py", "-v"
            ],
            "all": [
                "coverage", "run", "--rcfile=tests/coverage.ini",
                "-m", "pytest", "tests/", "-v"
            ]
        }
        
        if test_type not in coverage_commands:
            raise ValueError(f"Invalid test type: {test_type}")
        
        try:
            # Run coverage
            result = subprocess.run(
                coverage_commands[test_type],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False
            )
            
            print(f"Coverage command exit code: {result.returncode}")
            if result.stdout:
                print("STDOUT:", result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr)
            
            return self._analyze_coverage_results()
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Coverage analysis failed: {e}")
            return {"error": str(e), "coverage_percentage": 0.0}
    
    def _analyze_coverage_results(self) -> Dict[str, Any]:
        """Analyze coverage results from generated reports."""
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "coverage_percentage": 0.0,
            "total_statements": 0,
            "covered_statements": 0,
            "missing_lines": 0,
            "branch_coverage": 0.0,
            "file_coverage": {}
        }
        
        try:
            # Generate coverage reports
            subprocess.run(["coverage", "xml"], cwd=self.project_root, check=True)
            subprocess.run(["coverage", "json"], cwd=self.project_root, check=True)
            subprocess.run(["coverage", "html"], cwd=self.project_root, check=True)
            
            # Parse XML coverage report
            xml_path = self.project_root / "coverage.xml"
            if xml_path.exists():
                analysis.update(self._parse_xml_coverage(xml_path))
            
            # Parse JSON coverage report  
            json_path = self.project_root / "coverage.json"
            if json_path.exists():
                analysis.update(self._parse_json_coverage(json_path))
            
            print(f"✅ Coverage analysis complete: {analysis['coverage_percentage']:.2f}%")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Error generating coverage reports: {e}")
        
        return analysis
    
    def _parse_xml_coverage(self, xml_path: Path) -> Dict[str, Any]:
        """Parse XML coverage report."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extract overall coverage
            line_rate = float(root.get('line-rate', 0))
            branch_rate = float(root.get('branch-rate', 0))
            
            # Extract totals
            lines_covered = int(root.get('lines-covered', 0))
            lines_valid = int(root.get('lines-valid', 0))
            branches_covered = int(root.get('branches-covered', 0))
            branches_valid = int(root.get('branches-valid', 0))
            
            return {
                "coverage_percentage": line_rate * 100,
                "branch_coverage": branch_rate * 100,
                "total_statements": lines_valid,
                "covered_statements": lines_covered,
                "missing_lines": lines_valid - lines_covered,
                "total_branches": branches_valid,
                "covered_branches": branches_covered
            }
            
        except Exception as e:
            print(f"⚠️ Error parsing XML coverage: {e}")
            return {}
    
    def _parse_json_coverage(self, json_path: Path) -> Dict[str, Any]:
        """Parse JSON coverage report for detailed file information."""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            file_coverage = {}
            
            # Extract file-level coverage
            for filename, file_data in data.get('files', {}).items():
                # Skip files outside lambdas directory
                if not filename.startswith('lambdas/'):
                    continue
                
                summary = file_data.get('summary', {})
                file_coverage[filename] = {
                    "covered_lines": summary.get('covered_lines', 0),
                    "num_statements": summary.get('num_statements', 0),
                    "percent_covered": summary.get('percent_covered', 0.0),
                    "missing_lines": file_data.get('missing_lines', []),
                    "excluded_lines": file_data.get('excluded_lines', [])
                }
            
            return {"file_coverage": file_coverage}
            
        except Exception as e:
            print(f"⚠️ Error parsing JSON coverage: {e}")
            return {}
    
    def generate_coverage_badge(self, coverage_percentage: float) -> str:
        """Generate coverage badge JSON."""
        # Determine color based on coverage percentage
        if coverage_percentage >= 90:
            color = "brightgreen"
        elif coverage_percentage >= 80:
            color = "green" 
        elif coverage_percentage >= 70:
            color = "yellowgreen"
        elif coverage_percentage >= 60:
            color = "yellow"
        elif coverage_percentage >= 50:
            color = "orange"
        else:
            color = "red"
        
        badge_data = {
            "schemaVersion": 1,
            "label": "coverage",
            "message": f"{coverage_percentage:.1f}%",
            "color": color
        }
        
        # Save badge JSON
        badge_path = self.badges_dir / "coverage-badge.json"
        with open(badge_path, 'w') as f:
            json.dump(badge_data, f, indent=2)
        
        print(f"✅ Coverage badge generated: {badge_path}")
        return str(badge_path)
    
    def generate_summary_report(self, analysis: Dict[str, Any], test_type: str) -> str:
        """Generate comprehensive summary report."""
        summary_path = self.reports_dir / f"coverage-summary-{test_type}.md"
        
        with open(summary_path, 'w') as f:
            f.write(f"# Coverage Report - {test_type.title()}\n\n")
            f.write(f"**Generated:** {analysis.get('timestamp', 'Unknown')}\n")
            f.write(f"**Test Type:** {test_type}\n\n")
            
            # Overall metrics
            f.write("## Overall Coverage\n\n")
            f.write(f"- **Line Coverage:** {analysis.get('coverage_percentage', 0):.2f}%\n")
            f.write(f"- **Branch Coverage:** {analysis.get('branch_coverage', 0):.2f}%\n")
            f.write(f"- **Total Statements:** {analysis.get('total_statements', 0)}\n")
            f.write(f"- **Covered Statements:** {analysis.get('covered_statements', 0)}\n")
            f.write(f"- **Missing Lines:** {analysis.get('missing_lines', 0)}\n\n")
            
            # Coverage by file
            file_coverage = analysis.get('file_coverage', {})
            if file_coverage:
                f.write("## Coverage by File\n\n")
                f.write("| File | Coverage | Statements | Missing |\n")
                f.write("|------|----------|------------|---------|\n")
                
                # Sort files by coverage percentage (ascending)
                sorted_files = sorted(
                    file_coverage.items(),
                    key=lambda x: x[1].get('percent_covered', 0)
                )
                
                for filename, data in sorted_files:
                    coverage = data.get('percent_covered', 0)
                    statements = data.get('num_statements', 0)
                    missing = len(data.get('missing_lines', []))
                    
                    # Format filename for display
                    display_name = filename.replace('lambdas/', '').replace('.py', '')
                    
                    f.write(f"| `{display_name}` | {coverage:.1f}% | {statements} | {missing} |\n")
            
            # Low coverage files (< 70%)
            low_coverage_files = [
                (filename, data) for filename, data in file_coverage.items()
                if data.get('percent_covered', 0) < 70
            ]
            
            if low_coverage_files:
                f.write("\n## Files Needing Attention (< 70% coverage)\n\n")
                for filename, data in low_coverage_files:
                    coverage = data.get('percent_covered', 0)
                    missing_lines = data.get('missing_lines', [])
                    
                    f.write(f"### `{filename}`\n")
                    f.write(f"- Coverage: {coverage:.1f}%\n")
                    f.write(f"- Missing lines: {len(missing_lines)}\n")
                    
                    if missing_lines and len(missing_lines) <= 20:
                        f.write(f"- Line numbers: {', '.join(map(str, missing_lines))}\n")
                    elif missing_lines:
                        f.write(f"- Line numbers: {', '.join(map(str, missing_lines[:10]))}... (and {len(missing_lines) - 10} more)\n")
                    f.write("\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            overall_coverage = analysis.get('coverage_percentage', 0)
            
            if overall_coverage >= 90:
                f.write("✅ **Excellent coverage!** Your codebase is well tested.\n")
            elif overall_coverage >= 80:
                f.write("🟢 **Good coverage.** Consider improving coverage for files below 80%.\n")
            elif overall_coverage >= 70:
                f.write("🟡 **Acceptable coverage.** Focus on increasing coverage for critical components.\n")
            else:
                f.write("🔴 **Coverage needs improvement.** Prioritize adding tests for uncovered code.\n")
            
            f.write("\n### Next Steps\n")
            f.write("- Review files with low coverage\n")
            f.write("- Add tests for critical business logic\n")
            f.write("- Focus on edge cases and error handling\n")
            f.write("- Consider integration tests for complex workflows\n")
        
        print(f"✅ Summary report generated: {summary_path}")
        return str(summary_path)
    
    def generate_html_dashboard(self, analysis: Dict[str, Any], test_type: str) -> str:
        """Generate interactive HTML dashboard."""
        dashboard_path = self.reports_dir / f"coverage-dashboard-{test_type}.html"
        
        # Basic HTML template with embedded CSS and JavaScript
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coverage Dashboard - {test_type.title()}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .metric-card {{ display: inline-block; margin: 10px; padding: 20px; background: #f8f9fa; border-radius: 8px; text-align: center; min-width: 150px; }}
        .metric-value {{ font-size: 2em; font-weight: bold; margin-bottom: 5px; }}
        .metric-label {{ color: #666; text-transform: uppercase; font-size: 0.8em; }}
        .coverage-high {{ color: #28a745; }}
        .coverage-medium {{ color: #ffc107; }}
        .coverage-low {{ color: #dc3545; }}
        .file-list {{ margin-top: 30px; }}
        .file-item {{ margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }}
        .file-name {{ font-family: monospace; }}
        .coverage-bar {{ width: 100px; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }}
        .coverage-fill {{ height: 100%; background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%); border-radius: 10px; }}
        .timestamp {{ color: #666; font-size: 0.9em; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Coverage Dashboard</h1>
            <h2>Test Type: {test_type.title()}</h2>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value coverage-{self._get_coverage_class(analysis.get('coverage_percentage', 0))}">{analysis.get('coverage_percentage', 0):.1f}%</div>
                <div class="metric-label">Line Coverage</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value coverage-{self._get_coverage_class(analysis.get('branch_coverage', 0))}">{analysis.get('branch_coverage', 0):.1f}%</div>
                <div class="metric-label">Branch Coverage</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{analysis.get('covered_statements', 0)}</div>
                <div class="metric-label">Covered Lines</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{analysis.get('missing_lines', 0)}</div>
                <div class="metric-label">Missing Lines</div>
            </div>
        </div>
        
        <div class="file-list">
            <h3>File Coverage Details</h3>
        """
        
        # Add file coverage details
        file_coverage = analysis.get('file_coverage', {})
        for filename, data in sorted(file_coverage.items(), key=lambda x: x[1].get('percent_covered', 0)):
            coverage = data.get('percent_covered', 0)
            statements = data.get('num_statements', 0)
            missing = len(data.get('missing_lines', []))
            
            display_name = filename.replace('lambdas/', '').replace('.py', '')
            coverage_class = self._get_coverage_class(coverage)
            
            html_content += f"""
            <div class="file-item">
                <div class="file-name">{display_name}</div>
                <div>
                    <span class="coverage-{coverage_class}">{coverage:.1f}%</span>
                    <span style="color: #666; margin-left: 10px;">({statements} statements, {missing} missing)</span>
                    <div class="coverage-bar" style="margin-top: 5px;">
                        <div class="coverage-fill" style="width: {coverage}%;"></div>
                    </div>
                </div>
            </div>
            """
        
        html_content += f"""
        </div>
        
        <div class="timestamp">
            Generated: {analysis.get('timestamp', 'Unknown')}
        </div>
    </div>
</body>
</html>
        """
        
        with open(dashboard_path, 'w') as f:
            f.write(html_content)
        
        print(f"✅ HTML dashboard generated: {dashboard_path}")
        return str(dashboard_path)
    
    def _get_coverage_class(self, coverage: float) -> str:
        """Get CSS class based on coverage percentage."""
        if coverage >= 80:
            return "high"
        elif coverage >= 60:
            return "medium"
        else:
            return "low"
    
    def cleanup_old_reports(self, days: int = 7) -> None:
        """Clean up old coverage reports."""
        import time
        from pathlib import Path
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for report_file in self.reports_dir.glob("coverage-*"):
            if report_file.stat().st_mtime < cutoff_time:
                report_file.unlink()
                print(f"🗑️ Cleaned up old report: {report_file}")


def main():
    """Main entry point for the coverage report generator."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive coverage reports for AI PPT Assistant"
    )
    parser.add_argument(
        "--test-type",
        choices=["unit", "integration", "api", "all"],
        default="all",
        help="Type of tests to analyze coverage for"
    )
    parser.add_argument(
        "--project-root",
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--cleanup-days",
        type=int,
        default=7,
        help="Clean up reports older than this many days"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests, just generate reports from existing coverage data"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize generator
        generator = CoverageReportGenerator(args.project_root)
        
        print("🚀 Starting coverage report generation...")
        print(f"Project root: {generator.project_root}")
        print(f"Test type: {args.test_type}")
        
        if args.skip_tests:
            print("⏩ Skipping test execution, using existing coverage data")
            analysis = generator._analyze_coverage_results()
        else:
            # Run coverage analysis
            analysis = generator.run_coverage_analysis(args.test_type)
        
        if "error" in analysis:
            print(f"❌ Coverage analysis failed: {analysis['error']}")
            sys.exit(1)
        
        # Generate reports
        coverage_percentage = analysis.get('coverage_percentage', 0)
        print(f"📊 Overall coverage: {coverage_percentage:.2f}%")
        
        # Generate badge
        generator.generate_coverage_badge(coverage_percentage)
        
        # Generate summary report
        generator.generate_summary_report(analysis, args.test_type)
        
        # Generate HTML dashboard
        generator.generate_html_dashboard(analysis, args.test_type)
        
        # Cleanup old reports
        if args.cleanup_days > 0:
            generator.cleanup_old_reports(args.cleanup_days)
        
        print("✅ Coverage report generation complete!")
        print(f"📈 Coverage: {coverage_percentage:.2f}%")
        print(f"📁 Reports available in: {generator.reports_dir}")
        
        # Exit with appropriate code based on coverage
        if coverage_percentage < 60:
            print("⚠️ Coverage is below 60% - consider this a warning")
            sys.exit(1)
        elif coverage_percentage < 80:
            print("📝 Coverage is below 80% - room for improvement")
        else:
            print("🎉 Excellent coverage!")
        
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()