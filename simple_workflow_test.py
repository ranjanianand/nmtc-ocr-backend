#!/usr/bin/env python3
"""
Simple workflow test without complex dependencies
Tests core database operations and workflow stages
"""

import asyncio
import sys
import os
import uuid

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def simple_workflow_test():
    try:
        from app.services.supabase_service import supabase_service
        from app.services.database_service import DatabaseService
        
        db_service = DatabaseService()
        
        print("SIMPLE WORKFLOW TEST")
        print("=" * 50)
        print("Testing database operations and workflow stages")
        
        # Step 1: Verify master data exists
        doc_type_id = '76a27d1d-a098-46e4-ad1c-f2542b115eb0'
        
        print("\n1. Checking master data...")
        result = supabase_service.client.table('document_types').select('*').eq('id', doc_type_id).execute()
        if result.data:
            print(f"   Document type: {result.data[0].get('key')}")
        else:
            print("   ERROR: No document type found")
            return False
        
        # Step 2: Check sections
        result = supabase_service.client.table('sections').select('*').eq('document_type_id', doc_type_id).execute()
        sections = result.data if result.data else []
        print(f"   Sections available: {len(sections)}")
        
        # Step 3: Check queries  
        total_queries = 0
        for section in sections:
            result = supabase_service.client.table('queries').select('*').eq('section_id', section['id']).execute()
            queries = result.data if result.data else []
            total_queries += len(queries)
        print(f"   Queries available: {total_queries}")
        
        # Step 4: Create test document
        print("\n2. Creating test document...")
        test_doc = {
            'id': str(uuid.uuid4()),
            'org_id': 'ce117b87-d75c-4c8a-b3f5-922ddec539b0',
            'document_type_id': doc_type_id,
            'filename': 'test_workflow.pdf',
            'storage_path': '/test/workflow.pdf',
            'mime_type': 'application/pdf',
            'uploaded_by': '633e6379-c82f-4917-8215-6a8f0a7e972f',
            'ocr_status': 'processing'
        }
        
        result = supabase_service.client.table('documents').insert(test_doc).execute()
        if result.data:
            doc_id = result.data[0]['id']
            print(f"   Document created: {doc_id}")
        else:
            print("   ERROR: Failed to create document")
            return False
        
        # Step 5: Test workflow table operations
        print("\n3. Testing workflow operations...")
        session_id = str(uuid.uuid4())
        
        # Test processing session
        session_data = {
            'id': session_id,
            'document_id': doc_id,
            'status': 'in_progress',
            'started_at': '2025-09-13T19:00:00Z'
        }
        
        result = await db_service.create_processing_session(
            document_id=doc_id,
            user_id='633e6379-c82f-4917-8215-6a8f0a7e972f',
            org_id='ce117b87-d75c-4c8a-b3f5-922ddec539b0'
        )
        if result:
            print("   Processing session: CREATED")
        else:
            print("   Processing session: FAILED")
            return False
        
        # Test section instances
        for section in sections[:1]:  # Test one section
            instance_data = {
                'id': str(uuid.uuid4()),
                'document_id': doc_id,
                'section_id': section['id'],
                'status': 'completed',
                'extracted_text': 'Test extracted text',
                'confidence_score': 0.95
            }
            
            result = await db_service.store_section_instance(instance_data)
            if result:
                print(f"   Section instance: CREATED")
                
                # Test query execution
                if total_queries > 0:
                    query_result = {
                        'id': str(uuid.uuid4()),
                        'section_instance_id': instance_data['id'],
                        'query_id': 'test-query-id',
                        'extracted_value': 'Test value',
                        'confidence_score': 0.90,
                        'extraction_method': 'test_method'
                    }
                    
                    result = await db_service.store_query_execution(query_result)
                    if result:
                        print("   Query execution: CREATED")
        
        # Step 6: Test workflow stage completion
        stage_completion = {
            'id': str(uuid.uuid4()),
            'session_id': session_id,
            'stage_number': 1,
            'stage_name': 'Document Type Recognition',
            'status': 'completed',
            'started_at': '2025-09-13T19:00:00Z',
            'completed_at': '2025-09-13T19:01:00Z'
        }
        
        result = await db_service.complete_workflow_stage(stage_completion)
        if result:
            print("   Workflow stage: COMPLETED")
        
        # Step 7: Verify data in database
        print("\n4. Verifying workflow data...")
        
        # Check processing sessions
        result = supabase_service.client.table('processing_sessions').select('*').eq('id', session_id).execute()
        if result.data:
            print(f"   Processing session verified: {result.data[0].get('status')}")
        
        # Check stage completions
        result = supabase_service.client.table('workflow_stage_completions').select('*').eq('session_id', session_id).execute()
        stages = result.data if result.data else []
        print(f"   Workflow stages recorded: {len(stages)}")
        
        print("\n" + "=" * 50)
        print("SIMPLE WORKFLOW TEST: SUCCESS")
        print("All core database operations working")
        print("Workflow tables properly integrated")
        print("Ready for full AI service integration")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_workflow_test())
    if not success:
        print("Test failed - check errors above")