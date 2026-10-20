"""Agentic search: an LLM calls search/graph/read tools until it submits an answer.

Two toolsets share one loop, so the comparison is fair (same model, same budget):
  index agent  search_keyword, search_meaning, graph_neighbors, read_code  (Cartograph)
  grep agent   grep, read_file                                           (the baseline)
Every step is logged as an event; Phase 8 replays these traces on the map.
"""

import json
import os
import re
import time
from pathlib import Path

import psycopg

from .search import BM25, Dense, Doc

# Any OpenAI-compatible endpoint. Local Ollama is free and unlimited; Groq has a free tier.
OLLAMA = "http://localhost:11434"
LLMS = {
    # The non-thinking "instruct" edition: the default qwen3:4b writes ~1,000 tokens of hidden
    # reasoning per step (60-90 s on a 4 GB laptop GPU) and ignores /no_think via this API.
    # num_ctx: Ollama's default 4,096-token window silently cut off longer agent conversations.
    "qwen3-4b": {"base_url": f"{OLLAMA}/v1", "key_env": None, "model": "cartograph-qwen3-4b",
                 "ollama_from": "qwen3:4b-instruct", "num_ctx": 8192},
    "gpt-oss-120b": {"base_url": "https://api.groq.com/openai/v1", "key_env": "GROQ_API_KEY",
                     "model": "openai/gpt-oss-120b"},
}
MAX_STEPS = 8
MAX_RESULT_CHARS = 3000  # keeps tool output inside a small local model's context window


def tool(name: str, description: str, **params) -> dict:
    required = [k for k, v in params.items() if not v.pop("optional", False)]
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": params, "required": required}}}


SUBMIT = tool(
    "submit_answer", "Give the final answer and stop.",
    functions={"type": "array", "items": {"type": "string"},
               "description": "Function ids like F123, best first, at most 5. Empty if not found."},
    not_found={"type": "boolean", "description": "true if nothing in the repo answers it",
               "optional": True})
INDEX_TOOLS = [
    tool("search_keyword", "Keyword (BM25) search over functions. Best for exact names, strings, "
         "setting names, error messages.", query={"type": "string"}),
    tool("search_meaning", "Semantic search over functions. Best for describing what code does "
         "in plain words.", query={"type": "string"}),
    tool("graph_neighbors", "Functions that call this function (callers) or that it calls "
         "(callees), in call order.", function={"type": "string", "description": "e.g. F123"},
         direction={"type": "string", "enum": ["callers", "callees"]}),
    tool("read_code", "Show a function's code with line numbers.",
         function={"type": "string", "description": "e.g. F123"}),
    SUBMIT,
]
GREP_TOOLS = [
    tool("grep", "Search all source files for a regular expression (case-insensitive). "
         "Returns path:line: text.", pattern={"type": "string"}),
    tool("read_file", "Show lines of a file.", path={"type": "string"},
         start_line={"type": "integer"}, end_line={"type": "integer"}),
    tool("submit_answer", "Give the final answer and stop.",
         locations={"type": "array", "items": {"type": "string"},
                    "description": "Code locations like lib/response.js:126, best first, at most 5."},
         not_found={"type": "boolean", "optional": True}),
]
SYSTEM = {
    "index": (
        "You find the functions in a JavaScript repository that answer a developer's question. "
        "Use search_meaning for descriptions of behavior, search_keyword for exact names, strings "
        "and settings, graph_neighbors for what calls what, and read_code to check a candidate. "
        f"You have at most {MAX_STEPS} tool calls. When confident, call submit_answer with the "
        "best function ids first. If the repository does not answer it, submit not_found."),
    "grep": (
        "You find the code in a JavaScript repository that answers a developer's question. "
        "Use grep to search the files and read_file to read them. "
        f"You have at most {MAX_STEPS} tool calls. When confident, call submit_answer with the "
        "best path:line locations first. If the repository does not answer it, submit not_found."),
}


def ensure_ollama_model(cfg: dict) -> None:
    """Create the local model variant (base model + bigger context window). Idempotent."""
    import urllib.error
    import urllib.request

    body = json.dumps({"model": cfg["model"], "from": cfg["ollama_from"],
                       "parameters": {"num_ctx": cfg["num_ctx"]}}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"{OLLAMA}/api/create", body, {"Content-Type": "application/json"}), timeout=120)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Ollama can't create the model ({e.read().decode()[:200]}).\n"
                         f"Download the base model first: ollama pull {cfg['ollama_from']}") from e
    except urllib.error.URLError as e:
        raise SystemExit("Ollama isn't running. Start the Ollama app, or run: ollama serve") from e


class Agent:
    """Callable like the other retrievers: question -> ranked function ids. Extra per-question
    data (answer, steps, tokens, trace) lands in `last_extra` for the evaluator."""

    def __init__(self, conn: psycopg.Connection, root: str, docs: list[Doc], llm: str,
                 mode: str = "index", trace_dir: Path | None = None):
        from openai import OpenAI

        cfg = LLMS[llm]
        key = os.environ.get(cfg["key_env"], "") if cfg["key_env"] else "local"
        if not key:
            raise SystemExit(f"Set {cfg['key_env']} in .env to use {llm}.")
        if "ollama_from" in cfg:
            ensure_ollama_model(cfg)
        self.client, self.model = OpenAI(base_url=cfg["base_url"], api_key=key), cfg["model"]
        self.conn, self.root, self.mode, self.trace_dir = conn, Path(root), mode, trace_dir
        self.docs = {d.id: d for d in docs}
        if mode == "index":
            self.bm25, self.dense = BM25(docs), Dense(conn, root, "coderank")
        self.files = sorted({d.path for d in docs})
        self.last_extra: dict = {}

    # ---- helpers -------------------------------------------------------------------------
    def label(self, fid: int) -> str:
        d = self.docs[fid]
        start, end = self.conn.execute("SELECT start_line, end_line FROM functions WHERE id = %s",
                                       (fid,)).fetchone()
        return f"F{fid} {d.qualname} ({d.path}:{start}-{end})"

    def fid(self, handle) -> int | None:
        m = re.fullmatch(r"F?(\d+)", str(handle).strip())
        return int(m.group(1)) if m and int(m.group(1)) in self.docs else None

    def function_at(self, path: str, line: int) -> int | None:
        """Smallest searchable function containing path:line."""
        row = self.conn.execute(
            """SELECT fn.id FROM functions fn JOIN files f ON f.id = fn.file_id
               JOIN repos r ON r.id = f.repo_id WHERE r.root = %s AND f.path = %s
               AND fn.kind <> 'module' AND %s BETWEEN fn.start_line AND fn.end_line
               ORDER BY fn.end_line - fn.start_line LIMIT 1""",
            (self.root.as_posix(), path, line)).fetchone()
        return row[0] if row and row[0] in self.docs else None

    # ---- index tools ---------------------------------------------------------------------
    def search(self, retriever, query: str) -> tuple[str, list[int]]:
        ids = retriever(query, 10)
        return "\n".join(self.label(i) for i in ids) or "no results", ids

    def neighbors(self, handle, direction: str) -> tuple[str, list[int]]:
        fid = self.fid(handle)
        if fid is None:
            return f"unknown function {handle}", []
        if direction == "callers":
            rows = self.conn.execute(
                """SELECT c.caller_id, min(c.seq) FROM calls c WHERE c.callee_id = %s
                   GROUP BY 1 ORDER BY 1""", (fid,)).fetchall()
            ids = [r[0] for r in rows if r[0] in self.docs]
            return ("\n".join(self.label(i) for i in ids) or "no known callers"), ids
        rows = self.conn.execute(
            """SELECT c.callee_id, coalesce(c.receiver || '.', '') || coalesce(c.name, '?'),
                      c.resolution FROM calls c WHERE c.caller_id = %s ORDER BY c.seq""",
            (fid,)).fetchall()
        ids = list(dict.fromkeys(r[0] for r in rows if r[0] in self.docs))
        lines = [self.label(r[0]) if r[0] in self.docs else f"{r[1]} ({r[2]})" for r in rows]
        return "\n".join(dict.fromkeys(lines)) or "calls nothing", ids

    def read_code(self, handle) -> tuple[str, list[int]]:
        fid = self.fid(handle)
        if fid is None:
            return f"unknown function {handle}", []
        start, code = self.conn.execute("SELECT start_line, code FROM functions WHERE id = %s",
                                        (fid,)).fetchone()
        lines = code.splitlines()[:80]
        return self.label(fid) + "\n" + "\n".join(f"{start + i}: {t}" for i, t in
                                                  enumerate(lines)), [fid]

    # ---- grep tools ----------------------------------------------------------------------
    def grep(self, pattern: str) -> tuple[str, list[int]]:
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error:
            rx = re.compile(re.escape(pattern), re.IGNORECASE)
        hits, ids = [], []
        for path in self.files:
            for n, text in enumerate((self.root / path).read_text(
                    encoding="utf-8", errors="replace").splitlines(), 1):
                if rx.search(text):
                    hits.append(f"{path}:{n}: {text.strip()[:120]}")
                    if (fid := self.function_at(path, n)) and fid not in ids:
                        ids.append(fid)
                if len(hits) >= 40:
                    return "\n".join(hits) + "\n(more matches cut off)", ids
        return "\n".join(hits) or "no matches", ids

    def read_file(self, path: str, start: int, end: int) -> tuple[str, list[int]]:
        if path not in self.files:
            return f"unknown file {path}", []
        lines = (self.root / path).read_text(encoding="utf-8", errors="replace").splitlines()
        start, end = max(1, int(start)), min(len(lines), int(end), int(start) + 79)
        return "\n".join(f"{n}: {lines[n - 1]}" for n in range(start, end + 1)), []

    # ---- the loop ------------------------------------------------------------------------
    def run_tool(self, name: str, args: dict) -> tuple[str, list[int]]:
        if self.mode == "index":
            if name == "search_keyword":
                return self.search(self.bm25, args["query"])
            if name == "search_meaning":
                return self.search(self.dense, args["query"])
            if name == "graph_neighbors":
                return self.neighbors(args["function"], args.get("direction", "callees"))
            if name == "read_code":
                return self.read_code(args["function"])
        else:
            if name == "grep":
                return self.grep(args["pattern"])
            if name == "read_file":
                return self.read_file(args["path"], args.get("start_line", 1),
                                      args.get("end_line", 80))
        return f"unknown tool {name}", []

    def answer_ids(self, args: dict) -> list[int]:
        if self.mode == "index":
            ids = [self.fid(h) for h in args.get("functions") or []]
        else:
            ids = []
            for loc in args.get("locations") or []:
                m = re.fullmatch(r"(.+?):(\d+)", str(loc).strip())
                ids.append(self.function_at(m.group(1), int(m.group(2))) if m else None)
        return list(dict.fromkeys(i for i in ids if i is not None))

    def __call__(self, question: str, k: int = 50) -> list[int]:
        messages = [{"role": "system", "content": SYSTEM[self.mode]},
                    {"role": "user", "content": question}]
        tools = INDEX_TOOLS if self.mode == "index" else GREP_TOOLS
        seen: list[int] = []  # every function the agent was shown, in order
        events, answer, tokens, not_found = [], None, 0, False
        for step in range(MAX_STEPS + 1):
            start = time.perf_counter()
            resp = self.client.chat.completions.create(
                model=self.model, messages=messages, tools=tools, temperature=0)
            tokens += resp.usage.total_tokens if resp.usage else 0
            msg = resp.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))
            if not msg.tool_calls:
                events.append({"step": step, "type": "text", "text": (msg.content or "")[:500]})
                messages.append({"role": "user",
                                 "content": "Call submit_answer now with your best answer."})
                continue
            for call in msg.tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if name == "submit_answer":
                    answer, not_found = self.answer_ids(args), bool(args.get("not_found"))
                    events.append({"step": step, "type": "answer", "args": args,
                                   "ids": answer, "ms": round((time.perf_counter() - start) * 1000)})
                    break
                if step == MAX_STEPS:  # out of budget: no more tools, only an answer
                    result, ids = "Tool budget used up. Call submit_answer now.", []
                else:
                    try:
                        result, ids = self.run_tool(name, args)
                    except (KeyError, TypeError, ValueError) as e:
                        result, ids = f"bad arguments: {e}", []
                seen += [i for i in ids if i not in seen]
                events.append({"step": step, "type": "tool", "tool": name, "args": args,
                               "ids": ids, "ms": round((time.perf_counter() - start) * 1000)})
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": result[:MAX_RESULT_CHARS]})
            if answer is not None:
                break

        answer = answer or []
        # Ranking for Acc@k: the submitted answer first, then everything else the agent was
        # shown, in the order it saw it. Both agents are scored the same way.
        ranked = answer + [i for i in seen if i not in answer]
        self.last_extra = {"answer": answer, "not_found": not_found, "steps": len(events),
                           "tokens": tokens, "events": events}
        return ranked[:k]
