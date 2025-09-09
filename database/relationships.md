### Database relationships overview

This document summarizes the key foreign-key relationships defined in `schema.sql`. Only the most relevant columns are shown for clarity.

#### Table: `agent_prompts`
- created_by → auth.users.id
- prompt_role_id → public.prompt_roles.id
- document_type_id → public.document_types.id

#### Table: `api_keys`
- created_by → auth.users.id

#### Table: `audit_log`
- actor_user_id → auth.users.id
- org_id → public.organizations.id
- category_id → public.audit_categories.id

#### Table: `business_rules`
- document_type_id → public.document_types.id
- org_id → public.organizations.id
- created_by → auth.users.id
- status_id → public.status_types.id

#### Table: `document_categories`
- created_by → auth.users.id

#### Table: `document_types`
- parent_id → public.document_types.id (self-reference)
- created_by → auth.users.id
- org_id → public.organizations.id
- status_id → public.status_types.id
- workflow_state_id → public.workflow_states.id
- category_id → public.document_categories.id

#### Table: `documents`
- org_id → public.organizations.id
- document_type_id → public.document_types.id
- uploaded_by → auth.users.id

#### Table: `extractions`
- document_id → public.documents.id
- query_id → public.queries.id

#### Table: `industry_types`
- status_id → public.status_types.id

#### Table: `integration_configs`
- created_by → auth.users.id
- updated_by → auth.users.id

#### Table: `normalization_rules`
- document_type_id → public.document_types.id
- created_by → auth.users.id
- org_id → public.organizations.id
- status_id → public.status_types.id

#### Table: `obligations`
- document_id → public.documents.id
- org_id → public.organizations.id

#### Table: `org_members`
- role_id → public.user_roles.id
- user_id → auth.users.id
- org_id → public.organizations.id

#### Table: `organization_billing`
- billing_status_id → public.billing_status_types.id
- billing_contact_id → public.organization_contacts.id
- org_id → public.organizations.id

#### Table: `organization_contacts`
- org_id → public.organizations.id
- status_id → public.status_types.id
- contact_role_id → public.contact_roles.id

#### Table: `organization_plans`
- org_id → public.organizations.id
- status_id → public.status_types.id
- plan_type_id → public.plan_types.id

#### Table: `organization_usage`
- org_id → public.organizations.id

#### Table: `organizations`
- status_id → public.status_types.id
- created_by → auth.users.id
- industry_type_id → public.industry_types.id

#### Table: `plan_types`
- status_id → public.status_types.id

#### Table: `prompt_roles`
- created_by → auth.users.id

#### Table: `prompt_variables`
- agent_prompt_id → public.agent_prompts.id

#### Table: `queries`
- document_type_id → public.document_types.id
- section_id → public.sections.id

#### Table: `report_definitions`
- parent_id → public.report_definitions.id (self-reference)
- created_by → auth.users.id
- org_id → public.organizations.id

#### Table: `report_mappings`
- report_definition_id → public.report_definitions.id

#### Table: `sections`
- document_type_id → public.document_types.id

#### Table: `superadmins`
- user_id → auth.users.id

#### Table: `system_alerts`
- created_by → auth.users.id

#### Table: `system_settings`
- updated_by → auth.users.id

#### Table: `user_roles`
- status_id → public.status_types.id

#### Table: `workflow_states`
- (no foreign keys)

Notes:
- Several tables reference Postgres schemas outside `public` (e.g., `auth.users`). Ensure those schemas are available (as on Supabase).
- Self-referencing relationships occur on `document_types.parent_id` and `report_definitions.parent_id`.

