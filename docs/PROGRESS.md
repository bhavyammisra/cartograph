# Progress

Read this first when starting a new session. It says where the project stands right now. Rules for working live in `CLAUDE.md`; the full plan is `docs/PROJECT_GUIDE.md`; per-phase lessons are `docs/LEARNING_LOG.md`; background research is in `reports/`.

**Last updated:** 27 October 2026

## Current state
- **Phase:** 11 in progress: MCP server built and tested (`cartograph mcp <repo>`); the Claude Code measurement is waiting for Bhavyam to sign the `claude` CLI in (`claude auth login`). The two resolver errors found in Phase 10 are fixed (imported names now win over same-file and name-match guesses). Deferred from Phase 5: switching the headline eval to Prettier.
- **Next step:** after `claude auth login`, run `uv run --project engine python scripts/claude_eval.py --repo targets/express --questions eval/express/mined.jsonl --sample 20 --model sonnet` and write `eval/express/MCP.md`; then Phase 12. Re-run the agent eval (the text-recovery rule postdates the Phase 4 numbers). Before publishing numbers: index Prettier and mine its questions for the headline eval. Optional any time: strong-model comparison on the Groq free tier (needs Bhavyam's `GROQ_API_KEY` in `.env`).
- **Blocked on:** Bhavyam: sign the Claude Code CLI in (`claude auth login`) for the Phase 11 measurement; review `eval/express/handwritten.jsonl` and `eval/express/order.jsonl`, and set `"reviewed": true`.

## Phases

| # | Phase | Status |
|---|---|---|
| 0 | Setup: repo, engine, web, CI, database | Done |
| 1 | Indexer: tree-sitter functions, calls, imports into Postgres | Done (Express: 3,113 functions, 4.1 s full / 0.3 s incremental; lib/ calls 40% unresolved) |
| 2 | Eval harness: auto-mined + hand-labelled questions, grep and BM25 baselines | Done (grep agent finished in Phase 4) |
| 3 | Embeddings (CodeRankEmbed) + BM25 + RRF hybrid search | Done (issues Acc@5: BM25 0.703, dense 0.743, hybrid 0.784; jina dense 0.878 but 17x slower) |
| 4 | Agent loop with event logging | Done (issues: index agent Acc@1 0.527 / Acc@5 0.757 vs grep agent 0.284 / 0.378, local Qwen3 4B) |
| 5 | Precise call graph with Jelly, accuracy report; switch eval to Prettier | Done except Prettier (our links ~97% correct on a hand sample; recall vs Jelly 79%; see eval/express/CALLGRAPH.md) |
| 6 | FastAPI server + SSE stream | Done (search, graph, function, impact, live agent stream; 32 tests) |
| 7 | Map: Sigma.js, communities, semantic zoom | Done (transit map + yellow route on selection; search, station-sign panel, lines key, deep links, desktop + phone, light + dark) |
| 8 | Trace replay + "why this result" | Done (live route with numbered stops, follow camera, replay, provenance on search and answers, `#ask=` links; 33 engine + 5 web tests) |
| 9 | Impact analysis validated against git co-change | Done (Express, 245 cases, rolling: recall@5 call graph 0.050, history 0.294, both 0.313, same-file baseline 0.266; "Often changed with" in the panel) |
| 10 | "X before Y" ordering queries + mini benchmark | Done (35 questions on Express: engine 33/35 = 0.943, naive line-order baseline 12/35 = 0.343; counterexample paths with file:line) |
| 11 | MCP server, measured with Claude Code | Server done (4 tools, tested over stdio); measurement waiting for CLI sign-in |
| 12 | Industry polish: tests, CI, packaging, Docker, docs | Not started |
| 13 | Publish: PyPI, demo site (launch checklist), video, write-up | Not started |

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-20 | Name: Cartograph | It maps code. |
| 2026-10-20 | Python engine, TypeScript + React web | Python shows AI/ML skills and has the retrieval tooling; TS keeps web skills visible. |
| 2026-10-20 | Python 3.12 pinned via uv | AI libraries lag behind 3.14. |
| 2026-10-20 | Local Postgres + pgvector in Docker; no Supabase for now | One user, one machine; source code never leaves the laptop. Demo site will replay recorded traces, so it needs no database. |
| 2026-10-20 | JavaScript/TypeScript only | Samsung brief was JS; one language measured properly beats many unmeasured. |
| 2026-10-20 | Targets: Express (development), Prettier (headline eval), ESLint (generalization) | Express is small; Prettier is in SWE-PolyBench for external comparison; ESLint is in BugsJS. |
| 2026-10-20 | Eval harness before the agent (Phase 2) | Every later feature gets measured the day it lands. |
| 2026-10-20 | Baseline is a grep-only agent, not just BM25 | Fair comparison for the 2026 "grep vs index" debate. |
| 2026-10-20 | Embedding model: CodeRankEmbed (137M) default, jina-code-embeddings-0.5b as comparison | Small enough for CPU; strong published code-retrieval results. |
| 2026-10-20 | Call links favor precision over recall: short-name match only for plain `foo()` calls | Wrong links mislead the agent and impact analysis; Phase 5 measures recall vs Jelly. |
| 2026-10-20 | Bulk load with Postgres COPY | Row INSERTs took 162 s on Express, COPY 4.1 s. |
| 2026-10-20 | Eval gold checked against HEAD, not pre-fix snapshots (Express) | Simpler and fast; strict snapshots for the Prettier headline eval. |
| 2026-10-20 | Headline mined numbers use issue-sourced questions only | PR text is written by the fixer and names the code (Acc@1 0.59 vs 0.31). |
| 2026-10-20 | CodeRankEmbed is the default embedding model; jina for comparison only | jina: best Acc@5 but 17x slower and CC-BY-NC (non-commercial). |
| 2026-10-20 | Load models with transformers' built-in code, revision pinned; no trust_remote_code | Never execute downloaded model code. |
| 2026-10-20 | Agent LLM: free only. Ollama + Qwen3 4B locally, Groq free tier for a stronger model | Bhavyam wants no paid API; local fits the brief's CPU / minimal-GPU constraint. |
| 2026-10-20 | Agent model: Qwen3 4B Instruct (non-thinking), 8K context, 1,024-token reply cap | The thinking edition was 3x+ slower; the default 4K window cut conversations; the cap stops runaway generations. |
| 2026-10-20 | Agent ranking = submitted answer, then everything it was shown | Same rule for both agents; the answer alone is reported as Acc@answer. |
| 2026-10-20 | Evals checkpoint after every question | A crash at question 120 lost a 70-minute run. |
| 2026-10-20 | Jelly runs static-only (no --approx), via npx pinned to 0.13.0 | Approximate interpretation executes the analyzed code. |
| 2026-10-20 | Keep both call graphs: tree-sitter edges in `calls`, Jelly edges in `extra_edges` | Tree-sitter catches run-time-wired methods, Jelly catches callbacks; neither alone is enough. |
| 2026-10-20 | Parser version is part of each file's fingerprint | Parser changes re-parse every file automatically. |
| 2026-10-20 | API binds to 127.0.0.1 only | It serves the indexed source code. |
| 2026-10-20 | Agent stream = SSE from a worker thread through a queue | Browsers support SSE natively (`EventSource`); one-way push is all the map needs. |
| 2026-10-20 | Map design: Transit Diagram (chosen by Bhavyam); rules in DESIGN.md | Functions as stations, calls as track; line colours never used for controls. |
| 2026-10-20 | Hybrid design: transit colours for exploring; picking a function greys the map and lights its route in reserved yellow | Bhavyam's call after the Terminal Wayfinding mockup; amber line swapped for raspberry. |
| 2026-10-20 | Agent answers written as prose are recovered only by exact names of functions it was shown, and labelled in the UI | The 4B model sometimes never calls submit; guessing from partial words would invent answers. |
| 2026-10-21 | Impact is checked by rolling evaluation: each commit predicted from older commits only | A fixed 80/20 split left 21 test commits; rolling gives 82 with no peeking. |
| 2026-10-21 | Panel shows "Often changed with" (history) beside callers (call graph); no red ripple on the map | History predicts edits 6x better; red would break the yellow-route rule and clash with the red line. |
| 2026-10-25 | Ordering = call order + an "always runs / sometimes runs" flag per call, followed through the call graph | Branch-blind line order scored 0.343 on the benchmark; every "not always" answer needs a proof path. |
| 2026-10-27 | MCP tools call the HTTP API's own endpoint functions in-process | One source of truth: the website and Claude get the same answers. |
| 2026-10-27 | Claude Code eval: Sonnet, Read/Grep/Glob only (no shell, no web), 20 issue questions, with vs without Cartograph | Saves Bhavyam's allowance; no shell stops `git log` from revealing the fix commit. |
| 2026-10-20 | Sigma.js 3.0.3 (not 4) | Sigma 4's new styling API was too new to verify. |
| 2026-10-20 | Screenshots via scripts/capture.py (DevTools protocol) | Headless Edge can't emulate phones (min 496 px) and doesn't wait for data. |
| 2026-10-20 | MIT license, public repo | Standard for portfolio tools. |

## Environment
- Windows 11. Python 3.12.15 (uv-managed), uv 0.13.2, Node 24, npm 11, Git 2.53, gh signed in as `bhavyammisra`.
- `targets/express` cloned locally (141 .js files, 50 outside tests, 6,182 commits); `targets/` is gitignored.
- Docker 29.8.2 (Desktop, WSL 2). Postgres 17 + pgvector 0.8.7 via `docker compose up -d --wait`; `vector` extension created in DB `cartograph`.
- Eval: `cartograph mine ../targets/express --github expressjs/express --out ../eval/express/mined.jsonl` (GitHub responses cached in `engine/.cache/github`); `cartograph eval ../targets/express --questions ../eval/express/<set>.jsonl`.
- Embeddings: `cartograph embed ../targets/express [--model jina]`; `cartograph eval ... --retriever dense|hybrid --model coderank|jina`. Models cached in `~/.cache/huggingface`.
- Agent: the Ollama app (auto-starts) serves localhost:11434; Cartograph creates `cartograph-qwen3-4b` from `qwen3:4b-instruct` itself. `cartograph ask ../targets/express "<question>"`; `cartograph eval ... --retriever agent|grep-agent` (about 1 to 1.5 h per 127 questions, resumes after a crash). Live status: `& .\scripts\watch-eval.ps1`.
- Jelly: `cartograph jelly ../targets/express --entries lib examples index.js --out ../eval/express/callgraph-vs-jelly.json`. Needs the target's dependencies installed (`npm install --ignore-scripts --omit=dev` inside `targets/express`). Re-run after every `index` (Jelly edges are tied to function ids). After a re-index, jina embeddings are gone too (`cartograph embed ... --model jina` to restore, ~15 min).
- API: `uv run --project engine cartograph serve targets/express` (from the repo root) on http://127.0.0.1:8000, docs at /docs. Needs Postgres (Docker) and, for `/api/ask`, Ollama.
- Web: start the API (above), then `npm run dev` in `web/` (http://localhost:5173, proxies /api). Screenshots: `uv run --with websocket-client --no-project python scripts/capture.py --url http://localhost:5173/ --out <file> [--width 375 --height 812 --scale 2 --mobile] [--scheme light] --wait-for .stats`.
- Design context: PRODUCT.md, DESIGN.md, `.impeccable/surfaces/` (direction contract). The impeccable skill reads these.
- Laptop: i5-12450HX, 12 GB RAM, RTX 2050 (4 GB), ~45 GB free disk.
- Website dev server config: `.claude/launch.json` (port 5173).

## Known issues
- Changing an existing table's columns needs a manual reset (`DROP TABLE extra_edges, embeddings, imports, calls, functions, files, repos CASCADE`) then re-index; new tables are created automatically, and parser changes re-parse automatically (PARSER_VERSION).
- uv prints "Missing expected target directory for Python minor version link" on Windows. Harmless (optional symlink).
- Shells opened before Docker was installed can't find `docker`; restart the terminal or add `C:\Program Files\Docker\Docker\resources\bin` to PATH.
