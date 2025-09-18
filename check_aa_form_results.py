#!/usr/bin/env python3
"""
Check Real AA_form.pdf Processing Results
"""

import asyncio
from app.services.supabase_service import supabase_service

async def check_real_pdf_results():
    try:
        supabase = supabase_service.client

        print('=== REAL AA_FORM.PDF UPLOAD RESULTS ===')

        # Get the most recent AA_form.pdf document
        docs = supabase.table('documents').select('*').eq('filename', 'AA_form.pdf').order('uploaded_at', desc=True).limit(1).execute()

        if docs.data:
            doc = docs.data[0]
            doc_id = doc['id']

            print(f'Document ID: {doc_id}')
            print(f'Filename: {doc["filename"]}')
            print(f'Status: {doc["ocr_status"]}')
            print(f'Uploaded: {doc["uploaded_at"]}')
            print(f'Processing Results: {doc.get("processing_results", "None")}')
            print()

            # Check allocation year linkage
            print('=== ALLOCATION YEAR LINKAGE ===')
            years = supabase.table('allocation_years').select('*').eq('allocation_document_id', doc_id).execute()

            if years.data:
                year = years.data[0]
                print(f'Linked Year: {year["year"]}')
                print(f'Status: {year["status"]}')
                total_amt = float(year["total_amount"]) if year["total_amount"] else 0.0
                print(f'Total Amount: ${total_amt:,.2f}')
                print()
            else:
                print('No allocation year linkage found')
                print()

            # Check if there are any processing results yet
            print('=== PROCESSING PIPELINE STATUS ===')

            # Check document sections
            sections = supabase.table('document_section_instances').select('*').eq('document_id', doc_id).execute()
            print(f'Document Sections: {len(sections.data)} found')

            # Check query results
            queries = supabase.table('query_execution_results').select('*').eq('document_id', doc_id).execute()
            print(f'Query Results: {len(queries.data)} found')

            # Check workflow stages
            stages = supabase.table('workflow_stage_completions').select('*').eq('document_id', doc_id).execute()
            print(f'Workflow Stages: {len(stages.data)} completed')

            # Check processing sessions
            sessions = supabase.table('processing_sessions').select('*').eq('document_id', doc_id).execute()
            print(f'Processing Sessions: {len(sessions.data)} found')

            if sections.data or queries.data or stages.data or sessions.data:
                print()
                print('=== DETAILED RESULTS ===')

                if sections.data:
                    print('SECTIONS:')
                    for section in sections.data[:3]:  # Show first 3
                        print(f'- {section.get("section_name", "Unknown")}')

                if queries.data:
                    print('EXTRACTED DATA:')
                    for query in queries.data[:5]:  # Show first 5
                        print(f'- {query.get("query_key", "Unknown")}: {query.get("extracted_value", "No value")}')
            else:
                print('Processing still in progress - check back in a few minutes')

        else:
            print('No AA_form.pdf documents found')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_real_pdf_results())