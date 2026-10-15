"""Learner profile (single user). Used to tailor analogies and level."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Profile

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileIn(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=100)
    goal: Optional[str] = Field(default=None, max_length=500)
    background: Optional[str] = Field(default=None, max_length=1000)
    known_concepts: list[str] = Field(default_factory=list, max_length=40)


class ProfileOut(ProfileIn):
    updated_at: Optional[datetime] = None


def _out(p: Optional[Profile]) -> ProfileOut:
    if not p:
        return ProfileOut()
    return ProfileOut(display_name=p.display_name, goal=p.goal, background=p.background,
                      known_concepts=p.known_concepts or [], updated_at=p.updated_at)


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    return _out(db.get(Profile, 1))


@router.put("", response_model=ProfileOut)
def put_profile(body: ProfileIn, db: Session = Depends(get_db)):
    p = db.get(Profile, 1) or Profile(id=1)
    p.display_name = (body.display_name or "").strip() or None
    p.goal = (body.goal or "").strip() or None
    p.background = (body.background or "").strip() or None
    p.known_concepts = [c.strip()[:80] for c in body.known_concepts if c.strip()]
    db.add(p)
    db.commit()
    db.refresh(p)
    return _out(p)
