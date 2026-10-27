"""MCP tools against a tiny indexed repo. Needs Postgres (skipped without it)."""

import asyncio

import psycopg
import pytest
from test_api import HAVE_DB, URL  # pytest puts this folder on the path

from cartograph.store import index_repo


def call(server, tool, **args) -> str:
    result = asyncio.run(server.call_tool(tool, args))
    return "".join(c.text for c in result.content)


@pytest.mark.skipif(not HAVE_DB, reason="Postgres not running")
def test_tools_answer_with_file_and_line(tmp_path):
    from cartograph.mcp_server import build

    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "a.js").write_text(
        "function setCookie(name) { return serialize(name); }\n"
        "function serialize(v) { return v; }\n"
        "function clearCookie(name) { if (name) log(); return setCookie(name); }\n")
    root = tmp_path.resolve().as_posix()
    with psycopg.connect(URL, autocommit=True) as conn:
        index_repo(conn, tmp_path)
    try:
        server = build(root, URL, history=[
            {"time": 1, "changed": [["lib/a.js", "setCookie"], ["lib/a.js", "serialize"]]}])
        names = {t.name for t in asyncio.run(server.list_tools())}
        assert names == {"search_code", "get_function", "impact", "check_order"}
        assert "serialize (lib/a.js:2-2)" in call(server, "search_code", query="serialize")
        fn = call(server, "get_function", function="setCookie")
        assert "    1  function setCookie" in fn
        assert "Called by: clearCookie (lib/a.js:3)" in fn
        assert "Often changed with: serialize (lib/a.js:2) x1" in fn
        assert call(server, "impact", function="serialize") == (
            "1 hop: setCookie (lib/a.js:1)\n2 hops: clearCookie (lib/a.js:3)")
        assert call(server, "check_order", x="log", y="setCookie", start="clearCookie").startswith(
            "not always")
        assert "No function named" in call(server, "get_function", function="nope")
    finally:
        with psycopg.connect(URL, autocommit=True) as conn:
            conn.execute("DELETE FROM repos WHERE root = %s", (root,))
