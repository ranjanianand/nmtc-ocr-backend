-- NMTC Document Type Selection Implementation
-- Database Schema Updates - 2025-09-14
-- Execute these commands in Supabase SQL editor

-- Add optional description field to documents table
ALTER TABLE documents 
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS user_selected_type BOOLEAN DEFAULT FALSE;

-- Add index for better performance on document_type_id lookups
CREATE INDEX IF NOT EXISTS idx_documents_document_type_id ON documents(document_type_id);

-- Add index for user_selected_type filtering
CREATE INDEX IF NOT EXISTS idx_documents_user_selected_type ON documents(user_selected_type);

-- Update existing documents to mark them as AI-detected (retroactive)
UPDATE documents 
SET user_selected_type = FALSE 
WHERE user_selected_type IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN documents.description IS 'Optional user-provided description or notes about the document';
COMMENT ON COLUMN documents.user_selected_type IS 'TRUE if user manually selected document type, FALSE if AI-detected';

-- Verify the changes
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'documents' 
  AND column_name IN ('description', 'user_selected_type')
ORDER BY column_name;