from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from enum import Enum
import uuid


# Enums matching database schema
class StatusState(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class OwnerScope(str, Enum):
    TEMPLATE = "template"
    ORGANIZATION = "organization"


class OcrStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    DONE = "done"  # From seed data
    UPLOADED = "uploaded"  # From existing code


class OrgRole(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor" 
    ADMIN = "admin"
    OWNER = "owner"


class ObligationFrequency(str, Enum):
    ONE_TIME = "one_time"
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"


class ResponsibleParty(str, Enum):
    CDE = "cde"
    QALICB = "qalicb" 
    INVESTOR = "investor"
    THIRD_PARTY = "third_party"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ObligationStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CLOSED = "closed"


class NormalizationRuleType(str, Enum):
    DATE_FORMAT = "date_format"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    TEXT_NORMALIZATION = "text_normalization"


class PromptVariableSource(str, Enum):
    DOCUMENT = "document"
    USER_INPUT = "user_input"
    SYSTEM = "system"
    COMPUTED = "computed"


# Base Model
class BaseDBModel(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True
        use_enum_values = True


# Core Tables from schema.sql

class StatusType(BaseDBModel):
    """status_types table"""
    key: str = Field(..., unique=True)
    display_name: str
    description: Optional[str] = None
    order_index: int = 0


class IndustryType(BaseDBModel):
    """industry_types table"""
    key: str = Field(..., unique=True)
    display_name: str
    description: Optional[str] = None
    order_index: int = 0
    status_id: uuid.UUID


class Organization(BaseDBModel):
    """organizations table"""
    name: str = Field(..., unique=True)
    created_by: uuid.UUID
    status_id: uuid.UUID
    industry_type_id: Optional[uuid.UUID] = None


class UserRole(BaseDBModel):
    """user_roles table"""
    key: str = Field(..., unique=True)
    display_name: str
    description: Optional[str] = None
    permissions: Dict[str, Any] = Field(default_factory=dict)
    can_manage_users: bool = False
    can_view_billing: bool = False
    can_upload_documents: bool = True
    can_generate_reports: bool = True
    can_view_analytics: bool = False
    order_index: int = 0
    status_id: uuid.UUID


class OrgMember(BaseDBModel):
    """org_members table"""
    org_id: uuid.UUID
    user_id: uuid.UUID
    role: OrgRole = OrgRole.VIEWER
    role_id: uuid.UUID


class Superadmin(BaseModel):
    """superadmins table"""
    user_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class DocumentCategory(BaseDBModel):
    """document_categories table"""
    key: str = Field(..., unique=True)
    display_name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    status: str = "active"
    created_by: uuid.UUID


class WorkflowState(BaseDBModel):
    """workflow_states table"""
    key: str = Field(..., unique=True)
    display_name: str
    description: Optional[str] = None
    can_edit: bool = True
    order_index: int = 0


class DocumentType(BaseDBModel):
    """document_types table"""
    org_id: Optional[uuid.UUID] = None
    owner_scope: OwnerScope = OwnerScope.TEMPLATE
    parent_id: Optional[uuid.UUID] = None
    key: str
    display_name: str
    version: str = Field(..., pattern=r'^[0-9]+(\.[0-9]+){1,2}$')
    status: StatusState = StatusState.DRAFT
    notes: Optional[str] = None
    created_by: uuid.UUID
    org_id_eff: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    status_id: uuid.UUID
    workflow_state_id: uuid.UUID


class Document(BaseDBModel):
    """documents table"""
    org_id: uuid.UUID
    document_type_id: Optional[uuid.UUID] = None
    filename: str
    storage_path: str
    mime_type: str
    hash: Optional[bytes] = None
    uploaded_by: uuid.UUID
    uploaded_at: datetime = Field(default_factory=datetime.now)
    ocr_status: OcrStatus = OcrStatus.QUEUED
    parsed_index: Optional[Dict[str, Any]] = None


class Section(BaseDBModel):
    """sections table"""
    document_type_id: uuid.UUID
    canonical_name: str
    order_no: int = 0
    anchor_patterns: List[str] = Field(default_factory=list)
    ml_fallback_model: Optional[str] = None
    notes: Optional[str] = None
    version: int = 1


class Query(BaseDBModel):
    """queries table"""
    document_type_id: uuid.UUID
    section_id: uuid.UUID
    query_key: str
    question_text: str
    extractors: List[Dict[str, Any]] = Field(default_factory=list)
    normalizer_hint: Optional[str] = None
    required: bool = False
    version: int = 1
    status: StatusState = StatusState.ACTIVE


class Extraction(BaseDBModel):
    """extractions table"""
    document_id: uuid.UUID
    query_id: uuid.UUID
    raw_answer: Optional[str] = None
    normalized_value: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    citation: Optional[Dict[str, Any]] = None
    run_id: uuid.UUID


class Obligation(BaseDBModel):
    """obligations table"""
    org_id: uuid.UUID
    document_id: uuid.UUID
    obligation_key: str
    document: str
    section: str
    obligation: str
    frequency: ObligationFrequency
    due_rule: Optional[str] = None
    next_due_date: Optional[date] = None
    responsible_party: ResponsibleParty
    risk: RiskLevel
    source_citation: Optional[Dict[str, Any]] = None
    dependencies: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    status: ObligationStatus = ObligationStatus.OPEN
    computed_due_dates: Optional[Dict[str, Any]] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class BusinessRule(BaseDBModel):
    """business_rules table"""
    org_id: Optional[uuid.UUID] = None
    owner_scope: OwnerScope = OwnerScope.TEMPLATE
    document_type_id: Optional[uuid.UUID] = None
    rule_key: str
    condition_json: Dict[str, Any]
    action_json: Dict[str, Any]
    priority: int = 100
    notes: Optional[str] = None
    status: StatusState = StatusState.ACTIVE
    version: int = 1
    created_by: uuid.UUID
    org_id_eff: Optional[uuid.UUID] = None
    description_text: Optional[str] = None
    ai_generated: bool = False
    rule_confidence: Optional[float] = None
    status_id: uuid.UUID


class NormalizationRule(BaseDBModel):
    """normalization_rules table"""
    org_id: Optional[uuid.UUID] = None
    owner_scope: OwnerScope = OwnerScope.TEMPLATE
    document_type_id: Optional[uuid.UUID] = None
    rule_type: NormalizationRuleType
    pattern: str
    normalized_value: Dict[str, Any]
    priority: int = 100
    notes: Optional[str] = None
    status: StatusState = StatusState.ACTIVE
    version: int = 1
    created_by: uuid.UUID
    org_id_eff: Optional[uuid.UUID] = None
    description_text: Optional[str] = None
    ai_generated: bool = False
    pattern_confidence: Optional[float] = None
    status_id: uuid.UUID


class PromptRole(BaseDBModel):
    """prompt_roles table"""
    key: str = Field(..., unique=True)
    display_name: str
    description: Optional[str] = None
    order_index: int = 0
    status: str = "active"
    created_by: uuid.UUID

    @validator('status')
    def validate_status(cls, v):
        if v not in ['active', 'archived']:
            raise ValueError('status must be active or archived')
        return v


class AgentPrompt(BaseDBModel):
    """agent_prompts table"""
    agent_key: str
    version: str
    status: StatusState = StatusState.ACTIVE
    system_prompt: str
    task_prompt: str
    style_guide: Optional[str] = None
    output_schema_json: Dict[str, Any]
    guardrails: Optional[str] = None
    created_by: uuid.UUID
    document_type_id: Optional[uuid.UUID] = None
    prompt_role_id: Optional[uuid.UUID] = None


class PromptVariable(BaseDBModel):
    """prompt_variables table"""
    agent_prompt_id: uuid.UUID
    name: str
    source: PromptVariableSource
    required: bool = False
    default_value: Optional[Dict[str, Any]] = None


class RecurrenceRule(BaseDBModel):
    """recurrence_rules table"""
    frequency: ObligationFrequency
    periods_per_year: int
    scheduler_logic: str
    default_period_endpoints: str
    version: int = 1
    status: StatusState = StatusState.ACTIVE


class PlanType(BaseDBModel):
    """plan_types table"""
    key: str = Field(..., unique=True)
    display_name: str
    description: Optional[str] = None
    monthly_price: float
    document_limit: int
    user_limit: int
    storage_limit_gb: float
    features: Dict[str, Any] = Field(default_factory=dict)
    order_index: int = 0
    status_id: uuid.UUID


class OrganizationPlan(BaseDBModel):
    """organization_plans table"""
    org_id: uuid.UUID
    plan_type_id: uuid.UUID
    effective_date: date = Field(default_factory=date.today)
    end_date: Optional[date] = None
    custom_document_limit: Optional[int] = None
    custom_user_limit: Optional[int] = None
    custom_monthly_price: Optional[float] = None
    notes: Optional[str] = None
    status_id: uuid.UUID


class BillingStatusType(BaseDBModel):
    """billing_status_types table"""
    key: str = Field(..., unique=True)
    display_name: str
    description: Optional[str] = None
    is_active: bool = True
    order_index: int = 0


class ContactRole(BaseDBModel):
    """contact_roles table"""
    key: str = Field(..., unique=True)
    display_name: str
    description: Optional[str] = None
    order_index: int = 0


class OrganizationContact(BaseDBModel):
    """organization_contacts table"""
    org_id: uuid.UUID
    contact_role_id: uuid.UUID
    name: str
    email: str
    phone: Optional[str] = None
    title: Optional[str] = None
    is_primary: bool = False
    status_id: uuid.UUID


class OrganizationBilling(BaseDBModel):
    """organization_billing table"""
    org_id: uuid.UUID
    billing_status_id: uuid.UUID
    next_billing_date: Optional[date] = None
    last_invoice_date: Optional[date] = None
    payment_method: Optional[str] = None
    billing_contact_id: Optional[uuid.UUID] = None
    invoice_email: Optional[str] = None
    billing_notes: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class OrganizationUsage(BaseDBModel):
    """organization_usage table"""
    org_id: uuid.UUID
    usage_month: date
    documents_processed: int = 0
    storage_used_gb: float = 0.0
    api_calls: int = 0
    processing_minutes: float = 0.0
    monthly_spend: float = 0.0


class ReportDefinition(BaseDBModel):
    """report_definitions table"""
    org_id: Optional[uuid.UUID] = None
    owner_scope: OwnerScope = OwnerScope.TEMPLATE
    parent_id: Optional[uuid.UUID] = None
    report_key: str
    version: str
    status: StatusState = StatusState.ACTIVE
    template_json: Dict[str, Any]
    binding_rules: Dict[str, Any] = Field(default_factory=dict)
    export_capabilities: List[str] = Field(default_factory=lambda: ["PDF", "HTML", "DOCX", "ICS"])
    notes: Optional[str] = None
    created_by: uuid.UUID
    org_id_eff: Optional[uuid.UUID] = None


class ReportMapping(BaseDBModel):
    """report_mappings table"""
    report_definition_id: uuid.UUID
    mapping_type: str = "obligation_key"
    key_value: str
    filter_logic_json: Optional[Dict[str, Any]] = None


class AuditCategory(BaseDBModel):
    """audit_categories table"""
    key: str = Field(..., unique=True)
    display_name: str
    description: Optional[str] = None
    severity_level: str = "info"
    retention_days: int = 365


class AuditLog(BaseModel):
    """audit_log table"""
    id: int
    org_id: Optional[uuid.UUID] = None
    actor_user_id: Optional[uuid.UUID] = None
    scope: str
    record_id: Optional[uuid.UUID] = None
    action: str
    diff: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    category_id: Optional[uuid.UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    class Config:
        from_attributes = True


class SystemSetting(BaseDBModel):
    """system_settings table"""
    key: str = Field(..., unique=True)
    value: Dict[str, Any]
    category: str
    description: Optional[str] = None
    data_type: str = "string"
    is_sensitive: bool = False
    updated_by: uuid.UUID
    updated_at: datetime = Field(default_factory=datetime.now)


class ApiKey(BaseDBModel):
    """api_keys table"""
    key_name: str
    api_key: str = Field(..., unique=True)
    key_prefix: str
    permissions: Dict[str, Any] = Field(default_factory=dict)
    rate_limit: int = 1000
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_by: uuid.UUID


class SystemAlert(BaseDBModel):
    """system_alerts table"""
    alert_type: str
    threshold_value: float
    threshold_operator: str = "greater_than"
    is_enabled: bool = True
    notification_methods: List[str] = Field(default_factory=lambda: ["email"])
    recipients: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    last_triggered_at: Optional[datetime] = None
    created_by: uuid.UUID


class SystemMetric(BaseDBModel):
    """system_metrics table"""
    metric_name: str
    metric_value: float
    metric_unit: Optional[str] = None
    recorded_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConflictPolicy(BaseDBModel):
    """conflict_policies table"""
    precedence_order: List[str]
    resolution_action: str
    version: int = 1
    status: StatusState = StatusState.ACTIVE
    notes: Optional[str] = None


class IntegrationConfig(BaseDBModel):
    """integration_configs table"""
    service_name: str = Field(..., unique=True)
    config_data: Dict[str, Any]
    is_enabled: bool = True
    connection_status: str = "untested"
    last_tested_at: Optional[datetime] = None
    test_result: Optional[Dict[str, Any]] = None
    created_by: uuid.UUID
    updated_by: uuid.UUID
    updated_at: datetime = Field(default_factory=datetime.now)


# Request/Response Models for API

class OrganizationCreate(BaseModel):
    name: str
    industry_type_id: Optional[uuid.UUID] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    industry_type_id: Optional[uuid.UUID] = None
    status_id: Optional[uuid.UUID] = None


class DocumentCreate(BaseModel):
    document_type_id: Optional[uuid.UUID] = None
    filename: str
    storage_path: str
    mime_type: str
    hash: Optional[bytes] = None


class DocumentUpdate(BaseModel):
    document_type_id: Optional[uuid.UUID] = None
    ocr_status: Optional[OcrStatus] = None
    parsed_index: Optional[Dict[str, Any]] = None


class ObligationCreate(BaseModel):
    document_id: uuid.UUID
    obligation_key: str
    document: str
    section: str
    obligation: str
    frequency: ObligationFrequency
    due_rule: Optional[str] = None
    next_due_date: Optional[date] = None
    responsible_party: ResponsibleParty
    risk: RiskLevel
    source_citation: Optional[Dict[str, Any]] = None
    dependencies: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ObligationUpdate(BaseModel):
    obligation_key: Optional[str] = None
    document: Optional[str] = None
    section: Optional[str] = None
    obligation: Optional[str] = None
    frequency: Optional[ObligationFrequency] = None
    due_rule: Optional[str] = None
    next_due_date: Optional[date] = None
    responsible_party: Optional[ResponsibleParty] = None
    risk: Optional[RiskLevel] = None
    source_citation: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = None
    notes: Optional[str] = None
    status: Optional[ObligationStatus] = None
    computed_due_dates: Optional[Dict[str, Any]] = None


class OrgMemberCreate(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    role: OrgRole = OrgRole.VIEWER