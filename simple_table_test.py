#!/usr/bin/env python3
"""
Simple test script to verify workflow tables exist
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_workflow_tables():
    """Test if workflow enhancement tables exist"""
    try:
        from app.services.supabase_service import supabase_service
        
        print("Testing Workflow Enhancement Tables")
        print("=" * 50)
        
        workflow_tables = [
            'document_section_instances',
            'query_execution_results', 
            'normalization_applications',
            'business_rule_evaluations',
            'agent_prompt_applications',
            'workflow_stage_completions'
        ]
        
        print(f"Testing {len(workflow_tables)} workflow tables...")
        print()
        
        success_count = 0
        
        for table_name in workflow_tables:
            try:
                result = supabase_service.client.table(table_name).select('*').limit(0).execute()
                
                if hasattr(result, 'data'):
                    print(f"PASS: {table_name}")
                    success_count += 1
                else:
                    print(f"FAIL: {table_name} - No result object")
                    
            except Exception as e:
                print(f"FAIL: {table_name} - Error: {str(e)}")
        
        print()
        print(f"Results: {success_count}/{len(workflow_tables)} tables accessible")
        
        if success_count == len(workflow_tables):
            print("SUCCESS: All workflow tables are working!")
            return True
        else:
            print("ERROR: Some tables are missing")
            print()
            print("SOLUTION:")
            print("1. Go to Supabase Dashboard > SQL Editor")
            print("2. Copy content from: database/migrations/003_workflow_enhancement_tables.sql") 
            print("3. Paste and run the SQL")
            return False
            
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_workflow_tables())