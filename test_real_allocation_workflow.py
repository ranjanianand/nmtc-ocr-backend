#!/usr/bin/env python3
"""
Real Allocation Agreement Workflow Test
Tests the complete upload → Azure OCR → processing → report generation workflow using actual PDF.
"""

import requests
import json
import time
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8001"
TEST_ORG_ID = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"
TEST_YEAR = 2023  # Use 2023 for this test
PDF_FILE_PATH = "pdfs/AA_form.pdf"

def test_real_allocation_upload():
    """Test upload with real allocation agreement PDF"""
    print("=" * 60)
    print("REAL ALLOCATION AGREEMENT WORKFLOW TEST")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"Org ID: {TEST_ORG_ID}")
    print(f"Year: {TEST_YEAR}")
    print(f"PDF File: {PDF_FILE_PATH}")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    # Prepare the upload
    url = f"{BASE_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/upload-allocation"
    print(f"[INFO] Upload URL: {url}")

    # Upload real PDF file
    try:
        with open(PDF_FILE_PATH, 'rb') as f:
            files = {
                'file': ('AA_form.pdf', f, 'application/pdf')
            }
            data = {
                'description': f'Real allocation agreement test for {TEST_YEAR}'
            }

            print("[INFO] Uploading real PDF file...")
            response = requests.post(url, files=files, data=data, timeout=30)

            print(f"[INFO] Response status: {response.status_code}")

            if response.status_code == 200:
                response_data = response.json()
                print("[SUCCESS] Upload successful!")
                print("[INFO] Response data:")
                print(json.dumps(response_data, indent=2))

                document_id = response_data.get('document_id')
                pipeline_started = response_data.get('pipelineStarted')

                print()
                print("=" * 40)
                print("UPLOAD RESULTS")
                print("=" * 40)
                print(f"Document ID: {document_id}")
                print(f"Pipeline Started: {pipeline_started}")

                return {
                    'success': True,
                    'document_id': document_id,
                    'response': response_data
                }
            else:
                print(f"[ERROR] Upload failed with status {response.status_code}")
                print(f"[ERROR] Response: {response.text}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}

    except FileNotFoundError:
        print(f"[ERROR] PDF file not found: {PDF_FILE_PATH}")
        return {'success': False, 'error': 'File not found'}
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request failed: {e}")
        return {'success': False, 'error': str(e)}

def monitor_processing_progress(document_id, max_wait_minutes=10):
    """Monitor the processing progress until completion"""
    if not document_id:
        print("[ERROR] No document ID provided for monitoring")
        return False

    print()
    print("=" * 60)
    print("PROCESSING MONITORING")
    print("=" * 60)
    print(f"Document ID: {document_id}")
    print(f"Max wait time: {max_wait_minutes} minutes")
    print()

    url = f"{BASE_URL}/api/allocation-years/org/{TEST_ORG_ID}/year/{TEST_YEAR}/document/{document_id}/progress"

    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    check_count = 0

    while time.time() - start_time < max_wait_seconds:
        check_count += 1
        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                progress_data = response.json()
                pipeline = progress_data.get('pipeline', {})
                overall_status = pipeline.get('overall_status', 'unknown')
                overall_progress = pipeline.get('overall_progress', 0)
                current_stage = pipeline.get('current_stage', 0)

                print(f"[CHECK {check_count}] Status: {overall_status}, Progress: {overall_progress}%, Stage: {current_stage}/6")

                # Check if processing is complete
                if overall_status == 'completed' or overall_progress >= 100:
                    print("[SUCCESS] Processing completed!")
                    print("[INFO] Final progress data:")
                    print(json.dumps(progress_data, indent=2))
                    return progress_data
                elif overall_status == 'failed':
                    print("[ERROR] Processing failed!")
                    print(json.dumps(progress_data, indent=2))
                    return False

                # Wait before next check
                time.sleep(30)  # Check every 30 seconds
            else:
                print(f"[WARNING] Progress check failed: {response.status_code}")
                time.sleep(30)

        except requests.exceptions.RequestException as e:
            print(f"[WARNING] Progress check error: {e}")
            time.sleep(30)

    print(f"[TIMEOUT] Processing did not complete within {max_wait_minutes} minutes")
    return False

def check_final_results(document_id):
    """Check the final processing results and extracted data"""
    print()
    print("=" * 60)
    print("FINAL RESULTS ANALYSIS")
    print("=" * 60)

    # Check document status
    print("[INFO] Checking document status...")

    # Check processing results via API (if available)
    try:
        # Try to get document details
        doc_url = f"{BASE_URL}/api/documents/{document_id}"
        response = requests.get(doc_url, timeout=10)

        if response.status_code == 200:
            doc_data = response.json()
            print("[SUCCESS] Document details retrieved:")
            print(json.dumps(doc_data, indent=2))
            return doc_data
        else:
            print(f"[INFO] Document API returned {response.status_code}")

    except Exception as e:
        print(f"[INFO] Document API check: {e}")

    # Check allocation year update
    print("\n[INFO] Checking allocation year status...")
    try:
        year_url = f"{BASE_URL}/api/allocation-years/org/{TEST_ORG_ID}"
        response = requests.get(year_url, timeout=10)

        if response.status_code == 200:
            years_data = response.json()
            print("[SUCCESS] Allocation years data:")
            print(json.dumps(years_data, indent=2))

            # Find our specific year
            for year_info in years_data.get('allocation_years', []):
                if year_info.get('year') == TEST_YEAR:
                    print(f"\n[FOCUS] Year {TEST_YEAR} details:")
                    print(f"- Status: {year_info.get('status')}")
                    print(f"- Total Amount: ${year_info.get('total_amount', 0):,.2f}")
                    print(f"- Has Document: {year_info.get('has_allocation_document')}")
                    break

        else:
            print(f"[INFO] Allocation years API returned {response.status_code}")

    except Exception as e:
        print(f"[INFO] Allocation years API check: {e}")

def main():
    """Run the complete real allocation workflow test"""
    print("Starting Real Allocation Agreement Workflow Test")
    print(f"Started at: {datetime.now().isoformat()}")

    # Step 1: Upload real PDF
    upload_result = test_real_allocation_upload()

    if not upload_result['success']:
        print("\n[FAILED] Upload failed, cannot continue")
        return upload_result

    document_id = upload_result.get('document_id')

    # Step 2: Monitor processing progress
    print(f"\n[INFO] Starting monitoring for document: {document_id}")
    processing_result = monitor_processing_progress(document_id, max_wait_minutes=10)

    # Step 3: Check final results
    final_results = check_final_results(document_id)

    # Summary
    print()
    print("=" * 60)
    print("WORKFLOW TEST SUMMARY")
    print("=" * 60)
    print(f"Upload: {'PASS' if upload_result['success'] else 'FAIL'}")
    print(f"Processing: {'PASS' if processing_result else 'TIMEOUT/FAIL'}")
    print(f"Document ID: {document_id}")
    print(f"Completed at: {datetime.now().isoformat()}")

    return {
        'upload': upload_result['success'],
        'processing': bool(processing_result),
        'document_id': document_id,
        'final_results': final_results
    }

if __name__ == "__main__":
    results = main()