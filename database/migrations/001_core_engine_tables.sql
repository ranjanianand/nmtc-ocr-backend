-- NMTC Core Engine Database Schema - Enterprise Tables
-- Author: Database Architect Agent
-- Purpose: Enterprise-grade processing sessions, agent states, and background jobs

-- 1. Custom Types for Processing States
CREATE TYPE processing_session_status AS ENUM (
    'queued',
    'starting',
    'stage_0a_running',
    'awaiting_confirmation',
    'core_pipeline_running', 
    'completed',
    'failed',
    'cancelled',
    'timeout'
);

CREATE TYPE agent_stage_status AS ENUM (
    'pending',
    'running',
    'completed',
    'failed',
    'skipped',
    'requires_input'
);

CREATE TYPE job_status AS ENUM (
    'queued',
    'running',
    'completed',
    'failed',
    'cancelled',
    'timeout',
    'retry_scheduled'
);

-- 2. Processing Sessions Table - Core session management
CREATE TABLE public.processing_sessions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL,
    user_id uuid,
    org_id uuid NOT NULL,
    session_type text NOT NULL DEFAULT 'full_pipeline', -- 'stage_0a', 'core_pipeline', 'full_pipeline'
    status processing_session_status NOT NULL DEFAULT 'queued',
    current_stage text NOT NULL DEFAULT 'uploaded',
    progress_percentage integer NOT NULL DEFAULT 0,
    estimated_completion_time timestamp with time zone,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    last_heartbeat timestamp with time zone NOT NULL DEFAULT now(),
    error_count integer NOT NULL DEFAULT 0,
    max_retry_attempts integer NOT NULL DEFAULT 3,
    priority integer NOT NULL DEFAULT 100, -- Lower number = higher priority
    configuration jsonb DEFAULT '{}',
    metadata jsonb DEFAULT '{}',
    
    CONSTRAINT processing_sessions_pkey PRIMARY KEY (id),
    CONSTRAINT processing_sessions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE,
    CONSTRAINT processing_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id),
    CONSTRAINT processing_sessions_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id),
    CONSTRAINT progress_percentage_range CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    CONSTRAINT priority_range CHECK (priority >= 1 AND priority <= 1000)
);

-- 3. Agent Pipeline States Table - Track individual agent execution
CREATE TABLE public.agent_pipeline_states (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    agent_key text NOT NULL, -- 'agent_1_analyzer', 'agent_2_risk', 'agent_3_reports'
    stage_order integer NOT NULL,
    status agent_stage_status NOT NULL DEFAULT 'pending',
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    progress_percentage integer NOT NULL DEFAULT 0,
    input_data jsonb DEFAULT '{}',
    output_data jsonb DEFAULT '{}',
    error_details jsonb,
    retry_count integer NOT NULL DEFAULT 0,
    processing_duration_ms bigint,
    confidence_score numeric(5,4),
    quality_metrics jsonb DEFAULT '{}',
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT agent_pipeline_states_pkey PRIMARY KEY (id),
    CONSTRAINT agent_pipeline_states_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT agent_pipeline_states_unique_session_agent UNIQUE (session_id, agent_key),
    CONSTRAINT agent_progress_range CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    CONSTRAINT stage_order_range CHECK (stage_order >= 1 AND stage_order <= 10),
    CONSTRAINT confidence_score_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)
);

-- 4. Background Jobs Table - Enterprise job queue management
CREATE TABLE public.background_jobs (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    job_type text NOT NULL, -- 'document_upload', 'ocr_processing', 'agent_execution', 'report_generation'
    job_key text NOT NULL, -- Unique identifier for job deduplication
    parent_session_id uuid,
    status job_status NOT NULL DEFAULT 'queued',
    priority integer NOT NULL DEFAULT 100,
    scheduled_at timestamp with time zone NOT NULL DEFAULT now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    max_retry_attempts integer NOT NULL DEFAULT 3,
    retry_count integer NOT NULL DEFAULT 0,
    retry_delay_seconds integer NOT NULL DEFAULT 300,
    timeout_seconds integer NOT NULL DEFAULT 1800, -- 30 minutes default
    worker_id text,
    input_parameters jsonb NOT NULL DEFAULT '{}',
    output_results jsonb DEFAULT '{}',
    error_details jsonb,
    progress_info jsonb DEFAULT '{}',
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT background_jobs_pkey PRIMARY KEY (id),
    CONSTRAINT background_jobs_parent_session_fkey FOREIGN KEY (parent_session_id) REFERENCES public.processing_sessions(id),
    CONSTRAINT background_jobs_job_key_unique UNIQUE (job_key),
    CONSTRAINT retry_count_limit CHECK (retry_count <= max_retry_attempts),
    CONSTRAINT timeout_range CHECK (timeout_seconds >= 30 AND timeout_seconds <= 7200) -- 30 seconds to 2 hours
);

-- 5. Real-time Progress Events Table - Live progress tracking
CREATE TABLE public.progress_events (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    event_type text NOT NULL, -- 'stage_started', 'progress_update', 'stage_completed', 'error_occurred'
    stage_name text NOT NULL,
    progress_percentage integer NOT NULL,
    message text,
    details jsonb DEFAULT '{}',
    timestamp timestamp with time zone NOT NULL DEFAULT now(),
    user_id uuid,
    
    CONSTRAINT progress_events_pkey PRIMARY KEY (id),
    CONSTRAINT progress_events_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT progress_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id),
    CONSTRAINT event_progress_range CHECK (progress_percentage >= 0 AND progress_percentage <= 100)
);

-- 6. User Sessions Table - Cross-device synchronization
CREATE TABLE public.user_sessions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL,
    device_fingerprint text NOT NULL,
    session_token text NOT NULL,
    active_processing_sessions uuid[],
    last_activity timestamp with time zone NOT NULL DEFAULT now(),
    user_agent text,
    ip_address inet,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    expires_at timestamp with time zone NOT NULL DEFAULT (now() + interval '7 days'),
    
    CONSTRAINT user_sessions_pkey PRIMARY KEY (id),
    CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id),
    CONSTRAINT user_sessions_token_unique UNIQUE (session_token),
    CONSTRAINT session_not_expired CHECK (expires_at > created_at)
);

-- 7. Processing Errors Table - Comprehensive error tracking and recovery
CREATE TABLE public.processing_errors (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid,
    job_id uuid,
    error_type text NOT NULL, -- 'timeout', 'service_unavailable', 'data_corruption', 'permission_denied'
    error_code text,
    error_message text NOT NULL,
    stack_trace text,
    context_data jsonb DEFAULT '{}',
    is_recoverable boolean NOT NULL DEFAULT true,
    recovery_attempted boolean NOT NULL DEFAULT false,
    recovery_successful boolean,
    retry_count integer NOT NULL DEFAULT 0,
    occurred_at timestamp with time zone NOT NULL DEFAULT now(),
    resolved_at timestamp with time zone,
    
    CONSTRAINT processing_errors_pkey PRIMARY KEY (id),
    CONSTRAINT processing_errors_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id),
    CONSTRAINT processing_errors_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.background_jobs(id),
    CONSTRAINT retry_count_positive CHECK (retry_count >= 0)
);

-- Performance Indexes for Enterprise Scale

-- Processing Sessions Indexes
CREATE INDEX idx_processing_sessions_document_id ON public.processing_sessions(document_id);
CREATE INDEX idx_processing_sessions_status ON public.processing_sessions(status);
CREATE INDEX idx_processing_sessions_org_id ON public.processing_sessions(org_id);
CREATE INDEX idx_processing_sessions_heartbeat ON public.processing_sessions(last_heartbeat);
CREATE INDEX idx_processing_sessions_priority_status ON public.processing_sessions(priority, status) WHERE status IN ('queued', 'starting');
CREATE INDEX idx_processing_sessions_user_active ON public.processing_sessions(user_id, status) WHERE status IN ('queued', 'starting', 'stage_0a_running', 'core_pipeline_running');

-- Agent Pipeline States Indexes
CREATE INDEX idx_agent_pipeline_states_session_id ON public.agent_pipeline_states(session_id);
CREATE INDEX idx_agent_pipeline_states_status ON public.agent_pipeline_states(status);
CREATE INDEX idx_agent_pipeline_states_stage_order ON public.agent_pipeline_states(session_id, stage_order);
CREATE INDEX idx_agent_pipeline_states_agent_key ON public.agent_pipeline_states(agent_key, status);

-- Background Jobs Indexes (Critical for job queue performance)
CREATE INDEX idx_background_jobs_status_priority ON public.background_jobs(status, priority) WHERE status IN ('queued', 'retry_scheduled');
CREATE INDEX idx_background_jobs_job_type ON public.background_jobs(job_type);
CREATE INDEX idx_background_jobs_session_id ON public.background_jobs(parent_session_id);
CREATE INDEX idx_background_jobs_scheduled_at ON public.background_jobs(scheduled_at) WHERE status IN ('queued', 'retry_scheduled');
CREATE INDEX idx_background_jobs_worker_id ON public.background_jobs(worker_id) WHERE status = 'running';
CREATE INDEX idx_background_jobs_job_key ON public.background_jobs(job_key);

-- Progress Events Indexes (Real-time queries)
CREATE INDEX idx_progress_events_session_timestamp ON public.progress_events(session_id, timestamp DESC);
CREATE INDEX idx_progress_events_timestamp ON public.progress_events(timestamp DESC);
CREATE INDEX idx_progress_events_event_type ON public.progress_events(event_type, timestamp DESC);

-- User Sessions Indexes (Cross-device sync)
CREATE INDEX idx_user_sessions_user_id ON public.user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON public.user_sessions(session_token);
CREATE INDEX idx_user_sessions_last_activity ON public.user_sessions(last_activity);
CREATE INDEX idx_user_sessions_expires_at ON public.user_sessions(expires_at) WHERE expires_at > now();

-- Processing Errors Indexes (Error analysis and recovery)
CREATE INDEX idx_processing_errors_session_id ON public.processing_errors(session_id);
CREATE INDEX idx_processing_errors_error_type ON public.processing_errors(error_type);
CREATE INDEX idx_processing_errors_recoverable ON public.processing_errors(is_recoverable, recovery_attempted);
CREATE INDEX idx_processing_errors_occurred_at ON public.processing_errors(occurred_at DESC);
CREATE INDEX idx_processing_errors_unresolved ON public.processing_errors(is_recoverable) WHERE resolved_at IS NULL;

-- Utility Functions for Maintenance

-- Function to clean up old progress events (retain 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_progress_events()
RETURNS integer AS $$
DECLARE
    deleted_count integer;
BEGIN
    DELETE FROM public.progress_events 
    WHERE timestamp < now() - interval '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Cleaned up % old progress events', deleted_count;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired user sessions
CREATE OR REPLACE FUNCTION cleanup_expired_user_sessions()
RETURNS integer AS $$
DECLARE
    deleted_count integer;
BEGIN
    DELETE FROM public.user_sessions 
    WHERE expires_at < now();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Cleaned up % expired user sessions', deleted_count;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get session progress summary
CREATE OR REPLACE FUNCTION get_session_progress_summary(p_session_id uuid)
RETURNS jsonb AS $$
DECLARE
    session_info jsonb;
    agents_progress jsonb;
    recent_events jsonb;
BEGIN
    -- Get session info
    SELECT jsonb_build_object(
        'session_id', id,
        'status', status,
        'current_stage', current_stage,
        'progress_percentage', progress_percentage,
        'created_at', created_at,
        'last_heartbeat', last_heartbeat,
        'error_count', error_count
    ) INTO session_info
    FROM public.processing_sessions
    WHERE id = p_session_id;
    
    -- Get agents progress
    SELECT jsonb_agg(
        jsonb_build_object(
            'agent_key', agent_key,
            'status', status,
            'progress_percentage', progress_percentage,
            'stage_order', stage_order
        ) ORDER BY stage_order
    ) INTO agents_progress
    FROM public.agent_pipeline_states
    WHERE session_id = p_session_id;
    
    -- Get recent events
    SELECT jsonb_agg(
        jsonb_build_object(
            'event_type', event_type,
            'stage_name', stage_name,
            'progress_percentage', progress_percentage,
            'message', message,
            'timestamp', timestamp
        ) ORDER BY timestamp DESC
    ) INTO recent_events
    FROM (
        SELECT * FROM public.progress_events
        WHERE session_id = p_session_id
        ORDER BY timestamp DESC
        LIMIT 10
    ) recent;
    
    RETURN jsonb_build_object(
        'session', session_info,
        'agents', COALESCE(agents_progress, '[]'::jsonb),
        'recent_events', COALESCE(recent_events, '[]'::jsonb)
    );
END;
$$ LANGUAGE plpgsql;

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE public.processing_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_pipeline_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.background_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.progress_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processing_errors ENABLE ROW LEVEL SECURITY;

-- Processing Sessions RLS - Users can only see sessions from their organization
CREATE POLICY "Users can view processing sessions from their organization" ON public.processing_sessions
    FOR SELECT USING (
        org_id IN (
            SELECT organization_id FROM public.user_organization_roles 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert processing sessions in their organization" ON public.processing_sessions
    FOR INSERT WITH CHECK (
        org_id IN (
            SELECT organization_id FROM public.user_organization_roles 
            WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update processing sessions in their organization" ON public.processing_sessions
    FOR UPDATE USING (
        org_id IN (
            SELECT organization_id FROM public.user_organization_roles 
            WHERE user_id = auth.uid()
        )
    );

-- Agent Pipeline States RLS - Inherit from processing sessions
CREATE POLICY "Users can view agent states for their sessions" ON public.agent_pipeline_states
    FOR SELECT USING (
        session_id IN (
            SELECT id FROM public.processing_sessions
            WHERE org_id IN (
                SELECT organization_id FROM public.user_organization_roles 
                WHERE user_id = auth.uid()
            )
        )
    );

-- Progress Events RLS - Inherit from processing sessions
CREATE POLICY "Users can view progress events for their sessions" ON public.progress_events
    FOR SELECT USING (
        session_id IN (
            SELECT id FROM public.processing_sessions
            WHERE org_id IN (
                SELECT organization_id FROM public.user_organization_roles 
                WHERE user_id = auth.uid()
            )
        )
    );

-- User Sessions RLS - Users can only see their own sessions
CREATE POLICY "Users can view their own user sessions" ON public.user_sessions
    FOR ALL USING (user_id = auth.uid());

-- Comments for documentation
COMMENT ON TABLE public.processing_sessions IS 'Enterprise processing sessions with heartbeat monitoring and priority queuing';
COMMENT ON TABLE public.agent_pipeline_states IS 'Individual agent execution states within processing pipeline';
COMMENT ON TABLE public.background_jobs IS 'Enterprise job queue with retry logic and deduplication';
COMMENT ON TABLE public.progress_events IS 'Real-time progress events for live UI updates';
COMMENT ON TABLE public.user_sessions IS 'Cross-device session synchronization for users';
COMMENT ON TABLE public.processing_errors IS 'Comprehensive error tracking with recovery mechanisms';

COMMENT ON COLUMN public.processing_sessions.priority IS 'Job priority (1-1000, lower number = higher priority)';
COMMENT ON COLUMN public.background_jobs.job_key IS 'Unique key for job deduplication across retries';
COMMENT ON COLUMN public.agent_pipeline_states.confidence_score IS 'Agent output confidence score (0.0-1.0)';
COMMENT ON COLUMN public.progress_events.event_type IS 'Event type: stage_started, progress_update, stage_completed, error_occurred';