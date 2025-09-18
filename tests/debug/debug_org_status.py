#!/usr/bin/env python3
"""
Debug organization status and fix if needed
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_organization_status():
    """Check and fix organization status"""
    print("[*] Debugging organization status...")
    
    org_id = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Check organization status
        print(f"\n[*] Checking organization: {org_id}")
        result = supabase_service.client.table('organizations').select('*, status_types(key)').eq('id', org_id).execute()
        
        if result.data:
            org = result.data[0]
            print(f"[+] Organization found:")
            print(f"    - Name: {org.get('name')}")
            print(f"    - Status ID: {org.get('status_id')}")
            print(f"    - Status: {org.get('status_types', {}).get('key', 'No status')}")
            
            current_status = org.get('status_types', {}).get('key')
            if current_status != 'active':
                print(f"[!] Organization status is '{current_status}', need 'active'")
                
                # Find active status ID
                status_result = supabase_service.client.table('status_types').select('*').eq('key', 'active').execute()
                if status_result.data:
                    active_status_id = status_result.data[0]['id']
                    print(f"[*] Found active status ID: {active_status_id}")
                    
                    # Update organization to active
                    update_result = supabase_service.client.table('organizations').update({
                        'status_id': active_status_id
                    }).eq('id', org_id).execute()
                    
                    if update_result.data:
                        print(f"[+] Updated organization to active status!")
                    else:
                        print(f"[-] Failed to update organization status")
                else:
                    print(f"[-] Could not find active status type")
            else:
                print(f"[+] Organization already has active status!")
        else:
            print(f"[-] Organization not found!")
        
        # Test the exact query the frontend uses
        print(f"\n[*] Testing frontend query...")
        user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"  # admin user
        
        frontend_result = supabase_service.client.table('org_members').select('''
            org_id,
            organizations!inner (
                id,
                name,
                status_types!inner (
                    key
                )
            ),
            user_roles!inner (
                key,
                display_name,
                can_manage_users,
                can_view_billing,
                can_upload_documents,
                can_generate_reports,
                can_view_analytics
            )
        ''').eq('user_id', user_id).eq('organizations.status_types.key', 'active').execute()
        
        if frontend_result.data:
            print(f"[+] Frontend query SUCCESS! Found {len(frontend_result.data)} records")
            for record in frontend_result.data:
                print(f"    - Org: {record['organizations']['name']}")
                print(f"    - Role: {record['user_roles']['display_name']}")
                print(f"    - Can upload: {record['user_roles']['can_upload_documents']}")
        else:
            print(f"[-] Frontend query FAILED!")
            print(f"    Error: {frontend_result}")
        
        return True
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_organization_status()