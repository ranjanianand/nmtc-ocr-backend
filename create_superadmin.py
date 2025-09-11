#!/usr/bin/env python3
"""
Create a superadmin user to bypass org_members complexity
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_superadmin():
    """Create superadmin record for easier testing"""
    print("[*] Creating superadmin user...")
    
    admin_user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Create superadmin record
        superadmin_data = {
            "user_id": admin_user_id
        }
        
        result = supabase_service.client.table('superadmins').upsert(superadmin_data).execute()
        
        if result.data:
            print(f"[+] Superadmin created for user: {admin_user_id}")
            print(f"[+] Now admin@nmtc-test.org will login as superadmin!")
            return True
        else:
            print(f"[-] Failed to create superadmin")
            return False
        
    except Exception as e:
        print(f"[-] Error: {e}")
        return False

if __name__ == "__main__":
    success = create_superadmin()
    if success:
        print(f"\nSUCCESS! Try logging in with admin@nmtc-test.org / Test123!")
        print(f"This will bypass all org_members complexity as superadmin.")
    else:
        print(f"\nFAILED to create superadmin")