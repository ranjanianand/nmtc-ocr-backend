#!/usr/bin/env python3
"""
Debug the actual structure returned by the frontend query
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

def debug_query_structure():
    """Check what the frontend query actually returns"""
    print("[*] Debugging query structure...")
    
    user_id = "5df566c7-149f-4e98-9b59-2e200805fe9a"
    
    try:
        from app.services.supabase_service import supabase_service
        
        result = supabase_service.client.table('org_members').select('''
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
        ''').eq('user_id', user_id).execute()
        
        print(f"[+] Query returned {len(result.data)} records")
        print(f"[+] Raw data structure:")
        print(json.dumps(result.data, indent=2))
        
        return True
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_query_structure()