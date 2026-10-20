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

---

## Phase 3: Meaning search + hybrid search (20 October 2026)

### What we built
- `cartograph embed <repo> --model coderank|jina`: turns every searchable function into a vector and stores it in Postgres with pgvector (`engine/src/cartograph/embed.py`, `store.py`).
- Two new search methods (`search.py`): **Dense** (embed the question, return the closest function vectors with pgvector's `<=>` cosine distance) and **Hybrid** (BM25 + Dense merged with Reciprocal Rank Fusion).
- `cartograph eval ... --retriever bm25|dense|hybrid --model coderank|jina`.

### How it works
1. **Embedding a function:** the text `// lib/response.js: res.send` + the function's code goes through the model. Because the function's own text starts at `function send(...)` and misses the `res.send =` part, the file and full name are put in front.
2. **Pooling:** the model outputs one vector per token; we need one per function. CodeRankEmbed uses the first token's vector (**CLS pooling**), jina the last token's (**last-token pooling**). Both settings were read from each model's own config, not guessed. Vectors are normalized to length 1 so cosine similarity is a plain dot product.
3. **Questions get a prefix** the model was trained with ("Represent this query for searching relevant code: ").
4. **RRF:** each function gets `1/(60 + rank)` from every list it appears in; highest total wins. Ranks, not scores, because BM25 scores and cosine scores are on different scales. 60 is the constant from the original RRF paper (Cormack et al., 2009).

### Results (Express)
**Mined questions, issues only (n=74), the headline set:**
| Method | Acc@1 | Acc@5 | Acc@10 | MRR | p50 time/question |
|---|---|---|---|---|---|
| BM25 | 0.311 | 0.703 | 0.811 | 0.492 | 0.1 ms |
| Dense, CodeRankEmbed | 0.392 | 0.743 | 0.824 | 0.550 | 147 ms |
| Hybrid, CodeRankEmbed | 0.405 | 0.784 | 0.838 | 0.579 | 147 ms |
| Dense, jina | 0.405 | **0.878** | **0.919** | **0.604** | 2,085 ms |
| Hybrid, jina | **0.432** | 0.811 | 0.905 | 0.603 | 2,179 ms |

**Hand-drafted questions, by type (Acc@1 / Acc@5):**
| Method | Meaning (27) | Usage (8) | Structural (10) |
|---|---|---|---|
| BM25 | 0.444 / 0.741 | **0.625 / 0.875** | 0.200 / 0.700 |
| Dense, CodeRankEmbed | 0.704 / **0.926** | 0.500 / 0.750 | 0.200 / 0.500 |
| Hybrid, CodeRankEmbed | 0.556 / 0.852 | **0.625 / 0.875** | 0.100 / 0.700 |
| Dense, jina | **0.815 / 0.926** | 0.500 / 0.750 | 0.100 / 0.700 |
| Hybrid, jina | 0.593 / 0.815 | 0.500 / 0.750 | 0.200 / 0.700 |

**Cost:** embedding 275 functions on CPU took 55 s with CodeRankEmbed (about 18 s is model loading) vs 932 s with jina (17x slower). Per question: about 40 to 150 ms vs 400 to 2,100 ms.

### What the numbers say
- **Meaning search beats keywords on real user questions** (Acc@5 0.70 to 0.74 with CodeRankEmbed, 0.88 with jina).
- **Hybrid helps the small model** (0.74 to 0.78) but **hurts the big one** (0.88 to 0.81): when one list is much better, averaging in a worse one drags it down. RRF is not automatically better.
- **Keywords still win usage questions** (exact strings like `'etag fn'`).
- **Nobody solves structural questions** ("what does res.redirect call?", Acc@1 0.1 to 0.2). That needs the call graph, which is the agent's job in Phase 4.
- **jina is the most accurate but can't be our default:** 17x slower, and licensed CC-BY-NC-4.0 (non-commercial) while Cartograph is MIT. CodeRankEmbed (MIT) stays the default; jina is the "what a bigger model buys you" reference.

### Problems we hit
| Problem | Fix |
|---|---|
| CodeRankEmbed ships custom Python code to execute | This `transformers` version has the same model built in, so we load it **without** running downloaded code, and pin the exact model commit |
| sentence-transformers 6.1 crashed with the built-in NomicBert (`safe_serialization` argument) | Dropped the wrapper; load with `transformers` directly and do pooling ourselves (~30 lines) |
| My first RRF test expected the wrong winner | 1st + 3rd (1/61 + 1/63) beats 2nd + 2nd (2/62); fixed the test, RRF was right |
| jina's license is non-commercial | Comparison only, documented in `embed.py` |

### Known limits
- Code past 512 tokens is cut off when embedding (CPU speed).
- No HNSW index yet: vector search is an exact scan, fine for thousands of functions; the index comes when a repo needs it.

### New tools
- **PyTorch:** runs the neural network on CPU.
- **transformers (Hugging Face):** loads the model and its tokenizer (the part that splits text into tokens).
- **pgvector Python adapter:** sends NumPy vectors straight into Postgres.
- **Hugging Face Hub:** where the models are downloaded from (cached in `~/.cache/huggingface`).

### Interview lines
- "Dense retrieval with a 137M code model raised Acc@5 on real GitHub issues from 0.70 to 0.74, and hybrid RRF to 0.78. A 494M model reached 0.88 but was 17x slower and non-commercially licensed, so I kept the small one as default."
- "RRF isn't free accuracy: it helped the weaker retriever and hurt the stronger one, because fusion averages in the worse list."
- "I avoided `trust_remote_code` by loading the model through the library's built-in architecture, with the model revision pinned."

---

## Phase 4: The AI agent (20 October 2026)

### What we built
- `engine/src/cartograph/agent.py`: an agent loop. An LLM gets the question and a set of tools, calls them one at a time, reads the results, and finishes with `submit_answer` (or "not found"). At most 8 tool calls.
- Two toolsets on the **same loop and same model**, so the comparison is fair:
  - **Index agent (Cartograph):** `search_keyword` (BM25), `search_meaning` (CodeRankEmbed + pgvector), `graph_neighbors` (callers / callees from the Phase 1 call graph), `read_code`.
  - **Grep agent (the baseline):** `grep` (regex over the source files) and `read_file`. This is how Claude Code, Codex and Gemini CLI explore code.
- Every step is logged (tool, input, functions shown, time). These traces drive the map animation in Phase 8.
- `cartograph ask <repo> "<question>"` prints the agent's steps. `cartograph eval ... --retriever agent|grep-agent` scores it.
- `scripts/watch-eval.ps1`: a live status screen for long runs.

### The AI brain: free and local
- **Ollama** runs **Qwen3 4B Instruct (2507)** on the laptop's RTX 2050 (4 GB); about 55% of the model fits on the GPU, the rest runs on the CPU.
- Cartograph talks to it through the standard `openai` Python library (Ollama speaks the same API), so switching to a cloud model later is one setting.
- Cost: $0. Time: about 16 to 40 s per question.

### Results (Express)
**Real GitHub issues (n=74), the headline set:**
| Method | Acc@1 | Acc@5 | MRR | Time per question |
|---|---|---|---|---|
| BM25 keyword search | 0.311 | 0.703 | 0.492 | 0.1 ms |
| Hybrid search (BM25 + CodeRankEmbed, RRF) | 0.405 | 0.784 | 0.579 | 0.15 s |
| Meaning search, jina (comparison only) | 0.405 | **0.878** | 0.604 | 2.1 s |
| **Index agent (Cartograph, Qwen3 4B)** | **0.527** | 0.757 | **0.627** | 40 s |
| Grep agent (same model) | 0.284 | 0.378 | 0.322 | 32 s |

Head to head on those 74 questions (right function in the top 5): only the index agent 32, only the grep agent 4, both 24, neither 14.

**Hand-drafted questions by type (Acc@1 / Acc@5):**
| Method | Meaning (27) | Usage (8) | Structural (10) |
|---|---|---|---|
| Best single search | 0.815 / 0.926 (jina) | 0.625 / 0.875 (BM25) | 0.200 / 0.700 (BM25) |
| **Index agent** | **0.889 / 0.963** | 0.500 / **1.000** | **0.500 / 0.700** |
| Grep agent | 0.222 / 0.333 | 0.625 / 1.000 | 0.100 / 0.200 |

### What the numbers say
1. **The index nearly doubles a small agent's accuracy** versus grep: Acc@1 0.53 vs 0.28 on real issues, Acc@5 0.76 vs 0.38. The grep agent gave up (empty answer) on 87 of 127 mined questions; the index agent on 25.
2. **The agent is best at picking the single right answer** (Acc@1 0.53 and MRR 0.63, both the highest) but not at Acc@5: plain hybrid search (0.78) and jina (0.88) list more candidates. The agent shows fewer, better-checked results.
3. **The call graph works:** structural questions ("what does res.redirect call?") went from 0.2 to 0.5 at rank 1.
4. **Grep still wins exact-string questions** ("where is the 'etag fn' setting used?"): its submitted answer was right on all 8 usage questions.
5. **Speed is the price:** 40 s per question on a laptop vs 0.15 s for hybrid search.
6. **The small model prefers keywords:** 201 keyword searches vs 104 meaning searches and 47 graph lookups.

### Honest caveats
- The grep agent here runs on a 4B model. A strong model (like the ones behind Claude Code) greps far better, so this does **not** prove "indexes beat grep" in general. It shows that **for a small local model, an index is the difference between useful and not**. A strong-model comparison (Groq free tier) would test the general case.
- 1 of 127 grep-agent questions failed (a request hit the 3-minute limit) and counts as a miss.
- The hand-drafted questions still need Bhavyam's review.
- The first three runs had no reply cap; the last used a 1,024-token cap. The cap only affects runaway replies.

### Problems we hit (interview gold)
| Problem | Cause | Fix |
|---|---|---|
| 60 to 90 s per step, wrong answers | the default `qwen3:4b` writes about 1,000 tokens of hidden "thinking" per step and ignored `/no_think` through this API | switched to the non-thinking **instruct** edition: 30 s for a whole question |
| Agent said "not found" while its top result was correct | Ollama's default 4,096-token window silently cut off the conversation | auto-created model variant with an 8,192-token window |
| The model variant never actually changed | Ollama's create API streams its reply; the code didn't read it, so the request was cancelled | `stream: false`, and read the reply |
| Agent typed `submit_answer(["F282"])` or JSON as text instead of calling the tool | a common small-model failure | after a text reply, offer only the submit tool; read submissions written as text (16 index-agent and 47 grep-agent answers were rescued this way) |
| A 70-minute run crashed at question 120 and saved nothing | the model got stuck generating forever; three 10-minute timeouts | 1,024-token reply cap, 3-minute timeout with one retry, failed questions recorded as misses, and **results saved after every question so runs resume** |
| First full run failed instantly ("cartograph: program not found") | Windows briefly locked the command file | re-ran; runs now resume anyway |

### New tools
- **Ollama:** runs open AI models locally and serves an OpenAI-compatible API on `localhost:11434`.
- **Qwen3 4B Instruct:** a small open model from Alibaba with tool calling, quantized to 4 bits (Q4_K_M) so it fits in 2.5 GB.
- **openai Python library:** the standard client for OpenAI-style APIs, here pointed at Ollama.
- **Tool calling:** the model replies with a structured "call this function with these arguments" instead of text; our code runs it and sends back the result.

### Interview lines
- "On 74 real GitHub issues, the same 4B model found the right function first 53% of the time with my index tools vs 28% with grep only, running free on a laptop GPU."
- "The agent had the best Acc@1 and MRR but not the best Acc@5: it trades breadth for precision, which is what you want when a developer reads one answer."
- "Running a small local model taught me to engineer for failure: cap generations, time out, record failures as misses, and checkpoint after every question so a two-hour eval survives a crash."

---

## Phase 5: Precise call graph with Jelly (20 October 2026)

### What we built
- `engine/src/cartograph/jelly.py` and `cartograph jelly <repo> --entries lib examples`: runs **Jelly** (a research JavaScript analyzer), matches its functions to ours by file + line range, measures our call graph against it, and stores Jelly's links in a new `extra_edges` table.
- The agent's `graph_neighbors` tool now shows both sources; Jelly-only links are labelled "found by Jelly".
- Resolver fix found by the comparison: **follow `module.exports` re-exports**, so `var express = require('../../'); express()` resolves through `index.js` to `createApplication`.
- The parser's version is now part of each file's fingerprint, so changing the parser re-parses every file automatically (fixes the "schema change needs a manual reset" problem for parser changes).
- Full write-up: `eval/express/CALLGRAPH.md`.

### Precision and recall, in plain words
- **Precision:** of the links we claim, how many are real. Wrong links send the agent the wrong way.
- **Recall:** of the real links, how many we found. Missing links hide paths.

### Results (Express's own code)
| | Ours (tree-sitter) | Jelly |
|---|---|---|
| Links found | 291 | 79 |
| Shared | 62 | 62 |
| Raw agreement | 21% of ours are in Jelly | 79% of Jelly's are in ours (was 44%) |
| **Hand-checked estimate** | **~97% correct, finds ~94% of all real links found by either** | finds ~26% |

**Why raw agreement is misleading here:** Express builds `app`, `req` and `res` at run time (`Object.create`, `Object.setPrototypeOf`). Jelly loses track of which methods those objects carry, so it misses nearly all `res.send()` / `this.set()` style calls. A random sample of 25 of our links that Jelly lacked: **24 correct.** All 44 links Jelly had and we lacked: **real**, and ~29 of them were one fixable pattern (re-exports).

**By our confidence label:** `import` links agree with Jelly 97% of the time; `qualname` links (`res.send()` → `res.send = function...`) only 2%, but the hand check shows they are right: that's exactly the run-time wiring Jelly can't follow.

**Effect on the agent:** only 2 of 172 test questions touch a Jelly-only link, and re-running both gave identical scores. On Express, Jelly's value is **measurement**; its callback links should matter more in callback-heavy code.

### Problems we hit
| Problem | Cause | Fix |
|---|---|---|
| Jelly found only 77 links at first | Express's dependencies weren't installed, and they're what attaches methods | `npm install --ignore-scripts` (no install scripts run), analyze through dependencies, count only Express-to-Express links |
| 50 Jelly functions didn't match ours | Jelly treats each file's top-level code as one function starting at line 1, column 1 | map those to our `module` entries |
| "13% precision" looked alarming | the reference itself was blind to Express's run-time wiring | hand-checked a random sample instead of trusting one number |
| Parser change wouldn't re-parse anything | files' fingerprints hadn't changed | parser version is now part of the fingerprint |
| New table missing at agent start | tables were only created by `index` | every command creates missing tables on connect (idempotent) |

### Decisions to be able to explain
- **No approximate interpretation:** that Jelly mode *executes* the analyzed code. A code-search tool must never run the code it reads.
- **Two analyzers, not one:** tree-sitter is fast and catches method calls; Jelly tracks values and catches callbacks. Neither alone is enough.
- **Didn't re-run the 2-hour eval:** measured first that only 2 of 172 questions could be affected, re-ran those 2.

### New tools
- **Jelly** (Aarhus University, BSD-3): static analysis for JavaScript; builds call graphs by tracking where functions flow. Run via `npx` pinned to 0.13.0.
- **npx:** runs an npm package at an exact version without installing it globally.
- **`npm install --ignore-scripts`:** installs packages without running their install scripts (a supply-chain safety habit).

### Interview lines
- "I measured my tree-sitter call graph against Jelly, a research-grade analyzer. Raw agreement was 21%, but hand-checking showed Jelly was the blind one: Express wires its methods at run time. My links were about 97% correct on a sample."
- "The comparison paid for itself: it exposed a missing re-export rule, and fixing it raised recall against Jelly from 44% to 79%."
- "Static analysis has two failure modes, missing links and wrong links; I report both, with the method, instead of one accuracy number."

---

## Phase 6: The API server (20 October 2026)

### What we built
`cartograph serve <repo>` starts a web API on `http://127.0.0.1:8000` (`engine/src/cartograph/api.py`), the front door the map website will use.

| Endpoint | Returns | Measured on Express |
|---|---|---|
| `GET /api/health` | status, function count | 275 searchable functions |
| `GET /api/search?q=&mode=bm25\|dense\|hybrid&k=` | ranked functions | "delete a cookie" puts `res.clearCookie` first; 0.07 to 0.18 s |
| `GET /api/graph` | every function (nodes) and call (edges), each edge labelled with how we know it | 325 nodes, 308 edges (17 from Jelly) |
| `GET /api/functions/{id}` | code, location, callers, callees | `res.location`: called by `res.redirect`, calls `res.header` |
| `GET /api/impact/{id}?depth=` | what could break if this changes, with distance | `res.location` affects `res.redirect` (1 step), then everything that redirects (2 steps) |
| `GET /api/ask?q=&agent=index\|grep` | **live stream** of the agent's steps (Server-Sent Events) | steps arrived at 20:09:57, :58, 20:10:01; answer `res.clearCookie` |
| `GET /docs` | interactive documentation, generated by FastAPI | |

### How the pieces work
- **FastAPI + Pydantic:** each endpoint is a Python function; Pydantic classes (`Function`, `Edge`, `Hit`...) describe the exact JSON shape, and inputs are checked automatically (an empty search returns HTTP 422, an unknown function 404).
- **Uvicorn:** the server program that listens on the port.
- **Impact = BFS:** `graph.py` walks the call graph backwards ("who calls me, who calls them") level by level, with a depth limit and cycle protection. O(V + E) over the reachable part. Phase 9 checks it against git history.
- **Live stream (SSE):** the agent takes seconds per step, so it runs in a **background thread**. Each step goes into a **queue** (via the agent's new `on_event` hook), and the response generator sends each one to the browser as `data: {...}` the moment it arrives.
- **One database connection per request:** psycopg connections can't be shared safely between threads.
- **Load once, reuse:** the BM25 index and the embedding model are built once per server; the model warms up in the background at start, so the first search takes 0.18 s instead of 72 s.
- **Security:** the server binds to `127.0.0.1` only, because it serves the indexed source code.

### Problems we hit
| Problem | Fix |
|---|---|
| First meaning search took 72 s (loading PyTorch + the model) | warm the model up in a background thread at server start |
| A crash inside the agent thread would leave the browser waiting forever | the thread catches every failure and sends it as an `error` event, then always ends the stream |
| The terminal tab re-downloaded PyTorch on first run | PowerShell and the build shell used different download caches; one-time cost |

### Known limits
- If the browser disconnects mid-question, the agent thread still finishes that question.
- The graph is loaded fresh per request; fine for Express, may need caching for big repos.

### New tools
- **FastAPI**, **Uvicorn**, **Pydantic** (see above).
- **Server-Sent Events:** a standard way for a server to push a stream of messages over one HTTP response (`text/event-stream`); browsers read it with `EventSource`.
- **httpx / TestClient:** tests call the API in-process; the stream test swaps in a fake agent, so CI needs no model.

### Interview lines
- "The agent is slow and the UI must show it working, so I stream each step with Server-Sent Events: the agent runs in a worker thread and hands steps to the response through a queue."
- "I load the embedding model once per server and warm it up in the background, which took the first search from 72 seconds to 0.2."
- "Impact analysis is a BFS on the reversed call graph with a depth cap; it's O(V+E) over what's reachable and safe on cycles."

---

## Phase 7: The map website (20 October 2026)

### What we built
The codebase drawn as a **transit map** (`web/src/`), the direction you chose from the design round:
- **Stations** are functions (white centre, coloured ring; a file's top-level code is a solid stop; bigger stops have more calls). **Lines** are neighbourhoods of code that call each other, each in its own enamel colour and named after its busiest station (`res.send`, `createApplication`...). **Track** is calls; track between neighbourhoods is faded.
- **Semantic zoom:** zoomed out, the 12 biggest files are labelled as landmarks (5 on a phone); zoomed in, function names appear.
- **Search** (top bar, `/` to focus): type a name or a question, arrow through results, Enter flies the map to that station.
- **Station sign panel:** the function's name, file and lines, its code with syntax colours, and **Called by** / **Calls** lists you can click to "change trains".
- **Lines key:** what the colours mean; clicking a line highlights it.
- **Links:** selecting a function puts `#f=<id>` in the address, so a link opens straight to it.
- **Phones:** search on its own row, the key collapsed, the panel as a bottom sheet with the map above it.
- Light and dark themes follow the system.
- Design records: `PRODUCT.md` (who it's for, rules), `DESIGN.md` (colours, type, components, named rules), `.impeccable/surfaces/` (the direction contract).

### How it works
1. **Layout (ForceAtlas2):** a physics simulation in the browser. Calls pull functions together, everything pushes apart, and an extra light pull keeps each file's functions together. A fixed random seed means the same codebase always draws the same map.
2. **Neighbourhoods (Louvain):** community detection finds groups of functions that call each other more than they call the rest. Largest groups get the eight line colours; small ones share grey.
3. **Rendering (Sigma.js 3, WebGL):** draws on the graphics card. A custom "station" node program draws the ring + centre; a custom label renderer adds a halo in the map colour so labels stay readable over track.
4. **Reducers:** on every frame Sigma asks "how should this node/edge look now?". The answer depends on zoom, hover, the selected station and the focused line. That's how fading, highlighting and semantic zoom work without rebuilding the graph.

### Design process (your rules: impeccable, taste, Emil Kowalski)
- Interview (2 questions): designed for developers and demo viewers equally; WCAG 2.1 AA.
- A seeded "roll" assigned a direction from my own list; you chose **Transit Diagram** from the shortlist.
- Mechanical design detector: 0 findings. Finish review (run inline: no reviewer agent exists in this setup) found 2 material issues, both fixed and re-checked: line names that contradicted the map, and labels colliding around a selection. Verdict: ship (for those fixes).

### Checked in the browser
Desktop (1440x900) and phone (375x812), dark and light: map, search dropdown, Enter to fly, panel open, following a connection (`res.clearCookie` → `res.cookie`, address updates), Escape closes and clears the address, line focus toggles (`aria-pressed`). Build and lint clean.

### Problems we hit
| Problem | Fix |
|---|---|
| Sigma 4 just shipped a new styling API I couldn't verify | pinned Sigma 3.0.3, mature and documented |
| Blank page: Sigma calls the colouring function while it is still being constructed | keep zoom level in shared state instead of asking the renderer |
| 50 file labels piled into an unreadable heap | label only the biggest files (12 desktop, 5 phone) |
| The header said 308 calls in the API but 302 on screen (recursion was skipped when drawing) | count every link from the API, recursion included |
| File labels at the average position floated between neighbourhoods | label each file at its busiest real station |
| Headless Edge screenshots of "phones" were wrong: Edge never goes below 496 px wide, and its screenshot doesn't wait for data | wrote `scripts/capture.py`, which drives Edge through its DevTools protocol: exact device size, light/dark, waits for the map |
| A fix I made for the "cropped" phone map shrank it: the crop was the capture bug, not the page | removed it after checking in a real browser at 375 px |
| Opening the panel by clicking would stretch the map (Sigma only watches window resizes) | ResizeObserver on the map container |
| Five lines all named "lib/response.js" | lines named after their busiest *function*, file shown beneath |
| Focus ring colour was the same blue as a line | focus rings in ink: line colours never mean "interactive" |

### New tools
- **Sigma.js** (WebGL graph renderer) and **@sigma/node-border** (ring-shaped nodes).
- **graphology** (graph data structure) with **ForceAtlas2** (layout) and **Louvain** (community detection).
- **prism-react-renderer** (syntax highlighting, coloured by our CSS), **lucide-react** (icons), **Archivo** and **JetBrains Mono** (self-hosted fonts via Fontsource).
- **Chrome DevTools Protocol:** the browser's remote-control interface, used by `scripts/capture.py`.

### Interview lines
- "I render the call graph with Sigma.js on WebGL, lay it out with ForceAtlas2 and colour neighbourhoods with Louvain community detection; it reads like a metro map where calls are track and functions are stations."
- "Semantic zoom keeps it readable: file landmarks when zoomed out, function names when zoomed in, and a selection fades everything except its direct connections."
- "I verified the UI with real screenshots at desktop and phone sizes; when headless screenshots lied about phone layouts, I drove the browser through the DevTools protocol instead."

### Update: the combined design (transit map + yellow route)
Your idea after seeing the Terminal Wayfinding mockup: keep the transit map for exploring, and borrow wayfinding's best trick for looking things up.
- **Exploring:** the full-colour transit map, unchanged.
- **Picking a function** (search result or click): the map turns grey and only the route lights up in yellow: the function, its direct callers and callees, and the track between them. Close the panel and the colours come back.
- **Yellow is reserved:** it means only "where you are going". The amber line colour was swapped for raspberry so nothing else on the map is yellow. Phase 8 will draw the AI agent's search as a yellow route too.
- **Accessibility detail:** thin bright-yellow lines on near-white paper fail WCAG's 3:1 contrast for graphics, so light mode draws route stations as yellow signs with a black ring and the track in deep gold (3.4:1). Dark mode uses signal yellow (#ffd200).
- Recorded as "The Yellow Route Rule" in DESIGN.md and in the design contract.

*Interview line:* "Two modes: an overview that shows the codebase's structure in colour, and a focus mode where the map goes grey and only your route is yellow. I reserved yellow for that one meaning, and checked its contrast in both themes."
