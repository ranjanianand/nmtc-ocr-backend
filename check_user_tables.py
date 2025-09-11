#!/usr/bin/env python3
"""
Check what user-related tables exist in the database
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_user_tables():
    """Check available user tables and their structure"""
    print("[*] Checking user-related tables in database...")
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Tables to check from seed data
        user_tables = ['user_roles', 'profiles', 'auth.users']
        
        for table_name in user_tables:
            print(f"\n[*] Checking {table_name}...")
            try:
                # Get table schema by selecting limited records
                result = supabase_service.client.table(table_name.replace('auth.', '')).select('*').limit(1).execute()
                
                if result.data:
                    print(f"[+] {table_name} exists with columns:")
                    print(f"    {list(result.data[0].keys())}")
                    print(f"[+] Sample record: {result.data[0]}")
                else:
                    print(f"[+] {table_name} exists but is empty")
                    
            except Exception as e:
                print(f"[-] {table_name} error: {e}")
        
        # Check if we can access auth.users directly
        print(f"\n[*] Checking auth users via RPC...")
        try:
            # Try to call a function that might list auth users
            result = supabase_service.client.rpc('get_auth_users').execute()
            print(f"[+] Auth users accessible via RPC")
        except Exception as e:
            print(f"[-] Auth users RPC error: {e}")
        
        return True
        
    except Exception as e:
        print(f"[-] Error: {e}")
        return False

if __name__ == "__main__":
    check_user_tables()