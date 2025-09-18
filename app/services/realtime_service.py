"""
NMTC Supabase Real-Time Integration Service

Enterprise real-time communication service for cross-device synchronization and live updates.
Handles Supabase real-time subscriptions, channels, and live progress broadcasting.

Author: CORE ENGINE PROCESSING AGENT
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

from app.services.supabase_service import supabase_service
from app.config import settings

logger = logging.getLogger(__name__)

class ChannelType(str, Enum):
    """Types of real-time channels"""
    DOCUMENT_PROCESSING = "document_processing"
    USER_SESSION = "user_session"
    ORGANIZATION = "organization"
    SYSTEM_ALERTS = "system_alerts"

class EventType(str, Enum):
    """Real-time event types"""
    PROGRESS_UPDATE = "progress_update"
    STATUS_CHANGE = "status_change"
    ERROR_NOTIFICATION = "error_notification"
    USER_ACTION_REQUIRED = "user_action_required"
    PROCESSING_COMPLETE = "processing_complete"
    HEARTBEAT = "heartbeat"
    SYSTEM_MESSAGE = "system_message"

class RealtimeMessage:
    """Structure for real-time messages"""
    
    def __init__(
        self,
        channel: str,
        event_type: EventType,
        payload: Dict[str, Any],
        sender_id: str = None,
        target_users: List[str] = None,
        expires_at: datetime = None
    ):
        self.message_id = f"msg_{int(datetime.utcnow().timestamp())}_{id(self)}"
        self.channel = channel
        self.event_type = event_type
        self.payload = payload
        self.sender_id = sender_id
        self.target_users = target_users or []
        self.created_at = datetime.utcnow()
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(hours=24))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for transmission"""
        return {
            'message_id': self.message_id,
            'channel': self.channel,
            'event_type': self.event_type.value,
            'payload': self.payload,
            'sender_id': self.sender_id,
            'target_users': self.target_users,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RealtimeMessage':
        """Create message from dictionary"""
        msg = cls(
            channel=data['channel'],
            event_type=EventType(data['event_type']),
            payload=data['payload'],
            sender_id=data.get('sender_id'),
            target_users=data.get('target_users', []),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None
        )
        msg.message_id = data['message_id']
        msg.created_at = datetime.fromisoformat(data['created_at'])
        return msg

class ChannelManager:
    """Manages real-time channels and subscriptions"""
    
    def __init__(self):
        self.active_channels: Dict[str, Dict[str, Any]] = {}
        self.channel_subscribers: Dict[str, List[str]] = {}  # channel -> user_ids
        self.user_channels: Dict[str, List[str]] = {}  # user_id -> channels
        self.message_history: Dict[str, List[RealtimeMessage]] = {}
        self.max_history_per_channel = 100
    
    def create_channel(
        self, 
        channel_id: str, 
        channel_type: ChannelType,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new real-time channel"""
        if channel_id in self.active_channels:
            logger.warning(f"Channel already exists: {channel_id}")
            return self.active_channels[channel_id]
        
        channel_info = {
            'channel_id': channel_id,
            'channel_type': channel_type.value,
            'created_at': datetime.utcnow().isoformat(),
            'subscriber_count': 0,
            'message_count': 0,
            'last_activity': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        
        self.active_channels[channel_id] = channel_info
        self.channel_subscribers[channel_id] = []
        self.message_history[channel_id] = []
        
        logger.info(f"Created real-time channel: {channel_id} ({channel_type.value})")
        return channel_info
    
    def subscribe_user(self, channel_id: str, user_id: str) -> bool:
        """Subscribe a user to a channel"""
        if channel_id not in self.active_channels:
            logger.warning(f"Attempted to subscribe to non-existent channel: {channel_id}")
            return False
        
        if user_id not in self.channel_subscribers[channel_id]:
            self.channel_subscribers[channel_id].append(user_id)
            self.active_channels[channel_id]['subscriber_count'] += 1
        
        if user_id not in self.user_channels:
            self.user_channels[user_id] = []
        
        if channel_id not in self.user_channels[user_id]:
            self.user_channels[user_id].append(channel_id)
        
        logger.info(f"User {user_id} subscribed to channel {channel_id}")
        return True
    
    def unsubscribe_user(self, channel_id: str, user_id: str) -> bool:
        """Unsubscribe a user from a channel"""
        if channel_id not in self.channel_subscribers:
            return False
        
        if user_id in self.channel_subscribers[channel_id]:
            self.channel_subscribers[channel_id].remove(user_id)
            self.active_channels[channel_id]['subscriber_count'] -= 1
        
        if user_id in self.user_channels and channel_id in self.user_channels[user_id]:
            self.user_channels[user_id].remove(channel_id)
        
        logger.info(f"User {user_id} unsubscribed from channel {channel_id}")
        return True
    
    def get_channel_subscribers(self, channel_id: str) -> List[str]:
        """Get list of subscribers for a channel"""
        return self.channel_subscribers.get(channel_id, [])
    
    def get_user_channels(self, user_id: str) -> List[str]:
        """Get list of channels a user is subscribed to"""
        return self.user_channels.get(user_id, [])
    
    def get_channel_history(self, channel_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent message history for a channel"""
        if channel_id not in self.message_history:
            return []
        
        messages = self.message_history[channel_id][-limit:]
        return [msg.to_dict() for msg in messages]
    
    def add_message_to_history(self, channel_id: str, message: RealtimeMessage):
        """Add message to channel history"""
        if channel_id not in self.message_history:
            self.message_history[channel_id] = []
        
        self.message_history[channel_id].append(message)
        
        # Maintain history limit
        if len(self.message_history[channel_id]) > self.max_history_per_channel:
            self.message_history[channel_id] = self.message_history[channel_id][-self.max_history_per_channel:]
        
        # Update channel activity
        if channel_id in self.active_channels:
            self.active_channels[channel_id]['message_count'] += 1
            self.active_channels[channel_id]['last_activity'] = datetime.utcnow().isoformat()

class RealtimeService:
    """Main real-time communication service"""
    
    def __init__(self):
        self.channel_manager = ChannelManager()
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'channels_created': 0,
            'active_subscribers': 0,
            'errors': 0,
            'start_time': datetime.utcnow()
        }
    
    async def start(self):
        """Start the real-time service"""
        if self.is_running:
            logger.warning("Real-time service already running")
            return
        
        self.is_running = True
        self.processing_task = asyncio.create_task(self._message_processor())
        
        logger.info("Real-time service started")
    
    async def stop(self):
        """Stop the real-time service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Real-time service stopped")
    
    async def create_document_channel(self, document_id: str, user_id: str = None) -> str:
        """Create a channel for document processing updates"""
        channel_id = f"doc_{document_id}"
        
        metadata = {
            'document_id': document_id,
            'created_by': user_id,
            'purpose': 'document_processing_updates'
        }
        
        self.channel_manager.create_channel(
            channel_id, 
            ChannelType.DOCUMENT_PROCESSING, 
            metadata
        )
        
        # Subscribe the user if provided
        if user_id:
            self.channel_manager.subscribe_user(channel_id, user_id)
        
        self.stats['channels_created'] += 1
        
        logger.info(f"Created document channel: {channel_id}")
        return channel_id
    
    async def create_user_session_channel(self, user_id: str, org_id: str = None) -> str:
        """Create a channel for user session updates"""
        channel_id = f"user_{user_id}"
        
        metadata = {
            'user_id': user_id,
            'org_id': org_id,
            'purpose': 'user_session_updates'
        }
        
        self.channel_manager.create_channel(
            channel_id,
            ChannelType.USER_SESSION,
            metadata
        )
        
        self.channel_manager.subscribe_user(channel_id, user_id)
        self.stats['channels_created'] += 1
        
        logger.info(f"Created user session channel: {channel_id}")
        return channel_id
    
    async def send_progress_update(
        self,
        document_id: str,
        stage: str,
        progress_percentage: int,
        message: str,
        details: Dict[str, Any] = None,
        user_id: str = None
    ):
        """Send a progress update to document channel"""
        channel_id = f"doc_{document_id}"
        
        # Ensure channel exists
        if channel_id not in self.channel_manager.active_channels:
            await self.create_document_channel(document_id, user_id)
        
        payload = {
            'document_id': document_id,
            'stage': stage,
            'progress_percentage': progress_percentage,
            'message': message,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        message_obj = RealtimeMessage(
            channel=channel_id,
            event_type=EventType.PROGRESS_UPDATE,
            payload=payload,
            sender_id='system'
        )
        
        await self._queue_message(message_obj)
    
    async def send_status_change(
        self,
        document_id: str,
        old_status: str,
        new_status: str,
        user_id: str = None,
        details: Dict[str, Any] = None
    ):
        """Send a status change notification"""
        channel_id = f"doc_{document_id}"
        
        payload = {
            'document_id': document_id,
            'old_status': old_status,
            'new_status': new_status,
            'changed_by': user_id,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        message_obj = RealtimeMessage(
            channel=channel_id,
            event_type=EventType.STATUS_CHANGE,
            payload=payload,
            sender_id=user_id or 'system'
        )
        
        await self._queue_message(message_obj)
    
    async def send_error_notification(
        self,
        document_id: str,
        error_message: str,
        error_category: str = 'unknown',
        user_id: str = None,
        recoverable: bool = True
    ):
        """Send an error notification"""
        channel_id = f"doc_{document_id}"
        
        payload = {
            'document_id': document_id,
            'error_message': error_message,
            'error_category': error_category,
            'recoverable': recoverable,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        message_obj = RealtimeMessage(
            channel=channel_id,
            event_type=EventType.ERROR_NOTIFICATION,
            payload=payload,
            sender_id='system'
        )
        
        await self._queue_message(message_obj)
    
    async def send_user_action_required(
        self,
        document_id: str,
        action_type: str,
        action_message: str,
        action_data: Dict[str, Any] = None,
        user_id: str = None
    ):
        """Send a user action required notification"""
        channel_id = f"doc_{document_id}"
        
        payload = {
            'document_id': document_id,
            'action_type': action_type,
            'action_message': action_message,
            'action_data': action_data or {},
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        message_obj = RealtimeMessage(
            channel=channel_id,
            event_type=EventType.USER_ACTION_REQUIRED,
            payload=payload,
            sender_id='system',
            target_users=[user_id] if user_id else None
        )
        
        await self._queue_message(message_obj)
    
    async def send_processing_complete(
        self,
        document_id: str,
        final_status: str,
        processing_summary: Dict[str, Any] = None,
        user_id: str = None
    ):
        """Send processing complete notification"""
        channel_id = f"doc_{document_id}"
        
        payload = {
            'document_id': document_id,
            'final_status': final_status,
            'processing_summary': processing_summary or {},
            'completed_at': datetime.utcnow().isoformat()
        }
        
        message_obj = RealtimeMessage(
            channel=channel_id,
            event_type=EventType.PROCESSING_COMPLETE,
            payload=payload,
            sender_id='system'
        )
        
        await self._queue_message(message_obj)
    
    async def subscribe_user_to_document(self, user_id: str, document_id: str) -> bool:
        """Subscribe a user to document updates"""
        channel_id = f"doc_{document_id}"
        
        # Create channel if it doesn't exist
        if channel_id not in self.channel_manager.active_channels:
            await self.create_document_channel(document_id, user_id)
        
        return self.channel_manager.subscribe_user(channel_id, user_id)
    
    async def unsubscribe_user_from_document(self, user_id: str, document_id: str) -> bool:
        """Unsubscribe a user from document updates"""
        channel_id = f"doc_{document_id}"
        return self.channel_manager.unsubscribe_user(channel_id, user_id)
    
    async def get_user_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all channels a user is subscribed to"""
        channels = self.channel_manager.get_user_channels(user_id)
        
        subscriptions = []
        for channel_id in channels:
            if channel_id in self.channel_manager.active_channels:
                channel_info = self.channel_manager.active_channels[channel_id].copy()
                channel_info['recent_messages'] = self.channel_manager.get_channel_history(channel_id, 5)
                subscriptions.append(channel_info)
        
        return subscriptions
    
    async def get_document_activity(self, document_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent activity for a document"""
        channel_id = f"doc_{document_id}"
        return self.channel_manager.get_channel_history(channel_id, limit)
    
    async def _queue_message(self, message: RealtimeMessage):
        """Queue a message for processing"""
        try:
            await self.message_queue.put(message)
        except Exception as e:
            logger.error(f"Failed to queue message: {str(e)}")
            self.stats['errors'] += 1
    
    async def _message_processor(self):
        """Process queued messages"""
        logger.info("Real-time message processor started")
        
        while self.is_running:
            try:
                # Get message with timeout
                message = await asyncio.wait_for(
                    self.message_queue.get(), 
                    timeout=1.0
                )
                
                await self._process_message(message)
                self.stats['messages_sent'] += 1
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                self.stats['errors'] += 1
    
    async def _process_message(self, message: RealtimeMessage):
        """Process and deliver a message"""
        try:
            # Add to channel history
            self.channel_manager.add_message_to_history(message.channel, message)
            
            # Get channel subscribers
            subscribers = self.channel_manager.get_channel_subscribers(message.channel)
            
            # Filter by target users if specified
            if message.target_users:
                subscribers = [user for user in subscribers if user in message.target_users]
            
            if not subscribers:
                logger.debug(f"No subscribers for channel {message.channel}")
                return
            
            # Store message in database for Supabase real-time pickup
            await self._store_realtime_message(message, subscribers)
            
            logger.debug(f"Processed message to {len(subscribers)} subscribers on channel {message.channel}")
            
        except Exception as e:
            logger.error(f"Failed to process message: {str(e)}")
            self.stats['errors'] += 1
    
    async def _store_realtime_message(self, message: RealtimeMessage, subscribers: List[str]):
        """Store message in database for Supabase real-time subscriptions"""
        try:
            # Store in a real-time events table that frontend can subscribe to
            message_data = {
                'id': message.message_id,
                'channel': message.channel,
                'event_type': message.event_type.value,
                'payload': json.dumps(message.payload),
                'sender_id': message.sender_id,
                'target_users': subscribers,
                'created_at': message.created_at.isoformat(),
                'expires_at': message.expires_at.isoformat()
            }
            
            # Insert into realtime_events table (table should have RLS policies)
            try:
                result = supabase_service.client.table('realtime_events').insert(message_data).execute()
                logger.debug(f"Stored real-time message in database: {message.message_id}")
            except Exception as db_error:
                # If table doesn't exist, create a fallback mechanism
                logger.warning(f"Could not store in realtime_events table: {str(db_error)}")
                
                # Fallback: Store in document's parsed_index for polling-based updates
                if message.payload.get('document_id'):
                    await self._store_fallback_message(message)
            
        except Exception as e:
            logger.error(f"Failed to store real-time message: {str(e)}")
    
    async def _store_fallback_message(self, message: RealtimeMessage):
        """Fallback storage mechanism for real-time messages"""
        try:
            document_id = message.payload.get('document_id')
            if not document_id:
                return
            
            document = await supabase_service.get_document(document_id)
            parsed_index = document.get('parsed_index', {})
            
            if 'realtime_messages' not in parsed_index:
                parsed_index['realtime_messages'] = []
            
            parsed_index['realtime_messages'].append(message.to_dict())
            
            # Keep only last 20 messages
            if len(parsed_index['realtime_messages']) > 20:
                parsed_index['realtime_messages'] = parsed_index['realtime_messages'][-20:]
            
            await supabase_service.update_document_status(
                document_id=document_id,
                status='message_updated',
                updates={'parsed_index': parsed_index}
            )
            
        except Exception as e:
            logger.error(f"Fallback message storage failed: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'active_channels': len(self.channel_manager.active_channels),
            'total_subscribers': sum(len(subs) for subs in self.channel_manager.channel_subscribers.values()),
            'messages_per_second': self.stats['messages_sent'] / max(uptime, 1),
            'error_rate': self.stats['errors'] / max(self.stats['messages_sent'], 1),
            'is_running': self.is_running
        }

# Global real-time service instance
realtime_service = RealtimeService()

# Auto-start the service when module is imported
async def initialize_realtime_service():
    """Initialize the real-time service"""
    await realtime_service.start()
    logger.info("Real-time service initialized")

# Integration with progress tracker
async def send_progress_to_realtime(
    document_id: str,
    stage: str,
    progress_percentage: int,
    message: str,
    details: Dict[str, Any] = None,
    user_id: str = None
):
    """Send progress update to real-time service"""
    await realtime_service.send_progress_update(
        document_id=document_id,
        stage=stage,
        progress_percentage=progress_percentage,
        message=message,
        details=details,
        user_id=user_id
    )