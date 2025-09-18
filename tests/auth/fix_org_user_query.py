#!/usr/bin/env python3
"""
Fix the organization user query step by step
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_org_user_query():
    """Debug and fix the organization user query"""
    print("[*] Debugging organization user query...")
    
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"  # admin user
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Remove superadmin first
        print(f"[*] Removing superadmin...")
        supabase_service.client.table('superadmins').delete().eq('user_id', user_id).execute()
        print(f"[+] Superadmin removed")
        
        # Step 1: Check basic org_members query
        print(f"\n[*] Step 1: Basic org_members query...")
        basic_result = supabase_service.client.table('org_members').select('*').eq('user_id', user_id).execute()
        
        if basic_result.data:
            print(f"[+] Found org_member record:")
            member = basic_result.data[0]
            print(f"    - User ID: {member['user_id']}")
            print(f"    - Org ID: {member['org_id']}")
            print(f"    - Role ID: {member['role_id']}")
        else:
            print(f"[-] No org_member found for user")
            return False
            
        # Step 2: Check organization separately
        print(f"\n[*] Step 2: Check organization...")
        org_result = supabase_service.client.table('organizations').select('*, status_types(*)').eq('id', member['org_id']).execute()
        
        if org_result.data:
            org = org_result.data[0]
            print(f"[+] Organization found:")
            print(f"    - Name: {org['name']}")
            print(f"    - Status: {org['status_types']['key']}")
        else:
            print(f"[-] Organization not found")
            return False
            
        # Step 3: Check user role separately
        print(f"\n[*] Step 3: Check user role...")
        role_result = supabase_service.client.table('user_roles').select('*').eq('id', member['role_id']).execute()
        
        if role_result.data:
            role = role_result.data[0]
            print(f"[+] User role found:")
            print(f"    - Role: {role['display_name']}")
            print(f"    - Can upload: {role['can_upload_documents']}")
        else:
            print(f"[-] User role not found")
            return False
            
        # Step 4: Try simpler join query
        print(f"\n[*] Step 4: Simpler join query...")
        try:
            simple_join = supabase_service.client.table('org_members').select('''
                org_id,
                organizations(id, name),
                user_roles(key, display_name, can_upload_documents)
            ''').eq('user_id', user_id).execute()
            
            if simple_join.data:
                print(f"[+] Simple join works!")
                result = simple_join.data[0]
                print(f"    - Org: {result['organizations']['name']}")
                print(f"    - Role: {result['user_roles']['display_name']}")
                return True
            else:
                print(f"[-] Simple join failed")
                
        except Exception as e:
            print(f"[-] Simple join error: {e}")
            return False
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_org_user_query()
    if success:
        print(f"\n✅ Organization user query is working!")
        print(f"Try logging in with user@nmtc-test.org / Test123!")
    else:
        print(f"\n❌ Still debugging org user query")