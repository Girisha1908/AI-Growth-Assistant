"""Skill registry. Adding a skill = one module with `NAME` and `async run(ctx)`,
plus one line here and one rule in agent/router.py."""

from app.agent.skills import artifact, ask, explain, prd, quiz, ship30

SKILLS = {m.NAME: m for m in (ask, explain, quiz, ship30, artifact, prd)}
