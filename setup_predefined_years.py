#!/usr/bin/env python3
"""
Setup predefined allocation years (2020-2024) for testing
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def setup_predefined_years():
    """Ensure predefined years 2020-2024 exist"""

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        print("Setting up predefined allocation years...")

        # Use the actual org ID from your database
        test_org_id = "ce117b87-d75c-4c8a-b3f5-922ddec539b0"
        predefined_years = [2024, 2023, 2022, 2021, 2020]

        for year in predefined_years:
            # Check if year already exists
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
                    print(f"  [OK] Created predefined year: {year}")
                else:
                    print(f"  [ERROR] Failed to create year: {year}")
            else:
                print(f"  [EXISTS] Year {year} already exists")

        print("[SUCCESS] Predefined years setup complete!")

        # Verify setup
        all_years = supabase.table('allocation_years').select('year, status').eq('org_id', test_org_id).order('year', desc=True).execute()

        if all_years.data:
            print("\nCurrent allocation years:")
            for year_record in all_years.data:
                print(f"  - {year_record['year']}: {year_record['status']}")

        return True

    except Exception as e:
        print(f"[ERROR] Setup failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Predefined Allocation Years Setup")
    print("=" * 35)

    success = setup_predefined_years()

    if success:
        print("\n[SUCCESS] Ready for allocation year testing!")
        print("The frontend should now show years 2020-2024 in the left sidebar.")
    else:
        print("\n[ERROR] Setup failed - check errors above")