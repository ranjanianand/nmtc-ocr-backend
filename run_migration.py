#!/usr/bin/env python3
"""
Run the workflow enhancement tables migration
"""

import asyncio
import os
from app.services.supabase_service import supabase_service

async def run_migration():
    """Run the workflow enhancement migration"""
    try:
        # Read the migration file
        migration_file = "database/migrations/003_workflow_enhancement_tables.sql"
        
        if not os.path.exists(migration_file):
            print(f"Migration file not found: {migration_file}")
            return
            
        print(f"Reading migration file: {migration_file}")
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print(f"Migration SQL length: {len(migration_sql)} characters")
        print("Starting migration execution...")
        
        # Split the SQL into individual statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        print(f"Found {len(statements)} SQL statements to execute")
        
        # Execute each statement
        for i, statement in enumerate(statements, 1):
            try:
                if statement.upper().startswith('--') or len(statement) < 10:
                    continue
                    
                print(f"Executing statement {i}/{len(statements)}...")
                print(f"Statement preview: {statement[:100]}...")
                
                # Use Supabase client to execute SQL
                result = supabase_service.client.rpc('exec_sql', {'sql': statement}).execute()
                
                if hasattr(result, 'error') and result.error:
                    print(f"Error in statement {i}: {result.error}")
                else:
                    print(f"Statement {i} executed successfully")
                    
            except Exception as e:
                print(f"Exception in statement {i}: {str(e)}")
                # Continue with next statement
                continue
        
        print("Migration execution completed!")
        
        # Verify tables were created
        print("\nVerifying created tables...")
        
        table_names = [
            'document_section_instances',
            'query_execution_results', 
            'normalization_applications',
            'business_rule_evaluations',
            'agent_prompt_applications',
            'workflow_stage_completions'
        ]
        
        for table_name in table_names:
            try:
                result = supabase_service.client.table(table_name).select('*').limit(1).execute()
                print(f"✓ Table '{table_name}' exists and accessible")
            except Exception as e:
                print(f"✗ Table '{table_name}' verification failed: {str(e)}")
        
    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_migration())