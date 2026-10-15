"""The personal library: saved answers, essays and artifacts."""

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import Note

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    kind: Literal["note", "markdown", "html", "answer"] = "note"
    content: str = Field(min_length=1, max_length=300_000)
    sources: Optional[list[dict[str, Any]]] = None


class NoteOut(NoteIn):
    id: uuid.UUID
    created_at: datetime


def _out(n: Note) -> NoteOut:
    return NoteOut(id=n.id, title=n.title, kind=n.kind, content=n.content, sources=n.sources,
                   created_at=n.created_at)


@router.get("", response_model=list[NoteOut])
def list_notes(db: Session = Depends(get_db)):
    return [_out(n) for n in db.query(Note).order_by(Note.created_at.desc()).all()]


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(body: NoteIn, db: Session = Depends(get_db)):
    n = Note(title=body.title.strip(), kind=body.kind, content=body.content, sources=body.sources)
    db.add(n)
    db.commit()
    db.refresh(n)
    return _out(n)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: uuid.UUID, db: Session = Depends(get_db)):
    n = db.get(Note, note_id)
    if not n:
        raise AppError("note_not_found", "Note not found", 404)
    db.delete(n)
    db.commit()
