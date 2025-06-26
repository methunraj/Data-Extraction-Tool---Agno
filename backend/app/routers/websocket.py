"""
WebSocket router for real-time agent monitoring and updates
"""
import json
import logging
import asyncio
from typing import Dict, Set, Any, Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.websockets import WebSocketState

from ..core.dependencies import get_settings
from ..core.config import Settings

logger = logging.getLogger(__name__)

router = APIRouter()

class WebSocketManager:
    """Manages WebSocket connections for real-time monitoring"""
    
    def __init__(self):
        # Store active connections by session_id
        self.active_connections: Dict[str, WebSocket] = {}
        # Store connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.connection_metadata[session_id] = metadata or {}
        
        logger.info(f"WebSocket connected: {session_id}")
        
        # Send welcome message
        await self.send_message(session_id, {
            "type": "connection_established",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to IntelliExtract monitoring"
        })
        
    def disconnect(self, session_id: str):
        """Remove a WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.connection_metadata:
            del self.connection_metadata[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")
        
    async def send_message(self, session_id: str, message: Dict[str, Any]):
        """Send a message to a specific WebSocket connection"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(message))
                else:
                    logger.warning(f"WebSocket {session_id} is not connected, removing")
                    self.disconnect(session_id)
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
                
    async def broadcast_message(self, message: Dict[str, Any], exclude_session: Optional[str] = None):
        """Broadcast a message to all connected WebSocket clients"""
        disconnected_sessions = []
        
        for session_id, websocket in self.active_connections.items():
            if exclude_session and session_id == exclude_session:
                continue
                
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(message))
                else:
                    disconnected_sessions.append(session_id)
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")
                disconnected_sessions.append(session_id)
        
        # Clean up disconnected sessions
        for session_id in disconnected_sessions:
            self.disconnect(session_id)
            
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
        
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about all active connections"""
        return {
            "total_connections": self.get_connection_count(),
            "connections": {
                session_id: {
                    "connected_at": metadata.get("connected_at"),
                    "user_agent": metadata.get("user_agent"),
                    "ip_address": metadata.get("ip_address")
                }
                for session_id, metadata in self.connection_metadata.items()
            }
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

class AgentEventBroadcaster:
    """Handles broadcasting agent events to WebSocket clients"""
    
    @staticmethod
    async def agent_started(agent_type: str, request_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Broadcast agent start event"""
        message = {
            "type": "agent_started",
            "agent_type": agent_type,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        await websocket_manager.broadcast_message(message)
        
    @staticmethod
    async def agent_progress(agent_type: str, request_id: str, progress: float, status: str, details: Optional[str] = None):
        """Broadcast agent progress update"""
        message = {
            "type": "agent_progress",
            "agent_type": agent_type,
            "request_id": request_id,
            "progress": progress,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        await websocket_manager.broadcast_message(message)
        
    @staticmethod
    async def agent_completed(agent_type: str, request_id: str, success: bool, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """Broadcast agent completion event"""
        message = {
            "type": "agent_completed",
            "agent_type": agent_type,
            "request_id": request_id,
            "success": success,
            "result": result,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        await websocket_manager.broadcast_message(message)
        
    @staticmethod
    async def workflow_started(workflow_id: str, request_id: str, agents: list):
        """Broadcast workflow start event"""
        message = {
            "type": "workflow_started",
            "workflow_id": workflow_id,
            "request_id": request_id,
            "agents": agents,
            "timestamp": datetime.now().isoformat()
        }
        await websocket_manager.broadcast_message(message)
        
    @staticmethod
    async def workflow_completed(workflow_id: str, request_id: str, success: bool, results: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        """Broadcast workflow completion event"""
        message = {
            "type": "workflow_completed",
            "workflow_id": workflow_id,
            "request_id": request_id,
            "success": success,
            "results": results,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        await websocket_manager.broadcast_message(message)
        
    @staticmethod
    async def system_status(status: str, details: Optional[Dict[str, Any]] = None):
        """Broadcast system status update"""
        message = {
            "type": "system_status",
            "status": status,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        await websocket_manager.broadcast_message(message)

# Global event broadcaster instance
event_broadcaster = AgentEventBroadcaster()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    session_id: str,
    settings: Settings = Depends(get_settings)
):
    """WebSocket endpoint for real-time monitoring"""
    
    # Get client information
    client_host = websocket.client.host if websocket.client else "unknown"
    user_agent = websocket.headers.get("user-agent", "unknown")
    
    metadata = {
        "connected_at": datetime.now().isoformat(),
        "ip_address": client_host,
        "user_agent": user_agent
    }
    
    try:
        await websocket_manager.connect(websocket, session_id, metadata)
        
        # Send initial system status
        await websocket_manager.send_message(session_id, {
            "type": "system_status",
            "status": "healthy",
            "details": {
                "active_connections": websocket_manager.get_connection_count(),
                "server_time": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (with timeout to send periodic pings)
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client messages
                try:
                    data = json.loads(message)
                    await handle_client_message(session_id, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client {session_id}: {message}")
                    
            except asyncio.TimeoutError:
                # Send periodic ping to keep connection alive
                await websocket_manager.send_message(session_id, {
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client {session_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
    finally:
        websocket_manager.disconnect(session_id)

async def handle_client_message(session_id: str, data: Dict[str, Any]):
    """Handle messages received from WebSocket clients"""
    message_type = data.get("type")
    
    if message_type == "pong":
        # Client responding to ping
        logger.debug(f"Received pong from {session_id}")
        
    elif message_type == "subscribe":
        # Client wants to subscribe to specific events
        event_types = data.get("event_types", [])
        logger.info(f"Client {session_id} subscribing to events: {event_types}")
        
        # Store subscription preferences in metadata
        if session_id in websocket_manager.connection_metadata:
            websocket_manager.connection_metadata[session_id]["subscriptions"] = event_types
            
    elif message_type == "get_status":
        # Client requesting current system status
        await websocket_manager.send_message(session_id, {
            "type": "system_status",
            "status": "healthy",
            "details": {
                "active_connections": websocket_manager.get_connection_count(),
                "server_time": datetime.now().isoformat()
            },
            "timestamp": datetime.now().isoformat()
        })
        
    else:
        logger.warning(f"Unknown message type from {session_id}: {message_type}")

@router.get("/ws/connections")
async def get_websocket_connections():
    """Get information about active WebSocket connections"""
    return websocket_manager.get_connection_info()

@router.post("/ws/broadcast")
async def broadcast_test_message(message: Dict[str, Any]):
    """Broadcast a test message to all connected clients (for testing)"""
    test_message = {
        "type": "test_broadcast",
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    await websocket_manager.broadcast_message(test_message)
    return {"status": "broadcasted", "connections": websocket_manager.get_connection_count()}