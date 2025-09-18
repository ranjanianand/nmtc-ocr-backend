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
    
    async def create_document_record(self, org_id: str, file_path: str, metadata: dict, user_id: str = None):
        """Create initial document record in database with system user fallback"""
        try:
            logger.info(f"Creating document record for org: {org_id}, path: {file_path}")

            # Use exact column names from your table structure
            insert_data = {
                'org_id': org_id,
                'storage_path': file_path,
                'filename': metadata.get('filename'),
                'mime_type': 'application/pdf',
                'uploaded_by': user_id if user_id else '633e6379-c82f-4917-8215-6a8f0a7e972f',  # System user from seed data
                'ocr_status': 'processing'
            }
            
            # Handle document type - use document_category for allocation documents
            document_type_id = metadata.get('document_type_id')
            if document_type_id:
                # For allocation years, always use document_category instead of document_type_id
                if document_type_id in ['allocation_agreement', 'qlici_loan', 'qalicb_certification']:
                    insert_data['document_category'] = document_type_id
                    # Explicitly do NOT add document_type_id when using document_category
                    logger.info(f"Using document_category: {document_type_id} (skipping document_type_id)")
                else:
                    # Only add document_type_id if it looks like a UUID
                    import re
                    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
                    if uuid_pattern.match(document_type_id):
                        insert_data['document_type_id'] = document_type_id
                        logger.info(f"Using document_type_id UUID: {document_type_id}")
                    else:
                        logger.warning(f"Invalid document_type_id format: {document_type_id}, skipping")
            
            # Add description if provided
            if metadata.get('description'):
                insert_data['description'] = metadata.get('description')
                
            # Add user_selected_type flag
            if metadata.get('user_selected_type') is not None:
                insert_data['user_selected_type'] = metadata.get('user_selected_type')
            
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