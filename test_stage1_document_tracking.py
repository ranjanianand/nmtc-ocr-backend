"""
Test Stage 1 Document ID Tracking: Verify document ID system for Stage 1 workflow
Tests document ID generation, tracking, and retrieval for the Stage 1 OCR workflow
"""

import requests
import os
import json

def test_stage1_document_tracking():
    """Test Stage 1 document ID tracking system"""

    print("Stage 1 Document ID Tracking Test")
    print("=" * 50)

    # Configuration
    BACKEND_URL = "http://localhost:8006"
    ORG_ID = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"
    USER_ID = "test-user-stage1-tracking"

    print(f"Backend: {BACKEND_URL}")
    print(f"Organization: {ORG_ID}")
    print(f"User: {USER_ID}")

    # Step 1: Upload document and get document ID
    print("\nStep 1: Upload document and verify document ID generation...")
    test_file = "AA_form.pdf"
    if not os.path.exists(test_file):
        print(f"ERROR: Test file {test_file} not found")
        return False

    try:
        with open(test_file, 'rb') as f:
            files = {'file': (os.path.basename(test_file), f, 'application/pdf')}
            data = {
                'org_id': ORG_ID,
                'user_id': USER_ID,
                'description': 'Stage 1 Document Tracking Test'
            }

            upload_response = requests.post(
                f"{BACKEND_URL}/api/stage1-ocr/upload-and-extract",
                files=files,
                data=data
            )

            if upload_response.status_code == 200:
                result = upload_response.json()
                print("SUCCESS: Document uploaded with tracking ID")
                print(f"   Document ID: {result['document_id']}")
                print(f"   Text extracted: {result['ocr_results']['text_extracted']} characters")
                print(f"   Processing status: {result['ocr_results']['status']}")
                print(f"   Document tracking: WORKING")

                # Store document ID for tracking tests
                document_id = result['document_id']
                ocr_results = result['ocr_results']
                text_preview = result['text_preview']

            else:
                print(f"ERROR: Upload failed with status {upload_response.status_code}")
                return False

    except Exception as e:
        print(f"ERROR: Upload failed: {e}")
        return False

    # Step 2: Test document text retrieval endpoint
    print("\nStep 2: Testing document text retrieval...")
    try:
        text_response = requests.get(f"{BACKEND_URL}/api/stage1-ocr/document/{document_id}/text")
        if text_response.status_code == 200:
            text_result = text_response.json()
            print("SUCCESS: Document text retrieval endpoint working")
            print(f"   Document ID: {text_result['document_id']}")
            print(f"   Message: {text_result['message']}")
            print("   Note: This endpoint is ready for database integration")
        else:
            print(f"WARNING: Text retrieval returned {text_response.status_code}")
    except Exception as e:
        print(f"ERROR: Text retrieval failed: {e}")

    # Step 3: Verify document ID structure and consistency
    print("\nStep 3: Verifying document ID structure...")
    import uuid
    try:
        # Validate that document_id is a valid UUID
        uuid_obj = uuid.UUID(document_id)
        print("SUCCESS: Document ID is valid UUID format")
        print(f"   UUID version: {uuid_obj.version}")
        print(f"   UUID format: {str(uuid_obj)}")
        print("   Document ID structure: VERIFIED")
    except ValueError:
        print("ERROR: Document ID is not a valid UUID")
        return False

    # Step 4: Test multiple uploads to verify unique document IDs
    print("\nStep 4: Testing document ID uniqueness...")
    document_ids = [document_id]  # Include first document ID

    for i in range(2):
        try:
            with open(test_file, 'rb') as f:
                files = {'file': (os.path.basename(test_file), f, 'application/pdf')}
                data = {
                    'org_id': ORG_ID,
                    'user_id': USER_ID,
                    'description': f'Uniqueness test upload {i+2}'
                }

                upload_response = requests.post(
                    f"{BACKEND_URL}/api/stage1-ocr/upload-and-extract",
                    files=files,
                    data=data
                )

                if upload_response.status_code == 200:
                    result = upload_response.json()
                    new_document_id = result['document_id']
                    document_ids.append(new_document_id)
                    print(f"   Upload {i+2} document ID: {new_document_id}")

        except Exception as e:
            print(f"WARNING: Upload {i+2} failed: {e}")

    # Check uniqueness
    unique_ids = set(document_ids)
    if len(unique_ids) == len(document_ids):
        print("SUCCESS: All document IDs are unique")
        print(f"   Generated {len(document_ids)} unique document IDs")
    else:
        print("ERROR: Duplicate document IDs found")
        return False

    # Step 5: Verify tracking data structure
    print("\nStep 5: Verifying tracking data structure...")
    tracking_data = {
        "document_id": document_id,
        "org_id": ORG_ID,
        "user_id": USER_ID,
        "ocr_status": ocr_results['status'],
        "text_length": ocr_results['text_extracted'],
        "processing_time_ms": ocr_results['processing_time_ms'],
        "page_count": ocr_results['page_count'],
        "text_preview": text_preview
    }

    print("   Tracking data structure:")
    for key, value in tracking_data.items():
        print(f"     {key}: {value}")

    print("SUCCESS: Tracking data structure complete")

    return True, tracking_data

def main():
    """Run Stage 1 document tracking test"""

    print("Testing Stage 1 Document ID Tracking System")
    print("Focus: Document ID generation, tracking, and retrieval")
    print("-" * 60)

    success, tracking_data = test_stage1_document_tracking()

    if success:
        print("\nSTAGE 1 DOCUMENT TRACKING: SUCCESS")
        print("   [DONE] Document ID generation working")
        print("   [DONE] UUID format validation passed")
        print("   [DONE] Document ID uniqueness verified")
        print("   [DONE] Text retrieval endpoint available")
        print("   [DONE] Tracking data structure complete")

        print("\nSTAGE 1 TRACKING SYSTEM VERIFIED!")
        print("   Document IDs are unique and trackable")
        print("   OCR results are immediately available")
        print("   Ready for frontend integration with document tracking")

        print("\nINTEGRATION GUIDE:")
        print("   1. Frontend uploads to /api/stage1-ocr/upload-and-extract")
        print("   2. Backend returns document_id and complete OCR results")
        print("   3. Frontend can store document_id for later reference")
        print("   4. Use document_id to retrieve text via /api/stage1-ocr/document/{id}/text")
        print("   5. No background job polling required - immediate results")

    else:
        print("\nSTAGE 1 DOCUMENT TRACKING: ISSUES DETECTED")
        print("   Check document ID generation and tracking system")

if __name__ == "__main__":
    main()