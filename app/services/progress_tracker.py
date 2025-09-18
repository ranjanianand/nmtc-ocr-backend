"""
NMTC Real-Time Progress Tracking Service

Enterprise-grade progress tracking system with session management and real-time updates.
Supports cross-device synchronization via Supabase real-time subscriptions.

Author: CORE ENGINE PROCESSING AGENT
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

from app.services.supabase_service import supabase_service
from app.config import settings

logger = logging.getLogger(__name__)

class ProgressEventType(str, Enum):
    """Types of progress events for real-time tracking"""
    STAGE_STARTED = "stage_started"
    STAGE_PROGRESS = "stage_progress"
    STAGE_COMPLETED = "stage_completed"
    ERROR_OCCURRED = "error_occurred"
    USER_ACTION_REQUIRED = "user_action_required"
    PROCESSING_COMPLETE = "processing_complete"
    HEARTBEAT = "heartbeat"

class ProgressNotification:
    """Real-time progress notification"""
    
    def __init__(
        self, 
        document_id: str, 
        event_type: ProgressEventType,
        stage: str,
        progress_percentage: int,
        message: str,
        details: Dict[str, Any] = None,
        user_id: str = None
    ):
        self.document_id = document_id
        self.event_type = event_type
        self.stage = stage
        self.progress_percentage = progress_percentage
        self.message = message
        self.details = details or {}
        self.user_id = user_id
        self.timestamp = datetime.utcnow()
        self.notification_id = f"{document_id}_{int(self.timestamp.timestamp())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary for transmission"""
        return {
            'notification_id': self.notification_id,
            'document_id': self.document_id,
            'event_type': self.event_type.value,
            'stage': self.stage,
            'progress_percentage': self.progress_percentage,
            'message': self.message,
            'details': self.details,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat()
        }

class SessionManager:
    """Manages processing sessions with cross-device sync"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_subscribers: Dict[str, List[Callable]] = {}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self.heartbeat_interval = 30  # seconds
        self.session_timeout = 1800  # 30 minutes
    
    async def create_session(
        self, 
        document_id: str, 
        user_id: str = None,
        initial_stage: str = "uploaded"
    ) -> str:
        """Create a new processing session"""
        session_id = f"session_{document_id}_{int(datetime.utcnow().timestamp())}"
        
        session_data = {
            'session_id': session_id,
            'document_id': document_id,
            'user_id': user_id,
            'created_at': datetime.utcnow(),
            'last_activity': datetime.utcnow(),
            'current_stage': initial_stage,
            'progress_percentage': 0,
            'is_active': True,
            'events': [],
            'heartbeat_count': 0
        }
        
        self.active_sessions[session_id] = session_data
        
        # Store session in database for persistence
        await self._persist_session(session_id, session_data)
        
        # Start heartbeat monitoring
        self.heartbeat_tasks[session_id] = asyncio.create_task(
            self._heartbeat_monitor(session_id)
        )
        
        logger.info(f"Created processing session - ID: {session_id}, Document: {document_id}")
        return session_id
    
    async def update_session_progress(
        self,
        session_id: str,
        stage: str,
        progress_percentage: int,
        message: str,
        details: Dict[str, Any] = None,
        event_type: ProgressEventType = ProgressEventType.STAGE_PROGRESS
    ):
        """Update session progress and send real-time notification"""
        if session_id not in self.active_sessions:
            logger.warning(f"Session not found: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        session['current_stage'] = stage
        session['progress_percentage'] = progress_percentage
        session['last_activity'] = datetime.utcnow()
        
        # Create progress notification
        notification = ProgressNotification(
            document_id=session['document_id'],
            event_type=event_type,
            stage=stage,
            progress_percentage=progress_percentage,
            message=message,
            details=details,
            user_id=session['user_id']
        )
        
        # Add to session events
        session['events'].append(notification.to_dict())
        
        # Keep only last 50 events to prevent memory bloat
        if len(session['events']) > 50:
            session['events'] = session['events'][-50:]
        
        # Persist updated session
        await self._persist_session(session_id, session)
        
        # Send real-time notification
        await self._send_realtime_notification(notification)
        
        logger.info(f"Session progress updated - ID: {session_id}, Stage: {stage}, Progress: {progress_percentage}%")
    
    async def end_session(self, session_id: str, final_stage: str = "completed"):
        """End a processing session"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        session['is_active'] = False
        session['ended_at'] = datetime.utcnow()
        session['final_stage'] = final_stage
        
        # Persist final session state
        await self._persist_session(session_id, session)
        
        # Cancel heartbeat task
        if session_id in self.heartbeat_tasks:
            self.heartbeat_tasks[session_id].cancel()
            del self.heartbeat_tasks[session_id]
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        logger.info(f"Session ended - ID: {session_id}, Final stage: {final_stage}")
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session status"""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id].copy()
        
        # Try to load from database
        return await self._load_session_from_db(session_id)
    
    async def get_document_sessions(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a document"""
        document = await supabase_service.get_document(document_id)
        if not document:
            return []
        
        parsed_index = document.get('parsed_index', {})
        sessions = parsed_index.get('processing_sessions', {})
        
        return list(sessions.values())
    
    async def _heartbeat_monitor(self, session_id: str):
        """Monitor session heartbeat"""
        try:
            while session_id in self.active_sessions:
                await asyncio.sleep(self.heartbeat_interval)
                
                if session_id not in self.active_sessions:
                    break
                
                session = self.active_sessions[session_id]
                session['heartbeat_count'] += 1
                session['last_heartbeat'] = datetime.utcnow()
                
                # Check for timeout
                if (datetime.utcnow() - session['last_activity']).seconds > self.session_timeout:
                    logger.warning(f"Session timeout - ID: {session_id}")
                    await self.end_session(session_id, "timeout")
                    break
                
                # Send heartbeat notification
                notification = ProgressNotification(
                    document_id=session['document_id'],
                    event_type=ProgressEventType.HEARTBEAT,
                    stage=session['current_stage'],
                    progress_percentage=session['progress_percentage'],
                    message=f"Processing active - Heartbeat #{session['heartbeat_count']}",
                    details={'heartbeat_count': session['heartbeat_count']},
                    user_id=session['user_id']
                )
                
                await self._send_realtime_notification(notification)
                
        except asyncio.CancelledError:
            logger.info(f"Heartbeat monitor cancelled for session: {session_id}")
        except Exception as e:
            logger.error(f"Heartbeat monitor error for session {session_id}: {str(e)}")
    
    async def _persist_session(self, session_id: str, session_data: Dict[str, Any]):
        """Persist session data to database"""
        try:
            document_id = session_data['document_id']
            
            # Convert datetime objects to ISO strings for JSON storage
            session_copy = session_data.copy()
            for key, value in session_copy.items():
                if isinstance(value, datetime):
                    session_copy[key] = value.isoformat()
            
            # Update document with session data
            document = await supabase_service.get_document(document_id)
            parsed_index = document.get('parsed_index', {})
            
            if 'processing_sessions' not in parsed_index:
                parsed_index['processing_sessions'] = {}
            
            parsed_index['processing_sessions'][session_id] = session_copy
            
            await supabase_service.update_document_status(
                document_id=document_id,
                status=session_data['current_stage'],
                updates={'parsed_index': parsed_index}
            )
            
        except Exception as e:
            logger.error(f"Failed to persist session {session_id}: {str(e)}")
    
    async def _load_session_from_db(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from database"""
        try:
            # This would require a more efficient query in a real implementation
            # For now, we'll check the most recent documents
            result = supabase_service.client.table('documents').select('*').limit(100).execute()
            
            for document in result.data:
                parsed_index = document.get('parsed_index', {})
                sessions = parsed_index.get('processing_sessions', {})
                
                if session_id in sessions:
                    return sessions[session_id]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load session from DB {session_id}: {str(e)}")
            return None
    
    async def _send_realtime_notification(self, notification: ProgressNotification):
        """Send real-time notification via Supabase real-time"""
        try:
            # Send to Supabase real-time channel
            channel_name = f"document_processing_{notification.document_id}"
            
            # Store notification in database for real-time subscriptions
            notification_data = {
                'channel': channel_name,
                'event_type': 'progress_update',
                'payload': notification.to_dict(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Insert into notifications table (this would be picked up by real-time subscriptions)
            try:
                supabase_service.client.table('processing_notifications').insert(notification_data).execute()
            except:
                # If notifications table doesn't exist, we can still function
                logger.warning("Processing notifications table not available")
            
            # Also update the document's current progress for immediate access
            document = await supabase_service.get_document(notification.document_id)
            parsed_index = document.get('parsed_index', {})
            
            parsed_index['current_progress'] = {
                'stage': notification.stage,
                'progress_percentage': notification.progress_percentage,
                'message': notification.message,
                'last_update': notification.timestamp.isoformat(),
                'event_type': notification.event_type.value
            }
            
            await supabase_service.update_document_status(
                document_id=notification.document_id,
                status=notification.stage,
                updates={'parsed_index': parsed_index}
            )
            
        except Exception as e:
            logger.error(f"Failed to send real-time notification: {str(e)}")

class ProgressTracker:
    """Main progress tracking service"""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.progress_callbacks: Dict[str, List[Callable]] = {}
    
    async def start_tracking(
        self, 
        document_id: str, 
        user_id: str = None,
        initial_stage: str = "uploaded"
    ) -> str:
        """Start progress tracking for a document"""
        session_id = await self.session_manager.create_session(
            document_id, user_id, initial_stage
        )
        
        logger.info(f"Started progress tracking - Document: {document_id}, Session: {session_id}")
        return session_id
    
    async def update_progress(
        self,
        session_id: str,
        stage: str,
        progress_percentage: int,
        message: str,
        details: Dict[str, Any] = None,
        event_type: ProgressEventType = ProgressEventType.STAGE_PROGRESS
    ):
        """Update processing progress"""
        await self.session_manager.update_session_progress(
            session_id, stage, progress_percentage, message, details, event_type
        )
    
    async def complete_tracking(self, session_id: str):
        """Complete progress tracking"""
        await self.session_manager.end_session(session_id, "completed")
        logger.info(f"Completed progress tracking - Session: {session_id}")
    
    async def error_tracking(self, session_id: str, error_message: str, error_details: Dict[str, Any] = None):
        """Handle error in progress tracking"""
        await self.session_manager.update_session_progress(
            session_id=session_id,
            stage="error",
            progress_percentage=0,
            message=f"Processing error: {error_message}",
            details=error_details or {},
            event_type=ProgressEventType.ERROR_OCCURRED
        )
        
        await self.session_manager.end_session(session_id, "error")
        logger.error(f"Error in progress tracking - Session: {session_id}, Error: {error_message}")
    
    async def get_status(self, document_id: str) -> Dict[str, Any]:
        """Get current progress status for a document"""
        sessions = await self.session_manager.get_document_sessions(document_id)
        
        if not sessions:
            return {
                'document_id': document_id,
                'status': 'no_sessions',
                'message': 'No processing sessions found'
            }
        
        # Get the most recent session
        active_session = None
        latest_session = None
        
        for session in sessions:
            if session.get('is_active'):
                active_session = session
                break
            
            if not latest_session or session.get('created_at', '') > latest_session.get('created_at', ''):
                latest_session = session
        
        current_session = active_session or latest_session
        
        return {
            'document_id': document_id,
            'session_id': current_session.get('session_id'),
            'current_stage': current_session.get('current_stage'),
            'progress_percentage': current_session.get('progress_percentage', 0),
            'is_active': current_session.get('is_active', False),
            'last_activity': current_session.get('last_activity'),
            'message': self._get_stage_message(current_session.get('current_stage', 'unknown')),
            'recent_events': current_session.get('events', [])[-5:],  # Last 5 events
            'total_sessions': len(sessions)
        }
    
    def _get_stage_message(self, stage: str) -> str:
        """Get user-friendly message for processing stage"""
        stage_messages = {
            'uploaded': 'Document uploaded successfully',
            'stage_0a_starting': 'Starting initial processing',
            'stage_0a_ocr': 'Extracting text from document',
            'stage_0a_detection': 'Detecting document type',
            'stage_0a_complete': 'Initial processing complete',
            'awaiting_user_confirmation': 'Awaiting user confirmation',
            'core_pipeline_starting': 'Starting comprehensive analysis',
            'agent_1_document_analysis': 'Analyzing document structure',
            'agent_2_risk_assessment': 'Performing risk assessment',
            'agent_3_report_generation': 'Generating reports',
            'processing_complete': 'Processing completed successfully',
            'error': 'Processing encountered an error',
            'timeout': 'Processing timed out'
        }
        
        return stage_messages.get(stage, f'Processing stage: {stage}')

# Global progress tracker instance
progress_tracker = ProgressTracker()