"""Worktree model for git worktree management."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.project import Repository
    from app.models.task import Task


class Worktree(Base):
    """Git worktree model for isolated development environments."""

    __tablename__ = "worktrees"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    repo_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Worktree details
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    base_commit: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        server_default=text("'active'"),
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    merged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="worktrees",
    )
    task: Mapped[Optional["Task"]] = relationship(
        "Task",
        back_populates="worktrees",
    )

    __table_args__ = (
        Index("idx_worktrees_repo", "repo_id"),
        Index("idx_worktrees_task", "task_id"),
        Index("idx_worktrees_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Worktree {self.branch_name} ({self.status})>"
