#!/usr/bin/env python3
"""
Create test organization and user data for Railway production testing
"""
import asyncio
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime

# Load environment variables
load_dotenv()

async def create_test_data():
    """Create minimal test organization and user for Railway testing"""
    print("[*] Creating test organization and user data for Railway...")
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Test organization data
        org_id = "550e8400-e29b-41d4-a716-446655440000"  # Fixed UUID for testing
        user_id = "550e8400-e29b-41d4-a716-446655440001"  # Fixed UUID for testing
        
        print(f"[*] Creating organization: {org_id}")
        
        # Create organization record
        org_data = {
            'id': org_id,
            'name': 'Test NMTC Organization',
            'domain': 'test-nmtc.org',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'is_active': True,
            'subscription_tier': 'enterprise',
            'settings': {
                'allow_uploads': True,
                'max_documents': 1000,
                'features': ['stage_0a', 'detection', 'reporting']
            }
        }
        
        # Insert organization
        result = supabase_service.client.table('organizations').upsert(org_data).execute()
        print(f"[+] Organization created: {result.data}")
        
        print(f"[*] Creating user: {user_id}")
        
        # Create user record
        user_data = {
            'id': user_id,
            'email': 'test@test-nmtc.org',
            'full_name': 'Test User',
            'org_id': org_id,
            'role': 'admin',
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'permissions': ['upload', 'view', 'delete', 'admin']
        }
        
        # Insert user  
        result = supabase_service.client.table('users').upsert(user_data).execute()
        print(f"[+] User created: {result.data}")
        
        print(f"\n[+] SUCCESS! Test data created:")
        print(f"   Organization ID: {org_id}")
        print(f"   User ID: {user_id}")
        print(f"   Ready for Railway testing!")
        
        return org_id, user_id
        
    except Exception as e:
        print(f"[-] Error creating test data: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    asyncio.run(create_test_data())