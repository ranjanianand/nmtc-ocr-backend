#!/usr/bin/env python3
"""
Test Azure OCR with different models to process all 7 pages
"""
import asyncio
import os
import uuid
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_different_models():
    """Test different Azure models to capture all pages"""
    print("[*] Testing Different Azure Models for Full Page Processing")
    print("=" * 70)
    
    try:
        # Read the PDF file
        pdf_path = "pdfs/AA_form.pdf"
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        print(f"[+] PDF file size: {len(pdf_content)} bytes")
        
        from app.services.azure_service import azure_service
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
        
        # Test different models
        models_to_test = [
            "prebuilt-read",      # Current model - fast text extraction
            "prebuilt-layout",    # Layout analysis - might capture more pages
            "prebuilt-document",  # General document analysis
        ]
        
        results = {}
        
        for model_id in models_to_test:
            print(f"\n[*] Testing model: {model_id}")
            print("-" * 50)
            
            try:
                base64_content = base64.b64encode(pdf_content).decode('utf-8')
                analyze_request = AnalyzeDocumentRequest(base64_source=base64_content)
                
                print(f"[*] Starting {model_id} processing...")
                poller = azure_service.client.begin_analyze_document(
                    model_id=model_id,
                    analyze_request=analyze_request
                )
                
                result = poller.result()
                
                # Analyze results
                pages_count = len(result.pages) if hasattr(result, 'pages') and result.pages else 0
                content_length = len(result.content) if hasattr(result, 'content') and result.content else 0
                
                print(f"[+] {model_id} Results:")
                print(f"    - Pages processed: {pages_count}")
                print(f"    - Content length: {content_length} characters")
                
                if hasattr(result, 'content') and result.content:
                    print(f"    - Content sample: {result.content[:100]}...")
                
                # Show page breakdown
                if hasattr(result, 'pages') and result.pages:
                    total_lines = 0
                    total_words = 0
                    for i, page in enumerate(result.pages):
                        lines = len(page.lines) if hasattr(page, 'lines') and page.lines else 0
                        words = len(page.words) if hasattr(page, 'words') and page.words else 0
                        total_lines += lines
                        total_words += words
                        print(f"    - Page {i+1}: {lines} lines, {words} words")
                    
                    print(f"    - Total: {total_lines} lines, {total_words} words")
                
                results[model_id] = {
                    'pages_count': pages_count,
                    'content_length': content_length,
                    'result': result
                }
                
                # If we found a model that processes all pages, use it
                if pages_count >= 7:
                    print(f"[+] SUCCESS: {model_id} processed all {pages_count} pages!")
                    break
                elif pages_count > 2:
                    print(f"[+] IMPROVEMENT: {model_id} processed {pages_count} pages (better than prebuilt-read)")
                else:
                    print(f"[-] {model_id} only processed {pages_count} pages")
                    
            except Exception as e:
                print(f"[-] {model_id} failed: {e}")
                results[model_id] = {'error': str(e)}
        
        # Find the best model
        best_model = None
        max_pages = 0
        for model_id, result in results.items():
            if 'pages_count' in result and result['pages_count'] > max_pages:
                max_pages = result['pages_count']
                best_model = model_id
        
        print(f"\n" + "=" * 70)
        print("[+] SUMMARY:")
        for model_id, result in results.items():
            if 'error' in result:
                print(f"    - {model_id}: ERROR - {result['error']}")
            else:
                pages = result.get('pages_count', 0)
                chars = result.get('content_length', 0)
                print(f"    - {model_id}: {pages} pages, {chars} characters")
        
        if best_model:
            print(f"\n[+] BEST MODEL: {best_model} with {max_pages} pages")
            
            if max_pages >= 7:
                print("[+] Found a model that processes all pages!")
                # Test NMTC detection with the best result
                best_result = results[best_model]['result']
                if hasattr(best_result, 'content') and best_result.content:
                    await test_nmtc_with_full_text(best_result.content, max_pages)
            else:
                print(f"[!] Best model still only processes {max_pages} of 7 pages")
                print("[!] This might be a PDF structure issue or Azure service limitation")
        
        return results
        
    except Exception as e:
        print(f"[-] Error testing models: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_nmtc_with_full_text(full_text, pages_count):
    """Test NMTC detection with the full extracted text"""
    print(f"\n[*] Testing NMTC Detection with {pages_count}-page text")
    print("-" * 50)
    
    try:
        from app.services.detection_service import detection_service
        
        detection_result = detection_service.detect_document_type(
            text_content=full_text,
            document_id=uuid.uuid4(),
            filename="AA_form.pdf"
        )
        
        print(f"[+] NMTC Detection with full text:")
        print(f"    - Document type: {detection_result.document_type.value}")
        print(f"    - Confidence: {detection_result.confidence:.1%}")
        print(f"    - Primary indicators: {len(detection_result.primary_indicators)}")
        print(f"    - Text length: {len(full_text)} characters")
        
        # Show confidence level
        confidence = detection_result.confidence
        if confidence >= 0.9:
            print(f"    - Result: [HIGH] Auto-proceed to full processing")
        elif confidence >= 0.7:
            print(f"    - Result: [MEDIUM] Show countdown confirmation")
        else:
            print(f"    - Result: [LOW] Require manual selection")
            
    except Exception as e:
        print(f"[-] NMTC detection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_different_models())