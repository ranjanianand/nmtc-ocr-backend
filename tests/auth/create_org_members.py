#!/usr/bin/env python3
"""
Create organization member records for the auth users we created
"""
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def create_org_members():
    """Create org_members records for our auth users"""
    print("[*] Creating organization member records...")
    
    # Existing data
    org_id = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"  # Opportunity Finance Network
    admin_role_id = "53d48133-459b-488f-913d-24e44fbd7bc6"  # Admin role from seed data
    
    # Auth users we created
    admin_user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    regular_user_id = "3b6b0f56-2024-4be8-9cb7-00a17273fbe5"
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Create org_members records
        org_members = [
            {
                "user_id": admin_user_id,
                "org_id": org_id,
                "role_id": admin_role_id,
                "is_active": True,
                "joined_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "user_id": regular_user_id,
                "org_id": org_id,
                "role_id": admin_role_id,  # Give both admin for testing
                "is_active": True,
                "joined_at": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        
        print(f"\n[*] Creating org_members records...")
        for member in org_members:
            try:
                result = supabase_service.client.table('org_members').upsert(member).execute()
                
                if result.data:
                    print(f"[+] Created org_member for user: {member['user_id']}")
                else:
                    print(f"[-] Failed to create org_member for user: {member['user_id']}")
                    
            except Exception as e:
                print(f"[-] Error creating org_member for {member['user_id']}: {e}")
        
        # Verify the records
        print(f"\n[*] Verifying org_members records...")
        try:
            result = supabase_service.client.table('org_members').select('*').eq('org_id', org_id).execute()
            
            if result.data:
                print(f"[+] Found {len(result.data)} org_members for organization:")
                for member in result.data:
                    print(f"    - User: {member['user_id']}")
                    print(f"      Role: {member['role_id']}")
                    print(f"      Active: {member['is_active']}")
            else:
                print(f"[-] No org_members found")
                
        except Exception as e:
            print(f"[-] Error verifying org_members: {e}")
        
        print(f"\n" + "="*60)
        print(f"[+] ORG MEMBERS CREATED!")
        print(f"[+] Organization: Opportunity Finance Network")
        print(f"[+] Users can now login via frontend:")
        print(f"    - admin@nmtc-test.org / Test123!")
        print(f"    - user@nmtc-test.org / Test123!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_org_members()
    if success:
        print(f"\nSUCCESS - Organization members created! Ready for frontend login!")
    else:
        print(f"\nFAILED - Unable to create org members")