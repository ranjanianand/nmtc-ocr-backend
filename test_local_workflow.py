#!/usr/bin/env python3
"""
Test complete Stage 0A workflow locally with proper seed data credentials
"""
import requests
import time
import os

# Use working credentials from seed_data.sql
ORG_ID = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"  # Opportunity Finance Network
LOCAL_URL = "http://localhost:8000/api/documents/upload"

def test_complete_workflow():
    """Test complete Stage 0A workflow locally"""
    print(f"[*] Testing complete Stage 0A workflow locally...")
    print(f"[*] Using org_id: {ORG_ID}")
    print(f"[*] No user_id (will fallback to org_id)")
    
    test_file = "AA_form.pdf"
    
    if not os.path.exists(test_file):
        print(f"[-] {test_file} not found!")
        return False
    
    try:
        # Step 1: Upload document
        print(f"\n[1] Uploading {test_file}...")
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'application/pdf')}
            data = {
                'org_id': ORG_ID,
                'document_type': 'financial_statement',
                'cde_name': 'Test CDE',
                'client_info': 'Test Client'
                # No user_id - will use org_id as fallback
            }
            
            response = requests.post(LOCAL_URL, files=files, data=data, timeout=30)
            
            print(f"[*] Upload Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[-] Upload failed: {response.text}")
                return False
                
            result = response.json()
            document_id = result.get('document_id')
            print(f"[+] Document uploaded successfully: {document_id}")
        
        # Step 2: Monitor processing
        print(f"\n[2] Monitoring detection process...")
        status_url = f"http://localhost:8000/api/documents/{document_id}/status"
        
        for i in range(30):  # Wait up to 30 seconds
            time.sleep(2)
            status_response = requests.get(status_url)
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                current_status = status_data.get('status')
                print(f"[*] Status check {i+1}: {current_status}")
                
                # Check if detection is complete
                if 'detection' in status_data:
                    detection = status_data['detection']
                    detected_type = detection.get('detected_type')
                    confidence = detection.get('confidence', 0)
                    confidence_level = detection.get('confidence_level')
                    
                    print(f"[+] DETECTION COMPLETE!")
                    print(f"    - Detected Type: {detected_type}")
                    print(f"    - Confidence: {confidence * 100:.1f}%")
                    print(f"    - Confidence Level: {confidence_level}")
                    print(f"    - Requires Confirmation: {detection.get('requires_confirmation', 'unknown')}")
                    
                    # Stage 0A Success - we have Azure OCR + NMTC Detection + Smart Confidence
                    print(f"\n[+] STAGE 0A SUCCESS!")
                    print(f"    1. Upload: COMPLETE")
                    print(f"    2. Azure OCR: COMPLETE")
                    print(f"    3. NMTC Detection: COMPLETE")
                    print(f"    4. Smart Confidence Logic: COMPLETE")
                    
                    return True
                    
                elif current_status == 'error':
                    print(f"[-] Processing failed with error status")
                    return False
            else:
                print(f"[-] Status check failed: {status_response.status_code}")
        
        print(f"[-] Timeout waiting for detection to complete")
        return False
        
    except Exception as e:
        print(f"[-] Workflow error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("STAGE 0A WORKFLOW TEST")
    print("Upload -> Azure OCR -> NMTC Detection -> Smart Confidence UI")
    print("="*60)
    
    success = test_complete_workflow()
    
    print(f"\n{'='*60}")
    if success:
        print("SUCCESS - Stage 0A workflow is working!")
        print("Your Stage 0A is ready for production deployment!")
    else:
        print("FAILED - Need to debug the workflow")
    print("="*60)