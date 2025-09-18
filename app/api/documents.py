from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.supabase_service import supabase_service
from app.services.azure_service import azure_service
from app.config import settings
import uuid
import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["mvp"])

@router.post("/process-allocation-agreement")
async def process_allocation_agreement(file: UploadFile = File(...)):
    """
    MVP Endpoint: Process Allocation Agreement PDF Only

    3-Stage Pipeline:
    1. Upload & Validate (PDF only, AA documents only)
    2. Extract & Analyze (Azure OCR + Basic compliance checks)
    3. Return Results (Extracted data + compliance flags)
    """
    try:
        logger.info(f"MVP: Processing Allocation Agreement: {file.filename}")

        # Stage 1: Upload & Validate
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files supported")

        file_content = await file.read()
        file_size = len(file_content)

        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit")

        # Generate unique document ID
        document_id = str(uuid.uuid4())
        logger.info(f"MVP: Generated document ID: {document_id}")

        # Stage 2: Extract & Analyze
        logger.info("MVP: Starting Azure OCR extraction...")

        # Azure OCR Processing
        ocr_result = await azure_service.analyze_document_quick(file_content, document_id)
        extracted_text = ocr_result.get('full_text', '')

        if not extracted_text:
            raise HTTPException(status_code=400, detail="Failed to extract text from PDF")

        logger.info(f"MVP: Extracted {len(extracted_text)} characters")

        # Basic AA Data Extraction (Simple parsing for MVP)
        allocation_data = extract_allocation_data(extracted_text)

        # Basic Compliance Checks
        compliance_flags = check_compliance(allocation_data)

        # Calculate confidence scores (simple heuristic for MVP)
        confidence_scores = calculate_confidence(allocation_data)

        # Stage 3: Return Results
        logger.info("MVP: Processing completed successfully")

        return {
            "document_id": document_id,
            "status": "completed",
            "filename": file.filename,
            "file_size": file_size,
            "processing_time": "< 5 minutes",
            "extracted_data": allocation_data,
            "confidence_scores": confidence_scores,
            "compliance_flags": compliance_flags,
            "next_steps": [
                "Review extracted data for accuracy",
                "Correct any misidentified fields",
                "Download compliance report"
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MVP: Processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.get("/health")
async def health_check():
    """Simple health check for MVP"""
    return {
        "status": "healthy",
        "message": "NMTC MVP - Allocation Agreement Processor",
        "azure_ocr": "configured" if os.getenv("AZURE_DOC_INTELLIGENCE_KEY") else "not configured",
        "database": "configured" if os.getenv("SUPABASE_URL") else "not configured"
    }

# Helper Functions for MVP

def extract_allocation_data(text: str) -> dict:
    """
    Simple extraction for MVP - Extract key AA fields
    TODO: Replace with more sophisticated extraction
    """
    data = {}

    # Extract allocation amount (simple regex pattern)
    import re

    # Look for allocation amount patterns
    amount_patterns = [
        r'NMTC Allocation Amount[:\s]+\$?([\d,]+)',
        r'Allocation Amount[:\s]+\$?([\d,]+)',
        r'\$?([\d,]+),000,000'  # Common format like $45,000,000
    ]

    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['allocation_amount'] = match.group(1).replace(',', '')
            break

    # Extract effective date
    date_patterns = [
        r'Allocation Effective Date[:\s]+([A-Za-z]+ \d{1,2}, \d{4})',
        r'Effective Date[:\s]+([A-Za-z]+ \d{1,2}, \d{4})'
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['effective_date'] = match.group(1)
            break

    # Extract allocatee name
    allocatee_patterns = [
        r'Allocatee[:\s]+([A-Za-z ]+(?:Corporation|LLC|Inc))',
        r'CDE[:\s]+([A-Za-z ]+(?:Corporation|LLC|Inc))'
    ]

    for pattern in allocatee_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['allocatee_name'] = match.group(1).strip()
            break

    return data

def check_compliance(allocation_data: dict) -> list:
    """
    Basic compliance checks for MVP
    Focus on top 3 compliance issues identified in analysis
    """
    flags = []

    # 1. QEI Deadline Check
    if 'effective_date' in allocation_data:
        try:
            # Calculate 5-year deadline from effective date
            effective_date = datetime.strptime(allocation_data['effective_date'], '%B %d, %Y')
            deadline = effective_date.replace(year=effective_date.year + 5)
            days_remaining = (deadline - datetime.now()).days

            if days_remaining < 365:
                flags.append({
                    "type": "QEI_DEADLINE_WARNING",
                    "severity": "high",
                    "message": f"QEI deadline in {days_remaining} days ({deadline.strftime('%B %d, %Y')})",
                    "recommendation": "Prioritize QEI deployment"
                })
            elif days_remaining < 730:
                flags.append({
                    "type": "QEI_DEADLINE_NOTICE",
                    "severity": "medium",
                    "message": f"QEI deadline in {days_remaining} days ({deadline.strftime('%B %d, %Y')})",
                    "recommendation": "Plan QEI deployment schedule"
                })
        except:
            flags.append({
                "type": "EFFECTIVE_DATE_MISSING",
                "severity": "high",
                "message": "Could not parse effective date for QEI deadline calculation",
                "recommendation": "Manually verify effective date"
            })

    # 2. Allocation Amount Validation
    if 'allocation_amount' in allocation_data:
        try:
            amount = float(allocation_data['allocation_amount'])
            if amount > 100000000:  # $100M
                flags.append({
                    "type": "LARGE_ALLOCATION",
                    "severity": "medium",
                    "message": f"Large allocation amount: ${amount:,.0f}",
                    "recommendation": "Verify enhanced compliance requirements"
                })
        except:
            flags.append({
                "type": "ALLOCATION_AMOUNT_MISSING",
                "severity": "high",
                "message": "Could not parse allocation amount",
                "recommendation": "Manually verify allocation amount"
            })

    # 3. Basic Document Completeness
    required_fields = ['allocation_amount', 'effective_date', 'allocatee_name']
    missing_fields = [field for field in required_fields if field not in allocation_data]

    if missing_fields:
        flags.append({
            "type": "MISSING_REQUIRED_DATA",
            "severity": "medium",
            "message": f"Missing required fields: {', '.join(missing_fields)}",
            "recommendation": "Review document for missing information"
        })

    return flags

def calculate_confidence(allocation_data: dict) -> dict:
    """
    Simple confidence scoring for MVP
    """
    scores = {}

    for field, value in allocation_data.items():
        if field == 'allocation_amount':
            # High confidence if we found a reasonable dollar amount
            try:
                amount = float(value)
                scores[field] = 0.95 if 1000000 <= amount <= 200000000 else 0.7
            except:
                scores[field] = 0.3

        elif field == 'effective_date':
            # High confidence if date format is recognized
            try:
                datetime.strptime(value, '%B %d, %Y')
                scores[field] = 0.9
            except:
                scores[field] = 0.4

        elif field == 'allocatee_name':
            # Medium confidence for name extraction
            scores[field] = 0.8 if len(value) > 10 else 0.5

        else:
            scores[field] = 0.7  # Default confidence

    # Overall confidence is average of field confidences
    overall_confidence = sum(scores.values()) / len(scores) if scores else 0.5

    return {
        "field_scores": scores,
        "overall_confidence": overall_confidence,
        "confidence_level": "high" if overall_confidence > 0.8 else "medium" if overall_confidence > 0.6 else "low"
    }