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

        # Check documents table for 2023
        documents_2023 = supabase.table('documents').select('*').eq('allocation_year', 2023).execute()
        print(f"Found {len(documents_2023.data) if documents_2023.data else 0} documents for 2023")

        # Check qalicb_entities for 2023 (if they exist)
        try:
            qalicb_2023 = supabase.table('qalicb_entities').select('*').execute()
            if qalicb_2023.data:
                qalicb_2023_filtered = [q for q in qalicb_2023.data if q.get('allocation_year_id') in [ay['id'] for ay in (allocation_years.data or [])]]
                print(f"Found {len(qalicb_2023_filtered)} QALICB entities for 2023")
        except:
            print("QALICB entities table not found (OK)")

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

        # 2. Delete QALICB entities for 2023 (if any)
        try:
            if allocation_years.data:
                for allocation_year in allocation_years.data:
                    qalicb_delete = supabase.table('qalicb_entities').delete().eq('allocation_year_id', allocation_year['id']).execute()
                    print(f"  ✅ Deleted QALICB entities for allocation year {allocation_year['id']}")
        except Exception as e:
            print(f"  ℹ️  QALICB cleanup skipped: {e}")

        # 3. Delete allocation years for 2023
        if allocation_years.data:
            print(f"Deleting {len(allocation_years.data)} allocation year records for 2023...")
            for ay in allocation_years.data:
                try:
                    delete_result = supabase.table('allocation_years').delete().eq('id', ay['id']).execute()
                    print(f"  ✅ Deleted allocation year: {ay['id']}")
                except Exception as e:
                    print(f"  ❌ Failed to delete allocation year {ay['id']}: {e}")

        print("\n✅ Cleanup completed!")

        # Verify cleanup
        print("\n🔍 Verifying cleanup...")
        allocation_years_check = supabase.table('allocation_years').select('*').eq('year', 2023).execute()
        documents_check = supabase.table('documents').select('*').eq('allocation_year', 2023).execute()

        remaining_ay = len(allocation_years_check.data) if allocation_years_check.data else 0
        remaining_docs = len(documents_check.data) if documents_check.data else 0

        print(f"Remaining allocation year records for 2023: {remaining_ay}")
        print(f"Remaining documents for 2023: {remaining_docs}")

        if remaining_ay == 0 and remaining_docs == 0:
            print("✅ Database is clean for 2023 - ready for fresh testing!")
            return True
        else:
            print("⚠️  Some records may still remain")
            return False

    except Exception as e:
        print(f"❌ Database cleanup failed: {str(e)}")
        return False

def verify_predefined_years():
    """Ensure predefined years 2020-2024 exist for testing"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        print("\n🔍 Checking predefined years setup...")

        # Check if we have a test org
        test_org_id = "test-org-id"
        predefined_years = [2024, 2023, 2022, 2021, 2020]

        for year in predefined_years:
            existing = supabase.table('allocation_years').select('*').eq('year', year).eq('org_id', test_org_id).execute()

            if not existing.data:
                # Create predefined year record
                year_data = {
                    'org_id': test_org_id,
                    'year': year,
                    'total_amount': 0,
                    'deployed_amount': 0,
                    'status': 'inactive',
                    'created_at': '2025-01-15T00:00:00Z'
                }

                insert_result = supabase.table('allocation_years').insert(year_data).execute()

                if insert_result.data:
                    print(f"  ✅ Created predefined year: {year}")
                else:
                    print(f"  ❌ Failed to create year: {year}")
            else:
                print(f"  ✅ Year {year} already exists")

        print("✅ Predefined years setup complete!")

    except Exception as e:
        print(f"❌ Predefined years setup failed: {str(e)}")

if __name__ == "__main__":
    print("Database Cleanup for 2023 Allocation Testing")
    print("=" * 50)

    success = clean_2023_records()

    if success:
        verify_predefined_years()
        print("\n🎉 Ready for fresh 2023 allocation testing!")
        print("You can now:")
        print("1. Go to http://localhost:8081")
        print("2. Navigate to Allocation Years")
        print("3. Select 2023 from left sidebar")
        print("4. Upload allocation agreement")
    else:
        print("\n⚠️  Please check the errors above and try again")