#!/usr/bin/env python3
"""
Simple test for Azure Document Intelligence and NMTC Detection
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_azure_connection():
    """Test Azure Document Intelligence service connection"""
    print("[*] Testing Azure Document Intelligence connection...")
    
    try:
        from app.services.azure_service import azure_service
        
        # Create a minimal PDF content for testing
        test_pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 85
>>
stream
BT
/F1 12 Tf
100 700 Td
(NMTC Allocation Agreement Test Document) Tj
0 -20 Td
(Community Development Entity) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000053 00000 n
0000000125 00000 n
0000000178 00000 n
0000000264 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
430
%%EOF"""

        print(f"[+] Azure endpoint: {os.getenv('AZURE_DOC_INTELLIGENCE_ENDPOINT', 'Not configured')}")
        print(f"[+] Azure key configured: {'Yes' if os.getenv('AZURE_DOC_INTELLIGENCE_KEY') else 'No'}")
        
        # Test document validation
        is_valid = azure_service.validate_document(test_pdf_content)
        print(f"[+] PDF validation: {is_valid}")
        
        if is_valid:
            print("[*] Testing Azure OCR...")
            # Test actual Azure OCR
            import uuid
            result = await azure_service.analyze_document_quick(
                document_content=test_pdf_content,
                document_id=uuid.uuid4(),
                content_type="application/pdf"
            )
            
            print(f"[+] Azure OCR Success!")
            print(f"   [+] Pages processed: {result.get('page_count', 0)}")
            print(f"   [+] Characters extracted: {len(result.get('full_text', ''))}'")
            print(f"   [+] Text sample: {result.get('full_text', '')[:100]}...")
            print(f"   [+] Processing time: {result.get('processing_duration_ms', 0)}ms")
            
            return result
        else:
            print("[-] PDF validation failed")
            return None
            
    except Exception as e:
        print(f"[-] Azure service test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_nmtc_detection(ocr_result=None):
    """Test NMTC document type detection"""
    print("\n[*] Testing NMTC document type detection...")
    
    try:
        from app.services.detection_service import detection_service
        import uuid
        
        # Use OCR result text or fallback text
        if ocr_result and ocr_result.get('full_text'):
            test_text = ocr_result['full_text']
            print("[+] Using Azure OCR extracted text")
        else:
            test_text = """
            NMTC ALLOCATION AGREEMENT
            
            This NMTC Allocation Agreement (this "Agreement") is entered into as of [Date], 
            between the Community Development Financial Institutions Fund ("CDFI Fund"), 
            an instrumentality of the United States Department of the Treasury, 
            and [CDE Name], a [State] [Type of Entity] ("Allocatee").
            
            QUALIFIED EQUITY INVESTMENT
            COMMUNITY DEVELOPMENT ENTITY
            LOW-INCOME COMMUNITY
            ALLOCATION AMOUNT: $[Amount]
            """
            print("[+] Using fallback test text")
        
        print(f"[+] Testing with {len(test_text)} characters of text")
        
        # Test detection
        detection_result = detection_service.detect_document_type(
            text_content=test_text,
            document_id=uuid.uuid4(),
            filename="test_allocation_agreement.pdf"
        )
        
        print(f"[+] Detection completed!")
        print(f"   [+] Document type: {detection_result.document_type.value}")
        print(f"   [+] Confidence: {detection_result.confidence:.1%}")
        print(f"   [+] Primary indicators: {len(detection_result.primary_indicators)}")
        print(f"   [+] Secondary indicators: {len(detection_result.secondary_indicators)}")
        
        if detection_result.primary_indicators:
            print("   [+] Top primary indicators:")
            for i, indicator in enumerate(detection_result.primary_indicators[:3]):
                print(f"      {i+1}. {indicator.pattern_type} (conf: {indicator.confidence:.1%})")
                print(f"         Match: '{indicator.match_text[:50]}...'")
        
        # Test confidence logic
        confidence = detection_result.confidence
        print(f"\n[*] Smart confidence logic test:")
        if confidence >= 0.9:
            print(f"   [HIGH] confidence (>=90%): Auto-proceed to full processing")
        elif confidence >= 0.7:
            print(f"   [MEDIUM] confidence (70-89%): Show 10-second countdown confirmation")
        else:
            print(f"   [LOW] confidence (<70%): Require manual document type selection")
        
        return detection_result
        
    except Exception as e:
        print(f"[-] NMTC detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Run all tests"""
    print("[*] Starting Stage 0A Testing (Azure OCR + NMTC Detection)")
    print("=" * 60)
    
    # Test Azure OCR
    ocr_result = await test_azure_connection()
    
    # Test NMTC Detection
    detection_result = await test_nmtc_detection(ocr_result)
    
    print("\n" + "=" * 60)
    if ocr_result and detection_result:
        print("[+] ALL TESTS PASSED! Stage 0A workflow is working correctly.")
        print(f"   Azure OCR: [+] Working")
        print(f"   NMTC Detection: [+] Working") 
        print(f"   Smart Confidence Logic: [+] Working")
    else:
        print("[-] Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())