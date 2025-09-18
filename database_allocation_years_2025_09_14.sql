-- NMTC Allocation Years Management - Enhanced Flexible Hierarchy
-- Database Schema Addition - 2025-09-14
-- Predefined Years 2020-2024 with Flexible Document Hierarchy Support

-- 1. Create allocation years table (2020-2024 predefined)
CREATE TABLE IF NOT EXISTS allocation_years (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL, -- Organization context for security
    year INTEGER NOT NULL CHECK (year >= 2020 AND year <= 2024), -- Constrain to logical range
    total_amount DECIMAL(15,2) DEFAULT 0,
    deployed_amount DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'inactive', -- inactive/active/completed
    allocation_document_id UUID REFERENCES documents(id), -- Link to allocation agreement document
    processing_status VARCHAR(20) DEFAULT 'pending', -- pending/processing/completed/failed
    processing_results JSONB, -- Store core engine processing results
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(org_id, year)
);

-- 2. Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_allocation_years_org_year ON allocation_years(org_id, year);
CREATE INDEX IF NOT EXISTS idx_allocation_years_status ON allocation_years(status);

-- 3. Function to create predefined years for an organization (2020-2024)
CREATE OR REPLACE FUNCTION create_predefined_years_for_org(org_uuid UUID)
RETURNS TABLE(year_id UUID, year_created INTEGER) AS $$
BEGIN
    -- Insert predefined years 2020-2024 for the organization
    RETURN QUERY
    INSERT INTO allocation_years (org_id, year, status, processing_status)
    SELECT org_uuid, generate_series(2020, 2024), 'inactive', 'pending'
    ON CONFLICT (org_id, year) DO NOTHING
    RETURNING id, year;
END;
$$ LANGUAGE plpgsql;

-- 4. Create QALICB entities table (with org_id for security)
CREATE TABLE IF NOT EXISTS qalicb_entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    allocation_year_id UUID REFERENCES allocation_years(id) ON DELETE CASCADE,
    org_id UUID NOT NULL, -- IMPORTANT: Organization context for security/multi-tenancy
    organization_name VARCHAR(255) NOT NULL,
    business_address TEXT,
    business_type VARCHAR(100),
    expected_loan_amount DECIMAL(15,2),
    actual_loan_amount DECIMAL(15,2),
    census_tract VARCHAR(20),
    project_description TEXT,
    contact_information JSONB, -- Store contact details as JSON
    status VARCHAR(20) DEFAULT 'planning', -- planning, active, completed, cancelled
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
    -- Removed the composite foreign key constraint that was causing the error
);

-- 5. Create index for QALICB lookups
CREATE INDEX IF NOT EXISTS idx_qalicb_allocation_year ON qalicb_entities(allocation_year_id);
CREATE INDEX IF NOT EXISTS idx_qalicb_status ON qalicb_entities(status);

-- 6. Enhance documents table for flexible hierarchy linking
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS allocation_year_id UUID REFERENCES allocation_years(id),
ADD COLUMN IF NOT EXISTS qalicb_entity_id UUID REFERENCES qalicb_entities(id),
ADD COLUMN IF NOT EXISTS parent_document_id UUID REFERENCES documents(id), -- For future sub-document hierarchy
ADD COLUMN IF NOT EXISTS document_hierarchy_level INTEGER DEFAULT 0, -- 0=allocation, 1=qlici, 2=sub-docs
ADD COLUMN IF NOT EXISTS expected_amount DECIMAL(15,2),
ADD COLUMN IF NOT EXISTS validation_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS document_category VARCHAR(50) DEFAULT 'general'; -- allocation, qlici_loan, supporting, compliance

-- 7. Create indexes for document lookups and hierarchy
CREATE INDEX IF NOT EXISTS idx_documents_allocation_year ON documents(allocation_year_id);
CREATE INDEX IF NOT EXISTS idx_documents_qalicb ON documents(qalicb_entity_id);
CREATE INDEX IF NOT EXISTS idx_documents_parent ON documents(parent_document_id);
CREATE INDEX IF NOT EXISTS idx_documents_hierarchy_level ON documents(document_hierarchy_level);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(document_category);

-- 8. Enhanced function to get allocation year dashboard summary
CREATE OR REPLACE FUNCTION get_allocation_dashboard_summary(org_uuid UUID, target_year INTEGER)
RETURNS TABLE(
    year INTEGER,
    total_amount DECIMAL(15,2),
    deployed_amount DECIMAL(15,2),
    available_amount DECIMAL(15,2),
    qalicb_count INTEGER,
    document_count INTEGER,
    status VARCHAR(20),
    processing_status VARCHAR(20),
    processing_results JSONB,
    allocation_document_id UUID,
    has_allocation_agreement BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ay.year,
        ay.total_amount,
        ay.deployed_amount,
        (ay.total_amount - ay.deployed_amount) as available_amount,
        COALESCE(q.qalicb_count, 0)::INTEGER as qalicb_count,
        COALESCE(d.document_count, 0)::INTEGER as document_count,
        ay.status,
        ay.processing_status,
        ay.processing_results,
        ay.allocation_document_id,
        (ay.allocation_document_id IS NOT NULL) as has_allocation_agreement
    FROM allocation_years ay
    LEFT JOIN (
        SELECT allocation_year_id, COUNT(*) as qalicb_count
        FROM qalicb_entities
        WHERE org_id = org_uuid
        GROUP BY allocation_year_id
    ) q ON ay.id = q.allocation_year_id
    LEFT JOIN (
        SELECT allocation_year_id, COUNT(*) as document_count
        FROM documents
        WHERE allocation_year_id IS NOT NULL
        GROUP BY allocation_year_id
    ) d ON ay.id = d.allocation_year_id
    WHERE ay.org_id = org_uuid
    AND ay.year = target_year;
END;
$$ LANGUAGE plpgsql;

-- 9. Additional helper functions for QLICI management
CREATE OR REPLACE FUNCTION get_qalicb_entities_for_year(org_uuid UUID, target_year INTEGER)
RETURNS TABLE(
    qalicb_id UUID,
    organization_name VARCHAR(255),
    expected_loan_amount DECIMAL(15,2),
    actual_loan_amount DECIMAL(15,2),
    status VARCHAR(20),
    document_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        qe.id as qalicb_id,
        qe.organization_name,
        qe.expected_loan_amount,
        qe.actual_loan_amount,
        qe.status,
        COALESCE(d.document_count, 0)::INTEGER as document_count
    FROM qalicb_entities qe
    JOIN allocation_years ay ON qe.allocation_year_id = ay.id
    LEFT JOIN (
        SELECT qalicb_entity_id, COUNT(*) as document_count
        FROM documents
        WHERE qalicb_entity_id IS NOT NULL
        GROUP BY qalicb_entity_id
    ) d ON qe.id = d.qalicb_entity_id
    WHERE ay.org_id = org_uuid
    AND ay.year = target_year
    ORDER BY qe.created_at;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE allocation_years IS 'NMTC allocation years 2020-2024 with flexible document hierarchy support';
COMMENT ON TABLE qalicb_entities IS 'QALICB entities with org_id for security and multi-tenant access';
COMMENT ON FUNCTION create_predefined_years_for_org IS 'Creates predefined allocation years 2020-2024 for an organization';
COMMENT ON FUNCTION get_allocation_dashboard_summary IS 'Returns comprehensive dashboard data for allocation year including processing results';
COMMENT ON FUNCTION get_qalicb_entities_for_year IS 'Returns QLICI entities for specific year with document counts';

-- 9. Sample function to initialize predefined years for a new organization
CREATE OR REPLACE FUNCTION initialize_org_allocation_years(org_uuid UUID)
RETURNS SETOF allocation_years AS $$
BEGIN
    -- Create predefined years for the organization
    PERFORM create_predefined_years_for_org(org_uuid);

    -- Return all years for this organization
    RETURN QUERY
    SELECT * FROM allocation_years
    WHERE org_id = org_uuid
    ORDER BY year;
END;
$$ LANGUAGE plpgsql;

-- 10. Verify the schema changes
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('allocation_years', 'qalicb_entities', 'documents')
  AND column_name IN ('allocation_year_id', 'qalicb_entity_id', 'year', 'total_amount', 'organization_name')
ORDER BY table_name, column_name;