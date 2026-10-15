# PRD: The Lenny Growth Assistant

| | |
|---|---|
| **Author** | Girisha |
| **Status** | Draft v1 (October 2026) |
| **Repo** | `Girisha1908/AI-Growth-Assistant` |
| **Related docs** | `architecture.md`, `design.md`, `testing.md`, `README.md` |

---

## 1. Discovery brief

### 1.1 User and problem

**Primary user.** A product, growth or engineering practitioner who is early in their career. They are building judgment in product and growth, and they learn from Lenny's Podcast. This is the "internal team member" in the engagement scenario, with a learner's habits.

**Job to be done.** "When I have a product or growth question, give me an answer I can trust from real operators, show me exactly where it came from, and help me turn it into something I can reuse (a note, an essay, a one-pager)."

**Pain today**

| Pain | Why it hurts |
|---|---|
| 300+ long episodes (about 4.6M words of transcript) | Nobody can search or recall them by memory |
| Keyword search on YouTube or a podcast app | It matches words, not ideas, and returns no synthesis |
| Generic chatbots | They answer from training data, can't say which episode a claim came from, and invent quotes |
| Reading is passive | Insights are lost unless turned into notes or writing |

**What the assistant removes.** Search, synthesis and first-draft writing are done in one place, with every claim traceable to an episode. When the transcripts don't cover a question, it says so instead of guessing.

### 1.2 Success metrics

Targets are proposals. They are measured against a fixed evaluation set (see section 7, AC-12) so they can be re-run after every change.

| # | Metric | Type | Target |
|---|---|---|---|
| M1 | **Grounded-answer rate**: share of in-corpus eval questions whose answer cites at least one relevant episode | Product quality | ≥ 90% (30-question set) |
| M2 | **Correct-refusal rate**: share of out-of-corpus questions answered with the "not in the transcripts" message | Trust | 100% (10-question set) |
| M3 | **Citation validity**: share of displayed citations whose episode actually contains the cited chunk | Trust | 100% (by construction, verified by test) |
| M4 | **Time to first token / answer** on the local demo model | Operational | median ≤ 30 s for chat (hardware-dependent, reported honestly) |
| M5 | **Fresh-clone setup time** to a working chat, excluding ingestion | Operational | ≤ 15 min following only the README |
| M6 | **Corpus coverage** | Operational | 303 / 303 episodes indexed |
| M7 | **Artifact safety**: sandbox-escape test cases that succeed | Security | 0 |

### 1.3 Assumptions

The client brief is incomplete, so these are the assumptions made.

1. The user base is small and internal. There is no login, and one browser session is one user.
2. Public transcripts from `ChatPRD/lennys-podcast-transcripts` are the only knowledge source. They are public, so there is no confidential-data risk in the corpus.
3. Evaluators run the demo on a laptop with about 16 GB RAM and no GPU, which is why a small model (`llama3.2:3b`) is the default.
4. A cloud key may not be available to the evaluator. The local path must therefore work end to end with zero paid services.
5. "Strictly from transcripts" means the assistant must refuse rather than fall back on general model knowledge.
6. Answer quality from a 3B model will be below a frontier cloud model. This is accepted and disclosed, not hidden.
7. Transcript YAML headers (guest, title, YouTube URL, publish date, keywords) are reliable enough to use for citations. *(Checked across all 303 files: guest and keywords 303/303, title 302, duration 302, YouTube URL 301, publish date 300. Missing fields fall back gracefully.)*

### 1.4 Scope choices

| Area | Included | Excluded (and why) |
|---|---|---|
| Knowledge | All 303 episodes, chunked, embedded and traceable to guest, title, link | Newsletter content (not requested) |
| Retrieval | Vector search plus keyword (hybrid) search, with a relevance threshold | Reranker model, since extra latency and complexity for a 3B-model demo |
| Chat | Grounded Q&A, follow-ups, citations, refusals | Streaming tokens (P2), since it adds frontend complexity |
| Content | Ship 30 for 30 skill, Markdown and HTML artifacts | PDF export (P2) |
| Models | Ollama (mandatory) and Claude (code-verified) behind one interface | Fine-tuning. RAG is cheaper, auditable and needs no GPU |
| Personalisation | Learner profile, explain-simply mode, quiz mode, saved notes | Multi-user accounts and auth, since single-user is enough for this scope |
| Ops | Docker Compose, structured logs, health checks, graceful failures | Live cloud deployment. The brief asks for a locally runnable, evaluator-reproducible system |

### 1.5 Risks and trade-offs

| Risk | Impact | Mitigation | Residual |
|---|---|---|---|
| **Hallucination** | False claims presented as Lenny's guests' views | Strict system prompt, similarity threshold gate (refuse before calling the LLM), citations built from retrieved chunks, never from model output | Small model may still paraphrase loosely. Surface the source chunk text in the UI so users can check |
| **Retrieval misses names and exact terms** | Pure vector search blurs "Brian Chesky" or "RICE" | Hybrid keyword plus vector search | Needs tuning on the eval set |
| **Latency** | The 3B model on CPU is slow. Long essays have taken minutes | Show loading state, timeouts, shorter default essay target on local models | Demo must tolerate waits and say so |
| **Local-model quality** | Essays fall short of 1,250 words (595 observed) | Document the limit, make the target configurable, and offer the cloud provider for full-length output | Accepted trade-off |
| **Cost** | Cloud calls cost money | Local is the default. Cloud is opt-in via env var. No silent auto-fallback to cloud | None for the default path |
| **Data leakage** | Notes and profile are private. Transcripts are public | Single-user local storage, no third-party analytics, secrets only in `.env`, `.env` gitignored | Local machine security is the user's responsibility |
| **Unsafe artifact rendering** | Model-generated HTML may contain scripts or exfiltration | Sandboxed iframe via `srcdoc`, no `allow-same-origin`, scripts off by default, Markdown rendered with a sanitiser | Documented in `architecture.md` |
| **Embedding-model mismatch** | Changing the embedding model silently breaks search | Record the embed model and dimension per chunk, and refuse to query on mismatch | Re-ingest required if the model is changed |
| **Partial or inconsistent corpus** | Half-ingested data gives misleading coverage | `/health/chunks` reports episode and chunk counts, and ingestion is resumable and idempotent | None once M6 is met |

---

## 2. Product overview

A conversational web app over Lenny's Podcast transcripts. It answers with citations, writes Ship 30 for 30 style essays, and generates Markdown or HTML artifacts that render beside the chat. It runs fully locally on Ollama, and Claude can be switched in through configuration with no code change.

### 2.1 Current state (audited 12 Oct 2026)

| Capability | State |
|---|---|
| Docker Compose stack (Postgres + pgvector, FastAPI, Vite) | Done |
| Ingestion pipeline | Done. 100 of 303 episodes loaded; episode headers are currently discarded |
| Retrieval plus `/chat` with citations and refusal | Done |
| Sessions, history, follow-up handling | Done |
| `LLMProvider` with Ollama and Claude | Done. Claude verified at code level only |
| Ship 30 skill | Done. 595 words on 3B model |
| Artifact generation | Rebuilt in `app/agent`; covered by automated tests |
| Frontend | Rebuilt (chat, modes, citations, artifact viewer, transcripts, library, profile) |
| design.md, tests, full PRD, demo video | Not done |

---

## 3. Features

| ID | Feature | Priority | State |
|---|---|---|---|
| F1 | Grounded Q&A with citations and refusal | P0 | Done |
| F2 | Multi-turn sessions with history | P0 | Done |
| F3 | Provider toggle (Ollama / Claude), shown in UI | P0 | Backend done, UI pending |
| F4 | Ship 30 for 30 essay skill | P0 | Backend done, UI pending |
| F5 | Artifact generation and sandboxed viewer | P0 | Backend unverified, viewer pending |
| F6 | Rich citations: guest, episode title, YouTube link, date | P0 | New |
| F7 | Full ingestion of 303 episodes | P0 | New |
| F8 | Health and status indicators in UI | P0 | Backend done, UI pending |
| F9 | Hybrid retrieval (vector plus keyword) | P1 | New |
| F10 | Learner profile (goal, background) used to tailor answers | P1 | New |
| F11 | Explain-simply mode | P1 | New |
| F12 | Quiz-me mode built from retrieved transcript content | P1 | New |
| F13 | Save artifact / answer to notes library | P1 | New |
| F14 | Transcripts browser tab | P1 | New |
| F15 | PRD Architect mode | P2 | Optional |
| F16 | Artifact export to PDF | P2 | Optional |
| F17 | Streaming responses | P2 | Optional |

---

## 4. User flows

### Flow A: Ask a question
1. User opens the app and clicks **New chat**, which creates a session.
2. User types a question in **Ask** mode.
3. System embeds the question, runs hybrid retrieval, and applies the relevance gate.
4. If chunks pass, the LLM answers only from them. The reply shows the answer plus citation cards (guest, episode, link).
5. If nothing passes, the reply is the refusal message with no citations.

### Flow B: Follow-up
The user asks "what about the first week?" The system combines recent turns with the new message for retrieval and sends the last 6 messages to the model.

### Flow C: Ship 30 essay
1. User switches to **Ship 30** mode and enters a topic.
2. System retrieves chunks and builds a prompt that encodes the Ship 30 principles (hook, "for who / so that", one idea, 1-3-1 rhythm, skimmable format, grounded claims, actionable takeaway).
3. The essay appears as a Markdown artifact in the viewer, with a word count and sources.

### Flow D: Artifact
1. User asks for a "markdown summary" or "HTML card".
2. System detects the artifact intent, retrieves chunks, and generates content.
3. The chat shows a short message plus an "Open artifact" card. The viewer shows Rendered / Source tabs.
4. HTML renders only inside the sandboxed iframe.

### Flow E: Switch model
The evaluator edits `LLM_PROVIDER` in `.env` and restarts the API. The header chip shows the active provider.

### Flow F: Failure handling

| Failure | Behaviour |
|---|---|
| Ollama not running | Clear error message in chat, health chip turns red, no crash |
| Cloud key missing | Clear configuration error, with a pointer to `.env.example` |
| Model timeout | Timeout message, the user's message is kept, retry offered |
| Database down | `/health` reports degraded, the API returns structured 503 |
| Empty retrieval | Refusal message, never an LLM guess |

**Fallback policy:** there is no automatic cloud fallback. Silently sending data to a paid external service would be a surprise, so the user switches providers explicitly.

### Flow G: Learner features (P1)
Set a profile, pick **Explain simply** to get analogies tied to the profile, pick **Quiz me** for questions drawn from the retrieved episodes, and save any answer or artifact to **Notes**.

---

## 5. Functional requirements

**Backend**
- FastAPI with typed request and response models, validation, and structured error bodies `{error: {code, message}}`.
- Agent layer through the Anthropic Claude Agent SDK on the cloud path and an equivalent adapter on the local path, behind one `LLMProvider` interface.
- PostgreSQL stores sessions (with timestamps and user metadata), messages, episodes, chunks and notes.
- `/health` reports API, DB and active provider. `/health/chunks` reports episode and chunk counts.

**Frontend**
- Chat pane with session start, a mode switcher (Ask / Ship 30 / later modes) and a composer.
- Artifact viewer beside the chat, with Rendered and Source views.
- Light and dark themes per the "Starry Night" design system.

**Knowledge base**
- Load from the transcript repo, parse the YAML header into an `episodes` row, chunk the body, embed with the configured embedding model, and store with episode and chunk position.
- Refresh by re-running ingestion, which is idempotent per episode.

---

## 6. Non-functional requirements

| Area | Requirement |
|---|---|
| Reproducibility | `cp .env.example .env && docker compose up --build` works from a fresh clone |
| Observability | JSON structured logs with request IDs, and separate log events for retrieval, model call, DB and artifact render |
| Resilience | All failure modes in Flow F handled without a 500 |
| Security | No secrets in git, sandboxed HTML, CORS limited to the frontend origin |
| Accessibility | Keyboard-operable controls, visible focus, labelled inputs, sufficient contrast in both themes |
| Responsiveness | Usable at mobile, tablet and desktop widths. The artifact panel becomes a slide-over on small screens |

---

## 7. Acceptance criteria

| ID | Criterion | Verified by |
|---|---|---|
| AC-1 | `POST /sessions` returns a new session ID. Two sessions never share history | API test |
| AC-2 | An in-corpus question returns an answer plus at least one citation with guest, title and URL | API test and eval set |
| AC-3 | An out-of-corpus question returns the refusal text with an empty citation list, and the LLM is not called | API test |
| AC-4 | A follow-up in the same session uses prior context. The same text in a new session does not | API test |
| AC-5 | Messages and timestamps persist across an API restart | Persistence test |
| AC-6 | Changing `LLM_PROVIDER` changes the provider with no code change. `/health` and the UI show it | Config test and manual test |
| AC-7 | With Ollama stopped, `/chat` returns a structured error, not a 500 | Resilience test |
| AC-8 | Ship 30 output contains a hook, headings, bullets, bolded emphasis and a takeaway. Word count is reported honestly | Manual check and unit test of the prompt builder |
| AC-9 | An artifact request returns `artifact.type` of `markdown` or `html`, and it renders in the viewer, not as raw chat text | API test and UI test |
| AC-10 | HTML containing `<script>`, form posts and fetches to the API cannot run or reach the parent page | Sandbox test cases |
| AC-11 | `/health/chunks` shows 303 episodes after full ingestion, and re-running creates no duplicates | Ingestion test |
| AC-12 | An evaluation set of 30 in-corpus and 10 out-of-corpus questions is stored in the repo and can be re-run to compute M1–M3 | Eval script |
| AC-13 | A fresh clone reaches a working chat using only README steps | Manual fresh-clone test |

---

## 8. Required deliverables tracker

| # | Deliverable | State |
|---|---|---|
| 1 | Public GitHub repo, no secrets | In progress |
| 2 | `README.md` (needs updating: it says ~269 episodes and a "health-check frontend") | Needs update |
| 3 | PRD (this document) | Draft v1 |
| 4 | `design.md` | To do, from the Starry Night mockups |
| 5 | `architecture.md` | Exists. Needs schema, API and security sections extended |
| 6 | Agent transcripts folder, including failed attempts | Exists. Add this planning session and later phases |
| 7 | Automated tests plus manual UI test plan | To do |
| 8 | 2–3 minute demo video with camera, covering problem, product, local Ollama and one trade-off | To do |

---

## 9. Implementation plan

| Step | Work | Depends on |
|---|---|---|
| 1 | Commit or discard the uncommitted artifact work. Run its test script and record the result | none |
| 2 | Add an `episodes` table. Change ingestion to keep header metadata. Record the embed model per chunk | 1 |
| 3 | Start full ingestion of 303 episodes in the background (about 6–7 hours at the observed rate) | 2 |
| 4 | Add hybrid retrieval (keyword plus vector). Build the eval set and eval script | 2 |
| 5 | Backend modes: explain-simply, quiz, learner profile, notes endpoints | 2 |
| 6 | Frontend: chat, mode switcher, citation cards, artifact viewer, status chips, themes | 1 |
| 7 | Structured logging, error handling pass, resilience tests | 4, 6 |
| 8 | Automated tests, manual test plan, run the eval, record metrics | 3, 4, 7 |
| 9 | Write `design.md`, update `architecture.md` and `README.md`, save agent transcripts | 6, 8 |
| 10 | Fresh-clone test, record demo video, push, submit | all |

**Cut line if time runs short:** drop F12–F17 first, then F14, then F10–F11. Everything marked P0 stays.

---

## 10. Open questions

1. ~~Do transcripts contain timestamps?~~ **Yes** (`Speaker (HH:MM:SS):`). Each chunk stores its start time and citations deep-link to `&t=<seconds>s`. About 7% of chunks precede the first timestamp and link to the video start.
2. Is a small hybrid search (Postgres full-text plus pgvector) accurate enough, or does the eval set show a reranker is needed?
3. Which cloud provider key, if any, will be available for a live Claude demo?
