#!/usr/bin/env python3
"""
Check org_members table structure and create proper records
"""
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def check_and_create_org_members():
    """Check org_members structure and create records"""
    print("[*] Checking org_members table structure...")
    
    org_id = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"
    admin_user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    regular_user_id = "3b6b0f56-2024-4be8-9cb7-00a17273fbe5"
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Check existing org_members structure
        print(f"\n[*] Checking existing org_members...")
        result = supabase_service.client.table('org_members').select('*').limit(1).execute()
        
        if result.data:
            print(f"[+] org_members table structure:")
            print(f"    Columns: {list(result.data[0].keys())}")
            print(f"[+] Sample record: {result.data[0]}")
            
            # Get the role_id from existing record
            existing_role_id = result.data[0].get('role_id')
        else:
            print(f"[-] No existing org_members found")
            return False
        
        # Create minimal org_members records
        minimal_members = [
            {
                "user_id": admin_user_id,
                "org_id": org_id,
                "role_id": existing_role_id  # Use same role as existing member
            },
            {
                "user_id": regular_user_id,
                "org_id": org_id,
                "role_id": existing_role_id  # Use same role as existing member
            }
        ]
        
        print(f"\n[*] Creating minimal org_members records...")
        for member in minimal_members:
            try:
                result = supabase_service.client.table('org_members').upsert(member).execute()
                
                if result.data:
                    print(f"[+] Created org_member for user: {member['user_id']}")
                else:
                    print(f"[-] Failed to create org_member for user: {member['user_id']}")
                    
            except Exception as e:
                print(f"[-] Error creating org_member for {member['user_id']}: {e}")
        
        # Final verification
        print(f"\n[*] Final verification...")
        result = supabase_service.client.table('org_members').select('*').eq('org_id', org_id).execute()
        
        if result.data:
            print(f"[+] Total org_members for organization: {len(result.data)}")
            for member in result.data:
                print(f"    - User: {member['user_id']}")
                
            if len(result.data) >= 3:  # Original + 2 new
                print(f"\n[+] SUCCESS! Frontend login should work now!")
                return True
        
        return False
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_and_create_org_members()
    if success:
        print(f"\n✅ READY FOR FRONTEND LOGIN:")
        print(f"   Email: admin@nmtc-test.org")
        print(f"   Password: Test123!")
    else:
        print(f"\n❌ Still need to fix org_members setup")