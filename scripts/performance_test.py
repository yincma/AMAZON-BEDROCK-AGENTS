#!/usr/bin/env python3
"""
Lambda Performance Testing Script

This script tests the performance of Lambda functions by invoking them
and measuring response times, cold start durations, and other metrics.
"""

import boto3
import json
import time
import statistics
from typing import List, Dict, Any
from datetime import datetime, timedelta
import argparse


class LambdaPerformanceTester:
    """Test Lambda function performance including cold start metrics."""
    
    def __init__(self, region: str = 'us-east-1', project_name: str = 'ai-ppt-assistant'):
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.region = region
        self.project_name = project_name
        
        # API functions to test (prioritized by importance)
        self.api_functions = [
            f"{project_name}-api-presentation-status",
            f"{project_name}-api-generate-presentation", 
            f"{project_name}-api-presentation-download",
            f"{project_name}-api-modify-slide"
        ]
    
    def test_function_cold_start(self, function_name: str, test_payload: Dict = None) -> Dict[str, Any]:
        """Test cold start performance of a Lambda function."""
        if test_payload is None:
            test_payload = {"test": True, "source": "performance_test"}
        
        print(f"Testing cold start for {function_name}...")
        
        # Force cold start by updating environment variable
        try:
            response = self.lambda_client.get_function(FunctionName=function_name)
            env_vars = response['Configuration']['Environment'].get('Variables', {})
            env_vars['PERF_TEST_TIMESTAMP'] = str(int(time.time()))
            
            self.lambda_client.update_function_configuration(
                FunctionName=function_name,
                Environment={'Variables': env_vars}
            )
            
            # Wait for update to complete
            time.sleep(5)
            
        except Exception as e:
            print(f"Warning: Could not force cold start for {function_name}: {e}")
        
        # Measure invocation time
        start_time = time.time()
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps(test_payload),
                LogType='Tail'
            )
            
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # Convert to ms
            
            # Parse response
            status_code = response['StatusCode']
            payload = response['Payload'].read().decode()
            
            # Extract duration from logs if available
            import base64
            if 'LogResult' in response:
                logs = base64.b64decode(response['LogResult']).decode()
                # Look for duration in logs
                billed_duration = None
                for line in logs.split('\n'):
                    if 'Duration:' in line:
                        try:
                            duration_str = line.split('Duration: ')[1].split(' ms')[0]
                            billed_duration = float(duration_str)
                            break
                        except:
                            pass
            
            result = {
                'function_name': function_name,
                'status_code': status_code,
                'client_duration_ms': duration,
                'billed_duration_ms': billed_duration,
                'payload_size': len(payload),
                'success': status_code == 200,
                'timestamp': datetime.now().isoformat()
            }
            
            if status_code == 200:
                print(f"✅ {function_name}: {duration:.0f}ms (client), {billed_duration or 'N/A'}ms (billed)")
            else:
                print(f"❌ {function_name}: Failed with status {status_code}")
            
            return result
            
        except Exception as e:
            print(f"❌ {function_name}: Error - {str(e)}")
            return {
                'function_name': function_name,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_cloudwatch_metrics(self, function_name: str, hours_back: int = 1) -> Dict[str, Any]:
        """Get CloudWatch metrics for a function."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)
        
        metrics = {}
        
        try:
            # Get Duration metrics
            duration_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Duration',
                Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average', 'Maximum', 'Minimum']
            )
            
            if duration_response['Datapoints']:
                durations = [dp['Average'] for dp in duration_response['Datapoints']]
                metrics['avg_duration_ms'] = statistics.mean(durations)
                metrics['max_duration_ms'] = max(dp['Maximum'] for dp in duration_response['Datapoints'])
                metrics['min_duration_ms'] = min(dp['Minimum'] for dp in duration_response['Datapoints'])
            
            # Get Error metrics
            error_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Errors',
                Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            metrics['error_count'] = sum(dp['Sum'] for dp in error_response['Datapoints'])
            
            # Get Invocation metrics
            invocation_response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            metrics['invocation_count'] = sum(dp['Sum'] for dp in invocation_response['Datapoints'])
            
        except Exception as e:
            print(f"Warning: Could not get CloudWatch metrics for {function_name}: {e}")
            
        return metrics
    
    def run_performance_suite(self) -> Dict[str, Any]:
        """Run complete performance test suite."""
        print("🚀 Starting Lambda Performance Test Suite")
        print("=" * 50)
        
        results = {
            'test_timestamp': datetime.now().isoformat(),
            'project_name': self.project_name,
            'region': self.region,
            'functions_tested': [],
            'summary': {}
        }
        
        all_durations = []
        successful_tests = 0
        
        for function_name in self.api_functions:
            print(f"\n📊 Testing {function_name}...")
            
            # Test cold start
            test_result = self.test_function_cold_start(function_name)
            
            # Get CloudWatch metrics
            cloudwatch_metrics = self.get_cloudwatch_metrics(function_name)
            
            function_result = {
                'cold_start_test': test_result,
                'cloudwatch_metrics': cloudwatch_metrics
            }
            
            results['functions_tested'].append(function_result)
            
            if test_result.get('success'):
                successful_tests += 1
                if test_result.get('client_duration_ms'):
                    all_durations.append(test_result['client_duration_ms'])
        
        # Calculate summary statistics
        if all_durations:
            results['summary'] = {
                'total_functions_tested': len(self.api_functions),
                'successful_tests': successful_tests,
                'success_rate': (successful_tests / len(self.api_functions)) * 100,
                'avg_cold_start_ms': statistics.mean(all_durations),
                'max_cold_start_ms': max(all_durations),
                'min_cold_start_ms': min(all_durations),
                'cold_start_std_dev': statistics.stdev(all_durations) if len(all_durations) > 1 else 0
            }
        
        # Print summary
        print("\n" + "=" * 50)
        print("📈 PERFORMANCE TEST SUMMARY")
        print("=" * 50)
        
        if 'summary' in results:
            summary = results['summary']
            print(f"Functions tested: {summary['total_functions_tested']}")
            print(f"Successful tests: {summary['successful_tests']}")
            print(f"Success rate: {summary['success_rate']:.1f}%")
            print(f"Average cold start: {summary['avg_cold_start_ms']:.0f}ms")
            print(f"Max cold start: {summary['max_cold_start_ms']:.0f}ms")
            print(f"Min cold start: {summary['min_cold_start_ms']:.0f}ms")
            
            # Performance recommendations
            print("\n🎯 PERFORMANCE RECOMMENDATIONS:")
            if summary['avg_cold_start_ms'] > 1000:
                print("❌ High cold start times detected (>1s)")
                print("   → Consider enabling Provisioned Concurrency")
                print("   → Optimize Lambda layer size")
                print("   → Review memory allocation")
            elif summary['avg_cold_start_ms'] > 500:
                print("⚠️  Moderate cold start times (>500ms)")
                print("   → Monitor usage patterns for Provisioned Concurrency")
            else:
                print("✅ Good cold start performance (<500ms)")
                
        print("\n✅ Performance test completed!")
        return results


def main():
    """Main function to run performance tests."""
    parser = argparse.ArgumentParser(description='Test Lambda function performance')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--project', default='ai-ppt-assistant', help='Project name')
    parser.add_argument('--output', help='Output file for results (JSON)')
    
    args = parser.parse_args()
    
    tester = LambdaPerformanceTester(region=args.region, project_name=args.project)
    results = tester.run_performance_suite()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📁 Results saved to {args.output}")


if __name__ == '__main__':
    main()