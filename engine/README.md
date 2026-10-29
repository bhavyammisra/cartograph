# Cartograph

Ask questions about a JavaScript or TypeScript codebase in plain English and get the exact functions, files and lines that answer them. Includes hybrid search (BM25 + code embeddings), a call graph with impact analysis, "is X always called before Y?" queries with proof paths, a local AI agent, an HTTP API for the map website, and an MCP server for coding agents such as Claude Code.

Everything runs locally; your source code never leaves your machine.

## Install

Needs Python 3.12+ and Postgres with pgvector (for example `docker run -p 127.0.0.1:5432:5432 -e POSTGRES_USER=cartograph -e POSTGRES_PASSWORD=cartograph pgvector/pgvector:pg17`).

```bash
uvx cartograph index path/to/repo      # parse functions, calls and imports
uvx cartograph embed path/to/repo      # meaning vectors (CPU)
uvx cartograph serve path/to/repo      # HTTP API on 127.0.0.1:8000
uvx cartograph mcp path/to/repo        # MCP server for coding agents
uvx cartograph order path/to/repo res.status this.end   # is X always before Y?
```

Set `DATABASE_URL` if your database is elsewhere. The agent (`cartograph ask`) uses a local model through [Ollama](https://ollama.com).

Results, the map website, Docker setup and how everything is measured: [github.com/bhavyammisra/cartograph](https://github.com/bhavyammisra/cartograph).

License: MIT
