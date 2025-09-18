#!/usr/bin/env python3
"""
Clean database records for 2023 allocation year to start fresh testing
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def clean_2023_records():
    """Clean all 2023-related records from database"""

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("[ERROR] Missing Supabase configuration")
        return False

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        print("Checking existing 2023 records...")

        # Check allocation_years table
        allocation_years = supabase.table('allocation_years').select('*').eq('year', 2023).execute()
        print(f"Found {len(allocation_years.data) if allocation_years.data else 0} allocation year records for 2023")

        # Check documents table for 2023 - get allocation_year_id first
        if allocation_years.data:
            allocation_year_ids = [ay['id'] for ay in allocation_years.data]
            documents_2023 = supabase.table('documents').select('*').in_('allocation_year_id', allocation_year_ids).execute()
        else:
            documents_2023 = supabase.table('documents').select('*').eq('allocation_year_id', 'none').execute()
        print(f"Found {len(documents_2023.data) if documents_2023.data else 0} documents for 2023")

        print("Starting cleanup...")

        # 1. Delete documents for 2023
        if documents_2023.data:
            print(f"Deleting {len(documents_2023.data)} documents for 2023...")
            for doc in documents_2023.data:
                try:
                    delete_result = supabase.table('documents').delete().eq('id', doc['id']).execute()
                    print(f"  [OK] Deleted document: {doc.get('filename', doc['id'])}")
                except Exception as e:
                    print(f"  [ERROR] Failed to delete document {doc['id']}: {e}")

        # 2. Delete allocation years for 2023
        if allocation_years.data:
            print(f"Deleting {len(allocation_years.data)} allocation year records for 2023...")
            for ay in allocation_years.data:
                try:
                    delete_result = supabase.table('allocation_years').delete().eq('id', ay['id']).execute()
                    print(f"  [OK] Deleted allocation year: {ay['id']}")
                except Exception as e:
                    print(f"  [ERROR] Failed to delete allocation year {ay['id']}: {e}")

        print("Cleanup completed!")

        # Verify cleanup
        print("Verifying cleanup...")
        allocation_years_check = supabase.table('allocation_years').select('*').eq('year', 2023).execute()
        documents_check = supabase.table('documents').select('*').execute()  # Check all documents since we deleted by ID

        remaining_ay = len(allocation_years_check.data) if allocation_years_check.data else 0
        remaining_docs = len(documents_check.data) if documents_check.data else 0

        print(f"Remaining allocation year records for 2023: {remaining_ay}")
        print(f"Remaining documents for 2023: {remaining_docs}")

        if remaining_ay == 0 and remaining_docs == 0:
            print("[SUCCESS] Database is clean for 2023 - ready for fresh testing!")
            return True
        else:
            print("[WARNING] Some records may still remain")
            return False

    except Exception as e:
        print(f"[ERROR] Database cleanup failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Database Cleanup for 2023 Allocation Testing")
    print("=" * 50)

    success = clean_2023_records()

    if success:
        print("\n[SUCCESS] Ready for fresh 2023 allocation testing!")
        print("You can now:")
        print("1. Go to http://localhost:8081")
        print("2. Navigate to Allocation Years")
        print("3. Select 2023 from left sidebar")
        print("4. Upload allocation agreement")
    else:
        print("\n[WARNING] Please check the errors above and try again")