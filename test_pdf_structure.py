#!/usr/bin/env python3
"""
Analyze PDF structure to understand why only 2 of 7 pages are being processed
"""
import os

def analyze_pdf_structure():
    """Analyze the PDF file structure"""
    print("[*] Analyzing PDF Structure: AA_form.pdf")
    print("=" * 60)
    
    try:
        pdf_path = "pdfs/AA_form.pdf"
        
        # Try using PyPDF2 to analyze the structure
        try:
            from PyPDF2 import PdfReader
            
            print("[*] Using PyPDF2 to analyze PDF structure...")
            
            with open(pdf_path, 'rb') as f:
                reader = PdfReader(f)
                
                print(f"[+] PyPDF2 Analysis:")
                print(f"    - Total pages: {len(reader.pages)}")
                print(f"    - PDF version: {reader.pdf_header}")
                
                if hasattr(reader, 'metadata') and reader.metadata:
                    print(f"    - Metadata: {dict(reader.metadata)}")
                
                # Analyze each page
                for i, page in enumerate(reader.pages):
                    print(f"\n[+] Page {i+1} Analysis:")
                    
                    try:
                        # Extract text from this page
                        text = page.extract_text()
                        text_length = len(text.strip()) if text else 0
                        print(f"    - Text length: {text_length} characters")
                        
                        if text_length > 0:
                            # Show first 100 chars
                            sample = text.strip()[:100].replace('\n', ' ')
                            print(f"    - Text sample: {sample}...")
                        else:
                            print(f"    - No extractable text (might be image-only)")
                        
                        # Check if page has images
                        if hasattr(page, 'images') and page.images:
                            print(f"    - Images: {len(page.images)}")
                        
                        # Check page resources
                        if hasattr(page, '/Resources'):
                            resources = page['/Resources']
                            if '/XObject' in resources:
                                xobjects = resources['/XObject']
                                print(f"    - XObjects (images/forms): {len(xobjects)}")
                                
                    except Exception as e:
                        print(f"    - Error analyzing page: {e}")
                        
        except ImportError:
            print("[-] PyPDF2 not available, trying basic analysis...")
            
        except Exception as e:
            print(f"[-] PyPDF2 analysis failed: {e}")
        
        # Basic file analysis
        print(f"\n[*] Basic File Analysis:")
        with open(pdf_path, 'rb') as f:
            content = f.read()
            
        print(f"[+] File size: {len(content)} bytes")
        
        # Look for page references in PDF
        content_str = content.decode('latin1', errors='ignore')
        
        # Count /Page references
        page_refs = content_str.count('/Type/Page')
        print(f"[+] /Type/Page references: {page_refs}")
        
        # Look for /Count in Pages object
        if '/Type/Pages/Count' in content_str:
            import re
            count_match = re.search(r'/Type/Pages/Count\s+(\d+)', content_str)
            if count_match:
                declared_pages = int(count_match.group(1))
                print(f"[+] Declared page count: {declared_pages}")
        
        # Look for common page indicators
        page_indicators = [
            '/Page',
            'endobj',
            '/Contents',
            '/MediaBox',
            '/Resources'
        ]
        
        for indicator in page_indicators:
            count = content_str.count(indicator)
            print(f"[+] '{indicator}' occurrences: {count}")
            
        # Look for text patterns that might indicate why pages are being skipped
        print(f"\n[*] Looking for potential issues:")
        
        if content_str.count('/Type/Page') < 7:
            print(f"[!] Only {content_str.count('/Type/Page')} page objects found (expected 7)")
            print(f"[!] Some pages might be missing or corrupted")
        
        if 'scanned' in content_str.lower() or 'image' in content_str.lower():
            print(f"[!] PDF might contain scanned images instead of text")
        
        if content_str.count('/XObject') > 10:
            print(f"[!] Many XObjects ({content_str.count('/XObject')}) - might be image-heavy PDF")
            
    except Exception as e:
        print(f"[-] Error analyzing PDF structure: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_pdf_structure()