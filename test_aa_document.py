#!/usr/bin/env python3
"""
Test AA_form.pdf with complete workflow
Using Enhanced Database Architect principles - NO ASSUMPTIONS
"""

import asyncio
import sys
import os
import uuid

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_aa_document_workflow():
    try:
        from app.services.supabase_service import supabase_service
        from app.services.corrected_workflow_service import corrected_workflow_service
        
        print("TESTING AA_FORM.PDF WITH CORRECTED WORKFLOW")
        print("=" * 60)
        print("Using Enhanced Database Architect approach - VERIFIED SCHEMA ONLY")
        
        # Step 1: Verify we have the allocation_agreement document type
        doc_type_id = '76a27d1d-a098-46e4-ad1c-f2542b115eb0'
        
        print("1. Verifying document type exists...")
        result = supabase_service.client.table('document_types').select('*').eq('id', doc_type_id).execute()
        if not result.data:
            print("   ERROR: Document type not found")
            return False
        
        doc_type = result.data[0]
        print(f"   SUCCESS: {doc_type.get('key')} - {doc_type.get('display_name')}")
        
        # Step 2: Check for existing sections (VERIFIED COLUMNS ONLY)
        print("\n2. Checking sections for document type...")
        result = supabase_service.client.table('sections').select('*').eq('document_type_id', doc_type_id).execute()
        sections = result.data if result.data else []
        print(f"   Found {len(sections)} sections")
        
        if len(sections) == 0:
            print("   Creating test sections using VERIFIED schema...")
            # Using only columns we VERIFIED exist: id, document_type_id, canonical_name, order_no, anchor_patterns, ml_fallback_model, notes, version, created_at
            test_sections = [
                {
                    'id': str(uuid.uuid4()),
                    'document_type_id': doc_type_id,
                    'canonical_name': 'Allocation Details',
                    'order_no': 1,
                    'anchor_patterns': ['allocation amount', 'credit allocation', 'total allocation'],
                    'ml_fallback_model': 'gpt-4',
                    'notes': 'Core allocation information including amount and terms',
                    'version': 1
                },
                {
                    'id': str(uuid.uuid4()),
                    'document_type_id': doc_type_id,
                    'canonical_name': 'Geographic Restrictions',
                    'order_no': 2,
                    'anchor_patterns': ['service area', 'geographic', 'county', 'census tract'],
                    'ml_fallback_model': 'gpt-4',
                    'notes': 'Service area and geographic limitations',
                    'version': 1
                }
            ]
            
            for section in test_sections:
                result = supabase_service.client.table('sections').insert(section).execute()
            
            print(f"   Created {len(test_sections)} test sections")
            sections = test_sections
        
        # Step 3: Check for queries (VERIFIED COLUMNS ONLY)
        print("\n3. Checking queries...")
        total_queries = 0
        for section in sections:
            result = supabase_service.client.table('queries').select('*').eq('section_id', section['id']).execute()
            section_queries = result.data if result.data else []
            total_queries += len(section_queries)
        
        print(f"   Found {total_queries} total queries")
        
        if total_queries == 0:
            print("   Creating test queries using VERIFIED schema...")
            # Using only columns we VERIFIED exist: id, document_type_id, section_id, query_key, question_text, extractors, normalizer_hint, required, version, status, created_at
            for section in sections[:1]:  # Just first section for testing
                test_query = {
                    'id': str(uuid.uuid4()),
                    'document_type_id': doc_type_id,
                    'section_id': section['id'],
                    'query_key': 'AA.ALLOCATION.AMOUNT',
                    'question_text': 'What is the total NMTC allocation amount?',
                    'extractors': ['currency_extract'],
                    'normalizer_hint': 'currency',
                    'required': True,
                    'version': 1,
                    'status': 'active'
                }
                
                result = supabase_service.client.table('queries').insert(test_query).execute()
                print(f"   Created test query: {test_query['question_text']}")
        
        # Step 4: Check if AA_form.pdf exists
        print("\n4. Checking for AA_form.pdf...")
        if os.path.exists('pdfs/AA_form.pdf'):
            print("   SUCCESS: AA_form.pdf found")
            
            # Step 5: Create a test document record (VERIFIED COLUMNS ONLY)
            print("\n5. Creating document record...")
            # Using only columns we VERIFIED exist: id, org_id, document_type_id, filename, storage_path, mime_type, hash, uploaded_by, uploaded_at, ocr_status, parsed_index
            
            test_document = {
                'id': str(uuid.uuid4()),
                'org_id': 'ce117b87-d75c-4c8a-b3f5-922ddec539b0',  # From verified data
                'document_type_id': doc_type_id,
                'filename': 'AA_form.pdf',
                'storage_path': '/test/AA_form.pdf',
                'mime_type': 'application/pdf',
                'uploaded_by': '633e6379-c82f-4917-8215-6a8f0a7e972f',  # From verified data
                'ocr_status': 'pending'
            }
            
            result = supabase_service.client.table('documents').insert(test_document).execute()
            if result.data:
                doc_id = result.data[0]['id']
                print(f"   SUCCESS: Document record created - {doc_id}")
                
                # Step 6: Test the corrected workflow service
                print("\n6. Testing corrected workflow...")
                try:
                    workflow_result = await corrected_workflow_service.process_document(doc_id)
                    
                    if workflow_result and workflow_result.get('success'):
                        print("   SUCCESS: Workflow completed successfully")
                        print(f"   Stages completed: {workflow_result.get('stages_completed', 0)}")
                        print(f"   Processing session: {workflow_result.get('session_id')}")
                        
                        # Step 7: Check workflow results in database
                        print("\n7. Verifying results in database...")
                        session_id = workflow_result.get('session_id')
                        
                        if session_id:
                            result = supabase_service.client.table('workflow_stage_completions').select('*').eq('session_id', session_id).execute()
                            stages = result.data if result.data else []
                            print(f"   Workflow stages recorded: {len(stages)}")
                            
                            for stage in stages:
                                print(f"     Stage {stage.get('stage_number')}: {stage.get('stage_name')} - {stage.get('status')}")
                        
                        return True
                        
                    else:
                        print(f"   ERROR: Workflow failed - {workflow_result}")
                        return False
                        
                except Exception as e:
                    print(f"   ERROR: Workflow execution failed - {str(e)}")
                    return False
            else:
                print("   ERROR: Failed to create document record")
                return False
        else:
            print("   ERROR: AA_form.pdf not found in pdfs/ folder")
            return False
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_aa_document_workflow())
    if success:
        print("\n" + "=" * 60)
        print("COMPLETE WORKFLOW TEST: SUCCESS")
        print("Enhanced Database Architect approach proven effective")
        print("Ready for production use with real documents")
    else:
        print("\n" + "=" * 60)
        print("WORKFLOW TEST: FAILED")
        print("Review errors and fix issues before production")