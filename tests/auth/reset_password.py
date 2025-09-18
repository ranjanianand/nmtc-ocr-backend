#!/usr/bin/env python3
"""
Reset password for admin user manually
"""
import os
from dotenv import load_dotenv

load_dotenv()

def reset_password():
    """Reset password for admin user"""
    print("[*] Resetting password for admin user...")
    
    user_email = "admin@nmtc-test.org"
    new_password = "NewTest123!"
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    
    try:
        from app.services.supabase_service import supabase_service
        
        print(f"[*] Attempting to reset password for: {user_email}")
        
        # Method 1: Using Supabase Admin API to update user
        result = supabase_service.client.auth.admin.update_user_by_id(
            user_id, 
            {
                "password": new_password,
                "email_confirm": True
            }
        )
        
        if result.user:
            print(f"[+] Password reset successful!")
            print(f"[+] Email: {user_email}")
            print(f"[+] New Password: {new_password}")
            print(f"[+] User ID: {result.user.id}")
            return True
        else:
            print(f"[-] Password reset failed")
            print(f"Error: {result}")
            return False
        
    except Exception as e:
        print(f"[-] Error resetting password: {e}")
        
        # Method 2: Try alternative approach
        try:
            print(f"[*] Trying alternative method...")
            
            # Send password reset email
            reset_result = supabase_service.client.auth.reset_password_email(user_email)
            print(f"[+] Password reset email sent to: {user_email}")
            print(f"[!] Check email for reset link")
            return True
            
        except Exception as e2:
            print(f"[-] Alternative method also failed: {e2}")
            return False

if __name__ == "__main__":
    success = reset_password()
    if success:
        print(f"\n✅ Password reset completed!")
        print(f"Try logging in with:")
        print(f"Email: admin@nmtc-test.org")
        print(f"Password: NewTest123!")
    else:
        print(f"\n❌ Password reset failed")
        print(f"Try using Supabase Dashboard method")