# Phase 10: Deploy, handoff, demo

**Status:** compose and docs written; you run the real thing.

## Checklist
1. Fresh clone → README steps only → working chat.
2. Ingest all episodes (overnight if needed).
3. Run `eval/run_eval.py`; paste results in PRD.
4. Record 2–3 min video: problem → product → Ollama running locally → one trade-off.
5. Push `transcripts/` logs (redact secrets) and submit.

## Trade-off to say on camera
"The brief wants a cloud agent SDK and a local Ollama demo. I put one `LLMProvider` interface between the agent and the models, so the router and skills never know which model runs. The cost: the SDK path is only code-verified."
