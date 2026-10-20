# Cartograph

Ask questions about a JavaScript codebase in plain English and get the exact files and lines that answer them, while watching an AI agent search an interactive map of the code.

**Status: early development.** Nothing works end to end yet. Results will be added here only once they are measured. See [progress](docs/PROGRESS.md).

## Early results (Express, measured)

74 questions taken from real GitHub issues in [Express](https://github.com/expressjs/express); the answer is the function the fix changed. Acc@k = a correct function is in the top k results.

| Method | Acc@1 | Acc@5 | Time per question |
|---|---|---|---|
| BM25 keyword search | 0.31 | 0.70 | 0.1 ms |
| Hybrid search (BM25 + CodeRankEmbed, RRF) | 0.41 | 0.78 | 0.15 s |
| Grep-only agent (Qwen3 4B, local) | 0.28 | 0.38 | 32 s |
| **Cartograph agent (Qwen3 4B, local)** | **0.53** | 0.76 | 40 s |

Both agents use the same free model running on a laptop GPU (RTX 2050, 4 GB) and the same step budget; only their tools differ. Express is a small codebase, so these are development numbers: the headline evaluation moves to a larger repository. Method and caveats: [docs/LEARNING_LOG.md](docs/LEARNING_LOG.md).

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
uv run cartograph index ../path/to/js-repo   # parse a repo into the database
uv run cartograph embed ../path/to/js-repo   # add meaning vectors (CPU)
uv run cartograph serve ../path/to/js-repo   # API on http://127.0.0.1:8000 (docs at /docs)
cd web && npm install && npm run dev   # website on http://localhost:5173
```

## License

MIT
