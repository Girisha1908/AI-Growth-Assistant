import pytest

from app.agent.artifacts import (build_artifact, derive_title, ensure_html_document, extract_fenced,
                                 word_count)
from app.agent.router import decide_route
from app.agent.skills.ship30 import parse_outline


@pytest.mark.parametrize("msg,mode,art", [
    ("How should teams improve retention?", "ask", None),
    ("What is a summary statistic?", "ask", None),
    ("Write a Ship 30 for 30 essay about North Star metrics", "ship30", None),
    ("turn this into an atomic essay", "ship30", None),
    ("create a markdown summary doc on improving user retention", "artifact", "markdown"),
    ("give me an HTML card for North Star metrics", "artifact", "html"),
    ("draft a PRD for a habit tracker", "prd", None),
    ("quiz me on onboarding", "quiz", None),
    ("explain pricing like I'm a beginner", "explain", None),
])
def test_auto_routing(msg, mode, art):
    r = decide_route("auto", msg)
    assert (r.mode, r.artifact_type) == (mode, art)


def test_explicit_mode_wins():
    assert decide_route("quiz", "write an essay").mode == "quiz"
    assert decide_route("artifact", "make an html page").artifact_type == "html"
    assert decide_route(None, "hello").mode == "ask"


def test_fence_extraction():
    assert extract_fenced("Sure!\n```markdown\n# Hi\ntext\n```\nbye") == "# Hi\ntext"
    assert extract_fenced("# plain doc") == "# plain doc"
    assert extract_fenced("```html\n<p>cut off") == "<p>cut off"


def test_html_becomes_full_document():
    doc = ensure_html_document("<h1>Hi</h1>", "Hi")
    assert doc.lower().startswith("<!doctype html>") and "<h1>Hi</h1>" in doc
    full = "<html><body>x</body></html>"
    assert ensure_html_document(full) == full


def test_titles():
    assert derive_title("intro\n# My Doc\nx", "markdown", "fb") == "My Doc"
    assert derive_title("<title>T1</title>", "html", "fb") == "T1"
    assert derive_title("<h1><b>Big</b></h1>", "html", "fb") == "Big"
    assert derive_title("nothing", "markdown", "fb") == "fb"


def test_build_artifact_limits():
    a = build_artifact("```markdown\n# T\nbody\n```", "markdown", "fb", 1000)
    assert a["type"] == "markdown" and a["title"] == "T"
    with pytest.raises(ValueError):
        build_artifact("   ", "markdown", "fb", 1000)
    with pytest.raises(ValueError):
        build_artifact("x" * 5000, "markdown", "fb", 1000)


def test_outline_parser():
    title, heads = parse_outline("Title: **Why Retention Wins**\n1. First hook\n2) Second\n- Third\n4. Fourth\n5. Extra")
    assert title == "Why Retention Wins" and heads == ["First hook", "Second", "Third", "Fourth"]
    assert parse_outline("I cannot do that")[1] == []


def test_word_count():
    assert word_count("one two  three-four don't") == 4
