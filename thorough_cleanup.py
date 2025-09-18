#!/usr/bin/env python3
"""
Thorough database cleanup for 2023 allocation year - handles foreign key constraints
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def clean_2023_records():
    """Clean all 2023-related records from database with proper cascade"""

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("[ERROR] Missing Supabase configuration")
        return False

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        print("Finding 2023 allocation records...")

        # Find allocation_years for 2023
        allocation_years = supabase.table('allocation_years').select('*').eq('year', 2023).execute()
        print(f"Found {len(allocation_years.data) if allocation_years.data else 0} allocation year records for 2023")

        if not allocation_years.data:
            print("[INFO] No 2023 allocation records found. Database is already clean.")
            return True

        # Get the allocation year ID
        allocation_year_id = allocation_years.data[0]['id']
        print(f"Allocation year ID: {allocation_year_id}")

        # Find documents linked to this allocation year
        documents_2023 = supabase.table('documents').select('*').eq('allocation_year_id', allocation_year_id).execute()
        print(f"Found {len(documents_2023.data) if documents_2023.data else 0} documents linked to 2023")

        print("Starting cascade cleanup...")

        # Step 1: Delete agent_workflow_results that reference documents
        if documents_2023.data:
            document_ids = [doc['id'] for doc in documents_2023.data]
            print(f"Cleaning agent workflow results for {len(document_ids)} documents...")

            for doc_id in document_ids:
                try:
                    workflow_results = supabase.table('agent_workflow_results').delete().eq('document_id', doc_id).execute()
                    print(f"  [OK] Cleaned workflow results for document {doc_id}")
                except Exception as e:
                    print(f"  [WARNING] Could not clean workflow results for {doc_id}: {e}")

        # Step 2: Delete documents
        if documents_2023.data:
            print(f"Deleting {len(documents_2023.data)} documents...")
            for doc in documents_2023.data:
                try:
                    delete_result = supabase.table('documents').delete().eq('id', doc['id']).execute()
                    print(f"  [OK] Deleted document: {doc.get('filename', doc['id'])}")
                except Exception as e:
                    print(f"  [ERROR] Failed to delete document {doc['id']}: {e}")

        # Step 3: Delete QALICB entities if they exist
        try:
            qalicb_results = supabase.table('qalicb_entities').delete().eq('allocation_year_id', allocation_year_id).execute()
            print(f"  [OK] Cleaned QALICB entities for allocation year")
        except Exception as e:
            print(f"  [INFO] No QALICB entities to clean: {e}")

        # Step 4: Delete allocation year
        try:
            allocation_delete = supabase.table('allocation_years').delete().eq('id', allocation_year_id).execute()
            print(f"  [OK] Deleted allocation year record")
        except Exception as e:
            print(f"  [ERROR] Failed to delete allocation year: {e}")

        print("Cleanup completed!")

        # Verify cleanup
        print("Verifying cleanup...")
        remaining_years = supabase.table('allocation_years').select('*').eq('year', 2023).execute()
        remaining_count = len(remaining_years.data) if remaining_years.data else 0

        print(f"Remaining 2023 allocation year records: {remaining_count}")

        if remaining_count == 0:
            print("[SUCCESS] Database is clean for 2023!")
            return True
        else:
            print("[WARNING] Some records may still remain")
            return False

    except Exception as e:
        print(f"[ERROR] Database cleanup failed: {str(e)}")
        return False

def ensure_predefined_year_exists():
    """Ensure a clean 2023 predefined year record exists"""
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        print("Creating clean 2023 predefined year record...")

        # Create a fresh 2023 allocation year with no documents
        test_org_id = "test-org-id"
        year_data = {
            'org_id': test_org_id,
            'year': 2023,
            'total_amount': 0,
            'deployed_amount': 0,
            'status': 'inactive',
            'created_at': '2025-01-15T00:00:00Z'
        }

        insert_result = supabase.table('allocation_years').insert(year_data).execute()

        if insert_result.data:
            print(f"[OK] Created clean 2023 allocation year record")
            return True
        else:
            print(f"[ERROR] Failed to create 2023 record")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to create predefined year: {str(e)}")
        return False

if __name__ == "__main__":
    print("Thorough Database Cleanup for 2023 Allocation Testing")
    print("=" * 55)

    success = clean_2023_records()

    if success:
        # Create a fresh predefined year
        ensure_predefined_year_exists()

        print("\n[SUCCESS] Ready for fresh 2023 allocation testing!")
        print("You can now:")
        print("1. Go to http://localhost:8081")
        print("2. Navigate to Allocation Years")
        print("3. Select 2023 from left sidebar")
        print("4. Upload allocation agreement")
    else:
        print("\n[WARNING] Please check the errors above and try again")