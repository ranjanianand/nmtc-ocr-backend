#!/usr/bin/env python3
"""
Check Supabase database directly for all org members and their details
"""
import os
from dotenv import load_dotenv

load_dotenv()

def check_supabase_users():
    """Check all users in Supabase database"""
    print("[*] Checking Supabase database for all org members...")
    
    try:
        from app.services.supabase_service import supabase_service
        
        print(f"\n=== ALL ORG MEMBERS IN DATABASE ===")
        
        # Get all org members with their organization and role details
        result = supabase_service.client.table('org_members').select('''
            user_id,
            org_id,
            role_id,
            organizations(name, status_types(key)),
            user_roles(key, display_name, can_upload_documents)
        ''').execute()
        
        if result.data:
            print(f"Found {len(result.data)} org members:")
            
            # Group by organization
            orgs = {}
            for member in result.data:
                org_name = member['organizations']['name']
                if org_name not in orgs:
                    orgs[org_name] = []
                orgs[org_name].append(member)
            
            for org_name, members in orgs.items():
                org_status = members[0]['organizations']['status_types']['key']
                print(f"\n{org_name} (status: {org_status}) — {len(members)} members:")
                
                for member in members:
                    role = member['user_roles']
                    print(f"  - user_id: {member['user_id']}")
                    print(f"    role: {role['display_name']} (can_upload: {role['can_upload_documents']})")
        else:
            print("No org members found!")
        
        print(f"\n=== SPECIFIC CHECK FOR OUR TEST USER ===")
        test_user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
        
        member_check = supabase_service.client.table('org_members').select('''
            *,
            organizations(name, status_types(key)),
            user_roles(key, display_name, can_upload_documents)
        ''').eq('user_id', test_user_id).execute()
        
        if member_check.data:
            member = member_check.data[0]
            print(f"Test user {test_user_id}:")
            print(f"  - Organization: {member['organizations']['name']}")
            print(f"  - Status: {member['organizations']['status_types']['key']}")
            print(f"  - Role: {member['user_roles']['display_name']}")
            print(f"  - Can Upload: {member['user_roles']['can_upload_documents']}")
            print(f"  - Should Login: {member['organizations']['status_types']['key'] == 'active' and member['user_roles']['can_upload_documents']}")
        else:
            print(f"Test user {test_user_id} NOT FOUND in org_members!")
        
        return True
        
    except Exception as e:
        print(f"[-] Error checking Supabase: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_supabase_users()