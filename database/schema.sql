-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.agent_prompts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  agent_key text NOT NULL,
  version text NOT NULL,
  status USER-DEFINED NOT NULL DEFAULT 'active'::status_state,
  system_prompt text NOT NULL,
  task_prompt text NOT NULL,
  style_guide text,
  output_schema_json jsonb NOT NULL,
  guardrails text,
  created_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  document_type_id uuid,
  prompt_role_id uuid,
  CONSTRAINT agent_prompts_pkey PRIMARY KEY (id),
  CONSTRAINT agent_prompts_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id),
  CONSTRAINT agent_prompts_prompt_role_id_fkey FOREIGN KEY (prompt_role_id) REFERENCES public.prompt_roles(id),
  CONSTRAINT agent_prompts_document_type_id_fkey FOREIGN KEY (document_type_id) REFERENCES public.document_types(id)
);
CREATE TABLE public.api_keys (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key_name text NOT NULL,
  api_key text NOT NULL UNIQUE,
  key_prefix text NOT NULL,
  permissions jsonb NOT NULL DEFAULT '{}'::jsonb,
  rate_limit integer DEFAULT 1000,
  is_active boolean NOT NULL DEFAULT true,
  last_used_at timestamp with time zone,
  expires_at timestamp with time zone,
  created_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT api_keys_pkey PRIMARY KEY (id),
  CONSTRAINT api_keys_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id)
);
CREATE TABLE public.audit_categories (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  severity_level text NOT NULL DEFAULT 'info'::text,
  retention_days integer NOT NULL DEFAULT 365,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT audit_categories_pkey PRIMARY KEY (id)
);
CREATE TABLE public.audit_log (
  id bigint NOT NULL DEFAULT nextval('audit_log_id_seq'::regclass),
  org_id uuid,
  actor_user_id uuid,
  scope text NOT NULL,
  record_id uuid,
  action text NOT NULL,
  diff jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  category_id uuid,
  ip_address inet,
  user_agent text,
  CONSTRAINT audit_log_pkey PRIMARY KEY (id),
  CONSTRAINT audit_log_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES auth.users(id),
  CONSTRAINT audit_log_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id),
  CONSTRAINT audit_log_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.audit_categories(id)
);
CREATE TABLE public.billing_status_types (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  is_active boolean NOT NULL DEFAULT true,
  order_index integer NOT NULL DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT billing_status_types_pkey PRIMARY KEY (id)
);
CREATE TABLE public.business_rules (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid,
  owner_scope USER-DEFINED NOT NULL DEFAULT 'template'::owner_scope,
  document_type_id uuid,
  rule_key text NOT NULL,
  condition_json jsonb NOT NULL,
  action_json jsonb NOT NULL,
  priority integer NOT NULL DEFAULT 100,
  notes text,
  status USER-DEFINED NOT NULL DEFAULT 'active'::status_state,
  version integer NOT NULL DEFAULT 1,
  created_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  org_id_eff uuid DEFAULT COALESCE(org_id, '00000000-0000-0000-0000-000000000000'::uuid),
  description_text text,
  ai_generated boolean DEFAULT false,
  rule_confidence numeric DEFAULT NULL::numeric,
  status_id uuid NOT NULL,
  CONSTRAINT business_rules_pkey PRIMARY KEY (id),
  CONSTRAINT business_rules_document_type_id_fkey FOREIGN KEY (document_type_id) REFERENCES public.document_types(id),
  CONSTRAINT business_rules_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id),
  CONSTRAINT business_rules_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id),
  CONSTRAINT business_rules_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status_types(id)
);
CREATE TABLE public.conflict_policies (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  precedence_order ARRAY NOT NULL,
  resolution_action text NOT NULL,
  version integer NOT NULL DEFAULT 1,
  status USER-DEFINED NOT NULL DEFAULT 'active'::status_state,
  notes text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT conflict_policies_pkey PRIMARY KEY (id)
);
CREATE TABLE public.contact_roles (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  order_index integer NOT NULL DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT contact_roles_pkey PRIMARY KEY (id)
);
CREATE TABLE public.document_categories (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  version text NOT NULL DEFAULT '1.0.0'::text,
  status text NOT NULL DEFAULT 'active'::text,
  created_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT document_categories_pkey PRIMARY KEY (id),
  CONSTRAINT document_categories_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id)
);
CREATE TABLE public.document_types (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid,
  owner_scope USER-DEFINED NOT NULL DEFAULT 'template'::owner_scope,
  parent_id uuid,
  key text NOT NULL,
  display_name text NOT NULL,
  version text NOT NULL CHECK (version ~ '^[0-9]+(\.[0-9]+){1,2}$'::text),
  status USER-DEFINED NOT NULL DEFAULT 'draft'::status_state,
  notes text,
  created_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  org_id_eff uuid DEFAULT COALESCE(org_id, '00000000-0000-0000-0000-000000000000'::uuid),
  category_id uuid,
  status_id uuid NOT NULL,
  workflow_state_id uuid NOT NULL,
  CONSTRAINT document_types_pkey PRIMARY KEY (id),
  CONSTRAINT document_types_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id),
  CONSTRAINT document_types_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.document_types(id),
  CONSTRAINT document_types_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id),
  CONSTRAINT document_types_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status_types(id),
  CONSTRAINT document_types_workflow_state_id_fkey FOREIGN KEY (workflow_state_id) REFERENCES public.workflow_states(id),
  CONSTRAINT document_types_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.document_categories(id)
);
CREATE TABLE public.documents (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL,
  document_type_id uuid,
  filename text NOT NULL,
  storage_path text NOT NULL,
  mime_type text NOT NULL,
  hash bytea,
  uploaded_by uuid NOT NULL,
  uploaded_at timestamp with time zone NOT NULL DEFAULT now(),
  ocr_status USER-DEFINED NOT NULL DEFAULT 'queued'::ocr_status,
  parsed_index jsonb,
  CONSTRAINT documents_pkey PRIMARY KEY (id),
  CONSTRAINT documents_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id),
  CONSTRAINT documents_document_type_id_fkey FOREIGN KEY (document_type_id) REFERENCES public.document_types(id),
  CONSTRAINT documents_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES auth.users(id)
);
CREATE TABLE public.extractions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL,
  query_id uuid NOT NULL,
  raw_answer text,
  normalized_value jsonb,
  confidence numeric,
  citation jsonb,
  run_id uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT extractions_pkey PRIMARY KEY (id),
  CONSTRAINT extractions_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
  CONSTRAINT extractions_query_id_fkey FOREIGN KEY (query_id) REFERENCES public.queries(id)
);
CREATE TABLE public.industry_types (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  order_index integer NOT NULL DEFAULT 0,
  status_id uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT industry_types_pkey PRIMARY KEY (id),
  CONSTRAINT industry_types_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status_types(id)
);
CREATE TABLE public.integration_configs (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  service_name text NOT NULL UNIQUE,
  config_data jsonb NOT NULL,
  is_enabled boolean NOT NULL DEFAULT true,
  connection_status text DEFAULT 'untested'::text,
  last_tested_at timestamp with time zone,
  test_result jsonb,
  created_by uuid NOT NULL,
  updated_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT integration_configs_pkey PRIMARY KEY (id),
  CONSTRAINT integration_configs_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id),
  CONSTRAINT integration_configs_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES auth.users(id)
);
CREATE TABLE public.normalization_rules (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid,
  owner_scope USER-DEFINED NOT NULL DEFAULT 'template'::owner_scope,
  document_type_id uuid,
  rule_type USER-DEFINED NOT NULL,
  pattern text NOT NULL,
  normalized_value jsonb NOT NULL,
  priority integer NOT NULL DEFAULT 100,
  notes text,
  status USER-DEFINED NOT NULL DEFAULT 'active'::status_state,
  version integer NOT NULL DEFAULT 1,
  created_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  org_id_eff uuid DEFAULT COALESCE(org_id, '00000000-0000-0000-0000-000000000000'::uuid),
  description_text text,
  ai_generated boolean DEFAULT false,
  pattern_confidence numeric DEFAULT NULL::numeric,
  status_id uuid NOT NULL,
  CONSTRAINT normalization_rules_pkey PRIMARY KEY (id),
  CONSTRAINT normalization_rules_document_type_id_fkey FOREIGN KEY (document_type_id) REFERENCES public.document_types(id),
  CONSTRAINT normalization_rules_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id),
  CONSTRAINT normalization_rules_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id),
  CONSTRAINT normalization_rules_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status_types(id)
);
CREATE TABLE public.obligations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL,
  document_id uuid NOT NULL,
  obligation_key text NOT NULL,
  document text NOT NULL,
  section text NOT NULL,
  obligation text NOT NULL,
  frequency USER-DEFINED NOT NULL,
  due_rule text,
  next_due_date date,
  responsible_party USER-DEFINED NOT NULL,
  risk USER-DEFINED NOT NULL,
  source_citation jsonb,
  dependencies ARRAY NOT NULL DEFAULT '{}'::text[],
  notes text,
  status USER-DEFINED NOT NULL DEFAULT 'open'::obligation_status,
  computed_due_dates jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT obligations_pkey PRIMARY KEY (id),
  CONSTRAINT obligations_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id),
  CONSTRAINT obligations_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id)
);
CREATE TABLE public.org_members (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role USER-DEFINED NOT NULL DEFAULT 'viewer'::org_role,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  role_id uuid NOT NULL,
  CONSTRAINT org_members_pkey PRIMARY KEY (id),
  CONSTRAINT org_members_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.user_roles(id),
  CONSTRAINT org_members_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id),
  CONSTRAINT org_members_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id)
);
CREATE TABLE public.organization_billing (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL,
  billing_status_id uuid NOT NULL,
  next_billing_date date,
  last_invoice_date date,
  payment_method text,
  billing_contact_id uuid,
  invoice_email text,
  billing_notes text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT organization_billing_pkey PRIMARY KEY (id),
  CONSTRAINT organization_billing_billing_status_id_fkey FOREIGN KEY (billing_status_id) REFERENCES public.billing_status_types(id),
  CONSTRAINT organization_billing_billing_contact_id_fkey FOREIGN KEY (billing_contact_id) REFERENCES public.organization_contacts(id),
  CONSTRAINT organization_billing_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id)
);
CREATE TABLE public.organization_contacts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL,
  contact_role_id uuid NOT NULL,
  name text NOT NULL,
  email text NOT NULL,
  phone text,
  title text,
  is_primary boolean NOT NULL DEFAULT false,
  status_id uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT organization_contacts_pkey PRIMARY KEY (id),
  CONSTRAINT organization_contacts_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id),
  CONSTRAINT organization_contacts_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status_types(id),
  CONSTRAINT organization_contacts_contact_role_id_fkey FOREIGN KEY (contact_role_id) REFERENCES public.contact_roles(id)
);
CREATE TABLE public.organization_plans (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL,
  plan_type_id uuid NOT NULL,
  effective_date date NOT NULL DEFAULT CURRENT_DATE,
  end_date date,
  custom_document_limit integer,
  custom_user_limit integer,
  custom_monthly_price numeric,
  notes text,
  status_id uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT organization_plans_pkey PRIMARY KEY (id),
  CONSTRAINT organization_plans_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id),
  CONSTRAINT organization_plans_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status_types(id),
  CONSTRAINT organization_plans_plan_type_id_fkey FOREIGN KEY (plan_type_id) REFERENCES public.plan_types(id)
);
CREATE TABLE public.organization_usage (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL,
  usage_month date NOT NULL,
  documents_processed integer NOT NULL DEFAULT 0,
  storage_used_gb numeric NOT NULL DEFAULT 0,
  api_calls integer NOT NULL DEFAULT 0,
  processing_minutes numeric NOT NULL DEFAULT 0,
  monthly_spend numeric NOT NULL DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT organization_usage_pkey PRIMARY KEY (id),
  CONSTRAINT organization_usage_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id)
);
CREATE TABLE public.organizations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  created_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  status_id uuid NOT NULL,
  industry_type_id uuid,
  CONSTRAINT organizations_pkey PRIMARY KEY (id),
  CONSTRAINT organizations_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status_types(id),
  CONSTRAINT organizations_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id),
  CONSTRAINT organizations_industry_type_id_fkey FOREIGN KEY (industry_type_id) REFERENCES public.industry_types(id)
);
CREATE TABLE public.plan_types (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  monthly_price numeric NOT NULL,
  document_limit integer NOT NULL,
  user_limit integer NOT NULL,
  storage_limit_gb numeric NOT NULL,
  features jsonb NOT NULL DEFAULT '{}'::jsonb,
  order_index integer NOT NULL DEFAULT 0,
  status_id uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT plan_types_pkey PRIMARY KEY (id),
  CONSTRAINT plan_types_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status_types(id)
);
CREATE TABLE public.prompt_roles (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  order_index integer NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'active'::text CHECK (status = ANY (ARRAY['active'::text, 'archived'::text])),
  created_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT prompt_roles_pkey PRIMARY KEY (id),
  CONSTRAINT prompt_roles_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id)
);
CREATE TABLE public.prompt_variables (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  agent_prompt_id uuid NOT NULL,
  name text NOT NULL,
  source USER-DEFINED NOT NULL,
  required boolean NOT NULL DEFAULT false,
  default_value jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT prompt_variables_pkey PRIMARY KEY (id),
  CONSTRAINT prompt_variables_agent_prompt_id_fkey FOREIGN KEY (agent_prompt_id) REFERENCES public.agent_prompts(id)
);
CREATE TABLE public.queries (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  document_type_id uuid NOT NULL,
  section_id uuid NOT NULL,
  query_key text NOT NULL,
  question_text text NOT NULL,
  extractors jsonb NOT NULL DEFAULT '[]'::jsonb,
  normalizer_hint text,
  required boolean NOT NULL DEFAULT false,
  version integer NOT NULL DEFAULT 1,
  status USER-DEFINED NOT NULL DEFAULT 'active'::status_state,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT queries_pkey PRIMARY KEY (id),
  CONSTRAINT queries_document_type_id_fkey FOREIGN KEY (document_type_id) REFERENCES public.document_types(id),
  CONSTRAINT queries_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.sections(id)
);
CREATE TABLE public.recurrence_rules (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  frequency USER-DEFINED NOT NULL,
  periods_per_year integer NOT NULL,
  scheduler_logic text NOT NULL,
  default_period_endpoints text NOT NULL,
  version integer NOT NULL DEFAULT 1,
  status USER-DEFINED NOT NULL DEFAULT 'active'::status_state,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT recurrence_rules_pkey PRIMARY KEY (id)
);
CREATE TABLE public.report_definitions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  org_id uuid,
  owner_scope USER-DEFINED NOT NULL DEFAULT 'template'::owner_scope,
  parent_id uuid,
  report_key text NOT NULL,
  version text NOT NULL,
  status USER-DEFINED NOT NULL DEFAULT 'active'::status_state,
  template_json jsonb NOT NULL,
  binding_rules jsonb NOT NULL DEFAULT '{}'::jsonb,
  export_capabilities ARRAY NOT NULL DEFAULT '{PDF,HTML,DOCX,ICS}'::text[],
  notes text,
  created_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  org_id_eff uuid DEFAULT COALESCE(org_id, '00000000-0000-0000-0000-000000000000'::uuid),
  CONSTRAINT report_definitions_pkey PRIMARY KEY (id),
  CONSTRAINT report_definitions_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.report_definitions(id),
  CONSTRAINT report_definitions_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id),
  CONSTRAINT report_definitions_org_id_fkey FOREIGN KEY (org_id) REFERENCES public.organizations(id)
);
CREATE TABLE public.report_mappings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  report_definition_id uuid NOT NULL,
  mapping_type text NOT NULL DEFAULT 'obligation_key'::text,
  key_value text NOT NULL,
  filter_logic_json jsonb,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT report_mappings_pkey PRIMARY KEY (id),
  CONSTRAINT report_mappings_report_definition_id_fkey FOREIGN KEY (report_definition_id) REFERENCES public.report_definitions(id)
);
CREATE TABLE public.sections (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  document_type_id uuid NOT NULL,
  canonical_name text NOT NULL,
  order_no integer NOT NULL DEFAULT 0,
  anchor_patterns ARRAY NOT NULL DEFAULT '{}'::text[],
  ml_fallback_model text,
  notes text,
  version integer NOT NULL DEFAULT 1,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT sections_pkey PRIMARY KEY (id),
  CONSTRAINT sections_document_type_id_fkey FOREIGN KEY (document_type_id) REFERENCES public.document_types(id)
);
CREATE TABLE public.status_types (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  order_index integer NOT NULL DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT status_types_pkey PRIMARY KEY (id)
);
CREATE TABLE public.superadmins (
  user_id uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT superadmins_pkey PRIMARY KEY (user_id),
  CONSTRAINT superadmins_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.system_alerts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  alert_type text NOT NULL,
  threshold_value numeric NOT NULL,
  threshold_operator text NOT NULL DEFAULT 'greater_than'::text,
  is_enabled boolean NOT NULL DEFAULT true,
  notification_methods jsonb NOT NULL DEFAULT '["email"]'::jsonb,
  recipients jsonb NOT NULL DEFAULT '[]'::jsonb,
  description text,
  last_triggered_at timestamp with time zone,
  created_by uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT system_alerts_pkey PRIMARY KEY (id),
  CONSTRAINT system_alerts_created_by_fkey FOREIGN KEY (created_by) REFERENCES auth.users(id)
);
CREATE TABLE public.system_metrics (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  metric_name text NOT NULL,
  metric_value numeric NOT NULL,
  metric_unit text,
  recorded_at timestamp with time zone NOT NULL DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb,
  CONSTRAINT system_metrics_pkey PRIMARY KEY (id)
);
CREATE TABLE public.system_settings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  value jsonb NOT NULL,
  category text NOT NULL,
  description text,
  data_type text NOT NULL DEFAULT 'string'::text,
  is_sensitive boolean NOT NULL DEFAULT false,
  updated_by uuid NOT NULL,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT system_settings_pkey PRIMARY KEY (id),
  CONSTRAINT system_settings_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES auth.users(id)
);
CREATE TABLE public.user_roles (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  permissions jsonb NOT NULL DEFAULT '{}'::jsonb,
  can_manage_users boolean NOT NULL DEFAULT false,
  can_view_billing boolean NOT NULL DEFAULT false,
  can_upload_documents boolean NOT NULL DEFAULT true,
  can_generate_reports boolean NOT NULL DEFAULT true,
  can_view_analytics boolean NOT NULL DEFAULT false,
  order_index integer NOT NULL DEFAULT 0,
  status_id uuid NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT user_roles_pkey PRIMARY KEY (id),
  CONSTRAINT user_roles_status_id_fkey FOREIGN KEY (status_id) REFERENCES public.status_types(id)
);
CREATE TABLE public.workflow_states (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  key text NOT NULL UNIQUE,
  display_name text NOT NULL,
  description text,
  can_edit boolean NOT NULL DEFAULT true,
  order_index integer NOT NULL DEFAULT 0,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT workflow_states_pkey PRIMARY KEY (id)
);