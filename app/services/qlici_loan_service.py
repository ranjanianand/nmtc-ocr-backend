"""
QLICI Loan Entity Management Service
Handles user-driven creation and management of QLICI loan entities.
No auto-detection - pure manual user input workflow.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
from uuid import UUID

from app.services.supabase_service import supabase_service

logger = logging.getLogger(__name__)

class QLICILoanService:
    """
    Service for managing QLICI loan entities in the user-driven workflow.
    Users manually create QLICI entities before uploading documents.
    """
    
    def __init__(self):
        self.client = supabase_service.client
    
    async def create_qlici_loan(
        self, 
        allocation_year_id: str,
        org_id: str, 
        loan_name: str,
        loan_amount: float,
        borrower_name: str,
        project_description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new QLICI loan entity with user-provided information.
        
        Args:
            allocation_year_id: ID of the allocation year this loan belongs to
            org_id: Organization ID
            loan_name: User-friendly name (e.g., "ABC Manufacturing Project")
            loan_amount: Loan amount in dollars
            borrower_name: Name of borrowing entity
            project_description: Optional project description
            created_by: User ID who created this entity
            
        Returns:
            Dict with created QLICI loan data, None if failed
        """
        try:
            # Validate allocation year exists and has capacity
            allocation_year = await self._validate_allocation_capacity(allocation_year_id, loan_amount)
            if not allocation_year:
                logger.error(f"Allocation year {allocation_year_id} cannot accommodate ${loan_amount:,.2f}")
                return None
            
            # Create QLICI loan entity
            insert_data = {
                'allocation_year_id': allocation_year_id,
                'org_id': org_id,
                'loan_name': loan_name,
                'loan_amount': loan_amount,
                'borrower_name': borrower_name,
                'project_description': project_description or '',
                'status': 'active',
                'created_by': created_by,
                'documents_count': 0
            }
            
            result = self.client.table('qlici_loans').insert(insert_data).execute()
            
            if result.data:
                qlici_loan = result.data[0]
                logger.info(f"Created QLICI loan: {loan_name} - ${loan_amount:,.2f}")
                
                # The trigger will automatically update allocation_years.deployed_amount
                return qlici_loan
            else:
                logger.error("Failed to create QLICI loan - no data returned")
                return None
                
        except Exception as e:
            logger.error(f"Error creating QLICI loan: {str(e)}")
            return None
    
    async def get_qlici_loans_for_allocation_year(self, allocation_year_id: str) -> List[Dict[str, Any]]:
        """Get all QLICI loans for a specific allocation year."""
        try:
            result = self.client.table('qlici_loans').select(
                '*, allocation_years!inner(year, total_amount)'
            ).eq('allocation_year_id', allocation_year_id).eq('status', 'active').order('created_at').execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error fetching QLICI loans for allocation year {allocation_year_id}: {str(e)}")
            return []
    
    async def get_qlici_loans_for_org(self, org_id: str) -> List[Dict[str, Any]]:
        """Get all QLICI loans for an organization across all years."""
        try:
            result = self.client.table('qlici_loans').select(
                '*, allocation_years!inner(year, total_amount)'
            ).eq('org_id', org_id).eq('status', 'active').order('created_at', desc=True).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error fetching QLICI loans for org {org_id}: {str(e)}")
            return []
    
    async def update_qlici_loan(
        self, 
        qlici_loan_id: str, 
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update QLICI loan entity details."""
        try:
            # Add updated timestamp
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.client.table('qlici_loans').update(updates).eq('id', qlici_loan_id).execute()
            
            if result.data:
                logger.info(f"Updated QLICI loan {qlici_loan_id}")
                return result.data[0]
            else:
                logger.error(f"Failed to update QLICI loan {qlici_loan_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating QLICI loan {qlici_loan_id}: {str(e)}")
            return None
    
    async def delete_qlici_loan(self, qlici_loan_id: str) -> bool:
        """
        Soft delete QLICI loan (set status to cancelled).
        This will automatically update the allocation year deployed amount via trigger.
        """
        try:
            result = self.client.table('qlici_loans').update({
                'status': 'cancelled',
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', qlici_loan_id).execute()
            
            if result.data:
                logger.info(f"Cancelled QLICI loan {qlici_loan_id}")
                return True
            else:
                logger.error(f"Failed to cancel QLICI loan {qlici_loan_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling QLICI loan {qlici_loan_id}: {str(e)}")
            return False
    
    async def get_qlici_loan_details(self, qlici_loan_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific QLICI loan including documents."""
        try:
            # Get QLICI loan with allocation year info
            qlici_result = self.client.table('qlici_loans').select(
                '*, allocation_years!inner(year, total_amount, deployed_amount)'
            ).eq('id', qlici_loan_id).execute()
            
            if not qlici_result.data:
                return None
                
            qlici_loan = qlici_result.data[0]
            
            # Get associated documents
            docs_result = self.client.table('documents').select(
                'id, filename, document_type_id, ocr_status, uploaded_at, mime_type'
            ).eq('qlici_loan_id', qlici_loan_id).order('uploaded_at').execute()
            
            qlici_loan['documents'] = docs_result.data if docs_result.data else []
            
            return qlici_loan
            
        except Exception as e:
            logger.error(f"Error fetching QLICI loan details {qlici_loan_id}: {str(e)}")
            return None
    
    async def link_document_to_qlici_loan(self, document_id: str, qlici_loan_id: str) -> bool:
        """Link an uploaded document to a QLICI loan entity."""
        try:
            # Update document with QLICI loan reference
            result = self.client.table('documents').update({
                'qlici_loan_id': qlici_loan_id,
                'document_category': 'qlici_loan',
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', document_id).execute()
            
            if result.data:
                logger.info(f"Linked document {document_id} to QLICI loan {qlici_loan_id}")
                # The trigger will automatically update documents_count
                return True
            else:
                logger.error(f"Failed to link document {document_id} to QLICI loan {qlici_loan_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error linking document to QLICI loan: {str(e)}")
            return False
    
    async def _validate_allocation_capacity(self, allocation_year_id: str, loan_amount: float) -> Optional[Dict[str, Any]]:
        """Validate that allocation year has capacity for the new loan amount."""
        try:
            result = self.client.table('allocation_years').select('*').eq('id', allocation_year_id).execute()
            
            if not result.data:
                logger.error(f"Allocation year {allocation_year_id} not found")
                return None
                
            allocation_year = result.data[0]
            total_amount = float(allocation_year['total_amount'])
            deployed_amount = float(allocation_year['deployed_amount'] or 0)
            remaining_amount = total_amount - deployed_amount
            
            if loan_amount > remaining_amount:
                logger.error(f"Loan amount ${loan_amount:,.2f} exceeds remaining capacity ${remaining_amount:,.2f}")
                return None
                
            return allocation_year
            
        except Exception as e:
            logger.error(f"Error validating allocation capacity: {str(e)}")
            return None
    
    async def get_allocation_year_summary(self, allocation_year_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive summary of allocation year with all QLICI loans."""
        try:
            # Get allocation year
            allocation_result = self.client.table('allocation_years').select('*').eq('id', allocation_year_id).execute()
            
            if not allocation_result.data:
                return None
                
            allocation_year = allocation_result.data[0]
            
            # Get QLICI loans
            qlici_loans = await self.get_qlici_loans_for_allocation_year(allocation_year_id)
            
            # Calculate summary metrics
            total_amount = float(allocation_year['total_amount'])
            deployed_amount = float(allocation_year['deployed_amount'] or 0)
            remaining_amount = total_amount - deployed_amount
            utilization_percent = (deployed_amount / total_amount * 100) if total_amount > 0 else 0
            
            return {
                'allocation_year': allocation_year,
                'qlici_loans': qlici_loans,
                'summary': {
                    'total_amount': total_amount,
                    'deployed_amount': deployed_amount,
                    'remaining_amount': remaining_amount,
                    'utilization_percent': utilization_percent,
                    'qlici_count': len(qlici_loans),
                    'total_documents': sum(loan.get('documents_count', 0) for loan in qlici_loans)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting allocation year summary: {str(e)}")
            return None

# Global service instance
qlici_loan_service = QLICILoanService()