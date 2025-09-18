#!/usr/bin/env python3
"""
Create the workflow enhancement tables directly using psycopg2
"""

import os
from app.core.config import settings

def get_connection_string():
    """Get PostgreSQL connection string from Supabase settings"""
    # Extract database details from Supabase URL
    supabase_url = settings.SUPABASE_URL
    supabase_key = settings.SUPABASE_KEY
    
    print(f"Supabase URL: {supabase_url}")
    print(f"Supabase Key: {supabase_key[:20]}...")
    
    # For direct database access, we need the connection string
    # Usually in format: postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
    
    print("\n" + "="*60)
    print("DATABASE MIGRATION INSTRUCTIONS")
    print("="*60)
    print("\nSince we can't execute DDL through Supabase REST API,")
    print("please run the migration manually using one of these methods:\n")
    
    print("METHOD 1: Supabase Dashboard SQL Editor")
    print("-" * 40)
    print("1. Go to https://supabase.com/dashboard/project/[YOUR-PROJECT]/sql")
    print("2. Copy and paste the SQL from: database/migrations/003_workflow_enhancement_tables.sql")
    print("3. Click 'Run' to execute the migration")
    
    print("\nMETHOD 2: Direct PostgreSQL Connection")
    print("-" * 40)
    print("1. Get your database connection string from Supabase Dashboard > Settings > Database")
    print("2. Use psql or any PostgreSQL client:")
    print("   psql 'postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres'")
    print("3. Run the migration SQL file")
    
    print("\nMETHOD 3: Python with psycopg2 (if you have the connection string)")
    print("-" * 40)
    print("1. Install: pip install psycopg2-binary")
    print("2. Update this script with your connection string")
    print("3. Run this script")
    
    print("\n" + "="*60)
    
    # Read and display the migration SQL
    migration_file = "database/migrations/003_workflow_enhancement_tables.sql"
    if os.path.exists(migration_file):
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print(f"\nMIGRATION SQL TO EXECUTE ({len(migration_sql)} characters):")
        print("-" * 60)
        print(migration_sql[:500] + "..." if len(migration_sql) > 500 else migration_sql)
        print("-" * 60)
    else:
        print(f"\nERROR: Migration file not found: {migration_file}")

def try_psycopg2_method():
    """Try to use psycopg2 if available and connection string is provided"""
    try:
        import psycopg2
        
        # You need to replace this with your actual Supabase PostgreSQL connection string
        # Get it from: Supabase Dashboard > Settings > Database > Connection string > URI
        CONNECTION_STRING = None  # "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
        
        if not CONNECTION_STRING:
            print("\nTo use direct PostgreSQL connection:")
            print("1. Get your connection string from Supabase Dashboard")
            print("2. Update CONNECTION_STRING in this script")
            print("3. Run this script again")
            return False
        
        print("Connecting to PostgreSQL...")
        conn = psycopg2.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        
        # Read migration file
        migration_file = "database/migrations/003_workflow_enhancement_tables.sql"
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("Executing migration...")
        cursor.execute(migration_sql)
        conn.commit()
        
        print("Migration completed successfully!")
        
        # Verify tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN (
                'document_section_instances',
                'query_execution_results',
                'normalization_applications', 
                'business_rule_evaluations',
                'agent_prompt_applications',
                'workflow_stage_completions'
            )
        """)
        
        tables = cursor.fetchall()
        print(f"\nCreated tables: {[t[0] for t in tables]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except ImportError:
        print("\npsycopg2 not installed. To install:")
        print("pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"\nPostgreSQL connection failed: {e}")
        return False

if __name__ == "__main__":
    print("NMTC Workflow Enhancement Tables Migration")
    print("=" * 50)
    
    # Try direct PostgreSQL connection first
    if not try_psycopg2_method():
        # Fall back to manual instructions
        get_connection_string()