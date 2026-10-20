# Progress

Read this first when starting a new session. It says where the project stands right now. Rules for working live in `CLAUDE.md`; the full plan is `docs/PROJECT_GUIDE.md`; per-phase lessons are `docs/LEARNING_LOG.md`; background research is in `reports/`.

**Last updated:** 20 October 2026

## Current state
- **Phase:** 3 done. Phase 4 (agent) starting. Phase 2's grep-agent baseline is built together with the agent (same loop, fewer tools).
- **Next step:** Phase 4 with a free local model: Ollama + Qwen3 4B (main), Groq free tier `gpt-oss-120b` (strong comparison, needs Bhavyam's free key).
- **Blocked on:** Bhavyam: review `eval/express/handwritten.jsonl` and set `"reviewed": true`.

## Phases

| # | Phase | Status |
|---|---|---|
| 0 | Setup: repo, engine, web, CI, database | Done |
| 1 | Indexer: tree-sitter functions, calls, imports into Postgres | Done (Express: 3,113 functions, 4.1 s full / 0.3 s incremental; lib/ calls 40% unresolved) |
| 2 | Eval harness: auto-mined + hand-labelled questions, grep and BM25 baselines | In progress (BM25 done: mined issues Acc@5 0.703; hand structural Acc@1 0.20; grep agent left) |
| 3 | Embeddings (CodeRankEmbed) + BM25 + RRF hybrid search | Done (issues Acc@5: BM25 0.703, dense 0.743, hybrid 0.784; jina dense 0.878 but 17x slower) |
| 4 | Agent loop with event logging | Not started |
| 5 | Precise call graph with Jelly, accuracy report; switch eval to Prettier | Not started |
| 6 | FastAPI server + SSE stream | Not started |
| 7 | Map: Sigma.js, communities, semantic zoom | Not started |
| 8 | Trace replay + "why this result" | Not started |
| 9 | Impact analysis validated against git co-change | Not started |
| 10 | "X before Y" ordering queries + mini benchmark | Not started |
| 11 | MCP server, measured with Claude Code | Not started |
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
| 2026-10-20 | MIT license, public repo | Standard for portfolio tools. |

## Environment
- Windows 11. Python 3.12.15 (uv-managed), uv 0.13.2, Node 24, npm 11, Git 2.53, gh signed in as `bhavyammisra`.
- `targets/express` cloned locally (141 .js files, 50 outside tests, 6,182 commits); `targets/` is gitignored.
- Docker 29.8.2 (Desktop, WSL 2). Postgres 17 + pgvector 0.8.7 via `docker compose up -d --wait`; `vector` extension created in DB `cartograph`.
- Eval: `cartograph mine ../targets/express --github expressjs/express --out ../eval/express/mined.jsonl` (GitHub responses cached in `engine/.cache/github`); `cartograph eval ../targets/express --questions ../eval/express/<set>.jsonl`.
- Embeddings: `cartograph embed ../targets/express [--model jina]`; `cartograph eval ... --retriever dense|hybrid --model coderank|jina`. Models cached in `~/.cache/huggingface`.
- Laptop: i5-12450HX, 12 GB RAM, RTX 2050 (4 GB), ~45 GB free disk.
- Website dev server config: `.claude/launch.json` (port 5173).

## Known issues
- Schema changes need a manual reset (`DROP TABLE imports, calls, functions, files, repos CASCADE`) then re-index; no migrations yet.
- uv prints "Missing expected target directory for Python minor version link" on Windows. Harmless (optional symlink).
- Shells opened before Docker was installed can't find `docker`; restart the terminal or add `C:\Program Files\Docker\Docker\resources\bin` to PATH.
