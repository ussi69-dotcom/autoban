"""Session model with messages JSONB."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.agent import AgentInstance
    from app.models.project import Project
    from app.models.task import Task
    from app.models.user import User


class Session(Base):
    """Session model for agent conversations."""

    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    agent_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_instances.id", ondelete="SET NULL"),
        nullable=True,
    )
    task_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Session state
    status: Mapped[str] = mapped_column(
        String(50),
        server_default=text("'active'"),
        nullable=False,
    )
    messages: Mapped[list] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    tool_calls: Mapped[int] = mapped_column(
        Integer,
        server_default=text("0"),
        nullable=False,
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        server_default=text("0"),
        nullable=False,
    )

    # Parent session for sub-sessions
    parent_session_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    agent: Mapped[Optional["AgentInstance"]] = relationship(
        "AgentInstance",
        back_populates="sessions",
    )
    task: Mapped[Optional["Task"]] = relationship(
        "Task",
        back_populates="sessions",
    )
    project: Mapped[Optional["Project"]] = relationship(
        "Project",
        back_populates="sessions",
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="sessions",
    )
    parent_session: Mapped[Optional["Session"]] = relationship(
        "Session",
        back_populates="child_sessions",
        remote_side="Session.id",
    )
    child_sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="parent_session",
    )

    __table_args__ = (
        Index("idx_sessions_agent", "agent_id"),
        Index("idx_sessions_task", "task_id"),
        Index("idx_sessions_project", "project_id"),
        Index("idx_sessions_user", "user_id"),
        Index("idx_sessions_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Session {self.id} ({self.status})>"
