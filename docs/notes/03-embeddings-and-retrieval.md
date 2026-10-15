# Phase 3: Embeddings, hybrid search, the gate

**Status:** done and tested on real Postgres.

## Embeddings (you know this part)
`nomic-embed-text` turns text into 768 numbers. **Cosine distance** = 1 − similarity. Small = similar meaning.

## Why hybrid?
| Search | Good at | Bad at |
|---|---|---|
| Vector | meaning ("keep users" ≈ retention) | exact names/terms ("RICE", "Chesky") |
| Keyword (Postgres full-text) | exact words | synonyms |

We fuse both with **Reciprocal Rank Fusion**: score = Σ 1/(60 + rank). It uses ranks, so different score scales combine fairly.

## The gate (most important idea)
```
best vector distance > 0.45 ?  → refuse, don't call the model
```
A small model given weak context will answer anyway. Not asking it is the safest fix.

## Other details
* Max 2 chunks per episode, so one episode cannot fill every slot.
* Short follow-ups ("what about week one?") are searched with the previous question.
* Optional task prefixes (`search_query:`) are **off**, because the 0.45 threshold was tuned without them. Change one thing at a time, then re-run `eval/run_eval.py`.

**Key rule:** embed queries and chunks with the same model and settings.

## Interview questions
1. What is RRF? 2. How did you choose the threshold? (measured relevant ≈ 0.34–0.41, irrelevant > 0.46; re-check with the eval set) 3. Where does hybrid search fail? (OR keyword query, no IDF)
