#!/usr/bin/env python3
"""
Verify LiftFund organization and user data in Railway database
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def verify_liftfund_data():
    """Check if LiftFund org and user exist in Railway database"""
    print("[*] Verifying LiftFund organization and user data...")
    
    org_id = "12f559b7-9bcf-4b80-baf5-b7135aade230"
    email = "portfolio@liftfund.com"
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Check if LiftFund organization exists
        print(f"\n[*] Checking organization: {org_id}")
        try:
            result = supabase_service.client.table('organizations').select('*').eq('id', org_id).execute()
            if result.data:
                org = result.data[0]
                print(f"[+] ✅ LiftFund organization found!")
                print(f"    - ID: {org['id']}")
                print(f"    - Name: {org.get('name', 'No name')}")
                print(f"    - Status: {org.get('status_id', 'No status')}")
                print(f"    - Industry: {org.get('industry_type_id', 'No industry')}")
                org_exists = True
            else:
                print(f"[-] ❌ LiftFund organization NOT found!")
                org_exists = False
        except Exception as e:
            print(f"[-] Error checking organization: {e}")
            org_exists = False
        
        # Check for user with that email - try different user tables
        user_tables = ['users', 'user_roles', 'profiles']
        user_found = False
        user_id = None
        
        for table_name in user_tables:
            print(f"\n[*] Checking {table_name} for: {email}")
            try:
                result = supabase_service.client.table(table_name).select('*').eq('email', email).execute()
                if result.data:
                    user = result.data[0]
                    print(f"[+] ✅ User found in {table_name}!")
                    print(f"    - ID: {user.get('id', 'No ID')}")
                    print(f"    - Email: {user.get('email', 'No email')}")
                    print(f"    - Org ID: {user.get('org_id', 'No org_id')}")
                    print(f"    - All fields: {list(user.keys())}")
                    user_found = True
                    user_id = user.get('id')
                    break
                else:
                    print(f"[-] No user found in {table_name}")
            except Exception as e:
                print(f"[-] Error checking {table_name}: {e}")
        
        # Also check if we can find any user associated with LiftFund org
        if not user_found and org_exists:
            print(f"\n[*] Looking for ANY users in LiftFund organization...")
            for table_name in user_tables:
                try:
                    result = supabase_service.client.table(table_name).select('*').eq('org_id', org_id).execute()
                    if result.data:
                        print(f"[+] Found {len(result.data)} users in LiftFund from {table_name}:")
                        for user in result.data[:3]:  # Show first 3
                            print(f"    - {user.get('id', 'No ID')}: {user.get('email', 'No email')}")
                        user_found = True
                        user_id = result.data[0].get('id')
                        break
                except Exception as e:
                    continue
        
        # Final recommendation
        print(f"\n" + "="*60)
        if org_exists and user_found:
            print(f"[+] ✅ PERFECT! Both LiftFund org and user exist")
            print(f"[+] ✅ You can use:")
            print(f"    - org_id: {org_id}")
            print(f"    - user_id: {user_id}")
            print(f"[+] ✅ Ready for Railway testing!")
            return True
        elif org_exists:
            print(f"[+] ✅ LiftFund organization exists")
            print(f"[-] ❌ User {email} not found")
            print(f"[!] Use any user_id from LiftFund organization above")
            return False
        else:
            print(f"[-] ❌ LiftFund organization not found")
            print(f"[!] Need to use a different org_id from earlier check")
            return False
        
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = verify_liftfund_data()
    print(f"\nResult: {'✅ Ready for testing' if success else '❌ Need different credentials'}")