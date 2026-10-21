"""HTTP API for the map website: search, call graph, function details, impact, and a live
stream of the agent's steps (Server-Sent Events). Run with: cartograph serve <repo>.

Binds to 127.0.0.1 only: it serves the indexed source code, which must not leave the machine.
"""

import json
import queue
import threading
from collections import defaultdict
from typing import Literal

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .cochange import changed_together
from .graph import impact
from .search import BM25, Dense, load_corpus, rrf


class Function(BaseModel):
    id: int
    name: str
    qualname: str
    path: str
    start_line: int
    end_line: int
    kind: str  # tree-sitter node type, or "module" for a file's top-level code


class Edge(BaseModel):
    source: int  # caller
    target: int  # callee
    via: str  # how we know: same-file, import, qualname, name-match, or jelly


class Graph(BaseModel):
    nodes: list[Function]
    edges: list[Edge]


class CoChanged(Function):
    times: int  # commits that changed both functions


class FunctionDetail(Function):
    code: str
    callers: list[Function]
    callees: list[Function]
    changed_with: list[CoChanged]  # from git history; empty when it wasn't mined


class Hit(Function):
    rank: int
    keyword_rank: int | None  # where BM25 alone ranked it (None: not in its top 50)
    meaning_rank: int | None  # where meaning search alone ranked it


class Impacted(Function):
    distance: int  # 1 = calls it directly, 2 = calls a direct caller, ...


FUNCTION_COLS = "fn.id, fn.name, fn.qualname, f.path, fn.start_line, fn.end_line, fn.kind"
SCOPE = "JOIN files f ON f.id = fn.file_id JOIN repos r ON r.id = f.repo_id " \
        "WHERE r.root = %s AND NOT f.is_test"


def call_edges(conn, root: str) -> list[Edge]:
    """Every known call link: our resolved calls plus Jelly's extra edges."""
    rows = conn.execute(
        f"""SELECT DISTINCT ON (c.caller_id, c.callee_id) c.caller_id, c.callee_id,
                   c.resolution FROM calls c JOIN functions fn ON fn.id = c.caller_id {SCOPE}
                   AND c.callee_id IS NOT NULL
            UNION SELECT e.caller_id, e.callee_id, 'jelly' FROM extra_edges e
                   JOIN functions fn ON fn.id = e.caller_id {SCOPE}""", (root, root))
    ours = {}
    for s, t, via in rows:  # a link found by both keeps our label
        if (s, t) not in ours or ours[(s, t)] == "jelly":
            ours[(s, t)] = via
    return [Edge(source=s, target=t, via=v) for (s, t), v in ours.items()]


def function_places(conn, root: str) -> tuple[dict[tuple[str, str], int], dict[int, tuple[str, int]]]:
    """(path, qualname) -> id, and id -> (path, start line), for today's named functions."""
    ids, place = {}, {}
    for fid, path, qualname, line in conn.execute(
            f"SELECT fn.id, f.path, fn.qualname, fn.start_line FROM functions fn {SCOPE}"
            " AND fn.kind <> 'module' ORDER BY fn.id", (root,)):
        ids.setdefault((path, qualname), fid)  # shortcut: a repeated name maps to its first function
        place[fid] = (path, line)
    return ids, place


def create_app(root: str, db_url: str, llm: str = "qwen3-4b",
               history: list[dict] | None = None) -> FastAPI:
    """root: the indexed repo folder (posix path, as stored by `cartograph index`).
    history: mined commits (`cartograph impact-eval` caches them) for "often changed with"."""
    app = FastAPI(title="Cartograph", version="0.1.0")

    def connect() -> psycopg.Connection:
        return psycopg.connect(db_url, autocommit=True)  # one per request: not thread-safe

    with connect() as conn:
        docs = load_corpus(conn, root)
        together = changed_together(history or [], function_places(conn, root)[0])
    bm25 = BM25(docs)
    embedder_lock, embedder = threading.Lock(), []  # load the ~18 s model on first use only

    def get_embedder():
        with embedder_lock:
            if not embedder:
                from .embed import Embedder

                embedder.append(Embedder("coderank"))
            return embedder[0]

    # Warm up in the background so the first meaning search doesn't wait ~1 min for the model.
    threading.Thread(target=get_embedder, daemon=True).start()

    def functions(conn, ids: list[int]) -> list[Function]:
        rows = conn.execute(f"SELECT {FUNCTION_COLS} FROM functions fn {SCOPE} AND fn.id = ANY(%s)",
                            (root, ids)).fetchall()
        by_id = {r[0]: Function(**dict(zip(Function.model_fields, r))) for r in rows}
        return [by_id[i] for i in ids if i in by_id]  # keep the caller's order

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "root": root, "functions": len(docs)}

    @app.get("/api/search")
    def search(q: str = Query(min_length=1, max_length=2000),
               mode: Literal["bm25", "dense", "hybrid"] = "hybrid",
               k: int = Query(10, ge=1, le=50)) -> list[Hit]:
        with connect() as conn:
            # Each method's own ranking (top 50) is kept, so every hit can say why it's here.
            keyword = bm25(q, 50) if mode != "dense" else []
            meaning = (Dense(conn, root, "coderank", embedder=get_embedder())(q, 50)
                       if mode != "bm25" else [])
            ids = rrf([keyword, meaning])[:k] if mode == "hybrid" else (keyword or meaning)[:k]
            pos = lambda ranked, fid: ranked.index(fid) + 1 if fid in ranked else None
            return [Hit(**f.model_dump(), rank=i, keyword_rank=pos(keyword, f.id),
                        meaning_rank=pos(meaning, f.id))
                    for i, f in enumerate(functions(conn, ids), 1)]

    @app.get("/api/graph")
    def graph() -> Graph:
        with connect() as conn:
            rows = conn.execute(f"SELECT {FUNCTION_COLS} FROM functions fn {SCOPE} ORDER BY fn.id",
                                (root,)).fetchall()
            nodes = [Function(**dict(zip(Function.model_fields, r))) for r in rows]
            ids = {n.id for n in nodes}
            return Graph(nodes=nodes, edges=[e for e in call_edges(conn, root)
                                             if e.source in ids and e.target in ids])

    @app.get("/api/functions/{fid}")
    def function(fid: int) -> FunctionDetail:
        with connect() as conn:
            found = functions(conn, [fid])
            if not found:
                raise HTTPException(404, f"no function {fid} in {root}")
            code = conn.execute("SELECT code FROM functions WHERE id = %s", (fid,)).fetchone()[0]
            links = call_edges(conn, root)
            callers = functions(conn, sorted({e.source for e in links if e.target == fid}))
            callees = functions(conn, sorted({e.target for e in links if e.source == fid}))
            often = dict(together[fid].most_common(8)) if fid in together else {}
            changed_with = [CoChanged(**f.model_dump(), times=often[f.id])
                            for f in functions(conn, list(often))]
            return FunctionDetail(**found[0].model_dump(), code=code, callers=callers,
                                  callees=callees,
                                  changed_with=sorted(changed_with, key=lambda f: (-f.times, f.id)))

    @app.get("/api/impact/{fid}")
    def impact_of(fid: int, depth: int = Query(3, ge=1, le=10)) -> list[Impacted]:
        with connect() as conn:
            if not functions(conn, [fid]):
                raise HTTPException(404, f"no function {fid} in {root}")
            callers_of = defaultdict(set)
            for e in call_edges(conn, root):
                callers_of[e.target].add(e.source)
            dist = impact(callers_of, fid, depth)
            ordered = sorted(dist, key=lambda i: (dist[i], i))
            return [Impacted(**f.model_dump(), distance=dist[f.id])
                    for f in functions(conn, ordered)]

    @app.get("/api/ask")
    def ask(q: str = Query(min_length=1, max_length=2000),
            agent: Literal["index", "grep"] = "index") -> StreamingResponse:
        """Server-Sent Events: one `data: {json}` message per agent step, then `done`."""
        from .agent import Agent  # imported here so tests can swap it

        events: queue.Queue = queue.Queue()

        def work() -> None:
            try:
                with connect() as conn:
                    dense = (Dense(conn, root, "coderank", embedder=get_embedder())
                             if agent == "index" else None)
                    a = Agent(conn, root, docs, llm, agent, bm25=bm25, dense=dense,
                              on_event=events.put)
                    ranked = a(q)
                    events.put({"type": "done", "answer": a.last_extra["answer"],
                                "not_found": a.last_extra["not_found"], "ranked": ranked[:10],
                                "tokens": a.last_extra["tokens"]})
            # Thread boundary: any failure must reach the browser, or the stream hangs forever.
            # SystemExit: the agent's friendly setup errors, e.g. Ollama not running.
            except (Exception, SystemExit) as e:  # noqa: BLE001
                events.put({"type": "error", "text": str(e)[:500]})
            finally:
                events.put(None)

        # The agent blocks on the model for seconds per step, so it runs in its own thread and
        # hands steps over through a queue. shortcut: if the browser disconnects, the thread
        # still finishes the question; add cancellation if that wastes too much time.
        threading.Thread(target=work, daemon=True).start()

        def stream():
            while (event := events.get()) is not None:
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    return app
