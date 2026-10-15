#!/usr/bin/env python3
"""Evaluation harness for the PRD metrics (stdlib only; runs on the host or in the container).

  python eval/run_eval.py                    # retrieval-only: seconds, no LLM  (M1, M2, M3)
  python eval/run_eval.py --full             # also calls /chat per question    (adds M4 latency)
  python eval/run_eval.py --api http://localhost:8000 --out eval/last_run.md

Metrics
  M1 grounded-answer rate : in-corpus questions that return >= 1 source
  M2 correct-refusal rate : out-of-corpus questions that are refused (no sources)
  M3 citation validity    : every returned source resolves to a real ingested episode
"""
import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def call(api, path, payload=None, method=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(api + path, data=data, method=method or ("POST" if data else "GET"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            return json.loads(r.read() or "null")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise SystemExit(f"{path} -> HTTP {e.code}: {body[:300]}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Cannot reach {api}: {e.reason}. Is `docker compose up` running?")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--full", action="store_true", help="also run /chat (slow on local models)")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--out", default=str(Path(__file__).with_name("last_run.md")))
    a = ap.parse_args()
    qs = json.loads(Path(__file__).with_name("questions.json").read_text())

    cfg = call(a.api, "/config")
    rows, latencies, cited = [], [], []

    def run(q, expect_answer):
        t0 = time.time()
        if a.full:
            sid = call(a.api, "/sessions", {})["session_id"]
            r = call(a.api, "/chat", {"session_id": sid, "message": q, "mode": "ask", "provider": a.provider})
            sources, answerable = r["sources"], bool(r["sources"])
            latencies.append(time.time() - t0)
        else:
            r = call(a.api, "/search", {"query": q})
            sources, answerable = r["sources"], r["answerable"]
        cited.extend(sources)
        best = None if a.full else r.get("best_distance")
        rows.append((q, expect_answer, answerable, len(sources), best))
        mark = "ok " if answerable == expect_answer else "MISS"
        print(f"[{mark}] {'IN ' if expect_answer else 'OUT'} {len(sources)} src  {q[:70]}")

    for q in qs["in_corpus"]:
        run(q, True)
    for q in qs["out_of_corpus"]:
        run(q, False)

    # Snapshot AFTER the run: ingestion may add episodes while the questions run.
    chunks = call(a.api, "/health/chunks")
    episode_ids, page = set(), 1
    while items := call(a.api, f"/episodes?page_size=100&page={page}")["items"]:
        episode_ids |= {e["id"] for e in items}
        page += 1
    total_sources = len(cited)
    valid = sum(1 for s in cited if s.get("episode_id") in episode_ids and (s.get("url") or "").startswith("http"))

    ins = [r for r in rows if r[1]]
    outs = [r for r in rows if not r[1]]
    m1 = sum(1 for r in ins if r[2]) / len(ins)
    m2 = sum(1 for r in outs if not r[2]) / len(outs)
    m3 = (valid / total_sources) if total_sources else 0.0
    lines = [
        "# Evaluation run", "",
        f"- API: `{a.api}`  |  provider: `{a.provider or cfg['provider']}`  |  embed: `{cfg['embed_model']}`",
        f"- Corpus: {chunks['episodes']} episodes, {chunks['total_chunks']} chunks  |  threshold: {cfg['relevance_max_distance']}",
        f"- Mode: {'full (/chat)' if a.full else 'retrieval-only (/search)'}", "",
        "| Metric | Result | Target |", "|---|---|---|",
        f"| M1 grounded-answer rate (in-corpus) | {m1:.0%} ({sum(1 for r in ins if r[2])}/{len(ins)}) | >= 90% |",
        f"| M2 correct-refusal rate (out-of-corpus) | {m2:.0%} ({sum(1 for r in outs if not r[2])}/{len(outs)}) | 100% |",
        f"| M3 citation validity | {m3:.0%} ({valid}/{total_sources}) | 100% |",
    ]
    if latencies:
        lines.append(f"| M4 median /chat latency | {statistics.median(latencies):.1f}s | <= 30s (hardware-dependent) |")
    lines += ["", "## Misses", ""]
    misses = [r for r in rows if r[1] != r[2]]
    lines += [f"- {'should answer' if r[1] else 'should refuse'}: {r[0]}" + (f" (best distance {r[4]})" if r[4] is not None else "") for r in misses] or ["- none"]
    Path(a.out).write_text("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines[5:10]))
    print(f"\nReport written to {a.out}")
    sys.exit(0 if (m1 >= 0.9 and m2 == 1.0 and m3 == 1.0) else 1)


if __name__ == "__main__":
    main()
