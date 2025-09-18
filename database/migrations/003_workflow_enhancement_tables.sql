-- NMTC Workflow Enhancement Tables
-- Additional tables required for complete stage-dependent workflow
-- Author: Database Architect Agent

-- 1. Document Section Instances - Track identified sections per document
CREATE TABLE public.document_section_instances (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    section_id uuid NOT NULL, -- Reference to sections master table
    section_text text NOT NULL, -- Actual extracted section text
    confidence_score numeric(5,4), -- Confidence in section identification
    start_position integer, -- Start position in document
    end_position integer, -- End position in document
    page_number integer, -- Page where section was found
    identification_method text DEFAULT 'pattern_matching', -- How section was identified
    anchor_patterns_matched text[], -- Which patterns matched
    validation_status text DEFAULT 'pending', -- 'pending', 'validated', 'rejected'
    validated_by uuid, -- User who validated
    validated_at timestamp with time zone,
    metadata jsonb DEFAULT '{}',
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT document_section_instances_pkey PRIMARY KEY (id),
    CONSTRAINT document_section_instances_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT document_section_instances_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT document_section_instances_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(id),
    CONSTRAINT document_section_instances_validated_by_fkey FOREIGN KEY (validated_by) REFERENCES auth.users(id),
    CONSTRAINT confidence_score_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT validation_status_check CHECK (validation_status IN ('pending', 'validated', 'rejected'))
);

-- 2. Query Execution Results - Track query application results before normalization
CREATE TABLE public.query_execution_results (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    query_id uuid NOT NULL, -- Reference to queries master table
    section_instance_id uuid NOT NULL, -- Which section instance was queried
    raw_result text, -- Raw extraction result
    extraction_confidence numeric(5,4), -- Confidence in extraction
    extraction_method text DEFAULT 'ai_analysis', -- How data was extracted
    citation jsonb, -- Source citation in document
    execution_duration_ms bigint, -- How long query took
    error_message text, -- If query failed
    execution_status text DEFAULT 'completed', -- 'pending', 'running', 'completed', 'failed'
    retry_count integer DEFAULT 0,
    metadata jsonb DEFAULT '{}',
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT query_execution_results_pkey PRIMARY KEY (id),
    CONSTRAINT query_execution_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT query_execution_results_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT query_execution_results_query_id_fkey FOREIGN KEY (query_id) REFERENCES public.queries(id),
    CONSTRAINT query_execution_results_section_instance_id_fkey FOREIGN KEY (section_instance_id) REFERENCES public.document_section_instances(id),
    CONSTRAINT extraction_confidence_range CHECK (extraction_confidence >= 0.0 AND extraction_confidence <= 1.0),
    CONSTRAINT execution_status_check CHECK (execution_status IN ('pending', 'running', 'completed', 'failed'))
);

-- 3. Normalization Applications - Track which normalization rules were applied
CREATE TABLE public.normalization_applications (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    query_execution_id uuid NOT NULL, -- Which query result was normalized
    normalization_rule_id uuid NOT NULL, -- Which rule was applied
    input_value text NOT NULL, -- Original value before normalization
    output_value jsonb NOT NULL, -- Normalized value
    confidence_score numeric(5,4), -- Confidence in normalization
    rule_match_score numeric(5,4), -- How well the rule matched
    applied_at timestamp with time zone NOT NULL DEFAULT now(),
    applied_by text DEFAULT 'system', -- 'system' or user_id
    validation_status text DEFAULT 'pending',
    metadata jsonb DEFAULT '{}',
    
    CONSTRAINT normalization_applications_pkey PRIMARY KEY (id),
    CONSTRAINT normalization_applications_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT normalization_applications_query_execution_id_fkey FOREIGN KEY (query_execution_id) REFERENCES public.query_execution_results(id),
    CONSTRAINT normalization_applications_normalization_rule_id_fkey FOREIGN KEY (normalization_rule_id) REFERENCES public.normalization_rules(id),
    CONSTRAINT confidence_score_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT rule_match_score_range CHECK (rule_match_score >= 0.0 AND rule_match_score <= 1.0)
);

-- 4. Business Rule Evaluations - Track business rule evaluation results
CREATE TABLE public.business_rule_evaluations (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    business_rule_id uuid NOT NULL, -- Which business rule was evaluated
    evaluation_context jsonb NOT NULL, -- Input data for evaluation (extractions, etc.)
    evaluation_result boolean NOT NULL, -- Did the rule pass or fail?
    rule_output jsonb, -- Result of rule evaluation
    confidence_score numeric(5,4), -- Confidence in evaluation
    evaluation_method text DEFAULT 'automated', -- 'automated', 'manual', 'hybrid'
    affected_extractions uuid[], -- Which extractions were affected
    violation_severity text, -- 'low', 'medium', 'high', 'critical' (if failed)
    violation_message text, -- Human-readable violation description
    recommended_action text, -- What should be done about this
    evaluated_at timestamp with time zone NOT NULL DEFAULT now(),
    evaluated_by text DEFAULT 'system',
    review_status text DEFAULT 'pending', -- 'pending', 'reviewed', 'resolved'
    metadata jsonb DEFAULT '{}',
    
    CONSTRAINT business_rule_evaluations_pkey PRIMARY KEY (id),
    CONSTRAINT business_rule_evaluations_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT business_rule_evaluations_business_rule_id_fkey FOREIGN KEY (business_rule_id) REFERENCES public.business_rules(id),
    CONSTRAINT confidence_score_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT violation_severity_check CHECK (violation_severity IN ('low', 'medium', 'high', 'critical'))
);

-- 5. Agent Prompt Applications - Track when and how agent prompts are applied to results
CREATE TABLE public.agent_prompt_applications (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    agent_prompt_id uuid NOT NULL, -- Which agent prompt was used
    application_stage text NOT NULL, -- 'results_processing', 'insights_generation', 'reporting'
    input_data jsonb NOT NULL, -- What data was fed to the prompt
    prompt_response text, -- AI response from prompt
    response_structured jsonb, -- Structured version of response
    confidence_score numeric(5,4), -- Confidence in AI response
    processing_duration_ms bigint, -- How long prompt took
    token_usage jsonb, -- Token consumption stats
    model_used text, -- Which AI model was used
    prompt_version text, -- Version of prompt used
    application_context jsonb, -- Context about why prompt was applied
    quality_score numeric(5,4), -- Quality assessment of response
    human_review_required boolean DEFAULT false,
    applied_at timestamp with time zone NOT NULL DEFAULT now(),
    reviewed_at timestamp with time zone,
    reviewed_by uuid,
    review_notes text,
    metadata jsonb DEFAULT '{}',
    
    CONSTRAINT agent_prompt_applications_pkey PRIMARY KEY (id),
    CONSTRAINT agent_prompt_applications_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT agent_prompt_applications_agent_prompt_id_fkey FOREIGN KEY (agent_prompt_id) REFERENCES public.agent_prompts(id),
    CONSTRAINT agent_prompt_applications_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES auth.users(id),
    CONSTRAINT confidence_score_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT quality_score_range CHECK (quality_score >= 0.0 AND quality_score <= 1.0)
);

-- 6. Workflow Stage Completions - Track completion of each workflow stage
CREATE TABLE public.workflow_stage_completions (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    stage_name text NOT NULL, -- 'section_identification', 'query_application', etc.
    stage_order integer NOT NULL, -- Order of execution
    started_at timestamp with time zone NOT NULL DEFAULT now(),
    completed_at timestamp with time zone,
    status text NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed', 'skipped'
    input_data jsonb, -- What data was input to this stage
    output_data jsonb, -- What data was output from this stage
    output_references jsonb, -- References to records created in this stage
    error_details jsonb, -- Error information if failed
    performance_metrics jsonb, -- Timing, memory usage, etc.
    dependencies_met boolean DEFAULT true, -- Were all dependencies satisfied?
    human_intervention_required boolean DEFAULT false,
    quality_checks_passed boolean DEFAULT true,
    metadata jsonb DEFAULT '{}',
    
    CONSTRAINT workflow_stage_completions_pkey PRIMARY KEY (id),
    CONSTRAINT workflow_stage_completions_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT workflow_stage_completions_unique_stage UNIQUE (session_id, stage_name),
    CONSTRAINT status_check CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped'))
);

-- Create indexes for performance
CREATE INDEX idx_document_section_instances_session_id ON public.document_section_instances(session_id);
CREATE INDEX idx_document_section_instances_document_id ON public.document_section_instances(document_id);
CREATE INDEX idx_document_section_instances_section_id ON public.document_section_instances(section_id);

CREATE INDEX idx_query_execution_results_session_id ON public.query_execution_results(session_id);
CREATE INDEX idx_query_execution_results_query_id ON public.query_execution_results(query_id);
CREATE INDEX idx_query_execution_results_section_instance_id ON public.query_execution_results(section_instance_id);

CREATE INDEX idx_normalization_applications_session_id ON public.normalization_applications(session_id);
CREATE INDEX idx_normalization_applications_query_execution_id ON public.normalization_applications(query_execution_id);
CREATE INDEX idx_normalization_applications_rule_id ON public.normalization_applications(normalization_rule_id);

CREATE INDEX idx_business_rule_evaluations_session_id ON public.business_rule_evaluations(session_id);
CREATE INDEX idx_business_rule_evaluations_rule_id ON public.business_rule_evaluations(business_rule_id);
CREATE INDEX idx_business_rule_evaluations_result ON public.business_rule_evaluations(evaluation_result);

CREATE INDEX idx_agent_prompt_applications_session_id ON public.agent_prompt_applications(session_id);
CREATE INDEX idx_agent_prompt_applications_prompt_id ON public.agent_prompt_applications(agent_prompt_id);
CREATE INDEX idx_agent_prompt_applications_stage ON public.agent_prompt_applications(application_stage);

CREATE INDEX idx_workflow_stage_completions_session_id ON public.workflow_stage_completions(session_id);
CREATE INDEX idx_workflow_stage_completions_stage_order ON public.workflow_stage_completions(stage_order);
CREATE INDEX idx_workflow_stage_completions_status ON public.workflow_stage_completions(status);

-- Add RLS policies
ALTER TABLE public.document_section_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.query_execution_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.normalization_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_rule_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_prompt_applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflow_stage_completions ENABLE ROW LEVEL SECURITY;

-- RLS policies for organization-based access
CREATE POLICY "Users can view their organization's section instances" ON public.document_section_instances
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.documents d 
            WHERE d.id = document_section_instances.document_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's query results" ON public.query_execution_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.documents d 
            WHERE d.id = query_execution_results.document_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's normalization applications" ON public.normalization_applications
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps
            JOIN public.documents d ON ps.document_id = d.id
            WHERE ps.id = normalization_applications.session_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's business rule evaluations" ON public.business_rule_evaluations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps
            JOIN public.documents d ON ps.document_id = d.id
            WHERE ps.id = business_rule_evaluations.session_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's agent prompt applications" ON public.agent_prompt_applications
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps
            JOIN public.documents d ON ps.document_id = d.id
            WHERE ps.id = agent_prompt_applications.session_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's workflow stage completions" ON public.workflow_stage_completions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps
            JOIN public.documents d ON ps.document_id = d.id
            WHERE ps.id = workflow_stage_completions.session_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

-- Utility functions
CREATE OR REPLACE FUNCTION get_session_workflow_progress(session_uuid uuid)
RETURNS jsonb AS $$
DECLARE
    result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'total_stages', COUNT(*),
        'completed_stages', COUNT(*) FILTER (WHERE status = 'completed'),
        'failed_stages', COUNT(*) FILTER (WHERE status = 'failed'),
        'current_stage', (SELECT stage_name FROM public.workflow_stage_completions WHERE session_id = session_uuid AND status = 'running' LIMIT 1),
        'overall_progress', (COUNT(*) FILTER (WHERE status = 'completed')::float / COUNT(*) * 100)::integer,
        'stages_detail', jsonb_agg(
            jsonb_build_object(
                'stage_name', stage_name,
                'status', status,
                'started_at', started_at,
                'completed_at', completed_at,
                'stage_order', stage_order
            ) ORDER BY stage_order
        )
    ) INTO result
    FROM public.workflow_stage_completions 
    WHERE session_id = session_uuid;
    
    RETURN COALESCE(result, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Comments for documentation
COMMENT ON TABLE public.document_section_instances IS 'Tracks identified sections within each processed document';
COMMENT ON TABLE public.query_execution_results IS 'Stores raw results from applying queries to document sections';
COMMENT ON TABLE public.normalization_applications IS 'Records which normalization rules were applied and their results';
COMMENT ON TABLE public.business_rule_evaluations IS 'Tracks business rule evaluations and any violations found';
COMMENT ON TABLE public.agent_prompt_applications IS 'Records when and how agent prompts are applied for results processing';
COMMENT ON TABLE public.workflow_stage_completions IS 'Tracks completion status of each workflow stage for full traceability';