"""SQLAlchemy ORM models for chat sessions, messages, and transcript chunks.

Tables:
1. sessions: tracks conversation sessions with timestamps and metadata.
2. messages: tracks message history belonging to a session.
3. chunks: stores embedded transcript chunks for RAG retrieval.
"""

import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, func, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db import Base


class Session(Base):
    """Represents an interactive user chat session."""

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Note: 'metadata' is a reserved attribute on SQLAlchemy Base (Base.metadata).
    # We name the python attribute 'metadata_' while explicitly mapping it to the column name "metadata" in PostgreSQL.
    metadata_ = Column("metadata", JSON, nullable=True)

    # Relationship to messages
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    """Represents an individual message exchanged within a chat session."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship back to session
    session = relationship("Session", back_populates="messages")


class Chunk(Base):
    """Stores an embedded transcript chunk for RAG retrieval.

    Each chunk traces back to its source file and position, enabling
    citation of the original episode when surfacing answers.
    """

    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Relative path within the transcript repo, e.g. "episodes/brian-chesky/transcript.md"
    source_file = Column(String(500), nullable=False, index=True)
    # Position of this chunk within its source file (0-indexed)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    # 768 dimensions matches nomic-embed-text output
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("source_file", "chunk_index", name="uq_chunk_source_index"),
    )

