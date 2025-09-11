#!/usr/bin/env python3
"""
Find existing users in Railway database
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def find_existing_users():
    """Check for existing users we can use for testing"""
    print("[*] Looking for existing users in Railway database...")
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Check what user-related tables exist
        tables_to_check = ['users', 'user_roles', 'profiles', 'auth.users']
        
        for table_name in tables_to_check:
            print(f"\n[*] Checking {table_name} table...")
            try:
                result = supabase_service.client.table(table_name).select('*').limit(3).execute()
                if result.data:
                    print(f"[+] Found {len(result.data)} records in {table_name}")
                    for user in result.data:
                        print(f"    - ID: {user.get('id', 'No ID')}")
                        print(f"      Keys: {list(user.keys())}")
                else:
                    print(f"[!] {table_name} table is empty")
            except Exception as e:
                print(f"[-] {table_name} error: {e}")
        
        # Try to just upload without user_id (make it optional)
        print(f"\n[*] Let's try upload without user_id requirement...")
        return True
        
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        return False

if __name__ == "__main__":
    find_existing_users()