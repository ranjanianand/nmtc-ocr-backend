"""
First-Level Metadata Extraction Service

This service performs immediate metadata extraction after Azure OCR using document type
purpose prompts to provide quick insights before full core engine processing.
"""

from typing import Dict, List, Any, Optional
import json
import logging
import asyncio
import time
from datetime import datetime
from app.services.ai_service import ai_service
from app.services.supabase_service import supabase_service

logger = logging.getLogger(__name__)

class MetadataExtractionService:
    """
    Handles first-level metadata extraction using document type purpose prompts
    """

    def __init__(self):
        self.service_name = "Metadata Extraction Service"
        logger.info(f"{self.service_name} initialized")

    async def extract_first_level_metadata(self,
                                         document_id: str,
                                         document_category: str,
                                         extracted_text: str) -> Dict[str, Any]:
        """
        Extract first-level metadata using document type purpose prompt

        Args:
            document_id: Document ID for tracking
            document_category: Document category (e.g., 'allocation_agreement')
            extracted_text: Raw text from Azure OCR

        Returns:
            Dictionary containing extracted metadata and processing info
        """
        try:
            logger.info(f"Starting first-level metadata extraction for document {document_id}, category: {document_category}")

            # Get document type purpose prompt
            purpose_prompt = await self._get_document_type_purpose(document_category)
            if not purpose_prompt:
                logger.warning(f"No purpose prompt found for document category: {document_category}")
                return {
                    'success': False,
                    'error': f'No purpose prompt configured for document category: {document_category}',
                    'metadata': {}
                }

            # Performance optimization: Limit text size for faster processing
            text_limit = 6000  # Reduced for faster LLM processing
            optimized_text = extracted_text[:text_limit] if len(extracted_text) > text_limit else extracted_text

            # Prepare the extraction prompt
            extraction_prompt = {
                'agent_key': f'{document_category}_metadata_extractor',
                'system_prompt': f'You are an expert NMTC document analyst. Extract key metadata from the provided document text according to the specific requirements for {document_category} documents. Be concise and accurate.',
                'prompt_text': f"""{purpose_prompt}

DOCUMENT TEXT TO ANALYZE (First {text_limit} characters):
{optimized_text}

Please extract the requested information and return it in clean JSON format. If any required information is not found in the text, mark those fields as "Not Found" or null as appropriate. Focus on accuracy and specific details. Be concise to improve processing speed."""
            }

            # Call LLM for metadata extraction with timeout and retry logic
            logger.info(f"Calling AI service for metadata extraction with {len(optimized_text)} characters of optimized text")

            extraction_result = None
            max_retries = 2

            for attempt in range(max_retries):
                try:
                    extraction_result = await asyncio.wait_for(
                        ai_service.apply_agent_prompt(
                            extracted_data={'document_text': optimized_text},
                            agent_prompt=extraction_prompt
                        ),
                        timeout=30.0  # 30 second timeout for LLM call
                    )
                    break  # Success, exit retry loop
                except asyncio.TimeoutError:
                    logger.warning(f"LLM extraction timeout on attempt {attempt + 1} for document {document_id}")
                    if attempt == max_retries - 1:  # Last attempt
                        return {
                            'success': False,
                            'error': 'LLM extraction timeout after retries',
                            'metadata': {},
                            'processing_info': {
                                'model_used': 'timeout',
                                'attempts': max_retries
                            }
                        }
                    await asyncio.sleep(2)  # Brief delay before retry
                except Exception as llm_error:
                    logger.error(f"LLM extraction error on attempt {attempt + 1} for document {document_id}: {llm_error}")
                    if attempt == max_retries - 1:  # Last attempt
                        return {
                            'success': False,
                            'error': f'LLM extraction failed: {str(llm_error)}',
                            'metadata': {},
                            'processing_info': {
                                'model_used': 'error',
                                'error_type': type(llm_error).__name__,
                                'attempts': max_retries
                            }
                        }
                    await asyncio.sleep(2)  # Brief delay before retry

            if not extraction_result.get('success', False):
                logger.error(f"LLM extraction failed for document {document_id}: {extraction_result}")
                return {
                    'success': False,
                    'error': 'LLM extraction failed',
                    'details': extraction_result,
                    'metadata': {}
                }

            # Parse the extracted metadata
            parsed_metadata = self._parse_extraction_result(extraction_result, document_category)

            # Structure the response
            result = {
                'success': True,
                'document_id': document_id,
                'document_category': document_category,
                'extraction_timestamp': datetime.now().isoformat(),
                'metadata': parsed_metadata,
                'processing_info': {
                    'text_length': len(extracted_text),
                    'model_used': extraction_result.get('agent_metadata', {}).get('model_used', 'unknown'),
                    'llm_response_length': extraction_result.get('agent_metadata', {}).get('llm_response_length', 0),
                    'extraction_method': 'document_type_purpose_prompt'
                },
                'raw_llm_response': extraction_result
            }

            logger.info(f"Successfully extracted first-level metadata for document {document_id}")
            return result

        except Exception as e:
            logger.error(f"Error in first-level metadata extraction for document {document_id}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'document_id': document_id,
                'metadata': {}
            }

    async def _get_document_type_purpose(self, document_category: str) -> Optional[str]:
        """
        Get the purpose prompt for the specified document category
        """
        try:
            supabase = supabase_service.client

            # Query document_types table for the purpose field
            # We'll look for records where the category matches or notes contain the category
            result = supabase.table('document_types').select('purpose, notes').execute()

            if not result.data:
                logger.warning("No document types found in database")
                return None

            # Find the matching document type
            for doc_type in result.data:
                purpose = doc_type.get('purpose')
                notes = doc_type.get('notes', '')

                # Check if this is the allocation agreement type (based on your example)
                if (document_category == 'allocation_agreement' and
                    purpose and
                    'Allocation Agreement' in purpose):
                    logger.info(f"Found purpose prompt for {document_category}")
                    return purpose

                # Check for QLICI loan
                elif (document_category == 'qlici_loan' and
                      purpose and
                      'QLICI Loan Agreement' in purpose):
                    logger.info(f"Found purpose prompt for {document_category}")
                    return purpose

                # Check for QALICB certification
                elif (document_category == 'qalicb_certification' and
                      purpose and
                      'QALICB Certification' in purpose):
                    logger.info(f"Found purpose prompt for {document_category}")
                    return purpose

            logger.warning(f"No purpose prompt found for document category: {document_category}")
            return None

        except Exception as e:
            logger.error(f"Error getting document type purpose for {document_category}: {e}")
            return None

    def _parse_extraction_result(self, extraction_result: Dict[str, Any], document_category: str) -> Dict[str, Any]:
        """
        Parse and clean the LLM extraction result
        """
        try:
            # Try to extract JSON from various possible response structures
            llm_response = None

            # Check different possible response structures
            if 'analysis_result' in extraction_result and 'summary' in extraction_result['analysis_result']:
                llm_response = extraction_result['analysis_result']['summary']
            elif 'risk_assessment' in extraction_result and 'analysis' in extraction_result['risk_assessment']:
                llm_response = extraction_result['risk_assessment']['analysis']
            elif 'report_generation' in extraction_result:
                llm_response = extraction_result['report_generation'].get('detailed_analysis', '')
            elif 'generic_result' in extraction_result:
                llm_response = extraction_result['generic_result'].get('analysis', '')

            if not llm_response:
                logger.warning("Could not find LLM response text in extraction result")
                return {'raw_response': extraction_result, 'parsed_json': None}

            # Try to parse JSON from the response
            parsed_json = self._extract_json_from_text(llm_response)

            if parsed_json:
                logger.info(f"Successfully parsed JSON metadata for {document_category}")
                return {
                    'parsed_json': parsed_json,
                    'confidence': 'high',
                    'structure': 'json_parsed'
                }
            else:
                logger.info(f"Could not parse JSON, returning structured text for {document_category}")
                return {
                    'raw_text': llm_response,
                    'confidence': 'medium',
                    'structure': 'text_only'
                }

        except Exception as e:
            logger.error(f"Error parsing extraction result: {e}")
            return {
                'error': str(e),
                'raw_response': extraction_result
            }

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from text that might contain markdown code blocks or other formatting
        """
        try:
            # Remove markdown code blocks
            if '```json' in text:
                start = text.find('```json') + 7
                end = text.find('```', start)
                if end > start:
                    json_text = text[start:end].strip()
                    return json.loads(json_text)

            # Try to find JSON between braces
            start = text.find('{')
            if start >= 0:
                # Find the matching closing brace
                brace_count = 0
                end = start
                for i, char in enumerate(text[start:], start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break

                if end > start:
                    json_text = text[start:end]
                    return json.loads(json_text)

            # Try parsing the entire text as JSON
            return json.loads(text.strip())

        except json.JSONDecodeError:
            return None
        except Exception as e:
            logger.debug(f"JSON extraction error: {e}")
            return None

    async def store_metadata_in_document(self, document_id: str, metadata_result: Dict[str, Any]) -> bool:
        """
        Store the extracted metadata in the document's processing_results field
        """
        try:
            # Get current processing results
            supabase = supabase_service.client

            current_doc = supabase.table('documents').select('processing_results').eq('id', document_id).execute()

            if not current_doc.data:
                logger.error(f"Document {document_id} not found")
                return False

            # Update processing results with metadata
            current_results = current_doc.data[0].get('processing_results') or {}

            # Add the metadata extraction stage
            current_results['stage_0a_metadata_extraction'] = {
                'status': 'completed' if metadata_result['success'] else 'failed',
                'timestamp': metadata_result.get('extraction_timestamp', datetime.now().isoformat()),
                'metadata': metadata_result.get('metadata', {}),
                'processing_info': metadata_result.get('processing_info', {}),
                'stage_name': 'First-Level Metadata Extraction',
                'stage_description': 'Immediate document insights using document type purpose prompts'
            }

            # Update the document
            update_result = supabase.table('documents').update({
                'processing_results': current_results
            }).eq('id', document_id).execute()

            if update_result.data:
                logger.info(f"Successfully stored metadata for document {document_id}")
                return True
            else:
                logger.error(f"Failed to update document {document_id} with metadata")
                return False

        except Exception as e:
            logger.error(f"Error storing metadata for document {document_id}: {e}")
            return False

# Global service instance
metadata_extraction_service = MetadataExtractionService()