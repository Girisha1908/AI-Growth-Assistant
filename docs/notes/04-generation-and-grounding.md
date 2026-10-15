# Phase 4: Prompts, grounding, citations

**Status:** done; real answer quality needs your Ollama run.

## Prompt shape
```
system: rules (only excerpts, cite [n], refuse sentence, no invented quotes)
history: last 6 turns (clipped)
user:   numbered excerpts [1]..[n] + question
```

## Citations without trust
The model writes `[1]`. The **source cards come from database rows**, not model text. If the model lies about a number, the UI ignores it (only existing `[n]` become chips).

## Context window trap
Ollama truncates prompts beyond `num_ctx`. 4 chunks need about 3–4k tokens, so we request 8192.

## Small-model reality
`llama3.2:3b` is hedgy and shorter. We design around it (sectioned essays, strict rules) and say so in the docs.

## Interview questions
1. How do you prevent hallucination? (gate, strict prompt, DB-built citations, show excerpts) 2. What is the context window and why does it matter? 3. How do you evaluate answers? (eval set M1–M3; human spot checks)
