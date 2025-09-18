#!/usr/bin/env python3
"""
Check table structures and populate minimal data for testing
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def check_and_populate():
    try:
        from app.services.supabase_service import supabase_service
        
        doc_type_id = '76a27d1d-a098-46e4-ad1c-f2542b115eb0'
        
        print('Checking table structures and populating minimal data...')
        print('=' * 60)
        
        # 1. Verify document_types update worked
        print('1. Checking document_types...')
        result = supabase_service.client.table('document_types').select('*').eq('id', doc_type_id).execute()
        if result.data:
            dt = result.data[0]
            print(f'   Document Type: {dt.get("key")} - {dt.get("display_name")}')
            print(f'   Status: {dt.get("status")}')
        
        # 2. Check sections table structure
        print('\n2. Checking sections table structure...')
        result = supabase_service.client.table('sections').select('*').limit(1).execute()
        if result.data:
            section = result.data[0]
            print('   sections table columns:')
            for key in section.keys():
                print(f'     - {key}')
        
        # 3. Check if sections exist for this document type
        result = supabase_service.client.table('sections').select('*').eq('document_type_id', doc_type_id).execute()
        existing_sections = result.data if hasattr(result, 'data') and result.data else []
        print(f'   Existing sections: {len(existing_sections)}')
        
        # 4. Check queries table structure  
        print('\n3. Checking queries table structure...')
        result = supabase_service.client.table('queries').select('*').limit(1).execute()
        if result.data:
            query = result.data[0]
            print('   queries table columns:')
            for key in query.keys():
                print(f'     - {key}')
        
        # 5. Check agent_prompts table structure
        print('\n4. Checking agent_prompts table structure...')
        result = supabase_service.client.table('agent_prompts').select('*').limit(1).execute()
        if result.data:
            prompt = result.data[0]
            print('   agent_prompts table columns:')
            for key in prompt.keys():
                print(f'     - {key}')
        
        # 6. Quick validation - check if we have any data to work with
        print('\n5. Checking existing data sufficiency...')
        
        # Check if we have sections 
        result = supabase_service.client.table('sections').select('*').execute()
        all_sections = result.data if hasattr(result, 'data') and result.data else []
        print(f'   Total sections in database: {len(all_sections)}')
        
        # Check if we have queries
        result = supabase_service.client.table('queries').select('*').execute() 
        all_queries = result.data if hasattr(result, 'data') and result.data else []
        print(f'   Total queries in database: {len(all_queries)}')
        
        # Check if we have agent prompts
        result = supabase_service.client.table('agent_prompts').select('*').execute()
        all_prompts = result.data if hasattr(result, 'data') and result.data else []
        print(f'   Total agent prompts: {len(all_prompts)}')
        
        print('\n' + '=' * 60)
        print('ASSESSMENT:')
        
        # Determine if we can test
        can_test = True
        
        if not result.data or dt.get('key') != 'allocation_agreement':
            print('   FAIL: Document type not properly set')
            can_test = False
        else:
            print('   PASS: Document type is allocation_agreement')
        
        if len(all_sections) < 3:
            print('   WARN: Limited sections available')
        else:
            print(f'   PASS: {len(all_sections)} sections available')
            
        if len(all_queries) < 3:
            print('   WARN: Limited queries available')  
        else:
            print(f'   PASS: {len(all_queries)} queries available')
            
        if len(all_prompts) < 3:
            print('   WARN: Limited agent prompts available')
        else:
            print(f'   PASS: {len(all_prompts)} agent prompts available')
        
        # Final assessment
        if can_test and len(all_sections) > 0 and len(all_queries) > 0:
            print('\n   RESULT: READY FOR BASIC TESTING!')
            print('   - Document type: allocation_agreement ✓')
            print('   - Master tables have data ✓')
            print('   - Workflow can proceed with existing data')
            print('\n   RECOMMENDATION: Test AA_form.pdf now!')
        else:
            print('\n   RESULT: NEED MORE DATA')
            print('   - Basic structure exists')
            print('   - May need to enhance master table data for better results')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_and_populate())