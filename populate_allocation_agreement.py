#!/usr/bin/env python3
"""
Populate allocation_agreement master data for testing
"""

import asyncio
import sys
import os
import uuid

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def populate_allocation_agreement_data():
    try:
        from app.services.supabase_service import supabase_service
        
        doc_type_id = '76a27d1d-a098-46e4-ad1c-f2542b115eb0'
        
        print('Populating allocation_agreement master data...')
        print('=' * 60)
        
        # 1. Update the document type
        print('1. Updating document type...')
        update_data = {
            'key': 'allocation_agreement',
            'display_name': 'Allocation Agreement',
            'notes': 'NMTC Allocation Agreement - Contract between CDE and CDFI Fund for tax credit allocation',
            'status': 'active'
        }
        
        result = supabase_service.client.table('document_types').update(update_data).eq('id', doc_type_id).execute()
        print('   Document type updated successfully')
        
        # 2. Add sections for allocation agreement
        print('\n2. Adding sections...')
        sections_data = [
            {
                'id': str(uuid.uuid4()),
                'document_type_id': doc_type_id,
                'canonical_name': 'Allocation Details',
                'description': 'Core allocation information including amount and terms',
                'order_no': 1,
                'is_required': True,
                'anchor_patterns': ['allocation amount', 'credit allocation', 'total allocation'],
                'extraction_priority': 'high'
            },
            {
                'id': str(uuid.uuid4()),
                'document_type_id': doc_type_id,
                'canonical_name': 'Geographic Restrictions',
                'description': 'Service area and geographic limitations',
                'order_no': 2,
                'is_required': True,
                'anchor_patterns': ['service area', 'geographic', 'county', 'census tract'],
                'extraction_priority': 'high'
            },
            {
                'id': str(uuid.uuid4()),
                'document_type_id': doc_type_id,
                'canonical_name': 'Compliance Requirements',
                'description': 'Regulatory requirements and reporting obligations',
                'order_no': 3,
                'is_required': True,
                'anchor_patterns': ['compliance', 'reporting', 'requirements', 'obligations'],
                'extraction_priority': 'medium'
            }
        ]
        
        for section in sections_data:
            result = supabase_service.client.table('sections').upsert(section).execute()
        print(f'   Added {len(sections_data)} sections')
        
        # 3. Add queries for sections
        print('\n3. Adding queries...')
        
        # Get the section IDs we just created
        result = supabase_service.client.table('sections').select('*').eq('document_type_id', doc_type_id).execute()
        sections = result.data if hasattr(result, 'data') and result.data else []
        
        queries_added = 0
        for section in sections:
            section_id = section['id']
            section_name = section['canonical_name']
            
            if section_name == 'Allocation Details':
                queries = [
                    {
                        'id': str(uuid.uuid4()),
                        'section_id': section_id,
                        'question_text': 'What is the total NMTC allocation amount?',
                        'expected_data_type': 'currency',
                        'extraction_method': 'pattern_match',
                        'priority': 'high',
                        'extractors': ['\\$[0-9,]+', 'allocation.*amount', 'total.*credit']
                    },
                    {
                        'id': str(uuid.uuid4()),
                        'section_id': section_id,
                        'question_text': 'What is the QEI investment deadline?',
                        'expected_data_type': 'date',
                        'extraction_method': 'pattern_match',
                        'priority': 'high',
                        'extractors': ['deadline', 'investment.*date', 'QEI.*by']
                    }
                ]
            elif section_name == 'Geographic Restrictions':
                queries = [
                    {
                        'id': str(uuid.uuid4()),
                        'section_id': section_id,
                        'question_text': 'What counties are included in the service area?',
                        'expected_data_type': 'list',
                        'extraction_method': 'pattern_match',
                        'priority': 'high',
                        'extractors': ['county', 'counties', 'service area']
                    }
                ]
            else:  # Compliance Requirements
                queries = [
                    {
                        'id': str(uuid.uuid4()),
                        'section_id': section_id,
                        'question_text': 'What are the annual reporting requirements?',
                        'expected_data_type': 'text',
                        'extraction_method': 'pattern_match',
                        'priority': 'medium',
                        'extractors': ['annual.*report', 'reporting.*requirement']
                    }
                ]
            
            for query in queries:
                result = supabase_service.client.table('queries').upsert(query).execute()
                queries_added += 1
        
        print(f'   Added {queries_added} queries')
        
        # 4. Update agent prompts to be more specific
        print('\n4. Updating agent prompts...')
        
        agent_prompts = [
            {
                'agent_key': 'agent_1_analyzer',
                'prompt_name': 'NMTC Document Analyzer',
                'system_prompt': 'You are an expert NMTC document analyzer with 15+ years experience.',
                'task_prompt': 'Analyze the extracted data for completeness, accuracy, and NMTC compliance requirements.',
                'style_guide': 'Professional, detailed, regulatory-focused',
                'output_schema_json': {'analysis': 'text', 'quality_score': 'number', 'recommendations': 'array'}
            },
            {
                'agent_key': 'agent_2_risk',
                'prompt_name': 'NMTC Risk Assessor', 
                'system_prompt': 'You are an NMTC compliance and risk assessment specialist.',
                'task_prompt': 'Evaluate compliance risks, recapture risks, and regulatory violations.',
                'style_guide': 'Risk-focused, quantitative, actionable',
                'output_schema_json': {'risk_level': 'text', 'risk_score': 'number', 'mitigation': 'array'}
            },
            {
                'agent_key': 'agent_3_reports',
                'prompt_name': 'NMTC Report Generator',
                'system_prompt': 'You are an NMTC reporting specialist creating professional compliance reports.',
                'task_prompt': 'Generate comprehensive reports suitable for CDE management and CDFI Fund review.',
                'style_guide': 'Executive-level, comprehensive, actionable',
                'output_schema_json': {'summary': 'text', 'findings': 'array', 'recommendations': 'array'}
            }
        ]
        
        for prompt in agent_prompts:
            result = supabase_service.client.table('agent_prompts').update(prompt).eq('agent_key', prompt['agent_key']).execute()
        
        print(f'   Updated {len(agent_prompts)} agent prompts')
        
        print('\n' + '=' * 60)
        print('SUCCESS: allocation_agreement master data populated!')
        print('READY TO TEST: AA_form.pdf can now be processed')
        
        # Verify the data
        print('\nVERIFYING DATA:')
        result = supabase_service.client.table('document_types').select('*').eq('id', doc_type_id).execute()
        if result.data:
            dt = result.data[0]
            print(f'Document Type: {dt.get("key")} - {dt.get("display_name", "")} - {dt.get("notes", "")[:50]}')
        
        result = supabase_service.client.table('sections').select('*').eq('document_type_id', doc_type_id).execute()
        sections = result.data if hasattr(result, 'data') and result.data else []
        print(f'Sections: {len(sections)} created')
        
        total_queries = 0
        for section in sections:
            result = supabase_service.client.table('queries').select('*').eq('section_id', section['id']).execute()
            queries = result.data if hasattr(result, 'data') and result.data else []
            total_queries += len(queries)
        
        print(f'Queries: {total_queries} created')
        print('\nREADY FOR TESTING!')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(populate_allocation_agreement_data())