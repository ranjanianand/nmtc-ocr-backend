#!/usr/bin/env python3
"""
Direct Documents Upload Test
Test the core documents upload endpoint directly to isolate UUID issues.
"""

import requests
import json
import os
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_ORG_ID = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"
TEST_USER_ID = "633e6379-c82f-4917-8215-6a8f0a7e972f"
TEST_FILE_PATH = "test_allocation.txt"

def create_test_file():
    """Create a test allocation agreement file"""
    if not os.path.exists(TEST_FILE_PATH):
        with open(TEST_FILE_PATH, 'w') as f:
            f.write("""NMTC Allocation Agreement Test Document

This is a test allocation agreement document.
Total Allocation: $10,000,000
Service Area: Los Angeles County, California
QEI Investment Deadline: December 31, 2024
""")
        print(f"[INFO] Created test file: {TEST_FILE_PATH}")
    return TEST_FILE_PATH

def test_direct_documents_upload():
    """Test the direct documents upload endpoint"""
    print("=" * 60)
    print("DIRECT DOCUMENTS UPLOAD TEST")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"Org ID: {TEST_ORG_ID}")
    print(f"User ID: {TEST_USER_ID}")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    # Create test file
    file_path = create_test_file()

    # Prepare the upload
    url = f"{BASE_URL}/api/documents/upload"

    print(f"[INFO] Upload URL: {url}")

    # Prepare form data
    with open(file_path, 'rb') as f:
        files = {
            'file': ('test_allocation.pdf', f, 'application/pdf')
        }
        data = {
            'document_type_id': 'allocation_agreement',  # Use string instead of UUID
            'description': 'Test allocation agreement direct upload',
            'org_id': TEST_ORG_ID,
            'user_id': TEST_USER_ID  # Use proper UUID
        }

        try:
            print("[INFO] Sending direct upload request...")
            response = requests.post(url, files=files, data=data, timeout=30)

            print(f"[INFO] Response status: {response.status_code}")
            print(f"[INFO] Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print("[SUCCESS] Direct upload successful!")
                    print("[INFO] Response data:")
                    print(json.dumps(response_data, indent=2))

                    document_id = response_data.get('document_id')
                    processing_started = response_data.get('processing_started')

                    print()
                    print("=" * 40)
                    print("RESPONSE ANALYSIS")
                    print("=" * 40)
                    print(f"Document ID: {document_id}")
                    print(f"Processing Started: {processing_started}")

                    return {
                        'success': True,
                        'document_id': document_id,
                        'response': response_data
                    }

                except json.JSONDecodeError as e:
                    print(f"[ERROR] Invalid JSON response: {e}")
                    print(f"[ERROR] Raw response: {response.text}")
                    return {'success': False, 'error': 'Invalid JSON response'}
            else:
                print(f"[ERROR] Direct upload failed with status {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request failed: {e}")
            return {'success': False, 'error': str(e)}

def main():
    """Run the direct documents upload test"""
    print("Starting Direct Documents Upload Test")
    print(f"Started at: {datetime.now().isoformat()}")

    # Test direct upload
    upload_result = test_direct_documents_upload()

    # Summary
    print()
    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Direct Upload Test: {'PASS' if upload_result['success'] else 'FAIL'}")

    if upload_result['success']:
        print(f"Document ID: {upload_result.get('document_id')}")
    else:
        print(f"Error: {upload_result.get('error')}")

    print(f"Completed at: {datetime.now().isoformat()}")

    return upload_result

if __name__ == "__main__":
    results = main()