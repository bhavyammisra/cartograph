# Changelog

This project follows [semantic versioning](https://semver.org). Nothing is released yet.

## Unreleased (0.1.0)

### Added
- Indexer: tree-sitter parsing of JS/TS/JSX into functions, ordered calls with an always/sometimes-runs flag, and imports; call resolution with confidence labels; incremental re-indexing.
- Search: BM25, CodeRankEmbed meaning search (pgvector) and a hybrid with Reciprocal Rank Fusion.
- Agent: a local tool-calling agent (Qwen3 4B via Ollama) with a grep-only baseline for comparison.
- Optional Jelly call edges for callbacks and dynamic dispatch.
- Impact: callers up to 3 hops plus "often changed with" from git history.
- Ordering: "is X always called before Y?" with counterexample paths.
- API (FastAPI, Server-Sent Events) and MCP server (`cartograph mcp`).
- The map: Sigma.js transit-style code map, function panel, search with provenance, and the agent's route replay.
- Evaluations with question sets and saved results for Express: retrieval, call graph accuracy, impact, ordering, and Claude Code with and without the MCP tools.
- Docker images for the API and the map; CI with lint, types, tests, build and a regression eval; Dependabot.

### Fixed
- Imported names now win over same-file and name-match guesses in the resolver.
- `cartograph index` warns when functions have no meaning vectors (re-parsed functions lose them).
