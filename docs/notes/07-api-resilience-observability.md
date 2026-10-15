# Phase 7: API, failures, logs

**Status:** done and tested.

## Contract
Every error is `{"error": {"code", "message", "hint"}}`. Examples: `provider_unavailable` (503), `provider_timeout` (504), `provider_not_configured` (400), `database_unavailable` (503), `session_not_found` (404).

## Resilience rules
* Persist a turn only after success, so retry never duplicates.
* DB down at startup: API still starts; `/health` says `degraded`.
* No automatic cloud fallback (cost and privacy surprise).

## Observability
One JSON log line per event with a `request_id`: `route`, `retrieval`, `llm_call`, `artifact_generated`. Trace a slow answer: was it retrieval ms or model ms?

## Interview questions
1. How do you make failures actionable? (code + hint) 2. What would you add for production? (Alembic, auth, rate limits, metrics, tracing)
