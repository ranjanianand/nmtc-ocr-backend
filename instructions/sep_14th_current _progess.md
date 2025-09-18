      file: UploadFile = File(...),
      document_type_id: str = Form(...),
      description: Optional[str] = Form(None),
      parent_document_id: Optional[str] = Form(None),  # NEW: Link to allocation
      transaction_amount: Optional[float] = Form(None), # NEW: Amount validation
      qalicb_organization_name: Optional[str] = Form(None), # NEW: Simple QALICB name
      org_id: str = Form(...),
      user_id: Optional[str] = Form(None),
  ):

  Frontend Changes (Minimal)

  // Enhanced upload form - still simple!
  interface SimpleUploadForm {
    documentType: string;           // Required dropdown
    description?: string;           // Optional text

    // Conditional fields (only show for QLICI loans):
    relatedAllocation?: string;     // Dropdown of CDE's allocations
    qalicbName?: string;           // Simple text field
    loanAmount?: number;           // Number input
  }

  Business Logic (Simple Validation)

  Smart Form Behavior

  // When user selects "QLICI Loan Agreement":
  1. Show "Related Allocation" dropdown (CDE's allocations only)
  2. Show "QALICB Name" text field
  3. Show "Loan Amount" number field
  4. Validate: loan amount ≤ (allocation amount - already deployed)

  // When user selects "Allocation Agreement":
  1. Show "Allocation Amount" number field
  2. Hide QALICB/loan fields
  3. Validate: reasonable allocation amount range

  Phase 2: Add NMTC Consultants Later

  When Ready for Consultants

  -- Simple consultant model: add client_org_id
  ALTER TABLE documents ADD COLUMN client_org_id UUID; -- Which CDE client

  -- Consultant sees all their clients' documents:
  WHERE uploader_org_id = consultant_org OR client_org_id IN (consultant_clients)

  Bottom Line: Start CDE-Simple

  ✅ CDE organizations are the primary users✅ Single-org model is much simpler✅ 1:many relationship (allocation → loans) is straightforward✅ Can add consultant    
   multi-tenancy later✅ Validates business rules simply

  Should I implement this CDE-first simple approach with just the 3 additional fields?

> CDE Dashboard (Clean & Simple)

    Metro Community Development Corp Dashboard:

    📋 OUR ALLOCATIONS
    ├── 2024 Treasury Allocation - $50M (Active)
    ├── 2023 Treasury Allocation - $25M (Fully Deployed)

    💰 ACTIVE QLICI LOANS (for 2024 Allocation)
    ├── Detroit Manufacturing - $15M (Processing)
    ├── Urban Healthcare - $20M (Completed)
    ├── Community Center - $10M (Pending)
    └── Remaining: $5M available for deployment

    📊 PORTFOLIO SUMMARY
    ├── Total Allocated: $50M
    ├── Total Deployed: $45M
    ├── Compliance Status: ✅ On Track
    └── Next Review: March 2025 - you are correct,ACTIVE QLICI LOANS parent is  Allocation agreement - beforestarting all , please list out the gaps and shall        
  decide how to work on it - because simple showing only results and reports not a fulfilment

● You're absolutely right! A simple dashboard showing results isn't fulfillment. Let me analyze the critical gaps between a basic display and what CDEs actually      
  need for NMTC compliance and operations.

  Critical Gaps Analysis: Display vs. Real CDE Needs

  Gap 1: Transaction Lifecycle Management

  ❌ Current: Static document upload and display
  ✅ CDE Needs: Full transaction workflow management

  Example: QLICI Loan Process
  ├── 1. Application Review (Business Plan analysis)
  ├── 2. Underwriting (Financial analysis + Risk assessment)
  ├── 3. Credit Committee Approval (Decision tracking)
  ├── 4. Legal Documentation (Loan agreement generation)
  ├── 5. Closing Process (Fund disbursement)
  ├── 6. Post-Closing Monitoring (Compliance tracking)
  └── 7. Exit Planning (7-year strategy)

  Gap 2: Compliance Monitoring & Alerting

  ❌ Current: Document storage with status
  ✅ CDE Needs: Active compliance management

  Required Features:
  ├── Automatic deadline tracking (5-year compliance period)
  ├── Required documentation checklist per transaction
  ├── Risk flag alerts (QALICB non-compliance)
  ├── Portfolio-level compliance scoring
  ├── IRS examination preparation
  └── Annual reporting automation

  Gap 3: Financial Controls & Validation

  ❌ Current: Optional amount field
  ✅ CDE Needs: Strict financial controls

  Required Validations:
  ├── Allocation capacity tracking (deployed vs remaining)
  ├── QLICI loan amount limits (substantial compliance)
  ├── Geographic targeting validation (census tract verification)
  ├── Use of proceeds compliance (qualified purposes)
  ├── Cross-transaction consistency checks
  └── Regulatory reserve requirements

  Gap 4: Multi-Document Transaction Bundles

  ❌ Current: Individual document processing
  ✅ CDE Needs: Transaction-complete documentation

  Example: Single QLICI Loan Requires:
  ├── QALICB Business Plan ← Document type
  ├── Financial Statements (3 years) ← Document type
  ├── QLICI Loan Agreement ← Document type
  ├── Security Documents ← Document type
  ├── QALICB Certification ← Document type
  ├── Legal Opinion ← Document type
  ├── Environmental Reports ← Document type
  └── Insurance Certificates ← Document type

  Status: Transaction only "Complete" when ALL documents present

  Gap 5: QALICB Lifecycle Management

  ❌ Current: QALICB name as text field
  ✅ CDE Needs: QALICB entity management

  Required QALICB Data:
  ├── Legal entity information (EIN, incorporation)
  ├── Qualification status tracking (active/inactive)
  ├── Location verification (census tract compliance)
  ├── Business activity validation (qualified purposes)
  ├── Financial performance monitoring
  ├── Employment impact tracking
  └── Community benefit measurement

  Gap 6: Collaborative Workflow Management

  ❌ Current: Single-user document upload
  ✅ CDE Needs: Multi-stakeholder workflows

  Typical CDE Transaction Team:
  ├── Loan Officer (initial review)
  ├── Underwriter (financial analysis)
  ├── Legal Counsel (documentation review)
  ├── Compliance Officer (regulatory approval)
  ├── Credit Committee (final approval)
  ├── Portfolio Manager (ongoing monitoring)
  └── External: QALICB, Legal Counsel, Accountants

  Required: Role-based access, approval workflows, task assignments

  Gap 7: Regulatory Reporting & Analytics

  ❌ Current: Basic document metadata
  ✅ CDE Needs: Comprehensive analytics

  Required Reports:
  ├── CDE Annual Reports (regulatory filing)
  ├── Portfolio Performance Analytics (deployment rates)
  ├── Geographic Impact Analysis (community benefit)
  ├── QALICB Performance Monitoring (job creation)
  ├── Risk Assessment Reports (portfolio health)
  ├── Compliance Exception Reports (issues tracking)
  └── IRS Examination Packages (audit preparation)

  Gap 8: Integration with External Systems

  ❌ Current: Standalone document processor
  ✅ CDE Needs: Integrated operations platform

  Required Integrations:
  ├── Core Banking Systems (loan servicing)
  ├── Accounting Systems (financial reporting)
  ├── CRM Systems (QALICB relationship management)
  ├── Compliance Systems (regulatory tracking)
  ├── Document Management (enterprise storage)
  ├── Communication Systems (stakeholder notifications)
  └── Reporting Tools (regulatory filings)

  Real CDE Daily Operations

  What CDEs Actually Do Daily:

  Morning:
  ├── Review pipeline status (applications, underwriting, closing)
  ├── Check compliance alerts (deadlines, missing documents)
  ├── Monitor portfolio performance (deployment rates, issues)
  └── Plan day's activities (priorities, meetings)

  Throughout Day:
  ├── Process new QALICB applications
  ├── Review underwriting packages
  ├── Collaborate on transaction documentation
  ├── Respond to regulatory inquiries
  ├── Monitor existing loan performance
  └── Update transaction status and notes

  End of Day:
  ├── Update transaction pipeline
  ├── Prepare reports for management
  ├── Plan next day priorities
  └── Communicate with stakeholders

  Architecture Gap: Document Processor vs. CDE Operations Platform

  Current System Architecture:

  Document Upload → AI Processing → Results Display
      ↓
  Single-purpose tool for document analysis

  Required CDE Platform Architecture:

  Transaction Management System
  ├── Document Processing Engine (current system)
  ├── Workflow Management Engine
  ├── Compliance Monitoring Engine
  ├── Financial Controls Engine
  ├── Reporting & Analytics Engine
  ├── Integration API Layer
  └── User Experience Layer

      ↓
  Full-featured CDE operations platform

  Decision Points

  Option 1: Enhance Current System (Incremental)

  ✅ Faster to implement
  ✅ Builds on existing foundation
  ❌ May not meet full CDE operational needs
  ❌ Piecemeal approach could create technical debt

  Option 2: Build CDE Operations Platform (Comprehensive)

  ✅ Meets real CDE business needs
  ✅ Scalable architecture
  ❌ Significantly more complex
  ❌ Longer development timeline

  Option 3: Hybrid Approach (Recommended)

  Phase 1: Enhanced Document System
  ├── Add transaction linking (parent-child)
  ├── Add basic financial controls
  ├── Add compliance tracking
  └── Add multi-document transaction bundles

  Phase 2: Workflow Layer
  ├── Add approval workflows
  ├── Add role-based access
  ├── Add task management
  └── Add collaboration features

  Phase 3: Full Platform
  ├── Add analytics & reporting
  ├── Add external integrations
  ├── Add advanced compliance features
  └── Add portfolio management

  Immediate Priority Questions

  1. Scope Decision: Document processor enhancement OR full CDE platform?
  2. User Research: What are the TOP 3 CDE pain points we should solve first?
  3. Technical Strategy: Build on current foundation OR start CDE-specific architecture?
  4. Timeline: Quick wins (3 months) OR comprehensive solution (12+ months)?

  Which gaps should we prioritize first to deliver real CDE value?

> Document processor enhancement is top priority, because we are working on this and dont want to confuse wth other flows

● Perfect! Let's stay focused on Document Processor Enhancement and build the CDE-specific features on our solid foundation.

● Document Processor Enhancement: CDE-Focused Priorities

  Let's enhance our existing document processing system with the top 3 CDE-specific features that deliver immediate value:

  Priority 1: Transaction Linking (Parent-Child Documents)

  Enhancement: Link QLICI loans to their parent Allocation Agreement
  Business Value: CDEs can track deployment against capacity
  Implementation: Add parent_document_id + smart UI linking

  Priority 2: Financial Controls & Validation

  Enhancement: Validate loan amounts against allocation capacity
  Business Value: Prevent over-deployment and compliance violations
  Implementation: Real-time amount validation in upload flow

  Priority 3: Multi-Document Transaction Bundles

  Enhancement: Track document completeness per transaction
  Business Value: Ensure all required docs are present before closing
  Implementation: Document checklists and completion tracking

  Implementation Plan: Document Processor Enhancement

  Database Schema Enhancement (Simple)

  -- Extend our existing documents table with CDE features
  ALTER TABLE documents
  ADD COLUMN parent_document_id UUID REFERENCES documents(id),
  ADD COLUMN transaction_amount DECIMAL(15,2),
  ADD COLUMN qalicb_organization_name VARCHAR(255),
  ADD COLUMN document_status ENUM('draft', 'complete', 'approved', 'archived') DEFAULT 'draft',
  ADD COLUMN completion_percentage INTEGER DEFAULT 0;

  -- Add simple transaction bundle tracking
  CREATE TABLE transaction_bundles (
      id UUID PRIMARY KEY,
      name VARCHAR(255) NOT NULL,
      parent_document_id UUID REFERENCES documents(id), -- Links to Allocation
      org_id UUID NOT NULL,
      total_amount DECIMAL(15,2),
      deployed_amount DECIMAL(15,2) DEFAULT 0,
      status ENUM('planning', 'active', 'complete') DEFAULT 'planning',
      created_at TIMESTAMP DEFAULT NOW()
  );

  Enhanced Upload Flow

  Current: Document Type → Description → Upload → Process
  New:     Document Type → [Conditional Smart Form] → Upload → Process

  Smart Form Logic:
  ├── If "Allocation Agreement": Show amount field, create bundle
  ├── If "QLICI Loan": Show allocation dropdown, QALICB name, validate amount
  ├── If "Supporting Doc": Show transaction dropdown, link to bundle
  └── All: Calculate completion percentage and update bundle status

  Enhanced Results Dashboard

  Current: Document list with processing status
  New:     Transaction-grouped view with deployment tracking

  CDE Dashboard:
  ├── Active Transactions (with completion %)
  ├── Allocation Capacity (deployed vs remaining)
  ├── Document Processing Status (by transaction)
  └── Compliance Alerts (missing documents)

  Phase 1 Implementation Scope

  What We'll Build:

  ✅ Transaction linking - QLICI loans link to allocations
  ✅ Amount validation - Prevent over-deployment✅ Document bundling - Group docs by transaction
  ✅ Completion tracking - Show transaction progress
  ✅ CDE dashboard - Transaction-focused view

  What We Won't Build (Yet):

  ❌ Advanced workflows (approval chains)
  ❌ External integrations (banking systems)❌ Advanced analytics (complex reporting)
  ❌ Multi-user collaboration (role management)
  ❌ Audit trails (detailed logging)

  Immediate Next Steps

  1. Enhance database schema with transaction linking
  2. Update upload form with conditional smart fields
  3. Modify processing pipeline to handle parent-child relationships
  4. Build transaction dashboard showing grouped documents
  5. Add financial validation for amount limits

  Should I start implementing the database schema enhancements for CDE transaction linking?

> my approach is to creating or showing allocation agreements years - process allocation agreement using core engine - if in let menu we can show the years - and on  
   the right side we show the dashboard on over all on allocation - agreement, and their Qlicis list, utilization  etc and what ever required,  or empty list - then  
   allow to create qalicbs first with minimal information - then on selecting we can allow to upload by this we can avoid on detecting logics - i know upt to this    
  level - As a NMTC expertise how to approach it - becase allocation year plays imp.role

● Brilliant approach! You're thinking like a true NMTC expert. Allocation years are absolutely fundamental to NMTC operations. Let me design this
  allocation-year-centric approach:

  NMTC Allocation Year Strategy

  Why Allocation Years Are Critical:

  NMTC Compliance Reality:
  ├── Each allocation has a 5-year compliance period
  ├── Each allocation has a 7-year recapture period
  ├── Allocations from different years have different rules
  ├── CDEs track performance by allocation year
  └── IRS examinations are organized by allocation year

  Proposed UI/UX Flow: Allocation-Year-Centric

  Main Dashboard Layout:

  ┌─────────────────────────────────────────────────────────┐
  │ Metro Community Development Corp                        │
  ├─────────────────┬───────────────────────────────────────┤
  │ ALLOCATION      │ 2024 ALLOCATION DASHBOARD             │
  │ YEARS          │                                       │
  │                │ 📊 ALLOCATION OVERVIEW                │
  │ ▶ 2024 ($50M)  │ ├── Total Allocated: $50,000,000     │
  │   2023 ($25M)  │ ├── Deployed: $35,000,000 (70%)      │
  │   2022 ($30M)  │ ├── Available: $15,000,000            │
  │   2021 ($20M)  │ └── Status: Active (Year 1 of 5)     │
  │                │                                       │
  │ + New Year     │ 💰 QLICI DEPLOYMENT STATUS           │
  │                │ ├── Detroit Manufacturing ($15M) ✅   │
  │                │ ├── Urban Healthcare ($20M) ⏳        │
  │                │ ├── Community Center (Planning) 📝    │
  │                │ └── + Create New QLICI                │
  │                │                                       │
  │                │ 📋 DOCUMENT STATUS BY TRANSACTION     │
  │                │ Detroit Manufacturing QLICI:          │
  │                │ ├── Business Plan ✅                  │
  │                │ ├── Loan Agreement ✅                │
  │                │ ├── Financial Statements ⏳           │
  │                │ └── Legal Opinion ❌ Missing          │
  └─────────────────┴───────────────────────────────────────┘

  Workflow: Allocation-Year-First Approach

  Step 1: Allocation Agreement Processing

  User Flow:
  1. Upload Allocation Agreement for specific year
  2. Core engine processes and extracts:
     ├── Allocation amount ($50M)
     ├── Compliance period (2024-2029)
     ├── Geographic targeting requirements
     └── CDE certification details

  3. System creates "Allocation Year Record":
     ├── Year: 2024
     ├── Amount: $50,000,000
     ├── Status: Active
     ├── Deployed: $0 (initially)
     └── Documents: [allocation_agreement.pdf]

  Step 2: QALICB Pre-Registration (Smart!)

  Before ANY document upload, CDE creates QALICB entities:

  QALICB Creation Form:
  ├── Organization Name: "Detroit Manufacturing Company"
  ├── Business Address: "123 Main St, Detroit, MI 48201"
  ├── Business Type: "Manufacturing"
  ├── Expected Loan Amount: $15,000,000
  ├── Census Tract: Auto-verified for NMTC eligibility
  └── Contact Information: Basic details

  Benefits:
  ✅ No AI detection needed - we know it's for Detroit Manufacturing
  ✅ Amount validation - can't exceed remaining allocation
  ✅ Geographic validation - census tract compliance
  ✅ Business validation - qualified business activity

  Step 3: Document Upload (Context-Aware)

  When uploading documents:

  Context is PRE-SELECTED:
  ├── Allocation Year: 2024 (from left menu)
  ├── QALICB: Detroit Manufacturing (dropdown)
  ├── Document Type: Business Plan (required docs checklist)
  └── Expected: This is for $15M QLICI loan

  Upload Form becomes:
  ├── Document Type: [Auto-suggested based on missing docs]
  ├── Description: Auto-populated "Detroit Manufacturing Business Plan"
  ├── File: [Upload]
  └── Amount Cross-Check: Validates against expected $15M

  Database Schema: Allocation-Year-Centric

  Core Tables Structure:

  -- 1. Allocation Years (Master Records)
  CREATE TABLE allocation_years (
      id UUID PRIMARY KEY,
      org_id UUID NOT NULL,
      year INTEGER NOT NULL,
      total_amount DECIMAL(15,2) NOT NULL,
      deployed_amount DECIMAL(15,2) DEFAULT 0,
      compliance_start_date DATE,
      compliance_end_date DATE,
      status ENUM('active', 'completed', 'expired') DEFAULT 'active',
      allocation_agreement_document_id UUID REFERENCES documents(id)
  );

  -- 2. QALICB Entities (Pre-registered)
  CREATE TABLE qalicb_entities (
      id UUID PRIMARY KEY,
      allocation_year_id UUID REFERENCES allocation_years(id),
      organization_name VARCHAR(255) NOT NULL,
      business_address TEXT,
      business_type VARCHAR(100),
      expected_loan_amount DECIMAL(15,2),
      actual_loan_amount DECIMAL(15,2),
      census_tract VARCHAR(20),
      status ENUM('planning', 'active', 'completed') DEFAULT 'planning',
      created_at TIMESTAMP DEFAULT NOW()
  );

  -- 3. Enhanced Documents Table
  ALTER TABLE documents
  ADD COLUMN allocation_year_id UUID REFERENCES allocation_years(id),
  ADD COLUMN qalicb_entity_id UUID REFERENCES qalicb_entities(id),
  ADD COLUMN document_category ENUM('allocation', 'qlici_loan', 'supporting', 'compliance'),
  ADD COLUMN expected_amount DECIMAL(15,2),
  ADD COLUMN validation_status ENUM('pending', 'validated', 'rejected') DEFAULT 'pending';

  Smart Document Processing Logic

  Context-Aware Processing:

  # When document is uploaded:
  def process_document_with_context(document, allocation_year, qalicb_entity):

      # Skip AI detection entirely - we have context!
      processing_context = {
          'allocation_year': allocation_year.year,
          'allocation_amount': allocation_year.total_amount,
          'qalicb_name': qalicb_entity.organization_name,
          'expected_amount': qalicb_entity.expected_loan_amount,
          'business_type': qalicb_entity.business_type,
          'geographic_target': qalicb_entity.census_tract
      }

      # Direct to core processing with rich context
      result = await corrected_workflow_service.execute_complete_workflow(
          document_id=document.id,
          processing_context=processing_context  # Rich business context!
      )

      # Validate extracted data against expected context
      validate_against_context(result, processing_context)

      return result

  Business Logic Validation:

  def validate_against_context(extraction_result, context):
      # Amount validation
      extracted_amount = extraction_result.get('loan_amount')
      expected_amount = context['expected_amount']

      if abs(extracted_amount - expected_amount) > 100000:  # $100k tolerance
          flag_for_review("Amount mismatch", extracted_amount, expected_amount)

      # Business name validation
      extracted_borrower = extraction_result.get('borrower_name')
      expected_borrower = context['qalicb_name']

      if not fuzzy_match(extracted_borrower, expected_borrower):
          flag_for_review("Borrower name mismatch", extracted_borrower, expected_borrower)

      # Geographic validation
      extracted_location = extraction_result.get('project_location')
      expected_tract = context['geographic_target']

      if not validate_census_tract(extracted_location, expected_tract):
          flag_for_review("Geographic targeting issue", extracted_location, expected_tract)

  Implementation Benefits:

  ✅ Business Logic Benefits:

  - No AI guessing - rich context eliminates detection
  - Smart validation - cross-check extracted data vs expectations
  - Allocation tracking - real-time deployment monitoring
  - Compliance automation - year-based rule application

  ✅ User Experience Benefits:

  - Allocation-year navigation - matches CDE mental model
  - Pre-populated forms - minimal data entry required
  - Progress tracking - see transaction completion status
  - Error prevention - validate before processing

  ✅ Technical Benefits:

  - Builds on existing foundation - enhances current system
  - Rich processing context - better AI results
  - Simple data model - year → QALICBs → documents
  - Scalable approach - easy to add allocation years

  Implementation Order:

  Phase 1: Core Structure
  1. Create allocation_years and qalicb_entities tables
  2. Build allocation year selection UI (left menu)
  3. Build QALICB pre-registration form

  Phase 2: Enhanced Upload4. Context-aware document upload form
  5. Rich processing context integration
  6. Business logic validation

  Phase 3: Dashboard
  7. Allocation year dashboard (right side)
  8. Transaction progress tracking
  9. Document completion checklists

  Should I start implementing the allocation-year-centric database schema?

> i believe first we can focus allocation_agreement on open-ended - and shall proceed one by one - based on allocation agreement year - what woule be best to ask -   
  because for example in main dashboard or any place first shall we have option to upload allocation agreement instead of general upload documents, or create the     
  years first and shall ask for allocation agreement - what will be best best approach - first let us focus on this

● Excellent question! Let's think about this from a CDE user's real workflow perspective:

  CDE Reality Check: What Happens First?

  Scenario A: New CDE (First Time)

  CDE receives Treasury allocation letter →
  "We just got our 2024 $50M allocation from Treasury!"

  Question: Do they know it's "2024" or do they think "allocation agreement"?
  Answer: They think "We got our allocation agreement document to process"

  Scenario B: Existing CDE (Multiple Years)

  CDE has 2021, 2022, 2023 already → Now getting 2024
  They think: "We need to add our new 2024 allocation"

  Question: Do they create year first or upload document first?
  Answer: They want to upload the new allocation document

  User Mental Model Analysis

  Document-First Thinking (Natural):

  ✅ "I have this allocation agreement document to upload"
  ✅ "Let me upload this important document first"
  ✅ "The system should figure out it's 2024 from the document"
  ✅ "Then I can manage this year's activities"

  Year-First Thinking (System-Centric):

  ❌ "I need to create a 2024 year record first"
  ❌ "Let me set up the structure, then add documents"
  ❌ "I need to tell the system this is 2024"
  ❌ "Then I can upload documents into it"

  Recommended Approach: Smart Document-First

  Main Dashboard: Document-First Entry Point

  ┌─────────────────────────────────────────────────┐
  │ Metro Community Development Corp Dashboard      │
  │                                                 │
  │ 🎯 QUICK START                                  │
  │                                                 │
  │ [ 📄 Upload Allocation Agreement ]              │
  │   New Treasury allocation? Start here           │
  │                                                 │
  │ [ 📋 Upload Other Document ]                    │
  │   For existing allocations                      │
  │                                                 │
  │ ═══════════════════════════════════════════════ │
  │                                                 │
  │ 📊 YOUR ALLOCATIONS                             │
  │ ├── 2023 Allocation ($25M) - 80% deployed     │
  │ ├── 2022 Allocation ($30M) - 95% deployed     │
  │ └── 2021 Allocation ($20M) - Completed        │
  │                                                 │
  └─────────────────────────────────────────────────┘

  Smart Upload Flow: Auto-Detect Allocation Year

  Step 1: Smart Upload Detection

  // When user clicks "Upload Allocation Agreement"
  UploadForm.show({
    mode: 'allocation_agreement',
    title: 'Upload New Treasury Allocation Agreement',
    description: 'We\'ll automatically detect the year and amount'
  });

  // Form fields:
  ├── File Upload: [Required]
  ├── Description: [Optional] "Brief description of this allocation"
  └── Year Override: [Optional] "Leave blank for auto-detection"

  Step 2: Core Engine Auto-Detection

  # Enhanced core engine for allocation agreements
  async def process_allocation_agreement(document):

      # AI extraction with allocation-specific prompts
      extraction_result = await ai_service.extract_allocation_data(
          document_text=ocr_text,
          extract_fields=[
              'allocation_year',           # 2024
              'allocation_amount',         # $50,000,000
              'cde_name',                 # Metro Community Development
              'compliance_period_start',   # January 1, 2024
              'compliance_period_end',     # December 31, 2028
              'treasury_letter_date',      # When issued
              'geographic_targeting'       # Service area requirements
          ]
      )

      # Auto-create allocation year record
      allocation_year = await create_allocation_year({
          org_id: user.org_id,
          year: extraction_result.allocation_year,
          total_amount: extraction_result.allocation_amount,
          compliance_start: extraction_result.compliance_period_start,
          compliance_end: extraction_result.compliance_period_end,
          allocation_document_id: document.id,
          status: 'active'
      })

      return {
          success: True,
          allocation_year_created: allocation_year.id,
          extracted_data: extraction_result,
          next_step: 'allocation_year_dashboard'
      }

  Step 3: Post-Processing Success

  // After successful allocation processing
  ShowSuccessMessage({
    title: "2024 Allocation Successfully Processed!",
    message: "We detected your $50M Treasury allocation for 2024",
    actions: [
      "📊 View 2024 Dashboard",      // Go to year-specific dashboard
      "➕ Add QLICI Loan",          // Start adding QALICBs
      "📋 Upload More Documents"     // Add supporting docs
    ]
  });

  // Automatically redirect to: /dashboard/2024-allocation

  Resulting User Experience:

  New CDE (First Allocation):

  1. User: "Upload Allocation Agreement" → Upload file
  2. System: Auto-detects 2024, $50M → Creates allocation year
  3. User: Sees "2024 Allocation Dashboard" → Can start QLICI planning
  4. Natural progression: Document → Year → Activities

  Existing CDE (Additional Allocation):

  1. User: "Upload Allocation Agreement" → Upload 2024 file
  2. System: Detects 2024 (new year) → Creates alongside existing years
  3. User: Now has 2021, 2022, 2023, 2024 → Can switch between years
  4. Natural progression: New document → New year → Manage both

  Implementation Strategy:

  Phase 1: Smart Allocation Upload

  -- Simple schema to start
  CREATE TABLE allocation_years (
      id UUID PRIMARY KEY,
      org_id UUID NOT NULL,
      year INTEGER NOT NULL,
      total_amount DECIMAL(15,2),
      deployed_amount DECIMAL(15,2) DEFAULT 0,
      status ENUM('active', 'completed') DEFAULT 'active',
      allocation_document_id UUID REFERENCES documents(id),
      created_at TIMESTAMP DEFAULT NOW(),
      UNIQUE(org_id, year)  -- One allocation per org per year
  );

  Enhanced Document Processing:

  # Update core engine to detect allocation agreements
  if document_type_id == 'allocation_agreement':
      # Special allocation processing
      result = await process_allocation_agreement(document)

      # Auto-create allocation year if detected
      if result.allocation_year and result.allocation_amount:
          allocation_year = await create_or_update_allocation_year(result)

  else:
      # Regular document processing
      result = await standard_document_processing(document)

  UI Flow:

  Main Dashboard → "Upload Allocation Agreement" →
  Smart Upload Form → Auto-Processing →
  Allocation Year Created → Year-Specific Dashboard

  Benefits of Document-First Approach:

  ✅ Natural user workflow - matches CDE thinking✅ Auto-magic experience - system figures out the details✅ Flexible - works for first-time and existing CDEs✅      
  Progressive enhancement - upload → detect → organize✅ Error-resistant - if detection fails, user can override

  Should I implement this smart allocation agreement upload with auto-year-creation?

> As of now the apart from this, there will not changes on core-engine right - for example typical flow - user upload - Azure-coreengine work progcess- result page   
  - will there be any changes on this due to above changes?
  ⎿  5-hour limit reached ∙ resets 2:30pm
     /upgrade to increase your usage limit.

> please proceed

● You're absolutely right! The core engine workflow remains unchanged. Let me implement the allocation-year enhancement while keeping the existing processing
  pipeline intact.

● Perfect! The core engine stays exactly the same:

  Current Flow (Unchanged):
  User Upload → Azure OCR → Core Engine → Results Page

  What Changes:
  - Post-processing step that analyzes results for allocation data
  - Database enhancement to store allocation years
  - UI enhancement to show allocation-centric dashboard

  Let me implement this step by step:

  Step 1: Database Schema for Allocation Years

● Write(database_allocation_years_2025_09_14.sql)
  ⎿  Wrote 1 lines to database_allocation_years_2025_09_14.sql
     -- NMTC Allocation Years Management
     -- Database Schema Addition - 2025-09-14
     -- Execute after the previous document type selection schema
     -- 1. Create allocation years table
     CREATE TABLE IF NOT EXISTS allocation_years (
         id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
         org_id UUID NOT NULL,
         year INTEGER NOT NULL,
         total_amount DECIMAL(15,2) NOT NULL,

● Step 2: Add Allocation Year Detection Service (Post-Processing)

● Write(app\services\allocation_year_service.py)
  ⎿  Wrote 1 lines to app\services\allocation_year_service.py
     """
     NMTC Allocation Year Detection and Management Service
     Handles auto-detection and creation of allocation years from processed documents.
     """
     import re
     import logging
     from datetime import datetime, date
     from typing import Optional, Dict, Any
     from decimal import Decimal
╭──────────────────────────────────────────────────────────────────╮
│ ✻ Welcome to Claude Code!                                        │
│                                                                  │
│   /help for help, /status for your current setup                 │
│                                                                  │
│   cwd: E:\Raine\YOZY\Clients\AV\cdesolution\AI_OCR\nmtc-backend  │
╰──────────────────────────────────────────────────────────────────╯
════════════════════════════════════════════════════════════ Conversation compacted · ctrl+r for history ═══════════════════════════════════════════════════════════  
  ⎿  Read app\services\allocation_year_service.py (285 lines)
  ⎿  Read database_allocation_years_2025_09_14.sql (62 lines)
  ⎿  Read test_document_type_selection.py (135 lines)
  ⎿  Referenced file ..\nmtc-frontend\src\hooks\useDocumentProcessingV3.tsx
  ⎿  Read ..\nmtc-frontend\src\components\document-processing\EnterpriseDocumentProcessor.tsx (430 lines)
  ⎿  Todo list read (5 items)

● I'll continue integrating the allocation year service into the document processing pipeline. Let me modify the document upload API to call the allocation year      
  service after core processing completes.

● Read(app\api\documents.py)
  ⎿  Read 998 lines (ctrl+r to expand)

● Now I need to integrate the allocation year service into the document upload pipeline. I'll modify the upload endpoint to call the allocation year service after    
   core processing completes:

● Update(app\api\documents.py)
  ⎿  Updated app\api\documents.py with 40 additions and 4 removals
       216                    core_processing_success = False
       217                    processing_session_id = None
       218
       219 -              # Step 4: Update document with results
       220 -              logger.info("Step 4: Storing processing results...")
       219 +              # Step 4: Post-Processing - Allocation Year Detection
       220 +              logger.info("Step 4: Running post-processing analysis...")
       221
       222 +              allocation_analysis = None
       223 +              if core_processing_success and processing_session_id:
       224 +                  try:
       225 +                      from app.services.allocation_year_service import allocation_year_service
       226 +
       227 +                      # Prepare processing results for allocation analysis
       228 +                      processing_results_for_analysis = {
       229 +                          'extracted_text': extracted_text,
       230 +                          'parsed_index': {
       231 +                              'extracted_text': extracted_text,
       232 +                              'page_count': page_count,
       233 +                              'character_count': len(extracted_text),
       234 +                              'detected_type': detected_type,
       235 +                              'confidence': confidence
       236 +                          }
       237 +                      }
       238 +
       239 +                      # Run allocation year analysis
       240 +                      allocation_analysis = await allocation_year_service.analyze_for_allocation_data(
       241 +                          document_id=document_id,
       242 +                          processing_results=processing_results_for_analysis
       243 +                      )
       244 +
       245 +                      if allocation_analysis:
       246 +                          logger.info(f"Allocation analysis completed: {allocation_analysis}")
       247 +                      else:
       248 +                          logger.info("No allocation data detected - document is not allocation-related")
       249 +
       250 +                  except Exception as allocation_error:
       251 +                      logger.error(f"Allocation analysis error (non-critical): {allocation_error}")
       252 +                      # Don't fail the whole workflow if allocation analysis fails
       253 +                      allocation_analysis = None
       254 +
       255 +              # Step 5: Store processing results
       256 +              logger.info("Step 5: Storing processing results...")
       257 +
       258                processing_results = {
       259                    'ocr_status': 'done',
       260                    'parsed_index': {
     ...
       228                        'detected_type': detected_type,
       229                        'confidence': confidence,
       230                        'confidence_level': confidence_level,
       231 -                      'detection_metadata': detection_result.metadata,
       231                        'processing_completed_at': datetime.utcnow().isoformat(),
       232                        'core_processing': {
       233                            'success': core_processing_success,
       234                            'session_id': processing_session_id,
       235                            'triggered_at': datetime.utcnow().isoformat()
       236 -                      }
       236 +                      },
       237 +                      'allocation_analysis': allocation_analysis  # Add allocation analysis results
       238                    }
       239                }
       240

● Now I need to update the return response to include allocation analysis information:

● Update(app\api\documents.py)
  ⎿  Updated app\api\documents.py with 8 additions and 2 removals
       283                logger.info("Processing completed successfully!")
       284
       285                # Return comprehensive response with results
       286 +              success_message = f"Document processed successfully! Detected: {detected_type}. Core processing: {'SUCCESS' if 
           + core_processing_success else 'FAILED'}"
       287 +
       288 +              if allocation_analysis and allocation_analysis.get('allocation_detected'):
       289 +                  success_message += f" | Allocation Year: {allocation_analysis.get('allocation_data', {}).get('year', 'Unknown')}"
       290 +
       291                return {
       292                    "document_id": document_id,
       293                    "status": "completed",
       294 -                  "message": f"Document processed successfully! Detected: {detected_type}. Core processing: {'SUCCESS' if core_processing_success         
           - else 'FAILED'}",
       294 +                  "message": success_message,
       295                    "file_path": file_path,
       296                    "processing_results": {
       297                        "detected_type": detected_type,
     ...
       300                            "success": core_processing_success,
       301                            "session_id": processing_session_id,
       302                            "workflow_triggered": True
       303 -                      }
       303 +                      },
       304 +                      "allocation_analysis": allocation_analysis  # Include allocation analysis results
       305                    }
       306                }
       307

● Now I need to create an API endpoint to fetch allocation years for an organization. Let me add this to the documents API:

● Update(app\api\documents.py)
  ⎿  Updated app\api\documents.py with 18 additions
       445            logger.error(f"Error validating document: {e}")
       446            raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
       447
       448 +  @router.get("/allocation-years/{org_id}")
       449 +  async def get_organization_allocation_years(org_id: str):
       450 +      """Get all allocation years for an organization"""
       451 +      try:
       452 +          from app.services.allocation_year_service import allocation_year_service
       453 +