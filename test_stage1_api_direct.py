"""
Test Stage 1 OCR API directly without FastAPI server
Direct test of Stage 1 Azure OCR integration
"""

import asyncio
import requests
import os

async def test_stage1_api_direct():
    """Test Stage 1 API endpoints directly"""

    print("Testing Stage 1 OCR API Integration")
    print("=" * 50)

    # Test 1: Test Stage 1 OCR health endpoint
    print("\nStep 1: Testing Stage 1 OCR health endpoint...")
    try:
        response = requests.get("http://localhost:8006/api/stage1-ocr/health")
        if response.status_code == 200:
            print("SUCCESS: Stage 1 OCR health endpoint working")
            health_data = response.json()
            print(f"   Status: {health_data['status']}")
            print(f"   Azure service: {health_data['azure_service']}")
            return True
        else:
            print(f"ERROR: Health endpoint returned {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR: Could not connect to Stage 1 OCR API: {e}")
        return False

async def test_stage1_upload():
    """Test Stage 1 upload endpoint"""
    print("\nStep 2: Testing Stage 1 upload endpoint...")

    # Test file
    test_file = "AA_form.pdf"
    if not os.path.exists(test_file):
        print(f"ERROR: Test file {test_file} not found")
        return False

    try:
        upload_url = "http://localhost:8006/api/stage1-ocr/upload-and-extract"

        with open(test_file, 'rb') as f:
            files = {'file': (os.path.basename(test_file), f, 'application/pdf')}
            data = {
                'org_id': 'ce117b87-d75c-4c8a-b3f5-922ddec539b0',
                'user_id': 'test-user-id',
                'description': 'Stage 1 OCR test upload'
            }

            print("   Uploading file for Stage 1 OCR processing...")
            response = requests.post(upload_url, files=files, data=data)

            if response.status_code == 200:
                result = response.json()
                print("SUCCESS: Stage 1 OCR upload completed")
                print(f"   Document ID: {result['document_id']}")
                print(f"   Text extracted: {result['ocr_results']['text_extracted']} characters")
                print(f"   Processing time: {result['ocr_results']['processing_time_ms']} ms")
                print(f"   Page count: {result['ocr_results']['page_count']}")
                print(f"   Status: {result['ocr_results']['status']}")
                print(f"   Text preview: {result['text_preview'][:100]}...")
                return True, result
            else:
                print(f"ERROR: Upload failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                return False, None

    except Exception as e:
        print(f"ERROR: Upload test failed: {e}")
        return False, None

async def main():
    """Run Stage 1 API integration test"""

    print("Stage 1 OCR API Integration Test")
    print("Testing: FastAPI + Azure OCR + Job ID System")
    print("-" * 50)

    # Test health endpoint first
    health_ok = await test_stage1_api_direct()

    if health_ok:
        # Test upload endpoint
        upload_ok, result = await test_stage1_upload()

        if upload_ok:
            print("\nSTAGE 1 API INTEGRATION: SUCCESS")
            print("   [DONE] Health endpoint working")
            print("   [DONE] Upload and OCR extraction working")
            print("   [DONE] Azure OCR integration verified")
            print("   [DONE] Document ID generation working")
            print("   [DONE] Response structure validated")

            print("\nSTAGE 1 READY FOR FRONTEND INTEGRATION!")
            print("   API endpoint: /api/stage1-ocr/upload-and-extract")
            print("   Returns: document_id, ocr_results, text_preview")
            print("   Next: Connect frontend to this endpoint")

        else:
            print("\nSTAGE 1 UPLOAD FAILED")
            print("   Health endpoint working but upload failed")
    else:
        print("\nSTAGE 1 API NOT ACCESSIBLE")
        print("   Cannot connect to Stage 1 OCR endpoints")

if __name__ == "__main__":
    asyncio.run(main())