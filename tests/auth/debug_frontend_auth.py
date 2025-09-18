#!/usr/bin/env python3
"""
Debug the exact queries the frontend useAuth.tsx is making
"""
import os
from dotenv import load_dotenv

load_dotenv()

def debug_frontend_auth():
    """Test the exact queries from useAuth.tsx"""
    print("[*] Testing frontend authentication queries...")
    
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    
    try:
        from app.services.supabase_service import supabase_service
        
        print(f"\n=== STEP 1: ORG MEMBERS QUERY ===")
        print(f"Query: org_members WHERE user_id = '{user_id}'")
        
        # This is what the frontend does in useAuth.tsx:612
        result = supabase_service.client.table('org_members').select('*').eq('user_id', user_id).single().execute()
        
        if result.data:
            member_data = result.data
            print(f"[+] SUCCESS: Found member data")
            print(f"    user_id: {member_data.get('user_id')}")
            print(f"    org_id: {member_data.get('org_id')}")
            print(f"    role_id: {member_data.get('role_id')}")
        else:
            print(f"[-] FAIL: No member data found")
            return False
        
        print(f"\n=== STEP 2: ORGANIZATIONS QUERY ===")
        org_id = member_data['org_id']
        print(f"Query: organizations WHERE id = '{org_id}' with status_types")
        
        # This is what the frontend does in useAuth.tsx:L136
        org_result = supabase_service.client.table('organizations').select('*, status_types(*)').eq('id', org_id).single().execute()
        
        if org_result.data:
            org_data = org_result.data
            print(f"[+] SUCCESS: Found organization")
            print(f"    id: {org_data.get('id')}")
            print(f"    name: {org_data.get('name')}")
            
            # Check status_types join
            status_types = org_data.get('status_types')
            if status_types:
                print(f"    status_types.key: {status_types.get('key')}")
                org_status = status_types.get('key')
            else:
                print(f"    status_types: NULL")
                return False
        else:
            print(f"[-] FAIL: No organization found")
            return False
        
        print(f"\n=== STEP 3: USER_ROLES QUERY ===")
        role_id = member_data['role_id']
        print(f"Query: user_roles WHERE id = '{role_id}'")
        
        # This is what the frontend does in useAuth.tsx:L156
        role_result = supabase_service.client.table('user_roles').select('*').eq('id', role_id).single().execute()
        
        if role_result.data:
            role_data = role_result.data
            print(f"[+] SUCCESS: Found role")
            print(f"    id: {role_data.get('id')}")
            print(f"    key: {role_data.get('key')}")
            print(f"    display_name: {role_data.get('display_name')}")
            print(f"    can_upload_documents: {role_data.get('can_upload_documents')}")
        else:
            print(f"[-] FAIL: No role found")
            return False
        
        print(f"\n=== STEP 4: ORGANIZATION STATUS CHECK ===")
        print(f"Status check: org_status == 'active'")
        print(f"    org_status: '{org_status}'")
        
        if org_status != 'active':
            print(f"[-] ORGANIZATION NOT ACTIVE: {org_status}")
            print(f"Frontend will show: 'Organization Inactive. Contact support'")
            return False
        else:
            print(f"[+] Organization is active")
        
        print(f"\n=== STEP 5: FINAL MEMBERSHIP OBJECT ===")
        # This is what gets created in useAuth.tsx:L190-L200
        membership = {
            'org_id': member_data['org_id'],
            'org_name': org_data['name'],
            'user_role': role_data['key'],
            'role_display_name': role_data['display_name'],
            'can_manage_users': role_data.get('can_manage_users', False),
            'can_view_billing': role_data.get('can_view_billing', False),
            'can_upload_documents': role_data.get('can_upload_documents', False),
            'can_generate_reports': role_data.get('can_generate_reports', False),
            'can_view_analytics': role_data.get('can_view_analytics', False),
        }
        
        print(f"Frontend membership object:")
        for key, value in membership.items():
            print(f"    {key}: {value}")
        
        print(f"\n=== FINAL RESULT ===")
        if org_status == 'active' and role_data.get('can_upload_documents'):
            print(f"[+] LOGIN SHOULD SUCCEED")
            print(f"[+] User has active org + upload permissions")
            return True
        else:
            print(f"[-] LOGIN WILL FAIL")
            print(f"    Active org: {org_status == 'active'}")
            print(f"    Can upload: {role_data.get('can_upload_documents')}")
            return False
        
    except Exception as e:
        print(f"[-] Error in frontend auth debug: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_frontend_auth()
    print(f"\n" + "="*60)
    if success:
        print(f"[+] Frontend authentication should work!")
        print(f"[+] Try logging in again with: admin@nmtc-test.org / Test123!")
    else:
        print(f"[-] Frontend authentication will fail")
        print(f"[-] Fix the issues above first")
    print(f"="*60)