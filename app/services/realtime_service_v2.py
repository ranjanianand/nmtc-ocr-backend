"""
NMTC Enterprise Real-Time Service v2 - Database Integration

Enhanced real-time communication service that integrates with the enterprise database
architecture for processing sessions, agent states, and progress events.

Author: Core Engine Processing Agent + UX Design System Agent
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

from app.services.supabase_service import supabase_service
from app.services.database_service import database_service
from app.config import settings

logger = logging.getLogger(__name__)

class RealtimeChannelType(str, Enum):
    """Types of real-time channels for enterprise features"""
    PROCESSING_SESSION = "processing_session"
    AGENT_PIPELINE = "agent_pipeline"
    USER_DASHBOARD = "user_dashboard"
    ORGANIZATION_WIDE = "organization_wide"
    ERROR_ALERTS = "error_alerts"
    SYSTEM_STATUS = "system_status"

class RealtimeEventType(str, Enum):
    """Real-time event types aligned with database events"""
    SESSION_STARTED = "session_started"
    SESSION_PROGRESS = "session_progress"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"
    AGENT_STARTED = "agent_started"
    AGENT_PROGRESS = "agent_progress"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    USER_CONFIRMATION_REQUIRED = "user_confirmation_required"
    ERROR_OCCURRED = "error_occurred"
    HEARTBEAT = "heartbeat"
    CROSS_DEVICE_SYNC = "cross_device_sync"

class EnterpriseRealtimeService:
    """Enterprise real-time service with database integration"""
    
    def __init__(self):
        self.client = supabase_service.client
        self.active_channels: Dict[str, Any] = {}
        self.user_subscriptions: Dict[str, List[str]] = {}  # user_id -> [channel_ids]
        self.session_channels: Dict[str, str] = {}  # session_id -> channel_id
        self.is_running = False
        
    async def start(self):
        """Initialize enterprise real-time service"""
        try:
            self.is_running = True
            logger.info("🚀 Enterprise Real-time Service v2 started")
            
            # Setup system-wide channels
            await self._setup_system_channels()
            
            # Start background tasks
            asyncio.create_task(self._background_heartbeat())
            asyncio.create_task(self._cleanup_expired_channels())
            
            logger.info("✅ Enterprise real-time service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start enterprise real-time service: {str(e)}")
            raise
    
    async def stop(self):
        """Gracefully stop the real-time service"""
        try:
            self.is_running = False
            
            # Close all active channels
            for channel_id in list(self.active_channels.keys()):
                await self._close_channel(channel_id)
            
            logger.info("✅ Enterprise real-time service stopped cleanly")
            
        except Exception as e:
            logger.error(f"❌ Error stopping real-time service: {str(e)}")
    
    # ========================================
    # SESSION-BASED REAL-TIME TRACKING
    # ========================================
    
    async def create_processing_session_channel(
        self,
        session_id: str,
        document_id: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None
    ) -> str:
        """Create real-time channel for processing session"""
        
        channel_id = f"session_{session_id}"
        
        try:
            # Create channel configuration
            channel_config = {
                'channel_id': channel_id,
                'channel_type': RealtimeChannelType.PROCESSING_SESSION.value,
                'session_id': session_id,
                'document_id': document_id,
                'user_id': user_id,
                'org_id': org_id,
                'created_at': datetime.utcnow().isoformat(),
                'subscribers': [],
                'last_activity': datetime.utcnow().isoformat()
            }
            
            # Store channel
            self.active_channels[channel_id] = channel_config
            self.session_channels[session_id] = channel_id
            
            # Auto-subscribe user if provided
            if user_id:
                await self.subscribe_user_to_session(user_id, session_id)
            
            logger.info(f"Created processing session channel: {channel_id}")
            return channel_id
            
        except Exception as e:
            logger.error(f"Failed to create session channel: {str(e)}")
            raise
    
    async def emit_session_progress(
        self,
        session_id: str,
        event_type: RealtimeEventType,
        progress_data: Dict[str, Any]
    ):
        """Emit session progress update to all subscribers"""
        
        channel_id = self.session_channels.get(session_id)
        if not channel_id:
            logger.warning(f"No channel found for session {session_id}")
            return
        
        try:
            # Get session data from database
            session_data = await database_service.get_processing_session(uuid.UUID(session_id))
            if not session_data:
                logger.warning(f"Session {session_id} not found in database")
                return
            
            # Get agent states
            agent_states = await database_service.get_agent_states_for_session(uuid.UUID(session_id))
            
            # Get recent progress events
            recent_events = await database_service.get_recent_progress_events(
                uuid.UUID(session_id), limit=5
            )
            
            # Prepare comprehensive progress payload
            payload = {
                'session_id': session_id,
                'event_type': event_type.value,
                'timestamp': datetime.utcnow().isoformat(),
                'session_data': {
                    'status': session_data['status'],
                    'current_stage': session_data['current_stage'],
                    'progress_percentage': session_data['progress_percentage'],
                    'created_at': session_data['created_at'],
                    'last_heartbeat': session_data['last_heartbeat'],
                    'error_count': session_data['error_count']
                },
                'agent_states': [
                    {
                        'agent_key': agent['agent_key'],
                        'status': agent['status'],
                        'progress_percentage': agent['progress_percentage'],
                        'stage_order': agent['stage_order'],
                        'confidence_score': agent.get('confidence_score'),
                        'started_at': agent.get('started_at'),
                        'completed_at': agent.get('completed_at')
                    }
                    for agent in agent_states
                ],
                'recent_events': [
                    {
                        'event_type': event['event_type'],
                        'stage_name': event['stage_name'],
                        'progress_percentage': event['progress_percentage'],
                        'message': event['message'],
                        'timestamp': event['timestamp']
                    }
                    for event in recent_events
                ],
                'progress_data': progress_data,
                'api_version': 'v3-enterprise'
            }
            
            # Emit to Supabase real-time
            await self._emit_to_channel(channel_id, payload)
            
            # Update channel activity
            if channel_id in self.active_channels:
                self.active_channels[channel_id]['last_activity'] = datetime.utcnow().isoformat()
            
            logger.info(f"Emitted session progress for {session_id}: {event_type.value}")
            
        except Exception as e:
            logger.error(f"Failed to emit session progress: {str(e)}")
    
    async def emit_agent_progress(
        self,
        session_id: str,
        agent_key: str,
        agent_status: str,
        progress_percentage: int,
        additional_data: Dict[str, Any] = None
    ):
        """Emit agent-specific progress update"""
        
        try:
            progress_data = {
                'agent_key': agent_key,
                'agent_status': agent_status,
                'progress_percentage': progress_percentage,
                'timestamp': datetime.utcnow().isoformat(),
                'additional_data': additional_data or {}
            }
            
            # Determine event type based on agent status
            if agent_status == 'running':
                event_type = RealtimeEventType.AGENT_STARTED if progress_percentage == 0 else RealtimeEventType.AGENT_PROGRESS
            elif agent_status == 'completed':
                event_type = RealtimeEventType.AGENT_COMPLETED
            elif agent_status == 'failed':
                event_type = RealtimeEventType.AGENT_FAILED
            else:
                event_type = RealtimeEventType.AGENT_PROGRESS
            
            await self.emit_session_progress(session_id, event_type, progress_data)
            
        except Exception as e:
            logger.error(f"Failed to emit agent progress: {str(e)}")
    
    # ========================================
    # USER SUBSCRIPTION MANAGEMENT
    # ========================================
    
    async def subscribe_user_to_session(self, user_id: str, session_id: str):
        """Subscribe user to session updates"""
        
        channel_id = self.session_channels.get(session_id)
        if not channel_id:
            logger.warning(f"No channel found for session {session_id}")
            return
        
        try:
            # Add user to channel subscribers
            if channel_id in self.active_channels:
                if user_id not in self.active_channels[channel_id]['subscribers']:
                    self.active_channels[channel_id]['subscribers'].append(user_id)
            
            # Track user subscriptions
            if user_id not in self.user_subscriptions:
                self.user_subscriptions[user_id] = []
            
            if channel_id not in self.user_subscriptions[user_id]:
                self.user_subscriptions[user_id].append(channel_id)
            
            # Update user session in database for cross-device sync
            await database_service.sync_user_session(
                user_id=uuid.UUID(user_id),
                device_fingerprint=f"realtime_{datetime.utcnow().timestamp()}",
                session_token=f"rt_{session_id}_{user_id}",
                user_agent="Real-time Subscription"
            )
            
            logger.info(f"User {user_id} subscribed to session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe user to session: {str(e)}")
    
    async def unsubscribe_user_from_session(self, user_id: str, session_id: str):
        """Unsubscribe user from session updates"""
        
        channel_id = self.session_channels.get(session_id)
        if not channel_id:
            return
        
        try:
            # Remove user from channel subscribers
            if channel_id in self.active_channels:
                if user_id in self.active_channels[channel_id]['subscribers']:
                    self.active_channels[channel_id]['subscribers'].remove(user_id)
            
            # Update user subscriptions
            if user_id in self.user_subscriptions:
                if channel_id in self.user_subscriptions[user_id]:
                    self.user_subscriptions[user_id].remove(channel_id)
            
            logger.info(f"User {user_id} unsubscribed from session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe user: {str(e)}")
    
    async def get_user_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active sessions for user with real-time status"""
        
        try:
            # Get active sessions from database
            active_sessions = await database_service.get_active_sessions_for_user(
                user_id=uuid.UUID(user_id)
            )
            
            # Enhance with real-time information
            enhanced_sessions = []
            for session in active_sessions:
                session_id = session['id']
                channel_id = self.session_channels.get(session_id)
                
                enhanced_session = {
                    **session,
                    'real_time_tracking': {
                        'has_channel': bool(channel_id),
                        'channel_id': channel_id,
                        'is_subscribed': user_id in self.user_subscriptions.get(user_id, []),
                        'subscriber_count': len(self.active_channels.get(channel_id, {}).get('subscribers', []))
                    }
                }
                enhanced_sessions.append(enhanced_session)
            
            return enhanced_sessions
            
        except Exception as e:
            logger.error(f"Failed to get user active sessions: {str(e)}")
            return []
    
    # ========================================
    # CROSS-DEVICE SYNCHRONIZATION
    # ========================================
    
    async def sync_user_across_devices(self, user_id: str):
        """Synchronize user state across all devices"""
        
        try:
            # Get user's active sessions
            active_sessions = await self.get_user_active_sessions(user_id)
            
            # Prepare cross-device sync payload
            sync_payload = {
                'user_id': user_id,
                'event_type': RealtimeEventType.CROSS_DEVICE_SYNC.value,
                'timestamp': datetime.utcnow().isoformat(),
                'active_sessions': active_sessions,
                'sync_data': {
                    'total_active_sessions': len(active_sessions),
                    'subscribed_channels': len(self.user_subscriptions.get(user_id, [])),
                    'last_sync': datetime.utcnow().isoformat()
                }
            }
            
            # Emit to user-specific channel
            user_channel_id = f"user_{user_id}"
            await self._emit_to_channel(user_channel_id, sync_payload)
            
            logger.info(f"Cross-device sync completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to sync user across devices: {str(e)}")
    
    # ========================================
    # ERROR AND ALERT MANAGEMENT
    # ========================================
    
    async def emit_error_alert(
        self,
        session_id: Optional[str],
        error_type: str,
        error_message: str,
        user_id: Optional[str] = None,
        severity: str = 'medium'
    ):
        """Emit error alert to relevant subscribers"""
        
        try:
            error_payload = {
                'event_type': RealtimeEventType.ERROR_OCCURRED.value,
                'session_id': session_id,
                'error_type': error_type,
                'error_message': error_message,
                'severity': severity,
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': user_id,
                'requires_action': severity in ['high', 'critical']
            }
            
            # Emit to session channel if available
            if session_id and session_id in self.session_channels:
                channel_id = self.session_channels[session_id]
                await self._emit_to_channel(channel_id, error_payload)
            
            # Emit to user channel if available
            if user_id:
                user_channel_id = f"user_{user_id}"
                await self._emit_to_channel(user_channel_id, error_payload)
            
            logger.warning(f"Error alert emitted - Type: {error_type}, Severity: {severity}")
            
        except Exception as e:
            logger.error(f"Failed to emit error alert: {str(e)}")
    
    async def emit_user_action_required(
        self,
        session_id: str,
        action_type: str,
        action_data: Dict[str, Any],
        user_id: str
    ):
        """Emit user action required notification"""
        
        try:
            action_payload = {
                'event_type': RealtimeEventType.USER_CONFIRMATION_REQUIRED.value,
                'session_id': session_id,
                'action_type': action_type,
                'action_data': action_data,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }
            
            # Emit to session and user channels
            await self.emit_session_progress(
                session_id, 
                RealtimeEventType.USER_CONFIRMATION_REQUIRED, 
                action_payload
            )
            
            logger.info(f"User action required notification sent for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to emit user action required: {str(e)}")
    
    # ========================================
    # INTERNAL HELPER METHODS
    # ========================================
    
    async def _emit_to_channel(self, channel_id: str, payload: Dict[str, Any]):
        """Emit payload to Supabase real-time channel"""
        
        try:
            # Use Supabase real-time to broadcast
            # Note: This is a simplified implementation
            # In production, you would use the actual Supabase real-time client
            
            channel_info = self.active_channels.get(channel_id, {})
            subscribers = channel_info.get('subscribers', [])
            
            logger.debug(f"Emitting to channel {channel_id} with {len(subscribers)} subscribers")
            
            # In actual implementation, this would use supabase.realtime
            # For now, we log the emission
            logger.info(f"Real-time emit: {channel_id} -> {payload.get('event_type', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to emit to channel {channel_id}: {str(e)}")
    
    async def _setup_system_channels(self):
        """Setup system-wide channels"""
        
        try:
            # Create system status channel
            system_channel_id = "system_status"
            self.active_channels[system_channel_id] = {
                'channel_id': system_channel_id,
                'channel_type': RealtimeChannelType.SYSTEM_STATUS.value,
                'created_at': datetime.utcnow().isoformat(),
                'subscribers': [],
                'last_activity': datetime.utcnow().isoformat()
            }
            
            logger.info("System channels setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup system channels: {str(e)}")
    
    async def _background_heartbeat(self):
        """Background task for heartbeat monitoring"""
        
        while self.is_running:
            try:
                await asyncio.sleep(30)  # 30 second heartbeat
                
                # Emit heartbeat to active channels
                heartbeat_payload = {
                    'event_type': RealtimeEventType.HEARTBEAT.value,
                    'timestamp': datetime.utcnow().isoformat(),
                    'active_channels': len(self.active_channels),
                    'total_subscribers': sum(
                        len(channel.get('subscribers', [])) 
                        for channel in self.active_channels.values()
                    )
                }
                
                # Emit to system channel
                if "system_status" in self.active_channels:
                    await self._emit_to_channel("system_status", heartbeat_payload)
                
            except Exception as e:
                logger.error(f"Heartbeat failed: {str(e)}")
    
    async def _cleanup_expired_channels(self):
        """Background task to cleanup expired channels"""
        
        while self.is_running:
            try:
                await asyncio.sleep(300)  # 5 minute cleanup interval
                
                current_time = datetime.utcnow()
                expired_channels = []
                
                for channel_id, channel_data in self.active_channels.items():
                    last_activity = datetime.fromisoformat(channel_data['last_activity'])
                    if (current_time - last_activity).total_seconds() > 3600:  # 1 hour timeout
                        expired_channels.append(channel_id)
                
                # Remove expired channels
                for channel_id in expired_channels:
                    await self._close_channel(channel_id)
                
                if expired_channels:
                    logger.info(f"Cleaned up {len(expired_channels)} expired channels")
                
            except Exception as e:
                logger.error(f"Channel cleanup failed: {str(e)}")
    
    async def _close_channel(self, channel_id: str):
        """Close and cleanup a real-time channel"""
        
        try:
            if channel_id in self.active_channels:
                del self.active_channels[channel_id]
            
            # Remove from session channels mapping
            session_id = None
            for sid, cid in self.session_channels.items():
                if cid == channel_id:
                    session_id = sid
                    break
            
            if session_id:
                del self.session_channels[session_id]
            
            # Remove from user subscriptions
            for user_id, subscriptions in self.user_subscriptions.items():
                if channel_id in subscriptions:
                    subscriptions.remove(channel_id)
            
            logger.info(f"Closed channel: {channel_id}")
            
        except Exception as e:
            logger.error(f"Failed to close channel {channel_id}: {str(e)}")

# Global service instance
enterprise_realtime_service = EnterpriseRealtimeService()