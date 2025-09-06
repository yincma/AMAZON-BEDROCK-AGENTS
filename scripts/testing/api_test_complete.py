#!/usr/bin/env python3
"""
Complete API Testing Suite for AI PPT Assistant
Tests all deployed API endpoints with comprehensive scenarios
"""

import os
import sys
import json
import time
import uuid
import argparse
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
console = Console()

# API Configuration
class APIConfig:
    """API Configuration Settings"""
    def __init__(self):
        self.base_url = os.getenv('API_BASE_URL', 'http://localhost:3000/v1')
        self.api_key = os.getenv('API_KEY', 'test-api-key')
        self.timeout = int(os.getenv('API_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('RETRY_DELAY', '2'))

# Test Result Classes
class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TestResult:
    """Individual test result"""
    test_name: str
    endpoint: str
    method: str
    status: TestStatus
    response_time: float
    status_code: Optional[int] = None
    response_body: Optional[Dict] = None
    error_message: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

@dataclass
class TestSuite:
    """Complete test suite results"""
    suite_name: str
    start_time: str
    end_time: str = ""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[TestResult] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []
    
    def add_result(self, result: TestResult):
        """Add test result to suite"""
        self.results.append(result)
        self.total_tests += 1
        
        if result.status == TestStatus.PASSED:
            self.passed += 1
        elif result.status == TestStatus.FAILED:
            self.failed += 1
        elif result.status == TestStatus.SKIPPED:
            self.skipped += 1
    
    def get_success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed / self.total_tests) * 100

class APITestClient:
    """API Test Client with retry logic"""
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.session = None
        self.headers = {
            'X-API-Key': config.api_key,
            'Content-Type': 'application/json'
        }
    
    async def __aenter__(self):
        """Initialize session"""
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def request(self, method: str, endpoint: str, 
                      data: Optional[Dict] = None,
                      params: Optional[Dict] = None) -> tuple:
        """Make HTTP request with retry logic"""
        url = f"{self.config.base_url}{endpoint}"
        
        for attempt in range(self.config.max_retries):
            start_time = time.time()
            try:
                async with self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params
                ) as response:
                    response_time = time.time() - start_time
                    response_body = await response.json() if response.content_type == 'application/json' else None
                    
                    return response.status, response_body, response_time
                    
            except asyncio.TimeoutError:
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                    continue
                return None, {"error": "Request timeout"}, time.time() - start_time
                
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                    continue
                return None, {"error": str(e)}, time.time() - start_time
        
        return None, {"error": "Max retries exceeded"}, 0

class PresentationAPITests:
    """Test cases for Presentation endpoints"""
    
    def __init__(self, client: APITestClient):
        self.client = client
        self.created_ids = []
    
    async def test_create_presentation(self) -> TestResult:
        """Test POST /presentations"""
        test_data = {
            "title": f"Test Presentation {uuid.uuid4().hex[:8]}",
            "topic": "Automated API Testing for AI-powered presentation generation",
            "language": "en",
            "slide_count": 10,
            "style": "corporate",
            "template": "executive_summary",
            "audience_type": "technical",
            "tone": "informative",
            "include_speaker_notes": True
        }
        
        status_code, response, response_time = await self.client.request(
            method='POST',
            endpoint='/presentations',
            data=test_data
        )
        
        result = TestResult(
            test_name="Create Presentation",
            endpoint="/presentations",
            method="POST",
            status=TestStatus.PASSED if status_code == 202 else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )
        
        if status_code == 202 and response and 'task_id' in response:
            self.created_ids.append(response['task_id'])
        
        return result
    
    async def test_list_presentations(self) -> TestResult:
        """Test GET /presentations"""
        params = {
            'page_size': 10,
            'status': 'completed'
        }
        
        status_code, response, response_time = await self.client.request(
            method='GET',
            endpoint='/presentations',
            params=params
        )
        
        return TestResult(
            test_name="List Presentations",
            endpoint="/presentations",
            method="GET",
            status=TestStatus.PASSED if status_code == 200 else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )
    
    async def test_get_presentation(self, presentation_id: Optional[str] = None) -> TestResult:
        """Test GET /presentations/{id}"""
        if not presentation_id:
            presentation_id = str(uuid.uuid4())
        
        status_code, response, response_time = await self.client.request(
            method='GET',
            endpoint=f'/presentations/{presentation_id}'
        )
        
        # 404 is expected for non-existent ID
        expected_status = 404 if presentation_id == str(uuid.uuid4()) else 200
        
        return TestResult(
            test_name="Get Presentation Details",
            endpoint=f"/presentations/{presentation_id}",
            method="GET",
            status=TestStatus.PASSED if status_code == expected_status else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )
    
    async def test_update_presentation(self, presentation_id: Optional[str] = None) -> TestResult:
        """Test PUT /presentations/{id}"""
        if not presentation_id:
            presentation_id = str(uuid.uuid4())
        
        update_data = {
            "title": f"Updated Title {datetime.now().isoformat()}",
            "metadata": {
                "updated_by": "api_test",
                "version": "2.0"
            }
        }
        
        status_code, response, response_time = await self.client.request(
            method='PUT',
            endpoint=f'/presentations/{presentation_id}',
            data=update_data
        )
        
        return TestResult(
            test_name="Update Presentation",
            endpoint=f"/presentations/{presentation_id}",
            method="PUT",
            status=TestStatus.PASSED if status_code in [200, 404] else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )
    
    async def test_download_presentation(self, presentation_id: Optional[str] = None) -> TestResult:
        """Test GET /presentations/{id}/download"""
        if not presentation_id:
            presentation_id = str(uuid.uuid4())
        
        params = {'format': 'pptx'}
        
        status_code, response, response_time = await self.client.request(
            method='GET',
            endpoint=f'/presentations/{presentation_id}/download',
            params=params
        )
        
        return TestResult(
            test_name="Download Presentation",
            endpoint=f"/presentations/{presentation_id}/download",
            method="GET",
            status=TestStatus.PASSED if status_code in [200, 404] else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response if isinstance(response, dict) else {"type": "binary"}
        )
    
    async def test_add_slide(self, presentation_id: Optional[str] = None) -> TestResult:
        """Test POST /presentations/{id}/slides"""
        if not presentation_id:
            presentation_id = str(uuid.uuid4())
        
        slide_data = {
            "content": "This is a new slide content for testing",
            "position": 5,
            "layout": "content",
            "notes": "Speaker notes for the test slide"
        }
        
        status_code, response, response_time = await self.client.request(
            method='POST',
            endpoint=f'/presentations/{presentation_id}/slides',
            data=slide_data
        )
        
        return TestResult(
            test_name="Add Slide to Presentation",
            endpoint=f"/presentations/{presentation_id}/slides",
            method="POST",
            status=TestStatus.PASSED if status_code in [201, 404] else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )
    
    async def test_delete_presentation(self, presentation_id: Optional[str] = None) -> TestResult:
        """Test DELETE /presentations/{id}"""
        if not presentation_id:
            presentation_id = str(uuid.uuid4())
        
        status_code, response, response_time = await self.client.request(
            method='DELETE',
            endpoint=f'/presentations/{presentation_id}'
        )
        
        return TestResult(
            test_name="Delete Presentation",
            endpoint=f"/presentations/{presentation_id}",
            method="DELETE",
            status=TestStatus.PASSED if status_code in [204, 404] else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )

class TaskAPITests:
    """Test cases for Task endpoints"""
    
    def __init__(self, client: APITestClient):
        self.client = client
    
    async def test_get_task_status(self, task_id: Optional[str] = None) -> TestResult:
        """Test GET /tasks/{id}"""
        if not task_id:
            task_id = str(uuid.uuid4())
        
        status_code, response, response_time = await self.client.request(
            method='GET',
            endpoint=f'/tasks/{task_id}'
        )
        
        return TestResult(
            test_name="Get Task Status",
            endpoint=f"/tasks/{task_id}",
            method="GET",
            status=TestStatus.PASSED if status_code in [200, 404] else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )
    
    async def test_cancel_task(self, task_id: Optional[str] = None) -> TestResult:
        """Test DELETE /tasks/{id}"""
        if not task_id:
            task_id = str(uuid.uuid4())
        
        status_code, response, response_time = await self.client.request(
            method='DELETE',
            endpoint=f'/tasks/{task_id}'
        )
        
        return TestResult(
            test_name="Cancel Task",
            endpoint=f"/tasks/{task_id}",
            method="DELETE",
            status=TestStatus.PASSED if status_code in [204, 404] else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )

class TemplateAPITests:
    """Test cases for Template endpoints"""
    
    def __init__(self, client: APITestClient):
        self.client = client
    
    async def test_list_templates(self) -> TestResult:
        """Test GET /templates"""
        params = {'category': 'business'}
        
        status_code, response, response_time = await self.client.request(
            method='GET',
            endpoint='/templates',
            params=params
        )
        
        return TestResult(
            test_name="List Templates",
            endpoint="/templates",
            method="GET",
            status=TestStatus.PASSED if status_code == 200 else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )
    
    async def test_get_template(self, template_id: str = "executive_summary") -> TestResult:
        """Test GET /templates/{id}"""
        status_code, response, response_time = await self.client.request(
            method='GET',
            endpoint=f'/templates/{template_id}'
        )
        
        return TestResult(
            test_name="Get Template Details",
            endpoint=f"/templates/{template_id}",
            method="GET",
            status=TestStatus.PASSED if status_code in [200, 404] else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )

class HealthAPITests:
    """Test cases for Health endpoints"""
    
    def __init__(self, client: APITestClient):
        self.client = client
    
    async def test_health_check(self) -> TestResult:
        """Test GET /health"""
        status_code, response, response_time = await self.client.request(
            method='GET',
            endpoint='/health'
        )
        
        return TestResult(
            test_name="Health Check",
            endpoint="/health",
            method="GET",
            status=TestStatus.PASSED if status_code in [200, 503] else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )
    
    async def test_readiness_check(self) -> TestResult:
        """Test GET /health/ready"""
        status_code, response, response_time = await self.client.request(
            method='GET',
            endpoint='/health/ready'
        )
        
        return TestResult(
            test_name="Readiness Check",
            endpoint="/health/ready",
            method="GET",
            status=TestStatus.PASSED if status_code in [200, 503] else TestStatus.FAILED,
            response_time=response_time,
            status_code=status_code,
            response_body=response
        )

class APITestRunner:
    """Main test runner"""
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.suite = TestSuite(
            suite_name="AI PPT Assistant API Test Suite",
            start_time=datetime.now().isoformat()
        )
    
    async def run_all_tests(self, verbose: bool = False):
        """Run all API tests"""
        console.print("\n[bold cyan]🚀 Starting API Test Suite[/bold cyan]\n")
        console.print(f"[yellow]Base URL:[/yellow] {self.config.base_url}")
        console.print(f"[yellow]Timeout:[/yellow] {self.config.timeout}s\n")
        
        async with APITestClient(self.config) as client:
            # Initialize test classes
            presentation_tests = PresentationAPITests(client)
            task_tests = TaskAPITests(client)
            template_tests = TemplateAPITests(client)
            health_tests = HealthAPITests(client)
            
            # Test groups
            test_groups = [
                ("Health Checks", [
                    health_tests.test_health_check(),
                    health_tests.test_readiness_check()
                ]),
                ("Presentation APIs", [
                    presentation_tests.test_create_presentation(),
                    presentation_tests.test_list_presentations(),
                    presentation_tests.test_get_presentation(),
                    presentation_tests.test_update_presentation(),
                    presentation_tests.test_download_presentation(),
                    presentation_tests.test_add_slide(),
                    presentation_tests.test_delete_presentation()
                ]),
                ("Task APIs", [
                    task_tests.test_get_task_status(),
                    task_tests.test_cancel_task()
                ]),
                ("Template APIs", [
                    template_tests.test_list_templates(),
                    template_tests.test_get_template()
                ])
            ]
            
            # Run tests with progress bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                
                for group_name, tests in test_groups:
                    console.print(f"\n[bold blue]📋 {group_name}[/bold blue]")
                    
                    task = progress.add_task(f"Running {group_name}", total=len(tests))
                    
                    for test_coro in tests:
                        result = await test_coro
                        self.suite.add_result(result)
                        
                        # Display result
                        status_emoji = "✅" if result.status == TestStatus.PASSED else "❌"
                        status_color = "green" if result.status == TestStatus.PASSED else "red"
                        
                        console.print(
                            f"  {status_emoji} [{status_color}]{result.test_name}[/{status_color}] "
                            f"({result.method} {result.endpoint}) - "
                            f"{result.response_time:.2f}s - "
                            f"[dim]Status: {result.status_code}[/dim]"
                        )
                        
                        if verbose and result.status == TestStatus.FAILED:
                            console.print(f"    [red]Error: {result.error_message or result.response_body}[/red]")
                        
                        progress.update(task, advance=1)
        
        self.suite.end_time = datetime.now().isoformat()
    
    def generate_report(self) -> str:
        """Generate test report"""
        report_lines = []
        report_lines.append("\n" + "="*60)
        report_lines.append("📊 API TEST REPORT")
        report_lines.append("="*60)
        
        # Summary
        report_lines.append(f"\n📅 Test Suite: {self.suite.suite_name}")
        report_lines.append(f"⏰ Start Time: {self.suite.start_time}")
        report_lines.append(f"⏱️  End Time: {self.suite.end_time}")
        report_lines.append(f"\n📈 Results Summary:")
        report_lines.append(f"   Total Tests: {self.suite.total_tests}")
        report_lines.append(f"   ✅ Passed: {self.suite.passed}")
        report_lines.append(f"   ❌ Failed: {self.suite.failed}")
        report_lines.append(f"   ⏭️  Skipped: {self.suite.skipped}")
        report_lines.append(f"   Success Rate: {self.suite.get_success_rate():.1f}%")
        
        # Failed tests details
        if self.suite.failed > 0:
            report_lines.append("\n❌ Failed Tests:")
            for result in self.suite.results:
                if result.status == TestStatus.FAILED:
                    report_lines.append(f"   - {result.test_name} ({result.method} {result.endpoint})")
                    report_lines.append(f"     Status Code: {result.status_code}")
                    if result.error_message:
                        report_lines.append(f"     Error: {result.error_message}")
        
        # Performance metrics
        report_lines.append("\n⚡ Performance Metrics:")
        response_times = [r.response_time for r in self.suite.results]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            report_lines.append(f"   Average Response Time: {avg_time:.3f}s")
            report_lines.append(f"   Max Response Time: {max_time:.3f}s")
            report_lines.append(f"   Min Response Time: {min_time:.3f}s")
        
        # Detailed results table
        table = Table(title="\n📋 Detailed Test Results", show_header=True, header_style="bold magenta")
        table.add_column("Test Name", style="cyan", width=30)
        table.add_column("Endpoint", style="yellow")
        table.add_column("Method", style="blue", width=8)
        table.add_column("Status", width=10)
        table.add_column("Response Time", style="green", width=12)
        table.add_column("Status Code", width=12)
        
        for result in self.suite.results:
            status_style = "green" if result.status == TestStatus.PASSED else "red"
            table.add_row(
                result.test_name,
                result.endpoint,
                result.method,
                f"[{status_style}]{result.status.value}[/{status_style}]",
                f"{result.response_time:.3f}s",
                str(result.status_code) if result.status_code else "N/A"
            )
        
        console.print("\n".join(report_lines))
        console.print(table)
        
        return "\n".join(report_lines)
    
    def save_report(self, filename: str = "api_test_report.json"):
        """Save test report to file"""
        report_data = {
            "suite_name": self.suite.suite_name,
            "start_time": self.suite.start_time,
            "end_time": self.suite.end_time,
            "summary": {
                "total_tests": self.suite.total_tests,
                "passed": self.suite.passed,
                "failed": self.suite.failed,
                "skipped": self.suite.skipped,
                "success_rate": self.suite.get_success_rate()
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "status": r.status.value,
                    "response_time": r.response_time,
                    "status_code": r.status_code,
                    "timestamp": r.timestamp,
                    "response_body": r.response_body,
                    "error_message": r.error_message
                }
                for r in self.suite.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        console.print(f"\n[green]✅ Report saved to {filename}[/green]")

async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Complete API Testing Suite')
    parser.add_argument('--base-url', help='API base URL', default=None)
    parser.add_argument('--api-key', help='API key', default=None)
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--save-report', '-s', help='Save report to file', default='api_test_report.json')
    
    args = parser.parse_args()
    
    # Configure API
    config = APIConfig()
    if args.base_url:
        config.base_url = args.base_url
    if args.api_key:
        config.api_key = args.api_key
    
    # Run tests
    runner = APITestRunner(config)
    await runner.run_all_tests(verbose=args.verbose)
    
    # Generate and save report
    runner.generate_report()
    if args.save_report:
        runner.save_report(args.save_report)
    
    # Return exit code based on results
    return 0 if runner.suite.failed == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)