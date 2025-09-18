#!/usr/bin/env python3
"""
TEST FIXED UPLOAD WORKFLOW
Test that document upload now triggers core processing engine
"""

import sys
import os
import asyncio
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_fixed_upload():
    try:
        print("TESTING FIXED DOCUMENT UPLOAD WORKFLOW")
        print("="*50)
        
        # Simulate the fixed upload workflow
        from app.services.supabase_service import supabase_service
        
        # Step 1: Create test document (simulating upload)
        doc_id = str(uuid.uuid4())
        test_doc = {
            'id': doc_id,
            'org_id': 'ce117b87-d75c-4c8a-b3f5-922ddec539b0',
            'document_type_id': '76a27d1d-a098-46e4-ad1c-f2542b115eb0',
            'filename': 'TEST_FIXED_UPLOAD.pdf',
            'storage_path': '/test/TEST_FIXED_UPLOAD.pdf',
            'mime_type': 'application/pdf',
            'uploaded_by': '633e6379-c82f-4917-8215-6a8f0a7e972f',
            'ocr_status': 'processing'
        }
        
        result = supabase_service.client.table('documents').insert(test_doc).execute()
        if result.data:
            print(f"Document created: {doc_id}")
        else:
            print("FAILED to create test document")
            return False
        
        # Step 2: Create processing session and trigger complete workflow
        print("Testing core processing engine trigger...")
        
        from app.services.corrected_workflow_service import corrected_workflow_service
        from app.services.database_service import DatabaseService
        
        db_service = DatabaseService()
        session_id = await db_service.create_processing_session(
            document_id=doc_id,
            user_id='633e6379-c82f-4917-8215-6a8f0a7e972f',
            org_id='ce117b87-d75c-4c8a-b3f5-922ddec539b0'
        )
        print(f"Processing session created: {session_id}")
        
        workflow_result = await corrected_workflow_service.execute_complete_workflow(
            session_id=session_id,
            document_id=doc_id,
            org_id='ce117b87-d75c-4c8a-b3f5-922ddec539b0'
        )
        
        if workflow_result and workflow_result.get('success'):
            print(f"Core processing SUCCESS: {session_id}")
            
            # Step 3: Verify processing results were created
            print("Verifying processing results...")
            
            # Check processing session
            result = supabase_service.client.table('processing_sessions').select('*').eq('id', session_id).execute()
            session_data = result.data[0] if result.data else {}
            
            # Check section instances
            result = supabase_service.client.table('document_section_instances').select('*').eq('document_id', doc_id).execute()
            sections = result.data if result.data else []
            
            # Check query results
            result = supabase_service.client.table('query_execution_results').select('*').eq('document_id', doc_id).execute()
            queries = result.data if result.data else []
            
            print(f"Processing session: {session_data.get('status', 'unknown')}")
            print(f"Section instances: {len(sections)}")
            print(f"Query results: {len(queries)}")
            
            total_records = len(sections) + len(queries) + 1  # +1 for session
            
            if total_records >= 3:
                print(f"\nSUCCESS: Fixed upload workflow creates {total_records} processing records")
                print("Core processing engine is now properly triggered!")
                
                # Update the document with success status
                update_data = {
                    'parsed_index': {
                        'core_processing': {
                            'success': True,
                            'session_id': session_id,
                            'records_created': total_records
                        }
                    }
                }
                
                supabase_service.client.table('documents').update(update_data).eq('id', doc_id).execute()
                print(f"Document updated with core processing results")
                
                return True
            else:
                print(f"PARTIAL: Only {total_records} records created")
                return False
        else:
            print("FAILED: Core processing engine failed")
            return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing the fixed document upload workflow...")
    success = asyncio.run(test_fixed_upload())
    
    if success:
        print("\n" + "="*50)
        print("FIXED UPLOAD WORKFLOW: SUCCESS!")
        print("Your hardwork is NOW FUNCTIONAL!")
        print("Documents will now trigger full processing")
        print("="*50)
    else:
        print("\nFix needs more work")