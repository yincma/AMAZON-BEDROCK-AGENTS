"""
Performance Testing for Step Functions Workflow
Validates the 50% performance improvement through parallel processing
"""

import json
import boto3
import time
import statistics
from typing import List, Dict, Any
from datetime import datetime
import concurrent.futures
import argparse

# AWS clients
stepfunctions = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

class PerformanceTester:
    """Test harness for PPT generation performance"""

    def __init__(self, state_machine_arn: str, table_name: str):
        self.state_machine_arn = state_machine_arn
        self.table = dynamodb.Table(table_name)
        self.metrics = {
            'sequential_times': [],
            'parallel_times': [],
            'concurrent_test_results': []
        }

    def test_single_generation(self, num_slides: int, use_parallel: bool = True) -> Dict[str, Any]:
        """
        Test a single PPT generation

        Args:
            num_slides: Number of slides to generate
            use_parallel: Whether to use parallel processing

        Returns:
            Test results including timing
        """
        start_time = time.time()

        # Prepare test input
        test_input = {
            'title': f'Performance Test - {num_slides} slides',
            'num_slides': num_slides,
            'style': 'professional',
            'priority': 'high' if use_parallel else 'low',
            'test_mode': True,
            'parallel_enabled': use_parallel
        }

        # Start execution
        execution_name = f"perf-test-{int(time.time())}-{num_slides}"
        response = stepfunctions.start_execution(
            stateMachineArn=self.state_machine_arn,
            name=execution_name,
            input=json.dumps(test_input)
        )

        execution_arn = response['executionArn']

        # Wait for completion
        while True:
            status = stepfunctions.describe_execution(executionArn=execution_arn)
            if status['status'] != 'RUNNING':
                break
            time.sleep(1)

        end_time = time.time()
        execution_time = end_time - start_time

        return {
            'execution_arn': execution_arn,
            'num_slides': num_slides,
            'parallel': use_parallel,
            'execution_time': execution_time,
            'status': status['status'],
            'output': json.loads(status.get('output', '{}')) if status.get('output') else {}
        }

    def test_concurrent_requests(self, num_requests: int, slides_per_request: int) -> Dict[str, Any]:
        """
        Test concurrent PPT generation requests

        Args:
            num_requests: Number of concurrent requests
            slides_per_request: Slides per request

        Returns:
            Concurrent test results
        """
        print(f"\nTesting {num_requests} concurrent requests with {slides_per_request} slides each...")

        start_time = time.time()
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = []
            for i in range(num_requests):
                future = executor.submit(
                    self.test_single_generation,
                    slides_per_request,
                    use_parallel=True
                )
                futures.append(future)

            # Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=300)
                    results.append(result)
                except Exception as e:
                    print(f"Request failed: {e}")

        total_time = time.time() - start_time

        successful = sum(1 for r in results if r['status'] == 'SUCCEEDED')
        avg_time = statistics.mean([r['execution_time'] for r in results if r['status'] == 'SUCCEEDED'])

        return {
            'total_requests': num_requests,
            'successful_requests': successful,
            'total_time': total_time,
            'average_time_per_request': avg_time,
            'throughput': successful / total_time if total_time > 0 else 0,
            'results': results
        }

    def compare_sequential_vs_parallel(self, slide_counts: List[int]) -> Dict[str, Any]:
        """
        Compare sequential vs parallel processing performance

        Args:
            slide_counts: List of slide counts to test

        Returns:
            Comparison results
        """
        results = {
            'sequential': [],
            'parallel': [],
            'improvements': []
        }

        for num_slides in slide_counts:
            print(f"\nTesting {num_slides} slides...")

            # Test sequential processing
            print("  - Sequential processing...")
            seq_result = self.test_single_generation(num_slides, use_parallel=False)
            results['sequential'].append(seq_result)

            # Test parallel processing
            print("  - Parallel processing...")
            par_result = self.test_single_generation(num_slides, use_parallel=True)
            results['parallel'].append(par_result)

            # Calculate improvement
            if seq_result['execution_time'] > 0:
                improvement = ((seq_result['execution_time'] - par_result['execution_time'])
                             / seq_result['execution_time']) * 100
                results['improvements'].append({
                    'num_slides': num_slides,
                    'sequential_time': seq_result['execution_time'],
                    'parallel_time': par_result['execution_time'],
                    'improvement_percentage': improvement
                })
                print(f"  - Improvement: {improvement:.1f}%")

        return results

    def publish_metrics(self, results: Dict[str, Any]) -> None:
        """
        Publish performance metrics to CloudWatch

        Args:
            results: Test results to publish
        """
        namespace = 'AI-PPT-Assistant/Performance'

        metrics = []

        # Average execution time metrics
        if 'parallel' in results:
            for result in results['parallel']:
                metrics.append({
                    'MetricName': 'ExecutionTime',
                    'Value': result['execution_time'],
                    'Unit': 'Seconds',
                    'Dimensions': [
                        {'Name': 'ProcessingType', 'Value': 'Parallel'},
                        {'Name': 'SlideCount', 'Value': str(result['num_slides'])}
                    ]
                })

        # Improvement metrics
        if 'improvements' in results:
            for improvement in results['improvements']:
                metrics.append({
                    'MetricName': 'PerformanceImprovement',
                    'Value': improvement['improvement_percentage'],
                    'Unit': 'Percent',
                    'Dimensions': [
                        {'Name': 'SlideCount', 'Value': str(improvement['num_slides'])}
                    ]
                })

        # Concurrent request metrics
        if 'concurrent_test_results' in results:
            for concurrent_result in results['concurrent_test_results']:
                metrics.append({
                    'MetricName': 'Throughput',
                    'Value': concurrent_result['throughput'],
                    'Unit': 'Count/Second',
                    'Dimensions': [
                        {'Name': 'ConcurrentRequests', 'Value': str(concurrent_result['total_requests'])}
                    ]
                })

        # Publish to CloudWatch
        if metrics:
            for i in range(0, len(metrics), 20):  # CloudWatch limit is 20 metrics per call
                batch = metrics[i:i+20]
                cloudwatch.put_metric_data(
                    Namespace=namespace,
                    MetricData=batch
                )

    def generate_performance_report(self, results: Dict[str, Any]) -> str:
        """
        Generate a detailed performance report

        Args:
            results: Test results

        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("AI PPT Assistant - Performance Test Report")
        report.append("=" * 60)
        report.append(f"Test Date: {datetime.now().isoformat()}")
        report.append("")

        # Sequential vs Parallel Comparison
        if 'improvements' in results:
            report.append("Sequential vs Parallel Processing:")
            report.append("-" * 40)

            for imp in results['improvements']:
                report.append(f"\n{imp['num_slides']} Slides:")
                report.append(f"  Sequential: {imp['sequential_time']:.2f}s")
                report.append(f"  Parallel:   {imp['parallel_time']:.2f}s")
                report.append(f"  Improvement: {imp['improvement_percentage']:.1f}%")

            avg_improvement = statistics.mean([i['improvement_percentage']
                                              for i in results['improvements']])
            report.append(f"\nAverage Improvement: {avg_improvement:.1f}%")

        # Concurrent Request Results
        if 'concurrent_test_results' in results:
            report.append("\n" + "=" * 40)
            report.append("Concurrent Request Testing:")
            report.append("-" * 40)

            for test in results['concurrent_test_results']:
                report.append(f"\n{test['total_requests']} Concurrent Requests:")
                report.append(f"  Success Rate: {test['successful_requests']}/{test['total_requests']}")
                report.append(f"  Total Time: {test['total_time']:.2f}s")
                report.append(f"  Avg Time/Request: {test['average_time_per_request']:.2f}s")
                report.append(f"  Throughput: {test['throughput']:.2f} req/s")

        # Performance Requirements Check
        report.append("\n" + "=" * 40)
        report.append("Performance Requirements Validation:")
        report.append("-" * 40)

        # Check 10-page generation < 30s
        ten_page_results = [r for r in results.get('parallel', []) if r['num_slides'] == 10]
        if ten_page_results:
            ten_page_time = ten_page_results[0]['execution_time']
            report.append(f"\n✓ 10-page generation: {ten_page_time:.2f}s")
            if ten_page_time < 30:
                report.append("  ✅ PASS - Under 30 seconds requirement")
            else:
                report.append("  ❌ FAIL - Exceeds 30 seconds requirement")

        # Check 50 concurrent requests support
        fifty_concurrent = [t for t in results.get('concurrent_test_results', [])
                           if t['total_requests'] == 50]
        if fifty_concurrent:
            success_rate = fifty_concurrent[0]['successful_requests'] / 50 * 100
            report.append(f"\n✓ 50 concurrent requests: {success_rate:.1f}% success rate")
            if success_rate >= 95:
                report.append("  ✅ PASS - Supports 50 concurrent requests")
            else:
                report.append("  ❌ FAIL - Cannot handle 50 concurrent requests reliably")

        # Check 50% performance improvement
        if 'improvements' in results and results['improvements']:
            avg_improvement = statistics.mean([i['improvement_percentage']
                                              for i in results['improvements']])
            report.append(f"\n✓ Performance improvement: {avg_improvement:.1f}%")
            if avg_improvement >= 50:
                report.append("  ✅ PASS - Achieves 50% performance improvement")
            else:
                report.append("  ❌ FAIL - Does not achieve 50% improvement")

        report.append("\n" + "=" * 60)
        return "\n".join(report)


def main():
    """Main test execution"""
    parser = argparse.ArgumentParser(description='Performance testing for AI PPT Assistant')
    parser.add_argument('--state-machine-arn', required=True, help='Step Functions state machine ARN')
    parser.add_argument('--table-name', required=True, help='DynamoDB table name')
    parser.add_argument('--test-type', choices=['comparison', 'concurrent', 'full'],
                       default='full', help='Type of test to run')
    parser.add_argument('--output-file', help='Output file for report')

    args = parser.parse_args()

    tester = PerformanceTester(args.state_machine_arn, args.table_name)
    results = {}

    print("Starting performance tests...")

    if args.test_type in ['comparison', 'full']:
        # Test sequential vs parallel for different slide counts
        comparison_results = tester.compare_sequential_vs_parallel([5, 10, 15, 20])
        results.update(comparison_results)

    if args.test_type in ['concurrent', 'full']:
        # Test concurrent request handling
        concurrent_tests = []
        for num_requests in [10, 25, 50]:
            concurrent_result = tester.test_concurrent_requests(num_requests, 10)
            concurrent_tests.append(concurrent_result)
        results['concurrent_test_results'] = concurrent_tests

    # Publish metrics to CloudWatch
    print("\nPublishing metrics to CloudWatch...")
    tester.publish_metrics(results)

    # Generate report
    report = tester.generate_performance_report(results)
    print("\n" + report)

    # Save report to file if specified
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(report)
        print(f"\nReport saved to: {args.output_file}")

    # Return exit code based on requirements
    if 'improvements' in results:
        avg_improvement = statistics.mean([i['improvement_percentage']
                                         for i in results['improvements']])
        if avg_improvement >= 50:
            print("\n✅ Performance requirements MET!")
            return 0
        else:
            print("\n❌ Performance requirements NOT met.")
            return 1


if __name__ == "__main__":
    exit(main())