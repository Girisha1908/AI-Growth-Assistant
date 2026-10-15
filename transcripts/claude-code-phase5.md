# Claude Code: Phase 5, evaluation (2026-10-14)

## Failed attempt 1
`python eval/run_eval.py` stopped on question 3 with `/search -> HTTP 503 embedding_unavailable: Ollama embedding request timed out`.

* Cause: `embed_query` had a hard-coded 30 s timeout. Ollama serves embed calls one at a time, so during ingestion a query waits behind a 16-chunk batch (about 40 s on this CPU). Afterwards the api logs showed searches taking 45 to 60 s.
* Fix: `backend/app/embeddings.py` now gives queries 180 s, the same budget as document batches. The api was recreated with `docker compose up -d --build` and the ingest was restarted detached; it resumed. Tests re-run: backend 76/76, frontend 14/14.
* This also fixes random chat failures while ingestion runs, which the README says is supported.

## Run 2 (baseline, no tuning). Corpus 68 episodes, threshold 0.45, top_k 4, retrieval-only
| Metric | Result | Target |
|---|---|---|
| M1 grounded-answer rate | 100% (30/30) | >= 90% |
| M2 correct-refusal rate | 90% (9/10) | 100% |
| M3 citation validity | 98% (120/122) | 100% |

The run took about 25 min because every query queues behind ingestion.

## Analysis of the misses
* **M2:** "What is the boiling point of water on Mount Everest?" was answered. Its best distance was 0.435, and 0.4156 on a re-check with more episodes, both just under the 0.45 gate. The hits are mountain-climbing anecdotes from growth episodes (Andy Johns and others). As the corpus grows, more such near-misses are likely.
* **M3:** 2 of 122 sources were counted invalid. The harness requires `episode_id` to be in a list snapshot taken at the start **and** `url` to start with `http`. There are two candidate causes:
  1. Episode `daniel-lereya` has `youtube_url: ''` and `video_id: ''` in the source transcript itself. Its citations are real but have no link, so the harness fails them. No URL can be recovered from the data.
  2. The episode list is snapshotted once at the start of a 25-minute run while ingestion keeps adding episodes. A citation from a newly ingested episode counts as invalid.
## Decisions (user)
* **M2:** no tuning yet. Re-run the eval at 303/303 episodes, because distances shift as the corpus grows. If it still fails, try 0.42 and then 0.40, and show before/after M1 and M2 before keeping any change.
* **M3:** fix only the harness race. `eval/run_eval.py` now collects sources during the run and checks them against an episode list fetched **after** the run. The strict URL check stays. The missing link for `daniel-lereya` is a source-data gap and will be documented in `docs/prd.md` if it still shows up in the final run.
* Verified: the script compiles, and the new paging loop ends (84 episodes in 1 page).
