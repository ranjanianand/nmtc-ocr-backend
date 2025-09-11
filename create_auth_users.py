#!/usr/bin/env python3
"""
Create Supabase Auth users for frontend testing
"""
import os
from dotenv import load_dotenv
from datetime import datetime
import uuid

# Load environment variables
load_dotenv()

def create_test_users():
    """Create Supabase Auth users linked to existing organization"""
    print("[*] Creating Supabase Auth users for testing...")
    
    # Existing organization from seed data
    org_id = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"  # Opportunity Finance Network
    
    try:
        from app.services.supabase_service import supabase_service
        
        # Test users to create
        test_users = [
            {
                "email": "admin@nmtc-test.org", 
                "password": "Test123!",
                "role": "admin",
                "full_name": "NMTC Admin User"
            },
            {
                "email": "user@nmtc-test.org",
                "password": "Test123!", 
                "role": "user",
                "full_name": "NMTC Regular User"
            }
        ]
        
        created_users = []
        
        for user_data in test_users:
            print(f"\n[*] Creating user: {user_data['email']}")
            
            try:
                # Create auth user in Supabase Auth
                auth_response = supabase_service.client.auth.admin.create_user({
                    "email": user_data["email"],
                    "password": user_data["password"],
                    "email_confirm": True,  # Auto-confirm email
                    "user_metadata": {
                        "full_name": user_data["full_name"],
                        "role": user_data["role"]
                    }
                })
                
                if auth_response.user:
                    auth_user_id = auth_response.user.id
                    print(f"[+] Auth user created: {auth_user_id}")
                    
                    # Create user record in your users table
                    user_record = {
                        'id': auth_user_id,  # Use same ID as auth user
                        'email': user_data["email"],
                        'full_name': user_data["full_name"],
                        'org_id': org_id,
                        'role': user_data["role"],
                        'is_active': True,
                        'created_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }
                    
                    # Insert into users table
                    result = supabase_service.client.table('users').upsert(user_record).execute()
                    
                    if result.data:
                        print(f"[+] User record created in database")
                        created_users.append({
                            "email": user_data["email"],
                            "password": user_data["password"],
                            "user_id": auth_user_id,
                            "org_id": org_id,
                            "role": user_data["role"]
                        })
                    else:
                        print(f"[-] Failed to create user record in database")
                        
                else:
                    print(f"[-] Failed to create auth user")
                    
            except Exception as e:
                print(f"[-] Error creating user {user_data['email']}: {e}")
                continue
        
        # Summary
        print(f"\n" + "="*60)
        print(f"[+] CREATED {len(created_users)} TEST USERS")
        print(f"[+] Organization: Opportunity Finance Network")
        print(f"[+] Org ID: {org_id}")
        
        for user in created_users:
            print(f"\n[+] User: {user['email']}")
            print(f"    Password: {user['password']}")
            print(f"    User ID: {user['user_id']}")
            print(f"    Role: {user['role']}")
        
        print(f"\n[+] READY FOR FRONTEND TESTING!")
        print(f"[+] Use these credentials to login via frontend")
        print("="*60)
        
        return created_users
        
    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    users = create_test_users()
    if users:
        print(f"\nSUCCESS - {len(users)} users created for frontend testing!")
    else:
        print(f"\nFAILED - Unable to create test users")