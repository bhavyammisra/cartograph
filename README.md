# Cartograph

Ask questions about a JavaScript codebase in plain English and get the exact files and lines that answer them, while watching an AI agent search an interactive map of the code.

**Status: early development.** Nothing works end to end yet. Results will be added here only once they are measured. See [progress](docs/PROGRESS.md).

## Planned

- Hybrid search over a JS/TS repo: keyword (BM25), meaning (code embeddings) and call graph, merged with Reciprocal Rank Fusion
- An agent that plans, searches, follows calls and answers with file and line locations, or says "not found"
- A map of the codebase where you can watch the agent's search path and see why each result was chosen
- Impact analysis checked against the repo's own git history
- An evaluation comparing all of this against a grep-only agent

## Layout

```
engine/   Python: indexer, search, agent, API
web/      TypeScript + React: the code map
docs/     project guide and learning log
reports/  background research
```

## Development

Requires Python 3.12 (via [uv](https://docs.astral.sh/uv/)), Node.js 20+ and Docker.

```bash
docker compose up -d          # Postgres + pgvector
cd engine && uv run pytest    # engine tests
cd web && npm install && npm run dev   # website on http://localhost:5173
```

## License

MIT
