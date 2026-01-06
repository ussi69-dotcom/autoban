from typing import Callable, Dict, List, Any
import asyncio
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """Simple async event bus for internal events."""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: str, handler: Callable):
        """Subscribe a handler to an event type."""
        async with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
        logger.debug(f"Handler subscribed to event: {event_type}")

    async def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe a handler from an event type."""
        async with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] if h != handler
                ]
        logger.debug(f"Handler unsubscribed from event: {event_type}")

    async def emit(self, event_type: str, data: Any = None):
        """Emit an event to all subscribed handlers."""
        async with self._lock:
            handlers = self._handlers.get(event_type, []).copy()

        if not handlers:
            return

        logger.debug(f"Emitting event: {event_type} to {len(handlers)} handlers")

        # Execute handlers concurrently
        tasks = [self._safe_call(handler, event_type, data) for handler in handlers]
        await asyncio.gather(*tasks)

    async def _safe_call(self, handler: Callable, event_type: str, data: Any):
        """Safely call a handler, catching exceptions."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
        except Exception as e:
            logger.error(f"Error in event handler for {event_type}: {e}")


# Global event bus
event_bus = EventBus()


# Event type constants
class Events:
    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_DELETED = "task.deleted"
    TASK_STATUS_CHANGED = "task.status_changed"
    TASK_ASSIGNED = "task.assigned"

    # Agent events
    AGENT_SPAWNED = "agent.spawned"
    AGENT_STATUS_CHANGED = "agent.status_changed"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"
    AGENT_HEARTBEAT = "agent.heartbeat"

    # Session events
    SESSION_CREATED = "session.created"
    SESSION_MESSAGE = "session.message"
    SESSION_TOOL_CALL = "session.tool_call"
    SESSION_ENDED = "session.ended"

    # Project events
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"

    # Memory events
    MEMORY_ADDED = "memory.added"
    MEMORY_SEARCHED = "memory.searched"
