#!/usr/bin/env python3
"""
Test script to verify the workflow enhancement tables are created and accessible
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_tables():
    """Test if all workflow enhancement tables exist and are accessible"""
    try:
        from app.services.supabase_service import supabase_service
        
        print("Testing Workflow Enhancement Tables")
        print("=" * 50)
        
        # List of tables to test
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
                # Try to query the table (limit 0 to avoid any data)
                result = supabase_service.client.table(table_name).select('*').limit(0).execute()
                
                if hasattr(result, 'data'):
                    print(f"✓ {table_name:<30} - Table exists and accessible")
                    success_count += 1
                else:
                    print(f"✗ {table_name:<30} - Query returned no result object")
                    
            except Exception as e:
                print(f"✗ {table_name:<30} - Error: {str(e)}")
        
        print()
        print(f"Results: {success_count}/{len(workflow_tables)} tables accessible")
        
        if success_count == len(workflow_tables):
            print("🎉 ALL WORKFLOW TABLES ARE WORKING!")
            print("\nNext steps:")
            print("1. The corrected stage-dependent workflow is ready to use")
            print("2. Test with a real document upload")
            print("3. Check the new API endpoints for result retrieval")
            return True
        else:
            print("❌ Some tables are missing or inaccessible")
            print("\nPlease run the migration using Supabase Dashboard SQL Editor:")
            print("1. Copy content from: database/migrations/003_workflow_enhancement_tables.sql")
            print("2. Paste and run in: https://supabase.com/dashboard > SQL Editor")
            return False
            
    except Exception as e:
        print(f"Test failed: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check if your environment variables are set correctly")
        print("2. Verify Supabase connection is working")
        print("3. Run the migration in Supabase Dashboard")
        return False

async def test_database_service():
    """Test if the database service methods work with the new tables"""
    try:
        from app.services.database_service import DatabaseService
        
        print("\nTesting Database Service Methods")
        print("-" * 40)
        
        db_service = DatabaseService()
        
        # Test methods that should exist
        test_methods = [
            'store_section_instance',
            'store_query_execution', 
            'store_normalization_application',
            'store_business_rule_evaluation',
            'store_agent_prompt_application',
            'create_workflow_stage'
        ]
        
        method_count = 0
        
        for method_name in test_methods:
            if hasattr(db_service, method_name):
                print(f"✓ {method_name}")
                method_count += 1
            else:
                print(f"✗ {method_name} - Method not found")
        
        print(f"\nDatabase service methods: {method_count}/{len(test_methods)} available")
        
        return method_count == len(test_methods)
        
    except Exception as e:
        print(f"Database service test failed: {str(e)}")
        return False

if __name__ == "__main__":
    async def main():
        print("NMTC Workflow Enhancement Tables Test")
        print("=" * 60)
        
        # Test table accessibility
        tables_ok = await test_tables()
        
        # Test database service methods
        methods_ok = await test_database_service()
        
        print("\n" + "=" * 60)
        if tables_ok and methods_ok:
            print("🎉 ALL TESTS PASSED!")
            print("The corrected stage-dependent workflow is ready to use!")
        else:
            print("❌ TESTS FAILED")
            print("Please check the migration and database service setup.")
    
    asyncio.run(main())