# 3-Agent Pipeline Database Analysis

## Current Status: ❌ INCOMPLETE IMPLEMENTATION

The 3-Agent pipeline has been implemented with basic state tracking but is **NOT** properly integrated with the master tables for business logic and output storage.

## 🔍 Master Tables Analysis (Input Sources)

### ✅ Available Master Tables for Agent Inputs:

1. **`agent_prompts`** - Agent system and task prompts
   - `agent_key` (agent_1_analyzer, agent_2_risk, agent_3_reports)
   - `system_prompt`, `task_prompt`, `style_guide`
   - `output_schema_json` - Expected output structure
   - `guardrails` - Validation rules

2. **`business_rules`** - Organization-specific business logic
   - `condition_json` - Rule conditions
   - `action_json` - Rule actions
   - `priority` - Rule precedence
   - `document_type_id` - Applicable document types

3. **`normalization_rules`** - Data normalization patterns
   - `rule_type` - Type of normalization
   - `pattern` - Pattern to match
   - `normalized_value` - Expected output format

4. **`sections`** - Document structure definitions
   - `canonical_name` - Section names
   - `anchor_patterns` - Section identification patterns
   - `order_no` - Section sequence

5. **`queries`** - Extraction questions
   - `question_text` - What to extract
   - `extractors` - Extraction methods
   - `normalizer_hint` - How to normalize

6. **`recurrence_rules`** - Date/frequency patterns
   - `frequency` - How often
   - `periods_per_year` - Frequency details
   - `scheduler_logic` - Calculation rules

7. **`report_definitions`** - Report templates
   - `template_json` - Report structure
   - `binding_rules` - Data binding logic
   - `export_capabilities` - Output formats

8. **`report_mappings`** - Report data mappings
   - `mapping_type` - Type of mapping
   - `key_value` - Mapping key
   - `filter_logic_json` - Filtering rules

## ❌ Missing Output Storage Tables

### Current Gap: NO DEDICATED OUTPUT TABLES

The current implementation only tracks agent **state** but does NOT store agent **outputs/results**:

**Current State Tables:**
- ✅ `agent_pipeline_states` - Only tracks status, progress, confidence
- ✅ `processing_sessions` - Only tracks overall session status

**Missing Output Tables:**
- ❌ Agent 1 (Analyzer) results storage
- ❌ Agent 2 (Risk) results storage  
- ❌ Agent 3 (Reports) results storage
- ❌ Extracted data storage
- ❌ Generated reports storage
- ❌ Risk assessments storage

## 🎯 Required Output Tables

### 1. Agent Extraction Results
```sql
CREATE TABLE public.agent_extraction_results (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    agent_key text NOT NULL, -- agent_1_analyzer, agent_2_risk, agent_3_reports
    document_id uuid NOT NULL,
    query_id uuid, -- Reference to queries table
    section_id uuid, -- Reference to sections table
    raw_extraction text, -- Raw extracted text
    normalized_value jsonb, -- Processed/normalized value
    confidence_score numeric(5,4),
    extraction_method text, -- How it was extracted
    citation jsonb, -- Source location in document
    metadata jsonb DEFAULT '{}',
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT agent_extraction_results_pkey PRIMARY KEY (id),
    CONSTRAINT agent_extraction_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT agent_extraction_results_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT agent_extraction_results_query_id_fkey FOREIGN KEY (query_id) REFERENCES public.queries(id),
    CONSTRAINT agent_extraction_results_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(id)
);
```

### 2. Risk Assessment Results
```sql
CREATE TABLE public.risk_assessment_results (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    risk_category text NOT NULL, -- financial, operational, compliance, etc.
    risk_level text NOT NULL, -- low, medium, high, critical
    risk_score numeric(5,2), -- 0.00 to 100.00
    risk_description text NOT NULL,
    impact_analysis jsonb, -- Detailed impact assessment
    mitigation_recommendations jsonb, -- Risk mitigation suggestions
    business_rule_id uuid, -- Which business rule triggered this
    compliance_flags jsonb, -- Compliance issues identified
    metadata jsonb DEFAULT '{}',
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT risk_assessment_results_pkey PRIMARY KEY (id),
    CONSTRAINT risk_assessment_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT risk_assessment_results_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT risk_assessment_results_business_rule_id_fkey FOREIGN KEY (business_rule_id) REFERENCES public.business_rules(id)
);
```

### 3. Generated Reports
```sql
CREATE TABLE public.generated_reports (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    report_definition_id uuid NOT NULL,
    report_type text NOT NULL, -- summary, detailed, compliance, etc.
    report_format text NOT NULL, -- PDF, HTML, DOCX, JSON
    report_content jsonb NOT NULL, -- Structured report data
    report_binary bytea, -- Binary content (PDF, DOCX)
    storage_path text, -- File storage location
    generated_at timestamp with time zone NOT NULL DEFAULT now(),
    expires_at timestamp with time zone,
    download_count integer NOT NULL DEFAULT 0,
    metadata jsonb DEFAULT '{}',
    
    CONSTRAINT generated_reports_pkey PRIMARY KEY (id),
    CONSTRAINT generated_reports_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT generated_reports_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT generated_reports_report_definition_id_fkey FOREIGN KEY (report_definition_id) REFERENCES public.report_definitions(id)
);
```

### 4. Agent Workflow Results (Overall Summary)
```sql
CREATE TABLE public.agent_workflow_results (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    document_id uuid NOT NULL,
    workflow_status text NOT NULL, -- completed, partial, failed
    overall_confidence numeric(5,4),
    processing_summary jsonb NOT NULL, -- Summary of all agent outputs
    key_findings jsonb, -- Important discoveries
    compliance_status text, -- compliant, non_compliant, needs_review
    recommendations jsonb, -- Overall recommendations
    metadata jsonb DEFAULT '{}',
    completed_at timestamp with time zone NOT NULL DEFAULT now(),
    
    CONSTRAINT agent_workflow_results_pkey PRIMARY KEY (id),
    CONSTRAINT agent_workflow_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.processing_sessions(id) ON DELETE CASCADE,
    CONSTRAINT agent_workflow_results_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id)
);
```

## 🔄 Current Implementation Issues

### 1. Agent Pipeline NOT Using Master Tables
**Problem:** The current `background_processor_v2.py` hardcodes agent logic instead of reading from:
- `agent_prompts` table for agent instructions
- `business_rules` table for organization-specific rules
- `queries` table for what to extract
- `sections` table for document structure

### 2. No Result Storage
**Problem:** Agent outputs are not persisted:
- Extractions are not stored
- Risk assessments are not saved
- Generated reports are not persisted
- Results are lost after processing

### 3. No Business Rule Integration
**Problem:** Agents don't apply organization-specific business rules:
- No dynamic rule evaluation
- No custom normalization patterns
- No organization-specific compliance checks

## 🎯 Required Actions

### 1. Create Output Tables
- Implement the 4 output tables above
- Add proper foreign key relationships
- Add indexes for performance

### 2. Update Agent Pipeline
- Modify agents to read from master tables
- Implement result storage in output tables
- Add business rule evaluation logic

### 3. Database Integration
- Update `database_service.py` with new table operations
- Add CRUD operations for output tables
- Implement result retrieval APIs

### 4. Frontend Updates
- Update components to display stored results
- Add result viewing/download functionality
- Show business rule evaluation results

## 📊 Impact Assessment

**Without proper table integration:**
- ❌ Agents operate with hardcoded logic
- ❌ No organization customization
- ❌ Results are not persisted
- ❌ No compliance tracking
- ❌ No business rule application

**With proper table integration:**
- ✅ Dynamic, configurable agent behavior
- ✅ Organization-specific processing
- ✅ Persistent result storage
- ✅ Compliance monitoring
- ✅ Business rule enforcement
- ✅ Audit trail for all processing

## 🏆 Recommendation

**IMMEDIATE ACTION REQUIRED:** The 3-Agent pipeline needs significant database integration work to be production-ready for enterprise use.