"""
Simple test for allocation agreement endpoint
"""

import requests
import os

def test_allocation_endpoint():
    """Test the allocation agreement endpoint"""

    backend_url = "http://localhost:8006"

    # Test health first
    try:
        health = requests.get(f"{backend_url}/api/stage1-ocr/health")
        print(f"Health check: {health.status_code}")
        if health.status_code == 200:
            print(f"Health response: {health.json()}")
    except Exception as e:
        print(f"Health error: {e}")

    # Test the allocation endpoint
    try:
        test_file = "AA_form.pdf"
        if not os.path.exists(test_file):
            print("No test file found")
            return

        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'application/pdf')}
            data = {
                'org_id': 'test-org',
                'user_id': 'test-user',
                'allocation_year': '2025',
                'description': 'Test upload'
            }

            response = requests.post(
                f"{backend_url}/api/stage1-ocr/upload-allocation-agreement",
                files=files,
                data=data
            )

            print(f"Upload status: {response.status_code}")
            if response.status_code == 200:
                print("SUCCESS: Allocation agreement endpoint working")
                result = response.json()
                print(f"Job ID: {result.get('job_id')}")
                print(f"Document ID: {result.get('document_id')}")
            else:
                print(f"Error: {response.text}")

    except Exception as e:
        print(f"Upload error: {e}")

if __name__ == "__main__":
    test_allocation_endpoint()