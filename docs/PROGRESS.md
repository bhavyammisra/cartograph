# Progress

Read this first when starting a new session. It says where the project stands right now. Rules for working live in `CLAUDE.md`; the full plan is `docs/PROJECT_GUIDE.md`; per-phase lessons are `docs/LEARNING_LOG.md`; background research is in `reports/`.

**Last updated:** 20 October 2026

## Current state
- **Phase:** 0 done. Phase 1 (indexer) not started.
- **Next step:** Phase 1: parse `targets/express` with tree-sitter, extract functions, calls (in order) and imports, store in Postgres.
- **Blocked on:** nothing.

## Phases

| # | Phase | Status |
|---|---|---|
| 0 | Setup: repo, engine, web, CI, database | Done |
| 1 | Indexer: tree-sitter functions, calls, imports into Postgres | Not started |
| 2 | Eval harness: auto-mined + hand-labelled questions, grep and BM25 baselines | Not started |
| 3 | Embeddings (CodeRankEmbed) + BM25 + RRF hybrid search | Not started |
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
| 2026-10-20 | MIT license, public repo | Standard for portfolio tools. |

## Environment
- Windows 11. Python 3.12.15 (uv-managed), uv 0.13.2, Node 24, npm 11, Git 2.53, gh signed in as `bhavyammisra`.
- `targets/express` cloned locally (141 .js files, 50 outside tests, 6,182 commits); `targets/` is gitignored.
- Docker 29.8.2 (Desktop, WSL 2). Postgres 17 + pgvector 0.8.7 via `docker compose up -d --wait`; `vector` extension created in DB `cartograph`.
- Website dev server config: `.claude/launch.json` (port 5173).

## Known issues
- uv prints "Missing expected target directory for Python minor version link" on Windows. Harmless (optional symlink).
- Shells opened before Docker was installed can't find `docker`; restart the terminal or add `C:\Program Files\Docker\Dockeresourcesin` to PATH.
