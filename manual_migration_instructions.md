# Manual Database Migration Instructions

## ❌ Why the Tables Weren't Created

The tables weren't created because:

1. **Supabase REST API Limitation**: The Supabase Python client uses the REST API, which doesn't support DDL operations (CREATE TABLE, ALTER TABLE, etc.)
2. **DDL operations require direct PostgreSQL access** through the SQL editor or direct database connection

## ✅ How to Create the Tables

### **Method 1: Supabase Dashboard SQL Editor (RECOMMENDED)**

1. **Go to Supabase Dashboard**
   - Login to https://supabase.com/dashboard
   - Select your NMTC project

2. **Open SQL Editor**
   - Click on "SQL Editor" in the left sidebar
   - Click "New Query"

3. **Copy and Paste the Migration SQL**
   - Copy ALL the content from `database/migrations/003_workflow_enhancement_tables.sql`
   - Paste it into the SQL editor

4. **Execute the Migration**
   - Click the "Run" button
   - Wait for completion (should take a few seconds)

5. **Verify Table Creation**
   - Go to "Table Editor" in the left sidebar
   - You should see 6 new tables:
     - `document_section_instances`
     - `query_execution_results`
     - `normalization_applications`
     - `business_rule_evaluations`
     - `agent_prompt_applications`
     - `workflow_stage_completions`

### **Method 2: Direct PostgreSQL Connection**

If you prefer command line:

1. **Get Connection String**
   - Supabase Dashboard > Settings > Database > Connection string > URI
   - Format: `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`

2. **Connect and Execute**
   ```bash
   psql 'postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres'
   \i database/migrations/003_workflow_enhancement_tables.sql
   ```

## 🎯 After Creating the Tables

Once you've created the tables using either method above, you can verify by running:

```python
python test_tables.py
```

This will test if all the new tables are accessible and working properly.

## 📋 Migration SQL Summary

The migration creates these 6 tables with proper:
- **Foreign key relationships** to existing tables
- **Indexes** for performance
- **Row Level Security (RLS)** policies for organization isolation
- **Utility functions** for workflow progress tracking

**Tables being created:**
1. `document_section_instances` - Track identified sections per document
2. `query_execution_results` - Store query application results
3. `normalization_applications` - Record normalization rule applications
4. `business_rule_evaluations` - Track business rule validations
5. `agent_prompt_applications` - Record agent prompt usage (at results stage)
6. `workflow_stage_completions` - Track each workflow stage completion

## 🚨 Important Notes

- **Run the migration exactly once** to avoid duplicate table errors
- **All tables have proper foreign key constraints** to existing tables
- **RLS policies ensure organization-level data isolation**
- **The migration is safe to run** - it won't affect existing data