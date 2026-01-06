"""ProjectMemory model with pgvector embedding."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# pgvector support - Vector type for embeddings
try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False
    Vector = None

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task import Task


class ProjectMemory(Base):
    """Project memory model for agent knowledge base with vector embeddings."""

    __tablename__ = "project_memory"

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

    # Memory identification
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Vector embedding for semantic search (1536 dimensions for OpenAI embeddings)
    # Using raw column definition to support pgvector when available
    if VECTOR_AVAILABLE:
        embedding: Mapped[Optional[list[float]]] = mapped_column(
            Vector(1536),
            nullable=True,
        )
    else:
        # Fallback for environments without pgvector
        embedding = mapped_column(
            Text,
            nullable=True,
            comment="JSON-encoded embedding vector (pgvector not available)",
        )

    # Source tracking
    source_task_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(
        Float,
        server_default=text("1.0"),
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="memories",
    )
    source_task: Mapped[Optional["Task"]] = relationship(
        "Task",
        back_populates="source_memories",
    )

    __table_args__ = (
        UniqueConstraint("project_id", "memory_type", "key", name="uq_project_memory_type_key"),
        Index("idx_memory_project_type", "project_id", "memory_type"),
        # Note: ivfflat index for embeddings should be created via migration
        # CREATE INDEX idx_memory_embedding ON project_memory
        #     USING ivfflat (embedding vector_cosine_ops);
    )

    def __repr__(self) -> str:
        return f"<ProjectMemory {self.memory_type}:{self.key}>"
