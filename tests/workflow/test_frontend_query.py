#!/usr/bin/env python3
"""
Test the exact frontend query to understand the login issue
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_frontend_query():
    """Test the frontend organization user query exactly as written"""
    print("[*] Testing frontend login query...")
    
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"  # admin user
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Test the exact query from useAuth.tsx line 104-127
        print(f"[*] Testing useAuth.tsx query...")
        
        result = supabase_service.client.table('org_members').select('''
          org_id,
          organizations!inner (
            id,
            name,
            status_types!inner (
              key
            )
          ),
          user_roles!inner (
            key,
            display_name,
            can_manage_users,
            can_view_billing,
            can_upload_documents,
            can_generate_reports,
            can_view_analytics
          )
        ''').eq('user_id', user_id).execute()
        
        print(f"[+] Query executed successfully!")
        print(f"[+] Found {len(result.data)} records")
        
        for record in result.data:
            org = record['organizations']
            role = record['user_roles']
            status = org['status_types']['key']
            
            print(f"    - User ID: {user_id}")
            print(f"    - Org: {org['name']}")
            print(f"    - Status: {status}")
            print(f"    - Role: {role['display_name']}")
            print(f"    - Can upload: {role['can_upload_documents']}")
            
            if status != 'active':
                print(f"    [!] This org is '{status}', not 'active' - will be filtered out")
            else:
                print(f"    [+] This org is active - will be accepted")
        
        # Test with single() to simulate the frontend exactly
        print(f"\n[*] Testing with .single() to match frontend...")
        try:
            single_result = supabase_service.client.table('org_members').select('''
              org_id,
              organizations!inner (
                id,
                name,
                status_types!inner (
                  key
                )
              ),
              user_roles!inner (
                key,
                display_name,
                can_manage_users,
                can_view_billing,
                can_upload_documents,
                can_generate_reports,
                can_view_analytics
              )
            ''').eq('user_id', user_id).single()
            
            data = single_result.execute()
            if data.data:
                org = data.data['organizations']
                role = data.data['user_roles']
                status = org['status_types']['key']
                
                print(f"[+] Single query SUCCESS!")
                print(f"    - Org status: {status}")
                print(f"    - Will pass frontend filter: {status == 'active'}")
                
                return status == 'active'
            else:
                print(f"[-] Single query returned no data")
                return False
                
        except Exception as e:
            print(f"[-] Single query error: {e}")
            return False
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_frontend_query()
    if success:
        print(f"\n✅ Frontend query should work!")
        print(f"Try admin@nmtc-test.org / Test123!")
    else:
        print(f"\n❌ Frontend query has issues")