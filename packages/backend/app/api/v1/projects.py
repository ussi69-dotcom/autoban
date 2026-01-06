"""Project management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, Project, Organization, OrgMember, Task
from app.models.task import TaskStatus as TaskStatusEnum, TaskPriority as TaskPriorityEnum
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])


# ============================================================================
# Enums
# ============================================================================

class ProjectVisibility(str, Enum):
    """Project visibility settings."""
    PRIVATE = "private"
    INTERNAL = "internal"
    PUBLIC = "public"


class RepositoryProvider(str, Enum):
    """Supported repository providers."""
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    LOCAL = "local"


class RepositoryStatus(str, Enum):
    """Repository synchronization status."""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    ERROR = "error"


# ============================================================================
# Pydantic Schemas
# ============================================================================

class ProjectCreate(BaseModel):
    """Request schema for creating a project."""
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    slug: Optional[str] = Field(None, min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$",
                      description="URL-friendly identifier (auto-generated if not provided)")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    organization_id: Optional[str] = Field(None, description="ID of the organization (uses personal org if not provided)")
    visibility: ProjectVisibility = Field(ProjectVisibility.PRIVATE, description="Project visibility")


class ProjectUpdate(BaseModel):
    """Request schema for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    visibility: Optional[ProjectVisibility] = None


class RepositoryConnect(BaseModel):
    """Request schema for connecting a repository."""
    provider: RepositoryProvider = Field(..., description="Repository provider")
    url: str = Field(..., description="Repository URL")
    branch: str = Field("main", description="Default branch to track")
    auto_sync: bool = Field(True, description="Automatically sync on push")


class RepositoryResponse(BaseModel):
    """Response schema for repository details."""
    id: str
    provider: RepositoryProvider
    url: str
    branch: str
    status: RepositoryStatus
    auto_sync: bool
    last_synced_at: Optional[datetime] = None
    last_commit_sha: Optional[str] = None
    last_commit_message: Optional[str] = None
    connected_at: datetime


class ProjectResponse(BaseModel):
    """Response schema for project details."""
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    organization_id: str
    organization_name: str
    visibility: ProjectVisibility
    repository: Optional[RepositoryResponse] = None
    task_count: int
    active_agent_count: int
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Response containing paginated list of projects."""
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class ProjectStats(BaseModel):
    """Project statistics."""
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    pending_tasks: int
    total_sessions: int
    active_sessions: int
    total_commits: int
    lines_changed: int


# ============================================================================
# Project CRUD Endpoints
# ============================================================================

def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a name."""
    import re
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug[:50] if len(slug) > 50 else slug


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    responses={
        201: {"description": "Project created successfully"},
        400: {"description": "Invalid input or slug already taken"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied to organization"},
        404: {"description": "Organization not found"}
    }
)
async def create_project(
    request: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """
    Create a new project within an organization.

    - **name**: Display name for the project
    - **slug**: URL-friendly identifier (unique within organization)
    - **description**: Optional project description
    - **organization_id**: ID of the parent organization (uses personal org if not provided)
    - **visibility**: Who can see this project
    """
    # Get organization - either specified or user's personal org
    if request.organization_id:
        try:
            org_uuid = UUID(request.organization_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID format"
            )

        # Verify user has access to organization
        result = await db.execute(
            select(Organization)
            .join(OrgMember, OrgMember.org_id == Organization.id)
            .where(Organization.id == org_uuid)
            .where(OrgMember.user_id == user.id)
        )
        org = result.scalar_one_or_none()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied"
            )
    else:
        # Use user's personal organization
        result = await db.execute(
            select(Organization)
            .join(OrgMember, OrgMember.org_id == Organization.id)
            .where(OrgMember.user_id == user.id)
            .where(OrgMember.role == "owner")
            .limit(1)
        )
        org = result.scalar_one_or_none()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User has no organization"
            )

    # Generate slug if not provided
    slug = request.slug if request.slug else generate_slug(request.name)

    # Check if slug is unique within organization
    existing = await db.execute(
        select(Project)
        .where(Project.org_id == org.id)
        .where(Project.name == request.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A project with this name already exists in the organization"
        )

    # Create project
    project = Project(
        org_id=org.id,
        name=request.name,
        description=request.description,
        created_by=user.id,
        settings={"visibility": request.visibility.value},
    )
    db.add(project)
    await db.flush()

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        slug=slug,
        description=project.description,
        organization_id=str(org.id),
        organization_name=org.name,
        visibility=request.visibility,
        repository=None,
        task_count=0,
        active_agent_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List projects",
    responses={
        200: {"description": "List of projects"},
        401: {"description": "Not authenticated"}
    }
)
async def list_projects(
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    visibility: Optional[ProjectVisibility] = Query(None, description="Filter by visibility"),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ProjectListResponse:
    """
    List projects accessible to the current user.

    - **organization_id**: Filter by organization
    - **visibility**: Filter by visibility level
    - **search**: Search in name and description
    """
    # Get user's organizations
    orgs_result = await db.execute(
        select(OrgMember.org_id).where(OrgMember.user_id == user.id)
    )
    user_org_ids = [row[0] for row in orgs_result.fetchall()]

    if not user_org_ids:
        return ProjectListResponse(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
            has_more=False
        )

    # Build query for projects in user's organizations
    query = (
        select(Project)
        .options(selectinload(Project.organization))
        .where(Project.org_id.in_(user_org_ids))
        .where(Project.archived_at.is_(None))
    )

    # Filter by organization if specified
    if organization_id:
        try:
            org_uuid = UUID(organization_id)
            query = query.where(Project.org_id == org_uuid)
        except ValueError:
            pass

    # Search filter
    if search:
        query = query.where(
            Project.name.ilike(f"%{search}%") | Project.description.ilike(f"%{search}%")
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(Project.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    projects = result.scalars().all()

    # Build response
    items = []
    for project in projects:
        # Get task count
        task_count_result = await db.execute(
            select(func.count()).where(Task.project_id == project.id)
        )
        task_count = task_count_result.scalar() or 0

        items.append(ProjectResponse(
            id=str(project.id),
            name=project.name,
            slug=generate_slug(project.name),
            description=project.description,
            organization_id=str(project.org_id),
            organization_name=project.organization.name,
            visibility=ProjectVisibility(project.settings.get("visibility", "private")),
            repository=None,
            task_count=task_count,
            active_agent_count=0,
            created_at=project.created_at,
            updated_at=project.updated_at
        ))

    return ProjectListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(items)) < total
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details",
    responses={
        200: {"description": "Project details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Project not found"}
    }
)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """
    Get details of a specific project.

    - **project_id**: Project ID or slug
    """
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
        .options(selectinload(Project.organization))
        .where(Project.id == project_uuid)
        .where(Project.org_id.in_(user_org_ids))
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get task count
    task_count_result = await db.execute(
        select(func.count()).where(Task.project_id == project.id)
    )
    task_count = task_count_result.scalar() or 0

    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        slug=generate_slug(project.name),
        description=project.description,
        organization_id=str(project.org_id),
        organization_name=project.organization.name,
        visibility=ProjectVisibility(project.settings.get("visibility", "private")),
        repository=None,
        task_count=task_count,
        active_agent_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
    responses={
        200: {"description": "Project updated successfully"},
        400: {"description": "Invalid input"},
        401: {"description": "Not authenticated"},
        403: {"description": "Only project admins can update"},
        404: {"description": "Project not found"}
    }
)
async def update_project(
    project_id: str,
    request: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    """
    Update a project's details.

    - **project_id**: Project ID
    """
    # TODO: Update project in database

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project not found"
    )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    responses={
        204: {"description": "Project deleted"},
        401: {"description": "Not authenticated"},
        403: {"description": "Only organization admins can delete projects"},
        404: {"description": "Project not found"}
    }
)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a project and all associated data.

    This action is irreversible.

    - **project_id**: Project ID
    """
    # TODO: Delete project
    pass


@router.get(
    "/{project_id}/stats",
    response_model=ProjectStats,
    summary="Get project statistics",
    responses={
        200: {"description": "Project statistics"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Project not found"}
    }
)
async def get_project_stats(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> ProjectStats:
    """
    Get statistics for a project.

    - **project_id**: Project ID
    """
    # TODO: Calculate project stats

    return ProjectStats(
        total_tasks=0,
        completed_tasks=0,
        in_progress_tasks=0,
        pending_tasks=0,
        total_sessions=0,
        active_sessions=0,
        total_commits=0,
        lines_changed=0
    )


# ============================================================================
# Repository Management Endpoints
# ============================================================================

@router.post(
    "/{project_id}/repository",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Connect a repository",
    responses={
        201: {"description": "Repository connected successfully"},
        400: {"description": "Invalid repository URL or already connected"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Project not found"}
    }
)
async def connect_repository(
    project_id: str,
    request: RepositoryConnect,
    db: AsyncSession = Depends(get_db)
) -> RepositoryResponse:
    """
    Connect a repository to the project.

    The repository will be cloned and synced to the workspace.

    - **project_id**: Project ID
    - **provider**: Repository provider (github, gitlab, bitbucket, local)
    - **url**: Repository URL
    - **branch**: Default branch to track
    - **auto_sync**: Enable automatic sync on push
    """
    # TODO: Validate repository access
    # TODO: Create repository connection

    repo_id = str(uuid4())
    now = datetime.utcnow()

    return RepositoryResponse(
        id=repo_id,
        provider=request.provider,
        url=request.url,
        branch=request.branch,
        status=RepositoryStatus.PENDING,
        auto_sync=request.auto_sync,
        last_synced_at=None,
        last_commit_sha=None,
        last_commit_message=None,
        connected_at=now
    )


@router.get(
    "/{project_id}/repository",
    response_model=RepositoryResponse,
    summary="Get repository details",
    responses={
        200: {"description": "Repository details"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Project or repository not found"}
    }
)
async def get_repository(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> RepositoryResponse:
    """
    Get the connected repository details.

    - **project_id**: Project ID
    """
    # TODO: Fetch repository from database

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Repository not found"
    )


@router.post(
    "/{project_id}/repository/sync",
    response_model=RepositoryResponse,
    summary="Trigger repository sync",
    responses={
        200: {"description": "Sync started"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Repository not found"},
        409: {"description": "Sync already in progress"}
    }
)
async def sync_repository(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> RepositoryResponse:
    """
    Trigger a manual repository synchronization.

    Pulls the latest changes from the remote repository.

    - **project_id**: Project ID
    """
    # TODO: Trigger sync job

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Repository not found"
    )


@router.patch(
    "/{project_id}/repository",
    response_model=RepositoryResponse,
    summary="Update repository settings",
    responses={
        200: {"description": "Repository updated"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Repository not found"}
    }
)
async def update_repository(
    project_id: str,
    branch: Optional[str] = Query(None, description="New default branch"),
    auto_sync: Optional[bool] = Query(None, description="Enable/disable auto sync"),
    db: AsyncSession = Depends(get_db)
) -> RepositoryResponse:
    """
    Update repository settings.

    - **project_id**: Project ID
    - **branch**: New default branch to track
    - **auto_sync**: Enable or disable automatic syncing
    """
    # TODO: Update repository settings

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Repository not found"
    )


@router.delete(
    "/{project_id}/repository",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect repository",
    responses={
        204: {"description": "Repository disconnected"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        404: {"description": "Repository not found"}
    }
)
async def disconnect_repository(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Disconnect the repository from the project.

    The local workspace files will be preserved.

    - **project_id**: Project ID
    """
    # TODO: Disconnect repository
    pass


# ============================================================================
# Project Tasks Endpoints
# ============================================================================

class TaskStatusEnum_API(str, Enum):
    """Task status values for API."""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriorityEnum_API(str, Enum):
    """Task priority values for API."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskSummary(BaseModel):
    """Summary of a task for listing."""
    id: str
    title: str
    status: TaskStatusEnum_API
    priority: TaskPriorityEnum_API
    created_at: datetime


class TaskListSummaryResponse(BaseModel):
    """Response containing list of tasks for a project."""
    items: list[TaskSummary]
    total: int


@router.get(
    "/{project_id}/tasks",
    response_model=TaskListSummaryResponse,
    summary="List tasks for a project",
    responses={
        200: {"description": "List of tasks"},
        401: {"description": "Not authenticated"},
        404: {"description": "Project not found"}
    }
)
async def list_project_tasks(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TaskListSummaryResponse:
    """
    List all tasks for a specific project.

    - **project_id**: Project ID
    """
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

    # Verify project access
    project_result = await db.execute(
        select(Project)
        .where(Project.id == project_uuid)
        .where(Project.org_id.in_(user_org_ids))
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Fetch tasks
    tasks_result = await db.execute(
        select(Task)
        .where(Task.project_id == project_uuid)
        .order_by(Task.created_at.desc())
    )
    tasks = tasks_result.scalars().all()

    items = [
        TaskSummary(
            id=str(task.id),
            title=task.title,
            status=TaskStatusEnum_API(task.status.value),
            priority=TaskPriorityEnum_API(task.priority.value),
            created_at=task.created_at
        )
        for task in tasks
    ]

    return TaskListSummaryResponse(
        items=items,
        total=len(items)
    )
