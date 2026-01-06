"""Session management endpoints for agent work sessions."""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ============================================================================
# Enums
# ============================================================================

class SessionStatus(str, Enum):
    """Session lifecycle status."""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class MessageRole(str, Enum):
    """Message sender role."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    TOOL = "tool"


class MessageType(str, Enum):
    """Type of message content."""
    TEXT = "text"
    CODE = "code"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    STATUS = "status"


# ============================================================================
# Pydantic Schemas
# ============================================================================

class SessionCreate(BaseModel):
    """Request schema for creating a session."""
    task_id: str = Field(..., description="Task this session is for")
    agent_id: str = Field(..., description="Agent to run the session")
    initial_message: Optional[str] = Field(None, max_length=10000, description="Initial message to start with")
    auto_start: bool = Field(True, description="Automatically start the session")


class SessionResponse(BaseModel):
    """Response schema for session details."""
    id: str
    task_id: str
    task_title: str
    agent_id: str
    agent_name: str
    status: SessionStatus
    message_count: int
    token_count: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime


class SessionListResponse(BaseModel):
    """Response containing list of sessions."""
    items: list[SessionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class ToolCall(BaseModel):
    """Tool call details."""
    tool_name: str
    arguments: dict
    result: Optional[str] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class MessageResponse(BaseModel):
    """Response schema for a session message."""
    id: str
    session_id: str
    role: MessageRole
    type: MessageType
    content: str
    tool_calls: Optional[list[ToolCall]] = None
    token_count: int
    created_at: datetime


class MessageListResponse(BaseModel):
    """Response containing list of messages."""
    items: list[MessageResponse]
    total: int
    has_more: bool


class SendMessage(BaseModel):
    """Request schema for sending a message to a session."""
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    interrupt: bool = Field(False, description="Interrupt current agent activity")


class SessionCancelResponse(BaseModel):
    """Response after cancelling a session."""
    id: str
    status: SessionStatus
    message: str


class SessionSummary(BaseModel):
    """Summary of session work."""
    session_id: str
    task_id: str
    duration_seconds: int
    message_count: int
    tool_calls_count: int
    files_modified: list[str]
    commits_made: list[str]
    summary: str


# ============================================================================
# Session CRUD Endpoints
# ============================================================================

@router.get(
    "",
    response_model=SessionListResponse,
    summary="List sessions",
    responses={
        200: {"description": "List of sessions"},
        401: {"description": "Not authenticated"}
    }
)
async def list_sessions(
    task_id: Optional[str] = Query(None, description="Filter by task"),
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    status: Optional[SessionStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
) -> SessionListResponse:
    """
    List sessions with optional filters.

    - **task_id**: Filter by task
    - **agent_id**: Filter by agent
    - **project_id**: Filter by project
    - **status**: Filter by session status
    """
    # TODO: Fetch sessions from database

    return SessionListResponse(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
        has_more=False
    )


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a session",
    responses={
        201: {"description": "Session created"},
        400: {"description": "Invalid input or agent not available"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Task or agent not found"},
        409: {"description": "Task already has an active session"}
    }
)
async def create_session(
    request: SessionCreate,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """
    Create a new work session.

    Associates an agent with a task and optionally starts working.

    - **task_id**: Task for this session
    - **agent_id**: Agent to run the session
    - **initial_message**: Optional starting message
    - **auto_start**: Start immediately (default true)
    """
    # TODO: Verify task doesn't have active session
    # TODO: Verify agent is available
    # TODO: Create session

    session_id = str(uuid4())
    now = datetime.utcnow()

    return SessionResponse(
        id=session_id,
        task_id=request.task_id,
        task_title="Task Title",  # TODO: Fetch from db
        agent_id=request.agent_id,
        agent_name="Agent Name",  # TODO: Fetch from db
        status=SessionStatus.ACTIVE if request.auto_start else SessionStatus.PENDING,
        message_count=1 if request.initial_message else 0,
        token_count=0,
        started_at=now if request.auto_start else None,
        completed_at=None,
        cancelled_at=None,
        created_at=now
    )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get session details",
    responses={
        200: {"description": "Session details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Session not found"}
    }
)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """
    Get details of a specific session.

    - **session_id**: Session ID
    """
    # TODO: Fetch session from database

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found"
    )


@router.get(
    "/{session_id}/summary",
    response_model=SessionSummary,
    summary="Get session summary",
    responses={
        200: {"description": "Session summary"},
        400: {"description": "Session not completed"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Session not found"}
    }
)
async def get_session_summary(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> SessionSummary:
    """
    Get a summary of completed session work.

    Only available for completed sessions.

    - **session_id**: Session ID
    """
    # TODO: Generate or fetch session summary

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found"
    )


# ============================================================================
# Message Endpoints
# ============================================================================

@router.get(
    "/{session_id}/messages",
    response_model=MessageListResponse,
    summary="Get session messages",
    responses={
        200: {"description": "Session messages"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Session not found"}
    }
)
async def get_messages(
    session_id: str,
    role: Optional[MessageRole] = Query(None, description="Filter by role"),
    type: Optional[MessageType] = Query(None, description="Filter by type"),
    since: Optional[datetime] = Query(None, description="Get messages after this timestamp"),
    limit: int = Query(50, ge=1, le=200, description="Maximum messages to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
) -> MessageListResponse:
    """
    Get messages from a session.

    - **session_id**: Session ID
    - **role**: Filter by message role
    - **type**: Filter by message type
    - **since**: Get messages after timestamp
    - **limit**: Maximum messages to return
    - **offset**: Pagination offset
    """
    # TODO: Fetch messages from database

    return MessageListResponse(
        items=[],
        total=0,
        has_more=False
    )


@router.post(
    "/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message",
    responses={
        201: {"description": "Message sent"},
        400: {"description": "Session not active"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Session not found"}
    }
)
async def send_message(
    session_id: str,
    request: SendMessage,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """
    Send a message to an active session.

    The message will be processed by the agent.
    Use interrupt=true to stop current agent activity first.

    - **session_id**: Session ID
    - **content**: Message content
    - **interrupt**: Interrupt current activity
    """
    # TODO: Verify session is active
    # TODO: Send message to agent
    # TODO: Store message

    message_id = str(uuid4())
    now = datetime.utcnow()

    return MessageResponse(
        id=message_id,
        session_id=session_id,
        role=MessageRole.USER,
        type=MessageType.TEXT,
        content=request.content,
        tool_calls=None,
        token_count=len(request.content.split()),  # Rough estimate
        created_at=now
    )


# ============================================================================
# Session Control Endpoints
# ============================================================================

@router.post(
    "/{session_id}/start",
    response_model=SessionResponse,
    summary="Start a pending session",
    responses={
        200: {"description": "Session started"},
        400: {"description": "Session not in pending state"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Session not found"}
    }
)
async def start_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """
    Start a pending session.

    Only works for sessions created with auto_start=false.

    - **session_id**: Session ID
    """
    # TODO: Start session

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found"
    )


@router.post(
    "/{session_id}/pause",
    response_model=SessionResponse,
    summary="Pause an active session",
    responses={
        200: {"description": "Session paused"},
        400: {"description": "Session not active"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Session not found"}
    }
)
async def pause_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """
    Pause an active session.

    The agent will complete its current action before pausing.
    The session can be resumed later.

    - **session_id**: Session ID
    """
    # TODO: Pause session

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found"
    )


@router.post(
    "/{session_id}/resume",
    response_model=SessionResponse,
    summary="Resume a paused session",
    responses={
        200: {"description": "Session resumed"},
        400: {"description": "Session not paused"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Session not found"}
    }
)
async def resume_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """
    Resume a paused session.

    Continues from where the session was paused.

    - **session_id**: Session ID
    """
    # TODO: Resume session

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found"
    )


@router.post(
    "/{session_id}/complete",
    response_model=SessionResponse,
    summary="Mark session as completed",
    responses={
        200: {"description": "Session completed"},
        400: {"description": "Session not active"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Session not found"}
    }
)
async def complete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """
    Mark a session as completed.

    This signals that the task work is done.
    The associated task status should be updated separately.

    - **session_id**: Session ID
    """
    # TODO: Complete session

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Session not found"
    )


@router.post(
    "/{session_id}/cancel",
    response_model=SessionCancelResponse,
    summary="Cancel a session",
    responses={
        200: {"description": "Session cancelled"},
        400: {"description": "Session already completed or cancelled"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Session not found"}
    }
)
async def cancel_session(
    session_id: str,
    reason: Optional[str] = Query(None, max_length=500, description="Cancellation reason"),
    db: AsyncSession = Depends(get_db)
) -> SessionCancelResponse:
    """
    Cancel a session.

    Immediately stops all agent activity for this session.
    Any uncommitted changes may be lost.

    - **session_id**: Session ID
    - **reason**: Optional reason for cancellation
    """
    # TODO: Cancel session

    return SessionCancelResponse(
        id=session_id,
        status=SessionStatus.CANCELLED,
        message=f"Session cancelled{f': {reason}' if reason else ''}"
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a session",
    responses={
        204: {"description": "Session deleted"},
        400: {"description": "Session is active"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Session not found"}
    }
)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a session and all its messages.

    The session must be completed or cancelled first.

    - **session_id**: Session ID
    """
    # TODO: Verify session is not active
    # TODO: Delete session and messages
    pass
