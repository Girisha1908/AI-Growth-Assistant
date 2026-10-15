"""API contract, persistence, routing and failure behaviour (acceptance criteria AC-1..AC-9)."""

import pytest
from sqlalchemy.exc import OperationalError

from tests.conftest import FakeProvider

SRC = "retention first week users activation"


def chat(client, sid, message, **kw):
    return client.post("/chat", json={"session_id": sid, "message": message, **kw})


# ── AC-1 sessions ────────────────────────────────────────────────────────
def test_sessions_are_independent(client, corpus, provider):
    a = client.post("/sessions").json()["session_id"]
    b = client.post("/sessions").json()["session_id"]
    chat(client, a, SRC)
    assert len(client.get(f"/sessions/{a}/messages").json()) == 2
    assert client.get(f"/sessions/{b}/messages").json() == []


def test_session_list_and_delete(client, corpus, provider, session_id):
    chat(client, session_id, SRC)
    listing = client.get("/sessions").json()
    assert listing[0]["id"] == session_id and listing[0]["message_count"] == 2
    assert listing[0]["title"].startswith("retention")
    assert client.delete(f"/sessions/{session_id}").status_code == 204
    assert client.get(f"/sessions/{session_id}/messages").status_code == 404


def test_session_metadata_is_stored(client, db):
    from app.models import Session
    sid = client.post("/sessions", json={"metadata": {"locale": "en-IN"}},
                      headers={"user-agent": "pytest"}).json()["session_id"]
    meta = db.query(Session).first().metadata_
    assert meta["client"] == {"locale": "en-IN"} and meta["user_agent"] == "pytest" and sid


# ── AC-2 grounded answer with rich citations ─────────────────────────────
def test_grounded_answer_has_rich_citations(client, corpus, provider, session_id):
    r = chat(client, session_id, SRC)
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "ask" and body["answer"].endswith("[1].")
    top = body["sources"][0]
    assert top["n"] == 1 and top["guest"] == "Albert Cheng"
    assert top["title"] and top["url"].startswith("https://youtu.be/BBB?t=") and top["timestamp"]
    assert body["meta"]["provider"] == "fake" and body["meta"]["retrieval"]["returned"] >= 1
    # the model was shown numbered excerpts with guest + episode names
    prompt = provider.calls[0][-1]["content"]
    assert "[1] Albert Cheng" in prompt and "Retention in subscription products" in prompt


# ── AC-3 refusal without calling the model ───────────────────────────────
def test_off_topic_is_refused_without_llm(client, corpus, provider, session_id):
    r = chat(client, session_id, "capital city france paris").json()
    assert r["answer"].startswith("I don't have enough information") and r["sources"] == []
    assert provider.calls == []


def test_model_refusal_clears_sources(client, corpus, provider, session_id):
    provider.script = ["I don't have enough information from the transcripts to answer that."]
    r = chat(client, session_id, SRC).json()
    assert r["sources"] == []


# ── AC-4 follow-ups use history, new sessions do not ─────────────────────
def test_followup_uses_session_context(client, corpus, provider, session_id):
    chat(client, session_id, SRC)
    chat(client, session_id, "what about churn?")          # short follow-up: no topic on its own
    second = provider.calls[1]
    roles = [m["role"] for m in second]
    assert roles[0] == "system" and "user" in roles[1:-1] and "assistant" in roles[1:-1]
    assert any(SRC in m["content"] for m in second[1:-1])   # earlier turn is in the prompt

    # The same short follow-up in a NEW session has no topic to anchor on, so retrieval
    # gates it and the model is never called: context did not leak across sessions.
    other = client.post("/sessions").json()["session_id"]
    r = chat(client, other, "what about churn?").json()
    assert r["answer"].startswith("I don't have enough information") and len(provider.calls) == 2


# ── AC-5 persistence ─────────────────────────────────────────────────────
def test_history_survives_app_restart(corpus, provider):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c1:
        sid = c1.post("/sessions").json()["session_id"]
        chat(c1, sid, SRC)
    with TestClient(app) as c2:                              # a "restarted" API process
        msgs = c2.get(f"/sessions/{sid}/messages").json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["sources"][0]["guest"] == "Albert Cheng" and msgs[1]["meta"]["provider"] == "fake"


# ── AC-6 provider switching (no code change) ─────────────────────────────
def test_provider_override_without_key_is_structured_error(client, corpus, session_id, monkeypatch):
    monkeypatch.undo()   # use the real factory
    monkeypatch.setattr("app.config.settings.ANTHROPIC_API_KEY", None)
    r = client.post("/chat", json={"session_id": session_id, "message": SRC, "provider": "claude"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "provider_not_configured"


def test_config_endpoint_lists_providers(client):
    cfg = client.get("/config").json()
    names = {p["name"]: p for p in cfg["providers"]}
    assert set(names) == {"ollama", "claude", "claude-agent"} and names["ollama"]["configured"]
    assert cfg["relevance_max_distance"] == 0.45 and "hybrid" in cfg["search"]


# ── AC-7 resilience ──────────────────────────────────────────────────────
@pytest.mark.parametrize("exc,status,code", [
    (ConnectionError("Cannot connect to Ollama"), 503, "provider_unavailable"),
    (TimeoutError("timed out"), 504, "provider_timeout"),
    (RuntimeError("boom"), 502, "provider_error"),
])
def test_provider_failures_are_structured_and_leave_no_half_turn(
        client, corpus, provider, session_id, exc, status, code):
    provider.fail_with = exc
    r = chat(client, session_id, SRC)
    assert r.status_code == status and r.json()["error"]["code"] == code
    assert r.json()["error"]["message"]
    assert client.get(f"/sessions/{session_id}/messages").json() == []   # retry is clean


def test_embedding_outage_is_503(client, corpus, provider, session_id, monkeypatch):
    from app.embeddings import EmbeddingError

    def down(_):
        raise EmbeddingError("Cannot connect to Ollama")

    monkeypatch.setattr("app.retrieval.embed_query", down)
    r = chat(client, session_id, SRC)
    assert r.status_code == 503 and r.json()["error"]["code"] == "embedding_unavailable"


def test_database_down_is_structured_503(corpus, provider):
    from fastapi.testclient import TestClient
    from app.db import get_db
    from app.main import app

    def broken():
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = broken
    try:
        with TestClient(app) as c:
            r = c.post("/sessions")
        assert r.status_code == 503 and r.json()["error"]["code"] == "database_unavailable"
    finally:
        app.dependency_overrides.clear()


def test_validation_and_not_found_are_structured(client, provider):
    assert client.post("/chat", json={"session_id": "not-a-uuid", "message": "x"}).status_code == 422
    sid = client.post("/sessions").json()["session_id"]
    bad = client.post("/chat", json={"session_id": sid, "message": "   "})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "validation_error"
    bad_mode = client.post("/chat", json={"session_id": sid, "message": "hi", "mode": "nope"})
    assert bad_mode.status_code == 422
    missing = client.post("/chat", json={"session_id": "00000000-0000-0000-0000-000000000000", "message": "hi"})
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "session_not_found"


# ── AC-8 / AC-9 skills and artifacts ─────────────────────────────────────
def test_markdown_artifact_via_auto_route(client, corpus, provider, session_id):
    provider.script = ["```markdown\n# Retention Cheatsheet\n- keep users [1]\n```"]
    r = chat(client, session_id, "create a markdown summary doc on retention first week users").json()
    assert r["mode"] == "artifact" and r["artifact"]["type"] == "markdown"
    assert r["artifact"]["title"] == "Retention Cheatsheet" and "Retention Cheatsheet" in r["answer"]
    stored = client.get(f"/sessions/{session_id}/messages").json()[-1]
    assert stored["artifact"]["title"] == "Retention Cheatsheet"          # persisted with the message


def test_html_artifact_is_full_document_without_script_instructions(client, corpus, provider, session_id):
    provider.script = ["```html\n<h1>Retention card</h1><p>First week matters [1]</p>\n```"]
    r = chat(client, session_id, "give me an HTML card about retention first week users").json()
    assert r["artifact"]["type"] == "html"
    assert r["artifact"]["content"].lower().startswith("<!doctype html>")
    system = provider.calls[0][0]["content"]
    assert "NO JavaScript" in system and "NO external URLs" in system


def test_bad_artifact_output_is_a_clear_error(client, corpus, provider, session_id):
    provider.script = ["   "]
    r = chat(client, session_id, "create a markdown doc about retention first week users")
    assert r.status_code == 502 and r.json()["error"]["code"] == "bad_model_output"


def test_ship30_endpoint_sectioned_reaches_target_length(client, corpus, provider, session_id):
    para = ("**Retention starts early.** " + "Users decide in the first week [1]. " * 12)
    provider.script = ["Title: Why Week One Wins\n1. The first week\n2. The habit loop\n3. Churn signals\n4. What to measure"]
    provider.script += [para] * 6
    r = client.post("/skills/ship30", json={"session_id": session_id, "topic": SRC}).json()
    assert r["mode"] == "ship30" and r["meta"]["strategy"] == "sectioned" and r["meta"]["llm_calls"] == 7
    md = r["artifact"]["content"]
    assert md.startswith("# Why Week One Wins") and "## The first week" in md and "## Takeaway" in md
    assert r["meta"]["word_count"] > 400


def test_ship30_falls_back_to_single_when_outline_unusable(client, corpus, provider, session_id):
    provider.script = ["I'm not sure how to outline this.", "# Fallback Title\n\nBody text [1]"]
    r = client.post("/skills/ship30", json={"session_id": session_id, "topic": SRC}).json()
    assert r["meta"]["strategy"] == "single" and r["artifact"]["title"] == "Fallback Title"


def test_quiz_and_prd_modes(client, corpus, provider, session_id):
    provider.script = ["```markdown\n# Quiz: retention\n1. Q?\n```", "```markdown\n# PRD: Habit app\n## Problem\n```"]
    q = chat(client, session_id, "retention first week users", mode="quiz").json()
    p = chat(client, session_id, "retention first week users activation", mode="prd").json()
    assert q["mode"] == "quiz" and q["artifact"]["title"].startswith("Quiz")
    assert p["mode"] == "prd" and p["artifact"]["title"].startswith("PRD")


# ── personalisation ──────────────────────────────────────────────────────
def test_profile_roundtrip_and_prompt_injection(client, corpus, provider, session_id):
    put = client.put("/profile", json={"goal": "Become an AI engineer", "background": "final-year CS",
                                       "known_concepts": ["embeddings", " ", "backprop"]})
    assert put.status_code == 200 and put.json()["known_concepts"] == ["embeddings", "backprop"]
    assert client.get("/profile").json()["goal"] == "Become an AI engineer"
    chat(client, session_id, SRC, mode="explain")
    assert "Become an AI engineer" in provider.calls[-1][0]["content"]
    chat(client, session_id, SRC, mode="explain", personalize=False)
    assert "Become an AI engineer" not in provider.calls[-1][0]["content"]


# ── library, episodes, observability ─────────────────────────────────────
def test_notes_crud(client):
    n = client.post("/notes", json={"title": "My essay", "kind": "markdown", "content": "# Hi"}).json()
    assert client.get("/notes").json()[0]["id"] == n["id"]
    assert client.post("/notes", json={"title": "x", "kind": "weird", "content": "y"}).status_code == 422
    assert client.delete(f"/notes/{n['id']}").status_code == 204
    assert client.delete(f"/notes/{n['id']}").status_code == 404


def test_episode_browser_and_search(client, corpus):
    all_eps = client.get("/episodes").json()
    assert all_eps["total"] == 3
    hit = client.get("/episodes", params={"q": "chesky"}).json()
    assert [e["guest"] for e in hit["items"]] == ["Brian Chesky"]
    ep = client.get(f"/episodes/{hit['items'][0]['id']}")
    assert ep.status_code == 200 and ep.json()["youtube_url"]


def test_health_endpoints_report_real_state(client, corpus):
    h = client.get("/health").json()
    assert h["database"] == "connected" and h["provider"] == "fake" and h["status"] == "ok"
    c = client.get("/health/chunks").json()
    assert c["total_chunks"] == 6 and c["episodes"] == 3 and c["embed_models"] == ["nomic-embed-text"]
    assert c["legacy_chunks_without_metadata"] == 0


def test_health_degraded_when_provider_down(client, provider):
    async def down():
        return {"reachable": False, "error": "refused"}
    provider.ping = down
    assert client.get("/health").json()["status"] == "degraded"


def test_client_event_and_request_id(client):
    r = client.post("/client-events", json={"type": "artifact_render_error", "message": "iframe failed"})
    assert r.status_code == 202 and r.headers["x-request-id"]


def test_search_endpoint_is_retrieval_only(client, corpus, provider):
    hit = client.post("/search", json={"query": SRC}).json()
    assert hit["answerable"] and hit["reason"] == "ok" and hit["sources"][0]["guest"] == "Albert Cheng"
    miss = client.post("/search", json={"query": "capital city france paris"}).json()
    assert miss["answerable"] is False and miss["reason"] == "below_threshold" and miss["sources"] == []
    assert provider.calls == []          # never touches the model
