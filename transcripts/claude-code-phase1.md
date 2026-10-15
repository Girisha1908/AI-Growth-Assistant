# Claude Code: Phase 1, prerequisites (2026-10-13)

## Checks
| Check | Result |
|---|---|
| Docker engine | 29.6.1 (client and server), Compose v5.3.0 |
| Ollama on host | reachable, v0.34.0 |
| `llama3.2:3b` | present (3.2B Q4_K_M) |
| `nomic-embed-text` | present (768-dim) |

No installs or model pulls were needed.

## State found
* The stack was already up (db, api healthy, frontend; about 30 min).
* `/health` returned `status: ok`, provider `ollama` reachable, both models installed.
* An ingest was already running in the api container (`python -m app.scripts.ingest`, writing `transcripts/ingest.log`, started about 32 min earlier). `/health/chunks` showed 47 episodes, 1,795 chunks, `legacy_chunks_without_metadata: 0`.
* Log ETA from its first lines was about 430 to 476 min (roughly 100 s per episode).

## Issues
* The project had no `CLAUDE.md`. The user supplied one and it was saved to the repo root.
* The folder is not a git repository, so committing needs a decision (see the session).
* A first command was rejected because it used Git Bash. Switched to PowerShell with `curl.exe`, as `CLAUDE.md` requires.
