# Claude Code: Phase 4, full ingestion (2026-10-13)

* A detached ingest was already running before this session (`docker compose exec -d api sh -c "python -m app.scripts.ingest > /app/transcripts/ingest.log 2>&1"`, started about 22:45). It was left alone, so no second run was started that could race it.
* The first 30 episodes were skipped as already ingested, which confirms resumability.
* Progress lines: `[45/303] ... eta≈457min`, `[50/303] ... eta≈452min`, `[55/303] ... eta≈458min`.
* Rate is about 110 s per episode, embedding-bound on CPU. ETA is **about 7.5 h, finishing around 07:15 on 2026-10-14**.
* At 23:37: 56 episodes, 2,115 chunks, 0 legacy chunks, 0 failed.
* Monitor: `Get-Content transcripts\ingest.log -Tail 5` and `curl.exe http://localhost:8000/health/chunks`.

## Interruptions (2026-10-14/15)
1. The api recreate in Phase 5 killed the run. It was restarted and resumed.
2. A container restart around 01:05 on 10-15 killed it again at 86/303. `docker exec` processes do not survive a restart.
3. The restart at 01:35 died at once with "Cannot connect to Ollama". Ollama on the host had restarted.

Root issue: the run is a one-shot `docker exec`. Also, an Ollama blip in the middle of a run makes every remaining episode fail fast, and the script exits 3 with nothing ingested after that point.

## Fix (no code change)
* Wrapped the documented command in a capped retry loop. Each re-run skips finished episodes in seconds:
  `docker compose exec -d api sh -c 'for i in $(seq 50); do python -m app.scripts.ingest && break; echo --- attempt $i failed, retrying in 60s; sleep 60; done >> /app/transcripts/ingest.log 2>&1'`
* Failed attempt: the first version had double quotes inside the `sh -c` script. Windows PowerShell 5.1 strips them when calling native exes, so the loop never started. Removing the inner quotes fixed it.
* Kept the machine awake through the app, and started a background watcher that polls `/health/chunks` every 5 min.
* Hardware ceiling: i5-8250U (4 cores), 16 GB RAM, CPU-only Ollama, so about 110 s per episode. Chatting in the UI at the same time slows the ingest down.
