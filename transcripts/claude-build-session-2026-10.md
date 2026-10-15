# Build session: Claude chat (rebuild, docs and learning notes)

> Made in a Claude chat session, in parallel with the earlier Antigravity sessions in this folder. No secrets were shared. Environment: Claude's sandbox (Python 3.12, Node 22, Postgres 16 + pgvector installed via apt). No Docker, no Ollama, no browser.

## Sequence, including failures and fixes
| Step | What happened | Outcome |
|---|---|---|
| Audit | Cloned the GitHub repo; main had no artifact work (local-only, uncommitted) | Plan: rebuild artifacts inside a new agent layer |
| Data check | 303 transcripts; all have `Speaker (HH:MM:SS):` timestamps; header coverage 300-303 | Citations can deep-link to the second |
| Dependency | Installing `claude-agent-sdk` upgraded starlette and broke FastAPI's pin (`pip` warning) | Pinned `starlette>=0.40,<0.42`; `pip check` clean |
| Tooling mistake | `pkill -f` matched my own shell and killed it, twice | Switched to bracket patterns in separate calls |
| Test timeout | Whole suite hung for 300 s. Bisected per file, `faulthandler` showed the hang in `init_db`; `pg_locks` showed a test session holding a lock while `ALTER TABLE … IF NOT EXISTS` waited for an exclusive one | Rewrote migrations to check the catalog first, with `lock_timeout`; added a legacy-schema upgrade test |
| Wrong test expectation | A context-free follow-up in a new session was (correctly) refused, so the fake provider got no call | Changed the test to assert the refusal |
| Sandbox restart | Postgres stopped when a shell was killed | Restarted cluster; suite green (76 tests) |
| Smoke test | Stub Ollama + 40 real episodes (1,550 chunks): ask, Ship 30 (7 calls), HTML artifact, history, logs all worked | Pipeline verified; **quality not measured** |

## Not verified
Real Ollama/Claude output, Docker build, UI in a browser, ingestion speed, threshold calibration, Claude Agent SDK path.
