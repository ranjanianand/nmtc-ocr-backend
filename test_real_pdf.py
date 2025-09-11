#!/usr/bin/env python3
"""
Test Azure OCR and NMTC Detection with real PDF file
"""
import asyncio
import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_real_pdf():
    """Test Azure OCR with the real AA_form.pdf file"""
    print("[*] Testing with real PDF file: AA_form.pdf")
    print("=" * 60)
    
    try:
        # Read the real PDF file
        pdf_path = "pdfs/AA_form.pdf"
        if not os.path.exists(pdf_path):
            print(f"[-] PDF file not found: {pdf_path}")
            return
        
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        print(f"[+] Loaded PDF: {len(pdf_content)} bytes")
        
        # Test Azure OCR
        from app.services.azure_service import azure_service
        
        print("[*] Starting Azure OCR processing...")
        
        result = await azure_service.analyze_document_quick(
            document_content=pdf_content,
            document_id=uuid.uuid4(),
            content_type="application/pdf"
        )
        
        print(f"[+] Azure OCR completed successfully!")
        print(f"   [+] Pages processed: {result.get('page_count', 0)}")
        print(f"   [+] Characters extracted: {len(result.get('full_text', ''))}")
        print(f"   [+] Processing time: {result.get('processing_duration_ms', 0)}ms")
        
        # Show a sample of extracted text
        full_text = result.get('full_text', '')
        if len(full_text) > 200:
            print(f"   [+] Text sample (first 200 chars): {full_text[:200]}...")
        else:
            print(f"   [+] Full text: {full_text}")
        
        # Test NMTC Detection with real extracted text
        print("\n[*] Testing NMTC detection with extracted text...")
        
        from app.services.detection_service import detection_service
        
        detection_result = detection_service.detect_document_type(
            text_content=full_text,
            document_id=uuid.uuid4(),
            filename="AA_form.pdf"
        )
        
        print(f"[+] NMTC Detection completed!")
        print(f"   [+] Document type: {detection_result.document_type.value}")
        print(f"   [+] Confidence: {detection_result.confidence:.1%}")
        print(f"   [+] Primary indicators: {len(detection_result.primary_indicators)}")
        print(f"   [+] Secondary indicators: {len(detection_result.secondary_indicators)}")
        
        # Show top indicators
        if detection_result.primary_indicators:
            print("   [+] Top primary indicators:")
            for i, indicator in enumerate(detection_result.primary_indicators[:5]):
                print(f"      {i+1}. {indicator.pattern_type} (conf: {indicator.confidence:.1%})")
                # Show first 60 chars of match
                match_text = indicator.match_text[:60] + "..." if len(indicator.match_text) > 60 else indicator.match_text
                print(f"         Match: '{match_text}'")
        
        # Test confidence logic
        confidence = detection_result.confidence
        print(f"\n[*] Smart confidence logic result:")
        if confidence >= 0.9:
            print(f"   [HIGH] confidence (>=90%): Auto-proceed to full processing")
        elif confidence >= 0.7:
            print(f"   [MEDIUM] confidence (70-89%): Show 10-second countdown confirmation")
        else:
            print(f"   [LOW] confidence (<70%): Require manual document type selection")
        
        print(f"\n" + "=" * 60)
        print("[+] REAL PDF TEST COMPLETED SUCCESSFULLY!")
        print(f"[+] Document: AA_form.pdf ({len(pdf_content)} bytes)")
        print(f"[+] Azure OCR: {result.get('page_count', 0)} pages, {len(full_text)} characters")
        print(f"[+] Detection: {detection_result.document_type.value} ({confidence:.1%} confidence)")
        
        return {
            'ocr_result': result,
            'detection_result': detection_result,
            'confidence': confidence
        }
        
    except Exception as e:
        print(f"[-] Error processing real PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_real_pdf())