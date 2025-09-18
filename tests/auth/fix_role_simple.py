#!/usr/bin/env python3
"""
Fix user role by only updating role_id
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_role_simple():
    """Update only the role_id to admin"""
    print("[*] Fixing user role to admin (role_id only)...")
    
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"  # admin user
    admin_role_id = "53d48133-459b-488f-913d-24e44fbd7bc6"  # Admin role from previous query
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Update only role_id
        print(f"[*] Updating role_id to admin...")
        update_result = supabase_service.client.table('org_members').update({
            'role_id': admin_role_id
        }).eq('user_id', user_id).execute()
        
        if update_result.data:
            print(f"[+] Role updated successfully!")
        else:
            print(f"[-] Failed to update role")
            return False
        
        # Verify
        print(f"[*] Verifying...")
        verify_result = supabase_service.client.table('org_members').select('''
            *,
            user_roles(key, display_name, can_upload_documents, can_manage_users, can_view_billing, can_generate_reports, can_view_analytics)
        ''').eq('user_id', user_id).execute()
        
        if verify_result.data:
            member = verify_result.data[0]
            role = member['user_roles']
            print(f"[+] Updated user permissions:")
            print(f"    - Role: {role['display_name']}")
            print(f"    - Can upload: {role['can_upload_documents']}")
            print(f"    - Can manage users: {role['can_manage_users']}")
            print(f"    - Can view billing: {role['can_view_billing']}")
            
            return role['can_upload_documents']
        else:
            print(f"[-] Verification failed")
            return False
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_role_simple()
    if success:
        print(f"\n SUCCESS! Now try logging in:")
        print(f"Email: admin@nmtc-test.org")
        print(f"Password: Test123!")
        print(f"You should now have upload permissions!")
    else:
        print(f"\n FAILED to fix role")