"""SQLAlchemy ORM models.

Tables
------
episodes   one row per podcast episode (metadata from the transcript header)
chunks     embedded transcript pieces; each points back to its episode
sessions   one row per chat
messages   chat turns (+ the sources and artifact attached to assistant turns)
profile    single-row learner profile used to personalise answers
notes      saved answers / artifacts (the personal library)
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (JSON, Column, Date, DateTime, ForeignKey, Integer, String, Text,
                        UniqueConstraint, Uuid, func)
from sqlalchemy.orm import relationship

from app.db import Base

EMBED_DIM = 768  # nomic-embed-text output size


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(300), nullable=False, unique=True, index=True)  # folder name
    source_file = Column(String(500), nullable=False)
    guest = Column(String(300), nullable=True, index=True)
    title = Column(Text, nullable=False)
    youtube_url = Column(String(500), nullable=True)
    video_id = Column(String(50), nullable=True)
    publish_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chunks = relationship("Chunk", back_populates="episode", cascade="all, delete-orphan")


class Chunk(Base):
    """A retrievable piece of a transcript. Traceable: chunk -> episode -> YouTube."""

    __tablename__ = "chunks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    episode_id = Column(Uuid(as_uuid=True), ForeignKey("episodes.id", ondelete="CASCADE"),
                        nullable=True, index=True)
    source_file = Column(String(500), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    start_seconds = Column(Integer, nullable=True)  # timestamp of the chunk's first line
    embedding = Column(Vector(EMBED_DIM), nullable=False)
    embed_model = Column(String(100), nullable=True)  # settings.embed_tag at ingestion time
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    episode = relationship("Episode", back_populates="chunks")

    __table_args__ = (UniqueConstraint("source_file", "chunk_index", name="uq_chunk_source_index"),)
    # NOTE: a generated `tsv` tsvector column + GIN index for keyword search is
    # created by app.migrate (Postgres-only), not mapped here.


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # 'metadata' is reserved on declarative Base, so the attribute is metadata_.
    metadata_ = Column("metadata", JSON, nullable=True)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    mode = Column(String(30), nullable=True)      # ask | ship30 | explain | quiz | artifact | prd
    sources = Column(JSON, nullable=True)         # citations shown under an assistant answer
    artifact = Column(JSON, nullable=True)        # {type,title,content} rendered in the viewer
    meta = Column(JSON, nullable=True)            # provider, model, latency, retrieval stats
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="messages")


class Profile(Base):
    """Single-user learner profile (id is always 1)."""

    __tablename__ = "profile"

    id = Column(Integer, primary_key=True, default=1)
    display_name = Column(String(100), nullable=True)
    goal = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    known_concepts = Column(JSON, nullable=True)  # list[str]
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)


class Note(Base):
    __tablename__ = "notes"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False)
    kind = Column(String(20), nullable=False, default="note")  # note | markdown | html | answer
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
