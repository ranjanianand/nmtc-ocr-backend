from supabase import create_client, Client
from app.config import settings
from app.models.database import *
from typing import Optional, List, Dict, Any, Union
import logging
from datetime import datetime, date
import uuid

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base database error"""
    pass


class DatabaseService:
    def __init__(self):
        try:
            self.client: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
            logger.info("Database service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database service: {e}")
            raise DatabaseError(f"Failed to initialize database service: {e}")

    def _handle_db_error(self, error: Exception, operation: str, table: str = "") -> None:
        """Handle database errors with consistent logging"""
        error_msg = f"Database {operation} error"
        if table:
            error_msg += f" on {table}"
        error_msg += f": {str(error)}"
        logger.error(error_msg)
        raise DatabaseError(error_msg)

    def _validate_uuid(self, value: Union[str, uuid.UUID], field_name: str = "id") -> uuid.UUID:
        """Validate and convert UUID"""
        try:
            if isinstance(value, str):
                return uuid.UUID(value)
            elif isinstance(value, uuid.UUID):
                return value
            else:
                raise ValueError(f"Invalid UUID format for {field_name}")
        except ValueError as e:
            raise DatabaseError(f"Invalid UUID format for {field_name}: {e}")

    # Generic CRUD Operations
    async def create_record(self, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generic create operation for any table"""
        try:
            logger.info(f"Creating record in {table}")
            result = self.client.table(table).insert(data).execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Supabase error: {result.error}")
            
            return result.data[0] if result.data else None
        except Exception as e:
            self._handle_db_error(e, "create", table)

    async def get_record_by_id(self, table: str, record_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        """Generic get by ID operation for any table"""
        try:
            validated_id = self._validate_uuid(record_id)
            result = self.client.table(table).select('*').eq('id', str(validated_id)).execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Supabase error: {result.error}")
            
            return result.data[0] if result.data else None
        except Exception as e:
            self._handle_db_error(e, "get", table)

    async def update_record(self, table: str, record_id: Union[str, uuid.UUID], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generic update operation for any table"""
        try:
            validated_id = self._validate_uuid(record_id)
            logger.info(f"Updating record in {table}: {validated_id}")
            
            result = self.client.table(table).update(data).eq('id', str(validated_id)).execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Supabase error: {result.error}")
            
            return result.data[0] if result.data else None
        except Exception as e:
            self._handle_db_error(e, "update", table)

    async def delete_record(self, table: str, record_id: Union[str, uuid.UUID]) -> bool:
        """Generic delete operation for any table"""
        try:
            validated_id = self._validate_uuid(record_id)
            logger.info(f"Deleting record from {table}: {validated_id}")
            
            result = self.client.table(table).delete().eq('id', str(validated_id)).execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Supabase error: {result.error}")
            
            return len(result.data) > 0
        except Exception as e:
            self._handle_db_error(e, "delete", table)

    async def get_records_with_filters(
        self, 
        table: str, 
        filters: Dict[str, Any] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[Dict[str, Any]]:
        """Generic filtered query operation"""
        try:
            query = self.client.table(table).select('*')
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if value is not None:
                        query = query.eq(field, value)
            
            # Apply ordering
            if order_by:
                query = query.order(order_by, desc=order_desc)
            
            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            result = query.execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Supabase error: {result.error}")
            
            return result.data or []
        except Exception as e:
            self._handle_db_error(e, "query", table)

    # Organization Operations
    async def create_organization(self, org_data: OrganizationCreate, created_by: uuid.UUID, status_id: uuid.UUID) -> Optional[Organization]:
        """Create a new organization"""
        try:
            data = {
                "name": org_data.name,
                "created_by": str(created_by),
                "status_id": str(status_id)
            }
            
            if org_data.industry_type_id:
                data["industry_type_id"] = str(org_data.industry_type_id)
            
            result = await self.create_record("organizations", data)
            return Organization(**result) if result else None
        except Exception as e:
            self._handle_db_error(e, "create_organization")

    async def get_organization(self, org_id: uuid.UUID) -> Optional[Organization]:
        """Get organization by ID"""
        try:
            result = await self.get_record_by_id("organizations", org_id)
            return Organization(**result) if result else None
        except Exception as e:
            self._handle_db_error(e, "get_organization")

    async def update_organization(self, org_id: uuid.UUID, updates: OrganizationUpdate) -> Optional[Organization]:
        """Update organization"""
        try:
            data = {}
            if updates.name is not None:
                data["name"] = updates.name
            if updates.industry_type_id is not None:
                data["industry_type_id"] = str(updates.industry_type_id)
            if updates.status_id is not None:
                data["status_id"] = str(updates.status_id)
            
            if data:
                result = await self.update_record("organizations", org_id, data)
                return Organization(**result) if result else None
            
            return await self.get_organization(org_id)
        except Exception as e:
            self._handle_db_error(e, "update_organization")

    async def get_organizations_by_user(self, user_id: uuid.UUID) -> List[Organization]:
        """Get all organizations a user belongs to"""
        try:
            # First get org memberships
            memberships = await self.get_records_with_filters("org_members", {"user_id": str(user_id)})
            org_ids = [m["org_id"] for m in memberships]
            
            if not org_ids:
                return []
            
            # Get organizations
            query = self.client.table("organizations").select('*').in_('id', org_ids)
            result = query.execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Supabase error: {result.error}")
            
            return [Organization(**org) for org in result.data] if result.data else []
        except Exception as e:
            self._handle_db_error(e, "get_organizations_by_user")

    # Organization Member Operations
    async def create_org_member(self, org_id: uuid.UUID, member_data: OrgMemberCreate) -> Optional[OrgMember]:
        """Add user to organization"""
        try:
            data = {
                "org_id": str(org_id),
                "user_id": str(member_data.user_id),
                "role": member_data.role.value,
                "role_id": str(member_data.role_id)
            }
            
            result = await self.create_record("org_members", data)
            return OrgMember(**result) if result else None
        except Exception as e:
            self._handle_db_error(e, "create_org_member")

    async def get_org_members(self, org_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get all members of an organization"""
        try:
            # Use select with joins to get user and role details
            query = self.client.table("org_members").select(
                "*"
            ).eq("org_id", str(org_id))
            
            result = query.execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Supabase error: {result.error}")
            
            return result.data or []
        except Exception as e:
            self._handle_db_error(e, "get_org_members")

    async def remove_org_member(self, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Remove user from organization"""
        try:
            result = self.client.table("org_members").delete().eq("org_id", str(org_id)).eq("user_id", str(user_id)).execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Supabase error: {result.error}")
            
            return len(result.data) > 0
        except Exception as e:
            self._handle_db_error(e, "remove_org_member")

    async def update_member_role(self, org_id: uuid.UUID, user_id: uuid.UUID, new_role_id: uuid.UUID, new_role: OrgRole) -> Optional[OrgMember]:
        """Update organization member role"""
        try:
            data = {"role_id": str(new_role_id), "role": new_role.value}
            result = self.client.table("org_members").update(data).eq("org_id", str(org_id)).eq("user_id", str(user_id)).execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Supabase error: {result.error}")
            
            return OrgMember(**result.data[0]) if result.data else None
        except Exception as e:
            self._handle_db_error(e, "update_member_role")

    # Document Operations
    async def create_document(self, org_id: uuid.UUID, doc_data: DocumentCreate, uploaded_by: uuid.UUID) -> Optional[Document]:
        """Create a new document"""
        try:
            data = {
                "org_id": str(org_id),
                "filename": doc_data.filename,
                "storage_path": doc_data.storage_path,
                "mime_type": doc_data.mime_type,
                "uploaded_by": str(uploaded_by),
                "ocr_status": OcrStatus.QUEUED.value,
                "uploaded_at": datetime.now().isoformat()
            }
            
            if doc_data.document_type_id:
                data["document_type_id"] = str(doc_data.document_type_id)
            if doc_data.hash:
                data["hash"] = doc_data.hash
            
            result = await self.create_record("documents", data)
            return Document(**result) if result else None
        except Exception as e:
            self._handle_db_error(e, "create_document")

    async def get_document(self, document_id: uuid.UUID) -> Optional[Document]:
        """Get document by ID"""
        try:
            result = await self.get_record_by_id("documents", document_id)
            return Document(**result) if result else None
        except Exception as e:
            self._handle_db_error(e, "get_document")

    async def update_document(self, document_id: uuid.UUID, updates: DocumentUpdate) -> Optional[Document]:
        """Update document"""
        try:
            data = {}
            if updates.document_type_id is not None:
                data["document_type_id"] = str(updates.document_type_id)
            if updates.ocr_status is not None:
                data["ocr_status"] = updates.ocr_status.value
            if updates.parsed_index is not None:
                data["parsed_index"] = updates.parsed_index
            
            if data:
                result = await self.update_record("documents", document_id, data)
                return Document(**result) if result else None
            
            return await self.get_document(document_id)
        except Exception as e:
            self._handle_db_error(e, "update_document")

    async def get_organization_documents(
        self, 
        org_id: uuid.UUID,
        document_type_id: Optional[uuid.UUID] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Document]:
        """Get documents for an organization"""
        try:
            filters = {"org_id": str(org_id)}
            if document_type_id:
                filters["document_type_id"] = str(document_type_id)
            
            results = await self.get_records_with_filters(
                "documents", filters, limit=limit, offset=offset,
                order_by="uploaded_at", order_desc=True
            )
            
            return [Document(**doc) for doc in results]
        except Exception as e:
            self._handle_db_error(e, "get_organization_documents")

    # Document Type Operations
    async def get_document_types(self, org_id: Optional[uuid.UUID] = None) -> List[DocumentType]:
        """Get document types (templates or organization-specific)"""
        try:
            if org_id:
                # Get both template and org-specific types
                query = self.client.table("document_types").select('*').or_(
                    f"org_id.is.null,org_id.eq.{str(org_id)}"
                )
                result = query.execute()
                
                if hasattr(result, 'error') and result.error:
                    raise DatabaseError(f"Supabase error: {result.error}")
                
                return [DocumentType(**dt) for dt in result.data] if result.data else []
            else:
                # Get only template types (org_id is null)
                results = await self.get_records_with_filters("document_types", {"org_id": None})
                return [DocumentType(**dt) for dt in results]
        except Exception as e:
            self._handle_db_error(e, "get_document_types")

    async def get_document_type(self, document_type_id: uuid.UUID) -> Optional[DocumentType]:
        """Get document type by ID"""
        try:
            result = await self.get_record_by_id("document_types", document_type_id)
            return DocumentType(**result) if result else None
        except Exception as e:
            self._handle_db_error(e, "get_document_type")

    # Obligation Operations
    async def create_obligation(self, org_id: uuid.UUID, obligation_data: ObligationCreate) -> Optional[Obligation]:
        """Create a new obligation"""
        try:
            data = {
                "org_id": str(org_id),
                "document_id": str(obligation_data.document_id),
                "obligation_key": obligation_data.obligation_key,
                "document": obligation_data.document,
                "section": obligation_data.section,
                "obligation": obligation_data.obligation,
                "frequency": obligation_data.frequency.value,
                "responsible_party": obligation_data.responsible_party.value,
                "risk": obligation_data.risk.value,
                "dependencies": obligation_data.dependencies,
                "status": ObligationStatus.OPEN.value
            }
            
            if obligation_data.due_rule:
                data["due_rule"] = obligation_data.due_rule
            if obligation_data.next_due_date:
                data["next_due_date"] = obligation_data.next_due_date.isoformat()
            if obligation_data.source_citation:
                data["source_citation"] = obligation_data.source_citation
            if obligation_data.notes:
                data["notes"] = obligation_data.notes
            
            result = await self.create_record("obligations", data)
            return Obligation(**result) if result else None
        except Exception as e:
            self._handle_db_error(e, "create_obligation")

    async def get_obligation(self, obligation_id: uuid.UUID) -> Optional[Obligation]:
        """Get obligation by ID"""
        try:
            result = await self.get_record_by_id("obligations", obligation_id)
            return Obligation(**result) if result else None
        except Exception as e:
            self._handle_db_error(e, "get_obligation")

    async def update_obligation(self, obligation_id: uuid.UUID, updates: ObligationUpdate) -> Optional[Obligation]:
        """Update obligation"""
        try:
            data = {}
            
            # Handle all possible updates
            if updates.obligation_key is not None:
                data["obligation_key"] = updates.obligation_key
            if updates.document is not None:
                data["document"] = updates.document
            if updates.section is not None:
                data["section"] = updates.section
            if updates.obligation is not None:
                data["obligation"] = updates.obligation
            if updates.frequency is not None:
                data["frequency"] = updates.frequency.value
            if updates.due_rule is not None:
                data["due_rule"] = updates.due_rule
            if updates.next_due_date is not None:
                data["next_due_date"] = updates.next_due_date.isoformat()
            if updates.responsible_party is not None:
                data["responsible_party"] = updates.responsible_party.value
            if updates.risk is not None:
                data["risk"] = updates.risk.value
            if updates.source_citation is not None:
                data["source_citation"] = updates.source_citation
            if updates.dependencies is not None:
                data["dependencies"] = updates.dependencies
            if updates.notes is not None:
                data["notes"] = updates.notes
            if updates.status is not None:
                data["status"] = updates.status.value
            if updates.computed_due_dates is not None:
                data["computed_due_dates"] = updates.computed_due_dates
            
            # Always update the updated_at timestamp
            data["updated_at"] = datetime.now().isoformat()
            
            if data:
                result = await self.update_record("obligations", obligation_id, data)
                return Obligation(**result) if result else None
            
            return await self.get_obligation(obligation_id)
        except Exception as e:
            self._handle_db_error(e, "update_obligation")

    async def get_organization_obligations(
        self,
        org_id: uuid.UUID,
        status: Optional[ObligationStatus] = None,
        risk_level: Optional[RiskLevel] = None,
        due_before: Optional[date] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get obligations for an organization with filtering"""
        try:
            query = self.client.table("obligations").select('*').eq("org_id", str(org_id))
            
            if status:
                query = query.eq("status", status.value)
            if risk_level:
                query = query.eq("risk", risk_level.value)
            if due_before:
                query = query.lte("next_due_date", due_before.isoformat())
            
            query = query.order("next_due_date")
            
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            result = query.execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Supabase error: {result.error}")
            
            return result.data or []
        except Exception as e:
            self._handle_db_error(e, "get_organization_obligations")

    async def get_overdue_obligations(self, org_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get overdue obligations for an organization"""
        try:
            today = date.today()
            return await self.get_organization_obligations(
                org_id=org_id,
                due_before=today
            )
        except Exception as e:
            self._handle_db_error(e, "get_overdue_obligations")

    # System Configuration Operations
    async def get_status_types(self) -> List[StatusType]:
        """Get all status types"""
        try:
            results = await self.get_records_with_filters("status_types", {}, order_by="order_index")
            return [StatusType(**st) for st in results]
        except Exception as e:
            self._handle_db_error(e, "get_status_types")

    async def get_user_roles(self) -> List[UserRole]:
        """Get all user roles"""
        try:
            results = await self.get_records_with_filters("user_roles", {}, order_by="order_index")
            return [UserRole(**ur) for ur in results]
        except Exception as e:
            self._handle_db_error(e, "get_user_roles")

    async def get_industry_types(self) -> List[IndustryType]:
        """Get all industry types"""
        try:
            results = await self.get_records_with_filters("industry_types", {}, order_by="order_index")
            return [IndustryType(**it) for it in results]
        except Exception as e:
            self._handle_db_error(e, "get_industry_types")

    # Audit Operations
    async def create_audit_log(
        self,
        scope: str,
        action: str,
        org_id: Optional[uuid.UUID] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        record_id: Optional[uuid.UUID] = None,
        diff: Optional[Dict[str, Any]] = None,
        category_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create audit log entry"""
        try:
            data = {
                "scope": scope,
                "action": action,
                "created_at": datetime.now().isoformat()
            }
            
            if org_id:
                data["org_id"] = str(org_id)
            if actor_user_id:
                data["actor_user_id"] = str(actor_user_id)
            if record_id:
                data["record_id"] = str(record_id)
            if diff:
                data["diff"] = diff
            if category_id:
                data["category_id"] = str(category_id)
            if ip_address:
                data["ip_address"] = ip_address
            if user_agent:
                data["user_agent"] = user_agent
            
            return await self.create_record("audit_log", data)
        except Exception as e:
            self._handle_db_error(e, "create_audit_log")

    # File Storage Operations
    def upload_file(self, file_path: str, file_content: bytes, content_type: str = "application/pdf"):
        """Upload file to Supabase Storage"""
        try:
            logger.info(f"Uploading file to storage: {file_path}")
            
            result = self.client.storage.from_('documents').upload(
                file_path,
                file_content,
                {"content-type": content_type, "cache-control": "3600"}
            )
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Storage upload error: {result.error}")
            
            return result
        except Exception as e:
            self._handle_db_error(e, "upload_file", "storage")

    def get_file_url(self, file_path: str) -> str:
        """Get public URL for a file in storage"""
        try:
            result = self.client.storage.from_('documents').get_public_url(file_path)
            return result.get('publicUrl', '')
        except Exception as e:
            self._handle_db_error(e, "get_file_url", "storage")


    # Document Processing Methods for Quick Detection
    async def update_document_ocr_status(self, document_id: uuid.UUID, new_status: OcrStatus) -> Optional[Document]:
        """Update document OCR status"""
        try:
            result = await self.update_record("documents", document_id, {"ocr_status": new_status.value})
            return Document(**result) if result else None
        except Exception as e:
            self._handle_db_error(e, "update_document_ocr_status")

    async def store_ocr_results(
        self, 
        document_id: uuid.UUID, 
        ocr_results: Dict[str, Any], 
        status: OcrStatus = OcrStatus.COMPLETED
    ) -> Optional[Document]:
        """Store OCR processing results in document"""
        try:
            # Get current parsed_index
            document = await self.get_document(document_id)
            if not document:
                raise DatabaseError(f"Document {document_id} not found")
            
            # Update parsed_index with OCR results
            current_parsed_index = document.parsed_index or {}
            current_parsed_index["ocr_results"] = ocr_results
            current_parsed_index["last_updated"] = datetime.now().isoformat()
            
            # Update document with new status and results
            result = await self.update_record("documents", document_id, {
                "ocr_status": status.value,
                "parsed_index": current_parsed_index
            })
            
            return Document(**result) if result else None
        except Exception as e:
            self._handle_db_error(e, "store_ocr_results")

    async def get_documents_by_status(
        self, 
        org_id: uuid.UUID, 
        status: OcrStatus,
        limit: Optional[int] = None
    ) -> List[Document]:
        """Get documents by OCR status for an organization"""
        try:
            filters = {"org_id": str(org_id), "ocr_status": status.value}
            results = await self.get_records_with_filters(
                "documents", filters, limit=limit, 
                order_by="uploaded_at", order_desc=True
            )
            return [Document(**doc) for doc in results]
        except Exception as e:
            self._handle_db_error(e, "get_documents_by_status")

    async def get_processing_queue(self, limit: Optional[int] = None) -> List[Document]:
        """Get documents queued for processing"""
        try:
            results = await self.get_records_with_filters(
                "documents", 
                {"ocr_status": OcrStatus.QUEUED.value},
                limit=limit,
                order_by="uploaded_at"
            )
            return [Document(**doc) for doc in results]
        except Exception as e:
            self._handle_db_error(e, "get_processing_queue")

    async def get_failed_documents(
        self, 
        org_id: Optional[uuid.UUID] = None,
        limit: Optional[int] = None
    ) -> List[Document]:
        """Get documents that failed processing"""
        try:
            filters = {"ocr_status": OcrStatus.ERROR.value}
            if org_id:
                filters["org_id"] = str(org_id)
            
            results = await self.get_records_with_filters(
                "documents", filters, limit=limit,
                order_by="uploaded_at", order_desc=True
            )
            return [Document(**doc) for doc in results]
        except Exception as e:
            self._handle_db_error(e, "get_failed_documents")

    async def reset_stuck_documents(self, timeout_minutes: int = 60) -> List[uuid.UUID]:
        """Reset documents stuck in processing state"""
        try:
            # Calculate timeout threshold
            timeout_threshold = datetime.now().timestamp() - (timeout_minutes * 60)
            
            # Find stuck documents (in processing state for too long)
            query = self.client.table("documents").select('*').eq("ocr_status", OcrStatus.PROCESSING.value)
            result = query.execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Query failed: {result.error}")
            
            stuck_documents = []
            for doc in result.data or []:
                # Check if document has been processing for too long
                uploaded_at = datetime.fromisoformat(doc['uploaded_at'].replace('Z', '+00:00'))
                if uploaded_at.timestamp() < timeout_threshold:
                    stuck_documents.append(uuid.UUID(doc['id']))
            
            # Reset stuck documents to queued status
            reset_count = 0
            for doc_id in stuck_documents:
                try:
                    await self.update_record("documents", doc_id, {
                        "ocr_status": OcrStatus.QUEUED.value
                    })
                    reset_count += 1
                except Exception as e:
                    logger.warning(f"Failed to reset document {doc_id}: {e}")
            
            logger.info(f"Reset {reset_count} stuck documents out of {len(stuck_documents)} found")
            return stuck_documents[:reset_count]
            
        except Exception as e:
            self._handle_db_error(e, "reset_stuck_documents")

    async def get_document_processing_stats(self, org_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """Get document processing statistics"""
        try:
            filters = {}
            if org_id:
                filters["org_id"] = str(org_id)
            
            # Get counts for each status
            stats = {
                "total": 0,
                "queued": 0,
                "processing": 0,
                "completed": 0,
                "error": 0,
                "uploaded": 0  # Legacy status
            }
            
            for status in [OcrStatus.QUEUED, OcrStatus.PROCESSING, OcrStatus.COMPLETED, OcrStatus.ERROR, OcrStatus.UPLOADED]:
                status_filters = {**filters, "ocr_status": status.value}
                results = await self.get_records_with_filters("documents", status_filters)
                count = len(results)
                stats[status.value] = count
                stats["total"] += count
            
            return stats
        except Exception as e:
            self._handle_db_error(e, "get_document_processing_stats")

    async def search_documents_by_content(
        self, 
        org_id: uuid.UUID, 
        search_text: str, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search documents by OCR text content"""
        try:
            # This is a simplified search - in production you'd use full-text search
            # For now, we'll search in the parsed_index JSON
            query = self.client.table("documents").select('*').eq("org_id", str(org_id))
            result = query.execute()
            
            if hasattr(result, 'error') and result.error:
                raise DatabaseError(f"Search query failed: {result.error}")
            
            matching_docs = []
            for doc in result.data or []:
                # Check if search text appears in OCR results
                parsed_index = doc.get('parsed_index', {})
                ocr_results = parsed_index.get('ocr_results', {})
                full_text = ocr_results.get('full_text', '').lower()
                
                if search_text.lower() in full_text:
                    # Add relevance score based on frequency
                    relevance = full_text.count(search_text.lower())
                    doc['relevance_score'] = relevance
                    matching_docs.append(doc)
                    
                    if limit and len(matching_docs) >= limit:
                        break
            
            # Sort by relevance
            matching_docs.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            return matching_docs
        except Exception as e:
            self._handle_db_error(e, "search_documents_by_content")


# Global instance
database_service = DatabaseService()