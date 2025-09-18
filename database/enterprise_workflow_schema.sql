-- NMTC Platform Enterprise Workflow Orchestration Schema
-- Database schema for autonomous document processing workflow
-- January 17, 2025

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Master workflow orchestration table
CREATE TABLE IF NOT EXISTS workflow_jobs (
    job_id VARCHAR(20) PRIMARY KEY,              -- Human-readable: NMTC-2025-ABC123
    internal_uuid UUID UNIQUE DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    user_id UUID NOT NULL,
    job_type VARCHAR(50) NOT NULL DEFAULT 'allocation_processing',
    display_name VARCHAR(200) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,

    -- Status management
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent BETWEEN 0 AND 100),
    current_step VARCHAR(200),
    current_step_detail VARCHAR(500),

    -- Timing and estimation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    estimated_duration_minutes INTEGER DEFAULT 25,
    actual_duration_minutes INTEGER,

    -- Error handling and recovery
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_checkpoint VARCHAR(200),

    -- Input/Output data
    input_metadata JSONB,
    partial_results JSONB,
    final_results JSONB,

    -- Audit and compliance
    created_by UUID,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_status CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled', 'paused'))
);

-- Detailed step tracking for granular progress
CREATE TABLE IF NOT EXISTS workflow_steps (
    step_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(20) NOT NULL REFERENCES workflow_jobs(job_id) ON DELETE CASCADE,
    step_name VARCHAR(100) NOT NULL,
    step_display_name VARCHAR(200),
    step_order INTEGER NOT NULL,
    parent_step_id UUID REFERENCES workflow_steps(step_id),

    -- Step execution state
    status VARCHAR(20) DEFAULT 'pending',
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent BETWEEN 0 AND 100),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,

    -- Step-specific data and checkpoints
    step_input JSONB,
    step_output JSONB,
    checkpoint_data JSONB,
    error_details TEXT,

    -- Recovery information
    can_retry BOOLEAN DEFAULT TRUE,
    retry_count INTEGER DEFAULT 0,

    CONSTRAINT valid_step_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped'))
);

-- Enhanced document tracking with job relationships
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS job_id VARCHAR(20),
ADD COLUMN IF NOT EXISTS processing_status VARCHAR(50) DEFAULT 'uploaded',
ADD COLUMN IF NOT EXISTS job_created_at TIMESTAMP WITH TIME ZONE;

-- Add foreign key constraint if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_documents_job'
    ) THEN
        ALTER TABLE documents
        ADD CONSTRAINT fk_documents_job
        FOREIGN KEY (job_id) REFERENCES workflow_jobs(job_id) ON DELETE SET NULL;
    END IF;
END $$;

-- Event sourcing for complete audit trail
CREATE TABLE IF NOT EXISTS workflow_events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(20) NOT NULL REFERENCES workflow_jobs(job_id) ON DELETE CASCADE,
    step_id UUID REFERENCES workflow_steps(step_id) ON DELETE CASCADE,

    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(30) NOT NULL DEFAULT 'system',
    event_data JSONB,
    error_data JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,

    CONSTRAINT valid_event_category CHECK (event_category IN ('system', 'user', 'error', 'checkpoint'))
);

-- Resource management and queue optimization
CREATE TABLE IF NOT EXISTS processing_queue (
    queue_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(20) NOT NULL REFERENCES workflow_jobs(job_id) ON DELETE CASCADE,
    queue_position INTEGER,
    estimated_start_time TIMESTAMP WITH TIME ZONE,
    resource_requirements JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance and analytics tracking
CREATE TABLE IF NOT EXISTS job_performance_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(20) NOT NULL REFERENCES workflow_jobs(job_id) ON DELETE CASCADE,

    -- Performance data
    total_pages_processed INTEGER,
    azure_ocr_cost_usd DECIMAL(10,4),
    core_engine_tokens_used INTEGER,
    processing_efficiency_score DECIMAL(5,2),

    -- Resource utilization
    peak_memory_mb INTEGER,
    total_api_calls INTEGER,
    error_recovery_count INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI Processing Results Storage
CREATE TABLE IF NOT EXISTS ai_processing_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id VARCHAR(20) NOT NULL REFERENCES workflow_jobs(job_id) ON DELETE CASCADE,

    -- Agent results
    classification_result JSONB,
    extraction_result JSONB,
    analysis_result JSONB,

    -- Processing metadata
    classification_confidence DECIMAL(3,2),
    extraction_confidence DECIMAL(3,2),
    analysis_confidence DECIMAL(3,2),
    overall_confidence DECIMAL(3,2),

    -- AI service metadata
    ai_provider VARCHAR(50),
    model_used VARCHAR(100),
    total_tokens_used INTEGER,
    total_cost_usd DECIMAL(10,4),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_workflow_jobs_org_id ON workflow_jobs(org_id);
CREATE INDEX IF NOT EXISTS idx_workflow_jobs_user_id ON workflow_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_jobs_status ON workflow_jobs(status);
CREATE INDEX IF NOT EXISTS idx_workflow_jobs_created_at ON workflow_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_workflow_jobs_job_type ON workflow_jobs(job_type);

CREATE INDEX IF NOT EXISTS idx_workflow_steps_job_id ON workflow_steps(job_id);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_status ON workflow_steps(status);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_step_order ON workflow_steps(job_id, step_order);

CREATE INDEX IF NOT EXISTS idx_workflow_events_job_id ON workflow_events(job_id);
CREATE INDEX IF NOT EXISTS idx_workflow_events_created_at ON workflow_events(created_at);
CREATE INDEX IF NOT EXISTS idx_workflow_events_event_type ON workflow_events(event_type);

CREATE INDEX IF NOT EXISTS idx_documents_job_id ON documents(job_id);
CREATE INDEX IF NOT EXISTS idx_documents_processing_status ON documents(processing_status);

CREATE INDEX IF NOT EXISTS idx_processing_queue_created_at ON processing_queue(created_at);
CREATE INDEX IF NOT EXISTS idx_processing_queue_queue_position ON processing_queue(queue_position);

-- Create function for updating workflow job timestamps
CREATE OR REPLACE FUNCTION update_workflow_job_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS trigger_update_workflow_job_timestamp ON workflow_jobs;
CREATE TRIGGER trigger_update_workflow_job_timestamp
    BEFORE UPDATE ON workflow_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_workflow_job_timestamp();

-- Function to generate human-readable job IDs
CREATE OR REPLACE FUNCTION generate_job_id(org_prefix VARCHAR DEFAULT 'NMTC')
RETURNS VARCHAR AS $$
DECLARE
    year_part VARCHAR := TO_CHAR(CURRENT_DATE, 'YYYY');
    random_part VARCHAR := UPPER(LEFT(MD5(RANDOM()::TEXT), 6));
    job_id VARCHAR;
BEGIN
    job_id := org_prefix || '-' || year_part || '-' || random_part;

    -- Ensure uniqueness
    WHILE EXISTS (SELECT 1 FROM workflow_jobs WHERE workflow_jobs.job_id = job_id) LOOP
        random_part := UPPER(LEFT(MD5(RANDOM()::TEXT), 6));
        job_id := org_prefix || '-' || year_part || '-' || random_part;
    END LOOP;

    RETURN job_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get active jobs for organization
CREATE OR REPLACE FUNCTION get_active_jobs_for_org(org_uuid UUID)
RETURNS TABLE (
    job_id VARCHAR,
    display_name VARCHAR,
    status VARCHAR,
    progress_percent INTEGER,
    current_step VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE,
    estimated_completion TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        wj.job_id,
        wj.display_name,
        wj.status,
        wj.progress_percent,
        wj.current_step,
        wj.created_at,
        wj.created_at + (wj.estimated_duration_minutes || ' minutes')::INTERVAL as estimated_completion
    FROM workflow_jobs wj
    WHERE wj.org_id = org_uuid
    AND wj.status IN ('queued', 'running')
    ORDER BY wj.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get job status with step details
CREATE OR REPLACE FUNCTION get_job_status_details(job_uuid VARCHAR)
RETURNS TABLE (
    job_info JSONB,
    steps_info JSONB,
    recent_events JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        -- Job information
        jsonb_build_object(
            'job_id', wj.job_id,
            'status', wj.status,
            'progress_percent', wj.progress_percent,
            'current_step', wj.current_step,
            'current_step_detail', wj.current_step_detail,
            'created_at', wj.created_at,
            'started_at', wj.started_at,
            'estimated_completion', wj.created_at + (wj.estimated_duration_minutes || ' minutes')::INTERVAL,
            'display_name', wj.display_name,
            'original_filename', wj.original_filename,
            'error_message', wj.error_message,
            'retry_count', wj.retry_count
        ) as job_info,

        -- Steps information
        COALESCE(
            jsonb_agg(
                jsonb_build_object(
                    'step_name', ws.step_name,
                    'step_display_name', ws.step_display_name,
                    'status', ws.status,
                    'progress_percent', ws.progress_percent,
                    'started_at', ws.started_at,
                    'completed_at', ws.completed_at,
                    'duration_seconds', ws.duration_seconds,
                    'error_details', ws.error_details
                ) ORDER BY ws.step_order
            ),
            '[]'::jsonb
        ) as steps_info,

        -- Recent events
        COALESCE(
            (SELECT jsonb_agg(
                jsonb_build_object(
                    'event_type', we.event_type,
                    'event_category', we.event_category,
                    'created_at', we.created_at,
                    'event_data', we.event_data
                ) ORDER BY we.created_at DESC
            )
            FROM workflow_events we
            WHERE we.job_id = job_uuid
            LIMIT 10),
            '[]'::jsonb
        ) as recent_events

    FROM workflow_jobs wj
    LEFT JOIN workflow_steps ws ON wj.job_id = ws.job_id
    WHERE wj.job_id = job_uuid
    GROUP BY wj.job_id, wj.status, wj.progress_percent, wj.current_step,
             wj.current_step_detail, wj.created_at, wj.started_at,
             wj.estimated_duration_minutes, wj.display_name,
             wj.original_filename, wj.error_message, wj.retry_count;
END;
$$ LANGUAGE plpgsql;

-- Create sample data for testing (commented out for production)
/*
-- Insert sample workflow job
INSERT INTO workflow_jobs (
    job_id, org_id, user_id, display_name, original_filename,
    status, progress_percent, current_step
) VALUES (
    'NMTC-2025-TEST01',
    uuid_generate_v4(),
    uuid_generate_v4(),
    'Test Allocation Agreement 2024',
    'allocation_agreement_2024.pdf',
    'running',
    45,
    'azure_ocr_processing'
);
*/

-- Grant permissions (adjust as needed for your application user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nmtc_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nmtc_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO nmtc_app_user;

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES ('1.0.0', 'Initial enterprise workflow orchestration schema')
ON CONFLICT (version) DO NOTHING;

-- Add comments for documentation
COMMENT ON TABLE workflow_jobs IS 'Master table for workflow orchestration - tracks all long-running document processing jobs';
COMMENT ON TABLE workflow_steps IS 'Detailed step tracking for granular progress monitoring and recovery';
COMMENT ON TABLE workflow_events IS 'Event sourcing table for complete audit trail and compliance';
COMMENT ON TABLE processing_queue IS 'Queue management for resource optimization and job prioritization';
COMMENT ON TABLE job_performance_metrics IS 'Performance analytics and cost tracking';
COMMENT ON TABLE ai_processing_results IS 'Storage for AI agent results and confidence scores';

COMMENT ON COLUMN workflow_jobs.job_id IS 'Human-readable job identifier (NMTC-2025-ABC123)';
COMMENT ON COLUMN workflow_jobs.status IS 'Current job status: queued, running, completed, failed, cancelled, paused';
COMMENT ON COLUMN workflow_jobs.progress_percent IS 'Overall job progress percentage (0-100)';
COMMENT ON COLUMN workflow_jobs.last_checkpoint IS 'Last successful checkpoint for recovery';
COMMENT ON COLUMN workflow_jobs.partial_results IS 'Intermediate results available during processing';
COMMENT ON COLUMN workflow_jobs.final_results IS 'Complete results after job completion';

-- Success message
SELECT 'Enterprise workflow orchestration schema created successfully!' as status;