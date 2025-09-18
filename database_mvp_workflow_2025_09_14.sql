-- MVP ALLOCATION-YEAR-CENTRIC WORKFLOW
-- User-Driven Database Schema - 2025-09-14
-- Execute after allocation_years schema

-- 1. Create QLICI loans entity table
CREATE TABLE IF NOT EXISTS qlici_loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    allocation_year_id UUID NOT NULL REFERENCES allocation_years(id) ON DELETE CASCADE,
    org_id UUID NOT NULL,
    
    -- User-entered loan details (no auto-detect)
    loan_name VARCHAR(255) NOT NULL,
    loan_amount DECIMAL(15,2) NOT NULL,
    borrower_name VARCHAR(255) NOT NULL,
    project_description TEXT,
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'active',
    documents_count INTEGER DEFAULT 0,
    
    -- Audit fields
    created_by UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT qlici_loan_amount_positive CHECK (loan_amount > 0),
    CONSTRAINT qlici_status_valid CHECK (status IN ('active', 'completed', 'cancelled'))
);

-- 2. Update documents table for QLICI relationship
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS qlici_loan_id UUID REFERENCES qlici_loans(id) ON DELETE SET NULL;

-- 3. Update allocation_years with computed fields
ALTER TABLE allocation_years 
ADD COLUMN IF NOT EXISTS qlici_loans_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS documents_count INTEGER DEFAULT 0;

-- 4. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_qlici_loans_allocation_year ON qlici_loans(allocation_year_id);
CREATE INDEX IF NOT EXISTS idx_qlici_loans_org ON qlici_loans(org_id);
CREATE INDEX IF NOT EXISTS idx_documents_qlici_loan ON documents(qlici_loan_id);

-- 5. Create function to update allocation year deployed amount
CREATE OR REPLACE FUNCTION update_allocation_deployed_amount()
RETURNS TRIGGER AS $$
BEGIN
    -- Update deployed_amount in allocation_years table
    UPDATE allocation_years 
    SET deployed_amount = (
        SELECT COALESCE(SUM(loan_amount), 0) 
        FROM qlici_loans 
        WHERE allocation_year_id = COALESCE(NEW.allocation_year_id, OLD.allocation_year_id)
        AND status = 'active'
    ),
    qlici_loans_count = (
        SELECT COUNT(*) 
        FROM qlici_loans 
        WHERE allocation_year_id = COALESCE(NEW.allocation_year_id, OLD.allocation_year_id)
        AND status = 'active'
    ),
    updated_at = NOW()
    WHERE id = COALESCE(NEW.allocation_year_id, OLD.allocation_year_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- 6. Create triggers for automatic deployed amount updates
DROP TRIGGER IF EXISTS trg_qlici_loan_amount_update ON qlici_loans;
CREATE TRIGGER trg_qlici_loan_amount_update
    AFTER INSERT OR UPDATE OR DELETE ON qlici_loans
    FOR EACH ROW EXECUTE FUNCTION update_allocation_deployed_amount();

-- 7. Create function to update document counts
CREATE OR REPLACE FUNCTION update_document_counts()
RETURNS TRIGGER AS $$
BEGIN
    -- Update documents_count in qlici_loans
    IF NEW.qlici_loan_id IS NOT NULL THEN
        UPDATE qlici_loans 
        SET documents_count = (
            SELECT COUNT(*) 
            FROM documents 
            WHERE qlici_loan_id = NEW.qlici_loan_id
        )
        WHERE id = NEW.qlici_loan_id;
    END IF;
    
    -- Update documents_count in allocation_years
    IF NEW.allocation_year_id IS NOT NULL THEN
        UPDATE allocation_years 
        SET documents_count = (
            SELECT COUNT(*) 
            FROM documents 
            WHERE allocation_year_id = NEW.allocation_year_id
        )
        WHERE id = NEW.allocation_year_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 8. Create trigger for document count updates
DROP TRIGGER IF EXISTS trg_document_count_update ON documents;
CREATE TRIGGER trg_document_count_update
    AFTER INSERT OR UPDATE OR DELETE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_document_counts();

-- 9. Add comments for documentation
COMMENT ON TABLE qlici_loans IS 'QLICI loan entities created manually by users - no auto-detection';
COMMENT ON COLUMN qlici_loans.loan_name IS 'User-friendly name like "ABC Manufacturing Project"';
COMMENT ON COLUMN qlici_loans.loan_amount IS 'Loan amount entered manually by user';
COMMENT ON COLUMN qlici_loans.borrower_name IS 'Borrower company/entity name';
COMMENT ON COLUMN qlici_loans.project_description IS 'User description of the project';

COMMENT ON COLUMN documents.qlici_loan_id IS 'Links document to specific QLICI loan entity';
COMMENT ON COLUMN allocation_years.qlici_loans_count IS 'Auto-calculated count of QLICI loans';
COMMENT ON COLUMN allocation_years.documents_count IS 'Auto-calculated count of all documents';

-- 10. Insert sample data for testing (remove in production)
-- INSERT INTO allocation_years (org_id, year, total_amount, status, notes)
-- VALUES 
--   ('ce117b87-d75c-4c8a-b3f5-922ddec539b0', 2024, 50000000.00, 'active', 'Test 2024 allocation'),
--   ('ce117b87-d75c-4c8a-b3f5-922ddec539b0', 2023, 25000000.00, 'active', 'Test 2023 allocation');

-- 11. Verify the schema
SELECT 
    table_name, 
    column_name, 
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('qlici_loans', 'allocation_years', 'documents')
  AND column_name IN ('qlici_loan_id', 'allocation_year_id', 'loan_name', 'loan_amount', 'deployed_amount')
ORDER BY table_name, column_name;