# Learning log

One entry per phase: what was built, which tools were used and why, problems hit, and what to say in an interview.

---

## Phase 0: Setup (20 October 2026)

### What we built
No features yet. We built the workshop: a public GitHub repo, a folder for each part of the project, a working Python package, a working website, a database recipe, a codebase to practise on, and automatic tests on GitHub.

```
cartograph/
  engine/               Python package (the brain, built from Phase 1)
  web/                  React website (the map, built from Phase 7)
  docs/                 project guide + this log
  reports/              research
  targets/express/      the codebase we analyze (downloaded, not committed)
  docker-compose.yml    recipe to start Postgres + pgvector
  .github/workflows/    automatic tests on every push
```

### Tools used, and why

| Tool | What it did in this phase | Why this tool |
|---|---|---|
| **Git + GitHub** | Repo `bhavyammisra/cartograph`, public. Every step is committed and pushed, so GitHub always matches the laptop. | Version history, and recruiters can see steady progress. |
| **GitHub CLI (`gh`)** | Created the repo from the terminal. | Faster than clicking through the website. |
| **`.gitignore`** | A list of files git must never save: `.venv`, `node_modules`, `.env` (secrets), `targets/`. | Keeps the repo small and keeps passwords and other people's code out. |
| **`.gitattributes`** | Forces all text files to use Linux-style line endings (LF). | Windows uses different line endings (CRLF); without this, files look "changed" on other computers for no reason. |
| **uv** | Created the Python package, downloaded Python 3.12 for this project only, installed pytest and ruff. | Much faster than pip, and it records exact versions in `uv.lock` so anyone gets the same setup. |
| **Python 3.12** (not your 3.14) | The engine's Python version. | AI libraries we need later (like ONNX Runtime) often lag behind brand-new Python versions. |
| **`pyproject.toml`** | The engine's settings: name, version, license, the `cartograph` command, dependencies. | The standard Python project file; also what lets us publish to PyPI later. |
| **pytest** | One test: `cartograph --version` prints `cartograph 0.1.0`. | Proves testing works from day one. |
| **Ruff** | Checks Python code for style problems and common bugs. | Very fast, the current industry default. |
| **Vite + React + TypeScript** | Created the website, removed the template's demo content, added a placeholder page and a favicon. | Vite is the standard fast tool for React sites. |
| **oxlint** | Checks the website's code (came with the Vite template). | Fast linter, same job as Ruff for TypeScript. |
| **Docker Compose file** | Recipe to start Postgres 17 with pgvector. | One command gives anyone the same database. Not run yet: Docker Desktop isn't installed. |
| **`.env.example`** | Shows which secret settings exist (database address, AI key) without real values. | Real secrets go in `.env`, which git ignores. Standard practice. |
| **MIT License** | Lets anyone use the code with credit. | Without a license, nobody is legally allowed to reuse public code. |
| **GitHub Actions (CI)** | On every push, GitHub runs Ruff + pytest for the engine and lint + build for the website. | A green check on every commit shows the code works, not just on your laptop. |

### Problems we hit
- **uv's "Missing expected target directory" error** when installing Python 3.12. It only failed to create an optional shortcut link (Windows restricts these unless Developer Mode is on). Python 3.12 installed fine, so we ignored it.
- **Line-ending warnings (LF vs CRLF)** on the first commit. Fixed with `.gitattributes`.

### Checked
- `uv run pytest`: 1 passed. `ruff check`: clean. `cartograph --version` works.
- Website builds, and shows correctly in the browser at desktop and phone width with no console errors.

### Database step (finished after installing Docker)
- Installed WSL 2 (Windows' built-in Linux layer) and Docker Desktop.
- `docker compose up -d --wait` downloaded the `pgvector/pgvector:pg17` image and started Postgres; `--wait` holds until the healthcheck (`pg_isready`) says the database accepts connections.
- Ran `CREATE EXTENSION vector` (pgvector 0.8.7), stored three 3-number vectors and sorted by cosine distance (`<=>`) to `[1,0,0]`: payments 0.000, charge 0.006, auth 1.000. Closest meaning first, which is exactly what meaning search does later with 768-number vectors.
- The data lives in a Docker **volume** (`pgdata`), so it survives restarting the container.

### Interview lines
- "The repo is a monorepo: a Python engine and a TypeScript frontend, each with its own linter and tests, both run by GitHub Actions on every push."
- "I pinned Python 3.12 with uv and committed the lock file, so the environment is reproducible."
- "Secrets live in an ignored `.env` file; the repo only has `.env.example`."
