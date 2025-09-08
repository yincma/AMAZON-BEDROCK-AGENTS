#!/usr/bin/env python3
"""
API Endpoints Test Script for AI PPT Assistant
Tests all backend API functionalities comprehensively
"""

import json
import time
import uuid
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# API Configuration
API_BASE_URL = "https://1mivrhr3w7.execute-api.us-east-1.amazonaws.com/legacy"
API_KEY = "RUAeSTNzw33iQKQPFBggs9RPUXMnkmon7ZQmjV63"

# Request headers
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

# Test results storage
test_results = []


def log_test(endpoint: str, method: str, status: str, response_code: int, message: str = "", response_data: Any = None):
    """Log test results"""
    result = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "response_code": response_code,
        "message": message,
        "response_data": response_data
    }
    test_results.append(result)
    
    status_emoji = "✅" if status == "PASS" else "❌"
    print(f"{status_emoji} [{method}] {endpoint}: {status} (HTTP {response_code}) - {message}")
    

def test_create_presentation() -> Optional[str]:
    """Test POST /presentations - Create a new presentation"""
    print("\n" + "="*60)
    print("Testing: POST /presentations")
    print("="*60)
    
    endpoint = f"{API_BASE_URL}/presentations"
    payload = {
        "title": f"Test Presentation - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "topic": "Introduction to Cloud Computing with hands-on demos, best practices, and real-world case studies",
        "audience": "technical",
        "duration": 20,
        "slide_count": 5,
        "language": "en",
        "style": "professional"
    }
    
    try:
        response = requests.post(endpoint, headers=HEADERS, json=payload, timeout=30)
        response_data = response.json() if response.text else None
        
        if response.status_code == 202:
            task_id = response_data.get("task_id") if response_data else None
            log_test("/presentations", "POST", "PASS", response.status_code, 
                    f"Presentation creation initiated. Task ID: {task_id}", response_data)
            return task_id
        else:
            log_test("/presentations", "POST", "FAIL", response.status_code, 
                    f"Unexpected status code", response_data)
            return None
            
    except requests.exceptions.RequestException as e:
        log_test("/presentations", "POST", "FAIL", 0, f"Request failed: {str(e)}")
        return None


def test_get_task_status(task_id: str) -> Dict[str, Any]:
    """Test GET /tasks/{task_id} - Get task status"""
    print("\n" + "="*60)
    print(f"Testing: GET /tasks/{task_id}")
    print("="*60)
    
    endpoint = f"{API_BASE_URL}/tasks/{task_id}"
    
    try:
        response = requests.get(endpoint, headers=HEADERS, timeout=30)
        response_data = response.json() if response.text else None
        
        if response.status_code == 200:
            task_status = response_data.get("task", {}).get("status") if response_data else "unknown"
            log_test(f"/tasks/{task_id}", "GET", "PASS", response.status_code, 
                    f"Task status: {task_status}", response_data)
            return response_data or {}
        else:
            log_test(f"/tasks/{task_id}", "GET", "FAIL", response.status_code, 
                    f"Failed to get task status", response_data)
            return {}
            
    except requests.exceptions.RequestException as e:
        log_test(f"/tasks/{task_id}", "GET", "FAIL", 0, f"Request failed: {str(e)}")
        return {}


def test_list_presentations():
    """Test GET /presentations - List all presentations"""
    print("\n" + "="*60)
    print("Testing: GET /presentations")
    print("="*60)
    
    endpoint = f"{API_BASE_URL}/presentations"
    
    try:
        response = requests.get(endpoint, headers=HEADERS, timeout=30)
        response_data = response.json() if response.text else None
        
        if response.status_code == 200:
            count = len(response_data.get("presentations", [])) if response_data else 0
            log_test("/presentations", "GET", "PASS", response.status_code, 
                    f"Retrieved {count} presentations", response_data)
            return response_data
        else:
            log_test("/presentations", "GET", "FAIL", response.status_code, 
                    f"Failed to list presentations", response_data)
            return None
            
    except requests.exceptions.RequestException as e:
        log_test("/presentations", "GET", "FAIL", 0, f"Request failed: {str(e)}")
        return None


def test_get_presentation(presentation_id: str):
    """Test GET /presentations/{id} - Get specific presentation"""
    print("\n" + "="*60)
    print(f"Testing: GET /presentations/{presentation_id}")
    print("="*60)
    
    endpoint = f"{API_BASE_URL}/presentations/{presentation_id}"
    
    try:
        response = requests.get(endpoint, headers=HEADERS, timeout=30)
        response_data = response.json() if response.text else None
        
        if response.status_code == 200:
            log_test(f"/presentations/{presentation_id}", "GET", "PASS", response.status_code, 
                    f"Successfully retrieved presentation", response_data)
        elif response.status_code == 404:
            log_test(f"/presentations/{presentation_id}", "GET", "PASS", response.status_code, 
                    f"Presentation not found (expected if ID is test ID)", response_data)
        else:
            log_test(f"/presentations/{presentation_id}", "GET", "FAIL", response.status_code, 
                    f"Failed to get presentation", response_data)
            
    except requests.exceptions.RequestException as e:
        log_test(f"/presentations/{presentation_id}", "GET", "FAIL", 0, f"Request failed: {str(e)}")


def test_create_session() -> Optional[str]:
    """Test POST /sessions - Create a new session"""
    print("\n" + "="*60)
    print("Testing: POST /sessions")
    print("="*60)
    
    endpoint = f"{API_BASE_URL}/sessions"
    payload = {
        "user_id": f"test_user_{uuid.uuid4().hex[:8]}",
        "session_name": "Test Session for API Validation",
        "metadata": {
            "test_case": "api_validation",
            "created_by": "test_script"
        }
    }
    
    try:
        response = requests.post(endpoint, headers=HEADERS, json=payload, timeout=30)
        response_data = response.json() if response.text else None
        
        if response.status_code in [200, 201, 202]:
            session_id = response_data.get("session_id") if response_data else None
            log_test("/sessions", "POST", "PASS", response.status_code, 
                    f"Session created. Session ID: {session_id}", response_data)
            return session_id
        else:
            log_test("/sessions", "POST", "FAIL", response.status_code, 
                    f"Failed to create session", response_data)
            return None
            
    except requests.exceptions.RequestException as e:
        log_test("/sessions", "POST", "FAIL", 0, f"Request failed: {str(e)}")
        return None


def test_get_session(session_id: str):
    """Test GET /sessions/{id} - Get session details"""
    print("\n" + "="*60)
    print(f"Testing: GET /sessions/{session_id}")
    print("="*60)
    
    endpoint = f"{API_BASE_URL}/sessions/{session_id}"
    
    try:
        response = requests.get(endpoint, headers=HEADERS, timeout=30)
        response_data = response.json() if response.text else None
        
        if response.status_code == 200:
            log_test(f"/sessions/{session_id}", "GET", "PASS", response.status_code, 
                    f"Successfully retrieved session", response_data)
        elif response.status_code == 404:
            log_test(f"/sessions/{session_id}", "GET", "PASS", response.status_code, 
                    f"Session not found (expected if ID is test ID)", response_data)
        else:
            log_test(f"/sessions/{session_id}", "GET", "FAIL", response.status_code, 
                    f"Failed to get session", response_data)
            
    except requests.exceptions.RequestException as e:
        log_test(f"/sessions/{session_id}", "GET", "FAIL", 0, f"Request failed: {str(e)}")


def test_execute_agent():
    """Test POST /agents/{name}/execute - Execute an agent"""
    print("\n" + "="*60)
    print("Testing: POST /agents/{name}/execute")
    print("="*60)
    
    agent_name = "orchestrator"  # Use valid agent name from OpenAPI spec
    endpoint = f"{API_BASE_URL}/agents/{agent_name}/execute"
    payload = {
        "input": "Generate a presentation outline about cloud computing fundamentals with 5 slides",
        "enable_trace": False,
        "parameters": {
            "temperature": 0.7,
            "max_tokens": 1000
        }
    }
    
    try:
        response = requests.post(endpoint, headers=HEADERS, json=payload, timeout=30)
        response_data = response.json() if response.text else None
        
        if response.status_code in [200, 202]:
            log_test(f"/agents/{agent_name}/execute", "POST", "PASS", response.status_code, 
                    f"Agent execution initiated", response_data)
        else:
            log_test(f"/agents/{agent_name}/execute", "POST", "FAIL", response.status_code, 
                    f"Failed to execute agent", response_data)
            
    except requests.exceptions.RequestException as e:
        log_test(f"/agents/{agent_name}/execute", "POST", "FAIL", 0, f"Request failed: {str(e)}")


def generate_test_report():
    """Generate a comprehensive test report"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r["status"] == "PASS")
    failed_tests = sum(1 for r in test_results if r["status"] == "FAIL")
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Pass Rate: {(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%")
    
    if failed_tests > 0:
        print("\n❌ Failed Tests:")
        for result in test_results:
            if result["status"] == "FAIL":
                print(f"  - [{result['method']}] {result['endpoint']}: {result['message']}")
    
    # Save detailed results to file
    with open("api_test_results.json", "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    print("\n📄 Detailed results saved to: api_test_results.json")
    
    return test_results


def main():
    """Main test execution function"""
    print("🚀 Starting API Endpoints Testing")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Test 1: Create Presentation
    task_id = test_create_presentation()
    
    # Test 2: Check Task Status (if task_id available)
    if task_id:
        print(f"\n⏳ Waiting 3 seconds before checking task status...")
        time.sleep(3)
        test_get_task_status(task_id)
    
    # Test 3: List Presentations
    presentations = test_list_presentations()
    
    # Test 4: Get Specific Presentation (use first one if available)
    if presentations and presentations.get("presentations"):
        first_presentation_id = presentations["presentations"][0].get("presentation_id", "00000000-0000-0000-0000-000000000000")
        test_get_presentation(first_presentation_id)
    else:
        # Test with a valid UUID format but non-existent ID
        test_get_presentation("00000000-0000-0000-0000-000000000000")
    
    # Test 5: Create Session
    session_id = test_create_session()
    
    # Test 6: Get Session (if session_id available)
    if session_id:
        test_get_session(session_id)
    else:
        # Test with valid UUID format but non-existent session ID
        test_get_session("00000000-0000-0000-0000-000000000000")
    
    # Test 7: Execute Agent
    test_execute_agent()
    
    # Generate report
    generate_test_report()


if __name__ == "__main__":
    main()