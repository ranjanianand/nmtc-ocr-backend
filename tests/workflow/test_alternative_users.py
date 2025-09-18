#!/usr/bin/env python3
"""
Test alternative admin accounts from seed data to isolate the login issue
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_alternative_users():
    """Test different admin users from seed data"""
    print("[*] Testing alternative admin users from seed data...")
    
    # Alternative admin accounts to test
    test_users = [
        {
            "email": "admin@nmtc-test.org",
            "org": "Opportunity Finance Network",
            "org_id": "ce117b87-d75c-4c8a-b3f5-922ddec539b0"
        },
        {
            "email": "admin@ndconline.org", 
            "org": "National Development Council",
            "org_id": "07f96bfd-9641-4f58-adee-c452e50c1edf"
        },
        {
            "email": "admin@liftfund.com",
            "org": "LiftFund", 
            "org_id": "12f559b7-9bcf-4b80-baf5-b7135aade230"
        },
        {
            "email": "admin@grameenamerica.org",
            "org": "Grameen America",
            "org_id": "65dbcd62-3ec4-48ee-ba29-53037965c9c2"
        }
    ]
    
    try:
        from app.services.supabase_service import supabase_service
        
        # First, find all users in auth.users to get their IDs
        print(f"\n=== FINDING USER IDs FROM AUTH.USERS ===")
        auth_users = []
        
        for test_user in test_users:
            # We can't directly query auth.users, but we can check org_members for existing records
            member_result = supabase_service.client.table('org_members').select('*, organizations(name), user_roles(display_name, can_upload_documents)').eq('organizations.id', test_user['org_id']).execute()
            
            if member_result.data:
                for member in member_result.data:
                    if member['organizations']['name'] == test_user['org']:
                        role = member.get('user_roles', {})
                        if role.get('display_name') == 'Organization Admin':
                            print(f"[+] Found admin for {test_user['org']}:")
                            print(f"    - user_id: {member['user_id']}")
                            print(f"    - org_id: {member['org_id']}")  
                            print(f"    - can_upload: {role.get('can_upload_documents')}")
                            
                            # Test the complete frontend flow for this user
                            if test_frontend_flow(member['user_id'], test_user['email'], test_user['org']):
                                print(f"    - Frontend flow: WORKING")
                            else:
                                print(f"    - Frontend flow: BROKEN")
            
        return True
        
    except Exception as e:
        print(f"[-] Error testing alternative users: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_frontend_flow(user_id, email, org_name):
    """Test the exact frontend authentication flow for a user"""
    try:
        from app.services.supabase_service import supabase_service
        
        # Step 1: Get org member data
        member_result = supabase_service.client.table('org_members').select('*').eq('user_id', user_id).single().execute()
        if not member_result.data:
            return False
        member = member_result.data
        
        # Step 2: Get organization with status
        org_result = supabase_service.client.table('organizations').select('*, status_types(*)').eq('id', member['org_id']).single().execute()
        if not org_result.data:
            return False
        org = org_result.data
        
        # Step 3: Get role data
        role_result = supabase_service.client.table('user_roles').select('*').eq('id', member['role_id']).single().execute()
        if not role_result.data:
            return False
        role = role_result.data
        
        # Step 4: Validate
        is_active = org.get('status_types', {}).get('key') == 'active'
        can_upload = role.get('can_upload_documents', False)
        
        return is_active and can_upload
        
    except Exception as e:
        return False

if __name__ == "__main__":
    test_alternative_users()