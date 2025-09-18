#!/usr/bin/env python3
"""
Create fresh Supabase Auth user with known password
"""
import os
from dotenv import load_dotenv

load_dotenv()

def create_fresh_user():
    """Create or update auth user for testing"""
    print("[*] Creating fresh Supabase Auth user for testing...")
    
    # Known working user ID from org_members table
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    email = "admin@nmtc-test.org"
    password = "Test123!"
    
    try:
        from app.services.supabase_service import supabase_service
        
        print(f"[*] Creating/updating auth user:")
        print(f"    Email: {email}")
        print(f"    Password: {password}")
        print(f"    User ID: {user_id}")
        
        # Try to create the user (will fail if exists, but that's ok)
        try:
            auth_response = supabase_service.client.auth.admin.create_user({
                "id": user_id,
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": "NMTC Test Admin",
                    "role": "admin"
                }
            })
            
            if auth_response.user:
                print(f"[+] Auth user created successfully: {auth_response.user.id}")
            else:
                print(f"[-] Auth user creation failed")
                
        except Exception as create_error:
            print(f"[!] User might already exist, trying to update password...")
            
            # Try to update the existing user's password
            try:
                update_response = supabase_service.client.auth.admin.update_user_by_id(
                    user_id,
                    {
                        "password": password,
                        "email_confirm": True
                    }
                )
                
                if update_response.user:
                    print(f"[+] User password updated successfully: {update_response.user.id}")
                else:
                    print(f"[-] User password update failed")
                    
            except Exception as update_error:
                print(f"[-] Password update error: {update_error}")
        
        print(f"\n=== READY FOR LOGIN ===")
        print(f"Frontend URL: http://localhost:8080")
        print(f"Login Email: {email}")
        print(f"Login Password: {password}")
        print(f"Expected User ID: {user_id}")
        
        return True
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_fresh_user()
    if success:
        print(f"\n✅ Auth user setup complete!")
        print(f"Try logging in to http://localhost:8080")
    else:
        print(f"\n❌ Auth user setup failed!")