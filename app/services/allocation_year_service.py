"""
NMTC Allocation Year Detection and Management Service
Handles auto-detection and creation of allocation years from processed documents.
"""

import re
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any
from decimal import Decimal

from app.services.supabase_service import supabase_service

logger = logging.getLogger(__name__)

class AllocationYearService:
    """
    Service for managing NMTC allocation years and auto-detection from documents.
    This runs AFTER core engine processing to analyze results for allocation data.
    """
    
    def __init__(self):
        self.client = supabase_service.client
    
    async def analyze_for_allocation_data(self, document_id: str, processing_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze core engine processing results to detect allocation agreement data.
        This is called AFTER the normal processing pipeline completes.
        
        Args:
            document_id: Document ID that was processed
            processing_results: Results from core engine processing
            
        Returns:
            Dict with allocation data if detected, None otherwise
        """
        try:
            logger.info(f"Analyzing document {document_id} for allocation data")
            
            # Get the processed document
            doc_result = self.client.table('documents').select('*').eq('id', document_id).execute()
            if not doc_result.data:
                logger.error(f"Document {document_id} not found")
                return None
                
            document = doc_result.data[0]
            
            # Only analyze if document type suggests it could be an allocation
            doc_type_result = self.client.table('document_types').select('key').eq('id', document.get('document_type_id')).execute()
            doc_type_key = doc_type_result.data[0]['key'] if doc_type_result.data else 'unknown'
            
            if 'allocation' not in doc_type_key.lower():
                logger.info(f"Document type {doc_type_key} is not allocation-related, skipping")
                return None
            
            # Extract text content from processing results
            extracted_text = ""
            if processing_results.get('extracted_text'):
                extracted_text = processing_results['extracted_text']
            elif processing_results.get('parsed_index', {}).get('extracted_text'):
                extracted_text = processing_results['parsed_index']['extracted_text']
            
            if not extracted_text:
                logger.warning(f"No extracted text found for document {document_id}")
                return None
            
            # Analyze text for allocation patterns
            allocation_data = self._extract_allocation_patterns(extracted_text)
            
            if allocation_data:
                logger.info(f"Detected allocation data: {allocation_data}")
                
                # Create or update allocation year record
                allocation_year = await self._create_or_update_allocation_year(
                    org_id=document['org_id'],
                    document_id=document_id,
                    allocation_data=allocation_data
                )
                
                # Link document to allocation year
                if allocation_year:
                    await self._link_document_to_allocation_year(document_id, allocation_year['id'])
                
                return {
                    'allocation_detected': True,
                    'allocation_year_id': allocation_year['id'] if allocation_year else None,
                    'allocation_data': allocation_data
                }
            else:
                logger.info(f"No allocation data detected in document {document_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing allocation data for document {document_id}: {str(e)}")
            return None
    
    def _extract_allocation_patterns(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract allocation-specific data patterns from processed text.
        Uses regex patterns to find common allocation agreement elements.
        """
        allocation_data = {}
        
        # Pattern 1: Year detection (2024, 2025, etc.)
        year_patterns = [
            r'(?:allocation|award|grant).*?(?:year\s+)?(\d{4})',
            r'(\d{4})\s+(?:allocation|award|grant)',
            r'calendar\s+year\s+(\d{4})',
            r'tax\s+year\s+(\d{4})'
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                year = int(match.group(1))
                if 2020 <= year <= 2030:  # Reasonable year range
                    allocation_data['year'] = year
                    break
        
        # Pattern 2: Amount detection (various currency formats)
        amount_patterns = [
            r'\$[\d,]+(?:\.\d{2})?(?:\s+(?:million|mil|M))?',
            r'(?:amount|total|sum).*?\$[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*(?:dollars?|USD)',
        ]
        
        amounts_found = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Parse amount from string
                amount = self._parse_amount_string(match)
                if amount and amount > 1000000:  # At least $1M (reasonable allocation)
                    amounts_found.append(amount)
        
        if amounts_found:
            # Take the largest reasonable amount found
            allocation_data['total_amount'] = max(amounts_found)
        
        # Pattern 3: CDE/Organization name
        org_patterns = [
            r'(?:CDE|Community Development Entity)[\s\:]+([^\n\r]+)',
            r'(?:allocatee|recipient)[\s\:]+([^\n\r]+)',
        ]
        
        for pattern in org_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                allocation_data['organization_name'] = match.group(1).strip()
                break
        
        # Pattern 4: Date ranges (compliance periods)
        date_patterns = [
            r'(?:compliance\s+period|effective\s+period).*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}).*?(?:through|to|until).*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
            r'(\d{4}).*?(?:through|to|until).*?(\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    start_date = self._parse_date_string(match.group(1))
                    end_date = self._parse_date_string(match.group(2))
                    if start_date and end_date:
                        allocation_data['compliance_start_date'] = start_date
                        allocation_data['compliance_end_date'] = end_date
                        break
                except:
                    continue
        
        # Return data only if we found meaningful allocation indicators
        if allocation_data.get('year') and allocation_data.get('total_amount'):
            logger.info(f"Extracted allocation patterns: {allocation_data}")
            return allocation_data
        else:
            logger.info("No meaningful allocation patterns found")
            return None
    
    def _parse_amount_string(self, amount_str: str) -> Optional[float]:
        """Parse various currency string formats into float values."""
        try:
            # Remove currency symbols and common words
            clean_str = re.sub(r'[^\d,.]', '', amount_str)
            clean_str = clean_str.replace(',', '')
            
            amount = float(clean_str)
            
            # Handle millions notation
            if 'million' in amount_str.lower() or ' mil' in amount_str.lower() or 'M' in amount_str:
                amount *= 1000000
                
            return amount
        except:
            return None
    
    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """Parse various date string formats."""
        try:
            # Try different date formats
            for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except:
                    continue
            return None
        except:
            return None
    
    async def _create_or_update_allocation_year(self, org_id: str, document_id: str, allocation_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create or update allocation year record."""
        try:
            year = allocation_data['year']
            
            # Check if allocation year already exists
            existing_result = self.client.table('allocation_years').select('*').eq('org_id', org_id).eq('year', year).execute()
            
            if existing_result.data:
                # Update existing record
                allocation_year = existing_result.data[0]
                update_data = {
                    'total_amount': allocation_data.get('total_amount', allocation_year['total_amount']),
                    'allocation_document_id': document_id,
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                if allocation_data.get('compliance_start_date'):
                    update_data['compliance_start_date'] = allocation_data['compliance_start_date'].isoformat()
                if allocation_data.get('compliance_end_date'):
                    update_data['compliance_end_date'] = allocation_data['compliance_end_date'].isoformat()
                
                result = self.client.table('allocation_years').update(update_data).eq('id', allocation_year['id']).execute()
                logger.info(f"Updated existing allocation year {year} for org {org_id}")
                return result.data[0] if result.data else None
            else:
                # Create new allocation year
                insert_data = {
                    'org_id': org_id,
                    'year': year,
                    'total_amount': allocation_data['total_amount'],
                    'deployed_amount': 0,
                    'status': 'active',
                    'allocation_document_id': document_id,
                    'notes': f'Auto-created from allocation agreement document'
                }
                
                if allocation_data.get('compliance_start_date'):
                    insert_data['compliance_start_date'] = allocation_data['compliance_start_date'].isoformat()
                if allocation_data.get('compliance_end_date'):
                    insert_data['compliance_end_date'] = allocation_data['compliance_end_date'].isoformat()
                
                result = self.client.table('allocation_years').insert(insert_data).execute()
                logger.info(f"Created new allocation year {year} for org {org_id}")
                return result.data[0] if result.data else None
                
        except Exception as e:
            logger.error(f"Error creating/updating allocation year: {str(e)}")
            return None
    
    async def _link_document_to_allocation_year(self, document_id: str, allocation_year_id: str) -> bool:
        """Link document to its detected allocation year."""
        try:
            update_data = {
                'allocation_year_id': allocation_year_id,
                'document_category': 'allocation',
                'validation_status': 'validated'
            }
            
            result = self.client.table('documents').update(update_data).eq('id', document_id).execute()
            logger.info(f"Linked document {document_id} to allocation year {allocation_year_id}")
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error linking document to allocation year: {str(e)}")
            return False
    
    async def get_allocation_years_for_org(self, org_id: str) -> list:
        """Get all allocation years for an organization."""
        try:
            result = self.client.table('allocation_years').select('*').eq('org_id', org_id).order('year', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error fetching allocation years for org {org_id}: {str(e)}")
            return []

# Global service instance
allocation_year_service = AllocationYearService()