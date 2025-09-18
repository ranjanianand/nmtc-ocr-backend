"""
Quick API Test - Validate Core Engine v3 endpoints
"""

import requests
import json
import time

def test_health_endpoint():
    """Test API health endpoint"""
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=10)
        print(f"Health Check: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
            return True
        return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_database_connection():
    """Test database connectivity"""
    try:
        response = requests.get("http://localhost:8000/api/v3/health/database", timeout=10)
        print(f"Database Test: {response.status_code}")
        if response.status_code == 200:
            print(f"Database Status: {response.json()}")
            return True
        return False
    except Exception as e:
        print(f"Database test failed: {e}")
        return False

def test_upload_endpoint():
    """Test upload endpoint with small file"""
    try:
        # Create small test file
        test_content = b"%PDF-1.4\nThis is a test PDF content for API validation."
        
        files = {'file': ('test.pdf', test_content, 'application/pdf')}
        data = {
            'org_id': 'test_org',
            'user_id': 'test_user',
            'cde_name': 'Test CDE',
            'client_info': 'API Test'
        }
        
        response = requests.post(
            "http://localhost:8000/api/v3/documents/upload",
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"Upload Test: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Upload Response: {result}")
            return result.get('success', False), result.get('document_id')
        else:
            print(f"Upload failed: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"Upload test failed: {e}")
        return False, None

def main():
    print("🔍 Quick API Validation Test")
    print("=" * 40)
    
    # Test 1: Health
    if not test_health_endpoint():
        print("❌ Health check failed - stopping tests")
        return False
    
    # Test 2: Database
    if not test_database_connection():
        print("❌ Database test failed - stopping tests")
        return False
    
    # Test 3: Upload
    success, doc_id = test_upload_endpoint()
    if success:
        print(f"✅ Upload successful - Document ID: {doc_id}")
        return True
    else:
        print("❌ Upload test failed")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ All quick tests passed - API is ready for large document testing")
    else:
        print("\n❌ Quick tests failed - fix issues before large document testing")