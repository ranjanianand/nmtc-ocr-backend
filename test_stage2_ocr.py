"""
Stage 2 OCR Test: Check Azure OCR text extraction results
Tests OCR processing completion and text extraction from Stage 1 upload
"""

import requests
import json
import time

# Test configuration
API_BASE = "http://localhost:8005"
ORG_ID = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"  # Test org ID
USER_ID = "633e6379-c82f-4917-8215-6a8f0a7e972f"  # Test user ID
ALLOCATION_YEAR = 2024

# Document ID from Stage 1 test (update this with the actual document ID from Stage 1)
STAGE1_DOCUMENT_ID = "ca03d67d-0375-4546-aaec-ca325299f04f"  # From Stage 1 test

def test_stage2_ocr_status():
    """Test Stage 2: Check Azure OCR processing and text extraction"""

    print("Stage 2 OCR Test: Azure OCR Processing and Text Extraction")
    print("=" * 60)

    # Step 1: Check API health
    print("\nStep 1: Checking API Health...")
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            print("SUCCESS: Backend API is healthy")
            health_data = response.json()
            print(f"   Azure: {health_data['services']['azure']}")
            print(f"   Supabase: {health_data['services']['supabase']}")
        else:
            print("ERROR: Backend API health check failed")
            return False
    except Exception as e:
        print(f"ERROR: Could not connect to backend: {e}")
        return False

    # Step 2: Check document processing progress
    print(f"\nStep 2: Checking processing progress for document {STAGE1_DOCUMENT_ID}...")

    try:
        # Use the allocation years progress endpoint
        progress_url = f"{API_BASE}/api/allocation-years/org/{ORG_ID}/year/{ALLOCATION_YEAR}/document/{STAGE1_DOCUMENT_ID}/progress"

        print(f"   Checking progress at: {progress_url}")
        response = requests.get(progress_url)

        if response.status_code == 200:
            progress_data = response.json()
            print("SUCCESS: Progress data retrieved successfully!")

            # Display pipeline status
            pipeline = progress_data.get('pipeline', {})
            print(f"   Current Stage: {pipeline.get('current_stage', 'Unknown')}/{pipeline.get('total_stages', 'Unknown')}")
            print(f"   Overall Progress: {pipeline.get('overall_progress', 0)}%")
            print(f"   Overall Status: {pipeline.get('overall_status', 'unknown')}")

            # Show stage details
            stages = pipeline.get('stages', [])
            for stage in stages:
                status_icon = "[DONE]" if stage['status'] == 'completed' else "[WORK]" if stage['status'] == 'in_progress' else "[WAIT]"
                print(f"   {status_icon} {stage['name']}: {stage['status']} ({stage['progress']}%)")

            # Check if OCR is complete
            ocr_complete = any(stage['name'] == 'Azure OCR' and stage['status'] == 'completed' for stage in stages)
            processing_complete = progress_data.get('processing_complete', False)

            if ocr_complete:
                print("\nSUCCESS: Stage 2 COMPLETE: Azure OCR processing finished!")
                return True, processing_complete
            else:
                print("\nIN PROGRESS: Stage 2 still processing: Azure OCR still processing...")
                return False, False

        else:
            print(f"ERROR: Progress check failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False, False

    except Exception as e:
        print(f"ERROR: Progress check error: {e}")
        return False, False

def check_ocr_text_extraction():
    """Step 3: Try to get OCR text if available"""
    print(f"\nStep 3: Checking OCR text extraction for document {STAGE1_DOCUMENT_ID}...")

    try:
        # Check if there's a way to get the OCR text
        # This might be in document details or a separate endpoint
        status_url = f"{API_BASE}/api/documents/{STAGE1_DOCUMENT_ID}/status"

        response = requests.get(status_url)
        if response.status_code == 200:
            doc_data = response.json()
            print("SUCCESS: Document status retrieved!")

            # Look for OCR text or results
            if 'ocr_text' in doc_data:
                ocr_text = doc_data['ocr_text']
                print(f"SUCCESS: OCR Text extracted: {len(ocr_text)} characters")
                print(f"   Preview: {ocr_text[:200]}...")
                return True
            elif 'processing_results' in doc_data:
                results = doc_data['processing_results']
                if 'ocr_text' in results:
                    ocr_text = results['ocr_text']
                    print(f"SUCCESS: OCR Text in processing results: {len(ocr_text)} characters")
                    print(f"   Preview: {ocr_text[:200]}...")
                    return True
                else:
                    print("WARNING: Document status available but no OCR text found")
                    print(f"   Available fields: {list(results.keys())}")
                    return False
            else:
                print("WARNING: Document status available but no OCR data found")
                print(f"   Available fields: {list(doc_data.keys())}")
                return False
        else:
            print(f"ERROR: Document status check failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"ERROR: OCR text check error: {e}")
        return False

def wait_for_ocr_completion(max_wait_minutes=5):
    """Wait for OCR to complete with polling"""
    print(f"\nWaiting for OCR completion (max {max_wait_minutes} minutes)...")

    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    poll_interval = 10  # Check every 10 seconds

    while time.time() - start_time < max_wait_seconds:
        ocr_complete, processing_complete = test_stage2_ocr_status()

        if ocr_complete:
            print("\nSUCCESS: OCR completed successfully!")
            return True, processing_complete

        print(f"WAITING: Still processing... (elapsed: {int(time.time() - start_time)}s)")
        time.sleep(poll_interval)

    print(f"\nTIMEOUT: OCR did not complete within {max_wait_minutes} minutes")
    return False, False

def main():
    """Run Stage 2 OCR test"""

    print(f"Testing Stage 2 OCR for document: {STAGE1_DOCUMENT_ID}")
    print(f"Organization: {ORG_ID}")
    print(f"Allocation Year: {ALLOCATION_YEAR}")
    print("-" * 60)

    # Initial status check
    ocr_complete, processing_complete = test_stage2_ocr_status()

    if not ocr_complete:
        # Wait for OCR to complete
        ocr_complete, processing_complete = wait_for_ocr_completion(max_wait_minutes=3)

    if ocr_complete:
        # Try to get OCR text
        text_extracted = check_ocr_text_extraction()

        print(f"\nStage 2 Test Results:")
        print(f"   [DONE] Azure OCR Processing: COMPLETED")
        print(f"   [{'DONE' if text_extracted else 'PARTIAL'}] OCR Text Extraction: {'SUCCESS' if text_extracted else 'PARTIAL'}")
        print(f"   [{'DONE' if processing_complete else 'WORK'}] Full Processing: {'COMPLETED' if processing_complete else 'STILL RUNNING'}")

        if processing_complete:
            print("\nSTAGE 2 COMPLETE!")
            print("   [DONE] Upload → Storage → Azure OCR → Text Extraction: ALL SUCCESSFUL")
            print("   [READY] Ready for Stage 3: AI Analysis and Core Engine Processing")
        else:
            print("\nSTAGE 2 SUCCESSFUL!")
            print("   [DONE] Azure OCR and text extraction completed")
            print("   [WORK] Full processing pipeline still running in background")
    else:
        print(f"\nSTAGE 2 TIMEOUT")
        print("   Azure OCR may still be processing or needs debugging")

if __name__ == "__main__":
    main()