-- NMTC Agent Output Tables (Clean Version)
-- Only creates tables that don't already exist
-- Author: Database Architect Agent + Core Engine Processing Agent

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
    CONSTRAINT agent_extraction_results_confidence_check CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    CONSTRAINT agent_extraction_results_validation_status_check CHECK (validation_status IN ('pending', 'validated', 'rejected', 'needs_review'))
);

-- 2. Risk Assessment Results - Store risk analysis from Agent 2 (Risk Assessor)
CREATE TABLE public.risk_assessment_results (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    risk_category text NOT NULL, -- 'financial', 'operational', 'compliance', 'market', 'credit'
    risk_level text NOT NULL, -- 'low', 'medium', 'high', 'critical'
    risk_score numeric(5,2), -- Risk score 0.00 to 100.00
    risk_description text NOT NULL, -- Human-readable risk description
    impact_analysis jsonb, -- Detailed impact assessment
    mitigation_recommendations jsonb, -- Risk mitigation suggestions
    business_rule_id uuid, -- Which business rule triggered this risk assessment
    compliance_flags jsonb, -- Compliance issues identified
    confidence_score numeric(5,4), -- Agent's confidence in risk assessment
    source_extractions uuid[], -- Which extractions contributed to this risk
    metadata jsonb DEFAULT '{}',
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT risk_assessment_results_pkey PRIMARY KEY (id),
    CONSTRAINT risk_assessment_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT risk_assessment_results_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT risk_assessment_results_business_rule_id_fkey FOREIGN KEY (business_rule_id) REFERENCES public.business_rules(id),
    CONSTRAINT risk_assessment_results_risk_level_check CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT risk_assessment_results_risk_score_check CHECK (risk_score >= 0.00 AND risk_score <= 100.00),
    CONSTRAINT risk_assessment_results_confidence_check CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)
);

-- 3. Generated Reports - Store reports created by Agent 3 (Report Generator)
CREATE TABLE public.generated_reports (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    report_definition_id uuid NOT NULL, -- Which report template was used
    report_type text NOT NULL, -- 'summary', 'detailed', 'compliance', 'risk', 'executive'
    report_format text NOT NULL, -- 'PDF', 'HTML', 'DOCX', 'JSON', 'XLSX'
    report_content jsonb NOT NULL, -- Structured report data/content
    report_binary bytea, -- Binary content for PDF/DOCX reports
    storage_path text, -- File storage location if stored externally
    file_size_bytes bigint, -- Size of generated report
    generation_duration_ms bigint, -- How long it took to generate
    generated_at timestamp with time zone NOT NULL DEFAULT now(),
    expires_at timestamp with time zone, -- When report expires
    download_count integer NOT NULL DEFAULT 0, -- How many times downloaded
    access_permissions jsonb DEFAULT '{}', -- Who can access this report
    metadata jsonb DEFAULT '{}',
    
    CONSTRAINT generated_reports_pkey PRIMARY KEY (id),
    CONSTRAINT generated_reports_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT generated_reports_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT generated_reports_report_definition_id_fkey FOREIGN KEY (report_definition_id) REFERENCES public.report_definitions(id),
    CONSTRAINT generated_reports_download_count_check CHECK (download_count >= 0)
);

-- 4. Agent Workflow Results - Overall results summary from complete 3-agent workflow
CREATE TABLE public.agent_workflow_results (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    workflow_status text NOT NULL, -- 'completed', 'partial', 'failed'
    overall_confidence numeric(5,4), -- Overall confidence across all agents
    processing_summary jsonb NOT NULL, -- Summary of all agent processing
    key_findings jsonb, -- Important findings discovered
    compliance_status text, -- 'compliant', 'non_compliant', 'needs_review', 'insufficient_data'
    risk_summary jsonb, -- Aggregated risk assessment
    recommendations jsonb, -- Overall recommendations
    agent_performance_metrics jsonb, -- Performance stats for each agent
    total_processing_time_ms bigint, -- Total time for complete workflow
    extraction_count integer NOT NULL DEFAULT 0, -- Total extractions performed
    risk_count integer NOT NULL DEFAULT 0, -- Total risks identified
    report_count integer NOT NULL DEFAULT 0, -- Total reports generated
    error_count integer NOT NULL DEFAULT 0, -- Total errors encountered
    metadata jsonb DEFAULT '{}',
    completed_at timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT agent_workflow_results_pkey PRIMARY KEY (id),
    CONSTRAINT agent_workflow_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT agent_workflow_results_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT agent_workflow_results_unique_session_document UNIQUE (session_id, document_id),
    CONSTRAINT agent_workflow_results_confidence_check CHECK (overall_confidence >= 0.0 AND overall_confidence <= 1.0),
    CONSTRAINT agent_workflow_results_workflow_status_check CHECK (workflow_status IN ('completed', 'partial', 'failed')),
    CONSTRAINT agent_workflow_results_compliance_status_check CHECK (compliance_status IN ('compliant', 'non_compliant', 'needs_review', 'insufficient_data'))
);

-- Create indexes for performance
CREATE INDEX idx_agent_extraction_results_session_id ON public.agent_extraction_results(session_id);
CREATE INDEX idx_agent_extraction_results_document_id ON public.agent_extraction_results(document_id);
CREATE INDEX idx_agent_extraction_results_agent_key ON public.agent_extraction_results(agent_key);
CREATE INDEX idx_agent_extraction_results_validation_status ON public.agent_extraction_results(validation_status);
CREATE INDEX idx_agent_extraction_results_created_at ON public.agent_extraction_results(created_at);

CREATE INDEX idx_risk_assessment_results_session_id ON public.risk_assessment_results(session_id);
CREATE INDEX idx_risk_assessment_results_document_id ON public.risk_assessment_results(document_id);
CREATE INDEX idx_risk_assessment_results_risk_level ON public.risk_assessment_results(risk_level);
CREATE INDEX idx_risk_assessment_results_risk_category ON public.risk_assessment_results(risk_category);

CREATE INDEX idx_generated_reports_session_id ON public.generated_reports(session_id);
CREATE INDEX idx_generated_reports_document_id ON public.generated_reports(document_id);
CREATE INDEX idx_generated_reports_report_type ON public.generated_reports(report_type);
CREATE INDEX idx_generated_reports_generated_at ON public.generated_reports(generated_at);

CREATE INDEX idx_agent_workflow_results_session_id ON public.agent_workflow_results(session_id);
CREATE INDEX idx_agent_workflow_results_document_id ON public.agent_workflow_results(document_id);
CREATE INDEX idx_agent_workflow_results_workflow_status ON public.agent_workflow_results(workflow_status);
CREATE INDEX idx_agent_workflow_results_compliance_status ON public.agent_workflow_results(compliance_status);

-- Enable Row Level Security
ALTER TABLE public.agent_extraction_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_assessment_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_workflow_results ENABLE ROW LEVEL SECURITY;

-- RLS policies for organization-based access
CREATE POLICY "Users can view their organization's extraction results" ON public.agent_extraction_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps 
            WHERE ps.id = agent_extraction_results.session_id 
            AND ps.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's risk assessments" ON public.risk_assessment_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps 
            WHERE ps.id = risk_assessment_results.session_id 
            AND ps.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's generated reports" ON public.generated_reports
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps 
            WHERE ps.id = generated_reports.session_id 
            AND ps.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

CREATE POLICY "Users can view their organization's workflow results" ON public.agent_workflow_results
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.processing_sessions ps 
            WHERE ps.id = agent_workflow_results.session_id 
            AND ps.org_id = (auth.jwt() ->> 'organization_id')::uuid
        )
    );

-- Comments for documentation
COMMENT ON TABLE public.agent_extraction_results IS 'Stores data extracted by the document analyzer agent';
COMMENT ON TABLE public.risk_assessment_results IS 'Stores risk analysis results from the risk assessment agent';
COMMENT ON TABLE public.generated_reports IS 'Stores reports created by the report generation agent';
COMMENT ON TABLE public.agent_workflow_results IS 'Stores overall results summary from complete 3-agent workflow';