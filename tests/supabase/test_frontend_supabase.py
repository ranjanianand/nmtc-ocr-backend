#!/usr/bin/env python3
"""
Test the exact same queries that the frontend runs to see if there are any differences
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_frontend_supabase_queries():
    """Test the exact queries the frontend runs"""
    print("[*] Testing frontend Supabase queries...")
    
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    
    try:
        from app.services.supabase_service import supabase_service
        
        print(f"\n=== FRONTEND QUERY 1: Get org member data ===")
        member_result = supabase_service.client.table('org_members').select('*').eq('user_id', user_id).single().execute()
        
        if member_result.data:
            member_data = member_result.data
            print(f"[+] Step 1 SUCCESS:")
            print(f"    - org_id: {member_data['org_id']}")
            print(f"    - role_id: {member_data['role_id']}")
        else:
            print(f"[-] Step 1 FAILED: No member data")
            print(f"    Error: {member_result}")
            return False
        
        print(f"\n=== FRONTEND QUERY 2: Get organization with status ===")
        org_result = supabase_service.client.table('organizations').select('*, status_types(*)').eq('id', member_data['org_id']).single().execute()
        
        if org_result.data:
            org_data = org_result.data
            status_key = org_data.get('status_types', {}).get('key') if org_data.get('status_types') else None
            print(f"[+] Step 2 SUCCESS:")
            print(f"    - name: {org_data['name']}")
            print(f"    - status_types: {org_data.get('status_types')}")
            print(f"    - status_key: {status_key}")
        else:
            print(f"[-] Step 2 FAILED: No organization data")
            print(f"    Error: {org_result}")
            return False
        
        print(f"\n=== FRONTEND QUERY 3: Get role data ===")
        role_result = supabase_service.client.table('user_roles').select('*').eq('id', member_data['role_id']).single().execute()
        
        if role_result.data:
            role_data = role_result.data
            print(f"[+] Step 3 SUCCESS:")
            print(f"    - key: {role_data['key']}")
            print(f"    - display_name: {role_data['display_name']}")
            print(f"    - can_upload_documents: {role_data['can_upload_documents']}")
        else:
            print(f"[-] Step 3 FAILED: No role data")
            print(f"    Error: {role_result}")
            return False
        
        print(f"\n=== FRONTEND LOGIC: Final validation ===")
        org_status_active = status_key == 'active'
        
        print(f"[*] Organization status active: {org_status_active}")
        if not org_status_active:
            print(f"[-] Frontend would REJECT due to org status: {status_key}")
            return False
        
        print(f"[+] All frontend queries would SUCCEED!")
        print(f"[+] Frontend should create this orgMembership object:")
        membership = {
            "org_id": member_data['org_id'],
            "org_name": org_data['name'],
            "user_role": role_data['key'],
            "role_display_name": role_data['display_name'],
            "can_upload_documents": role_data['can_upload_documents'],
            "can_manage_users": role_data['can_manage_users'],
            "can_view_billing": role_data['can_view_billing'],
            "can_generate_reports": role_data['can_generate_reports'],
            "can_view_analytics": role_data['can_view_analytics']
        }
        print(f"    {membership}")
        
        return True
        
    except Exception as e:
        print(f"[-] Error in frontend queries: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_frontend_supabase_queries()
    if success:
        print(f"\n[+] Frontend queries should work perfectly!")
        print(f"[!] If login still fails, the issue is in:")
        print(f"    - JavaScript error handling")
        print(f"    - Browser console errors") 
        print(f"    - Network/CORS issues")
        print(f"    - Timing/race conditions")
    else:
        print(f"\n[-] Frontend queries have issues - need to fix database/queries")