#!/usr/bin/env python3
"""
Manually create allocation years tables using Supabase client
"""

import sys
sys.path.append('.')

from app.services.supabase_service import supabase_service

def create_allocation_tables_manual():
    """Create allocation tables manually by direct table operations"""
    try:
        print("Creating Allocation Years tables manually...")
        print("=" * 60)

        # Since we can't execute raw SQL, let's try a different approach
        # Let's check if we can create some test data first to see table structure

        print("Checking existing table structures...")

        # Check documents table structure
        try:
            result = supabase_service.client.table('documents').select('*').limit(1).execute()
            print("✓ documents table exists")
            print(f"Documents table columns: {list(result.data[0].keys()) if result.data else 'empty table'}")
        except Exception as e:
            print(f"documents table error: {e}")

        # Check if allocation_years table exists
        try:
            result = supabase_service.client.table('allocation_years').select('*').limit(1).execute()
            print("✓ allocation_years table already exists!")
            print(f"Allocation years columns: {list(result.data[0].keys()) if result.data else 'empty table'}")
            return True
        except Exception as e:
            print(f"allocation_years table doesn't exist: {e}")

        # Check if qalicb_entities table exists
        try:
            result = supabase_service.client.table('qalicb_entities').select('*').limit(1).execute()
            print("✓ qalicb_entities table already exists!")
            print(f"QALICB entities columns: {list(result.data[0].keys()) if result.data else 'empty table'}")
        except Exception as e:
            print(f"qalicb_entities table doesn't exist: {e}")

        print()
        print("=" * 60)
        print("NEXT STEPS:")
        print("1. The database schema needs to be applied through Supabase SQL Editor")
        print("2. Go to your Supabase project dashboard")
        print("3. Navigate to SQL Editor")
        print("4. Copy and paste the contents of 'database_allocation_years_2025_09_14.sql'")
        print("5. Execute the SQL to create tables and functions")
        print("6. Then run the API tests again")
        print()
        print("Alternatively, I can show you the essential table structures to create manually.")

        return False

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_essential_sql():
    """Show the essential SQL needed"""
    print("\n" + "=" * 60)
    print("ESSENTIAL SQL TO RUN IN SUPABASE SQL EDITOR:")
    print("=" * 60)

    essential_sql = """
-- 1. Create allocation_years table
CREATE TABLE IF NOT EXISTS allocation_years (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL,
    year INTEGER NOT NULL CHECK (year >= 2020 AND year <= 2024),
    total_amount DECIMAL(15,2) DEFAULT 0,
    deployed_amount DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'inactive',
    allocation_document_id UUID REFERENCES documents(id),
    processing_status VARCHAR(20) DEFAULT 'pending',
    processing_results JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, year)
);

-- 2. Create qalicb_entities table
CREATE TABLE IF NOT EXISTS qalicb_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    allocation_year_id UUID REFERENCES allocation_years(id) ON DELETE CASCADE,
    org_id UUID NOT NULL,
    organization_name VARCHAR(255) NOT NULL,
    business_address TEXT,
    business_type VARCHAR(100),
    expected_loan_amount DECIMAL(15,2),
    actual_loan_amount DECIMAL(15,2),
    census_tract VARCHAR(20),
    project_description TEXT,
    contact_information JSONB,
    status VARCHAR(20) DEFAULT 'planning',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. Add columns to documents table
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS allocation_year_id UUID REFERENCES allocation_years(id),
ADD COLUMN IF NOT EXISTS qalicb_entity_id UUID REFERENCES qalicb_entities(id),
ADD COLUMN IF NOT EXISTS parent_document_id UUID REFERENCES documents(id),
ADD COLUMN IF NOT EXISTS document_hierarchy_level INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS expected_amount DECIMAL(15,2),
ADD COLUMN IF NOT EXISTS validation_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS document_category VARCHAR(50) DEFAULT 'general';

-- 4. Create basic indexes
CREATE INDEX IF NOT EXISTS idx_allocation_years_org_year ON allocation_years(org_id, year);
CREATE INDEX IF NOT EXISTS idx_qalicb_allocation_year ON qalicb_entities(allocation_year_id);
CREATE INDEX IF NOT EXISTS idx_documents_allocation_year ON documents(allocation_year_id);

-- 5. Function to initialize predefined years
CREATE OR REPLACE FUNCTION initialize_org_allocation_years(org_uuid UUID)
RETURNS SETOF allocation_years AS $$
BEGIN
    -- Create predefined years 2020-2024 for the organization
    INSERT INTO allocation_years (org_id, year, status, processing_status)
    SELECT org_uuid, generate_series(2020, 2024), 'inactive', 'pending'
    ON CONFLICT (org_id, year) DO NOTHING;

    -- Return all years for this organization
    RETURN QUERY
    SELECT * FROM allocation_years
    WHERE org_id = org_uuid
    ORDER BY year;
END;
$$ LANGUAGE plpgsql;
"""

    print(essential_sql)
    print("=" * 60)

if __name__ == '__main__':
    success = create_allocation_tables_manual()
    if not success:
        show_essential_sql()