# Architecture

```mermaid
flowchart LR
    repo[(Your JS/TS repo)] -->|tree-sitter| parse[Parser<br/>functions, calls in order,<br/>imports, branch flags]
    parse --> resolve[Resolver<br/>call -> function,<br/>labelled by how]
    resolve --> db[(Postgres + pgvector<br/>files, functions, calls,<br/>embeddings, extra edges)]
    jelly[Jelly<br/>static analyzer] -.->|callback edges| db
    embed[CodeRankEmbed<br/>CPU] -->|meaning vectors| db
    git[(git history)] -->|co-change| cache[History cache]

    db --> search[Hybrid search<br/>BM25 + vectors, RRF]
    db --> graph[Call graph:<br/>impact, ordering]
    search --> agent[Agent<br/>Qwen3 4B via Ollama]
    graph --> agent
    cache --> api

    search --> api[FastAPI<br/>REST + SSE]
    graph --> api
    agent --> api
    api --> web[React map<br/>Sigma.js]
    api --> mcp[MCP server<br/>Claude Code, Cursor]
```

## The parts, and why each one

| Part | What it does | Why this choice |
|---|---|---|
| **Parser** (`parser.py`) | Reads each file with tree-sitter into functions, the calls each one makes in execution order (arguments before the call), imports, and whether each call always runs or only on some paths. | tree-sitter is fast, error-tolerant and handles JS, TS and JSX with one API. It never runs the code. |
| **Resolver** (`resolve.py`) | Links each call to the function it reaches and labels how: `import`, `same-file`, `qualname`, `name-match`, `builtin`, `external`, `dynamic`, `unresolved`. | Labels let every consumer decide how far to trust a link. Precision over recall: a wrong link misleads the agent more than a missing one. |
| **Store** (`store.py`) | Postgres tables for repos, files, functions, calls, imports, embeddings and extra edges. Bulk loads with `COPY`. Each file's fingerprint includes the parser version. | One database for rows and vectors (pgvector). `COPY` took indexing from 162 s to 4 s. Unchanged files are skipped. |
| **Jelly** (`jelly.py`) | Optional: imports call edges from the Jelly static analyzer (callbacks, dynamic dispatch). | Catches calls tree-sitter can't see; kept in a separate table because they carry no call order. |
| **Search** (`search.py`, `embed.py`) | BM25 over names and code, CodeRankEmbed vectors, merged with Reciprocal Rank Fusion (k = 60). | Keywords find exact names; meaning finds descriptions. RRF merges ranks without tuning weights. CodeRankEmbed is small enough for CPU and MIT licensed. |
| **Agent** (`agent.py`) | A tool-calling loop: keyword search, meaning search, follow calls, read code; at most 8 steps; must answer with function ids or "not found". | A free local model (Qwen3 4B Instruct via Ollama). Every step is logged as an event, so the map can replay it. |
| **Impact** (`graph.py`, `cochange.py`) | Callers up to 3 hops (breadth-first search over the reversed call graph), plus functions that changed together in git history. | Measured: history predicts what you'll edit, the call graph shows what depends on it. Both are shown, labelled. |
| **Ordering** (`order.py`) | "Is X always called before Y?" through the call graph, using call order and the always/sometimes flag, with a counterexample path. | Cheaper than a full control-flow graph and enough for most questions; the limits are measured. |
| **API** (`api.py`) | FastAPI: search, graph, function, impact, and the agent's steps live over Server-Sent Events. Binds to 127.0.0.1. | The website and the MCP server share it. It serves source code, so it never listens on the network by default. |
| **MCP server** (`mcp_server.py`) | The same answers as MCP tools for coding agents. Calls the API's own handlers in-process. | One source of truth for the website and agents. |
| **Map** (`web/`) | React + Sigma.js (WebGL): functions as stations, calls as track, colour by Louvain community, ForceAtlas2 layout. Search, a function panel, and the agent's route replay. | WebGL keeps thousands of nodes smooth; design rules are in `DESIGN.md`. |

## Data flow for one question

1. The browser opens `/api/ask?q=...` (Server-Sent Events).
2. The agent runs in a worker thread; each tool call becomes an event put on a queue.
3. The API streams each event as it happens; the map draws a numbered stop for each function the agent visits.
4. The final answer arrives with the path that led there ("found by meaning search #1, reached by following the calls of res.redirect").

## Safety

- Cartograph only reads code. Nothing in the target repository is executed (Jelly runs static-only, without its approximate-interpretation mode).
- The API and the database listen on localhost only.
- Downloaded models are loaded with the library's own code at a pinned revision, never with `trust_remote_code`.
- Keys come from environment variables (`.env`, never committed).
