"""API endpoints against a tiny indexed repo. Needs Postgres (skipped without it)."""

import json
import os

import psycopg
import pytest

from cartograph.graph import impact
from cartograph.store import DEFAULT_DB, index_repo

URL = os.environ.get("DATABASE_URL", DEFAULT_DB)
try:
    psycopg.connect(URL, connect_timeout=2).close()  # skip fast, not hang, without Postgres
    HAVE_DB = True
except psycopg.OperationalError:
    HAVE_DB = False


def test_impact_bfs_levels_and_depth_limit():
    callers_of = {1: {2, 3}, 2: {4}, 4: {1, 5}}  # a cycle back to 1 must not loop
    assert impact(callers_of, 1) == {2: 1, 3: 1, 4: 2, 5: 3}
    assert impact(callers_of, 1, max_depth=1) == {2: 1, 3: 1}


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient

    from cartograph.api import create_app

    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "a.js").write_text(
        "function setCookie(name) { return serialize(name); }\n"
        "function serialize(v) { return v; }\n"
        "function clearCookie(name) { return setCookie(name); }\n")
    with psycopg.connect(URL, autocommit=True) as conn:
        index_repo(conn, tmp_path)
    try:
        # Mined history: setCookie changed twice with serialize, once with clearCookie.
        history = [{"time": t, "changed": [["lib/a.js", "setCookie"], ["lib/a.js", other]]}
                   for t, other in [(1, "serialize"), (2, "serialize"), (3, "clearCookie")]]
        yield TestClient(create_app(tmp_path.resolve().as_posix(), URL, history=history))
    finally:  # the real database: remove this test repo again
        with psycopg.connect(URL, autocommit=True) as conn:
            conn.execute("DELETE FROM repos WHERE root = %s", (tmp_path.resolve().as_posix(),))


@pytest.mark.skipif(not HAVE_DB, reason="Postgres not running")
def test_search_graph_function_impact(client):
    hits = client.get("/api/search", params={"q": "cookie serialize", "mode": "bm25"}).json()
    assert hits[0]["qualname"] in ("setCookie", "serialize") and hits[0]["rank"] == 1
    # provenance: in keyword-only mode the keyword rank is the rank, and meaning is absent
    assert [(h["keyword_rank"], h["meaning_rank"]) for h in hits] == [(h["rank"], None) for h in hits]

    graph = client.get("/api/graph").json()
    by_name = {n["qualname"]: n["id"] for n in graph["nodes"]}
    links = {(e["source"], e["target"]) for e in graph["edges"]}
    assert (by_name["clearCookie"], by_name["setCookie"]) in links

    detail = client.get(f"/api/functions/{by_name['setCookie']}").json()
    assert "serialize(name)" in detail["code"]
    assert [c["qualname"] for c in detail["callers"]] == ["clearCookie"]
    assert [c["qualname"] for c in detail["callees"]] == ["serialize"]
    assert [(c["qualname"], c["times"]) for c in detail["changed_with"]] == [
        ("serialize", 2), ("clearCookie", 1)]

    hit = client.get(f"/api/impact/{by_name['serialize']}").json()
    assert [(h["qualname"], h["distance"]) for h in hit] == [("setCookie", 1), ("clearCookie", 2)]

    assert client.get("/api/functions/999999999").status_code == 404
    assert client.get("/api/search", params={"q": ""}).status_code == 422  # input checked


@pytest.mark.skipif(not HAVE_DB, reason="Postgres not running")
def test_ask_streams_each_step(client, monkeypatch):
    class FakeAgent:  # no model: emit two steps the way the real agent does
        def __init__(self, *args, on_event=None, **kw):
            self.on_event = on_event

        def __call__(self, question):
            self.on_event({"type": "tool", "tool": "search_meaning", "ids": [1]})
            self.on_event({"type": "answer", "ids": [1]})
            self.last_extra = {"answer": [1], "not_found": False, "tokens": 10}
            return [1]

    monkeypatch.setattr("cartograph.agent.Agent", FakeAgent)
    with client.stream("GET", "/api/ask", params={"q": "cookies", "agent": "grep"}) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    assert [e["type"] for e in events] == ["tool", "answer", "done"]
    assert events[-1]["answer"] == [1]
