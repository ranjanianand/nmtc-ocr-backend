#!/usr/bin/env python3
"""
Simple Allocation Agreement Upload Test
Tests the basic upload functionality and identifies response format issues.
"""

import requests
import json
import os
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_ORG_ID = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"
TEST_YEAR = 2024
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

def test_allocation_upload():
    """Test the allocation agreement upload endpoint"""
    print("=" * 60)
    print("ALLOCATION AGREEMENT UPLOAD TEST")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"Org ID: {TEST_ORG_ID}")
    print(f"Year: {TEST_YEAR}")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    # Create test file
    file_path = create_test_file()

    # Prepare the upload
    url = f"{BASE_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/upload-allocation"

    print(f"[INFO] Upload URL: {url}")

    # Prepare form data
    with open(file_path, 'rb') as f:
        files = {
            'file': ('test_allocation.pdf', f, 'application/pdf')
        }
        data = {
            'description': f'Test allocation agreement for {TEST_YEAR}'
        }

        try:
            print("[INFO] Sending upload request...")
            response = requests.post(url, files=files, data=data, timeout=30)

            print(f"[INFO] Response status: {response.status_code}")
            print(f"[INFO] Response headers: {dict(response.headers)}")

            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print("[SUCCESS] Upload successful!")
                    print("[INFO] Response data:")
                    print(json.dumps(response_data, indent=2))

                    # Check for key fields
                    document_id = response_data.get('document_id')
                    processing_started = response_data.get('processing_started')
                    pipeline_started = response_data.get('pipelineStarted')  # Frontend compatibility

                    print()
                    print("=" * 40)
                    print("RESPONSE ANALYSIS")
                    print("=" * 40)
                    print(f"Document ID: {document_id}")
                    print(f"Processing Started: {processing_started}")
                    print(f"Pipeline Started (frontend): {pipeline_started}")

                    # Check pipeline info
                    pipeline = response_data.get('pipeline', {})
                    if pipeline:
                        print(f"Pipeline Status: {pipeline.get('status')}")
                        print(f"Current Stage: {pipeline.get('current_stage')}")
                        print(f"Total Stages: {pipeline.get('total_stages')}")

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
                print(f"[ERROR] Upload failed with status {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request failed: {e}")
            return {'success': False, 'error': str(e)}

def test_progress_monitoring(document_id):
    """Test progress monitoring for uploaded document"""
    if not document_id:
        print("[ERROR] No document ID provided for progress monitoring")
        return False

    print()
    print("=" * 60)
    print("PROGRESS MONITORING TEST")
    print("=" * 60)

    url = f"{BASE_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/document/{document_id}/progress"
    print(f"[INFO] Progress URL: {url}")

    try:
        response = requests.get(url, timeout=10)
        print(f"[INFO] Progress response status: {response.status_code}")

        if response.status_code == 200:
            progress_data = response.json()
            print("[SUCCESS] Progress monitoring working!")
            print("[INFO] Progress data:")
            print(json.dumps(progress_data, indent=2))
            return True
        else:
            print(f"[ERROR] Progress check failed: {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Progress check failed: {e}")
        return False

def main():
    """Run the tests"""
    print("Starting Simple Allocation Agreement Tests")
    print(f"Started at: {datetime.now().isoformat()}")

    # Test 1: Upload
    upload_result = test_allocation_upload()

    # Test 2: Progress monitoring (if upload succeeded)
    progress_result = False
    if upload_result['success'] and upload_result.get('document_id'):
        progress_result = test_progress_monitoring(upload_result['document_id'])

    # Summary
    print()
    print("=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    print(f"Upload Test: {'PASS' if upload_result['success'] else 'FAIL'}")
    print(f"Progress Test: {'PASS' if progress_result else 'FAIL'}")

    if upload_result['success']:
        print(f"Document ID for further testing: {upload_result.get('document_id')}")

    print(f"Completed at: {datetime.now().isoformat()}")

    return {
        'upload': upload_result['success'],
        'progress': progress_result,
        'document_id': upload_result.get('document_id')
    }

if __name__ == "__main__":
    results = main()