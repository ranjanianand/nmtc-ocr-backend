-- NMTC 3-Agent Pipeline Output Tables
-- Author: Database Architect Agent + Core Engine Processing Agent
-- Purpose: Store results from 3-Agent processing pipeline (Analyzer, Risk, Reports)

-- 1. Agent Extraction Results - Store data extracted by Agent 1 (Analyzer)
CREATE TABLE public.agent_extraction_results (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    agent_key text NOT NULL, -- 'agent_1_analyzer', 'agent_2_risk', 'agent_3_reports'
    document_id uuid NOT NULL,
    query_id uuid, -- Reference to queries table (what was being extracted)
    section_id uuid, -- Reference to sections table (which document section)
    raw_extraction text, -- Raw extracted text from document
    normalized_value jsonb, -- Processed/normalized value using normalization_rules
    confidence_score numeric(5,4), -- Agent's confidence in extraction (0.0000 to 1.0000)
    extraction_method text, -- 'ocr', 'pattern_match', 'ml_model', 'rule_based'
    citation jsonb, -- Source location: {"page": 1, "coordinates": {...}, "text_span": [...]}
    business_rule_applied uuid, -- Which business rule was applied (if any)
    validation_status text NOT NULL DEFAULT 'pending', -- 'pending', 'validated', 'rejected', 'needs_review'
    metadata jsonb DEFAULT '{}', -- Additional extraction metadata
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    validated_at timestamp with time zone,
    validated_by uuid, -- User who validated the extraction
    
    CONSTRAINT agent_extraction_results_pkey PRIMARY KEY (id),
    CONSTRAINT agent_extraction_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT agent_extraction_results_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT agent_extraction_results_query_id_fkey FOREIGN KEY (query_id) REFERENCES public.queries(id),
    CONSTRAINT agent_extraction_results_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(id),
    CONSTRAINT agent_extraction_results_business_rule_applied_fkey FOREIGN KEY (business_rule_applied) REFERENCES public.business_rules(id),
    CONSTRAINT agent_extraction_results_validated_by_fkey FOREIGN KEY (validated_by) REFERENCES auth.users(id),
    CONSTRAINT confidence_score_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT validation_status_check CHECK (validation_status IN ('pending', 'validated', 'rejected', 'needs_review'))
);

-- 2. Risk Assessment Results - Store risk analysis from Agent 2 (Risk Assessor)
CREATE TABLE public.risk_assessment_results (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    risk_category text NOT NULL, -- 'financial', 'operational', 'compliance', 'legal', 'market'
    risk_subcategory text, -- More specific risk type
    risk_level text NOT NULL, -- 'low', 'medium', 'high', 'critical'
    risk_score numeric(5,2), -- Quantitative risk score (0.00 to 100.00)
    risk_title text NOT NULL, -- Short risk description
    risk_description text NOT NULL, -- Detailed risk explanation
    impact_analysis jsonb, -- {"financial": 50000, "timeline": "6 months", "departments": ["finance"]}
    likelihood_assessment jsonb, -- {"probability": 0.3, "factors": [...], "historical_data": {...}}
    mitigation_recommendations jsonb, -- [{"action": "...", "priority": "high", "cost": 1000}]
    business_rule_id uuid, -- Which business rule triggered this risk assessment
    compliance_flags jsonb, -- Compliance issues: {"NMTC": ["requirement_1"], "SOX": []}
    regulatory_references jsonb, -- References to regulations/standards
    source_extractions uuid[], -- Array of extraction IDs that led to this risk
    risk_owner text, -- Who should handle this risk
    due_date date, -- When this risk should be addressed
    metadata jsonb DEFAULT '{}',
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    reviewed_at timestamp with time zone,
    reviewed_by uuid, -- User who reviewed the risk assessment
    review_status text DEFAULT 'pending', -- 'pending', 'accepted', 'disputed', 'resolved'
    
    CONSTRAINT risk_assessment_results_pkey PRIMARY KEY (id),
    CONSTRAINT risk_assessment_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT risk_assessment_results_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT risk_assessment_results_business_rule_id_fkey FOREIGN KEY (business_rule_id) REFERENCES public.business_rules(id),
    CONSTRAINT risk_assessment_results_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES auth.users(id),
    CONSTRAINT risk_score_range CHECK (risk_score >= 0.00 AND risk_score <= 100.00),
    CONSTRAINT risk_level_check CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT review_status_check CHECK (review_status IN ('pending', 'accepted', 'disputed', 'resolved'))
);

-- 3. Generated Reports - Store reports created by Agent 3 (Report Generator)
CREATE TABLE public.generated_reports (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    report_definition_id uuid NOT NULL, -- Which report template was used
    report_type text NOT NULL, -- 'summary', 'detailed', 'compliance', 'risk', 'executive'
    report_format text NOT NULL, -- 'PDF', 'HTML', 'DOCX', 'JSON', 'CSV'
    report_title text NOT NULL,
    report_content jsonb NOT NULL, -- Structured report data
    report_binary bytea, -- Binary content for PDF, DOCX files
    storage_path text, -- External file storage location (S3, etc.)
    file_size bigint, -- Size in bytes
    generation_method text, -- 'template_based', 'ai_generated', 'hybrid'
    data_sources jsonb, -- Which extractions and assessments were used
    report_mappings_used uuid[], -- Array of report_mapping IDs used
    quality_score numeric(5,4), -- Report quality assessment
    completeness_percentage integer, -- How complete is the report (0-100)
    generated_at timestamp with time zone NOT NULL DEFAULT now(),
    expires_at timestamp with time zone, -- When report should be deleted
    download_count integer NOT NULL DEFAULT 0,
    last_downloaded_at timestamp with time zone,
    last_downloaded_by uuid,
    approval_status text DEFAULT 'draft', -- 'draft', 'pending_review', 'approved', 'published'
    approved_by uuid,
    approved_at timestamp with time zone,
    metadata jsonb DEFAULT '{}',
    
    CONSTRAINT generated_reports_pkey PRIMARY KEY (id),
    CONSTRAINT generated_reports_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT generated_reports_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT generated_reports_report_definition_id_fkey FOREIGN KEY (report_definition_id) REFERENCES public.report_definitions(id),
    CONSTRAINT generated_reports_last_downloaded_by_fkey FOREIGN KEY (last_downloaded_by) REFERENCES auth.users(id),
    CONSTRAINT generated_reports_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES auth.users(id),
    CONSTRAINT quality_score_range CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    CONSTRAINT completeness_range CHECK (completeness_percentage >= 0 AND completeness_percentage <= 100),
    CONSTRAINT approval_status_check CHECK (approval_status IN ('draft', 'pending_review', 'approved', 'published'))
);

-- 4. Agent Workflow Summary - Overall results from entire 3-Agent pipeline
CREATE TABLE public.agent_workflow_results (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    workflow_status text NOT NULL, -- 'completed', 'partial', 'failed', 'requires_input'
    overall_confidence numeric(5,4), -- Combined confidence from all agents
    processing_summary jsonb NOT NULL, -- Summary of all agent outputs
    key_findings jsonb, -- Important discoveries across all agents
    compliance_status text NOT NULL, -- 'compliant', 'non_compliant', 'needs_review', 'unknown'
    compliance_score numeric(5,2), -- Overall compliance score (0.00 to 100.00)
    recommendations jsonb, -- Overall recommendations from all agents
    action_items jsonb, -- Required follow-up actions
    risk_summary jsonb, -- Summary of all identified risks
    extraction_summary jsonb, -- Summary of all extractions
    report_summary jsonb, -- Summary of all generated reports
    business_rules_applied uuid[], -- Array of business rule IDs that were applied
    processing_duration_ms bigint, -- Total processing time
    agent_execution_order text[], -- Order in which agents executed
    final_review_required boolean DEFAULT false, -- Whether human review is needed
    auto_approval_eligible boolean DEFAULT false, -- Whether this can be auto-approved
    metadata jsonb DEFAULT '{}',
    completed_at timestamp with time zone NOT NULL DEFAULT now(),
    reviewed_at timestamp with time zone,
    reviewed_by uuid,
    final_status text DEFAULT 'pending_review', -- 'pending_review', 'approved', 'rejected', 'requires_changes'
    
    CONSTRAINT agent_workflow_results_pkey PRIMARY KEY (id),
    CONSTRAINT agent_workflow_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT agent_workflow_results_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT agent_workflow_results_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES auth.users(id),
    CONSTRAINT overall_confidence_range CHECK (overall_confidence >= 0.0 AND overall_confidence <= 1.0),
    CONSTRAINT compliance_score_range CHECK (compliance_score >= 0.00 AND compliance_score <= 100.00),
    CONSTRAINT workflow_status_check CHECK (workflow_status IN ('completed', 'partial', 'failed', 'requires_input')),
    CONSTRAINT compliance_status_check CHECK (compliance_status IN ('compliant', 'non_compliant', 'needs_review', 'unknown')),
    CONSTRAINT final_status_check CHECK (final_status IN ('pending_review', 'approved', 'rejected', 'requires_changes'))
);

-- 5. Agent Processing Logs - Detailed logs of agent execution
CREATE TABLE public.agent_processing_logs (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    agent_key text NOT NULL,
    log_level text NOT NULL, -- 'debug', 'info', 'warning', 'error', 'critical'
    log_message text NOT NULL,
    log_data jsonb, -- Structured log data
    timestamp timestamp with time zone NOT NULL DEFAULT now(),
    processing_step text, -- Which step of agent processing
    execution_context jsonb, -- Context information
    performance_metrics jsonb, -- Timing, memory usage, etc.
    
    CONSTRAINT agent_processing_logs_pkey PRIMARY KEY (id),
    CONSTRAINT agent_processing_logs_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT log_level_check CHECK (log_level IN ('debug', 'info', 'warning', 'error', 'critical'))
);

-- Create indexes for performance
CREATE INDEX idx_agent_extraction_results_session_id ON public.agent_extraction_results(session_id);
CREATE INDEX idx_agent_extraction_results_document_id ON public.agent_extraction_results(document_id);
CREATE INDEX idx_agent_extraction_results_agent_key ON public.agent_extraction_results(agent_key);
CREATE INDEX idx_agent_extraction_results_confidence ON public.agent_extraction_results(confidence_score DESC);

CREATE INDEX idx_risk_assessment_results_session_id ON public.risk_assessment_results(session_id);
CREATE INDEX idx_risk_assessment_results_document_id ON public.risk_assessment_results(document_id);
CREATE INDEX idx_risk_assessment_results_risk_level ON public.risk_assessment_results(risk_level);
CREATE INDEX idx_risk_assessment_results_risk_score ON public.risk_assessment_results(risk_score DESC);

CREATE INDEX idx_generated_reports_session_id ON public.generated_reports(session_id);
CREATE INDEX idx_generated_reports_document_id ON public.generated_reports(document_id);
CREATE INDEX idx_generated_reports_report_type ON public.generated_reports(report_type);
CREATE INDEX idx_generated_reports_generated_at ON public.generated_reports(generated_at DESC);

CREATE INDEX idx_agent_workflow_results_session_id ON public.agent_workflow_results(session_id);
CREATE INDEX idx_agent_workflow_results_document_id ON public.agent_workflow_results(document_id);
CREATE INDEX idx_agent_workflow_results_compliance_status ON public.agent_workflow_results(compliance_status);
CREATE INDEX idx_agent_workflow_results_overall_confidence ON public.agent_workflow_results(overall_confidence DESC);

CREATE INDEX idx_agent_processing_logs_session_id ON public.agent_processing_logs(session_id);
CREATE INDEX idx_agent_processing_logs_agent_key ON public.agent_processing_logs(agent_key);
CREATE INDEX idx_agent_processing_logs_timestamp ON public.agent_processing_logs(timestamp DESC);
CREATE INDEX idx_agent_processing_logs_log_level ON public.agent_processing_logs(log_level);

-- Add RLS (Row Level Security) policies if needed
ALTER TABLE public.agent_extraction_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_assessment_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_workflow_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_processing_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (basic organization-based access)
CREATE POLICY "Users can view their organization's extraction results" ON public.agent_extraction_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.documents d 
            WHERE d.id = agent_extraction_results.document_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's risk assessments" ON public.risk_assessment_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.documents d 
            WHERE d.id = risk_assessment_results.document_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's reports" ON public.generated_reports
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.documents d 
            WHERE d.id = generated_reports.document_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's workflow results" ON public.agent_workflow_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.documents d 
            WHERE d.id = agent_workflow_results.document_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's processing logs" ON public.agent_processing_logs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps
            JOIN public.documents d ON ps.document_id = d.id
            WHERE ps.id = agent_processing_logs.session_id 
            AND d.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

-- Add helpful utility functions
CREATE OR REPLACE FUNCTION get_session_extraction_summary(session_uuid uuid)
RETURNS jsonb AS $$
DECLARE
    result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'total_extractions', COUNT(*),
        'high_confidence_extractions', COUNT(*) FILTER (WHERE confidence_score > 0.8),
        'validated_extractions', COUNT(*) FILTER (WHERE validation_status = 'validated'),
        'average_confidence', ROUND(AVG(confidence_score)::numeric, 4),
        'extractions_by_agent', jsonb_object_agg(agent_key, agent_count)
    ) INTO result
    FROM (
        SELECT agent_key, COUNT(*) as agent_count
        FROM public.agent_extraction_results 
        WHERE session_id = session_uuid
        GROUP BY agent_key
    ) agent_counts,
    public.agent_extraction_results
    WHERE session_id = session_uuid;
    
    RETURN COALESCE(result, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_session_risk_summary(session_uuid uuid)
RETURNS jsonb AS $$
DECLARE
    result jsonb;
BEGIN
    SELECT jsonb_build_object(
        'total_risks', COUNT(*),
        'critical_risks', COUNT(*) FILTER (WHERE risk_level = 'critical'),
        'high_risks', COUNT(*) FILTER (WHERE risk_level = 'high'),
        'average_risk_score', ROUND(AVG(risk_score)::numeric, 2),
        'risks_by_category', jsonb_object_agg(risk_category, category_count)
    ) INTO result
    FROM (
        SELECT risk_category, COUNT(*) as category_count
        FROM public.risk_assessment_results 
        WHERE session_id = session_uuid
        GROUP BY risk_category
    ) category_counts,
    public.risk_assessment_results
    WHERE session_id = session_uuid;
    
    RETURN COALESCE(result, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add triggers for automatic workflow result updates
CREATE OR REPLACE FUNCTION update_workflow_result_summary()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the workflow results summary when extractions or risks are added
    UPDATE public.agent_workflow_results SET
        extraction_summary = get_session_extraction_summary(NEW.session_id),
        risk_summary = get_session_risk_summary(NEW.session_id),
        metadata = jsonb_set(
            COALESCE(metadata, '{}'::jsonb),
            '{last_updated}',
            to_jsonb(now())
        )
    WHERE session_id = NEW.session_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_workflow_summary_on_extraction
    AFTER INSERT OR UPDATE ON public.agent_extraction_results
    FOR EACH ROW EXECUTE FUNCTION update_workflow_result_summary();

CREATE TRIGGER trigger_update_workflow_summary_on_risk
    AFTER INSERT OR UPDATE ON public.risk_assessment_results
    FOR EACH ROW EXECUTE FUNCTION update_workflow_result_summary();

-- Add comments for documentation
COMMENT ON TABLE public.agent_extraction_results IS 'Stores data extracted by Agent 1 (Document Analyzer) including raw and normalized values';
COMMENT ON TABLE public.risk_assessment_results IS 'Stores risk assessments performed by Agent 2 (Risk Assessor) including impact analysis and mitigation recommendations';
COMMENT ON TABLE public.generated_reports IS 'Stores reports generated by Agent 3 (Report Generator) in various formats';
COMMENT ON TABLE public.agent_workflow_results IS 'Stores overall summary and results from the complete 3-Agent processing pipeline';
COMMENT ON TABLE public.agent_processing_logs IS 'Detailed execution logs from all agents for debugging and audit purposes';

COMMENT ON COLUMN public.agent_extraction_results.normalized_value IS 'Value processed through normalization_rules table patterns';
COMMENT ON COLUMN public.risk_assessment_results.compliance_flags IS 'JSON object with regulatory compliance issues identified';
COMMENT ON COLUMN public.generated_reports.data_sources IS 'References to extraction and risk assessment IDs used in report generation';
COMMENT ON COLUMN public.agent_workflow_results.business_rules_applied IS 'Array of business_rules table IDs that were evaluated during processing';