#!/usr/bin/env python3
"""
Example Usage: NMTC Document Processing with Type Detection

This script demonstrates how the integrated Stage 0A workflow with document type detection works.
It shows both the quick detection (OCR + type detection) and standalone type detection tasks.
"""

import asyncio
from typing import Dict, Any
from app.services.detection_service import detection_service
from app.utils.nmtc_patterns import NMTCDocumentType

# Sample NMTC documents for testing
SAMPLE_DOCUMENTS = {
    "allocation_agreement": {
        "filename": "nmtc_allocation_agreement.pdf",
        "content": """
        NEW MARKETS TAX CREDIT ALLOCATION AGREEMENT
        
        This New Markets Tax Credit Allocation Agreement ("Agreement") is entered into 
        between the Community Development Financial Institutions Fund ("CDFI Fund") and 
        ABC Community Development Entity, LLC ("CDE").
        
        WHEREAS, the CDE has been certified as a Community Development Entity under Section 45D;
        WHEREAS, the CDFI Fund has authority to allocate New Markets Tax Credits;
        
        NOW THEREFORE, the parties agree as follows:
        
        1. ALLOCATION AMOUNT
        The QEI Amount allocated to CDE under this Agreement is $25,000,000 (Twenty-Five Million Dollars).
        
        2. COMPLIANCE PERIOD  
        The 7-year compliance period begins on the initial investment date as defined in Treasury regulations.
        
        3. RECAPTURE PROVISIONS
        Any recapture event as defined in Section 45D shall result in the recapture of credits claimed.
        
        4. REPORTING REQUIREMENTS
        CDE shall submit annual compliance reports to the CDFI Fund demonstrating compliance
        with all qualified low-income community investment requirements.
        """
    },
    
    "qlici_loan": {
        "filename": "qlici_loan_agreement.pdf", 
        "content": """
        QUALIFIED LOW-INCOME COMMUNITY INVESTMENT LOAN AGREEMENT
        
        This Qualified Low-Income Community Investment Loan Agreement ("Agreement") is made
        between XYZ Community Development Entity, LLC ("Lender") and Main Street Business
        Development Corp ("Borrower").
        
        RECITALS:
        A. Borrower is a Qualified Active Low-Income Community Business (QALICB);
        B. This loan constitutes a Qualified Low-Income Community Investment (QLICI);
        
        LOAN TERMS:
        Principal Amount: $750,000.00
        Interest Rate: 4.75% per annum
        Maturity Date: December 31, 2031
        
        QALICB COMPLIANCE:
        Borrower shall maintain its status as a QALICB throughout the term including:
        - Satisfying the substantially all test (at least 85% of assets used in qualifying business)
        - Meeting the 70% income test for low-income community location
        - Satisfying the 40% property test for qualifying business property
        
        The borrower shall use loan proceeds exclusively for qualifying business activities
        within the designated low-income community census tract 12345.67.
        """
    },
    
    "qalicb_certification": {
        "filename": "qalicb_certificate.pdf",
        "content": """
        QUALIFIED ACTIVE LOW-INCOME COMMUNITY BUSINESS CERTIFICATION
        
        Certificate Number: QALICB-2024-00123
        
        This is to certify that DOWNTOWN MANUFACTURING LLC, located at 123 Main Street,
        Cityville, State 12345, Census Tract 1001.02, is hereby certified as a 
        Qualified Active Low-Income Community Business (QALICB) under Section 45D
        of the Internal Revenue Code.
        
        CERTIFICATION DETAILS:
        Effective Date: January 1, 2024
        Certification Period: 7 years from effective date
        
        QUALIFYING CRITERIA:
        ✓ Located in qualified low-income community (Census Tract 1001.02)
        ✓ Median family income test: Area MFI is 65% of state median (below 80% threshold)
        ✓ Poverty rate test: Census tract poverty rate is 22% (above 20% threshold)
        ✓ Substantially all test: 90% of tangible property located in qualifying census tract
        ✓ Active business test: Engaged in qualifying business activities (manufacturing)
        
        This certification shall remain valid provided the business continues to satisfy
        all QALICB requirements including the 40% property test and 70% income test.
        
        Annual recertification required by December 31 of each year.
        """
    },
    
    "community_benefits_agreement": {
        "filename": "community_benefits_agreement.pdf",
        "content": """
        COMMUNITY BENEFITS AGREEMENT
        
        This Community Benefits Agreement ("CBA") is entered into between Riverside
        Development Project LLC ("Developer") and the Downtown Community Coalition
        ("Community Organization").
        
        COMMUNITY COMMITMENTS:
        
        1. LOCAL HIRING
        Developer commits to hire at least 30% of construction workers from the local
        community zip codes 12345, 12346, and 12347.
        
        2. WORKFORCE DEVELOPMENT  
        Developer shall provide job training programs for at least 50 local residents
        in construction trades and provide apprenticeship opportunities.
        
        3. LOCAL PROCUREMENT
        Developer agrees to procure at least 25% of goods and services from local
        businesses, with preference for minority business enterprises (MBE) and
        disadvantaged business enterprises (DBE).
        
        4. AFFORDABLE HOUSING
        Developer shall ensure that 20% of residential units remain affordable to
        households earning 80% or less of area median income for 15 years.
        
        5. COMMUNITY IMPACT MONITORING
        Developer shall provide annual reports on job creation, local hiring metrics,
        and community investment outcomes to the Community Organization.
        
        This agreement ensures meaningful community benefits from the NMTC-funded
        development project and promotes equitable economic development.
        """
    }
}

async def demonstrate_document_processing():
    """Demonstrate the document processing and type detection workflow"""
    
    print("🚀 NMTC Document Processing & Type Detection Demo")
    print("=" * 60)
    
    for doc_type, doc_info in SAMPLE_DOCUMENTS.items():
        print(f"\n📄 Processing: {doc_info['filename']}")
        print("-" * 40)
        
        # Step 1: Simulate what happens during quick detection task
        print("🔍 Step 1: Document Type Detection")
        
        try:
            # This is what happens inside the Celery task after OCR
            detection_result = detection_service.detect_document_type(
                text_content=doc_info['content'],
                filename=doc_info['filename']
            )
            
            # Display results
            print(f"✅ Detected Type: {detection_result.document_type.value.replace('_', ' ').title()}")
            print(f"📊 Confidence: {detection_result.confidence:.1%}")
            print(f"🎯 Primary Indicators: {len(detection_result.primary_indicators)}")
            print(f"🔍 Secondary Indicators: {len(detection_result.secondary_indicators)}")
            
            if detection_result.primary_indicators:
                print("🎯 Top Primary Indicators:")
                for indicator in detection_result.primary_indicators[:3]:  # Show top 3
                    print(f"   - {indicator.pattern_type}: {indicator.confidence:.1%} confidence")
                    print(f"     Match: '{indicator.match_text[:50]}...'")
            
            # Show extracted metadata highlights
            if detection_result.metadata and 'extracted_fields' in detection_result.metadata:
                fields = detection_result.metadata['extracted_fields']
                if fields:
                    print("📋 Key Fields Extracted:")
                    for field_type, values in fields.items():
                        if values:
                            print(f"   - {field_type.title()}: {values[0] if values else 'N/A'}")
            
            print(f"💭 Reasoning: {detection_result.reasoning[:100]}...")
            
        except Exception as e:
            print(f"❌ Detection failed: {e}")
        
        print()

def demonstrate_integration_workflow():
    """Show how the integrated workflow works"""
    
    print("\n🔗 Integrated Workflow Overview")
    print("=" * 40)
    
    print("📋 Stage 0A - Quick Document Detection + Type Detection:")
    print("1. 📤 Document uploaded to Supabase storage")
    print("2. 🔄 Celery task: process_document_quick_detection() triggered")
    print("3. 📥 Download document from storage")
    print("4. 🧠 Azure Document Intelligence: OCR processing")
    print("5. 🏷️  NMTC Type Detection: Pattern matching & classification")
    print("6. 💾 Store results in database (parsed_index)")
    print("7. 📊 Return processing summary with type & confidence")
    
    print("\n🔧 Available Celery Tasks:")
    print("- process_document_quick_detection(document_id, user_id)")
    print("  └─ Complete OCR + Type Detection workflow")
    print("- process_document_type_detection(document_id, user_id)") 
    print("  └─ Standalone type detection for already processed docs")
    print("- process_document_layout_analysis(document_id, user_id)")
    print("  └─ Advanced layout analysis (tables, forms, etc.)")
    print("- get_document_processing_status(document_id)")
    print("  └─ Get current processing status and detection results")
    
    print("\n📊 Database Storage Structure (parsed_index):")
    print("""
    {
      "ocr_results": {
        "full_text": "extracted text...",
        "page_count": 5,
        "confidence_scores": [...],
        "overall_confidence": 0.95
      },
      "detection_results": {
        "document_type_detected": "allocation_agreement",
        "confidence": 0.87,
        "primary_indicators": [...],
        "secondary_indicators": [...],
        "metadata": { "extracted_fields": {...} },
        "reasoning": "Document classified as..."
      },
      "processing_history": [
        {
          "stage": "quick_detection",
          "status": "completed",
          "processed_at": "2024-01-15T10:30:00Z",
          "task_id": "celery-task-123"
        }
      ]
    }
    """)

def show_supported_document_types():
    """Display all supported NMTC document types"""
    
    print("\n📚 Supported NMTC Document Types")
    print("=" * 40)
    
    supported_types = detection_service.get_supported_document_types()
    
    for i, doc_type in enumerate(supported_types, 1):
        print(f"{i:2}. {doc_type['name']}")
        print(f"    Type ID: {doc_type['type']}")
        print(f"    Description: {doc_type['description']}")
        print()

async def main():
    """Main demo function"""
    
    # Show supported document types
    show_supported_document_types()
    
    # Demonstrate document processing
    await demonstrate_document_processing()
    
    # Show integration workflow
    demonstrate_integration_workflow()
    
    print("\n✅ Demo completed! The Stage 0A system with NMTC document type detection")
    print("   is ready for production use.")
    print("\n🚀 To run the system:")
    print("1. Start Redis: redis-server")
    print("2. Start Celery: celery -A app.tasks.document_tasks worker --loglevel=info")
    print("3. Start FastAPI: uvicorn app.main:app --reload")
    print("4. Upload documents via API and watch the magic happen! ✨")

if __name__ == "__main__":
    asyncio.run(main())