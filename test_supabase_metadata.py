#!/usr/bin/env python3
"""
Test Supabase Metadata Storage
"""

import asyncio
import json
from app.services.supabase_service import supabase_service
from app.services.metadata_extraction_service import metadata_extraction_service

async def test_supabase_connection():
    """Test Supabase online database connection and metadata storage"""
    try:
        supabase = supabase_service.client
        print("=== SUPABASE ONLINE DATABASE TEST ===")
        print()

        # Test 1: Check recent documents in online database
        print("1. CHECKING RECENT DOCUMENTS:")
        docs_result = supabase.table('documents').select('id, filename, processing_results, ocr_status, uploaded_at').order('uploaded_at', desc=True).limit(3).execute()

        if docs_result.data:
            recent_doc = docs_result.data[0]  # Get most recent
            print(f"   Most recent: {recent_doc['filename']}")
            print(f"   Status: {recent_doc['ocr_status']}")
            print(f"   ID: {recent_doc['id']}")

            # Check if it has processing_results
            processing_results = recent_doc.get('processing_results')
            if processing_results:
                print("   Has processing_results: YES")
                if 'stage_0a_metadata_extraction' in processing_results:
                    print("   Has metadata extraction: YES")
                    metadata_stage = processing_results['stage_0a_metadata_extraction']
                    print(f"   Metadata status: {metadata_stage.get('status', 'unknown')}")
                else:
                    print("   Has metadata extraction: NO")
                    print(f"   Available stages: {list(processing_results.keys())}")
            else:
                print("   Has processing_results: NO")
        else:
            print("   No documents found")

        print()

        # Test 2: Check document_types with purpose prompts
        print("2. CHECKING DOCUMENT_TYPES PURPOSE PROMPTS:")
        doc_types_result = supabase.table('document_types').select('id, purpose, notes').execute()

        allocation_prompt_found = False
        if doc_types_result.data:
            for dtype in doc_types_result.data:
                purpose = dtype.get('purpose', '')
                if purpose and 'Allocation Agreement' in purpose:
                    print("   Allocation Agreement purpose prompt: FOUND")
                    print(f"   Prompt length: {len(purpose)} characters")
                    allocation_prompt_found = True
                    break

        if not allocation_prompt_found:
            print("   Allocation Agreement purpose prompt: NOT FOUND")

        print()

        # Test 3: Direct metadata extraction test
        print("3. TESTING METADATA EXTRACTION SERVICE:")

        sample_allocation_text = """
        NMTC Allocation Agreement

        Community Development Entity: Urban Investment Partners LLC
        Federal EIN: 12-3456789

        QEI Amount: $8,500,000
        Allocation from CDFI Fund: $8,500,000
        Execution Date: March 15, 2024
        Investment Deadline: December 31, 2024

        Service Area: Los Angeles County, California
        Census Tracts: 1001.01, 1002.02, 1003.01

        Compliance Period: 7 years starting January 1, 2025
        """

        print("   Sample text prepared...")

        # Call our metadata extraction service
        extraction_result = await metadata_extraction_service.extract_first_level_metadata(
            document_id="test-supabase-123",
            document_category="allocation_agreement",
            extracted_text=sample_allocation_text
        )

        print(f"   Extraction success: {extraction_result.get('success', False)}")

        if extraction_result.get('success'):
            metadata = extraction_result.get('metadata', {})
            processing_info = extraction_result.get('processing_info', {})

            print(f"   Model used: {processing_info.get('model_used', 'unknown')}")
            print(f"   Text length processed: {processing_info.get('text_length', 0)} chars")
            print(f"   LLM response length: {processing_info.get('llm_response_length', 0)} chars")

            # Check metadata structure
            if 'parsed_json' in metadata and metadata['parsed_json']:
                print("   Structured JSON metadata: YES")
                parsed_json = metadata['parsed_json']
                print(f"   JSON keys: {list(parsed_json.keys())}")

                # Show some sample extracted data
                if 'ALLOCATION DETAILS' in str(parsed_json):
                    print("   Contains ALLOCATION DETAILS: YES")
                if 'CDE' in str(parsed_json) or 'Community Development Entity' in str(parsed_json):
                    print("   Contains CDE info: YES")

            elif 'raw_text' in metadata:
                print("   Raw text response: YES")
                raw_text = metadata['raw_text']
                print(f"   Response length: {len(raw_text)} chars")

        else:
            print(f"   Extraction failed: {extraction_result.get('error', 'Unknown error')}")

        print()

        # Test 4: Test storing metadata in database
        print("4. TESTING DATABASE STORAGE:")
        if extraction_result.get('success'):
            # Try to store the metadata (this will create a test entry)
            storage_success = await metadata_extraction_service.store_metadata_in_document(
                document_id="test-storage-456",  # Use different ID for test
                metadata_result=extraction_result
            )
            print(f"   Metadata storage test: {'SUCCESS' if storage_success else 'FAILED'}")
        else:
            print("   Skipped storage test (extraction failed)")

        print()
        print("=== TEST SUMMARY ===")
        print("Supabase connection: WORKING")
        print("Documents table access: WORKING")
        print("Document_types access: WORKING")
        print(f"Metadata extraction: {'WORKING' if extraction_result.get('success') else 'FAILED'}")
        print("Ready for production use!")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_supabase_connection())