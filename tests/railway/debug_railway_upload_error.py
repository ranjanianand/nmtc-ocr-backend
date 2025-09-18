#!/usr/bin/env python3
"""
Debug the specific 500 error on Railway upload endpoint
"""
import os
from dotenv import load_dotenv
import json

load_dotenv()

def debug_upload_error():
    """Debug what's causing the 500 error on upload"""
    print("[*] Debugging Railway 500 upload error...")
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Test 1: Check if we can connect to Supabase
        print(f"\n=== TEST 1: SUPABASE CONNECTION ===")
        try:
            result = supabase_service.client.table('organizations').select('id').limit(1).execute()
            print(f"[+] Supabase connection: WORKING")
            print(f"[+] Sample org ID: {result.data[0]['id'] if result.data else 'None'}")
        except Exception as e:
            print(f"[-] Supabase connection: FAILED - {e}")
            return
        
        # Test 2: Check user authentication context
        print(f"\n=== TEST 2: USER AUTHENTICATION ===")
        test_user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
        
        try:
            # Check if user exists in org_members
            member_result = supabase_service.client.table('org_members').select('*').eq('user_id', test_user_id).execute()
            if member_result.data:
                print(f"[+] User found in org_members: {test_user_id}")
                print(f"[+] Org ID: {member_result.data[0]['org_id']}")
                print(f"[+] Role ID: {member_result.data[0]['role_id']}")
            else:
                print(f"[-] User NOT found in org_members: {test_user_id}")
        except Exception as e:
            print(f"[-] Error checking user: {e}")
        
        # Test 3: Check documents table structure
        print(f"\n=== TEST 3: DOCUMENTS TABLE ===")
        try:
            result = supabase_service.client.table('documents').select('*').limit(1).execute()
            if result.data:
                print(f"[+] Documents table exists with columns:")
                for col in result.data[0].keys():
                    print(f"    - {col}")
            else:
                print(f"[+] Documents table exists but empty")
        except Exception as e:
            print(f"[-] Documents table error: {e}")
        
        # Test 4: Simulate upload payload
        print(f"\n=== TEST 4: SIMULATE UPLOAD ===")
        try:
            # Create test document record matching actual schema
            test_doc = {
                'org_id': member_result.data[0]['org_id'] if member_result.data else 'ce117b87-d75c-4c8a-b3f5-922ddec539b0',
                'storage_path': 'uploads/test.pdf',
                'filename': 'test.pdf',
                'mime_type': 'application/pdf',
                'uploaded_by': test_user_id,
                'ocr_status': 'processing'
            }
            
            # Try inserting test document
            result = supabase_service.client.table('documents').insert(test_doc).execute()
            
            if result.data:
                print(f"[+] Test document insert: SUCCESS")
                print(f"[+] Inserted document ID: {result.data[0]['id']}")
                
                # Clean up test record using the returned ID
                doc_id = result.data[0]['id']
                supabase_service.client.table('documents').delete().eq('id', doc_id).execute()
                print(f"[+] Cleaned up test record: {doc_id}")
            else:
                print(f"[-] Test document insert: FAILED")
                
        except Exception as e:
            print(f"[-] Document insert error: {e}")
            print(f"[!] This is likely the cause of the 500 error!")
            
        # Test 5: Check Azure credentials
        print(f"\n=== TEST 5: AZURE CREDENTIALS ===")
        azure_endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
        azure_key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
        
        print(f"[+] Azure endpoint: {'SET' if azure_endpoint else 'MISSING'}")
        print(f"[+] Azure key: {'SET' if azure_key else 'MISSING'}")
        
        if azure_endpoint and azure_key:
            print(f"[+] Azure credentials appear configured")
        else:
            print(f"[-] Missing Azure credentials - set in Railway environment variables")
        
        # Test 6: Check Celery/Redis connectivity
        print(f"\n=== TEST 6: CELERY/REDIS ===")
        redis_url = os.getenv('REDIS_URL')
        print(f"[+] Redis URL: {'SET' if redis_url else 'MISSING'}")
        
        if not redis_url:
            print(f"[-] Missing REDIS_URL - Celery tasks will fail")
        
        print(f"\n=== SUMMARY ===")
        print(f"Most likely causes of 500 error:")
        print(f"1. Foreign key constraint violation (missing org_id/user_id)")
        print(f"2. Missing environment variables (Azure/Redis)")
        print(f"3. Database schema mismatch")
        print(f"4. Authentication context not passed properly")
        
        return True
        
    except Exception as e:
        print(f"[-] Critical error in debug: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_upload_error()