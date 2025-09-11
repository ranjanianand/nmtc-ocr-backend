#!/usr/bin/env python3
"""
Verify the exact ID mapping logic: auth.users.id → org_members.user_id → organizations
"""
import os
from dotenv import load_dotenv

load_dotenv()

def verify_id_mapping():
    """Verify ID mapping chain works correctly"""
    print("[*] Verifying ID mapping logic...")
    
    # This is what we get from session.user.id after login
    session_user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    
    try:
        from app.services.supabase_service import supabase_service
        
        print(f"\n=== ID MAPPING VERIFICATION ===")
        print(f"session.user.id: {session_user_id}")
        
        print(f"\n=== STEP 1: Query org_members by user_id ===")
        print(f"Query: org_members WHERE user_id = '{session_user_id}'")
        
        member_result = supabase_service.client.table('org_members').select('*').eq('user_id', session_user_id).execute()
        
        if member_result.data:
            member = member_result.data[0]
            print(f"[+] FOUND org_members record:")
            print(f"    - org_members.id (PK): {member['id']} ← Row primary key")
            print(f"    - org_members.user_id: {member['user_id']} ← Should match session.user.id")  
            print(f"    - org_members.org_id: {member['org_id']} ← Links to organizations")
            print(f"    - org_members.role_id: {member['role_id']} ← Links to user_roles")
            
            # Verify the critical mapping
            mapping_correct = member['user_id'] == session_user_id
            print(f"\n[*] Critical Check: auth.users.id == org_members.user_id")
            print(f"    - session.user.id: {session_user_id}")
            print(f"    - org_members.user_id: {member['user_id']}")
            print(f"    - Match: {mapping_correct} {'✓' if mapping_correct else '✗'}")
            
            if not mapping_correct:
                print(f"[!] CRITICAL ERROR: ID mapping is broken!")
                return False
                
        else:
            print(f"[-] NOT FOUND: No org_members record for user_id: {session_user_id}")
            print(f"[!] This means the user exists in auth.users but not linked in org_members")
            return False
        
        print(f"\n=== STEP 2: Join to organizations via org_id ===")
        print(f"Query: organizations WHERE id = '{member['org_id']}'")
        
        org_result = supabase_service.client.table('organizations').select('*, status_types(*)').eq('id', member['org_id']).execute()
        
        if org_result.data:
            org = org_result.data[0]
            print(f"[+] FOUND organization:")
            print(f"    - organizations.id: {org['id']}")
            print(f"    - organizations.name: {org['name']}")
            print(f"    - status_types.key: {org['status_types']['key']}")
        else:
            print(f"[-] NOT FOUND: No organization for org_id: {member['org_id']}")
            return False
        
        print(f"\n=== STEP 3: Join to user_roles via role_id ===")
        print(f"Query: user_roles WHERE id = '{member['role_id']}'")
        
        role_result = supabase_service.client.table('user_roles').select('*').eq('id', member['role_id']).execute()
        
        if role_result.data:
            role = role_result.data[0]
            print(f"[+] FOUND user_roles:")
            print(f"    - user_roles.id: {role['id']}")
            print(f"    - user_roles.key: {role['key']}")
            print(f"    - user_roles.display_name: {role['display_name']}")
            print(f"    - can_upload_documents: {role['can_upload_documents']}")
        else:
            print(f"[-] NOT FOUND: No user_roles for role_id: {member['role_id']}")
            return False
        
        print(f"\n=== COMPLETE CHAIN VERIFICATION ===")
        print(f"[+] auth.users.id → org_members.user_id: WORKING")
        print(f"[+] org_members.org_id → organizations.id: WORKING")
        print(f"[+] org_members.role_id → user_roles.id: WORKING")
        print(f"[+] Organization status: {org['status_types']['key']}")
        print(f"[+] Upload permission: {role['can_upload_documents']}")
        
        # Final validation
        chain_working = (
            mapping_correct and 
            org['status_types']['key'] == 'active' and
            role['can_upload_documents'] == True
        )
        
        print(f"\n=== FINAL RESULT ===")
        print(f"ID Chain Working: {chain_working}")
        print(f"Should Allow Login: {chain_working}")
        
        return chain_working
        
    except Exception as e:
        print(f"[-] Error in ID mapping: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_id_mapping()
    if success:
        print(f"\n[+] ID MAPPING IS PERFECT!")
        print(f"[!] The logic: auth.users.id → org_members.user_id → organizations works!")
        print(f"[!] Frontend authentication should work with this chain!")
    else:
        print(f"\n[-] ID MAPPING HAS ISSUES!")
        print(f"[!] Need to fix the database relationships!")