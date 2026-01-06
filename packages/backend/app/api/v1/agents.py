"""Agent management endpoints."""

from datetime import datetime
from typing import Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.agent_pool import AgentPoolManager, AgentStatus as PoolAgentStatus

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
    model_config = ConfigDict(populate_by_name=True)
    name: str = Field(..., min_length=1, max_length=50, description="Agent name")
    type: AgentType = Field(
        AgentType.CLAUDE,
        alias="agent_type",
        description="Type of AI agent"
    )
    project_id: str = Field(..., description="Project to assign agent to")
    model: Optional[str] = Field(None, min_length=1, max_length=255, description="Specific model version")
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

POOL_STATUS_TO_API_STATUS = {
    PoolAgentStatus.INITIALIZING: AgentStatus.STARTING,
    PoolAgentStatus.IDLE: AgentStatus.IDLE,
    PoolAgentStatus.BUSY: AgentStatus.RUNNING,
    PoolAgentStatus.ERROR: AgentStatus.ERROR,
    PoolAgentStatus.STOPPING: AgentStatus.STOPPING,
    PoolAgentStatus.STOPPED: AgentStatus.STOPPED,
}

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
    # TODO: Fetch agents from database

    return AgentListResponse(
        items=[],
        total=0,
        active_count=0,
        idle_count=0
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
    # TODO: Fetch agent from database

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Agent not found"
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
    http_request: Request,
    db: AsyncSession = Depends(get_db)
) -> AgentResponse:
    """
    Spawn a new AI agent.

    Creates and starts a new agent instance in the agent pool.
    The agent will be assigned to the specified project.

    - **name**: Display name for the agent
    - **agent_type**: AI provider type (claude, gpt, gemini)
    - **project_id**: Project to assign agent to
    - **model**: Specific model version (optional)
    - **system_prompt**: Custom system prompt (optional)
    - **max_tokens**: Maximum tokens per response
    - **temperature**: Model temperature for response randomness
    """
    agent_pool = getattr(http_request.app.state, "agent_pool", None)
    if not isinstance(agent_pool, AgentPoolManager):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent pool unavailable"
        )

    if len(agent_pool.agents) >= agent_pool.max_agents:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent pool at capacity"
        )

    try:
        agent_id = await agent_pool.spawn_agent()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to spawn agent"
        ) from exc

    if not agent_id:
        detail = "Agent pool at capacity"
        if len(agent_pool.agents) < agent_pool.max_agents:
            detail = "Failed to spawn agent"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )

    agent_info = await agent_pool.get_agent_info(agent_id)
    pool_status = agent_info.status if agent_info else None
    api_status = POOL_STATUS_TO_API_STATUS.get(pool_status, AgentStatus.STARTING)
    now = datetime.utcnow()
    started_at = (
        datetime.utcfromtimestamp(agent_info.started_at)
        if agent_info and agent_info.started_at
        else now
    )
    last_activity_at = (
        datetime.utcfromtimestamp(agent_info.last_heartbeat)
        if agent_info and agent_info.last_heartbeat
        else None
    )

    # Default models per type
    default_models = {
        AgentType.CLAUDE: "claude-sonnet-4-20250514",
        AgentType.GPT: "gpt-4-turbo",
        AgentType.GEMINI: "gemini-pro",
        AgentType.CUSTOM: "custom"
    }

    return AgentResponse(
        id=agent_id,
        name=request.name,
        type=request.type,
        status=api_status,
        project_id=request.project_id,
        project_name="Project Name",  # TODO: Fetch from db
        current_task_id=None,
        current_session_id=agent_info.current_session_id if agent_info else None,
        config=AgentConfig(
            model=request.model or default_models[request.type],
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
        last_activity_at=last_activity_at,
        started_at=started_at,
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
    # TODO: Stop agent

    return AgentStatusResponse(
        id=agent_id,
        status=AgentStatus.STOPPING,
        message="Agent is stopping"
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
    # TODO: Verify agent is stopped
    # TODO: Delete agent
    pass
