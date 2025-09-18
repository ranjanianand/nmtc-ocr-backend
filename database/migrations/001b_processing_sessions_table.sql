-- Processing Sessions Table
-- Required base table for the workflow enhancement system

-- Processing Sessions - Track complete document processing workflows
CREATE TABLE public.processing_sessions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL,
    user_id uuid,
    org_id uuid NOT NULL,
    session_type text NOT NULL DEFAULT 'full_pipeline', -- 'full_pipeline', 'quick_detection', 'validation_only'
    status text NOT NULL DEFAULT 'queued', -- 'queued', 'stage_0a_running', 'awaiting_confirmation', 'core_pipeline_running', 'completed', 'failed', 'cancelled'
    current_stage text, -- Current processing stage name
    progress_percentage integer NOT NULL DEFAULT 0, -- 0-100
    priority integer NOT NULL DEFAULT 100, -- Higher number = higher priority
    configuration jsonb DEFAULT '{}', -- Session configuration options
    metadata jsonb DEFAULT '{}', -- Session metadata and progress details
    error_details jsonb, -- Error information if failed
    error_count integer NOT NULL DEFAULT 0, -- Number of errors encountered
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    expires_at timestamp with time zone, -- Session expiration time
    
    CONSTRAINT processing_sessions_pkey PRIMARY KEY (id),
    CONSTRAINT processing_sessions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE,
    CONSTRAINT processing_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id),
    CONSTRAINT processing_sessions_progress_range CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    CONSTRAINT processing_sessions_priority_range CHECK (priority >= 1 AND priority <= 1000)
);

-- Agent Pipeline States - Track individual agent execution within sessions
CREATE TABLE public.agent_pipeline_states (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    agent_key text NOT NULL, -- 'agent_1_analyzer', 'agent_2_risk', 'agent_3_reports'
    status text NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed', 'cancelled'
    progress_percentage integer NOT NULL DEFAULT 0, -- 0-100
    confidence_score numeric(5,4), -- Overall confidence in agent results (0.0000 to 1.0000)
    input_data jsonb, -- Input data provided to agent
    output_data jsonb, -- Agent's output results
    error_details jsonb, -- Error information if failed
    quality_metrics jsonb, -- Quality assessment metrics
    execution_order integer NOT NULL DEFAULT 1, -- Order of execution (1, 2, 3...)
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    metadata jsonb DEFAULT '{}',
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT agent_pipeline_states_pkey PRIMARY KEY (id),
    CONSTRAINT agent_pipeline_states_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT agent_pipeline_states_unique_agent_per_session UNIQUE (session_id, agent_key),
    CONSTRAINT agent_pipeline_states_progress_range CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    CONSTRAINT agent_pipeline_states_confidence_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)
);

-- Background Jobs Queue - Track asynchronous processing jobs
CREATE TABLE public.background_jobs (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    job_type text NOT NULL, -- 'document_processing', 'report_generation', 'data_extraction'
    job_key text NOT NULL, -- Unique job identifier
    status text NOT NULL DEFAULT 'queued', -- 'queued', 'running', 'completed', 'failed', 'cancelled'
    priority integer NOT NULL DEFAULT 100, -- Higher number = higher priority
    input_parameters jsonb NOT NULL, -- Job input parameters
    output_results jsonb, -- Job output results
    error_details jsonb, -- Error information if failed
    retry_count integer NOT NULL DEFAULT 0, -- Number of retry attempts
    max_retries integer NOT NULL DEFAULT 3, -- Maximum retry attempts
    worker_id text, -- ID of worker processing this job
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    expires_at timestamp with time zone, -- Job expiration time
    metadata jsonb DEFAULT '{}',
    
    CONSTRAINT background_jobs_pkey PRIMARY KEY (id),
    CONSTRAINT background_jobs_unique_key UNIQUE (job_key),
    CONSTRAINT background_jobs_priority_range CHECK (priority >= 1 AND priority <= 1000),
    CONSTRAINT background_jobs_retry_count_check CHECK (retry_count >= 0 AND retry_count <= max_retries)
);

-- Agent Processing Logs - Detailed logging for agent execution
CREATE TABLE public.agent_processing_logs (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    agent_key text NOT NULL, -- Which agent generated this log
    log_level text NOT NULL, -- 'debug', 'info', 'warning', 'error', 'critical'
    log_message text NOT NULL, -- Human-readable log message
    processing_step text, -- Which step in processing generated this log
    log_data jsonb, -- Structured log data
    timestamp timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT agent_processing_logs_pkey PRIMARY KEY (id),
    CONSTRAINT agent_processing_logs_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_processing_sessions_document_id ON public.processing_sessions(document_id);
CREATE INDEX idx_processing_sessions_user_id ON public.processing_sessions(user_id);
CREATE INDEX idx_processing_sessions_org_id ON public.processing_sessions(org_id);
CREATE INDEX idx_processing_sessions_status ON public.processing_sessions(status);
CREATE INDEX idx_processing_sessions_priority ON public.processing_sessions(priority);
CREATE INDEX idx_processing_sessions_created_at ON public.processing_sessions(created_at);

CREATE INDEX idx_agent_pipeline_states_session_id ON public.agent_pipeline_states(session_id);
CREATE INDEX idx_agent_pipeline_states_agent_key ON public.agent_pipeline_states(agent_key);
CREATE INDEX idx_agent_pipeline_states_status ON public.agent_pipeline_states(status);

CREATE INDEX idx_background_jobs_job_type ON public.background_jobs(job_type);
CREATE INDEX idx_background_jobs_status ON public.background_jobs(status);
CREATE INDEX idx_background_jobs_priority ON public.background_jobs(priority);
CREATE INDEX idx_background_jobs_created_at ON public.background_jobs(created_at);

CREATE INDEX idx_agent_processing_logs_session_id ON public.agent_processing_logs(session_id);
CREATE INDEX idx_agent_processing_logs_agent_key ON public.agent_processing_logs(agent_key);
CREATE INDEX idx_agent_processing_logs_log_level ON public.agent_processing_logs(log_level);
CREATE INDEX idx_agent_processing_logs_timestamp ON public.agent_processing_logs(timestamp);

-- Enable Row Level Security
ALTER TABLE public.processing_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_pipeline_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.background_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_processing_logs ENABLE ROW LEVEL SECURITY;

-- RLS policies for organization-based access
CREATE POLICY "Users can view their organization's processing sessions" ON public.processing_sessions
    FOR SELECT USING (org_id = (auth.jwt() ->> 'organization_id')::uuid);

CREATE POLICY "Users can view their organization's agent states" ON public.agent_pipeline_states
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps 
            WHERE ps.id = agent_pipeline_states.session_id 
            AND ps.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's background jobs" ON public.background_jobs
    FOR SELECT USING (
        (input_parameters ->> 'org_id')::uuid = (auth.jwt() ->> 'organization_id')::uuid
    );

CREATE POLICY "Users can view their organization's processing logs" ON public.agent_processing_logs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps 
            WHERE ps.id = agent_processing_logs.session_id 
            AND ps.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

-- Comments for documentation
COMMENT ON TABLE public.processing_sessions IS 'Tracks complete document processing workflows from upload to completion';
COMMENT ON TABLE public.agent_pipeline_states IS 'Tracks individual agent execution within processing sessions';
COMMENT ON TABLE public.background_jobs IS 'Queue for asynchronous processing jobs';
COMMENT ON TABLE public.agent_processing_logs IS 'Detailed logging for agent execution and debugging';