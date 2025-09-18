-- Migration: Add processing_results column for purpose-driven metadata flow
-- Date: 2025-01-13
-- Description: Simplified single JSONB column to store all processing results

-- Add the processing_results column
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS processing_results JSONB;

-- Add comment for documentation
COMMENT ON COLUMN documents.processing_results IS 'Complete processing results including stages, LLM extraction, core processing, and metadata';

-- Add GIN index for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_documents_processing_results
ON documents USING GIN (processing_results);

-- Add index for processing stage queries
CREATE INDEX IF NOT EXISTS idx_documents_processing_stage
ON documents ((processing_results->'stages'->>'current_stage'));

-- Add index for document type and processing status combination
CREATE INDEX IF NOT EXISTS idx_documents_category_processing
ON documents(document_category, ((processing_results->'stages'->>'current_stage')));

-- Update user_selected_type default for new flow
ALTER TABLE documents
ALTER COLUMN user_selected_type SET DEFAULT true;

-- Add sample data structure comment
COMMENT ON COLUMN documents.processing_results IS 'JSONB structure:
{
  "stages": {
    "upload": {"status": "completed", "timestamp": "2025-01-13T10:00:00Z"},
    "ocr": {"status": "completed", "timestamp": "2025-01-13T10:00:15Z", "text_length": 15000},
    "llm_extraction": {"status": "completed", "timestamp": "2025-01-13T10:00:25Z"},
    "core_processing": {"status": "pending"},
    "current_stage": "core_processing"
  },
  "llm_results": {
    "allocation_amount": 5000000,
    "cde_name": "Community Development Financial Institution",
    "compliance_period_years": 7,
    "extracted_timestamp": "2025-01-13T10:00:25Z"
  },
  "core_results": {
    "validated_data": {...},
    "compliance_scores": {"overall": 95, "substantially_all": "passed"},
    "business_metrics": {"utilization_rate": 0.85},
    "validation_errors": []
  },
  "metadata": {
    "processing_version": "2.0",
    "document_type": "allocation_agreement",
    "confidence_level": "high"
  }
}';