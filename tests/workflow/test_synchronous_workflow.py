#!/usr/bin/env python3
"""
Test the new synchronous Stage 0A workflow:
Upload PDF → Immediate Azure OCR → Immediate NMTC Detection → Store results → Return to user
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_synchronous_workflow():
    """Test the complete synchronous workflow locally"""
    print("[*] Testing Synchronous Stage 0A Workflow...")
    
    # Test configuration
    base_url = "http://localhost:8000"
    test_pdf = "AA_form.pdf"
    
    # Test organization context
    org_id = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    
    try:
        # Check if test PDF exists
        if not os.path.exists(test_pdf):
            print(f"[-] Test PDF not found: {test_pdf}")
            return False
        
        print(f"[+] Using test PDF: {test_pdf} ({os.path.getsize(test_pdf)} bytes)")
        
        # Prepare upload request
        upload_url = f"{base_url}/api/documents/upload"
        
        print(f"[*] Uploading to: {upload_url}")
        print(f"[*] Organization: {org_id}")
        print(f"[*] User: {user_id}")
        
        # Upload file with form data
        with open(test_pdf, 'rb') as f:
            files = {'file': (test_pdf, f, 'application/pdf')}
            data = {
                'org_id': org_id,
                'user_id': user_id,
                'document_type': 'allocation_agreement',
                'cde_name': 'Test CDE',
                'client_info': 'Synchronous workflow test'
            }
            
            print(f"\n=== UPLOADING FILE ===")
            response = requests.post(upload_url, files=files, data=data, timeout=120)  # 2 min timeout for processing
        
        print(f"[*] Response Status: {response.status_code}")
        print(f"[*] Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n=== UPLOAD SUCCESS ===")
            print(f"[+] Document ID: {result.get('document_id')}")
            print(f"[+] Status: {result.get('status')}")
            print(f"[+] Message: {result.get('message')}")
            
            # Check processing results
            if 'processing_results' in result:
                proc_results = result['processing_results']
                print(f"\n=== PROCESSING RESULTS ===")
                print(f"[+] Detected Type: {proc_results.get('detected_type')}")
                print(f"[+] Confidence: {proc_results.get('confidence')}%")
                print(f"[+] Confidence Level: {proc_results.get('confidence_level')}")
                print(f"[+] Page Count: {proc_results.get('page_count')}")
                print(f"[+] Character Count: {proc_results.get('character_count')}")
                print(f"[+] Requires Confirmation: {proc_results.get('requires_confirmation')}")
                print(f"[+] Auto Process Ready: {proc_results.get('auto_process_ready')}")
                
                # Evaluate Stage 0A success criteria
                print(f"\n=== STAGE 0A EVALUATION ===")
                
                success_criteria = {
                    "PDF uploaded to Supabase": result.get('status') in ['completed', 'error'],
                    "Azure OCR extracted text": proc_results.get('character_count', 0) > 0,
                    "NMTC detection completed": proc_results.get('detected_type') != 'unknown',
                    "Smart confidence logic": proc_results.get('confidence_level') in ['high', 'medium', 'low'],
                    "Results stored in database": result.get('document_id') is not None
                }
                
                all_passed = True
                for criterion, passed in success_criteria.items():
                    status = "✓ PASS" if passed else "✗ FAIL"
                    print(f"  {criterion}: {status}")
                    if not passed:
                        all_passed = False
                
                print(f"\n=== FINAL RESULT ===")
                if all_passed and result.get('status') == 'completed':
                    print(f"[+] STAGE 0A WORKFLOW: COMPLETE SUCCESS!")
                    print(f"[+] All components working: Upload -> Azure OCR -> NMTC Detection -> Smart Confidence UI")
                    return True
                else:
                    print(f"[!] STAGE 0A WORKFLOW: PARTIAL SUCCESS")
                    print(f"Some components may need attention")
                    return False
            else:
                print(f"[-] No processing results in response")
                return False
                
        else:
            print(f"[-] Upload failed: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"[-] Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"[-] Raw response: {response.text}")
            return False
    
    except requests.exceptions.Timeout:
        print(f"[-] Request timeout - processing may take longer than expected")
        return False
    except requests.exceptions.ConnectionError:
        print(f"[-] Connection error - is the backend server running?")
        return False
    except Exception as e:
        print(f"[-] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_backend_health():
    """Check if backend is running and healthy"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print(f"[+] Backend server is healthy")
            return True
        else:
            print(f"[-] Backend server health check failed: {response.status_code}")
            return False
    except:
        print(f"[-] Backend server is not responding")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("SYNCHRONOUS STAGE 0A WORKFLOW TEST")
    print("=" * 80)
    
    # Check prerequisites
    if not check_backend_health():
        print(f"\n❌ Prerequisites not met - start backend server first")
        exit(1)
    
    # Run the test
    success = test_synchronous_workflow()
    
    if success:
        print(f"\n[+] SUCCESS: Stage 0A workflow is working perfectly!")
        print(f"[+] Ready for production deployment with simplified architecture!")
    else:
        print(f"\n[-] ISSUES DETECTED: Stage 0A workflow needs attention")
        print(f"[-] Check the logs above for specific problems")
    
    print("=" * 80)