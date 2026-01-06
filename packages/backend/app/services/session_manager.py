"""
Session Manager for AutoBan.

Manages sessions linking users, projects, tasks, and agents.
Handles message routing and response streaming.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Status states for a session."""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"


class MessageRole(Enum):
    """Role of a message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ToolCall:
    """Represents a tool call made by the agent."""
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    success: bool = True
    error: Optional[str] = None

    def complete(self, result: str, success: bool = True, error: Optional[str] = None) -> None:
        """Mark the tool call as completed."""
        self.result = result
        self.success = success
        self.error = error
        self.completed_at = time.time()

    @property
    def duration_ms(self) -> Optional[float]:
        """Get the duration of the tool call in milliseconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return None


@dataclass
class TokenUsage:
    """Tracks token usage for a session."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def add(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read: int = 0,
        cache_write: int = 0,
    ) -> None:
        """Add token counts."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cache_read_tokens += cache_read
        self.cache_write_tokens += cache_write

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_write_tokens": self.cache_write_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class Message:
    """A message in a session."""
    message_id: str
    role: MessageRole
    content: str
    timestamp: float = field(default_factory=time.time)
    tool_calls: List[ToolCall] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    """Represents a session linking user, project, task, and agent."""
    session_id: str
    user_id: str
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    status: SessionStatus = SessionStatus.PENDING
    messages: List[Message] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_message(
        self,
        role: MessageRole,
        content: str,
        tool_calls: Optional[List[ToolCall]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Add a message to the session."""
        message = Message(
            message_id=str(uuid.uuid4()),
            role=role,
            content=content,
            tool_calls=tool_calls or [],
            metadata=metadata or {},
        )
        self.messages.append(message)
        self.updated_at = time.time()
        return message

    def add_tool_call(self, tool_call: ToolCall) -> None:
        """Track a tool call in the session."""
        self.tool_calls.append(tool_call)
        self.updated_at = time.time()

    def update_tokens(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read: int = 0,
        cache_write: int = 0,
    ) -> None:
        """Update token usage for the session."""
        self.token_usage.add(input_tokens, output_tokens, cache_read, cache_write)
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "message_count": len(self.messages),
            "tool_call_count": len(self.tool_calls),
            "token_usage": self.token_usage.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "ended_at": self.ended_at,
            "metadata": self.metadata,
        }


@dataclass
class StreamChunk:
    """A chunk of streamed response data."""
    chunk_type: str  # "text", "tool_call", "tool_result", "error", "done"
    content: Any
    timestamp: float = field(default_factory=time.time)


class SessionManager:
    """
    Manages sessions between users and agents.

    Features:
    - Create and manage sessions
    - Route messages to agents
    - Stream responses back to clients
    - Track tool calls and token usage
    """

    def __init__(self, agent_pool: Optional[Any] = None):
        """
        Initialize the session manager.

        Args:
            agent_pool: Optional AgentPoolManager for agent assignment
        """
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self._agent_pool = agent_pool
        self._lock = asyncio.Lock()
        self._stream_callbacks: Dict[str, Callable[[StreamChunk], None]] = {}
        self._message_handlers: Dict[str, Callable] = {}

    async def create_session(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            user_id: The user creating the session
            project_id: Optional project to associate with
            task_id: Optional task to associate with
            metadata: Optional additional metadata

        Returns:
            The created session
        """
        session_id = str(uuid.uuid4())

        session = Session(
            session_id=session_id,
            user_id=user_id,
            project_id=project_id,
            task_id=task_id,
            metadata=metadata or {},
        )

        async with self._lock:
            self._sessions[session_id] = session

            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            self._user_sessions[user_id].append(session_id)

        logger.info(f"Created session {session_id} for user {user_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user."""
        session_ids = self._user_sessions.get(user_id, [])
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    async def assign_agent(self, session_id: str, agent_id: str) -> bool:
        """
        Assign an agent to a session.

        Args:
            session_id: The session to assign to
            agent_id: The agent to assign

        Returns:
            True if assignment was successful
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return False

            session.agent_id = agent_id
            session.status = SessionStatus.ACTIVE
            session.updated_at = time.time()

        # If we have an agent pool, assign the agent there too
        if self._agent_pool:
            await self._agent_pool.assign_agent(agent_id, session_id)

        logger.info(f"Assigned agent {agent_id} to session {session_id}")
        return True

    async def send_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Message]:
        """
        Send a user message to a session.

        Args:
            session_id: The session to send to
            content: The message content
            metadata: Optional message metadata

        Returns:
            The created message, or None if session not found
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None

        if session.status not in (SessionStatus.ACTIVE, SessionStatus.PENDING):
            logger.warning(f"Session {session_id} is not active (status: {session.status})")
            return None

        message = session.add_message(
            role=MessageRole.USER,
            content=content,
            metadata=metadata,
        )

        logger.info(f"Added user message to session {session_id}")

        # Route to agent if assigned
        if session.agent_id:
            await self._route_to_agent(session, message)

        return message

    async def _route_to_agent(self, session: Session, message: Message) -> None:
        """
        Route a message to the assigned agent.

        This is a placeholder implementation. In production, this would:
        1. Send the message to the agent process via IPC
        2. Handle the agent's response stream
        """
        handler = self._message_handlers.get(session.session_id)
        if handler:
            try:
                await handler(session, message)
            except Exception as e:
                logger.error(f"Error routing message to agent: {e}")

    async def stream_response(
        self,
        session_id: str,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream response chunks from the agent.

        This is a placeholder implementation that simulates streaming.
        In production, this would stream from the actual agent process.

        Args:
            session_id: The session to stream from

        Yields:
            StreamChunk objects containing response data
        """
        session = await self.get_session(session_id)
        if not session:
            yield StreamChunk(
                chunk_type="error",
                content={"error": "Session not found"},
            )
            return

        # Placeholder: Simulate streaming response
        # In production, this would stream from the agent process

        # Simulate some text chunks
        sample_response = "I understand your request. Let me help you with that."
        words = sample_response.split()

        for word in words:
            yield StreamChunk(
                chunk_type="text",
                content=word + " ",
            )
            await asyncio.sleep(0.05)  # Simulate streaming delay

        # Simulate a tool call
        tool_call = ToolCall(
            tool_call_id=str(uuid.uuid4()),
            tool_name="example_tool",
            arguments={"param": "value"},
        )
        yield StreamChunk(
            chunk_type="tool_call",
            content={
                "tool_call_id": tool_call.tool_call_id,
                "tool_name": tool_call.tool_name,
                "arguments": tool_call.arguments,
            },
        )

        # Simulate tool result
        await asyncio.sleep(0.1)
        tool_call.complete("Tool executed successfully")
        session.add_tool_call(tool_call)

        yield StreamChunk(
            chunk_type="tool_result",
            content={
                "tool_call_id": tool_call.tool_call_id,
                "result": tool_call.result,
                "success": tool_call.success,
            },
        )

        # Update token usage (simulated)
        session.update_tokens(input_tokens=50, output_tokens=100)

        yield StreamChunk(
            chunk_type="done",
            content={
                "token_usage": session.token_usage.to_dict(),
            },
        )

    async def add_assistant_message(
        self,
        session_id: str,
        content: str,
        tool_calls: Optional[List[ToolCall]] = None,
        token_usage: Optional[Dict[str, int]] = None,
    ) -> Optional[Message]:
        """
        Add an assistant message to a session.

        Args:
            session_id: The session to add to
            content: The message content
            tool_calls: Optional list of tool calls made
            token_usage: Optional token usage to record

        Returns:
            The created message, or None if session not found
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        message = session.add_message(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
        )

        if tool_calls:
            for tc in tool_calls:
                session.add_tool_call(tc)

        if token_usage:
            session.update_tokens(
                input_tokens=token_usage.get("input_tokens", 0),
                output_tokens=token_usage.get("output_tokens", 0),
                cache_read=token_usage.get("cache_read_tokens", 0),
                cache_write=token_usage.get("cache_write_tokens", 0),
            )

        return message

    async def record_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Optional[ToolCall]:
        """
        Record a new tool call in a session.

        Args:
            session_id: The session to record in
            tool_name: Name of the tool being called
            arguments: Arguments passed to the tool

        Returns:
            The created ToolCall, or None if session not found
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        tool_call = ToolCall(
            tool_call_id=str(uuid.uuid4()),
            tool_name=tool_name,
            arguments=arguments,
        )
        session.add_tool_call(tool_call)

        logger.debug(f"Recorded tool call {tool_call.tool_call_id} in session {session_id}")
        return tool_call

    async def complete_tool_call(
        self,
        session_id: str,
        tool_call_id: str,
        result: str,
        success: bool = True,
        error: Optional[str] = None,
    ) -> bool:
        """
        Mark a tool call as completed.

        Args:
            session_id: The session containing the tool call
            tool_call_id: The tool call to complete
            result: The result of the tool call
            success: Whether the call succeeded
            error: Optional error message if failed

        Returns:
            True if the tool call was found and updated
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        for tc in session.tool_calls:
            if tc.tool_call_id == tool_call_id:
                tc.complete(result, success, error)
                session.updated_at = time.time()
                return True

        return False

    async def pause_session(self, session_id: str) -> bool:
        """Pause a session."""
        session = await self.get_session(session_id)
        if not session:
            return False

        session.status = SessionStatus.PAUSED
        session.updated_at = time.time()
        logger.info(f"Paused session {session_id}")
        return True

    async def resume_session(self, session_id: str) -> bool:
        """Resume a paused session."""
        session = await self.get_session(session_id)
        if not session or session.status != SessionStatus.PAUSED:
            return False

        session.status = SessionStatus.ACTIVE
        session.updated_at = time.time()
        logger.info(f"Resumed session {session_id}")
        return True

    async def end_session(
        self,
        session_id: str,
        status: SessionStatus = SessionStatus.COMPLETED,
    ) -> bool:
        """
        End a session.

        Args:
            session_id: The session to end
            status: The final status (COMPLETED, ERROR, or TERMINATED)

        Returns:
            True if the session was ended successfully
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        session.status = status
        session.ended_at = time.time()
        session.updated_at = time.time()

        # Release the agent if assigned
        if session.agent_id and self._agent_pool:
            await self._agent_pool.release_agent(session.agent_id)

        logger.info(f"Ended session {session_id} with status {status.value}")
        return True

    async def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a session."""
        session = await self.get_session(session_id)
        if not session:
            return None

        successful_tools = sum(1 for tc in session.tool_calls if tc.success)
        failed_tools = sum(1 for tc in session.tool_calls if not tc.success)

        tool_durations = [
            tc.duration_ms for tc in session.tool_calls if tc.duration_ms is not None
        ]
        avg_tool_duration = (
            sum(tool_durations) / len(tool_durations) if tool_durations else 0
        )

        return {
            "session_id": session_id,
            "status": session.status.value,
            "duration_seconds": (
                (session.ended_at or time.time()) - session.created_at
            ),
            "message_count": len(session.messages),
            "user_messages": sum(
                1 for m in session.messages if m.role == MessageRole.USER
            ),
            "assistant_messages": sum(
                1 for m in session.messages if m.role == MessageRole.ASSISTANT
            ),
            "tool_calls": {
                "total": len(session.tool_calls),
                "successful": successful_tools,
                "failed": failed_tools,
                "avg_duration_ms": avg_tool_duration,
            },
            "token_usage": session.token_usage.to_dict(),
        }

    def register_message_handler(
        self,
        session_id: str,
        handler: Callable,
    ) -> None:
        """
        Register a message handler for a session.

        The handler will be called when messages are routed to the agent.
        """
        self._message_handlers[session_id] = handler

    def unregister_message_handler(self, session_id: str) -> None:
        """Unregister a message handler for a session."""
        self._message_handlers.pop(session_id, None)

    async def cleanup_old_sessions(
        self,
        max_age_hours: float = 24.0,
        inactive_hours: float = 2.0,
    ) -> int:
        """
        Clean up old or inactive sessions.

        Args:
            max_age_hours: Maximum age before session is cleaned up
            inactive_hours: Hours of inactivity before cleanup

        Returns:
            Number of sessions cleaned up
        """
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        inactive_seconds = inactive_hours * 3600

        sessions_to_remove = []

        async with self._lock:
            for session_id, session in self._sessions.items():
                age = now - session.created_at
                inactive_time = now - session.updated_at

                should_remove = (
                    age > max_age_seconds or
                    (inactive_time > inactive_seconds and
                     session.status not in (SessionStatus.ACTIVE, SessionStatus.PENDING))
                )

                if should_remove:
                    sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            await self.end_session(session_id, SessionStatus.TERMINATED)
            async with self._lock:
                session = self._sessions.pop(session_id, None)
                if session:
                    user_sessions = self._user_sessions.get(session.user_id, [])
                    if session_id in user_sessions:
                        user_sessions.remove(session_id)

        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} sessions")

        return len(sessions_to_remove)
