from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, Set, Optional
import json
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and channel subscriptions."""

    def __init__(self):
        # websocket -> set of subscribed channels
        self.connections: Dict[WebSocket, Set[str]] = {}
        # channel -> set of subscribed websockets
        self.channels: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.connections[websocket] = set()
        logger.info(f"WebSocket connected: {user_id or 'anonymous'}")

    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection."""
        async with self._lock:
            # Unsubscribe from all channels
            if websocket in self.connections:
                for channel in self.connections[websocket]:
                    if channel in self.channels:
                        self.channels[channel].discard(websocket)
                        if not self.channels[channel]:
                            del self.channels[channel]
                del self.connections[websocket]
        logger.info("WebSocket disconnected")

    async def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe a connection to a channel."""
        async with self._lock:
            if websocket in self.connections:
                self.connections[websocket].add(channel)
                if channel not in self.channels:
                    self.channels[channel] = set()
                self.channels[channel].add(websocket)
        logger.debug(f"Subscribed to channel: {channel}")

    async def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe a connection from a channel."""
        async with self._lock:
            if websocket in self.connections:
                self.connections[websocket].discard(channel)
            if channel in self.channels:
                self.channels[channel].discard(websocket)
                if not self.channels[channel]:
                    del self.channels[channel]
        logger.debug(f"Unsubscribed from channel: {channel}")

    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast a message to all subscribers of a channel."""
        async with self._lock:
            subscribers = self.channels.get(channel, set()).copy()

        disconnected = []
        for websocket in subscribers:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to websocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(ws)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            await self.disconnect(websocket)


# Global connection manager
manager = ConnectionManager()


def get_manager() -> ConnectionManager:
    """Get the global connection manager."""
    return manager


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time updates.

    Supported message types:
    - subscribe: Subscribe to a channel
    - unsubscribe: Unsubscribe from a channel
    - session:message: Send message to a session

    Channel formats:
    - project:<project_id>: Project updates (tasks, etc.)
    - agent:<agent_id>:logs: Agent log streaming
    - session:<session_id>: Session messages
    """
    # TODO: Validate token and get user_id
    user_id = None
    if token:
        # user_id = await validate_token(token)
        pass

    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            await handle_message(websocket, data, user_id)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


async def handle_message(websocket: WebSocket, data: dict, user_id: Optional[str]):
    """Handle incoming WebSocket messages."""
    msg_type = data.get("type")

    if msg_type == "subscribe":
        channel = data.get("channel")
        if channel:
            # TODO: Check authorization for channel
            await manager.subscribe(websocket, channel)
            await manager.send_personal(websocket, {
                "type": "subscribed",
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat()
            })

    elif msg_type == "unsubscribe":
        channel = data.get("channel")
        if channel:
            await manager.unsubscribe(websocket, channel)
            await manager.send_personal(websocket, {
                "type": "unsubscribed",
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat()
            })

    elif msg_type == "session:message":
        session_id = data.get("session_id")
        content = data.get("content")
        if session_id and content:
            # TODO: Route message to session manager
            # For now, echo back
            await manager.send_personal(websocket, {
                "type": "session:message:received",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            })

    elif msg_type == "ping":
        await manager.send_personal(websocket, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })

    else:
        await manager.send_personal(websocket, {
            "type": "error",
            "message": f"Unknown message type: {msg_type}"
        })


# Helper functions for broadcasting events

async def broadcast_task_update(project_id: str, task_id: str, changes: dict):
    """Broadcast task update to project subscribers."""
    await manager.broadcast_to_channel(f"project:{project_id}", {
        "type": "task:updated",
        "task_id": task_id,
        "changes": changes,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_task_created(project_id: str, task: dict):
    """Broadcast new task to project subscribers."""
    await manager.broadcast_to_channel(f"project:{project_id}", {
        "type": "task:created",
        "task": task,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_task_deleted(project_id: str, task_id: str):
    """Broadcast task deletion to project subscribers."""
    await manager.broadcast_to_channel(f"project:{project_id}", {
        "type": "task:deleted",
        "task_id": task_id,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_agent_status(agent_id: str, status: str, details: dict = None):
    """Broadcast agent status change."""
    await manager.broadcast_to_channel(f"agent:{agent_id}", {
        "type": "agent:status",
        "agent_id": agent_id,
        "status": status,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_agent_log(agent_id: str, level: str, message: str):
    """Broadcast agent log message."""
    await manager.broadcast_to_channel(f"agent:{agent_id}:logs", {
        "type": "agent:log",
        "agent_id": agent_id,
        "level": level,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_session_message(session_id: str, role: str, content: str, tool_calls: list = None):
    """Broadcast session message."""
    await manager.broadcast_to_channel(f"session:{session_id}", {
        "type": "session:message",
        "session_id": session_id,
        "role": role,
        "content": content,
        "tool_calls": tool_calls,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_session_tool(session_id: str, tool: str, status: str, result: str = None):
    """Broadcast tool execution status."""
    await manager.broadcast_to_channel(f"session:{session_id}", {
        "type": "session:tool",
        "session_id": session_id,
        "tool": tool,
        "status": status,
        "result": result,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_background_completed(parent_session_id: str, task_description: str, summary: str):
    """Broadcast background task completion."""
    await manager.broadcast_to_channel(f"session:{parent_session_id}", {
        "type": "background:completed",
        "parent_session_id": parent_session_id,
        "task_description": task_description,
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat()
    })
