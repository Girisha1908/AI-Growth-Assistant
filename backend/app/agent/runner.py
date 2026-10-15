"""Orchestrates one agent turn."""

import time
from typing import Any, Optional

from sqlalchemy.orm import Session as DbSession

from app.agent.router import decide_route
from app.agent.skills import SKILLS
from app.agent.types import REFUSAL_MESSAGE, AgentContext
from app.config import settings
from app.embeddings import EmbeddingError
from app.errors import AppError, ProviderError, provider_error_from
from app.logging_utils import get_logger
from app.providers.base import LLMProvider
from app.retrieval import build_retrieval_query, public_source, search_chunks

log = get_logger("agent")


class InstrumentedProvider(LLMProvider):
    """Wraps any provider to time and log every model call (event=llm_call)."""

    def __init__(self, inner: LLMProvider):
        self.inner, self.name, self.model, self.calls = inner, inner.name, inner.model, 0

    async def chat(self, messages: list[dict]) -> str:
        self.calls += 1
        t0 = time.perf_counter()
        try:
            out = await self.inner.chat(messages)
            log.info("llm_call", extra={"provider": self.name, "model": self.model, "ok": True,
                                        "ms": round((time.perf_counter() - t0) * 1000),
                                        "prompt_chars": sum(len(m["content"]) for m in messages),
                                        "output_chars": len(out)})
            return out
        except Exception as e:  # noqa: BLE001
            log.error("llm_call", extra={"provider": self.name, "model": self.model, "ok": False,
                                         "ms": round((time.perf_counter() - t0) * 1000),
                                         "error": str(e)[:300]})
            raise


def run_retrieval(db: DbSession, question: str, history: list[dict]):
    prior = [m["content"] for m in history if m["role"] == "user"]
    query = build_retrieval_query(prior, question)
    try:
        result = search_chunks(query, db)
        if not result.chunks and query != question:  # combined query found nothing: retry alone
            result = search_chunks(question, db)
        return result
    except EmbeddingError as e:
        raise ProviderError("embedding_unavailable", str(e), 503,
                            "Start Ollama and make sure the embedding model is pulled.") from e


async def run_turn(db: DbSession, *, question: str, history: list[dict], mode: Optional[str],
                   provider: LLMProvider, profile: Optional[dict]) -> dict[str, Any]:
    t0 = time.perf_counter()
    route = decide_route(mode, question)
    log.info("route", extra={"mode": route.mode, "reason": route.reason})

    retrieval = run_retrieval(db, question, history)
    meta = {"provider": provider.name, "model": provider.model, "route": route.reason,
            "retrieval": {"reason": retrieval.reason, "best_distance": retrieval.best_distance,
                          "returned": len(retrieval.chunks), "ms": retrieval.ms,
                          "vector_hits": retrieval.vector_hits,
                          "keyword_hits": retrieval.keyword_hits}}

    if not retrieval.chunks:  # gate: no model call, no guessing
        meta["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        return {"answer": REFUSAL_MESSAGE, "mode": route.mode, "sources": [],
                "artifact": None, "meta": meta}

    llm = InstrumentedProvider(provider)
    ctx = AgentContext(question=question, chunks=retrieval.chunks, history=history, provider=llm,
                       profile=profile, artifact_type=route.artifact_type,
                       target_words=settings.SHIP30_TARGET_WORDS, strategy=settings.SHIP30_STRATEGY)
    try:
        out = await SKILLS[route.mode].run(ctx)
    except AppError:
        raise
    except ValueError as e:
        if route.mode in ("artifact", "prd", "quiz"):  # bad model output, not bad config
            raise ProviderError("bad_model_output", str(e), 502,
                                "The model did not return a usable document. Try again.") from e
        raise provider_error_from(e) from e
    except Exception as e:  # noqa: BLE001
        raise provider_error_from(e) from e

    refused = REFUSAL_MESSAGE in out.answer
    sources = [] if refused else [public_source(n, c) for n, c in enumerate(retrieval.chunks, 1)]
    meta.update(out.meta)
    meta["llm_calls"] = llm.calls
    meta["latency_ms"] = round((time.perf_counter() - t0) * 1000)
    if out.artifact:
        log.info("artifact_generated", extra={"type": out.artifact["type"],
                                              "bytes": len(out.artifact["content"].encode())})
    return {"answer": out.answer, "mode": route.mode, "sources": sources,
            "artifact": None if refused else out.artifact, "meta": meta}
