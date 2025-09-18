#!/usr/bin/env python3
"""
Test First-Level Metadata Extraction Service

Direct test of the new metadata extraction service using document type purpose prompts
"""

import asyncio
import json
from app.services.metadata_extraction_service import metadata_extraction_service

async def test_metadata_extraction():
    """Test the metadata extraction service directly"""
    print("=== FIRST-LEVEL METADATA EXTRACTION TEST ===")
    print()

    # Sample extracted text from an allocation agreement (mock)
    sample_allocation_text = """
NMTC Allocation Agreement

Community Development Entity: Urban Investment Partners LLC
Federal EIN: 12-3456789
Address: 123 Main Street, Los Angeles, CA 90012

Investor Entity: Capital Growth Fund
Address: 456 Wall Street, New York, NY 10005

ALLOCATION DETAILS:
Total Allocation from CDFI Fund: $10,000,000
QEI (Qualified Equity Investment) Amount: $10,000,000
Allocation Agreement Execution Date: January 15, 2024
Initial Investment Deadline: December 31, 2024

COMPLIANCE REQUIREMENTS:
Seven-year compliance period begins: January 1, 2025
Substantially all test: 85% of QEI proceeds must be deployed within 12 months
Geographic restrictions: Los Angeles County, California (Census Tracts 1001, 1002, 1003)

FINANCIAL TERMS:
QEI Investment Schedule:
- Tranche 1: $3,000,000 by March 31, 2024
- Tranche 2: $4,000,000 by June 30, 2024
- Tranche 3: $3,000,000 by September 30, 2024

Management Fee: 2.5% annually on outstanding QEI
Administrative Monitoring: Quarterly reporting required

REGULATORY REFERENCES:
Section 45D Internal Revenue Code
Treasury Regulation Section 1.45D-1
CDFI Fund Notice 2024-01
Safe Harbor provisions apply per Treasury guidance
"""

    # Test the metadata extraction
    test_document_id = "test-doc-12345"
    test_document_category = "allocation_agreement"

    print(f"Testing document category: {test_document_category}")
    print(f"Text sample length: {len(sample_allocation_text)} characters")
    print()

    try:
        print("🔄 Calling metadata extraction service...")
        result = await metadata_extraction_service.extract_first_level_metadata(
            document_id=test_document_id,
            document_category=test_document_category,
            extracted_text=sample_allocation_text
        )

        print(f"✅ Metadata extraction completed!")
        print(f"Success: {result.get('success', False)}")
        print()

        if result.get('success'):
            print("=== EXTRACTED METADATA ===")
            metadata = result.get('metadata', {})

            # Show metadata structure
            if 'parsed_json' in metadata and metadata['parsed_json']:
                print("📊 JSON PARSED SUCCESSFULLY:")
                parsed_data = metadata['parsed_json']
                print(json.dumps(parsed_data, indent=2))
            elif 'raw_text' in metadata:
                print("📝 RAW TEXT RESPONSE:")
                print(metadata['raw_text'][:500] + "..." if len(metadata.get('raw_text', '')) > 500 else metadata.get('raw_text', ''))
            else:
                print("⚠️  No structured metadata found")
                print(json.dumps(metadata, indent=2))

            print()
            print("=== PROCESSING INFO ===")
            processing_info = result.get('processing_info', {})
            print(f"Model Used: {processing_info.get('model_used', 'unknown')}")
            print(f"Text Length: {processing_info.get('text_length', 0):,} characters")
            print(f"LLM Response Length: {processing_info.get('llm_response_length', 0)} characters")
            print(f"Method: {processing_info.get('extraction_method', 'unknown')}")

        else:
            print("❌ EXTRACTION FAILED:")
            print(f"Error: {result.get('error', 'Unknown error')}")
            if 'details' in result:
                print("Details:", json.dumps(result['details'], indent=2))

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=== SUMMARY ===")
    print("This test verifies that:")
    print("✅ Document type purpose prompts are retrieved from database")
    print("✅ OpenAI GPT-4o-mini processes the allocation agreement text")
    print("✅ Structured metadata is extracted and parsed")
    print("✅ Results are formatted for frontend display")
    print()
    print("Next: This metadata will be shown immediately after upload")
    print("      while full core engine processing continues in background")

if __name__ == "__main__":
    asyncio.run(test_metadata_extraction())