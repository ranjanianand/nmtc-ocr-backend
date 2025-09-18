"""
Metadata Preview API Endpoints

Provides quick access to first-level metadata extraction results for immediate user feedback
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging
from app.services.supabase_service import supabase_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metadata", tags=["metadata"])

@router.get("/document/{document_id}/preview")
async def get_document_metadata_preview(document_id: str) -> Dict[str, Any]:
    """
    Get metadata preview for a specific document with optimized performance

    Returns first-level metadata extraction results if available,
    otherwise returns processing status
    """
    try:
        # Input validation
        if not document_id or len(document_id) < 10:
            raise HTTPException(status_code=400, detail="Invalid document ID")

        supabase = supabase_service.client

        # Optimized query: Only select needed fields for faster response
        doc_result = supabase.table('documents').select(
            'id, filename, ocr_status, processing_results, uploaded_at, document_category'
        ).eq('id', document_id).single().execute()

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        document = doc_result.data
        processing_results = document.get('processing_results', {})

        # Quick status check for common cases
        if not processing_results:
            return {
                'success': True,
                'document_id': document_id,
                'filename': document['filename'],
                'document_category': document['document_category'],
                'metadata_available': False,
                'ocr_status': document['ocr_status'],
                'status': 'processing',
                'message': 'Document is being processed. Metadata will be available shortly.'
            }

        # Check for Stage 0A metadata extraction results
        metadata_stage = processing_results.get('stage_0a_metadata_extraction')

        if metadata_stage and metadata_stage.get('status') == 'completed':
            # Return successful metadata extraction
            return {
                'success': True,
                'document_id': document_id,
                'filename': document['filename'],
                'document_category': document['document_category'],
                'metadata_available': True,
                'extraction_timestamp': metadata_stage.get('timestamp'),
                'metadata': metadata_stage.get('metadata', {}),
                'processing_info': metadata_stage.get('processing_info', {}),
                'confidence': metadata_stage.get('metadata', {}).get('confidence', 'unknown'),
                'status': 'completed'
            }

        elif metadata_stage and metadata_stage.get('status') == 'failed':
            # Return failed extraction info
            return {
                'success': False,
                'document_id': document_id,
                'filename': document['filename'],
                'document_category': document['document_category'],
                'metadata_available': False,
                'error': 'Metadata extraction failed',
                'status': 'failed'
            }

        else:
            # Return processing status
            return {
                'success': True,
                'document_id': document_id,
                'filename': document['filename'],
                'document_category': document['document_category'],
                'metadata_available': False,
                'ocr_status': document['ocr_status'],
                'status': 'processing',
                'message': 'Document is still being processed. Metadata will be available shortly.'
            }

    except Exception as e:
        logger.error(f"Error getting metadata preview for document {document_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metadata preview: {str(e)}"
        )

@router.get("/org/{org_id}/recent")
async def get_recent_metadata_previews(org_id: str, limit: int = 10) -> Dict[str, Any]:
    """
    Get recent documents with metadata previews for an organization
    """
    try:
        supabase = supabase_service.client

        # Get recent documents for the organization
        docs_result = supabase.table('documents').select(
            'id, filename, ocr_status, processing_results, uploaded_at, document_category'
        ).eq('org_id', org_id).order('uploaded_at', desc=True).limit(limit).execute()

        documents_with_metadata = []

        for doc in docs_result.data or []:
            processing_results = doc.get('processing_results', {})
            metadata_stage = processing_results.get('stage_0a_metadata_extraction')

            doc_preview = {
                'document_id': doc['id'],
                'filename': doc['filename'],
                'document_category': doc['document_category'],
                'uploaded_at': doc['uploaded_at'],
                'ocr_status': doc['ocr_status']
            }

            if metadata_stage and metadata_stage.get('status') == 'completed':
                doc_preview.update({
                    'metadata_available': True,
                    'status': 'completed',
                    'extraction_timestamp': metadata_stage.get('timestamp'),
                    'confidence': metadata_stage.get('metadata', {}).get('confidence', 'unknown')
                })
            elif metadata_stage and metadata_stage.get('status') == 'failed':
                doc_preview.update({
                    'metadata_available': False,
                    'status': 'failed'
                })
            else:
                doc_preview.update({
                    'metadata_available': False,
                    'status': 'processing'
                })

            documents_with_metadata.append(doc_preview)

        return {
            'success': True,
            'org_id': org_id,
            'documents': documents_with_metadata,
            'total_documents': len(documents_with_metadata)
        }

    except Exception as e:
        logger.error(f"Error getting recent metadata previews for org {org_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recent metadata previews: {str(e)}"
        )

@router.get("/health")
async def metadata_service_health() -> Dict[str, Any]:
    """Health check for metadata preview service"""
    try:
        # Test database connection
        supabase = supabase_service.client
        result = supabase.table('documents').select('id').limit(1).execute()

        return {
            'status': 'healthy',
            'service': 'metadata_preview',
            'database_connection': 'ok',
            'timestamp': '2025-09-16T17:15:00Z'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'service': 'metadata_preview',
            'error': str(e),
            'timestamp': '2025-09-16T17:15:00Z'
        }