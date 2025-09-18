#!/usr/bin/env python3
"""
Final database cleanup - handles circular foreign key references
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def clean_2023_records():
    """Clean all 2023-related records handling circular references"""

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
            print("[INFO] No 2023 allocation records found.")
            return True

        allocation_year_id = allocation_years.data[0]['id']
        allocation_document_id = allocation_years.data[0].get('allocation_document_id')

        print(f"Allocation year ID: {allocation_year_id}")
        print(f"Allocation document ID: {allocation_document_id}")

        print("Starting cleanup with circular reference handling...")

        # Step 1: Break circular reference by setting allocation_document_id to NULL
        if allocation_document_id:
            print("Breaking circular reference...")
            try:
                update_result = supabase.table('allocation_years').update({
                    'allocation_document_id': None
                }).eq('id', allocation_year_id).execute()
                print(f"  [OK] Cleared allocation_document_id reference")
            except Exception as e:
                print(f"  [ERROR] Failed to clear reference: {e}")

        # Step 2: Clean agent workflow results
        all_documents = supabase.table('documents').select('id').eq('allocation_year_id', allocation_year_id).execute()
        if all_documents.data:
            document_ids = [doc['id'] for doc in all_documents.data]
            print(f"Cleaning workflow results for {len(document_ids)} documents...")

            for doc_id in document_ids:
                try:
                    supabase.table('agent_workflow_results').delete().eq('document_id', doc_id).execute()
                    print(f"  [OK] Cleaned workflow for {doc_id}")
                except Exception as e:
                    print(f"  [WARNING] Workflow cleanup issue for {doc_id}: {e}")

        # Step 3: Delete documents
        if all_documents.data:
            print(f"Deleting {len(all_documents.data)} documents...")
            for doc in all_documents.data:
                try:
                    supabase.table('documents').delete().eq('id', doc['id']).execute()
                    print(f"  [OK] Deleted document {doc['id']}")
                except Exception as e:
                    print(f"  [ERROR] Failed to delete document {doc['id']}: {e}")

        # Step 4: Delete QALICB entities
        try:
            supabase.table('qalicb_entities').delete().eq('allocation_year_id', allocation_year_id).execute()
            print(f"  [OK] Cleaned QALICB entities")
        except Exception as e:
            print(f"  [INFO] No QALICB entities to clean: {e}")

        # Step 5: Delete allocation year
        try:
            supabase.table('allocation_years').delete().eq('id', allocation_year_id).execute()
            print(f"  [OK] Deleted allocation year record")
        except Exception as e:
            print(f"  [ERROR] Failed to delete allocation year: {e}")

        # Verify
        remaining = supabase.table('allocation_years').select('*').eq('year', 2023).execute()
        remaining_count = len(remaining.data) if remaining.data else 0

        print(f"Verification: {remaining_count} remaining 2023 records")

        return remaining_count == 0

    except Exception as e:
        print(f"[ERROR] Cleanup failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Final Database Cleanup for 2023")
    print("=" * 35)

    success = clean_2023_records()

    if success:
        print("\n[SUCCESS] 2023 records cleaned!")
        print("Database is ready for fresh testing.")
    else:
        print("\n[WARNING] Some cleanup issues occurred.")
        print("You may need to manually clean remaining records in Supabase dashboard.")