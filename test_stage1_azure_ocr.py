"""
Stage 1 Azure OCR Test: Direct Azure OCR extraction and data storage
Tests Azure OCR service independently to extract text and store results
"""

import os
import asyncio
import uuid
from pathlib import Path

async def test_azure_ocr_direct():
    """Test Stage 1: Direct Azure OCR text extraction"""

    print("Stage 1 Azure OCR Test: Direct Text Extraction and Storage")
    print("=" * 60)

    # Step 1: Import and initialize Azure service
    print("\nStep 1: Initializing Azure Document Intelligence service...")
    try:
        from app.services.azure_service import AzureDocumentIntelligenceService
        azure_service = AzureDocumentIntelligenceService()
        print("SUCCESS: Azure service initialized")
    except Exception as e:
        print(f"ERROR: Failed to initialize Azure service: {e}")
        return False

    # Step 2: Find test PDF file
    print("\nStep 2: Finding test PDF file...")
    test_file = "AA_form.pdf"

    if not os.path.exists(test_file):
        print(f"ERROR: Test file {test_file} not found")
        return False

    print(f"SUCCESS: Found test file: {test_file}")
    file_size = os.path.getsize(test_file) / (1024 * 1024)  # MB
    print(f"   File size: {file_size:.2f} MB")

    # Step 3: Read file content
    print("\nStep 3: Reading PDF content...")
    try:
        with open(test_file, 'rb') as f:
            file_content = f.read()
        print(f"SUCCESS: Read {len(file_content)} bytes from PDF")
    except Exception as e:
        print(f"ERROR: Failed to read file: {e}")
        return False

    # Step 4: Test Azure OCR extraction
    print("\nStep 4: Testing Azure OCR text extraction...")
    try:
        document_id = uuid.uuid4()
        print(f"   Using document ID: {document_id}")

        # Call Azure OCR directly
        print("   Calling Azure Document Intelligence API...")
        ocr_results = await azure_service.analyze_document_quick(
            document_content=file_content,
            document_id=document_id,
            content_type="application/pdf"
        )

        print("SUCCESS: Azure OCR completed!")
        print(f"   Analysis type: {ocr_results.get('analysis_type', 'unknown')}")
        print(f"   Processing duration: {ocr_results.get('processing_duration_ms', 0):.2f}ms")
        print(f"   Page count: {ocr_results.get('page_count', 0)}")

        # Check extracted text
        full_text = ocr_results.get('full_text', '')
        if full_text:
            print(f"SUCCESS: Extracted text: {len(full_text)} characters")
            print(f"   Text preview: {full_text[:200]}...")
            return True, ocr_results
        else:
            print("WARNING: No text extracted from document")
            return False, ocr_results

    except Exception as e:
        print(f"ERROR: Azure OCR failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

async def test_data_storage_simulation():
    """Test Stage 1: Simulate storing OCR data to database"""

    print("\nStep 5: Simulating OCR data storage...")

    # Simulate how the data would be stored
    sample_ocr_data = {
        "document_id": "ca03d67d-0375-4546-aaec-ca325299f04f",
        "full_text": "Sample extracted text from Azure OCR...",
        "analysis_type": "quick_read",
        "page_count": 2,
        "processed_at": "2025-09-17T09:00:00Z"
    }

    print("   OCR data structure for database storage:")
    print(f"   - Document ID: {sample_ocr_data['document_id']}")
    print(f"   - Full text length: {len(sample_ocr_data['full_text'])} characters")
    print(f"   - Analysis type: {sample_ocr_data['analysis_type']}")
    print(f"   - Page count: {sample_ocr_data['page_count']}")
    print(f"   - Processed at: {sample_ocr_data['processed_at']}")

    # In a real scenario, this would be stored to Supabase documents table
    # with fields like: ocr_text, ocr_status, ocr_metadata
    print("\n   Database storage fields:")
    print("   - ocr_text: Full extracted text content")
    print("   - ocr_status: 'completed'")
    print("   - ocr_metadata: JSON with analysis details")
    print("   - processing_results: Complete OCR results structure")

    return True

async def main():
    """Run Stage 1 Azure OCR test"""

    print("Testing Stage 1: Azure OCR Extraction and Data Storage")
    print("Focus: Upload -> Azure OCR -> Text Extraction -> Data Store")
    print("-" * 60)

    # Test direct Azure OCR
    ocr_success, ocr_results = await test_azure_ocr_direct()

    if ocr_success:
        print("\nSTAGE 1 AZURE OCR: SUCCESS")
        print("   [DONE] Azure Document Intelligence API connection")
        print("   [DONE] PDF file reading and processing")
        print("   [DONE] Text extraction via prebuilt-read model")
        print("   [DONE] Structured OCR results generation")

        # Show what data would be stored
        await test_data_storage_simulation()

        print("\nSTAGE 1 COMPLETE!")
        print("   Azure OCR extraction working correctly")
        print("   Text extraction: VERIFIED")
        print("   Data structure: READY FOR STORAGE")
        print("\nNext: Store OCR results in database and verify persistence")

    else:
        print("\nSTAGE 1 FAILED")
        print("   Azure OCR extraction not working")
        print("   Check Azure configuration and API keys")

if __name__ == "__main__":
    asyncio.run(main())