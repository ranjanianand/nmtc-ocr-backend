"""
NMTC Core Engine Database Service - Enterprise CRUD Operations

Comprehensive database service for managing processing sessions, agent states,
background jobs, and real-time progress tracking with enterprise scalability.

Author: Database Architect Agent + Core Engine Processing Agent
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import traceback

from app.services.supabase_service import supabase_service
from app.config import settings

logger = logging.getLogger(__name__)

class ProcessingSessionStatus(str, Enum):
    QUEUED = "queued"
    STARTING = "starting"
    STAGE_0A_RUNNING = "stage_0a_running"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CORE_PIPELINE_RUNNING = "core_pipeline_running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class AgentStageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    REQUIRES_INPUT = "requires_input"

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRY_SCHEDULED = "retry_scheduled"

# Agent Output Table Enums
class ValidationStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NEEDS_REVIEW = "needs_review"
    UNKNOWN = "unknown"

class DatabaseService:
    """Enterprise database service for Core Engine operations"""
    
    def __init__(self):
        self.client = supabase_service.client
        self.connection_pool_size = 20
        self.query_timeout = 30
        
    # ========================================
    # PROCESSING SESSIONS MANAGEMENT
    # ========================================
    
    async def create_processing_session(
        self,
        document_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        org_id: uuid.UUID,
        session_type: str = 'full_pipeline',
        priority: int = 100,
        configuration: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create new processing session with proper initialization"""
        
        session_data = {
            'document_id': str(document_id),
            'user_id': str(user_id) if user_id else None,
            'org_id': str(org_id),
            'session_type': session_type,
            'status': ProcessingSessionStatus.QUEUED.value,
            'current_stage': 'uploaded',
            'priority': priority,
            'configuration': configuration or {
                'enable_stage_0a': True,
                'require_user_confirmation': True,
                'enable_real_time_updates': True,
                'timeout_minutes': 30
            }
        }
        
        try:
            result = await self._execute_insert('processing_sessions', session_data)
            session_id = result['id']
            
            # Initialize agent pipeline states
            await self._initialize_agent_pipeline_states(session_id)
            
            logger.info(f"Created processing session {session_id} for document {document_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create processing session: {str(e)}")
            raise
    
    async def update_session_progress(
        self,
        session_id: uuid.UUID,
        status: Optional[ProcessingSessionStatus] = None,
        current_stage: Optional[str] = None,
        progress_percentage: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update session progress with real-time event emission"""
        
        update_data = {
            'last_heartbeat': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if status is not None:
            update_data['status'] = status.value
        if current_stage is not None:
            update_data['current_stage'] = current_stage
        if progress_percentage is not None:
            update_data['progress_percentage'] = progress_percentage
        if metadata is not None:
            update_data['metadata'] = metadata
        
        try:
            result = await self._execute_update('processing_sessions', session_id, update_data)
            
            # Create progress event for real-time updates
            if current_stage and progress_percentage is not None:
                await self.create_progress_event(
                    session_id=session_id,
                    event_type='progress_update',
                    stage_name=current_stage,
                    progress_percentage=progress_percentage,
                    message=f"Session progress: {progress_percentage}%"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update session progress: {str(e)}")
            raise
    
    async def get_processing_session(self, session_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get processing session by ID with related data"""
        try:
            result = await self._execute_select(
                'processing_sessions',
                filters={'id': str(session_id)},
                single=True
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get processing session {session_id}: {str(e)}")
            return None
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            result = await self._execute_select(
                'documents',
                filters={'id': document_id},
                single=True
            )
            return result
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {str(e)}")
            return None
    
    async def get_document_types(self, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get document types, optionally filtered by organization"""
        try:
            filters = {}
            if org_id:
                filters['org_id'] = org_id
                
            result = await self._execute_select(
                'document_types',
                filters=filters
            )
            return result or []
        except Exception as e:
            logger.error(f"Failed to get document types: {str(e)}")
            return []
    
    async def get_active_sessions_for_user(
        self,
        user_id: uuid.UUID,
        org_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get active processing sessions for a user"""
        
        filters = {
            'user_id': str(user_id),
            'status': ['queued', 'starting', 'stage_0a_running', 'core_pipeline_running', 'awaiting_confirmation']
        }
        
        if org_id:
            filters['org_id'] = str(org_id)
        
        try:
            return await self._execute_select(
                'processing_sessions',
                filters=filters,
                order_by='created_at',
                order_desc=True
            )
        except Exception as e:
            logger.error(f"Failed to get active sessions for user {user_id}: {str(e)}")
            return []
    
    # ========================================
    # AGENT PIPELINE STATES MANAGEMENT
    # ========================================
    
    async def _initialize_agent_pipeline_states(self, session_id: str):
        """Initialize agent pipeline states for a new session"""
        
        agents = [
            'document_analyzer',
            'compliance_checker',
            'report_generator'
        ]
        
        for agent_key in agents:
            state_data = {
                'session_id': session_id,
                'agent_key': agent_key,
                'status': AgentStageStatus.PENDING.value
            }
            await self._execute_insert('agent_pipeline_states', state_data)
    
    async def update_agent_state(
        self,
        session_id: uuid.UUID,
        agent_key: str,
        status: AgentStageStatus,
        progress_percentage: Optional[int] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
        quality_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update agent execution state with comprehensive tracking"""
        
        update_data = {
            'status': status.value,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if progress_percentage is not None:
            update_data['progress_percentage'] = progress_percentage
        
        if status == AgentStageStatus.RUNNING:
            update_data['started_at'] = datetime.utcnow().isoformat()
        elif status in [AgentStageStatus.COMPLETED, AgentStageStatus.FAILED]:
            update_data['completed_at'] = datetime.utcnow().isoformat()
            
        if input_data:
            update_data['input_data'] = input_data
        if output_data:
            update_data['output_data'] = output_data
        if error_details:
            update_data['error_details'] = error_details
        if confidence_score is not None:
            update_data['confidence_score'] = confidence_score
        if quality_metrics:
            update_data['quality_metrics'] = quality_metrics
        
        try:
            # Update agent state
            result = await self._execute_update_with_filters(
                'agent_pipeline_states',
                filters={'session_id': str(session_id), 'agent_key': agent_key},
                update_data=update_data
            )
            
            # Update session progress based on all agents
            await self._update_session_progress_from_agents(session_id)
            
            # Create progress event
            await self.create_progress_event(
                session_id=session_id,
                event_type='agent_update',
                stage_name=agent_key,
                progress_percentage=progress_percentage or 0,
                message=f"Agent {agent_key}: {status.value}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to update agent state: {str(e)}")
            raise
    
    async def get_agent_states_for_session(self, session_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Get all agent states for a session"""
        try:
            return await self._execute_select(
                'agent_pipeline_states',
                filters={'session_id': str(session_id)},
                order_by='stage_order'
            )
        except Exception as e:
            logger.error(f"Failed to get agent states for session {session_id}: {str(e)}")
            return []
    
    async def _update_session_progress_from_agents(self, session_id: uuid.UUID):
        """Calculate and update session progress based on agent states"""
        try:
            agents = await self.get_agent_states_for_session(session_id)
            
            if not agents:
                return
            
            # Calculate overall progress
            total_progress = sum(agent.get('progress_percentage', 0) for agent in agents)
            average_progress = total_progress // len(agents)
            
            # Determine current stage based on active agent
            current_stage = 'core_pipeline_running'
            for agent in sorted(agents, key=lambda x: x['stage_order']):
                if agent['status'] == AgentStageStatus.RUNNING.value:
                    current_stage = f"running_{agent['agent_key']}"
                    break
                elif agent['status'] == AgentStageStatus.FAILED.value:
                    current_stage = 'failed'
                    break
            
            # Check if all agents completed
            all_completed = all(
                agent['status'] == AgentStageStatus.COMPLETED.value 
                for agent in agents
            )
            
            if all_completed:
                current_stage = 'processing_complete'
                average_progress = 100
            
            await self.update_session_progress(
                session_id=session_id,
                current_stage=current_stage,
                progress_percentage=average_progress
            )
            
        except Exception as e:
            logger.error(f"Failed to update session progress from agents: {str(e)}")
    
    # ========================================
    # BACKGROUND JOBS MANAGEMENT
    # ========================================
    
    async def enqueue_background_job(
        self,
        job_type: str,
        job_key: str,
        input_parameters: Dict[str, Any],
        session_id: Optional[uuid.UUID] = None,
        priority: int = 100,
        timeout_seconds: int = 1800,
        max_retry_attempts: int = 3
    ) -> Dict[str, Any]:
        """Enqueue background job with deduplication and priority handling"""
        
        job_data = {
            'job_type': job_type,
            'job_key': job_key,
            'parent_session_id': str(session_id) if session_id else None,
            'priority': priority,
            'timeout_seconds': timeout_seconds,
            'max_retry_attempts': max_retry_attempts,
            'input_parameters': input_parameters
        }
        
        try:
            # Try to create new job
            result = await self._execute_insert('background_jobs', job_data)
            logger.info(f"Enqueued job {job_key} with ID {result['id']}")
            return result
            
        except Exception as e:
            # Handle job key conflict (deduplication)
            if 'job_key_unique' in str(e):
                existing_job = await self.get_job_by_key(job_key)
                if existing_job and existing_job['status'] in ['queued', 'running']:
                    logger.info(f"Job {job_key} already exists and is active")
                    return existing_job
                elif existing_job:
                    # Requeue failed job
                    await self.requeue_job(existing_job['id'])
                    return existing_job
            raise
    
    async def get_next_job(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Get next job for worker with proper locking (FOR UPDATE SKIP LOCKED)"""
        
        try:
            # Use raw SQL for proper locking
            query = """
            UPDATE background_jobs 
            SET status = 'running', 
                started_at = now(), 
                worker_id = %s,
                updated_at = now()
            WHERE id = (
                SELECT id FROM background_jobs 
                WHERE status IN ('queued', 'retry_scheduled') 
                AND scheduled_at <= now()
                ORDER BY priority ASC, scheduled_at ASC 
                LIMIT 1 
                FOR UPDATE SKIP LOCKED
            )
            RETURNING *;
            """
            
            result = await self._execute_raw_query(query, [worker_id])
            
            if result:
                logger.info(f"Worker {worker_id} claimed job {result[0]['id']}")
                return result[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get next job for worker {worker_id}: {str(e)}")
            return None
    
    async def complete_job(
        self,
        job_id: uuid.UUID,
        output_results: Optional[Dict[str, Any]] = None,
        success: bool = True
    ) -> Dict[str, Any]:
        """Mark job as completed or failed"""
        
        update_data = {
            'completed_at': datetime.utcnow().isoformat(),
            'status': JobStatus.COMPLETED.value if success else JobStatus.FAILED.value,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if output_results:
            update_data['output_results'] = output_results
        
        try:
            result = await self._execute_update('background_jobs', job_id, update_data)
            logger.info(f"Job {job_id} marked as {'completed' if success else 'failed'}")
            return result
        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {str(e)}")
            raise
    
    async def get_job_by_key(self, job_key: str) -> Optional[Dict[str, Any]]:
        """Get job by unique key"""
        try:
            return await self._execute_select(
                'background_jobs',
                filters={'job_key': job_key},
                single=True
            )
        except Exception as e:
            logger.error(f"Failed to get job by key {job_key}: {str(e)}")
            return None
    
    async def requeue_job(self, job_id: uuid.UUID, delay_seconds: int = 300) -> Dict[str, Any]:
        """Requeue failed job with delay"""
        
        scheduled_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        
        update_data = {
            'status': JobStatus.RETRY_SCHEDULED.value,
            'scheduled_at': scheduled_at.isoformat(),
            'retry_count': 'retry_count + 1',  # Will be handled in raw SQL
            'worker_id': None,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        try:
            # Use raw SQL for retry_count increment
            query = """
            UPDATE background_jobs 
            SET status = %s,
                scheduled_at = %s,
                retry_count = retry_count + 1,
                worker_id = NULL,
                updated_at = %s
            WHERE id = %s
            RETURNING *;
            """
            
            result = await self._execute_raw_query(query, [
                JobStatus.RETRY_SCHEDULED.value,
                scheduled_at.isoformat(),
                datetime.utcnow().isoformat(),
                str(job_id)
            ])
            
            if result:
                logger.info(f"Requeued job {job_id} for retry")
                return result[0]
            
            raise Exception(f"Job {job_id} not found for requeue")
            
        except Exception as e:
            logger.error(f"Failed to requeue job {job_id}: {str(e)}")
            raise
    
    # ========================================
    # PROGRESS EVENTS MANAGEMENT
    # ========================================
    
    async def create_progress_event(
        self,
        session_id: uuid.UUID,
        event_type: str,
        stage_name: str,
        progress_percentage: int,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Create progress event for real-time updates"""
        
        event_data = {
            'session_id': str(session_id),
            'event_type': event_type,
            'stage_name': stage_name,
            'progress_percentage': progress_percentage,
            'message': message,
            'details': details or {},
            'user_id': str(user_id) if user_id else None
        }
        
        try:
            result = await self._execute_insert('progress_events', event_data)
            
            # Emit real-time update via Supabase Realtime
            from app.services.realtime_service import realtime_service
            await realtime_service.emit_progress_update(session_id, event_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create progress event: {str(e)}")
            raise
    
    async def get_recent_progress_events(
        self,
        session_id: uuid.UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent progress events for a session"""
        try:
            return await self._execute_select(
                'progress_events',
                filters={'session_id': str(session_id)},
                order_by='timestamp',
                order_desc=True,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Failed to get progress events for session {session_id}: {str(e)}")
            return []
    
    # ========================================
    # USER SESSIONS MANAGEMENT
    # ========================================
    
    async def sync_user_session(
        self,
        user_id: uuid.UUID,
        device_fingerprint: str,
        session_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronize user session across devices"""
        
        # Get active processing sessions for user
        active_sessions = await self.get_active_sessions_for_user(user_id)
        active_session_ids = [session['id'] for session in active_sessions]
        
        session_data = {
            'user_id': str(user_id),
            'device_fingerprint': device_fingerprint,
            'session_token': session_token,
            'active_processing_sessions': active_session_ids,
            'last_activity': datetime.utcnow().isoformat(),
            'user_agent': user_agent,
            'ip_address': ip_address,
            'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
        
        try:
            # Upsert user session
            result = await self.client.table('user_sessions')\
                .upsert(session_data, on_conflict='session_token')\
                .execute()
            
            return result.data[0] if result.data else session_data
            
        except Exception as e:
            logger.error(f"Failed to sync user session: {str(e)}")
            raise
    
    # ========================================
    # ERROR TRACKING AND RECOVERY
    # ========================================
    
    async def log_processing_error(
        self,
        session_id: Optional[uuid.UUID],
        job_id: Optional[uuid.UUID],
        error_type: str,
        error_message: str,
        error_code: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        is_recoverable: bool = True
    ) -> Dict[str, Any]:
        """Log processing error with comprehensive context"""
        
        error_data = {
            'session_id': str(session_id) if session_id else None,
            'job_id': str(job_id) if job_id else None,
            'error_type': error_type,
            'error_code': error_code,
            'error_message': error_message,
            'stack_trace': traceback.format_exc(),
            'context_data': context_data or {},
            'is_recoverable': is_recoverable
        }
        
        try:
            result = await self._execute_insert('processing_errors', error_data)
            logger.error(f"Logged processing error {result['id']}: {error_message}")
            return result
        except Exception as e:
            logger.error(f"Failed to log processing error: {str(e)}")
            raise
    
    # ========================================
    # UTILITY AND HELPER METHODS
    # ========================================
    
    async def get_session_progress_summary(self, session_id: uuid.UUID) -> Dict[str, Any]:
        """Get comprehensive session progress summary"""
        try:
            # Use the database function
            query = "SELECT get_session_progress_summary(%s) as summary"
            result = await self._execute_raw_query(query, [str(session_id)])
            
            if result and result[0]['summary']:
                return result[0]['summary']
            
            return {'error': 'Session not found'}
            
        except Exception as e:
            logger.error(f"Failed to get session progress summary: {str(e)}")
            return {'error': str(e)}
    
    async def cleanup_old_data(self):
        """Clean up old progress events and expired sessions"""
        try:
            # Clean up old progress events (30 days)
            progress_query = "SELECT cleanup_old_progress_events()"
            await self._execute_raw_query(progress_query)
            
            # Clean up expired user sessions
            sessions_query = "SELECT cleanup_expired_user_sessions()"
            await self._execute_raw_query(sessions_query)
            
            logger.info("Data cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {str(e)}")
    
    # ========================================
    # INTERNAL HELPER METHODS
    # ========================================
    
    async def _execute_insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute insert operation with error handling"""
        try:
            result = self.client.table(table).insert(data).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Insert failed for table {table}: {str(e)}")
            raise
    
    async def _execute_update(
        self,
        table: str,
        record_id: uuid.UUID,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute update operation with error handling"""
        try:
            result = await self.client.table(table)\
                .update(data)\
                .eq('id', str(record_id))\
                .execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Update failed for table {table}, ID {record_id}: {str(e)}")
            raise
    
    async def _execute_update_with_filters(
        self,
        table: str,
        filters: Dict[str, Any],
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute update with custom filters"""
        try:
            query = self.client.table(table).update(update_data)
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Filtered update failed for table {table}: {str(e)}")
            raise
    
    async def _execute_select(
        self,
        table: str,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        limit: Optional[int] = None,
        single: bool = False
    ) -> Union[Dict[str, Any], List[Dict[str, Any]], None]:
        """Execute select operation with filtering and ordering"""
        try:
            query = self.client.table(table).select('*')
            
            if filters:
                for key, value in filters.items():
                    if isinstance(value, list):
                        query = query.in_(key, value)
                    else:
                        query = query.eq(key, value)
            
            if order_by:
                query = query.order(order_by, desc=order_desc)
            
            if limit:
                query = query.limit(limit)
            
            if single:
                query = query.single()
            
            result = query.execute()
            
            if single:
                return result.data if result.data else None
            else:
                return result.data or []
                
        except Exception as e:
            logger.error(f"Select failed for table {table}: {str(e)}")
            if single:
                return None
            return []
    
    async def _execute_raw_query(self, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query with parameters"""
        try:
            # Note: This is a simplified version. In production, you would use
            # a proper database driver like asyncpg for raw SQL queries
            result = await self.client.rpc('execute_sql', {
                'query': query,
                'params': params or []
            }).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Raw query failed: {str(e)}")
            raise
    
    # ============ AGENT OUTPUT OPERATIONS ============
    
    async def store_agent_extraction(self, extraction_data: Dict[str, Any]) -> str:
        """
        Store extraction result from Agent 1 (Document Analyzer)
        
        Args:
            extraction_data: Dictionary containing extraction details
            
        Returns:
            str: Extraction result ID
        """
        try:
            result = await self._insert_record('agent_extraction_results', {
                'session_id': extraction_data['session_id'],
                'agent_key': extraction_data.get('agent_key', 'agent_1_analyzer'),
                'document_id': extraction_data['document_id'],
                'query_id': extraction_data.get('query_id'),
                'section_id': extraction_data.get('section_id'),
                'raw_extraction': extraction_data['raw_extraction'],
                'normalized_value': extraction_data.get('normalized_value'),
                'confidence_score': extraction_data.get('confidence_score', 0.0),
                'extraction_method': extraction_data.get('extraction_method', 'ai_analysis'),
                'citation': extraction_data.get('citation'),
                'business_rule_applied': extraction_data.get('business_rule_applied'),
                'validation_status': extraction_data.get('validation_status', ValidationStatus.PENDING),
                'metadata': extraction_data.get('metadata', {})
            })
            
            logger.info(f"Stored extraction result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to store agent extraction: {str(e)}")
            raise
    
    async def store_risk_assessment(self, risk_data: Dict[str, Any]) -> str:
        """
        Store risk assessment result from Agent 2 (Risk Assessor)
        
        Args:
            risk_data: Dictionary containing risk assessment details
            
        Returns:
            str: Risk assessment ID
        """
        try:
            result = await self._insert_record('risk_assessment_results', {
                'session_id': risk_data['session_id'],
                'document_id': risk_data['document_id'],
                'risk_category': risk_data['risk_category'],
                'risk_subcategory': risk_data.get('risk_subcategory'),
                'risk_level': risk_data['risk_level'],
                'risk_score': risk_data.get('risk_score'),
                'risk_title': risk_data['risk_title'],
                'risk_description': risk_data['risk_description'],
                'impact_analysis': risk_data.get('impact_analysis'),
                'likelihood_assessment': risk_data.get('likelihood_assessment'),
                'mitigation_recommendations': risk_data.get('mitigation_recommendations'),
                'business_rule_id': risk_data.get('business_rule_id'),
                'compliance_flags': risk_data.get('compliance_flags'),
                'regulatory_references': risk_data.get('regulatory_references'),
                'source_extractions': risk_data.get('source_extractions'),
                'risk_owner': risk_data.get('risk_owner'),
                'due_date': risk_data.get('due_date'),
                'review_status': risk_data.get('review_status', 'pending'),
                'metadata': risk_data.get('metadata', {})
            })
            
            logger.info(f"Stored risk assessment: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to store risk assessment: {str(e)}")
            raise
    
    async def store_generated_report(self, report_data: Dict[str, Any]) -> str:
        """
        Store generated report from Agent 3 (Report Generator)
        
        Args:
            report_data: Dictionary containing report details
            
        Returns:
            str: Generated report ID
        """
        try:
            result = await self._insert_record('generated_reports', {
                'session_id': report_data['session_id'],
                'document_id': report_data['document_id'],
                'report_definition_id': report_data['report_definition_id'],
                'report_type': report_data['report_type'],
                'report_format': report_data['report_format'],
                'report_title': report_data['report_title'],
                'report_content': report_data['report_content'],
                'report_binary': report_data.get('report_binary'),
                'storage_path': report_data.get('storage_path'),
                'file_size': report_data.get('file_size'),
                'generation_method': report_data.get('generation_method', 'ai_generated'),
                'data_sources': report_data.get('data_sources'),
                'report_mappings_used': report_data.get('report_mappings_used'),
                'quality_score': report_data.get('quality_score'),
                'completeness_percentage': report_data.get('completeness_percentage', 100),
                'approval_status': report_data.get('approval_status', 'draft'),
                'metadata': report_data.get('metadata', {})
            })
            
            logger.info(f"Stored generated report: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to store generated report: {str(e)}")
            raise
    
    async def store_workflow_results(self, session_id: str, document_id: str, **kwargs) -> str:
        """
        Store overall workflow results from complete 3-Agent pipeline
        
        Args:
            workflow_data: Dictionary containing workflow summary
            
        Returns:
            str: Workflow results ID
        """
        try:
            result = await self._execute_insert('agent_workflow_results', {
                'session_id': session_id,
                'document_id': document_id,
                'workflow_status': kwargs.get('workflow_status', 'completed'),
                'overall_confidence': kwargs.get('overall_confidence', 0.0),
                'processing_summary': kwargs.get('processing_summary', 'Workflow completed successfully'),
                'key_findings': kwargs.get('key_findings'),
                'compliance_status': kwargs.get('compliance_status', ComplianceStatus.UNKNOWN),
                'recommendations': kwargs.get('recommendations'),
                'risk_summary': kwargs.get('risk_summary'),
                'total_processing_time_ms': kwargs.get('processing_duration_ms', 0),
                'extraction_count': kwargs.get('extraction_count', 0),
                'risk_count': kwargs.get('risk_count', 0),
                'report_count': kwargs.get('report_count', 0),
                'error_count': kwargs.get('error_count', 0),
                'agent_performance_metrics': kwargs.get('agent_performance_metrics', {}),
                'metadata': kwargs.get('metadata', {})
            })
            
            logger.info(f"Stored workflow results: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to store workflow results: {str(e)}")
            raise
    
    async def log_agent_processing(self, log_data: Dict[str, Any]) -> str:
        """
        Store detailed agent processing logs
        
        Args:
            log_data: Dictionary containing log details
            
        Returns:
            str: Log entry ID
        """
        try:
            result = await self._insert_record('agent_processing_logs', {
                'session_id': log_data['session_id'],
                'agent_key': log_data['agent_key'],
                'log_level': log_data.get('log_level', 'info'),
                'log_message': log_data['log_message'],
                'log_data': log_data.get('log_data'),
                'processing_step': log_data.get('processing_step'),
                'execution_context': log_data.get('execution_context'),
                'performance_metrics': log_data.get('performance_metrics')
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to store agent log: {str(e)}")
            raise
    
    # ============ MASTER TABLE OPERATIONS ============
    
    async def get_agent_prompts(self, agent_key: str, document_type_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get agent prompts from master table
        
        Args:
            agent_key: Agent identifier (agent_1_analyzer, agent_2_risk, agent_3_reports)
            document_type_id: Optional document type filter
            
        Returns:
            List[Dict]: Agent prompt configurations
        """
        try:
            conditions = {'agent_key': agent_key, 'status': 'active'}
            if document_type_id:
                conditions['document_type_id'] = document_type_id
            
            result = await self._select_records('agent_prompts', conditions)
            logger.info(f"Retrieved {len(result)} agent prompts for {agent_key}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get agent prompts: {str(e)}")
            return []
    
    async def get_business_rules(self, org_id: str, document_type_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get business rules from master table
        
        Args:
            org_id: Organization ID
            document_type_id: Optional document type filter
            
        Returns:
            List[Dict]: Business rules for the organization
        """
        try:
            conditions = {'org_id': org_id, 'status': 'active'}
            if document_type_id:
                conditions['document_type_id'] = document_type_id
            
            result = await self._select_records('business_rules', conditions, order_by='priority')
            logger.info(f"Retrieved {len(result)} business rules for org {org_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get business rules: {str(e)}")
            return []
    
    async def get_normalization_rules(self, org_id: str, document_type_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get normalization rules from master table
        
        Args:
            org_id: Organization ID
            document_type_id: Optional document type filter
            
        Returns:
            List[Dict]: Normalization rules for the organization
        """
        try:
            conditions = {'org_id': org_id, 'status': 'active'}
            if document_type_id:
                conditions['document_type_id'] = document_type_id
            
            result = await self._select_records('normalization_rules', conditions, order_by='priority')
            logger.info(f"Retrieved {len(result)} normalization rules for org {org_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get normalization rules: {str(e)}")
            return []
    
    async def get_document_sections(self, document_type_id: str) -> List[Dict[str, Any]]:
        """
        Get document sections from master table
        
        Args:
            document_type_id: Document type ID
            
        Returns:
            List[Dict]: Document sections and structure
        """
        try:
            result = await self._select_records('sections', {'document_type_id': document_type_id}, order_by='order_no')
            logger.info(f"Retrieved {len(result)} sections for document type {document_type_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get document sections: {str(e)}")
            return []
    
    async def get_extraction_queries(self, document_type_id: str) -> List[Dict[str, Any]]:
        """
        Get extraction queries from master table
        
        Args:
            document_type_id: Document type ID
            
        Returns:
            List[Dict]: Queries for data extraction
        """
        try:
            result = await self._select_records('queries', {'document_type_id': document_type_id, 'status': 'active'})
            logger.info(f"Retrieved {len(result)} queries for document type {document_type_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get extraction queries: {str(e)}")
            return []
    
    async def get_report_definitions(self, org_id: str) -> List[Dict[str, Any]]:
        """
        Get report definitions from master table
        
        Args:
            org_id: Organization ID
            
        Returns:
            List[Dict]: Available report templates
        """
        try:
            conditions = {'org_id': org_id, 'status': 'active'}
            result = await self._select_records('report_definitions', conditions)
            logger.info(f"Retrieved {len(result)} report definitions for org {org_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get report definitions: {str(e)}")
            return []
    
    # ============ RESULT RETRIEVAL OPERATIONS ============
    
    async def get_session_extractions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all extractions for a session"""
        try:
            result = await self._select_records('agent_extraction_results', {'session_id': session_id}, order_by='created_at')
            logger.info(f"Retrieved {len(result)} extractions for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get session extractions: {str(e)}")
            return []
    
    async def get_session_risk_assessments(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all risk assessments for a session"""
        try:
            result = await self._select_records('risk_assessment_results', {'session_id': session_id}, order_by='risk_score DESC')
            logger.info(f"Retrieved {len(result)} risk assessments for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get session risk assessments: {str(e)}")
            return []
    
    async def get_session_reports(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all generated reports for a session"""
        try:
            result = await self._select_records('generated_reports', {'session_id': session_id}, order_by='generated_at DESC')
            logger.info(f"Retrieved {len(result)} reports for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get session reports: {str(e)}")
            return []
    
    async def get_session_workflow_results(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow results summary for a session"""
        try:
            result = await self._select_records('agent_workflow_results', {'session_id': session_id}, single=True)
            logger.info(f"Retrieved workflow results for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get session workflow results: {str(e)}")
            return None
    
    # ============ WORKFLOW STAGE OPERATIONS ============
    
    async def create_workflow_stage(self, session_id: str, stage_name: str, stage_order: int, status: str = 'pending', **kwargs) -> str:
        """Create workflow stage completion record"""
        try:
            result = await self._execute_insert('workflow_stage_completions', {
                'session_id': session_id,
                'stage_name': stage_name,
                'stage_order': stage_order,
                'status': status,
                'input_data': kwargs.get('input_data'),
                'dependencies_met': kwargs.get('dependencies_met', True),
                'metadata': kwargs.get('metadata', {})
            })
            logger.info(f"Created workflow stage: {stage_name} for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to create workflow stage: {str(e)}")
            raise
    
    async def update_workflow_stage(self, session_id: str, stage_name: str, status: str = None, **kwargs) -> bool:
        """Update workflow stage completion"""
        try:
            updates = {}
            if status:
                updates['status'] = status
            updates.update(kwargs)
            
            result = await self._execute_update_with_filters(
                'workflow_stage_completions',
                {'session_id': session_id, 'stage_name': stage_name},
                updates
            )
            logger.info(f"Updated workflow stage {stage_name} for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update workflow stage: {str(e)}")
            return False
    
    async def store_section_instance(self, section_data: Dict[str, Any]) -> str:
        """Store identified document section"""
        try:
            result = await self._insert_record('document_section_instances', {
                'session_id': section_data['session_id'],
                'document_id': section_data['document_id'],
                'section_id': section_data['section_id'],
                'section_text': section_data['section_text'],
                'confidence_score': section_data.get('confidence_score', 0.0),
                'start_position': section_data.get('start_position'),
                'end_position': section_data.get('end_position'),
                'page_number': section_data.get('page_number'),
                'identification_method': section_data.get('identification_method', 'pattern_matching'),
                'anchor_patterns_matched': section_data.get('anchor_patterns_matched', []),
                'metadata': section_data.get('metadata', {})
            })
            logger.info(f"Stored section instance: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to store section instance: {str(e)}")
            raise
    
    async def store_query_execution(self, query_data: Dict[str, Any]) -> str:
        """Store query execution result"""
        try:
            result = await self._insert_record('query_execution_results', {
                'session_id': query_data['session_id'],
                'document_id': query_data['document_id'],
                'query_id': query_data['query_id'],
                'section_instance_id': query_data['section_instance_id'],
                'raw_result': query_data.get('raw_result'),
                'extraction_confidence': query_data.get('extraction_confidence', 0.0),
                'extraction_method': query_data.get('extraction_method', 'ai_analysis'),
                'citation': query_data.get('citation'),
                'execution_duration_ms': query_data.get('execution_duration_ms'),
                'execution_status': query_data.get('execution_status', 'completed'),
                'metadata': query_data.get('metadata', {})
            })
            logger.info(f"Stored query execution: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to store query execution: {str(e)}")
            raise
    
    async def store_normalization_application(self, norm_data: Dict[str, Any]) -> str:
        """Store normalization rule application"""
        try:
            result = await self._insert_record('normalization_applications', {
                'session_id': norm_data['session_id'],
                'query_execution_id': norm_data['query_execution_id'],
                'normalization_rule_id': norm_data['normalization_rule_id'],
                'input_value': norm_data['input_value'],
                'output_value': norm_data['output_value'],
                'confidence_score': norm_data.get('confidence_score', 0.0),
                'rule_match_score': norm_data.get('rule_match_score', 0.0),
                'applied_by': norm_data.get('applied_by', 'system'),
                'metadata': norm_data.get('metadata', {})
            })
            logger.info(f"Stored normalization application: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to store normalization application: {str(e)}")
            raise
    
    async def store_business_rule_evaluation(self, eval_data: Dict[str, Any]) -> str:
        """Store business rule evaluation result"""
        try:
            result = await self._insert_record('business_rule_evaluations', {
                'session_id': eval_data['session_id'],
                'business_rule_id': eval_data['business_rule_id'],
                'evaluation_context': eval_data['evaluation_context'],
                'evaluation_result': eval_data['evaluation_result'],
                'rule_output': eval_data.get('rule_output'),
                'confidence_score': eval_data.get('confidence_score', 0.0),
                'evaluation_method': eval_data.get('evaluation_method', 'automated'),
                'affected_extractions': eval_data.get('affected_extractions', []),
                'violation_severity': eval_data.get('violation_severity'),
                'violation_message': eval_data.get('violation_message'),
                'recommended_action': eval_data.get('recommended_action'),
                'metadata': eval_data.get('metadata', {})
            })
            logger.info(f"Stored business rule evaluation: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to store business rule evaluation: {str(e)}")
            raise
    
    async def store_agent_prompt_application(self, prompt_data: Dict[str, Any]) -> str:
        """Store agent prompt application result"""
        try:
            result = await self._insert_record('agent_prompt_applications', {
                'session_id': prompt_data['session_id'],
                'agent_prompt_id': prompt_data['agent_prompt_id'],
                'application_stage': prompt_data['application_stage'],
                'input_data': prompt_data['input_data'],
                'prompt_response': prompt_data.get('prompt_response'),
                'response_structured': prompt_data.get('response_structured'),
                'confidence_score': prompt_data.get('confidence_score', 0.0),
                'processing_duration_ms': prompt_data.get('processing_duration_ms'),
                'token_usage': prompt_data.get('token_usage'),
                'model_used': prompt_data.get('model_used'),
                'prompt_version': prompt_data.get('prompt_version'),
                'application_context': prompt_data.get('application_context'),
                'quality_score': prompt_data.get('quality_score'),
                'human_review_required': prompt_data.get('human_review_required', False),
                'metadata': prompt_data.get('metadata', {})
            })
            logger.info(f"Stored agent prompt application: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to store agent prompt application: {str(e)}")
            raise
    
    # ============ WORKFLOW RETRIEVAL OPERATIONS ============
    
    async def get_session_sections(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all identified sections for a session"""
        try:
            result = await self._select_records('document_section_instances', {'session_id': session_id}, order_by='page_number')
            logger.info(f"Retrieved {len(result)} sections for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get session sections: {str(e)}")
            return []
    
    async def get_session_query_results(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all query execution results for a session"""
        try:
            result = await self._select_records('query_execution_results', {'session_id': session_id}, order_by='created_at')
            logger.info(f"Retrieved {len(result)} query results for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get session query results: {str(e)}")
            return []
    
    async def get_session_business_rule_evaluations(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all business rule evaluations for a session"""
        try:
            result = await self._select_records('business_rule_evaluations', {'session_id': session_id}, order_by='evaluated_at')
            logger.info(f"Retrieved {len(result)} business rule evaluations for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get session business rule evaluations: {str(e)}")
            return []
    
    async def get_session_workflow_stages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all workflow stages for a session"""
        try:
            result = await self._select_records('workflow_stage_completions', {'session_id': session_id}, order_by='stage_order')
            logger.info(f"Retrieved {len(result)} workflow stages for session {session_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to get session workflow stages: {str(e)}")
            return []

# Global service instance
database_service = DatabaseService()