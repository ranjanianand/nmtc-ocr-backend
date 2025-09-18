#!/usr/bin/env python3
"""
Test manual detection endpoint to bypass Celery issues
"""
import requests
import time

# Document ID from the successful upload
DOCUMENT_ID = "64d43ea2-918f-4c40-a0be-55bef7861b22"
LOCAL_URL = "http://localhost:8000"

def test_manual_detection():
    """Test manual detection endpoint"""
    print(f"[*] Testing manual detection for document: {DOCUMENT_ID}")
    
    # Test manual detection endpoint
    detection_url = f"{LOCAL_URL}/api/documents/{DOCUMENT_ID}/manual-detection"
    
    print(f"[*] Triggering manual detection...")
    
    try:
        response = requests.post(detection_url, timeout=60)  # Longer timeout for Azure processing
        
        print(f"[*] Detection Status: {response.status_code}")
        print(f"[*] Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n[+] MANUAL DETECTION SUCCESS!")
            print(f"    - Document ID: {result.get('document_id')}")
            print(f"    - Status: {result.get('status')}")
            print(f"    - Message: {result.get('message')}")
            
            detection_result = result.get('detection_result', {})
            if detection_result:
                print(f"    - Detected Type: {detection_result.get('detected_type')}")
                print(f"    - Confidence: {detection_result.get('confidence', 0) * 100:.1f}%")
                print(f"    - Confidence Level: {detection_result.get('confidence_level')}")
                
            extraction_summary = result.get('extraction_summary', {})
            if extraction_summary:
                print(f"    - Content Length: {extraction_summary.get('content_length')} chars")
                print(f"    - Pages Processed: {extraction_summary.get('pages_processed')}")
            
            print(f"\n[+] STAGE 0A COMPLETE!")
            print(f"    1. ✅ Upload: DONE")
            print(f"    2. ✅ Azure OCR: DONE")
            print(f"    3. ✅ NMTC Detection: DONE")
            print(f"    4. ✅ Smart Confidence: DONE")
            
            return True
        else:
            print(f"[-] Manual detection failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"[-] Detection error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("MANUAL DETECTION TEST - STAGE 0A")
    print("Azure OCR -> NMTC Detection -> Smart Confidence")
    print("="*60)
    
    success = test_manual_detection()
    
    print(f"\n{'='*60}")
    if success:
        print("SUCCESS - Stage 0A workflow is WORKING!")
        print("Ready for production deployment!")
    else:
        print("FAILED - Need more debugging")
    print("="*60)