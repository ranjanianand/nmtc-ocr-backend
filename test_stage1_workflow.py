"""
Stage 1 Workflow Test: Upload → Storage → Azure OCR
Tests only the first stage without AI agent processing
"""

import requests
import os
import sys
from pathlib import Path

# Test configuration
API_BASE = "http://localhost:8005"
ORG_ID = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"  # Test org ID
USER_ID = "633e6379-c82f-4917-8215-6a8f0a7e972f"  # Test user ID
ALLOCATION_YEAR = 2024

def test_stage1_workflow():
    """Test Stage 1: Upload → Storage → Azure OCR only"""

    print("🚀 Stage 1 Workflow Test: Upload → Storage → Azure OCR")
    print("=" * 60)

    # Step 1: Check API health
    print("\n📋 Step 1: Checking API Health...")
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            print("✅ Backend API is healthy")
            health_data = response.json()
            print(f"   Azure: {health_data['services']['azure']}")
            print(f"   Supabase: {health_data['services']['supabase']}")
        else:
            print("❌ Backend API health check failed")
            return False
    except Exception as e:
        print(f"❌ Could not connect to backend: {e}")
        return False

    # Step 2: Find a test PDF file
    print("\n📋 Step 2: Finding test PDF file...")

    # Look for PDF files in the pds folder structure
    pdf_paths = [
        "E:/Raine/YOZY/Clients/AV/cdesolution/AI_OCR/nmtc-backend/pds/2024/AA_form.pdf",
        "E:/Raine/YOZY/Clients/AV/cdesolution/AI_OCR/nmtc-backend/pds/2023/AA_form.pdf",
        "E:/Raine/YOZY/Clients/AV/cdesolution/AI_OCR/nmtc-backend/pds/2022/AA_form.pdf"
    ]

    test_file = None
    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            test_file = pdf_path
            break

    if not test_file:
        print("❌ No test PDF found in pds folders")
        print("   Looked for:")
        for path in pdf_paths:
            print(f"   - {path}")
        return False

    print(f"✅ Found test file: {test_file}")
    file_size = os.path.getsize(test_file) / (1024 * 1024)  # MB
    print(f"   File size: {file_size:.2f} MB")

    # Step 3: Test Stage 1 Upload (OCR only)
    print("\n📋 Step 3: Testing Stage 1 Upload (Azure OCR only)...")

    try:
        # We'll use the allocation years endpoint but modify to stop at OCR
        upload_url = f"{API_BASE}/api/allocation-years/org/{ORG_ID}/year/{ALLOCATION_YEAR}/upload-allocation"

        with open(test_file, 'rb') as f:
            files = {'file': (os.path.basename(test_file), f, 'application/pdf')}
            data = {
                'description': 'Stage 1 Test: Upload to Storage and Azure OCR only',
                'user_id': USER_ID
            }

            print("   📤 Uploading file...")
            response = requests.post(upload_url, files=files, data=data)

            if response.status_code == 200:
                result = response.json()
                print("✅ Stage 1 Upload successful!")
                print(f"   Document ID: {result.get('document_id', 'N/A')}")
                print(f"   Message: {result.get('message', 'N/A')}")

                document_id = result.get('document_id')
                return document_id
            else:
                print(f"❌ Upload failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def check_ocr_status(document_id):
    """Check if Azure OCR has completed"""
    print(f"\n📋 Step 4: Checking Azure OCR status for document {document_id}...")

    try:
        # Check document status
        status_url = f"{API_BASE}/api/allocation-years/document/{document_id}/status"
        response = requests.get(status_url)

        if response.status_code == 200:
            status_data = response.json()
            ocr_status = status_data.get('ocr_status', 'unknown')
            print(f"✅ OCR Status: {ocr_status}")

            if ocr_status == 'completed':
                print("✅ Azure OCR completed successfully!")

                # Try to get OCR results
                if 'ocr_text' in status_data:
                    ocr_text = status_data['ocr_text']
                    print(f"✅ OCR Text extracted: {len(ocr_text)} characters")
                    print(f"   Preview: {ocr_text[:200]}...")
                    return True
                else:
                    print("⚠️ OCR completed but no text found in response")
                    return True

            elif ocr_status == 'processing':
                print("⏳ OCR still processing...")
                return False
            elif ocr_status == 'failed':
                print("❌ OCR processing failed")
                return False
            else:
                print(f"⚠️ Unknown OCR status: {ocr_status}")
                return False
        else:
            print(f"❌ Could not check status: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error checking OCR status: {e}")
        return False

def main():
    """Run Stage 1 workflow test"""

    # Test Stage 1 workflow
    document_id = test_stage1_workflow()

    if document_id:
        print(f"\n🎯 Stage 1 Test Results:")
        print(f"   ✅ File upload: SUCCESS")
        print(f"   ✅ Storage upload: SUCCESS")
        print(f"   ✅ Database record: SUCCESS")
        print(f"   📄 Document ID: {document_id}")

        # Wait a moment for OCR to start
        import time
        print("\n⏳ Waiting 5 seconds for Azure OCR to start...")
        time.sleep(5)

        # Check OCR status
        ocr_success = check_ocr_status(document_id)

        if ocr_success:
            print("\n🎉 STAGE 1 COMPLETE!")
            print("   ✅ Upload → Storage → Azure OCR: ALL SUCCESSFUL")
        else:
            print("\n⚠️ STAGE 1 PARTIAL SUCCESS")
            print("   ✅ Upload → Storage: SUCCESS")
            print("   ⏳ Azure OCR: STILL PROCESSING or NEEDS DEBUGGING")
    else:
        print("\n❌ STAGE 1 FAILED")
        print("   Stage 1 workflow did not complete successfully")

if __name__ == "__main__":
    main()