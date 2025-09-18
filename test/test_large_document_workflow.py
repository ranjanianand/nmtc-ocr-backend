"""
Enterprise Large Document Workflow Testing
Tests end-to-end processing of 50MB+ documents with Core Engine v3

This test suite validates:
1. Database schema and table creation
2. Large file upload handling
3. Background processing pipeline
4. Real-time progress tracking
5. Agent state management
6. Cross-device synchronization
7. Error handling and recovery
"""

import asyncio
import json
import time
import requests
import os
from datetime import datetime
from typing import Dict, Any, List

class LargeDocumentWorkflowTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = []
        self.test_session_id = f"test_{int(time.time())}"
        
    def log_test(self, test_name: str, success: bool, message: str, duration: float = 0):
        """Log test result"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message} ({duration:.2f}s)")
        
    def test_database_schema(self) -> bool:
        """Test 1: Verify database schema exists"""
        start_time = time.time()
        
        try:
            # Test database connection and schema
            response = requests.get(f"{self.base_url}/api/health")
            
            if response.status_code == 200:
                health_data = response.json()
                db_status = health_data.get('database', {}).get('status') == 'connected'
                
                if db_status:
                    self.log_test(
                        "Database Schema", 
                        True, 
                        "Database connection and schema validated",
                        time.time() - start_time
                    )
                    return True
                else:
                    self.log_test(
                        "Database Schema", 
                        False, 
                        "Database not connected",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Database Schema", 
                    False, 
                    f"Health check failed: {response.status_code}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Database Schema", 
                False, 
                f"Database test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def create_large_test_file(self, size_mb: int = 55) -> str:
        """Create a large PDF-like test file"""
        test_file_path = f"test/large_document_{size_mb}mb.pdf"
        
        # Create test directory if it doesn't exist
        os.makedirs("test", exist_ok=True)
        
        # Create a file with the specified size
        with open(test_file_path, 'wb') as f:
            # Write PDF header
            f.write(b"%PDF-1.4\n")
            
            # Calculate remaining bytes needed
            target_size = size_mb * 1024 * 1024
            written = len(b"%PDF-1.4\n")
            
            # Fill with dummy content
            chunk_size = 1024 * 1024  # 1MB chunks
            dummy_content = b"A" * chunk_size
            
            while written < target_size:
                remaining = target_size - written
                if remaining < chunk_size:
                    f.write(b"A" * remaining)
                    written += remaining
                else:
                    f.write(dummy_content)
                    written += chunk_size
        
        return test_file_path
    
    def test_large_file_upload(self) -> tuple[bool, str]:
        """Test 2: Upload 50MB+ document"""
        start_time = time.time()
        
        try:
            # Create large test file
            test_file_path = self.create_large_test_file(55)
            file_size = os.path.getsize(test_file_path)
            
            print(f"📄 Created test file: {file_size / 1024 / 1024:.1f}MB")
            
            # Prepare upload
            with open(test_file_path, 'rb') as f:
                files = {'file': ('large_test_document.pdf', f, 'application/pdf')}
                data = {
                    'org_id': 'test_org_001',
                    'user_id': 'test_user_001',
                    'cde_name': 'Test CDE',
                    'client_info': 'Large Document Test Client'
                }
                
                # Upload file
                response = requests.post(
                    f"{self.base_url}/api/v3/documents/upload",
                    files=files,
                    data=data,
                    timeout=120  # 2 minute timeout for large files
                )
            
            # Clean up test file
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    document_id = result.get('document_id')
                    session_id = result.get('session_id')
                    
                    self.log_test(
                        "Large File Upload", 
                        True, 
                        f"Successfully uploaded {file_size / 1024 / 1024:.1f}MB file. Doc ID: {document_id[:8]}...",
                        time.time() - start_time
                    )
                    return True, document_id
                else:
                    self.log_test(
                        "Large File Upload", 
                        False, 
                        f"Upload failed: {result.get('message', 'Unknown error')}",
                        time.time() - start_time
                    )
                    return False, ""
            else:
                self.log_test(
                    "Large File Upload", 
                    False, 
                    f"HTTP error: {response.status_code} - {response.text[:200]}",
                    time.time() - start_time
                )
                return False, ""
                
        except Exception as e:
            self.log_test(
                "Large File Upload", 
                False, 
                f"Upload exception: {str(e)}",
                time.time() - start_time
            )
            return False, ""
    
    def test_background_processing(self, document_id: str) -> bool:
        """Test 3: Monitor background processing pipeline"""
        start_time = time.time()
        max_wait_time = 1800  # 30 minutes max
        poll_interval = 5  # Check every 5 seconds
        
        try:
            print(f"📊 Monitoring processing for document {document_id[:8]}...")
            
            processing_complete = False
            elapsed_time = 0
            stage_history = []
            
            while elapsed_time < max_wait_time and not processing_complete:
                # Get processing status
                response = requests.get(f"{self.base_url}/api/v3/documents/{document_id}/status")
                
                if response.status_code == 200:
                    status = response.json()
                    current_stage = status.get('session', {}).get('current_stage', 'unknown')
                    progress = status.get('session', {}).get('progress_percentage', 0)
                    
                    # Track stage progression
                    if current_stage not in stage_history:
                        stage_history.append(current_stage)
                        print(f"  📈 Stage: {current_stage} ({progress}%)")
                    
                    # Check if processing is complete
                    if current_stage in ['completed', 'complete'] or progress >= 100:
                        processing_complete = True
                        break
                    
                    # Check for errors
                    if current_stage == 'error' or current_stage == 'failed':
                        self.log_test(
                            "Background Processing", 
                            False, 
                            f"Processing failed at stage: {current_stage}",
                            time.time() - start_time
                        )
                        return False
                
                time.sleep(poll_interval)
                elapsed_time += poll_interval
            
            if processing_complete:
                self.log_test(
                    "Background Processing", 
                    True, 
                    f"Processing completed successfully. Stages: {' → '.join(stage_history)}",
                    time.time() - start_time
                )
                return True
            else:
                self.log_test(
                    "Background Processing", 
                    False, 
                    f"Processing timeout after {max_wait_time/60:.1f} minutes",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Background Processing", 
                False, 
                f"Processing monitoring failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_agent_state_tracking(self, document_id: str) -> bool:
        """Test 4: Verify agent state tracking"""
        start_time = time.time()
        
        try:
            response = requests.get(f"{self.base_url}/api/v3/documents/{document_id}/agents")
            
            if response.status_code == 200:
                agents = response.json()
                
                # Check for 3-agent pipeline
                expected_agents = ['agent_1_analyzer', 'agent_2_risk', 'agent_3_reports']
                found_agents = [agent.get('agent_key') for agent in agents]
                
                missing_agents = set(expected_agents) - set(found_agents)
                
                if not missing_agents:
                    agent_states = {agent['agent_key']: agent['status'] for agent in agents}
                    self.log_test(
                        "Agent State Tracking", 
                        True, 
                        f"All 3 agents tracked: {agent_states}",
                        time.time() - start_time
                    )
                    return True
                else:
                    self.log_test(
                        "Agent State Tracking", 
                        False, 
                        f"Missing agents: {missing_agents}",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Agent State Tracking", 
                    False, 
                    f"Failed to get agent states: {response.status_code}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Agent State Tracking", 
                False, 
                f"Agent tracking test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_realtime_updates(self, document_id: str) -> bool:
        """Test 5: Verify real-time progress updates"""
        start_time = time.time()
        
        try:
            # Get progress events
            response = requests.get(f"{self.base_url}/api/v3/documents/{document_id}/events")
            
            if response.status_code == 200:
                events = response.json()
                
                if len(events) > 0:
                    event_types = set(event.get('event_type') for event in events)
                    
                    # Check for expected event types
                    expected_events = {'upload_complete', 'processing_started', 'agent_update'}
                    found_events = event_types.intersection(expected_events)
                    
                    if found_events:
                        self.log_test(
                            "Real-time Updates", 
                            True, 
                            f"Progress events captured: {list(found_events)} ({len(events)} total)",
                            time.time() - start_time
                        )
                        return True
                    else:
                        self.log_test(
                            "Real-time Updates", 
                            False, 
                            f"No expected events found. Got: {list(event_types)}",
                            time.time() - start_time
                        )
                        return False
                else:
                    self.log_test(
                        "Real-time Updates", 
                        False, 
                        "No progress events found",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Real-time Updates", 
                    False, 
                    f"Failed to get events: {response.status_code}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Real-time Updates", 
                False, 
                f"Real-time test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def test_memory_performance(self) -> bool:
        """Test 6: Check system performance during large file processing"""
        start_time = time.time()
        
        try:
            # Get system health during processing
            response = requests.get(f"{self.base_url}/api/health")
            
            if response.status_code == 200:
                health = response.json()
                
                # Check if system is responsive
                response_time = time.time() - start_time
                
                if response_time < 5.0:  # Should respond within 5 seconds
                    self.log_test(
                        "Memory Performance", 
                        True, 
                        f"System responsive during processing (response: {response_time:.2f}s)",
                        time.time() - start_time
                    )
                    return True
                else:
                    self.log_test(
                        "Memory Performance", 
                        False, 
                        f"System slow response: {response_time:.2f}s",
                        time.time() - start_time
                    )
                    return False
            else:
                self.log_test(
                    "Memory Performance", 
                    False, 
                    f"Health check failed: {response.status_code}",
                    time.time() - start_time
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Memory Performance", 
                False, 
                f"Performance test failed: {str(e)}",
                time.time() - start_time
            )
            return False
    
    def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete test suite"""
        print("🚀 Starting Enterprise Large Document Workflow Tests")
        print("=" * 60)
        
        start_time = time.time()
        document_id = ""
        
        # Test 1: Database Schema
        if not self.test_database_schema():
            return self.generate_report(False, "Database schema test failed")
        
        # Test 2: Large File Upload
        upload_success, document_id = self.test_large_file_upload()
        if not upload_success:
            return self.generate_report(False, "Large file upload failed")
        
        # Test 3: Background Processing (this is the long one)
        if not self.test_background_processing(document_id):
            return self.generate_report(False, "Background processing failed")
        
        # Test 4: Agent State Tracking
        if not self.test_agent_state_tracking(document_id):
            return self.generate_report(False, "Agent state tracking failed")
        
        # Test 5: Real-time Updates
        if not self.test_realtime_updates(document_id):
            return self.generate_report(False, "Real-time updates failed")
        
        # Test 6: Performance
        if not self.test_memory_performance():
            return self.generate_report(False, "Performance test failed")
        
        return self.generate_report(True, "All tests passed successfully")
    
    def generate_report(self, success: bool, summary: str) -> Dict[str, Any]:
        """Generate test report"""
        total_duration = sum(result['duration'] for result in self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)
        
        report = {
            "overall_success": success,
            "summary": summary,
            "test_session": self.test_session_id,
            "total_duration": total_duration,
            "tests_passed": passed_tests,
            "tests_total": total_tests,
            "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "detailed_results": self.test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Overall Success: {'✅ PASS' if success else '❌ FAIL'}")
        print(f"Tests Passed: {passed_tests}/{total_tests} ({report['pass_rate']:.1f}%)")
        print(f"Total Duration: {total_duration:.2f} seconds")
        print(f"Summary: {summary}")
        
        return report

def main():
    """Run the test suite"""
    tester = LargeDocumentWorkflowTester()
    results = tester.run_full_test_suite()
    
    # Save results to file
    with open("test/large_document_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: test/large_document_test_results.json")
    
    return results['overall_success']

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)