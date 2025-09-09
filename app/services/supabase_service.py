from supabase import create_client, Client
from app.config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    async def create_document_record(self, org_id: str, file_path: str, metadata: dict):
        """Create initial document record in database"""
        try:
            logger.info(f"Creating document record for org: {org_id}, path: {file_path}")
            
            # Use exact column names from your table structure
            insert_data = {
                'org_id': org_id,
                'storage_path': file_path,
                'filename': metadata.get('filename'),
                'mime_type': 'application/pdf',
                'uploaded_by': org_id,  # Using org_id as uploaded_by for now
                'ocr_status': 'uploaded'
            }
            
            # Add document_type_id if provided
            if metadata.get('document_type'):
                insert_data['document_type_id'] = metadata.get('document_type')
            
            logger.info(f"Insert data: {insert_data}")
            
            result = self.client.table('documents').insert(insert_data).execute()
            
            logger.info(f"Database insert result: {result}")
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error creating document record: {e}")
            raise
    
    async def update_document_status(self, document_id: str, status: str, updates: dict = None):
        """Update document status and optional additional fields"""
        try:
            update_data = {'ocr_status': status}
            if updates:
                update_data.update(updates)
            
            result = self.client.table('documents').update(update_data).eq('id', document_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating document status: {e}")
            raise
    
    async def get_document(self, document_id: str):
        """Get document by ID"""
        try:
            result = self.client.table('documents').select('*').eq('id', document_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            raise
    
    def upload_file(self, file_path: str, file_content: bytes):
        """Upload file to Supabase Storage"""
        try:
            logger.info(f"Uploading file to storage: {file_path}")
            
            result = self.client.storage.from_('documents').upload(
                file_path, 
                file_content, 
                {"content-type": "application/pdf", "cache-control": "3600"}
            )
            
            logger.info(f"Storage upload result: {result}")
            
            # Check for errors
            if hasattr(result, 'error') and result.error:
                logger.error(f"Storage upload error: {result.error}")
                raise Exception(f"Storage error: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Exception during file upload: {e}")
            raise

# Global instance
supabase_service = SupabaseService()