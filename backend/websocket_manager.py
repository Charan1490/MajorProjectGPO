"""
WebSocket Manager for Real-Time Fleet Updates
Handles WebSocket connections, subscriptions, and message broadcasting
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time fleet monitoring
    """
    
    def __init__(self):
        # All active connections
        self.active_connections: Set[WebSocket] = set()
        
        # Subscriptions: connection -> set of channels
        self.subscriptions: Dict[WebSocket, Set[str]] = defaultdict(set)
        
        # Reverse index: channel -> set of connections
        self.channel_subscribers: Dict[str, Set[WebSocket]] = defaultdict(set)
        
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, dict] = {}
        
        # Message queue for rate limiting
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Start background workers
        self._start_workers()
    
    def _start_workers(self):
        """Start background tasks"""
        # Message processing worker will be started by FastAPI
        pass
    
    # ============================================================================
    # CONNECTION MANAGEMENT
    # ============================================================================
    
    async def connect(
        self,
        websocket: WebSocket,
        client_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = set()
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "client_id": client_id,
            "connected_at": datetime.now(),
            "metadata": metadata or {}
        }
        
        logger.info(
            f"WebSocket connected: client_id={client_id}, "
            f"total_connections={len(self.active_connections)}"
        )
        
        # Send welcome message
        await self.send_personal_message(websocket, {
            "message_type": "connection_established",
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id,
            "data": {
                "message": "Connected to Fleet Management WebSocket",
                "available_channels": [
                    "fleet_status",
                    "deployments",
                    "machine_updates",
                    "alerts"
                ]
            }
        })
    
    def disconnect(self, websocket: WebSocket):
        """Unregister a disconnected WebSocket"""
        # Remove from active connections
        self.active_connections.discard(websocket)
        
        # Remove from all subscriptions
        channels = self.subscriptions.get(websocket, set())
        for channel in channels:
            self.channel_subscribers[channel].discard(websocket)
        
        # Clean up
        self.subscriptions.pop(websocket, None)
        metadata = self.connection_metadata.pop(websocket, {})
        
        logger.info(
            f"WebSocket disconnected: client_id={metadata.get('client_id')}, "
            f"remaining_connections={len(self.active_connections)}"
        )
    
    # ============================================================================
    # SUBSCRIPTION MANAGEMENT
    # ============================================================================
    
    def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe connection to a channel"""
        if websocket not in self.active_connections:
            logger.warning("Attempted to subscribe disconnected WebSocket")
            return False
        
        self.subscriptions[websocket].add(channel)
        self.channel_subscribers[channel].add(websocket)
        
        logger.info(
            f"Subscription added: channel={channel}, "
            f"client_id={self.connection_metadata[websocket].get('client_id')}"
        )
        return True
    
    def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe connection from a channel"""
        self.subscriptions[websocket].discard(channel)
        self.channel_subscribers[channel].discard(websocket)
        
        logger.info(
            f"Subscription removed: channel={channel}, "
            f"client_id={self.connection_metadata[websocket].get('client_id')}"
        )
    
    def get_subscriptions(self, websocket: WebSocket) -> List[str]:
        """Get all channels a connection is subscribed to"""
        return list(self.subscriptions.get(websocket, set()))
    
    # ============================================================================
    # MESSAGE SENDING
    # ============================================================================
    
    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send message to a specific connection"""
        try:
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to connection: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast message to all subscribers of a channel"""
        subscribers = self.channel_subscribers.get(channel, set())
        
        if not subscribers:
            return
        
        # Add channel info to message
        message["channel"] = channel
        
        disconnected = set()
        
        for connection in subscribers:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to channel subscriber: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    # ============================================================================
    # HIGH-LEVEL FLEET MESSAGES
    # ============================================================================
    
    async def broadcast_machine_status(self, machine_data: dict):
        """Broadcast machine status update"""
        message = {
            "message_type": "machine_status",
            "timestamp": datetime.now().isoformat(),
            "data": machine_data
        }
        await self.broadcast_to_channel("machine_updates", message)
        await self.broadcast_to_channel("fleet_status", message)
    
    async def broadcast_deployment_update(self, deployment_data: dict):
        """Broadcast deployment status update"""
        message = {
            "message_type": "deployment_update",
            "timestamp": datetime.now().isoformat(),
            "data": deployment_data
        }
        await self.broadcast_to_channel("deployments", message)
        await self.broadcast_to_channel("fleet_status", message)
    
    async def broadcast_deployment_progress(self, progress_data: dict):
        """Broadcast deployment progress for a specific machine"""
        message = {
            "message_type": "deployment_progress",
            "timestamp": datetime.now().isoformat(),
            "data": progress_data
        }
        await self.broadcast_to_channel("deployments", message)
    
    async def broadcast_alert(self, alert_data: dict):
        """Broadcast alert to monitoring clients"""
        message = {
            "message_type": "alert",
            "timestamp": datetime.now().isoformat(),
            "data": alert_data
        }
        await self.broadcast_to_channel("alerts", message)
        
        # Also send to fleet_status for general awareness
        await self.broadcast_to_channel("fleet_status", message)
    
    async def broadcast_fleet_statistics(self, stats_data: dict):
        """Broadcast fleet-wide statistics"""
        message = {
            "message_type": "fleet_statistics",
            "timestamp": datetime.now().isoformat(),
            "data": stats_data
        }
        await self.broadcast_to_channel("fleet_status", message)
    
    # ============================================================================
    # MESSAGE HANDLING
    # ============================================================================
    
    async def handle_client_message(self, websocket: WebSocket, message: dict):
        """Handle incoming message from client"""
        try:
            message_type = message.get("type")
            
            if message_type == "subscribe":
                channels = message.get("channels", [])
                for channel in channels:
                    self.subscribe(websocket, channel)
                
                await self.send_personal_message(websocket, {
                    "message_type": "subscription_confirmed",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "channels": channels,
                        "subscriptions": self.get_subscriptions(websocket)
                    }
                })
            
            elif message_type == "unsubscribe":
                channels = message.get("channels", [])
                for channel in channels:
                    self.unsubscribe(websocket, channel)
                
                await self.send_personal_message(websocket, {
                    "message_type": "unsubscription_confirmed",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "channels": channels,
                        "subscriptions": self.get_subscriptions(websocket)
                    }
                })
            
            elif message_type == "ping":
                await self.send_personal_message(websocket, {
                    "message_type": "pong",
                    "timestamp": datetime.now().isoformat(),
                    "data": message.get("data", {})
                })
            
            elif message_type == "get_subscriptions":
                await self.send_personal_message(websocket, {
                    "message_type": "subscriptions",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "subscriptions": self.get_subscriptions(websocket)
                    }
                })
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_personal_message(websocket, {
                    "message_type": "error",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "error": f"Unknown message type: {message_type}"
                    }
                })
        
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            await self.send_personal_message(websocket, {
                "message_type": "error",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "error": "Failed to process message"
                }
            })
    
    # ============================================================================
    # STATISTICS
    # ============================================================================
    
    def get_connection_stats(self) -> dict:
        """Get WebSocket connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "total_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
            "channels": {
                channel: len(subscribers)
                for channel, subscribers in self.channel_subscribers.items()
            },
            "connections": [
                {
                    "client_id": metadata.get("client_id"),
                    "connected_at": metadata.get("connected_at").isoformat()
                    if metadata.get("connected_at") else None,
                    "subscriptions": list(self.subscriptions.get(ws, set()))
                }
                for ws, metadata in self.connection_metadata.items()
            ]
        }
    
    # ============================================================================
    # KEEPALIVE
    # ============================================================================
    
    async def send_keepalive(self):
        """Send keepalive ping to all connections"""
        message = {
            "message_type": "keepalive",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "active_connections": len(self.active_connections)
            }
        }
        await self.broadcast_to_all(message)


# Global connection manager instance
websocket_manager = ConnectionManager()


# ============================================================================
# FASTAPI WEBSOCKET HANDLER
# ============================================================================

async def fleet_websocket_endpoint(websocket: WebSocket, client_id: Optional[str] = None):
    """
    WebSocket endpoint for fleet monitoring
    
    Usage in FastAPI:
    
    @app.websocket("/ws/fleet")
    async def fleet_websocket(websocket: WebSocket, client_id: Optional[str] = None):
        await fleet_websocket_endpoint(websocket, client_id)
    """
    await websocket_manager.connect(websocket, client_id)
    
    try:
        # Auto-subscribe to fleet_status channel
        websocket_manager.subscribe(websocket, "fleet_status")
        
        # Listen for messages
        while True:
            # Receive message
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await websocket_manager.handle_client_message(websocket, message)
            
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message(websocket, {
                    "message_type": "error",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "error": "Invalid JSON"
                    }
                })
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def keepalive_task():
    """Send periodic keepalive messages"""
    while True:
        await asyncio.sleep(30)  # Every 30 seconds
        await websocket_manager.send_keepalive()
