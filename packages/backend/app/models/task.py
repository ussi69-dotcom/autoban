"""Task model with status and priority enums."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.agent import AgentInstance
    from app.models.memory import ProjectMemory
    from app.models.project import Project
    from app.models.session import Session
    from app.models.user import User
    from app.models.worktree import Worktree


class TaskStatus(str, enum.Enum):
    """Task status enum."""

    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    """Task priority enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    """Task model for kanban board."""

    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_task_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Task details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", create_type=False, values_callable=lambda e: [x.value for x in e]),
        server_default=text("'todo'"),
        nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority", create_type=False, values_callable=lambda e: [x.value for x in e]),
        server_default=text("'medium'"),
        nullable=False,
    )

    # Agent assignment
    recommended_profile: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    assigned_agent_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_instances.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Metadata
    labels: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        server_default=text("'{}'"),
        nullable=False,
    )
    estimated_mins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_mins: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Git integration
    branch_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pr_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Ownership
    created_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=datetime.utcnow,
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="tasks",
    )
    parent_task: Mapped[Optional["Task"]] = relationship(
        "Task",
        back_populates="subtasks",
        remote_side="Task.id",
    )
    subtasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="parent_task",
        cascade="all, delete-orphan",
    )
    assigned_agent: Mapped[Optional["AgentInstance"]] = relationship(
        "AgentInstance",
        back_populates="assigned_tasks",
        foreign_keys=[assigned_agent_id],
    )
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="created_tasks",
        foreign_keys=[created_by],
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="task",
    )
    worktrees: Mapped[list["Worktree"]] = relationship(
        "Worktree",
        back_populates="task",
    )
    source_memories: Mapped[list["ProjectMemory"]] = relationship(
        "ProjectMemory",
        back_populates="source_task",
    )

    __table_args__ = (
        Index("idx_tasks_project_status", "project_id", "status"),
        Index("idx_tasks_parent", "parent_task_id"),
        Index("idx_tasks_assigned_agent", "assigned_agent_id"),
    )

    def __repr__(self) -> str:
        return f"<Task {self.title[:50]}>"
