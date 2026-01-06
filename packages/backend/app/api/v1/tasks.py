"""Task management endpoints for Kanban board."""

from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, Project, Task as TaskModel, OrgMember
from app.models.task import TaskStatus as TaskStatusEnum, TaskPriority as TaskPriorityEnum
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ============================================================================
# Enums
# ============================================================================

class TaskStatus(str, Enum):
    """Kanban board task statuses."""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(str, Enum):
    """Task types."""
    FEATURE = "feature"
    BUG = "bug"
    REFACTOR = "refactor"
    TEST = "test"
    DOCS = "docs"
    CHORE = "chore"


# ============================================================================
# Pydantic Schemas
# ============================================================================

class TaskCreate(BaseModel):
    """Request schema for creating a task."""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=5000, description="Task description (markdown)")
    project_id: str = Field(..., description="Project this task belongs to")
    type: TaskType = Field(TaskType.FEATURE, description="Task type")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    status: TaskStatus = Field(TaskStatus.BACKLOG, description="Initial status")
    labels: list[str] = Field(default_factory=list, description="Labels/tags")
    estimated_hours: Optional[float] = Field(None, ge=0, description="Estimated hours")
    parent_task_id: Optional[str] = Field(None, description="Parent task for subtasks")


class TaskBatchCreate(BaseModel):
    """Request schema for batch creating tasks."""
    tasks: list[TaskCreate] = Field(..., min_length=1, max_length=50, description="List of tasks to create")


class TaskUpdate(BaseModel):
    """Request schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    labels: Optional[list[str]] = None
    estimated_hours: Optional[float] = Field(None, ge=0)


class TaskStatusChange(BaseModel):
    """Request schema for changing task status."""
    status: TaskStatus = Field(..., description="New status")
    comment: Optional[str] = Field(None, max_length=500, description="Optional status change comment")


class TaskAssign(BaseModel):
    """Request schema for assigning an agent to a task."""
    agent_id: str = Field(..., description="Agent ID to assign")
    auto_start: bool = Field(True, description="Automatically start working on the task")


class AgentSummary(BaseModel):
    """Summary of an assigned agent."""
    id: str
    name: str
    type: str
    status: str


class TaskResponse(BaseModel):
    """Response schema for task details."""
    id: str
    title: str
    description: Optional[str] = None
    project_id: str
    project_name: str
    type: TaskType
    priority: TaskPriority
    status: TaskStatus
    labels: list[str]
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    assigned_agent: Optional[AgentSummary] = None
    parent_task_id: Optional[str] = None
    subtask_count: int
    completed_subtask_count: int
    session_id: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """Response containing paginated list of tasks."""
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class TaskGroupedResponse(BaseModel):
    """Response with tasks grouped by status for Kanban board."""
    backlog: list[TaskResponse]
    todo: list[TaskResponse]
    in_progress: list[TaskResponse]
    in_review: list[TaskResponse]
    done: list[TaskResponse]
    cancelled: list[TaskResponse]
    total: int


class TaskBatchResponse(BaseModel):
    """Response for batch operations."""
    created: list[TaskResponse]
    failed: list[dict]
    total_created: int
    total_failed: int


class StatusChangeHistoryEntry(BaseModel):
    """Entry in task status change history."""
    from_status: TaskStatus
    to_status: TaskStatus
    changed_by: str
    comment: Optional[str] = None
    changed_at: datetime


class TaskHistoryResponse(BaseModel):
    """Response containing task status history."""
    task_id: str
    history: list[StatusChangeHistoryEntry]


# ============================================================================
# Helper Functions
# ============================================================================

async def verify_project_access(db: AsyncSession, user: User, project_id: str) -> Project:
    """Verify user has access to a project and return it."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project ID format"
        )

    # Get user's organizations
    orgs_result = await db.execute(
        select(OrgMember.org_id).where(OrgMember.user_id == user.id)
    )
    user_org_ids = [row[0] for row in orgs_result.fetchall()]

    # Fetch project
    result = await db.execute(
        select(Project)
        .where(Project.id == project_uuid)
        .where(Project.org_id.in_(user_org_ids))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied"
        )

    return project


def task_to_response(task: TaskModel, project: Project) -> TaskResponse:
    """Convert a Task model to TaskResponse."""
    return TaskResponse(
        id=str(task.id),
        title=task.title,
        description=task.description,
        project_id=str(task.project_id),
        project_name=project.name,
        type=TaskType(task.recommended_profile or "feature"),
        priority=TaskPriority(task.priority.value),
        status=TaskStatus(task.status.value),
        labels=task.labels or [],
        estimated_hours=task.estimated_mins / 60 if task.estimated_mins else None,
        actual_hours=task.actual_mins / 60 if task.actual_mins else None,
        assigned_agent=None,
        parent_task_id=str(task.parent_task_id) if task.parent_task_id else None,
        subtask_count=0,
        completed_subtask_count=0,
        session_id=None,
        created_by=str(task.created_by) if task.created_by else "system",
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        completed_at=task.completed_at
    )


# ============================================================================
# Task CRUD Endpoints
# ============================================================================

@router.get(
    "",
    response_model=TaskListResponse,
    summary="List tasks",
    responses={
        200: {"description": "List of tasks"},
        401: {"description": "Not authenticated"}
    }
)
async def list_tasks(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    task_status: Optional[TaskStatus] = Query(None, alias="status", description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    type: Optional[TaskType] = Query(None, description="Filter by type"),
    assigned_agent_id: Optional[str] = Query(None, description="Filter by assigned agent"),
    labels: Optional[str] = Query(None, description="Filter by labels (comma-separated)"),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search in title/description"),
    parent_task_id: Optional[str] = Query(None, description="Filter by parent task (get subtasks)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskListResponse:
    """
    List tasks with optional filters.

    - **project_id**: Filter by project
    - **status**: Filter by task status
    - **priority**: Filter by priority
    - **type**: Filter by task type
    - **assigned_agent_id**: Filter tasks assigned to a specific agent
    - **labels**: Comma-separated list of labels to filter by
    - **search**: Search in title and description
    - **parent_task_id**: Get subtasks of a parent task
    """
    # Get user's organizations
    orgs_result = await db.execute(
        select(OrgMember.org_id).where(OrgMember.user_id == user.id)
    )
    user_org_ids = [row[0] for row in orgs_result.fetchall()]

    if not user_org_ids:
        return TaskListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            has_more=False
        )

    # Build query - get tasks from projects in user's orgs
    query = (
        select(TaskModel)
        .join(Project, TaskModel.project_id == Project.id)
        .options(selectinload(TaskModel.project))
        .where(Project.org_id.in_(user_org_ids))
    )

    # Filter by project if specified
    if project_id:
        try:
            project_uuid = UUID(project_id)
            query = query.where(TaskModel.project_id == project_uuid)
        except ValueError:
            pass

    # Filter by status
    if task_status:
        query = query.where(TaskModel.status == TaskStatusEnum(task_status.value))

    # Filter by priority
    if priority:
        query = query.where(TaskModel.priority == TaskPriorityEnum(priority.value))

    # Search filter
    if search:
        query = query.where(
            TaskModel.title.ilike(f"%{search}%") | TaskModel.description.ilike(f"%{search}%")
        )

    # Filter by parent task
    if parent_task_id:
        try:
            parent_uuid = UUID(parent_task_id)
            query = query.where(TaskModel.parent_task_id == parent_uuid)
        except ValueError:
            pass

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(TaskModel.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    tasks = result.scalars().all()

    items = [task_to_response(task, task.project) for task in tasks]

    return TaskListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(items)) < total
    )


@router.get(
    "/grouped",
    response_model=TaskGroupedResponse,
    summary="Get tasks grouped by status",
    responses={
        200: {"description": "Tasks grouped by status for Kanban board"},
        401: {"description": "Not authenticated"},
        404: {"description": "Project not found"}
    }
)
async def get_tasks_grouped(
    project_id: str = Query(..., description="Project ID to get tasks for"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    type: Optional[TaskType] = Query(None, description="Filter by type"),
    labels: Optional[str] = Query(None, description="Filter by labels (comma-separated)"),
    include_subtasks: bool = Query(False, description="Include subtasks in results"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskGroupedResponse:
    """
    Get tasks grouped by status for Kanban board display.

    Returns tasks organized into their respective status columns.

    - **project_id**: Project to get tasks for
    - **priority**: Optional priority filter
    - **type**: Optional type filter
    - **labels**: Optional labels filter
    - **include_subtasks**: Whether to include subtasks
    """
    # Verify project access
    project = await verify_project_access(db, user, project_id)

    # Build query
    query = (
        select(TaskModel)
        .where(TaskModel.project_id == project.id)
    )

    # Filter by priority
    if priority:
        query = query.where(TaskModel.priority == TaskPriorityEnum(priority.value))

    # Exclude subtasks unless requested
    if not include_subtasks:
        query = query.where(TaskModel.parent_task_id.is_(None))

    result = await db.execute(query)
    tasks = result.scalars().all()

    # Group tasks by status
    grouped = {
        "backlog": [],
        "todo": [],
        "in_progress": [],
        "in_review": [],
        "done": [],
        "cancelled": [],
    }

    for task in tasks:
        response = task_to_response(task, project)
        status_key = task.status.value
        if status_key in grouped:
            grouped[status_key].append(response)

    return TaskGroupedResponse(
        backlog=grouped["backlog"],
        todo=grouped["todo"],
        in_progress=grouped["in_progress"],
        in_review=grouped["in_review"],
        done=grouped["done"],
        cancelled=grouped["cancelled"],
        total=len(tasks)
    )


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
    responses={
        201: {"description": "Task created successfully"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied to project"},
        404: {"description": "Project not found"}
    }
)
async def create_task(
    request: TaskCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Create a new task.

    - **title**: Task title
    - **description**: Markdown description
    - **project_id**: Project this task belongs to
    - **type**: Task type (feature, bug, etc.)
    - **priority**: Priority level
    - **status**: Initial status (defaults to backlog)
    - **labels**: Optional labels
    - **estimated_hours**: Optional time estimate
    - **parent_task_id**: Optional parent for subtasks
    """
    # Verify project access
    project = await verify_project_access(db, user, request.project_id)

    # Handle parent task if specified
    parent_task_uuid = None
    if request.parent_task_id:
        try:
            parent_task_uuid = UUID(request.parent_task_id)
            # Verify parent task exists and belongs to the same project
            parent_result = await db.execute(
                select(TaskModel).where(
                    TaskModel.id == parent_task_uuid,
                    TaskModel.project_id == project.id
                )
            )
            if not parent_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent task not found"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent task ID format"
            )

    # Create task - use the model's enum directly to ensure proper type matching
    status_enum = TaskStatusEnum[request.status.name]  # Convert API enum to model enum
    priority_enum = TaskPriorityEnum[request.priority.name]

    task = TaskModel(
        project_id=project.id,
        title=request.title,
        description=request.description,
        status=status_enum,
        priority=priority_enum,
        recommended_profile=request.type.value,
        labels=request.labels,
        estimated_mins=int(request.estimated_hours * 60) if request.estimated_hours else None,
        parent_task_id=parent_task_uuid,
        created_by=user.id,
    )
    db.add(task)
    await db.flush()

    return task_to_response(task, project)


@router.post(
    "/batch",
    response_model=TaskBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Batch create tasks",
    responses={
        201: {"description": "Tasks created"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"}
    }
)
async def batch_create_tasks(
    request: TaskBatchCreate,
    db: AsyncSession = Depends(get_db)
) -> TaskBatchResponse:
    """
    Create multiple tasks in a single request.

    Useful for importing tasks or creating related tasks together.
    Each task is validated independently; failures don't affect other tasks.

    - **tasks**: List of tasks to create (max 50)
    """
    # TODO: Validate and create tasks
    # TODO: Collect successes and failures

    created = []
    failed = []

    for i, task_data in enumerate(request.tasks):
        try:
            # TODO: Create task
            task_id = str(uuid4())
            now = datetime.utcnow()

            task = TaskResponse(
                id=task_id,
                title=task_data.title,
                description=task_data.description,
                project_id=task_data.project_id,
                project_name="Project Name",
                type=task_data.type,
                priority=task_data.priority,
                status=task_data.status,
                labels=task_data.labels,
                estimated_hours=task_data.estimated_hours,
                actual_hours=None,
                assigned_agent=None,
                parent_task_id=task_data.parent_task_id,
                subtask_count=0,
                completed_subtask_count=0,
                session_id=None,
                created_by="current_user_id",
                created_at=now,
                updated_at=now,
                started_at=None,
                completed_at=None
            )
            created.append(task)
        except Exception as e:
            failed.append({"index": i, "error": str(e)})

    return TaskBatchResponse(
        created=created,
        failed=failed,
        total_created=len(created),
        total_failed=len(failed)
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task details",
    responses={
        200: {"description": "Task details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Task not found"}
    }
)
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Get details of a specific task.

    - **task_id**: Task ID
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format"
        )

    # Get user's organizations
    orgs_result = await db.execute(
        select(OrgMember.org_id).where(OrgMember.user_id == user.id)
    )
    user_org_ids = [row[0] for row in orgs_result.fetchall()]

    # Fetch task with project
    result = await db.execute(
        select(TaskModel)
        .join(Project, TaskModel.project_id == Project.id)
        .options(selectinload(TaskModel.project))
        .where(TaskModel.id == task_uuid)
        .where(Project.org_id.in_(user_org_ids))
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task_to_response(task, task.project)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task",
    responses={
        200: {"description": "Task updated"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Task not found"}
    }
)
async def update_task(
    task_id: str,
    request: TaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Update a task's details.

    Does not change status - use the status change endpoint for that.

    - **task_id**: Task ID
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format"
        )

    # Get user's organizations
    orgs_result = await db.execute(
        select(OrgMember.org_id).where(OrgMember.user_id == user.id)
    )
    user_org_ids = [row[0] for row in orgs_result.fetchall()]

    if not user_org_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Get task with project
    result = await db.execute(
        select(TaskModel)
        .join(Project, TaskModel.project_id == Project.id)
        .where(TaskModel.id == task_uuid)
        .where(Project.org_id.in_(user_org_ids))
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Update fields
    if request.title is not None:
        task.title = request.title
    if request.description is not None:
        task.description = request.description
    if request.priority is not None:
        task.priority = TaskPriorityEnum[request.priority.name]
    if request.type is not None:
        task.recommended_profile = request.type.value
    if request.labels is not None:
        task.labels = request.labels
    if request.estimated_hours is not None:
        task.estimated_mins = int(request.estimated_hours * 60)

    await db.commit()
    await db.refresh(task)

    # Reload with project for response
    result = await db.execute(
        select(TaskModel)
        .options(selectinload(TaskModel.project))
        .where(TaskModel.id == task_uuid)
    )
    task = result.scalar_one()

    return task_to_response(task, task.project)


@router.post(
    "/{task_id}/status",
    response_model=TaskResponse,
    summary="Change task status",
    responses={
        200: {"description": "Status changed"},
        400: {"description": "Invalid status transition"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Task not found"}
    }
)
async def change_task_status(
    task_id: str,
    request: TaskStatusChange,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Change a task's status.

    Records the status change in history with optional comment.
    Updates started_at when moving to in_progress.
    Updates completed_at when moving to done.

    - **task_id**: Task ID
    - **status**: New status
    - **comment**: Optional comment for the status change
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format"
        )

    # Get user's organizations
    orgs_result = await db.execute(
        select(OrgMember.org_id).where(OrgMember.user_id == user.id)
    )
    user_org_ids = [row[0] for row in orgs_result.fetchall()]

    if not user_org_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Get task with project
    result = await db.execute(
        select(TaskModel)
        .join(Project, TaskModel.project_id == Project.id)
        .where(TaskModel.id == task_uuid)
        .where(Project.org_id.in_(user_org_ids))
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Update status - convert API enum to model enum
    old_status = task.status
    new_status = TaskStatusEnum[request.status.name]
    task.status = new_status

    # Update timestamps based on status
    if new_status == TaskStatusEnum.IN_PROGRESS and old_status != TaskStatusEnum.IN_PROGRESS:
        task.started_at = datetime.utcnow()
    elif new_status == TaskStatusEnum.DONE and old_status != TaskStatusEnum.DONE:
        task.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(task)

    # Reload with project for response
    result = await db.execute(
        select(TaskModel)
        .options(selectinload(TaskModel.project))
        .where(TaskModel.id == task_uuid)
    )
    task = result.scalar_one()

    return task_to_response(task, task.project)


@router.get(
    "/{task_id}/history",
    response_model=TaskHistoryResponse,
    summary="Get task status history",
    responses={
        200: {"description": "Task status history"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Task not found"}
    }
)
async def get_task_history(
    task_id: str,
    db: AsyncSession = Depends(get_db)
) -> TaskHistoryResponse:
    """
    Get the status change history for a task.

    - **task_id**: Task ID
    """
    # TODO: Fetch history from database

    return TaskHistoryResponse(
        task_id=task_id,
        history=[]
    )


# ============================================================================
# Agent Assignment Endpoints
# ============================================================================

@router.post(
    "/{task_id}/assign",
    response_model=TaskResponse,
    summary="Assign agent to task",
    responses={
        200: {"description": "Agent assigned"},
        400: {"description": "Agent not available or already assigned"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Task or agent not found"}
    }
)
async def assign_agent(
    task_id: str,
    request: TaskAssign,
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Assign an AI agent to work on a task.

    If auto_start is true, the agent will immediately start working.

    - **task_id**: Task ID
    - **agent_id**: Agent ID to assign
    - **auto_start**: Start working immediately
    """
    # TODO: Verify agent is available
    # TODO: Assign agent to task
    # TODO: Optionally start work session

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Task not found"
    )


@router.post(
    "/{task_id}/unassign",
    response_model=TaskResponse,
    summary="Unassign agent from task",
    responses={
        200: {"description": "Agent unassigned"},
        400: {"description": "Agent is currently working"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Task not found"}
    }
)
async def unassign_agent(
    task_id: str,
    force: bool = Query(False, description="Force unassign even if agent is working"),
    db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    """
    Remove the assigned agent from a task.

    If the agent is currently working, use force=true to stop and unassign.

    - **task_id**: Task ID
    - **force**: Force unassign even if agent is working
    """
    # TODO: Unassign agent

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Task not found"
    )


# ============================================================================
# Task Delete Endpoint
# ============================================================================

@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    responses={
        204: {"description": "Task deleted"},
        400: {"description": "Cannot delete task with active session"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Task not found"}
    }
)
async def delete_task(
    task_id: str,
    cascade: bool = Query(False, description="Also delete subtasks"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a task.

    Cannot delete a task with an active agent session unless cancelled first.
    Use cascade=true to also delete all subtasks.

    - **task_id**: Task ID
    - **cascade**: Delete subtasks as well
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid task ID format"
        )

    # Get user's organizations
    orgs_result = await db.execute(
        select(OrgMember.org_id).where(OrgMember.user_id == user.id)
    )
    user_org_ids = [row[0] for row in orgs_result.fetchall()]

    if not user_org_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Get task with project
    result = await db.execute(
        select(TaskModel)
        .join(Project, TaskModel.project_id == Project.id)
        .where(TaskModel.id == task_uuid)
        .where(Project.org_id.in_(user_org_ids))
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # If cascade, delete subtasks first
    if cascade:
        subtasks_result = await db.execute(
            select(TaskModel).where(TaskModel.parent_task_id == task_uuid)
        )
        subtasks = subtasks_result.scalars().all()
        for subtask in subtasks:
            await db.delete(subtask)

    # Delete the task
    await db.delete(task)
    await db.commit()
