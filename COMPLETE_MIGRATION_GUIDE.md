# Complete Database Migration Guide

## 🚨 CRITICAL: Run Migrations in Exact Order

You need to run **3 migrations in sequence** to get the full corrected workflow system working.

## 📋 Migration Sequence

### **Step 1: Processing Sessions Tables (Foundation)**
**File:** `database/migrations/001b_processing_sessions_table.sql`
**Creates:** 4 core tables needed by the workflow system
- `processing_sessions` 
- `agent_pipeline_states`
- `background_jobs`
- `agent_processing_logs`

### **Step 2: Agent Output Tables** 
**File:** `database/migrations/002_agent_output_tables.sql`
**Creates:** 5 tables for storing agent results
- `agent_extraction_results`
- `risk_assessment_results` 
- `generated_reports`
- `agent_workflow_results`
- `agent_processing_logs` (if not exists)

### **Step 3: Workflow Enhancement Tables**
**File:** `database/migrations/003_workflow_enhancement_tables.sql`
**Creates:** 6 tables for the corrected stage-dependent workflow
- `document_section_instances`
- `query_execution_results`
- `normalization_applications`
- `business_rule_evaluations`
- `agent_prompt_applications`
- `workflow_stage_completions`

## 🎯 How to Execute (Supabase Dashboard)

### **For Each Migration (repeat 3 times):**

1. **Open Supabase Dashboard**
   - Go to https://supabase.com/dashboard
   - Select your NMTC project

2. **Open SQL Editor**
   - Click "SQL Editor" in left sidebar
   - Click "New Query"

3. **Copy Migration SQL**
   - Copy ALL content from the migration file
   - Paste into SQL Editor

4. **Execute Migration** 
   - Click "Run" button
   - Wait for completion (10-20 seconds each)
   - Check for success message

5. **Verify Tables Created**
   - Go to "Table Editor" 
   - Confirm new tables appear

## 🧪 After All 3 Migrations

Run this test to verify everything works:

```bash
python simple_table_test.py
```

**Expected Result:**
```
PASS: document_section_instances
PASS: query_execution_results  
PASS: normalization_applications
PASS: business_rule_evaluations
PASS: agent_prompt_applications
PASS: workflow_stage_completions

Results: 6/6 tables accessible
SUCCESS: All workflow tables are working!
```

## 📊 Total Tables Created: 15

**Foundation (4 tables):**
- processing_sessions
- agent_pipeline_states  
- background_jobs
- agent_processing_logs

**Agent Output (5 tables):**
- agent_extraction_results
- risk_assessment_results
- generated_reports
- agent_workflow_results
- (agent_processing_logs - already exists)

**Workflow Enhancement (6 tables):**
- document_section_instances
- query_execution_results
- normalization_applications
- business_rule_evaluations
- agent_prompt_applications
- workflow_stage_completions

## 🎉 What You Get After Migration

✅ **Corrected Stage-Dependent Workflow**
- Proper sequence: Document Type → Sections → Queries → Normalization → Business Rules → Risk Assessment → **Agent Prompts** → Reports

✅ **Complete Database Integration**
- All master tables properly referenced
- Full result storage and retrieval
- Organization-level data isolation

✅ **Enterprise Features**
- Real-time progress tracking
- Complete audit trail
- Risk assessment with business rules
- Professional results dashboard

✅ **API Endpoints Ready**
- `/api/documents/{id}/workflow-results`
- `/api/documents/{id}/extraction-results` 
- `/api/documents/{id}/risk-assessment`
- `/api/documents/{id}/reports`
- `/api/documents/{id}/processing-sessions`

✅ **Frontend Components Ready**
- WorkflowResultsDashboard component
- Enhanced results validation interface
- Custom useWorkflowResults hook

## 🚀 Ready for Production Testing

Once all migrations are complete, the entire corrected workflow system will be fully functional and ready for document processing testing!