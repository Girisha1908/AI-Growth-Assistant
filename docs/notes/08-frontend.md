# Phase 8: Frontend

**Status:** builds and unit-tested; manual plan in `testing.md`.

## Structure
`hooks/` state (chat, status, theme) · `lib/` pure logic (api, sandbox, text) · `components/` UI. Layout copies Claude: sidebar, centred chat, one composer, artifact panel on the right. Less on screen = less to distrust.

## Choices
Server is source of truth; optimistic user bubble; Stop uses `AbortController`; ask-mode sends `auto`; fonts and icons bundled (works offline).

## Interview questions
1. How do you show uncertainty to users? (refusal card, similarity, excerpts) 2. How do you keep the artifact viewer safe? (phase 6)
