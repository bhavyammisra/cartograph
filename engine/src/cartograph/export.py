"""Export a static demo: the API's answers as JSON files the website can read with no server.

    out/health.json, out/graph.json, out/functions/<id>.json   the map and every function panel
    out/traces.json                                            {question: [agent events]}, recorded

Search, impact and live questions need the engine, so the demo site offers name search and
replays the recorded questions only. Uses the API's own endpoint functions, like the MCP server.
"""

import asyncio
import json
from pathlib import Path

from fastapi.routing import APIRoute

from .api import create_app


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Compact JSON: the graph and panels are downloaded by every visitor.
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")


async def record(stream) -> list[dict]:
    """Collect one agent run from the API's Server-Sent Events response."""
    events = []
    async for chunk in stream.body_iterator:
        text = chunk.decode() if isinstance(chunk, bytes) else chunk
        events += [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]
    return events


def export(root: str, db_url: str, out: Path, questions: list[str], llm: str,
           history: list[dict] | None = None) -> dict:
    app = create_app(root, db_url, llm, history)
    endpoint = {r.path: r.endpoint for r in app.routes if isinstance(r, APIRoute)}
    health = endpoint["/api/health"]()
    write(out / "health.json", {**health, "root": Path(health["root"]).name})  # no local paths
    graph = endpoint["/api/graph"]()
    write(out / "graph.json", graph.model_dump())
    for node in graph.nodes:
        write(out / "functions" / f"{node.id}.json",
              endpoint["/api/functions/{fid}"](fid=node.id).model_dump())
    traces = {}
    for q in questions:
        events = asyncio.run(record(endpoint["/api/ask"](q=q, agent="index")))
        if any(e["type"] == "error" for e in events):
            raise SystemExit(f"recording {q!r} failed: {events[-1]}")
        traces[q] = events
    write(out / "traces.json", traces)
    return {"functions": len(graph.nodes), "edges": len(graph.edges), "traces": len(traces)}
