#!/usr/bin/env python3
"""
Fix user role to admin so they can upload documents
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_user_role():
    """Update user role to admin"""
    print("[*] Fixing user role to admin...")
    
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"  # admin user
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Find admin role ID
        print(f"[*] Finding admin role...")
        admin_role_result = supabase_service.client.table('user_roles').select('*').eq('key', 'admin').execute()
        
        if admin_role_result.data:
            admin_role_id = admin_role_result.data[0]['id']
            print(f"[+] Found admin role: {admin_role_id}")
            print(f"    - Can upload: {admin_role_result.data[0]['can_upload_documents']}")
        else:
            print(f"[-] Admin role not found")
            return False
        
        # Update org_member role
        print(f"[*] Updating user role to admin...")
        update_result = supabase_service.client.table('org_members').update({
            'role_id': admin_role_id,
            'role': 'admin'
        }).eq('user_id', user_id).execute()
        
        if update_result.data:
            print(f"[+] User role updated to admin!")
        else:
            print(f"[-] Failed to update user role")
            return False
        
        # Verify the change
        print(f"[*] Verifying the change...")
        verify_result = supabase_service.client.table('org_members').select('''
            *,
            user_roles(key, display_name, can_upload_documents)
        ''').eq('user_id', user_id).execute()
        
        if verify_result.data:
            member = verify_result.data[0]
            print(f"[+] Updated user role:")
            print(f"    - Role: {member['user_roles']['display_name']}")
            print(f"    - Can upload: {member['user_roles']['can_upload_documents']}")
            
            if member['user_roles']['can_upload_documents']:
                print(f"[+] SUCCESS! User can now upload documents!")
                return True
            else:
                print(f"[-] Still can't upload documents")
                return False
        else:
            print(f"[-] Verification failed")
            return False
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = fix_user_role()
    if success:
        print(f"\nSUCCESS! Try logging in with:")
        print(f"Email: admin@nmtc-test.org")
        print(f"Password: Test123!")
        print(f"You should now have admin access with upload permissions!")
    else:
        print(f"\nFAILED to fix user role")