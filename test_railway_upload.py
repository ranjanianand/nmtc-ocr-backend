#!/usr/bin/env python3
"""
FINAL SOLUTION: Test Railway upload with proper seed data credentials
"""
import requests
import os

# Working credentials from seed_data.sql
ORG_ID = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"  # Opportunity Finance Network
# No user_id needed - will fallback to org_id

# Railway endpoint
RAILWAY_URL = "https://nmtc-backend-production.up.railway.app/api/documents/upload"

def test_railway_upload():
    """Test upload with working seed data credentials"""
    print(f"[*] Testing Railway upload...")
    print(f"[*] Using org_id: {ORG_ID}")
    print(f"[*] No user_id (will use org_id as fallback)")
    
    # Test with the working AA_form.pdf
    test_file = "AA_form.pdf"
    
    if not os.path.exists(test_file):
        print(f"[-] {test_file} not found!")
        return False
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'application/pdf')}
            data = {
                'org_id': ORG_ID,
                'document_type': 'financial_statement',
                'cde_name': 'Test CDE',
                'client_info': 'Test Client'
                # NO user_id - let it fallback to org_id
            }
            
            print(f"[*] Uploading {test_file}...")
            response = requests.post(RAILWAY_URL, files=files, data=data, timeout=30)
            
            print(f"[*] Response Status: {response.status_code}")
            print(f"[*] Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                document_id = result.get('document_id')
                print(f"[+] ✅ SUCCESS! Document uploaded: {document_id}")
                
                # Test status check
                status_url = f"https://nmtc-backend-production.up.railway.app/api/documents/{document_id}/status"
                status_response = requests.get(status_url)
                print(f"[*] Status check: {status_response.status_code}")
                print(f"[*] Status: {status_response.text}")
                
                return True
            else:
                print(f"[-] ❌ Upload failed: {response.text}")
                return False
                
    except Exception as e:
        print(f"[-] Upload error: {e}")
        return False

if __name__ == "__main__":
    success = test_railway_upload()
    print(f"\n{' SUCCESS - Upload working!' if success else ' FAILED - Need to debug'}")