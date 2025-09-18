#!/usr/bin/env python3
"""
Apply Allocation Years Database Schema
"""

import sys
sys.path.append('.')

from app.services.supabase_service import supabase_service

def apply_allocation_schema():
    """Apply the allocation years database schema"""
    try:
        print("Applying Allocation Years Database Schema...")
        print("=" * 60)

        # Read the SQL schema file
        with open('database_allocation_years_2025_09_14.sql', 'r') as f:
            schema_sql = f.read()

        # Split into individual statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

        print(f"Found {len(statements)} SQL statements to execute")

        success_count = 0
        error_count = 0

        for i, statement in enumerate(statements, 1):
            if not statement.strip():
                continue

            try:
                print(f"Executing statement {i}...")

                # Special handling for different statement types
                if 'CREATE TABLE' in statement.upper():
                    table_name = statement.split('CREATE TABLE')[1].split('IF NOT EXISTS')[1].split('(')[0].strip() if 'IF NOT EXISTS' in statement else statement.split('CREATE TABLE')[1].split('(')[0].strip()
                    print(f"  Creating table: {table_name}")
                elif 'CREATE INDEX' in statement.upper():
                    index_name = statement.split('CREATE INDEX')[1].split('IF NOT EXISTS')[1].split('ON')[0].strip() if 'IF NOT EXISTS' in statement else statement.split('CREATE INDEX')[1].split('ON')[0].strip()
                    print(f"  Creating index: {index_name}")
                elif 'CREATE OR REPLACE FUNCTION' in statement.upper():
                    func_name = statement.split('CREATE OR REPLACE FUNCTION')[1].split('(')[0].strip()
                    print(f"  Creating function: {func_name}")
                elif 'ALTER TABLE' in statement.upper():
                    print(f"  Altering table structure")
                elif 'COMMENT ON' in statement.upper():
                    print(f"  Adding comment")

                # Execute the statement
                result = supabase_service.client.rpc('query', {'sql': statement}).execute()

                if result.data is not None:
                    print(f"  ✓ SUCCESS")
                    success_count += 1
                else:
                    print(f"  ⚠ WARNING: No data returned")
                    success_count += 1

            except Exception as e:
                print(f"  ✗ ERROR: {e}")
                error_count += 1
                # Continue with next statement
                continue

        print()
        print("=" * 60)
        print(f"Schema Application Complete!")
        print(f"✓ Successful statements: {success_count}")
        print(f"✗ Failed statements: {error_count}")
        print(f"Total statements: {len([s for s in statements if s.strip()])}")

        # Test the schema by checking if tables exist
        print()
        print("Verifying schema application...")

        try:
            # Test allocation_years table
            result = supabase_service.client.table('allocation_years').select('*').limit(1).execute()
            print("✓ allocation_years table accessible")
        except Exception as e:
            print(f"✗ allocation_years table error: {e}")

        try:
            # Test qalicb_entities table
            result = supabase_service.client.table('qalicb_entities').select('*').limit(1).execute()
            print("✓ qalicb_entities table accessible")
        except Exception as e:
            print(f"✗ qalicb_entities table error: {e}")

        try:
            # Test function
            result = supabase_service.client.rpc('initialize_org_allocation_years', {'org_uuid': 'test-uuid'}).execute()
            print("✓ initialize_org_allocation_years function working")
        except Exception as e:
            print(f"✗ initialize_org_allocation_years function error: {e}")

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    apply_allocation_schema()