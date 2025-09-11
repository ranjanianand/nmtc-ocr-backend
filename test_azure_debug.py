#!/usr/bin/env python3
"""
Debug Azure OCR response to see why only 2 pages are processed from 7-page PDF
"""
import asyncio
import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def debug_azure_response():
    """Debug Azure OCR response structure"""
    print("[*] Debugging Azure OCR Response for AA_form.pdf")
    print("=" * 60)
    
    try:
        # Read the PDF file
        pdf_path = "pdfs/AA_form.pdf"
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        print(f"[+] PDF file size: {len(pdf_content)} bytes")
        
        # Check PDF pages using a simple method first
        pdf_header = pdf_content[:1000].decode('latin1', errors='ignore')
        print(f"[+] PDF header sample: {pdf_header[:200]}...")
        
        # Test Azure OCR
        from app.services.azure_service import azure_service
        from azure.ai.documentintelligence.models import ContentFormat
        import base64
        
        print("[*] Calling Azure Document Intelligence directly...")
        
        # Create the request manually to debug
        base64_content = base64.b64encode(pdf_content).decode('utf-8')
        
        # Use the client directly to see raw response
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
        
        analyze_request = AnalyzeDocumentRequest(base64_source=base64_content)
        
        print("[*] Starting Azure processing...")
        poller = azure_service.client.begin_analyze_document(
            model_id="prebuilt-read",
            analyze_request=analyze_request,
            output_content_format=ContentFormat.TEXT
        )
        
        print("[*] Waiting for Azure response...")
        result = poller.result()
        
        print(f"[+] Azure processing completed!")
        print(f"[+] Result type: {type(result)}")
        print(f"[+] Result attributes: {dir(result)}")
        
        # Debug the actual result structure
        if hasattr(result, 'content'):
            content_length = len(result.content) if result.content else 0
            print(f"[+] Content length: {content_length} characters")
            if result.content:
                print(f"[+] Content sample: {result.content[:200]}...")
        
        if hasattr(result, 'pages'):
            print(f"[+] Pages found: {len(result.pages) if result.pages else 0}")
            
            if result.pages:
                for i, page in enumerate(result.pages):
                    print(f"[+] Page {i+1}:")
                    print(f"    - Type: {type(page)}")
                    print(f"    - Attributes: {[attr for attr in dir(page) if not attr.startswith('_')]}")
                    
                    if hasattr(page, 'lines'):
                        lines_count = len(page.lines) if page.lines else 0
                        print(f"    - Lines: {lines_count}")
                        if page.lines and len(page.lines) > 0:
                            # Show first few lines from this page
                            for j, line in enumerate(page.lines[:3]):
                                line_content = getattr(line, 'content', 'No content')
                                print(f"      Line {j+1}: {line_content[:60]}...")
                    
                    if hasattr(page, 'words'):
                        words_count = len(page.words) if page.words else 0
                        print(f"    - Words: {words_count}")
        
        # Try to get all text manually
        all_text = ""
        if hasattr(result, 'pages') and result.pages:
            for page in result.pages:
                if hasattr(page, 'lines') and page.lines:
                    for line in page.lines:
                        if hasattr(line, 'content'):
                            all_text += line.content + "\n"
        
        print(f"\n[+] Manually extracted text length: {len(all_text)} characters")
        if all_text:
            print(f"[+] Manual text sample: {all_text[:200]}...")
        
        # Compare with result.content
        if hasattr(result, 'content') and result.content:
            print(f"[+] Azure content vs manual extraction:")
            print(f"    - Azure content: {len(result.content)} chars")
            print(f"    - Manual extraction: {len(all_text)} chars")
            print(f"    - Match: {result.content == all_text.strip()}")
        
        # Check if there's a page limit issue
        if hasattr(result, 'pages') and len(result.pages) < 7:
            print(f"\n[!] WARNING: Expected 7 pages but got {len(result.pages)}")
            print(f"[!] This might be due to:")
            print(f"    - Azure service limits")
            print(f"    - PDF structure issues")
            print(f"    - Empty pages being skipped")
            print(f"    - API model limitations")
        
        return result
        
    except Exception as e:
        print(f"[-] Error debugging Azure response: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(debug_azure_response())