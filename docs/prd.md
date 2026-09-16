# Product Requirements Document (PRD) — Lenny Growth Assistant

## Scope Choices & Assumptions

- **Cloud Provider (Claude) Testing**: We built and unit-verified the cloud provider (`ClaudeProvider` against Anthropic's Messages API) but did not pay for live API testing given the time constraint; the pluggable architecture proves provider-swapping works seamlessly via the local Ollama path.
- **Transcript Ingestion Scope**: Ingested a representative subset of 100/303 episodes due to initial time constraints; the architecture supports full ingestion by re-running the ingest script with the cap removed.
