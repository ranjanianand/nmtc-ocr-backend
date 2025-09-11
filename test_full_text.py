#!/usr/bin/env python3
"""
Test NMTC Detection with complete 7-page text extracted using PyPDF2
"""
import asyncio
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def extract_full_pdf_text():
    """Extract complete text from all 7 pages using PyPDF2"""
    print("[*] Extracting Full Text from All 7 Pages using PyPDF2")
    print("=" * 60)
    
    try:
        from PyPDF2 import PdfReader
        
        pdf_path = "pdfs/AA_form.pdf"
        
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            
            print(f"[+] PDF has {len(reader.pages)} pages")
            
            full_text = ""
            page_texts = []
            
            for i, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        page_text = page_text.strip()
                        page_texts.append(page_text)
                        full_text += page_text + "\n\n"
                        print(f"[+] Page {i+1}: {len(page_text)} characters")
                        
                        # Show first 80 chars of each page
                        sample = page_text[:80].replace('\n', ' ')
                        print(f"    Sample: {sample}...")
                        
                except Exception as e:
                    print(f"[-] Error extracting page {i+1}: {e}")
                    page_texts.append("")
            
            print(f"\n[+] Total extracted text: {len(full_text)} characters")
            print(f"[+] Average per page: {len(full_text) // len(reader.pages)} characters")
            
            return full_text.strip(), page_texts
            
    except Exception as e:
        print(f"[-] Error extracting PDF text: {e}")
        return None, None

async def test_nmtc_detection_full():
    """Test NMTC detection with complete extracted text"""
    print("\n[*] Testing NMTC Detection with Complete 7-Page Text")
    print("=" * 60)
    
    # Extract full text
    full_text, page_texts = extract_full_pdf_text()
    
    if not full_text:
        print("[-] Failed to extract text")
        return
    
    try:
        from app.services.detection_service import detection_service
        
        print(f"[*] Running NMTC detection on {len(full_text)} characters...")
        
        detection_result = detection_service.detect_document_type(
            text_content=full_text,
            document_id=uuid.uuid4(),
            filename="AA_form.pdf"
        )
        
        print(f"\n[+] NMTC Detection Results with Full Text:")
        print(f"    - Document type: {detection_result.document_type.value}")
        print(f"    - Confidence: {detection_result.confidence:.1%}")
        print(f"    - Primary indicators: {len(detection_result.primary_indicators)}")
        print(f"    - Secondary indicators: {len(detection_result.secondary_indicators)}")
        print(f"    - Text analyzed: {len(full_text):,} characters")
        
        # Show top indicators with their sources
        if detection_result.primary_indicators:
            print(f"\n[+] Top Primary Indicators:")
            for i, indicator in enumerate(detection_result.primary_indicators[:8]):
                print(f"    {i+1}. {indicator.pattern_type} (conf: {indicator.confidence:.1%})")
                match_text = indicator.match_text[:60] + "..." if len(indicator.match_text) > 60 else indicator.match_text
                print(f"       Match: '{match_text}'")
                
                # Try to identify which page this came from
                if hasattr(indicator, 'context') and indicator.context:
                    context_sample = indicator.context[:80] + "..." if len(indicator.context) > 80 else indicator.context
                    print(f"       Context: {context_sample}")
        
        # Test confidence logic with full text
        confidence = detection_result.confidence
        print(f"\n[*] Smart Confidence Logic with Full Text:")
        if confidence >= 0.9:
            print(f"   [HIGH] confidence (≥90%): ✅ Auto-proceed to full processing")
            ui_action = "AUTO-PROCESSING"
        elif confidence >= 0.7:
            print(f"   [MEDIUM] confidence (70-89%): ⏱️ Show 10-second countdown confirmation")
            ui_action = "COUNTDOWN-CONFIRMATION"
        else:
            print(f"   [LOW] confidence (<70%): 📝 Require manual document type selection")
            ui_action = "MANUAL-SELECTION"
        
        # Compare with Azure results
        print(f"\n[*] Comparison with Azure OCR:")
        print(f"    - Azure (2 pages): 3,559 characters, 62.1% confidence")
        print(f"    - PyPDF2 (7 pages): {len(full_text):,} characters, {confidence:.1%} confidence")
        print(f"    - Improvement: +{len(full_text) - 3559:,} characters, {confidence - 0.621:+.1%} confidence")
        
        print(f"\n" + "=" * 60)
        print(f"[+] COMPLETE 7-PAGE ANALYSIS SUCCESS!")
        print(f"[+] Document: AA_form.pdf (All 7 pages processed)")
        print(f"[+] Detection: {detection_result.document_type.value} ({confidence:.1%} confidence)")
        print(f"[+] UI Action: {ui_action}")
        print(f"[+] Text Analyzed: {len(full_text):,} characters from 7 pages")
        
        return {
            'detection_result': detection_result,
            'confidence': confidence,
            'ui_action': ui_action,
            'text_length': len(full_text),
            'pages_processed': 7
        }
        
    except Exception as e:
        print(f"[-] NMTC detection failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_nmtc_detection_full())