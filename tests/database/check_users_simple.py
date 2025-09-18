#!/usr/bin/env python3
"""
Simple check for existing users
"""
import os
from dotenv import load_dotenv

load_dotenv()

def check_simple_users():
    """Check what users exist"""
    try:
        from app.services.supabase_service import supabase_service
        
        print(f"=== CHECKING ORG MEMBERS ===")
        result = supabase_service.client.table('org_members').select('*').execute()
        
        if result.data:
            print(f"Found {len(result.data)} org members")
            for member in result.data[:3]:  # Show first 3
                print(f"  user_id: {member.get('user_id')}")
                print(f"  org_id: {member.get('org_id')}")
                print(f"  role_id: {member.get('role_id')}")
                print("")
        else:
            print("No org members found")
        
        print(f"=== CHECKING FOR SPECIFIC USER ===")
        test_user = "5df566c7-149f-4e98-9b59-2e200805fe9a"
        
        user_result = supabase_service.client.table('org_members').select('*').eq('user_id', test_user).execute()
        
        if user_result.data:
            print(f"[+] Test user found: {test_user}")
            print(f"    org_id: {user_result.data[0].get('org_id')}")
            print(f"    role_id: {user_result.data[0].get('role_id')}")
        else:
            print(f"[-] Test user NOT found: {test_user}")
            
        print(f"\n=== VALID LOGIN CREDENTIALS ===")
        print(f"For Supabase Auth login, try these:")
        print(f"Email: admin@nmtc-test.org")
        print(f"Password: Test123!")
        print(f"User ID: 5df566c7-149f-4e98-9b59-2e200805fe9a")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    check_simple_users()