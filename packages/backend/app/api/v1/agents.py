"""Agent management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.agent import AgentInstance, AgentStatus as DBAgentStatus
from app.models.project import Project

router = APIRouter(prefix="/agents", tags=["Agents"])


# ============================================================================
# Enums
# ============================================================================

class AgentType(str, Enum):
    """Types of AI agents."""
    CLAUDE = "claude"
    GPT = "gpt"
    GEMINI = "gemini"
    CUSTOM = "custom"


class AgentStatus(str, Enum):
    """Agent lifecycle status."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class LogLevel(str, Enum):
    """Log severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# ============================================================================
# Pydantic Schemas
# ============================================================================

class AgentSpawn(BaseModel):
    """Request schema for spawning a new agent."""
    name: str = Field(..., min_length=1, max_length=50, description="Agent name")
    type: AgentType = Field(AgentType.CLAUDE, description="Type of AI agent")
    project_id: str = Field(..., description="Project to assign agent to")
    model: Optional[str] = Field(None, description="Specific model version")
    system_prompt: Optional[str] = Field(None, max_length=10000, description="Custom system prompt")
    max_tokens: int = Field(4096, ge=100, le=100000, description="Max tokens per response")
    temperature: float = Field(0.7, ge=0, le=2, description="Model temperature")


class AgentConfig(BaseModel):
    """Agent configuration details."""
    model: str
    system_prompt: Optional[str] = None
    max_tokens: int
    temperature: float
    tools_enabled: list[str]


class AgentMetrics(BaseModel):
    """Agent performance metrics."""
    total_sessions: int
    completed_tasks: int
    failed_tasks: int
    total_tokens_used: int
    average_response_time_ms: float
    uptime_seconds: int


class AgentResponse(BaseModel):
    """Response schema for agent details."""
    id: str
    name: str
    type: AgentType
    status: AgentStatus
    project_id: str
    project_name: str
    current_task_id: Optional[str] = None
    current_session_id: Optional[str] = None
    config: AgentConfig
    metrics: AgentMetrics
    last_activity_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    created_at: datetime


class AgentListResponse(BaseModel):
    """Response containing list of agents."""
    items: list[AgentResponse]
    total: int
    active_count: int
    idle_count: int


class LogEntry(BaseModel):
    """A single log entry."""
    timestamp: datetime
    level: LogLevel
    message: str
    metadata: Optional[dict] = None


class AgentLogsResponse(BaseModel):
    """Response containing agent logs."""
    agent_id: str
    logs: list[LogEntry]
    total: int
    has_more: bool


class AgentStatusResponse(BaseModel):
    """Response after status change operation."""
    id: str
    status: AgentStatus
    message: str


# ============================================================================
# Agent Endpoints
# ============================================================================

@router.get(
    "",
    response_model=AgentListResponse,
    summary="List agents",
    responses={
        200: {"description": "List of agents"},
        401: {"description": "Not authenticated"}
    }
)
async def list_agents(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    status: Optional[AgentStatus] = Query(None, description="Filter by status"),
    type: Optional[AgentType] = Query(None, description="Filter by type"),
    db: AsyncSession = Depends(get_db)
) -> AgentListResponse:
    """
    List all agents accessible to the current user.

    - **project_id**: Filter by project
    - **status**: Filter by agent status
    - **type**: Filter by agent type
    """
    # Build query
    query = select(AgentInstance)

    # Apply filters
    if status:
        db_status = DBAgentStatus(status.value) if status.value in [s.value for s in DBAgentStatus] else None
        if db_status:
            query = query.where(AgentInstance.status == db_status)

    if type:
        query = query.where(AgentInstance.agent_type == type.value)

    # Execute query
    result = await db.execute(query)
    agents = result.scalars().all()

    # Count active and idle
    active_count = sum(1 for a in agents if a.status in (DBAgentStatus.BUSY, DBAgentStatus.INITIALIZING))
    idle_count = sum(1 for a in agents if a.status == DBAgentStatus.IDLE)

    # Convert to response
    items = []
    for agent in agents:
        items.append(AgentResponse(
            id=str(agent.id),
            name=f"{agent.agent_type}-{str(agent.id)[:8]}",
            type=AgentType(agent.agent_type) if agent.agent_type in [t.value for t in AgentType] else AgentType.CUSTOM,
            status=AgentStatus(agent.status.value) if agent.status.value in [s.value for s in AgentStatus] else AgentStatus.STOPPED,
            project_id="",  # Agents aren't tied to projects in current model
            project_name="",
            current_task_id=str(agent.current_task_id) if agent.current_task_id else None,
            current_session_id=str(agent.current_session_id) if agent.current_session_id else None,
            config=AgentConfig(
                model=agent.model,
                system_prompt=None,
                max_tokens=4096,
                temperature=0.7,
                tools_enabled=["file_read", "file_write", "terminal", "browser"]
            ),
            metrics=AgentMetrics(
                total_sessions=0,
                completed_tasks=0,
                failed_tasks=0,
                total_tokens_used=0,
                average_response_time_ms=0,
                uptime_seconds=int((datetime.utcnow() - agent.started_at.replace(tzinfo=None)).total_seconds()) if agent.started_at else 0
            ),
            last_activity_at=agent.last_heartbeat,
            started_at=agent.started_at,
            created_at=agent.started_at
        ))

    return AgentListResponse(
        items=items,
        total=len(items),
        active_count=active_count,
        idle_count=idle_count
    )


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent details",
    responses={
        200: {"description": "Agent details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Agent not found"}
    }
)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    """
    Get details of a specific agent.

    - **agent_id**: Agent ID
    """
    try:
        agent_uuid = UUID(agent_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID format"
        )

    result = await db.execute(select(AgentInstance).where(AgentInstance.id == agent_uuid))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    return AgentResponse(
        id=str(agent.id),
        name=f"{agent.agent_type}-{str(agent.id)[:8]}",
        type=AgentType(agent.agent_type) if agent.agent_type in [t.value for t in AgentType] else AgentType.CUSTOM,
        status=AgentStatus(agent.status.value) if agent.status.value in [s.value for s in AgentStatus] else AgentStatus.STOPPED,
        project_id="",
        project_name="",
        current_task_id=str(agent.current_task_id) if agent.current_task_id else None,
        current_session_id=str(agent.current_session_id) if agent.current_session_id else None,
        config=AgentConfig(
            model=agent.model,
            system_prompt=None,
            max_tokens=4096,
            temperature=0.7,
            tools_enabled=["file_read", "file_write", "terminal", "browser"]
        ),
        metrics=AgentMetrics(
            total_sessions=0,
            completed_tasks=0,
            failed_tasks=0,
            total_tokens_used=0,
            average_response_time_ms=0,
            uptime_seconds=int((datetime.utcnow() - agent.started_at.replace(tzinfo=None)).total_seconds()) if agent.started_at else 0
        ),
        last_activity_at=agent.last_heartbeat,
        started_at=agent.started_at,
        created_at=agent.started_at
    )


@router.post(
    "/spawn",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Spawn a new agent",
    responses={
        201: {"description": "Agent spawned successfully"},
        400: {"description": "Invalid configuration"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied to project"},
        404: {"description": "Project not found"},
        503: {"description": "Agent pool at capacity"}
    }
)
async def spawn_agent(
    request: AgentSpawn,
    db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    """
    Spawn a new AI agent.

    Creates and starts a new agent instance in the agent pool.
    The agent will be assigned to the specified project.

    - **name**: Display name for the agent
    - **type**: AI provider type (claude, gpt, gemini)
    - **project_id**: Project to assign agent to
    - **model**: Specific model version (optional)
    - **system_prompt**: Custom system prompt (optional)
    - **max_tokens**: Maximum tokens per response
    - **temperature**: Model temperature for response randomness
    """
    # Default models per type
    default_models = {
        AgentType.CLAUDE: "claude-sonnet-4-20250514",
        AgentType.GPT: "gpt-4-turbo",
        AgentType.GEMINI: "gemini-pro",
        AgentType.CUSTOM: "custom"
    }

    model = request.model or default_models[request.type]
    now = datetime.utcnow()

    # Validate project exists
    try:
        project_uuid = UUID(request.project_id)
        project_result = await db.execute(select(Project).where(Project.id == project_uuid))
        project = project_result.scalar_one_or_none()
        project_name = project.name if project else "Unknown Project"
    except (ValueError, Exception):
        project_name = "Unknown Project"

    # Check current agent count (max 10 agents)
    count_result = await db.execute(
        select(func.count(AgentInstance.id)).where(
            AgentInstance.status.in_([DBAgentStatus.IDLE, DBAgentStatus.BUSY, DBAgentStatus.INITIALIZING])
        )
    )
    active_count = count_result.scalar() or 0

    if active_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent pool at capacity (max 10 agents)"
        )

    # Create agent instance in database
    agent = AgentInstance(
        agent_type=request.type.value,
        model=model,
        status=DBAgentStatus.INITIALIZING,
        started_at=now,
        last_heartbeat=now,
    )
    db.add(agent)
    await db.flush()

    # Update status to IDLE (simulating successful spawn)
    # In production, this would happen after subprocess confirms it's ready
    agent.status = DBAgentStatus.IDLE
    agent.last_heartbeat = datetime.utcnow()

    return AgentResponse(
        id=str(agent.id),
        name=request.name,
        type=request.type,
        status=AgentStatus.IDLE,
        project_id=request.project_id,
        project_name=project_name,
        current_task_id=None,
        current_session_id=None,
        config=AgentConfig(
            model=model,
            system_prompt=request.system_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            tools_enabled=["file_read", "file_write", "terminal", "browser"]
        ),
        metrics=AgentMetrics(
            total_sessions=0,
            completed_tasks=0,
            failed_tasks=0,
            total_tokens_used=0,
            average_response_time_ms=0,
            uptime_seconds=0
        ),
        last_activity_at=now,
        started_at=now,
        created_at=now
    )


@router.post(
    "/{agent_id}/stop",
    response_model=AgentStatusResponse,
    summary="Stop an agent",
    responses={
        200: {"description": "Agent stopping"},
        400: {"description": "Agent not running"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Agent not found"}
    }
)
async def stop_agent(
    agent_id: str,
    force: bool = Query(False, description="Force stop immediately without cleanup"),
    db: AsyncSession = Depends(get_db)
) -> AgentStatusResponse:
    """
    Stop a running agent.

    Gracefully stops the agent, completing any in-progress operations.
    Use force=true to immediately terminate without cleanup.

    - **agent_id**: Agent ID
    - **force**: Force immediate termination
    """
    try:
        agent_uuid = UUID(agent_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID format"
        )

    result = await db.execute(select(AgentInstance).where(AgentInstance.id == agent_uuid))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if agent.status in (DBAgentStatus.STOPPED, DBAgentStatus.STOPPING):
        return AgentStatusResponse(
            id=agent_id,
            status=AgentStatus.STOPPED,
            message="Agent is already stopped"
        )

    # Update agent status
    agent.status = DBAgentStatus.STOPPED
    agent.stopped_at = datetime.utcnow()

    return AgentStatusResponse(
        id=agent_id,
        status=AgentStatus.STOPPED,
        message="Agent stopped successfully"
    )


@router.post(
    "/{agent_id}/restart",
    response_model=AgentStatusResponse,
    summary="Restart an agent",
    responses={
        200: {"description": "Agent restarting"},
        400: {"description": "Agent in invalid state for restart"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Agent not found"}
    }
)
async def restart_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
) -> AgentStatusResponse:
    """
    Restart an agent.

    Stops and restarts the agent with its current configuration.
    Useful for recovering from errors or refreshing state.

    - **agent_id**: Agent ID
    """
    # TODO: Restart agent

    return AgentStatusResponse(
        id=agent_id,
        status=AgentStatus.STARTING,
        message="Agent is restarting"
    )


@router.post(
    "/{agent_id}/pause",
    response_model=AgentStatusResponse,
    summary="Pause an agent",
    responses={
        200: {"description": "Agent paused"},
        400: {"description": "Agent not running"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Agent not found"}
    }
)
async def pause_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
) -> AgentStatusResponse:
    """
    Pause a running agent.

    Suspends agent activity. The agent can be resumed later.
    Current work is preserved but not progressed.

    - **agent_id**: Agent ID
    """
    # TODO: Pause agent

    return AgentStatusResponse(
        id=agent_id,
        status=AgentStatus.PAUSED,
        message="Agent paused"
    )


@router.post(
    "/{agent_id}/resume",
    response_model=AgentStatusResponse,
    summary="Resume a paused agent",
    responses={
        200: {"description": "Agent resumed"},
        400: {"description": "Agent not paused"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Agent not found"}
    }
)
async def resume_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
) -> AgentStatusResponse:
    """
    Resume a paused agent.

    Continues from where the agent was paused.

    - **agent_id**: Agent ID
    """
    # TODO: Resume agent

    return AgentStatusResponse(
        id=agent_id,
        status=AgentStatus.RUNNING,
        message="Agent resumed"
    )


# ============================================================================
# Agent Logs Endpoints
# ============================================================================

@router.get(
    "/{agent_id}/logs",
    response_model=AgentLogsResponse,
    summary="Get agent logs",
    responses={
        200: {"description": "Agent logs"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Agent not found"}
    }
)
async def get_agent_logs(
    agent_id: str,
    level: Optional[LogLevel] = Query(None, description="Filter by log level"),
    since: Optional[datetime] = Query(None, description="Get logs since timestamp"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
) -> AgentLogsResponse:
    """
    Get logs for a specific agent.

    - **agent_id**: Agent ID
    - **level**: Filter by minimum log level
    - **since**: Get logs after this timestamp
    - **limit**: Maximum logs to return
    - **offset**: Pagination offset
    """
    # TODO: Fetch logs from database/log aggregator

    return AgentLogsResponse(
        agent_id=agent_id,
        logs=[],
        total=0,
        has_more=False
    )


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an agent",
    responses={
        204: {"description": "Agent deleted"},
        400: {"description": "Agent is still running"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Agent not found"}
    }
)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete an agent.

    The agent must be stopped before deletion.
    This removes all agent configuration and metrics.

    - **agent_id**: Agent ID
    """
    try:
        agent_uuid = UUID(agent_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID format"
        )

    result = await db.execute(select(AgentInstance).where(AgentInstance.id == agent_uuid))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if agent.status not in (DBAgentStatus.STOPPED, DBAgentStatus.ERROR):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent must be stopped before deletion"
        )

    await db.delete(agent)
