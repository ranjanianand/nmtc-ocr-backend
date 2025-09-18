"""
MVP Workflow API Endpoints
Handles allocation-year-centric user workflow with manual input.
"""

from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mvp", tags=["mvp-workflow"])

# =====================================================
# PYDANTIC MODELS FOR REQUEST/RESPONSE
# =====================================================

class CreateQLICILoanRequest(BaseModel):
    allocation_year_id: str
    loan_name: str
    loan_amount: float
    borrower_name: str
    project_description: Optional[str] = None

class UpdateQLICILoanRequest(BaseModel):
    loan_name: Optional[str] = None
    loan_amount: Optional[float] = None
    borrower_name: Optional[str] = None
    project_description: Optional[str] = None

class CreateAllocationYearRequest(BaseModel):
    year: int
    total_amount: float
    description: Optional[str] = None

# =====================================================
# ALLOCATION YEARS ENDPOINTS
# =====================================================

@router.get("/allocation-years/{org_id}")
async def get_allocation_years_for_org(org_id: str):
    """Get all allocation years for organization (left menu)"""
    try:
        from app.services.allocation_year_service import allocation_year_service
        
        allocation_years = await allocation_year_service.get_allocation_years_for_org(org_id)
        
        # Add summary data for each year
        enriched_years = []
        for year in allocation_years:
            year_data = {
                **year,
                'remaining_amount': float(year['total_amount']) - float(year.get('deployed_amount', 0)),
                'utilization_percent': (float(year.get('deployed_amount', 0)) / float(year['total_amount']) * 100) if year['total_amount'] > 0 else 0
            }
            enriched_years.append(year_data)
        
        return {
            "org_id": org_id,
            "allocation_years": enriched_years,
            "total_years": len(enriched_years)
        }
        
    except Exception as e:
        logger.error(f"Error fetching allocation years for org {org_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch allocation years: {str(e)}")

@router.post("/allocation-years/{org_id}")
async def create_allocation_year(org_id: str, request: CreateAllocationYearRequest):
    """Create new allocation year manually (user uploads allocation agreement)"""
    try:
        from app.services.allocation_year_service import allocation_year_service
        
        # Create allocation year with user-provided data
        allocation_data = {
            'year': request.year,
            'total_amount': request.total_amount,
            'organization_name': f'Org {org_id}',  # Could be enhanced with real org data
        }
        
        # Create allocation year record
        allocation_year = await allocation_year_service._create_or_update_allocation_year(
            org_id=org_id,
            document_id=None,  # Will be linked when allocation agreement is uploaded
            allocation_data=allocation_data
        )
        
        if allocation_year:
            logger.info(f"Created allocation year {request.year} for org {org_id}")
            return {
                "success": True,
                "allocation_year": allocation_year,
                "message": f"Allocation year {request.year} created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create allocation year")
            
    except Exception as e:
        logger.error(f"Error creating allocation year: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create allocation year: {str(e)}")

@router.get("/allocation-years/{org_id}/{year}/dashboard")
async def get_allocation_year_dashboard(org_id: str, year: int):
    """Get complete dashboard data for specific allocation year"""
    try:
        from app.services.allocation_year_service import allocation_year_service
        from app.services.qlici_loan_service import qlici_loan_service
        
        # Get allocation year
        allocation_years = await allocation_year_service.get_allocation_years_for_org(org_id)
        allocation_year = next((ay for ay in allocation_years if ay['year'] == year), None)
        
        if not allocation_year:
            return {
                "org_id": org_id,
                "year": year,
                "allocation_year": None,
                "has_allocation_agreement": False,
                "qlici_loans": [],
                "summary": {
                    "total_amount": 0,
                    "deployed_amount": 0,
                    "remaining_amount": 0,
                    "utilization_percent": 0,
                    "qlici_count": 0
                }
            }
        
        # Get QLICI loans for this year
        qlici_loans = await qlici_loan_service.get_qlici_loans_for_allocation_year(allocation_year['id'])
        
        # Get allocation agreement document
        allocation_document = None
        if allocation_year.get('allocation_document_id'):
            from app.services.supabase_service import supabase_service
            doc_result = supabase_service.client.table('documents').select('*').eq('id', allocation_year['allocation_document_id']).execute()
            allocation_document = doc_result.data[0] if doc_result.data else None
        
        # Calculate summary
        total_amount = float(allocation_year['total_amount'])
        deployed_amount = float(allocation_year.get('deployed_amount', 0))
        remaining_amount = total_amount - deployed_amount
        utilization_percent = (deployed_amount / total_amount * 100) if total_amount > 0 else 0
        
        return {
            "org_id": org_id,
            "year": year,
            "allocation_year": allocation_year,
            "allocation_document": allocation_document,
            "has_allocation_agreement": allocation_document is not None,
            "qlici_loans": qlici_loans,
            "summary": {
                "total_amount": total_amount,
                "deployed_amount": deployed_amount,
                "remaining_amount": remaining_amount,
                "utilization_percent": utilization_percent,
                "qlici_count": len(qlici_loans),
                "total_documents": allocation_year.get('documents_count', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")

# =====================================================
# QLICI LOANS ENDPOINTS
# =====================================================

@router.post("/qlici-loans")
async def create_qlici_loan(request: CreateQLICILoanRequest, created_by: Optional[str] = None):
    """Create new QLICI loan entity (user-driven)"""
    try:
        from app.services.qlici_loan_service import qlici_loan_service
        from app.services.supabase_service import supabase_service
        
        # Get org_id from allocation_year
        allocation_result = supabase_service.client.table('allocation_years').select('org_id').eq('id', request.allocation_year_id).execute()
        if not allocation_result.data:
            raise HTTPException(status_code=404, detail="Allocation year not found")
        
        org_id = allocation_result.data[0]['org_id']
        
        # Create QLICI loan
        qlici_loan = await qlici_loan_service.create_qlici_loan(
            allocation_year_id=request.allocation_year_id,
            org_id=org_id,
            loan_name=request.loan_name,
            loan_amount=request.loan_amount,
            borrower_name=request.borrower_name,
            project_description=request.project_description,
            created_by=created_by
        )
        
        if qlici_loan:
            return {
                "success": True,
                "qlici_loan": qlici_loan,
                "message": f"QLICI loan '{request.loan_name}' created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create QLICI loan")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating QLICI loan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create QLICI loan: {str(e)}")

@router.get("/qlici-loans/{qlici_loan_id}")
async def get_qlici_loan_details(qlici_loan_id: str):
    """Get detailed QLICI loan information including documents"""
    try:
        from app.services.qlici_loan_service import qlici_loan_service
        
        qlici_loan = await qlici_loan_service.get_qlici_loan_details(qlici_loan_id)
        
        if not qlici_loan:
            raise HTTPException(status_code=404, detail="QLICI loan not found")
        
        return {
            "qlici_loan": qlici_loan,
            "documents_count": len(qlici_loan.get('documents', [])),
            "documents": qlici_loan.get('documents', [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching QLICI loan details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch QLICI loan details: {str(e)}")

@router.put("/qlici-loans/{qlici_loan_id}")
async def update_qlici_loan(qlici_loan_id: str, request: UpdateQLICILoanRequest):
    """Update QLICI loan details"""
    try:
        from app.services.qlici_loan_service import qlici_loan_service
        
        # Prepare updates (only include non-None values)
        updates = {}
        if request.loan_name is not None:
            updates['loan_name'] = request.loan_name
        if request.loan_amount is not None:
            updates['loan_amount'] = request.loan_amount
        if request.borrower_name is not None:
            updates['borrower_name'] = request.borrower_name
        if request.project_description is not None:
            updates['project_description'] = request.project_description
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        updated_qlici = await qlici_loan_service.update_qlici_loan(qlici_loan_id, updates)
        
        if updated_qlici:
            return {
                "success": True,
                "qlici_loan": updated_qlici,
                "message": "QLICI loan updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update QLICI loan")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating QLICI loan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update QLICI loan: {str(e)}")

@router.delete("/qlici-loans/{qlici_loan_id}")
async def delete_qlici_loan(qlici_loan_id: str):
    """Delete (cancel) QLICI loan"""
    try:
        from app.services.qlici_loan_service import qlici_loan_service
        
        success = await qlici_loan_service.delete_qlici_loan(qlici_loan_id)
        
        if success:
            return {
                "success": True,
                "message": "QLICI loan cancelled successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to cancel QLICI loan")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting QLICI loan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel QLICI loan: {str(e)}")

# =====================================================
# DOCUMENT UPLOAD FOR QLICI LOANS
# =====================================================

@router.post("/qlici-loans/{qlici_loan_id}/upload-document")
async def upload_document_to_qlici_loan(
    qlici_loan_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    description: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    """Upload document and link to specific QLICI loan"""
    try:
        from app.services.qlici_loan_service import qlici_loan_service
        from app.services.supabase_service import supabase_service
        
        # Get QLICI loan details
        qlici_loan = await qlici_loan_service.get_qlici_loan_details(qlici_loan_id)
        if not qlici_loan:
            raise HTTPException(status_code=404, detail="QLICI loan not found")
        
        org_id = qlici_loan['org_id']
        allocation_year_id = qlici_loan['allocation_year_id']
        
        # Use existing document upload from documents.py
        # This maintains the core processing workflow
        from app.api.documents import upload_document as core_upload_document
        
        # Upload document using core workflow
        upload_result = await core_upload_document(
            file=file,
            document_type_id=document_type,  # Pass document type
            description=description,
            org_id=org_id,
            user_id=user_id
        )
        
        if upload_result.get('document_id'):
            document_id = upload_result['document_id']
            
            # Link document to QLICI loan
            link_success = await qlici_loan_service.link_document_to_qlici_loan(
                document_id=document_id,
                qlici_loan_id=qlici_loan_id
            )
            
            if link_success:
                return {
                    "success": True,
                    "document_id": document_id,
                    "qlici_loan_id": qlici_loan_id,
                    "message": f"Document uploaded and linked to QLICI loan '{qlici_loan['loan_name']}'",
                    "processing_results": upload_result.get('processing_results', {})
                }
            else:
                logger.error(f"Document uploaded but failed to link to QLICI loan {qlici_loan_id}")
                return {
                    "success": True,
                    "document_id": document_id,
                    "qlici_loan_id": qlici_loan_id,
                    "message": "Document uploaded successfully but linking failed",
                    "warning": "Document exists but not linked to QLICI loan"
                }
        else:
            raise HTTPException(status_code=500, detail="Document upload failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document to QLICI loan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")

# =====================================================
# TEST ENDPOINTS
# =====================================================

@router.get("/test/workflow")
async def test_mvp_workflow():
    """Test MVP workflow components"""
    try:
        from app.services.supabase_service import supabase_service
        
        # Test database connectivity
        allocation_years_test = supabase_service.client.table('allocation_years').select('id').limit(1).execute()
        qlici_loans_test = supabase_service.client.table('qlici_loans').select('id').limit(1).execute()
        
        return {
            "status": "success",
            "database_connectivity": {
                "allocation_years": "accessible" if allocation_years_test else "error",
                "qlici_loans": "accessible" if qlici_loans_test else "error"
            },
            "workflow_components": {
                "allocation_year_service": "loaded",
                "qlici_loan_service": "loaded",
                "api_endpoints": "active"
            },
            "message": "MVP workflow ready for testing"
        }
        
    except Exception as e:
        logger.error(f"MVP workflow test failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "message": "MVP workflow has issues"
        }