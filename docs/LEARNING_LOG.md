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

---

## Phase 1: Indexer (20 October 2026)

### What we built
`cartograph index <folder>` reads every JS/TS file in a repo and saves, in Postgres, every function, every call inside each function **in the order it runs**, and every import. It then decides which real function each call points to, and labels how sure it is. Re-running it only re-reads files that changed.

Code: `engine/src/cartograph/parser.py` (reading code), `resolve.py` (linking calls), `store.py` (database), `__init__.py` (the `cartograph` command).

### How it works, step by step
1. **Walk the folder**, skipping `node_modules`, `.git`, build output, `.d.ts` and `.min.js`. Files under `test/` or named `.test.`/`.spec.` are kept but marked `is_test`.
2. **Fingerprint each file** (SHA-256 hash). If the fingerprint matches the database, skip the file.
3. **Parse with tree-sitter** into a syntax tree, then walk it:
   - Every function becomes a row, named smartly: `function foo()`, `const foo = () => {}`, `res.send = function send()`, `class Cart { add() }` (named `Cart.add`), `{ pick: () => {} }`. Chained names like `res.set = res.header = function header()` keep every name (**aliases**).
   - Code at the top of a file (outside any function) belongs to a **module** pseudo-function, so its calls aren't lost.
   - Calls are recorded **after their arguments** (post-order): in `foo(bar())`, `bar` runs first, so it gets the lower order number. This is what Phase 10's "X before Y" needs.
   - `require('x')` and `import ... from 'x'` become import rows, including renamed ones (`{ merge: mergeAll }`).
4. **Bulk-save** with Postgres `COPY`.
5. **Resolve every call** (re-run for the whole repo each time, because one changed file can change what other files' calls point to). Labels, most to least sure:

| Label | Meaning | Example |
|---|---|---|
| same-file | function with that name defined in the same file | `this.enabled()` -> `app.enabled` |
| import | name imported from another repo file | `Router.route()` with `Router = require('./router')` |
| qualname | exactly one function has that full name | `res.send()` -> `res.send = function...` |
| name-match | plain `foo()` and only one function named `foo` exists | |
| builtin | a JavaScript built-in | `JSON.parse`, `Object.create`, `Error` |
| external | from an npm package | `debug()`, `finalhandler()` |
| unresolved | can't tell from text alone | `next()`, `this.get()` |
| dynamic | the call has no name | `handlers[name]()` |

### Results on Express (141 files, 50 source + 91 test)
- 3,113 functions. Full index **4.1 s**; re-index with no changes **0.3 s**.
- In Express's own code (`lib/`): same-file 27.2%, builtin 20.8%, external 7.4%, name-match 2.0%, qualname 1.5%, dynamic 1.0%, import 0.2%, **unresolved 40.0%**.
- Hand-checked 10 random `lib/` functions: names and line ranges all correct, calls in the right order.

### Problems we hit (good interview material)
| Problem | Cause | Fix |
|---|---|---|
| The keyword `function` counted as a function | tree-sitter gives the keyword token the same type name | Only real function node types count |
| `Object.create` linked to Express's own `create` | name matching ignored JS built-ins | `builtin` label for built-in objects and functions |
| `users.map` linked to an example's `app.map` | short-name matching on any receiver is guesswork | Short-name match only for plain `foo()`; `x.foo()` needs a full-name match |
| `this.router.handle` linked to `app.handle` | same: `router` is an external package | same fix |
| `this.set` unresolved | `res.set = res.header = function header` kept only one name | Store aliases; every full name also counts by its last part |
| `require('../../')` not followed | folder imports mean `index.js` | Try `<folder>/index.js` too |
| First full index took **162 s** | profiling showed 18.5 s of 20 s waiting on the DB receiving rows one statement at a time | Batched, then Postgres `COPY` bulk load: **4.1 s** |

### Design choice to be able to explain
We chose **precision over recall** for links: a wrong link sends the agent and the impact analysis down the wrong path, while a missing link only means "we don't know". Phase 5 measures both against Jelly.

### Limits (honest)
- tree-sitter sees text structure, not values: `const fn = pick(); fn()` and methods created in loops (`app[method] = ...`, which is how Express defines `app.get`) stay unresolved.
- `var extname = path.extname` style aliases of imported functions aren't traced yet.
- Changing the table layout currently needs a manual reset (`DROP TABLE ...`) and full re-index.

### New tools
- **tree-sitter** (+ JS/TS grammars): parser, turns code into a syntax tree.
- **psycopg 3**: Python's standard Postgres driver; we use its `COPY` support for bulk loading.
- **cProfile**: Python's built-in profiler; it showed where the 162 seconds went instead of guessing.
- **SHA-256 (hashlib)**: file fingerprints for incremental re-indexing.
- **GitHub Actions service container**: CI now starts its own Postgres so the database test runs on every push.

### Interview lines
- "I record calls in post-order so the sequence matches execution order, which my ordering queries depend on."
- "Each call edge carries a confidence label; I deliberately chose precision over recall and measured the unresolved rate: 40% in Express's core."
- "Profiling showed the indexer was waiting on the database, so I switched to COPY bulk loading: 162 s down to 4 s."

---

## Phase 2, part 1: Evaluation harness + BM25 baseline (20 October 2026)

### What we built
The exam every later feature is graded on:
- `cartograph mine` builds questions from a repo's history (`engine/src/cartograph/mine.py`).
- `eval/express/handwritten.jsonl`: 45 questions written against Express's code (27 meaning, 8 usage, 10 structural), every answer checked in the source.
- `cartograph eval` scores any search method (`evaluate.py`) and saves per-question results in `eval/express/results/`.
- The first competitor: **BM25 keyword search** (`search.py`).

### How mining works
1. Go through every commit that touched `lib/`, skipping docs/chore/upgrade commits.
2. For each `#number` in the message, ask GitHub (via `gh api`, cached in `.cache/`) whether it's an issue or a pull request. Pull requests are followed to the issue they fix ("fixes #123"). If there isn't one, the PR's own text is used and flagged `source: pr`.
3. **Question** = issue title + text. **Gold** = functions whose old code the fix changed: read the diff (`git diff -U0` gives the changed line numbers), parse the file as it was before the fix with our Phase 1 parser, and take the smallest function containing each changed line.
4. Keep a question only if its gold functions still exist today (the shortcut, see below) and there are at most 5.

Result: **127 questions** (74 from issues, 53 from PRs). Hand check of 20 random issue questions: **18 clean, 2 noisy (10%)**, details in `eval/express/NOISE_CHECK.md`.

### The scores
| Score | Meaning |
|---|---|
| Acc@k | a correct function is in the top k |
| Recall@10 | share of all correct functions in the top 10 |
| MRR | average of 1/rank of the first correct answer |
| File Acc@5 | a correct *file* is in the top 5 |
| p50 / p95 ms | median / slow-end time per question |

### BM25 results (Express, 275 searchable functions)
| Set | n | Acc@1 | Acc@5 | Acc@10 | MRR | File Acc@5 |
|---|---|---|---|---|---|---|
| Mined, all | 127 | 0.425 | 0.756 | 0.843 | 0.576 | 0.961 |
| Mined, issues only | 74 | 0.311 | 0.703 | 0.811 | 0.492 | 0.932 |
| Mined, PRs only | 53 | 0.585 | 0.830 | 0.887 | 0.693 | 1.000 |
| Mined, answer not named in question | 39 | 0.282 | 0.590 | 0.744 | 0.428 | 0.949 |
| Hand, meaning | 27 | 0.444 | 0.741 | 0.778 | 0.596 | 0.963 |
| Hand, usage | 8 | 0.625 | 0.875 | 1.000 | 0.726 | 1.000 |
| Hand, structural | 10 | 0.200 | 0.700 | 0.900 | 0.400 | 1.000 |

Median time per question: 0.1 ms.

### What the numbers say
- **PR questions are easier** than issue questions (Acc@1 0.59 vs 0.31): the person fixing names the code. Headline numbers should use issues.
- **Questions that name the answer are easier.** Without the name: Acc@1 0.28.
- **Keyword search is weak at structure** (Acc@1 0.20 on "what does X call"): it can't follow calls. That's the gap the call graph and the agent should close.
- **Express is small:** file-level is nearly solved (0.93 or more). The hard part is the right *function*. The headline eval moves to Prettier for this reason.

### Known limits
- Gold is checked against today's code, not the code before each fix. Slightly easier than the strict method; the strict version comes with Prettier.
- Hand questions were drafted by Claude against the code and **still need Bhavyam's review** (`"reviewed": false`) before calling them hand-labelled.
- Grep-agent baseline not run yet (needs an AI API key).

### New tools
- **`gh api`**: GitHub's API from the command line, to read issues and PRs.
- **`git diff -U0`**: a diff with zero context lines, so every hunk header gives exactly the changed line numbers.
- **bm25s**: a fast BM25 library in Python (uses NumPy).
- **JSONL**: one JSON object per line; the standard format for eval sets (easy to append, diff and stream).

### Interview lines
- "I auto-mined 127 questions from Express's history: issue text as the question, functions changed by the fix as the answer, and I hand-checked a sample for a 10% noise rate."
- "I split results by whether the question was written by a user (issue) or the fixer (PR); PR questions were almost twice as easy, so headline numbers use issues only."
- "BM25 handled usage questions well but only got 20% at rank 1 on structural questions, which motivated the call-graph tools."
