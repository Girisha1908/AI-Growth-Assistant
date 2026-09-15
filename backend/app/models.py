"""SQLAlchemy ORM models for chat sessions and messages.

Only two tables are defined for the initial skeleton:
1. sessions: tracks conversation sessions with timestamps and metadata.
2. messages: tracks message history belonging to a session.
"""

import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
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
