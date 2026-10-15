# Phase 9: Tests and evaluation

**Status:** 76 backend + 14 frontend tests passing; eval harness works (needs your real Ollama run for numbers).

## Two kinds of checking
| Kind | Question | Tool |
|---|---|---|
| Software tests | Does the code do what we intended? | pytest, vitest (fake model, fake embeddings) |
| Evaluation | Is the AI good? | `eval/run_eval.py` (30 in-corpus + 10 out-of-corpus questions) |

Like ML: unit tests = code correctness, eval set = model accuracy on held-out data.

## Metrics
M1 grounded rate ≥ 90% · M2 refusal rate 100% · M3 citation validity 100% · M4 latency.

**Key rule:** re-run the eval after any change to chunking, embeddings, threshold or prompts.

## Interview questions
1. How do you test an LLM app? 2. Why use fakes in unit tests? (deterministic, free, fast)
