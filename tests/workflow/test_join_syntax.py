#!/usr/bin/env python3
"""
Test different PostgREST join syntaxes to find what works
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_join_syntax():
    """Test different PostgREST join approaches"""
    print("[*] Testing PostgREST join syntax...")
    
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Test 1: Basic foreign key join without inner
        print(f"\n[*] Test 1: Basic foreign key joins...")
        try:
            result1 = supabase_service.client.table('org_members').select('''
              org_id,
              organizations(id, name, status_id),
              user_roles(key, display_name, can_upload_documents)
            ''').eq('user_id', user_id).execute()
            
            print(f"[+] Basic joins work! Got {len(result1.data)} records")
            if result1.data:
                print(f"    Data: {result1.data[0]}")
        except Exception as e:
            print(f"[-] Basic joins failed: {e}")
        
        # Test 2: Join with status_types 
        print(f"\n[*] Test 2: Join with status_types...")
        try:
            result2 = supabase_service.client.table('org_members').select('''
              org_id,
              organizations(id, name, status_types(key)),
              user_roles(key, display_name, can_upload_documents)
            ''').eq('user_id', user_id).execute()
            
            print(f"[+] Status joins work! Got {len(result2.data)} records")
            if result2.data:
                record = result2.data[0]
                print(f"    Org: {record.get('organizations', {}).get('name')}")
                print(f"    Status: {record.get('organizations', {}).get('status_types', {}).get('key')}")
                print(f"    Role: {record.get('user_roles', {}).get('display_name')}")
                print(f"    Can upload: {record.get('user_roles', {}).get('can_upload_documents')}")
        except Exception as e:
            print(f"[-] Status joins failed: {e}")
            
        # Test 3: Manual filtering approach
        print(f"\n[*] Test 3: Manual filtering approach...")
        try:
            # Get org member data
            org_result = supabase_service.client.table('org_members').select('*').eq('user_id', user_id).execute()
            if org_result.data:
                member = org_result.data[0]
                org_id = member['org_id']
                role_id = member['role_id']
                
                # Get organization with status
                org_data = supabase_service.client.table('organizations').select('*, status_types(*)').eq('id', org_id).execute()
                
                # Get role data
                role_data = supabase_service.client.table('user_roles').select('*').eq('id', role_id).execute()
                
                if org_data.data and role_data.data:
                    org = org_data.data[0]
                    role = role_data.data[0]
                    status = org['status_types']['key']
                    
                    print(f"[+] Manual approach works!")
                    print(f"    Org: {org['name']}")
                    print(f"    Status: {status}")
                    print(f"    Role: {role['display_name']}")
                    print(f"    Can upload: {role['can_upload_documents']}")
                    print(f"    Status is active: {status == 'active'}")
                    
                    return status == 'active' and role['can_upload_documents']
        except Exception as e:
            print(f"[-] Manual approach failed: {e}")
        
        return False
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_join_syntax()
    print(f"\n{'SUCCESS' if success else 'FAILED'}: User can {'login and upload' if success else 'not access properly'}")