"""MCP server: Cartograph's search, call graph, impact and ordering as tools for any MCP client
(Claude Code, Cursor, ...). Run with: cartograph mcp <repo>  (stdio transport).

The tools call the HTTP API's own endpoint functions in-process, so the website and MCP clients
always get the same answers. Results are short plain text: every line an agent reads costs tokens.
"""

import psycopg
from fastapi.routing import APIRoute
from mcp.server.mcpserver import MCPServer

from .api import SCOPE, create_app
from .order import Order

INSTRUCTIONS = """Cartograph has indexed this JavaScript/TypeScript repository: every function, \
who calls it, what it calls, what changes with it in git history, and meaning-based search.
Start with search_code for "where is X handled?" questions; it understands descriptions, not just \
names. Then get_function to read a candidate with its callers and callees. Answers name \
functions as `name (path:line)`."""


def build(root: str, db_url: str, history: list[dict] | None = None) -> MCPServer:
    app = create_app(root, db_url, history=history)
    # FastAPI keeps each route's plain Python function; call those, passing every argument
    # (their defaults are FastAPI Query markers, not values).
    endpoint = {r.path: r.endpoint for r in app.routes if isinstance(r, APIRoute)}
    nodes = endpoint["/api/graph"]().nodes
    by_name: dict[str, list] = {}
    for n in nodes:
        by_name.setdefault(n.qualname, []).append(n)
    with psycopg.connect(db_url, autocommit=True) as conn:
        order = Order.load(conn, root)
        # Meaning search needs `cartograph embed`; without it, search by keywords only.
        embedded = conn.execute(f"""SELECT 1 FROM embeddings e JOIN functions fn
                                    ON fn.id = e.function_id {SCOPE} AND e.model = 'coderank'
                                    LIMIT 1""", (root,)).fetchone() is not None

    def place(f) -> str:
        return f"{f.qualname} ({f.path}:{f.start_line})"

    def find(function: str):
        """A function by full name (res.send) or id (F123 / 123); else a message saying why not."""
        key = function.strip().removeprefix("F")
        if key.isdigit():
            hits = [n for n in nodes if n.id == int(key)]
        else:
            hits = by_name.get(function.strip(), [])
            if not hits:  # a short name: `send` finds res.send if it is the only one
                hits = [n for n in nodes if n.name == function.strip()
                        or n.qualname.endswith("." + function.strip())]
        if len(hits) == 1:
            return hits[0]
        if not hits:
            return f"No function named {function!r}. Try search_code."
        return "Several functions match; call again with an id:\n" + "\n".join(
            f"F{n.id} {place(n)}" for n in hits[:20])

    server = MCPServer("cartograph", instructions=INSTRUCTIONS)

    @server.tool()
    def search_code(query: str, limit: int = 10) -> str:
        """Find functions by what they do or by name (keyword + meaning search, merged).
        Returns `F<id> name (path:start-end)`, best first."""
        hits = endpoint["/api/search"](q=query, mode="hybrid" if embedded else "bm25",
                                      k=max(1, min(limit, 50)))
        return "\n".join(f"F{h.id} {h.qualname} ({h.path}:{h.start_line}-{h.end_line})"
                         for h in hits) or "No matches."

    @server.tool()
    def get_function(function: str) -> str:
        """Read one function: its code with line numbers, who calls it, what it calls, and what
        usually changes with it in git history. `function` is a full name (res.send) or an id (F12)."""
        f = find(function)
        if isinstance(f, str):
            return f
        d = endpoint["/api/functions/{fid}"](fid=f.id)
        code = "\n".join(f"{d.start_line + i:>5}  {line}" for i, line in enumerate(d.code.splitlines()))
        parts = [f"F{d.id} {place(d)} to line {d.end_line}", code,
                 "Called by: " + (", ".join(map(place, d.callers)) or "nothing in this repo"),
                 "Calls: " + (", ".join(map(place, d.callees)) or "nothing in this repo")]
        if d.changed_with:
            parts.append("Often changed with: " + ", ".join(
                f"{place(c)} x{c.times}" for c in d.changed_with))
        return "\n".join(parts)

    @server.tool()
    def impact(function: str, depth: int = 3) -> str:
        """What could break if this function changes: everything that calls it, directly or
        through other callers (up to `depth` hops), nearest first."""
        f = find(function)
        if isinstance(f, str):
            return f
        hits = endpoint["/api/impact/{fid}"](fid=f.id, depth=max(1, min(depth, 10)))
        return "\n".join(f"{h.distance} hop{'s' * (h.distance > 1)}: {place(h)}" for h in hits) or \
            f"Nothing in this repo calls {f.qualname}."

    @server.tool()
    def check_order(x: str, y: str, start: str | None = None) -> str:
        """Is x always called before y? x and y are function names (res.status) or names of
        outside calls (this.end). From `start` (a function), or from every entry point if omitted.
        A "not always" answer lists call paths that reach y with no x before it."""
        if start is None:
            within = order.entries()
        elif isinstance(s := find(start), str):
            return s
        else:
            within = [s.id]
        r = order.ask(x, y, within)
        lines = [f"{r['answer']} ({r['starts_reaching_y']} starting points reach {y})"]
        for begin, path in list(r["counterexamples"].items())[:5]:
            lines.append(f"from {begin}: " + " -> ".join(path))
        return "\n".join(lines)

    return server
