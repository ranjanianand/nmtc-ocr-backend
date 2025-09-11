#!/usr/bin/env python3
"""
Check the actual database schema on Railway
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_database_schema():
    """Check what tables and columns exist in Railway database"""
    print("[*] Checking Railway database schema...")
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Check organizations table
        print("\n[*] Checking organizations table...")
        try:
            result = supabase_service.client.table('organizations').select('*').limit(1).execute()
            print(f"[+] Organizations table exists")
            if result.data:
                print(f"[+] Sample record: {result.data[0].keys()}")
            else:
                print(f"[!] Organizations table is empty")
        except Exception as e:
            print(f"[-] Organizations table error: {e}")
        
        # Check users table
        print("\n[*] Checking users table...")
        try:
            result = supabase_service.client.table('users').select('*').limit(1).execute()
            print(f"[+] Users table exists")
            if result.data:
                print(f"[+] Sample record: {result.data[0].keys()}")
            else:
                print(f"[!] Users table is empty")
        except Exception as e:
            print(f"[-] Users table error: {e}")
            
        # Check documents table  
        print("\n[*] Checking documents table...")
        try:
            result = supabase_service.client.table('documents').select('*').limit(1).execute()
            print(f"[+] Documents table exists")
            if result.data:
                print(f"[+] Sample record: {result.data[0].keys()}")
            else:
                print(f"[!] Documents table is empty")
        except Exception as e:
            print(f"[-] Documents table error: {e}")
        
        # Try to find ANY existing organization to use
        print("\n[*] Looking for any existing organizations...")
        try:
            result = supabase_service.client.table('organizations').select('id, name').execute()
            if result.data:
                print(f"[+] Found {len(result.data)} existing organizations:")
                for org in result.data[:3]:  # Show first 3
                    print(f"    - {org['id']}: {org.get('name', 'No name')}")
                return result.data[0]['id']  # Return first org ID
            else:
                print(f"[!] No organizations exist in database")
                return None
        except Exception as e:
            print(f"[-] Error checking existing organizations: {e}")
            return None
        
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        return None

if __name__ == "__main__":
    org_id = check_database_schema()
    if org_id:
        print(f"\n[+] Use this org_id for testing: {org_id}")
    else:
        print(f"\n[-] Need to create organization data first")