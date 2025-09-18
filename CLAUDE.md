# CLAUDE.md - NMTC MVP Project Guide

This file provides comprehensive guidance to Claude Code when working with this NMTC MVP project.

## Project Overview

**NMTC MVP - Allocation Agreement Processor**
*Simple, focused PDF processing for NMTC Allocation Agreements with compliance checking*

### Project Status: MVP Development Phase
- **Current Branch**: `mvp-only` (NEVER work on main branch)
- **Development Timeline**: 6-week MVP sprint
- **Focus**: Allocation Agreement PDFs ONLY
- **Goal**: Process AA PDFs in <5 minutes with >90% accuracy

## MVP Architecture

### Core Philosophy
- **Simplicity over sophistication**
- **Single focus**: Allocation Agreement documents only
- **3-stage pipeline**: Upload → Extract & Validate → Export Results
- **No feature creep**: If it's not core AA processing, don't build it

### Technical Stack
```
Backend: FastAPI 0.115.6 (Python)
Database: Supabase (PostgreSQL)
OCR: Azure Document Intelligence
PDF Generation: ReportLab
Frontend: React + TypeScript (separate repo)
```

### Project Structure
```
nmtc-backend/
├── app/
│   ├── main.py                  # FastAPI app (56 lines)
│   ├── config.py               # Configuration
│   ├── api/
│   │   └── documents.py        # MVP endpoint (257 lines)
│   ├── services/
│   │   ├── azure_service.py    # Azure OCR integration
│   │   ├── supabase_service.py # Database operations
│   │   └── database_service.py # Database models
│   ├── models/
│   │   ├── database.py         # Data models
│   │   └── document.py         # Document schemas
│   └── utils/
│       ├── auth.py             # Authentication
│       ├── exceptions.py       # Error handling
│       └── logging_config.py   # Logging setup
├── pdfs/
│   └── AA_form.pdf            # Sample Allocation Agreement for testing
├── requirements.txt           # MVP dependencies (15 packages)
├── .env                      # Environment variables
└── CLAUDE.md                 # This file
```

## Current MVP Implementation

### Single Core Endpoint
**POST** `/api/process-allocation-agreement`
- **Purpose**: Process Allocation Agreement PDFs only
- **Input**: PDF file upload
- **Output**: Extracted data + compliance flags + confidence scores

### 3-Stage Processing Pipeline
```
Stage 1: Upload & Validate
├── PDF file validation
├── File size check (<50MB)
└── Generate document ID

Stage 2: Extract & Analyze
├── Azure OCR text extraction
├── Basic AA data extraction (regex patterns)
├── Compliance checking (QEI deadline, amount validation)
└── Confidence scoring

Stage 3: Return Results
├── Extracted data (allocation_amount, effective_date, allocatee_name)
├── Compliance flags (QEI warnings, missing data alerts)
├── Confidence scores (field-level + overall)
└── Next steps recommendations
```

### Core Features Implemented
1. **Azure OCR Integration**: Text extraction from AA PDFs
2. **Basic Data Extraction**: Amount, effective date, allocatee name
3. **Compliance Checking**:
   - QEI deadline calculation (5-year warning system)
   - Allocation amount validation
   - Document completeness checks
4. **Confidence Scoring**: Field-level and overall confidence metrics
5. **Error Handling**: Clean error responses with logging

## Development Rules & Constraints

### 🔴 CRITICAL RULES (Never Break)
1. **Work ONLY in `mvp-only` branch** - Never switch to main
2. **Allocation Agreement PDFs ONLY** - No other document types
3. **No feature creep** - If it's not essential AA processing, don't build it
4. **Simple solutions first** - Choose the easiest approach that works

### 🟡 IMPORTANT GUIDELINES
1. **6-week timeline** - Prioritize working features over perfect code
2. **User testing weekly** - Test with real CDE users every Friday
3. **Commit frequently** - Daily commits with clear messages
4. **Document decisions** - Update this file when making architectural changes

### 🟢 DEVELOPMENT PREFERENCES
1. **Readable code** over complex optimizations
2. **Working features** over comprehensive testing
3. **MVP completeness** over individual feature perfection

## Environment Configuration

### Required Environment Variables (.env)
```bash
# Supabase Database
SUPABASE_URL=https://[project].supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...

# Azure Document Intelligence
AZURE_DOC_INTELLIGENCE_ENDPOINT=https://[resource].cognitiveservices.azure.com/
AZURE_DOC_INTELLIGENCE_KEY=...

# Application Settings
MAX_FILE_SIZE_MB=50
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001
ENV=development
```

### Development Commands
```bash
# Start MVP development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Install dependencies
pip install -r requirements.txt

# Test MVP endpoint
curl -X POST "http://localhost:8001/api/process-allocation-agreement" \
     -F "file=@pdfs/AA_form.pdf"

# Health check
curl http://localhost:8001/api/health
```

## Current Limitations & TODOs

### Known Limitations
1. **Simple regex extraction** - Needs improvement for complex AA formats
2. **No manual override UI** - Data corrections not implemented
3. **No PDF report generation** - Compliance reports not implemented
4. **No geographic compliance** - Service area validation missing
5. **No data persistence** - Results not saved to database

### Week 1 Priorities
1. **Test with real AA PDF** (`pdfs/AA_form.pdf`)
2. **Improve data extraction** patterns for better accuracy
3. **Add basic data persistence** to Supabase
4. **Implement manual override** response format

### Week 2-3 Priorities
1. **Build manual override interface** (API endpoints)
2. **Add geographic compliance** validation
3. **Implement PDF report generation**
4. **Enhanced error handling** and validation

### Week 4-6 Priorities
1. **User interface integration** with frontend
2. **Performance optimization** for larger documents
3. **Comprehensive testing** with beta CDEs
4. **Deployment preparation**

## Data Models & Schemas

### Allocation Agreement Data Fields
```python
{
    "allocation_amount": "45000000",        # Extracted dollar amount
    "effective_date": "April 22, 2024",    # Allocation effective date
    "allocatee_name": "Metro Community Development Corporation",
    "control_number": "23NMA0425",         # CDE control number
    "service_area": [...],                  # Geographic service areas
    "product_requirements": {...}          # Product mix requirements
}
```

### Compliance Flags Schema
```python
{
    "type": "QEI_DEADLINE_WARNING",
    "severity": "high|medium|low",
    "message": "Human-readable warning",
    "recommendation": "Actionable next step"
}
```

### Confidence Scores Schema
```python
{
    "field_scores": {
        "allocation_amount": 0.95,
        "effective_date": 0.9,
        "allocatee_name": 0.8
    },
    "overall_confidence": 0.88,
    "confidence_level": "high|medium|low"
}
```

## Testing Strategy

### Sample Data
- **Test Document**: `pdfs/AA_form.pdf` (Metro Community Development Corp, $45M allocation)
- **Expected Results**:
  - Allocation Amount: $45,000,000
  - Effective Date: April 22, 2024
  - Allocatee: Metro Community Development Corporation

### Testing Approach
1. **Unit Testing**: Test individual extraction functions
2. **Integration Testing**: Test full pipeline with sample PDF
3. **User Testing**: Weekly sessions with CDE staff
4. **Performance Testing**: Process documents under 5 minutes

### Success Criteria
- **Accuracy**: >90% correct extraction of core fields
- **Performance**: <5 minutes processing time
- **Usability**: Non-technical users can complete workflow in <10 minutes
- **Reliability**: >95% uptime, proper error handling

## Deployment & Infrastructure

### Current Setup
- **Development**: Local FastAPI server on port 8001
- **Database**: Supabase cloud instance
- **OCR**: Azure Document Intelligence cloud service
- **Version Control**: GitHub (`mvp-only` branch)

### Production Requirements (Future)
- **Hosting**: Railway/Heroku for FastAPI backend
- **Frontend**: Separate deployment for React app
- **Database**: Supabase production tier
- **File Storage**: Supabase Storage for uploaded PDFs
- **Monitoring**: Basic uptime and error monitoring

## Troubleshooting

### Common Issues
1. **Port 8001 in use**: Use different port (`--port 8002`)
2. **Azure OCR errors**: Check API key and endpoint configuration
3. **Supabase connection issues**: Verify URL and service key
4. **Import errors**: Ensure working in `mvp-only` branch

### Debug Commands
```bash
# Check if app imports work
python -c "from app.main import app; print('Import successful')"

# Test Azure OCR connection
python -c "from app.services.azure_service import azure_service; print('Azure configured')"

# Test Supabase connection
python -c "from app.services.supabase_service import supabase_service; print('Supabase configured')"
```

## Communication & Coordination

### Stakeholder Updates
- **Weekly demos**: Friday afternoons with real CDE users
- **Progress tracking**: Update this file with weekly accomplishments
- **Issue escalation**: Document blockers immediately in GitHub issues

### Decision Log
- **2025-01-18**: Pivoted from complex 6-stage pipeline to simple 3-stage MVP
- **2025-01-18**: Removed all non-AA document types for MVP focus
- **2025-01-18**: Simplified documents.py from 1058 lines to 257 lines

## Success Metrics

### MVP Success Criteria (6-week target)
- **Technical**: Process AA PDFs in <5 minutes with >90% accuracy
- **User Experience**: Non-technical users complete workflow in <10 minutes
- **Business Value**: Reduce manual processing time by >70%
- **Adoption**: 3+ CDEs prefer MVP over manual process

### Weekly Milestones
- **Week 1**: Basic pipeline working with real AA PDF
- **Week 2**: Manual override capability implemented
- **Week 3**: PDF compliance reports generated
- **Week 4**: Frontend integration completed
- **Week 5**: Beta testing with 3 CDEs
- **Week 6**: Production-ready deployment

## Contact & Resources

### Key Resources
- **NMTC Sample Document**: `pdfs/AA_form.pdf`
- **GitHub Repository**: https://github.com/ranjanianand/nmtc-ocr-backend
- **Development Branch**: `mvp-only`
- **API Documentation**: FastAPI auto-docs at `/docs`

### Development Support
- **Primary Focus**: Allocation Agreement processing only
- **Time Constraint**: 6-week MVP timeline
- **Quality Standard**: Working > Perfect
- **User Priority**: CDE staff usability over technical sophistication

---

## Quick Reference

### Start Development
1. `git checkout mvp-only`
2. `pip install -r requirements.txt`
3. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8001`
4. Test: `curl http://localhost:8001/api/health`

### Core MVP Endpoint
```bash
curl -X POST "http://localhost:8001/api/process-allocation-agreement" \
     -F "file=@pdfs/AA_form.pdf"
```

### Remember: Simple, Focused, Working MVP in 6 Weeks!

*Last Updated: January 18, 2025*
*Status: MVP Foundation Complete - Ready for Week 1 Development*