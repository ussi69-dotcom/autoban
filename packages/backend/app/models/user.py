"""User model with OAuth fields."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.audit import AuditLog
    from app.models.organization import OrgMember
    from app.models.project import Project
    from app.models.session import Session
    from app.models.task import Task


class User(Base):
    """User model with OAuth support."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # OAuth fields
    oauth_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    oauth_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # API key for programmatic access
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    org_memberships: Mapped[list["OrgMember"]] = relationship(
        "OrgMember",
        back_populates="user",
        foreign_keys="OrgMember.user_id",
        cascade="all, delete-orphan",
    )
    created_projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="created_by_user",
        foreign_keys="Project.created_by",
    )
    created_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="created_by_user",
        foreign_keys="Task.created_by",
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        foreign_keys="Session.user_id",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        foreign_keys="AuditLog.user_id",
    )
    invitations_sent: Mapped[list["OrgMember"]] = relationship(
        "OrgMember",
        back_populates="inviter",
        foreign_keys="OrgMember.invited_by",
    )

    __table_args__ = (
        Index("idx_users_oauth", "oauth_provider", "oauth_id"),
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
