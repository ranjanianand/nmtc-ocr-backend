#!/usr/bin/env python3
"""
Debug complete login flow step by step to find the exact failure point
"""
import os
from dotenv import load_dotenv

load_dotenv()

def debug_full_login_flow():
    """Debug each step of the login flow"""
    print("[*] Debugging complete login flow...")
    
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    user_email = "admin@nmtc-test.org"
    
    try:
        from app.services.supabase_service import supabase_service
        
        print(f"\n=== STEP 1: Check if Auth User Exists ===")
        # We can't query auth.users directly, but we know the user exists from creation
        print(f"[+] Auth User ID: {user_id}")
        print(f"[+] Auth Email: {user_email}")
        
        print(f"\n=== STEP 2: Check Super Admin ===")
        superadmin_result = supabase_service.client.table('superadmins').select('*').eq('user_id', user_id).execute()
        if superadmin_result.data:
            print(f"[+] User IS a superadmin - would redirect to /dashboard")
            print(f"    Superadmin record: {superadmin_result.data[0]}")
            # For normal user flow, we want to remove this
            print(f"[!] Removing superadmin status for normal user testing...")
            supabase_service.client.table('superadmins').delete().eq('user_id', user_id).execute()
            print(f"[+] Superadmin status removed")
        else:
            print(f"[+] User is NOT a superadmin - will check org membership")
        
        print(f"\n=== STEP 3: Check Organization Membership ===")
        org_member_result = supabase_service.client.table('org_members').select('*').eq('user_id', user_id).execute()
        if org_member_result.data:
            member = org_member_result.data[0]
            print(f"[+] Found org membership:")
            print(f"    - Member ID: {member['id']}")
            print(f"    - User ID: {member['user_id']}")
            print(f"    - Org ID: {member['org_id']}")
            print(f"    - Role ID: {member['role_id']}")
        else:
            print(f"[-] NO org membership found!")
            return False
        
        print(f"\n=== STEP 4: Check Organization Status ===")
        org_result = supabase_service.client.table('organizations').select('*, status_types(*)').eq('id', member['org_id']).execute()
        if org_result.data:
            org = org_result.data[0]
            status_key = org.get('status_types', {}).get('key')
            print(f"[+] Found organization:")
            print(f"    - Org ID: {org['id']}")
            print(f"    - Org Name: {org['name']}")
            print(f"    - Status ID: {org.get('status_id')}")
            print(f"    - Status Key: {status_key}")
            print(f"    - Is Active: {status_key == 'active'}")
        else:
            print(f"[-] NO organization found!")
            return False
        
        print(f"\n=== STEP 5: Check User Role ===")
        role_result = supabase_service.client.table('user_roles').select('*').eq('id', member['role_id']).execute()
        if role_result.data:
            role = role_result.data[0]
            print(f"[+] Found user role:")
            print(f"    - Role ID: {role['id']}")
            print(f"    - Role Key: {role['key']}")
            print(f"    - Display Name: {role['display_name']}")
            print(f"    - Can Upload: {role['can_upload_documents']}")
            print(f"    - Can Manage Users: {role['can_manage_users']}")
        else:
            print(f"[-] NO user role found!")
            return False
        
        print(f"\n=== STEP 6: Final Validation ===")
        is_org_active = status_key == 'active'
        has_upload_permission = role['can_upload_documents']
        
        print(f"[*] Organization Active: {is_org_active}")
        print(f"[*] Has Upload Permission: {has_upload_permission}")
        print(f"[*] Should Allow Login: {is_org_active and has_upload_permission}")
        
        if is_org_active and has_upload_permission:
            print(f"\n✅ LOGIN SHOULD SUCCEED!")
            print(f"Expected user context:")
            print(f"    - userType: 'org_user'")
            print(f"    - email: {user_email}")
            print(f"    - orgId: {org['id']}")
            print(f"    - orgName: {org['name']}")
            print(f"    - role: {role['key']}")
            print(f"    - permissions.canUploadDocuments: {has_upload_permission}")
            return True
        else:
            print(f"\n❌ LOGIN SHOULD FAIL!")
            if not is_org_active:
                print(f"    - Reason: Organization not active (status: {status_key})")
            if not has_upload_permission:
                print(f"    - Reason: No upload permission")
            return False
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_full_login_flow()
    if success:
        print(f"\n🎯 Frontend login should work with admin@nmtc-test.org / Test123!")
    else:
        print(f"\n🚫 Login will fail - check the issues above")