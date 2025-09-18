# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Structure

This is a full-stack NMTC (New Markets Tax Credit) document processing application with:

- **Backend**: FastAPI application in `/nmtc-backend`
- **Frontend**: React/TypeScript with Vite in `/nmtc-frontend`
- **Database**: Supabase (PostgreSQL) with complex document workflow tables
- **Processing**: Azure Document Intelligence + AI agents for NMTC compliance analysis

## Development Commands

### Backend (nmtc-backend/)
```bash
# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Install dependencies
pip install -r requirements.txt

# Run specific test categories
python tests/auth/test_authentication.py
python tests/workflow/test_allocation_workflow.py
python tests/database/test_schema_validation.py

# Database operations
python apply_allocation_schema.py  # Apply schema changes
python setup_predefined_years.py  # Setup allocation years 2020-2024
```

### Frontend (nmtc-frontend/)
```bash
# Start development server (auto-finds available port, typically 8082)
npm run dev

# Build for production
npm run build

# Development build
npm run build:dev

# Linting
npm run lint
```

## Core Architecture

### API Versions & Routing
The backend supports multiple API versions for different processing approaches:

- `/api/documents` - Legacy v1 upload and processing
- `/api/v2/documents` - Enterprise v2 with enhanced workflow tracking
- `/api/v3/documents` - Enterprise v3 with full database integration
- `/api/mvp` - MVP workflow endpoints
- `/api/allocation-years` - **PRIMARY**: Allocation-year-centric workflow

**Current Focus**: Allocation Years API provides the main user workflow for year-based document management.

### Processing Pipeline Architecture

#### 3-Agent Processing System
1. **Document Analyzer Agent**: Structure analysis and data extraction
2. **Risk Assessor Agent**: NMTC compliance validation
3. **Report Generator Agent**: Professional document generation

#### 6-Stage Allocation Processing Pipeline
```
1. File Upload → 2. Azure OCR → 3. Document Analysis →
4. Core Engine Processing → 5. Allocation Data Integration → 6. Dashboard Generation
```

#### Database Workflow Tables
- **documents**: Uploaded files with processing status
- **document_types**: Master configuration for document processing rules
- **sections**: Document section definitions for extraction
- **queries**: Specific extraction queries per section
- **allocation_years**: Year-based organization (2020-2024 predefined)
- **processing_sessions**: Track complete document workflow state
- **agent_pipeline_states**: Individual agent execution tracking

### Frontend Architecture

#### Key Hooks
- `useAllocationYears`: Primary hook for allocation year management with pipeline monitoring
- `useAuth`: Supabase authentication with organization membership

#### Core Workflow
```
Left Sidebar (Years 2020-2024) → Year Selection → Dashboard View → Document Upload →
Real-time Progress Pipeline → Results Dashboard
```

#### Component Structure
- `AllocationYears`: Main container with year selection
- `AllocationDashboard`: Year-specific document and QALICB management
- `ProcessingPipeline`: Real-time progress visualization (6 stages, 3-second polling)
- `AllocationAgreementUpload`: Context-aware upload with auto-defaulted document types

## Configuration Management

### Environment Variables (.env)
```bash
# Supabase
SUPABASE_URL=https://[project].supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Azure Document Intelligence
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://[resource].cognitiveservices.azure.com/
AZURE_DOC_INTELLIGENCE_KEY=...

# Server Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001
FRONTEND_PORT=8080

# Processing
MAX_FILE_SIZE_MB=50
PROCESSING_TIMEOUT_SECONDS=300
```

### API Routing
Frontend uses Vite proxy configuration to route `/api` requests to backend:
```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:8001',
    changeOrigin: true,
  },
}
```

## Database Schema Key Points

### Allocation Year Structure
- **allocation_years**: Central table linking organizations to specific years (2020-2024)
- **documents**: Links to allocation_years via `allocation_year_id`
- **Computed Fields**: `available_amount`, `utilization_percent` auto-calculated

### Document Workflow Dependencies
```
document_types.id → sections.document_type_id → queries.section_id
                 ↓
documents.document_type_id → processing_sessions → agent_pipeline_states
```

### Critical Foreign Key Relationships
- `documents.org_id` → Organizations (external Supabase auth)
- `documents.allocation_year_id` → allocation_years.id
- `sections.document_type_id` → document_types.id
- All processing tables link back to documents.id

## Development Patterns

### React Hook Stability
Always use `useCallback` for functions used in `useEffect` dependencies:
```typescript
const fetchData = useCallback(async (id: string) => {
  // logic
}, [id]);

useEffect(() => {
  fetchData(id);
}, [fetchData, id]); // Safe - fetchData is stable
```

### Backend Error Handling Pattern
All upload endpoints must include rollback capability:
```python
async def upload_with_processing():
    try:
        # 1. Store file
        # 2. Create database record
        # 3. Trigger processing pipeline
        return success_response
    except Exception as e:
        # Rollback: clean up created records
        await cleanup_on_failure()
        raise HTTPException(500, detail=f"Upload failed: {e}")
```

### API Endpoint Validation
Use the endpoint validator utility to prevent duplicate endpoints:
```python
from app.utils.endpoint_validator import startup_validation_middleware
startup_validation_middleware(app)  # Validates on startup
```

## Testing Structure

Tests are organized by category in `/tests/`:
- `auth/`: Authentication and user management
- `azure/`: Azure Document Intelligence integration
- `database/`: Schema validation and queries
- `workflow/`: End-to-end processing workflows
- `supabase/`: Database integration tests

## Known Configuration Requirements

- Backend typically runs on port 8001 (configurable)
- Frontend auto-selects available port (usually 8082 in development)
- Supabase requires specific table structure with `auth.users` integration
- Azure Document Intelligence requires valid endpoint + key for OCR processing
- Organization ID `ce117b87-d75c-4c8a-b3f5-922ddec539b0` used for testing

## Critical Workflow Notes

### Allocation Agreement Processing
1. Must auto-default document type to "Allocation Agreement"
2. Processing pipeline has 6 stages with real-time updates every 3 seconds
3. Dashboard auto-generates after successful processing completion
4. Year context (2020-2024) drives the entire workflow

### Document Type Hierarchy
- Level 0: Allocation Agreement (parent document)
- Level 1+: QLICI Loans, CBAs, Financial Reports (child documents)

### Real-time Features
- Pipeline progress updates via polling (every 3 seconds)
- Background processing with agent state tracking
- Cross-device state synchronization through Supabase

This codebase follows enterprise patterns with comprehensive error handling, real-time processing, and a sophisticated document workflow optimized for NMTC compliance requirements.

## Specialized Claude Code Agents

This project has specialized agents in `.claude/agents/` for different aspects of development:

### Core Processing & Architecture
- **Core Engine Processing Agent**: End-to-end document processing orchestrator with 15+ years FastAPI expertise. Handles complete workflow from upload to report generation, background processing, and Azure integration.
- **Enhanced Database Architect Agent**: RELIABLE database specialist that NEVER makes assumptions - always verifies current schema before changes. Uses mandatory pre-work checklist and incremental testing.

### Domain & Business Logic
- **NMTC Domain Expert Agent**: 20+ years NMTC compliance specialist with authority on Allocation Agreements, QLICI loans, Community Benefits Agreements, and regulatory frameworks. Defines risk assessment and business intelligence requirements.

### Frontend Development
- **React Enterprise UI Agent**: Professional React/TypeScript frontend specialist building enterprise-grade components, real-time interfaces, and document processing workflows with shadcn/ui.
- **UX Design System Agent**: Enterprise UX specialist creating professional design systems, user workflows, and visual hierarchies for complex document processing interfaces.

### Backend & Infrastructure
- **FastAPI Backend Agent**: Enterprise FastAPI specialist with 15+ years Python backend experience. Handles API design, authentication, middleware, security, and integration patterns.
- **Database Architect Agent**: Enterprise database design specialist for NMTC platform with PostgreSQL and Supabase expertise, handling document_sessions schemas and real-time subscriptions.

### Project Coordination
- **Project Management Agent**: 15+ years experience tracking daily progress, maintaining continuity, and coordinating development workflows. Creates dated instruction files and ensures seamless day-to-day project evolution.

### Agent Collaboration Pattern
These agents work together on complex tasks:
- Database Architect verifies schema before Core Engine implements processing
- NMTC Expert defines business rules that FastAPI Backend implements
- React UI Agent builds components that integrate with Core Engine's real-time updates
- Project Manager coordinates dependencies and maintains daily progress logs