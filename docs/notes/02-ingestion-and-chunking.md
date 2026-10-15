# Phase 2: Ingestion and chunking

**Status:** code done and tested; full 303-episode run is yours (needs Ollama).

## Pipeline
```
transcript.md → parse YAML header → paragraphs (+ timestamps) → ~500-word chunks (50 overlap)
             → batch embed (16 at a time) → one transaction per episode
```

## Why chunk?
A whole episode (about 15k words) is too big for one embedding or prompt, and one vector for it would be a blurry average. About 500 words keeps one idea per vector.

## Why overlap?
A sentence cut at a boundary still appears whole in one of the two chunks.

## Design choices
| Choice | Reason |
|---|---|
| Keep speaker labels | "Lenny asked…" vs the guest answering matters for quotes |
| Store `start_seconds` | Citations link to the exact moment |
| Episode-atomic writes | No half-ingested episodes; safe to Ctrl+C and resume |
| Skip up-to-date episodes | Resumable; `--force` to redo |
| Batch embedding | One HTTP call per 16 chunks instead of 16 |

**Key rule:** never mix embedding setups in one table (tracked by `embed_model`).

## Numbers
303 episodes, about 11.7k chunks (dry run on real data). Median chunk is 450 words.

## Interview questions
1. How do you pick chunk size? (try, then measure with the eval set) 2. How do you refresh the index? 3. What if one episode fails? (rolled back, reported, run continues)
