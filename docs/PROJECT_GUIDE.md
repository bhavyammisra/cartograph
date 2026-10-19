# Cartograph: the complete project guide

This guide explains the whole project in plain words, from the first folder to a published, industry-level tool. Read Part 1 and Part 2 now. Read each phase in Part 3 just before we build it. Part 5 is for interview prep.

Stack decision used here: **Python for the engine, TypeScript + React for the map.** (Reasons are in the earlier chat: Python shows AI skills on your resume, TypeScript keeps your web skills visible.)

---

## Part 1: What we are building, in plain words

### The problem

Big codebases have thousands of files. A new developer can't remember where everything is. An AI can't read it all either, because the code is far bigger than what fits in its "memory" (its context window). So the slow part of fixing anything is **finding where it happens**.

### What Cartograph does

You type a question in normal English, like *"Where do we handle failed payments?"* Cartograph answers with the exact files and line numbers, and shows you a map of the code where you can watch the AI search.

### The four big pieces

Think of it like a library.

1. **The indexer (the librarian who catalogs every book).** Runs once per repo. It reads every JavaScript file, finds every function, notes which function calls which, and stores all of it in a database. It also builds three "catalogs" (indexes) so we can search fast later.
2. **The agent (the research assistant).** When you ask a question, an AI (LLM) decides which catalog to search, reads the results, follows connections between functions, and keeps going until it has the answer.
3. **The map (the floor plan of the library).** A web page that draws every function as a dot and every call as a line. You can zoom, click a dot to see its code, and watch the agent's search light up the map.
4. **The evaluation (the exam).** A set of questions with known correct answers. We run Cartograph on them and measure how often it's right and how fast. This is what turns "I built a cool demo" into "I built something that works, and here's the proof."

### The three kinds of questions

| Kind | Example | Which catalog answers it |
|---|---|---|
| Meaning | "Where do we handle failed payments?" (the code might say `onChargeDeclined`) | Embedding search (understands meaning) |
| Usage | "Where is the Bluetooth settings link used?" | Keyword search (exact names) |
| Structural | "Which files call `validateUser` before `saveOrder`?" | Call graph (who calls whom, in what order) |

### What makes it different from the many similar tools

From the research report (`reports/Cartograph novelty and landscape.md`):
- It **proves its accuracy** with numbers, compared against a plain "grep" AI agent. Most tools only claim things.
- It answers **"X before Y" questions** for JavaScript, even across functions.
- It **shows the AI's search path on the map** and explains why each result was picked.
- Its **impact analysis is checked against real history**: when a function changed in the past, what else actually changed with it?

---

## Part 2: Every technology we use, explained

For each one: **what it is**, **what people usually use it for**, **what we use it for**, and **one line to say in an interview**.

### 2.1 Languages

**Python**
- *What it is:* A general-purpose programming language that's easy to read.
- *Usually used for:* AI and machine learning, data analysis, backend servers, scripts and automation.
- *We use it for:* The whole engine: reading code, building the indexes, running searches, the AI agent, the API server, and the evaluation.
- *Interview line:* "The engine is Python because the retrieval and ML tooling (embedding models, evaluation, fine-tuning) lives there."

**TypeScript (TS)**
- *What it is:* JavaScript with types added. Types mean you declare "this variable is a number" and mistakes get caught before running.
- *Usually used for:* Websites and web apps, Node.js backends, developer tools.
- *We use it for:* The map website (frontend).
- *Interview line:* "The frontend is TypeScript so graph data shapes coming from the API are type-checked."

**JavaScript (JS)**
- *What it is:* The language of the web. Browsers run it, and Node.js runs it on servers.
- *Usually used for:* Websites, servers, tools.
- *We use it for:* It's the language **of the code we analyze**. We don't write Cartograph in JS; we read other people's JS projects.

**SQL**
- *What it is:* The language for asking databases questions ("give me every function in file X").
- *Usually used for:* Anything stored in a relational database.
- *We use it for:* Storing functions, calls and vectors in Postgres, and querying them. Graph walks (BFS) can be written as SQL "recursive queries."

**HTML and CSS**
- *What they are:* HTML is a page's structure (headings, buttons); CSS is its looks (colors, spacing, layout).
- *We use them for:* The map website's layout and styling, through React.

**YAML** (files ending in `.yml` / `.yaml`)
- *What it is:* A plain-text format for settings, using indentation instead of brackets.
- *Usually used for:* Configuration files.
- *We use it for:* GitHub Actions workflows (the automatic test runs) and `docker-compose.yml` (how to start the database).

**JSON** (`.json`)
- *What it is:* A text format for data, like `{"name": "saveOrder", "line": 42}`.
- *Usually used for:* Sending data between programs, and config.
- *We use it for:* The API's answers to the website, Jelly's call graph output, saved agent traces, and `package.json` (the frontend's list of dependencies).

**TOML** (`pyproject.toml`)
- *What it is:* Another settings format, simpler than YAML.
- *We use it for:* The Python project's settings: its name, version, and the libraries it needs. This file is also what lets us publish to PyPI.

**Markdown** (`.md`)
- *What it is:* Plain text with light formatting (`#` for headings, `**bold**`). GitHub renders it nicely.
- *We use it for:* README, this guide, docs.

**Dockerfile and shell commands (Bash / PowerShell)**
- *Dockerfile:* A recipe for building a container (see Docker below).
- *Shell:* The terminal language for running commands like `git commit` or `uv run pytest`.

### 2.2 Code reading and analysis

**tree-sitter**
- *What it is:* A fast parser. A parser reads source code and turns it into a tree that shows its structure (this is a function, this is a call inside it, this is an argument).
- *Usually used for:* Syntax highlighting in editors (VS Code, Neovim, GitHub), code navigation, code tools.
- *We use it for:* Reading every JS/TS file and pulling out functions, their line numbers, their calls and imports. Fast, works on broken code too.
- *Its limit:* It only sees text structure, not meaning. If code does `const fn = pick(); fn()`, tree-sitter doesn't know which function `fn` is.
- *Interview line:* "tree-sitter gives me a fast syntax tree, but it can't resolve dynamic calls, so I added a second, precise tier."

**AST (Abstract Syntax Tree)**
- *What it is:* The tree tree-sitter produces. Every piece of code becomes a node: function, call, `if` statement.
- *We use it for:* Finding functions and calls, and knowing the **order** of calls inside a function (needed for "X before Y").

**Jelly**
- *What it is:* A research-grade static analyzer for JavaScript/TypeScript from Aarhus University. "Static" means it analyzes code without running it.
- *Usually used for:* Building accurate call graphs, security analysis of npm packages.
- *We use it for:* A **precise call graph** to compare against our fast tree-sitter one. It even reports precision and recall between two call graphs.
- *Interview line:* "I measured how accurate my tree-sitter call graph was against Jelly, so I know exactly what I'm missing."

**Call graph**
- *What it is:* A graph where dots (nodes) are functions and arrows (edges) mean "A calls B."
- *We use it for:* Following connections during search, impact analysis, "X before Y" queries, and the map itself.

### 2.3 Storage

**PostgreSQL (Postgres)**
- *What it is:* A free, very widely used relational database (data in tables with rows and columns).
- *Usually used for:* The main database of most web apps.
- *We use it for:* Storing everything: files, functions, call edges, embeddings, eval results.

**pgvector**
- *What it is:* A Postgres add-on that can store vectors (lists of numbers) and find the "closest" ones quickly.
- *Usually used for:* Semantic search and RAG apps.
- *We use it for:* Storing one vector per function and finding functions whose meaning matches the question.
- *Detail to know:* It uses an **HNSW index**, a clever structure that finds near neighbors fast without comparing against every vector. Approximate, but very fast.

**Postgres full-text search / BM25**
- *What it is:* Keyword search. BM25 is the standard scoring formula: words that are rare across the codebase but frequent in a function score high.
- *Usually used for:* Search engines (Elasticsearch uses BM25).
- *We use it for:* The keyword catalog. We split code names like `getUserById` into `get user by id` so searching "user" finds it. We'll use the Python library `bm25s` for true BM25 scoring.

**Docker and Docker Compose**
- *What it is:* Docker packages a program with everything it needs into a "container" that runs the same on any machine. Compose starts several containers with one command.
- *Usually used for:* Running databases locally, deploying servers.
- *We use it for:* `docker compose up` starts Postgres with pgvector already installed. No manual database setup.

**Supabase**
- *What it is:* Hosted Postgres with extras (you already used it for Khairiyat and Road-Report).
- *We use it for:* The database behind the public demo website (pgvector is built in).

### 2.4 Search and AI

**Embeddings**
- *What it is:* A model turns text or code into a list of numbers (a vector, e.g. 768 numbers). Things with similar meaning get similar vectors.
- *Usually used for:* Semantic search, recommendations, RAG.
- *We use it for:* Turning each function into a vector, and each question into a vector, then finding the closest functions. That's how "failed payments" finds `onChargeDeclined`.

**CodeRankEmbed (main embedding model)**
- *What it is:* A small (137 million parameters) open model made for code search, by Nomic. Runs fine on a laptop CPU.
- *We use it for:* Making the vectors. We'll compare it with **jina-code-embeddings-0.5b** (bigger, maybe more accurate) and report which is better.

**sentence-transformers / ONNX Runtime**
- *What they are:* Python libraries that load and run embedding models. ONNX Runtime is a faster engine for running models on CPU.
- *We use them for:* Running CodeRankEmbed during indexing and at query time.

**Cosine similarity**
- *What it is:* A way to measure how close two vectors are (1 = same direction, 0 = unrelated).
- *We use it for:* Ranking functions by meaning-match.

**RRF (Reciprocal Rank Fusion)**
- *What it is:* A simple way to merge several ranked lists. Each result gets points of `1 / (60 + its rank)` from each list, and we add the points up.
- *Why:* Keyword scores and vector scores are on different scales, so you can't just add them. Ranks are comparable.
- *We use it for:* Combining keyword search and embedding search into one list.
- *Interview line:* "RRF only uses ranks, so it needs no tuning and is robust when one retriever's scores are weird."

**LLM (Large Language Model) and tool calling**
- *What it is:* The AI (like Claude). "Tool calling" means we give the model a list of functions it may call (search, read file, follow graph), and it decides which to call and with what arguments.
- *Usually used for:* Chatbots, agents, coding assistants.
- *We use it for:* The agent's brain: planning which searches to run and deciding when it has the answer.

**Agent loop**
- *What it is:* A loop: the AI thinks, calls a tool, reads the result, thinks again, until it answers or hits a limit.
- *Our tools:* `search_keyword`, `search_meaning`, `graph_neighbors`, `read_code`, `find_call_order`.
- *Interview line:* "The loop has a step and token budget so it can't run forever, and it's allowed to answer 'not found.'"

**MCP (Model Context Protocol)**
- *What it is:* A standard way for AI apps (Claude Code, Cursor) to use outside tools. Like a USB port for AI tools.
- *We use it for:* Letting Claude Code use Cartograph's search tools directly. Then we measure if it saves tokens and improves answers.

### 2.5 Graph algorithms

**BFS (Breadth-First Search)**
- *What it is:* Explore a graph level by level: first all direct neighbors, then their neighbors, and so on. (You know this from DSA.)
- *We use it for:* Impact analysis. Reverse the arrows ("who calls me?") and BFS from a function to find everything that could break if it changes.

**Community detection (Leiden / Louvain)**
- *What it is:* Algorithms that find groups of nodes connected more to each other than to the rest.
- *We use it for:* Coloring the map into "neighborhoods" (e.g. the payments area, the auth area). Library: `leidenalg` with `igraph` in Python.

**NetworkX**
- *What it is:* A Python library for graphs (BFS, paths, etc.).
- *We use it for:* Graph algorithms during indexing and testing, where SQL would be awkward.

### 2.6 Backend server

**FastAPI**
- *What it is:* A modern Python framework for building web APIs (URLs that return data).
- *Usually used for:* Backends for web apps and ML models.
- *We use it for:* The API the website talks to: `/search`, `/graph`, `/function/{id}`, `/impact/{id}`.

**Pydantic**
- *What it is:* A Python library that checks data shapes ("this must have a `file` string and a `line` number").
- *We use it for:* Validating API inputs and outputs, and settings.

**Server-Sent Events (SSE)**
- *What it is:* A simple way for a server to keep sending updates to a web page over one connection.
- *We use it for:* Streaming the agent's steps live, so the map animates while the agent works.

### 2.7 Frontend (the map)

**React**
- *What it is:* A library for building web interfaces out of components (you know it).
- *We use it for:* The whole website: search box, map, code panel, results list.

**Vite**
- *What it is:* A fast tool that runs the website while you develop and bundles it for publishing.
- *We use it for:* `npm run dev` during development, `npm run build` for the demo site.

**Sigma.js + graphology**
- *What they are:* graphology stores a graph in the browser; Sigma.js draws it using WebGL (the graphics card), so thousands of dots stay smooth.
- *We use them for:* Drawing the code map, zooming, highlighting the agent's path.
- *Interview line:* "Canvas or SVG choke at thousands of nodes, so I render with WebGL through Sigma.js and precompute the layout on the server."

**Semantic zoom**
- *What it is:* Showing different detail at different zoom levels: folders when zoomed out, functions when zoomed in.
- *We use it for:* Avoiding a "hairball" (a mess of overlapping lines).

### 2.8 Quality tools

**Git and GitHub**
- *Git:* Saves versions of your code (commits). *GitHub:* Hosts it online.
- *We use them for:* Version control, issues, releases. We also **read the git history of the repo we analyze** to auto-build test questions and validate impact analysis.

**uv**
- *What it is:* A very fast Python package and project manager (replaces pip + virtualenv).
- *We use it for:* Installing libraries, running scripts (`uv run ...`), and letting users run Cartograph with one command (`uvx cartograph`).

**npm**
- *What it is:* Node.js's package manager.
- *We use it for:* Frontend libraries (React, Sigma.js) and installing Jelly.

**pytest**
- *What it is:* The standard Python testing tool.
- *We use it for:* Tests like "this small JS file should produce these 3 functions and these 2 calls."

**Ruff and mypy**
- *Ruff:* Checks Python code style and common bugs, very fast. *mypy:* Checks Python type hints.
- *We use them for:* Keeping code clean, enforced in CI.

**Playwright**
- *What it is:* A tool that opens a real browser and clicks around automatically.
- *We use it for:* Checking the map page works and looks right at desktop and phone sizes.

**GitHub Actions (CI)**
- *What it is:* CI = Continuous Integration. Every time you push code, GitHub runs your tests automatically.
- *We use it for:* Run lint, tests, and a small eval on every push. A green check on the repo is a strong signal to reviewers.

### 2.9 Publishing

**PyPI**
- *What it is:* The public store for Python packages (where `pip install` downloads from).
- *We use it for:* Publishing Cartograph so anyone can run `uvx cartograph` or `pip install cartograph`. (We must check the name is free; we may need `cartograph-code` or similar.)

**Vercel**
- *What it is:* Hosting for websites (you've used it).
- *We use it for:* The public demo of the map.

**Hugging Face**
- *What it is:* A site that hosts AI models and datasets.
- *We use it for:* Downloading the embedding model, and optionally publishing our eval dataset so others can use it.

### 2.10 Measurement words (for the eval)

| Word | Plain meaning |
|---|---|
| Precision@5 / Acc@5 | Of questions asked, how often the right answer appears in the top 5 results. |
| Recall | Of all the correct locations, what share did we find. |
| MRR | How high the first right answer ranks, on average (1st place = 1, 2nd = 0.5, 3rd = 0.33). |
| Latency p50 / p95 | Typical answer time / time for the slowest 5% of questions. |
| Indexing cost | Time and disk space to index a repo. |
| Cost per query | Money spent on the AI per question. |
| Baseline | The simple method we compare against (grep agent, plain keyword search). |
| Ablation | Turning parts off one at a time to see what each part contributes. |
| Ground truth / gold | The known correct answer for a test question. |
| Co-change | Functions that were edited in the same commit in the past. |

---

## Part 3: Building it, phase by phase

Each phase: **what we do, why, what you'll learn, how we know it's done, what an interviewer might ask.** Time estimates assume part-time work alongside college; total about 16 weeks.

### Phase 0: Setup (week 1)

**Do:**
- Create the GitHub repo `cartograph` and connect this folder.
- Install: Python 3.12+, uv, Node.js 20+, Docker Desktop, Git.
- Create the folder layout:

```
cartograph/
  engine/             Python: indexer, search, agent, API, MCP
    cartograph/       the Python package
    tests/            pytest tests
    pyproject.toml    Python settings and dependencies
  web/                TypeScript + React map
    src/
    package.json
  eval/               questions, gold answers, eval scripts, results
  docs/               this guide, architecture notes
  docker-compose.yml  starts Postgres + pgvector
  .github/workflows/  CI settings
  README.md
  LICENSE
```

- Pick a license: **MIT** (simple, lets anyone use it, standard for portfolio tools).
- Clone the test repos: **Express** (small, for building) and later **Prettier** (headline eval).

**Learn:** Monorepo layout (one repo, two languages), why a license matters (without one, nobody may legally reuse your code).

**Done when:** `docker compose up` starts Postgres, `uv run pytest` runs (even with zero tests), `npm run dev` shows an empty page.

### Phase 1: The indexer (weeks 2 to 3)

**Do:**
1. Walk every `.js`/`.ts` file (skip `node_modules`, build output, tests can be tagged).
2. Parse with tree-sitter. Pull out each function: name, file, start line, end line, code text.
3. Pull out calls inside each function, **in order**, and imports at the top of files.
4. Resolve calls to functions where possible (same file, imported names, `this.method`). Mark each edge with how sure we are.
5. Save to Postgres tables: `files`, `functions`, `calls`, `imports`.
6. Make it **incremental**: store each file's hash; on re-index, only re-parse files whose hash changed.

**Learn:** Parsing, ASTs, name resolution, why JS is hard (dynamic calls, callbacks, `require` vs `import`).

**Done when:** Indexing Express gives a function count and call count you've spot-checked by hand on 10 functions, and tests cover small sample files.

**Interview:** "How did you build the call graph? What can't tree-sitter resolve?"

### Phase 2: Eval harness and baselines (weeks 3 to 4)

We build the exam **before** the clever parts, so every later step is measured.

**Do:**
1. **Auto-mined questions:** scan the repo's git history for bug-fix commits linked to issues. Question = issue title + text. Gold answer = the functions the fix changed (we compare old and new code to find them). Hand-check 50 to measure how noisy this is.
2. **Hand-written questions:** 40 to 60 questions across meaning / usage / structural, with answers you label yourself.
3. **Metrics script:** Acc@1/5/10, MRR, recall, latency p50/p95, cost.
4. **Baselines:** (a) plain keyword search, (b) a "grep agent": the same LLM with only grep and file reading.

**Learn:** How retrieval is measured, why a fair baseline matters, data noise.

**Done when:** One command prints a results table for both baselines.

**Interview:** "How did you build your test set? How did you know the labels were right?"

### Phase 3: Embeddings and hybrid search (weeks 5 to 6)

**Do:**
1. Embed every function with CodeRankEmbed, store in pgvector with an HNSW index.
2. Build the BM25 keyword index (with name splitting: `getUserById` becomes `get user by id`).
3. Merge both with RRF.
4. Run the eval: keyword vs embeddings vs hybrid. Then try jina-code-embeddings-0.5b and compare.

**Learn:** Vectors, nearest-neighbor search, why hybrid beats either alone.

**Done when:** The first real ablation table exists.

**Interview:** "Why not just use embeddings? Why RRF instead of adding scores?"

### Phase 4: The agent (weeks 7 to 8)

**Do:**
1. Define tools: `search_keyword`, `search_meaning`, `graph_neighbors`, `read_code`.
2. Write the loop: plan, call tools, read results, follow 1 to 2 call-graph hops, answer with file + lines, or say "not found."
3. Set limits: max steps, max tokens.
4. **Log every step as an event** (tool, input, results, ranks). This log powers the map animation later.
5. Run the eval with two LLMs (one cheap, one strong). Cache answers so re-runs are free.

**Learn:** Tool calling, prompt design, agent failure modes (loops, giving up, confident wrong answers).

**Done when:** The agent beats the grep agent on accuracy or cost, or we know honestly why not.

**Interview:** "What happens when the agent gets stuck? How do you stop it hallucinating?"

### Phase 5: Precise call graph with Jelly (week 9)

**Do:** Run Jelly on the repo, load its call graph, compare with ours using its precision/recall tool. Store both; edges get a confidence label. Switch the main eval to Prettier.

**Done when:** You can say "my fast call graph finds X% of Jelly's edges, and Y% of mine are correct."

**Interview:** "Why is static analysis of JavaScript hard?"

### Phase 6: API server (week 9)

**Do:** FastAPI endpoints for search, graph data, function code, impact, and an SSE stream of agent events. Pydantic models for every response.

**Done when:** You can call every endpoint from the browser and get clean JSON.

### Phase 7: The map (weeks 10 to 11)

**Do:**
1. Compute layout and communities at index time (server side), send positions to the browser.
2. Sigma.js renders it. Zoomed out: folders/modules. Zoomed in: functions.
3. Click a node: code panel with syntax highlighting, callers and callees.
4. Search box connects to the agent.
5. Check with Playwright at desktop and phone width. Follow your site rules: no purple gradients, no pill buttons, no emoji icons, no fake numbers, no filler copy.

**Learn:** WebGL rendering, layout algorithms, keeping big graphs readable.

**Interview:** "How do you render thousands of nodes smoothly?"

### Phase 8: Trace replay and "why this result" (week 12)

**Do:** Play the agent's event log on the map: visited nodes light up, followed edges draw as a trail, discarded results fade, answers glow. Clicking an answer shows: "keyword rank 3, meaning rank 1, reached via `checkout` to `charge`." Flag search loops (agent revisiting the same place).

**Interview:** "Why does seeing the path matter?" (Answer: trust and debugging. You can see *why* the AI was wrong.)

### Phase 9: Impact analysis, validated (week 13)

**Do:**
1. Reverse BFS from a function = predicted blast radius.
2. Validate with history: for past commits that changed function f, did the other functions changed in that commit appear in f's predicted radius? Measure precision and recall for: call graph only, co-change history only, both combined.
3. On the map: a red ripple spreading outward, ranked by likelihood.

**Interview:** "How do you know your impact analysis is right?" This answer impresses because almost no tool checks.

### Phase 10: "X before Y" queries (week 14)

**Do:** Three levels: (1) same function, statement order from the AST; (2) across calls, X's path reaches Y in order; (3) from every entry point (route handlers, exports), is X always called before Y? Show counterexample paths. Write ~30 such questions with gold answers and publish them as a small benchmark.

**Interview:** "How did you make the graph search respect order?" (A path search where each step must happen after the previous one in its function. Cap path depth so it doesn't explode.)

### Phase 11: MCP server (week 15)

**Do:** Expose the same tools over MCP. Connect Claude Code. Run the eval with and without Cartograph; report tokens and accuracy.

### Phase 12: Making it industry level (weeks 15 to 16)

This is what separates a student project from a real tool.

| Area | What we do |
|---|---|
| Tests | Unit tests for parser, search, graph; one end-to-end test that indexes a tiny sample repo. |
| CI | GitHub Actions: lint (Ruff), type check (mypy, tsc), tests, small eval, frontend build, on every push. |
| Packaging | `pyproject.toml` with a `cartograph` command; `uvx cartograph index .`, `cartograph serve`, `cartograph eval`, `cartograph mcp`. |
| Docker | `docker compose up` brings up database + API + web together. |
| Config | Settings via environment variables and a `.env.example` file. API keys never committed. |
| Security | The tool only reads code; never runs it. Keys read from env only. Dependency vulnerability scan in CI (Dependabot). |
| Errors and logs | Clear error messages ("Postgres isn't running, try `docker compose up`"), structured logs. |
| Docs | README (results table + GIF first, then setup), architecture doc with a diagram, eval methodology doc, CONTRIBUTING, CHANGELOG. |
| Versioning | Semantic versions (`0.1.0`, `0.2.0`), git tags, GitHub Releases with notes. |
| Performance | Measure index time and memory on Prettier; batch embeddings; cache LLM calls. |
| Reproducibility | Pinned dependency versions (uv lock file), fixed random seeds, eval results saved as files in the repo. |

---

## Part 4: Publishing and launch

### Step 1: Publish the package
- Check the name on PyPI. Build with `uv build`, publish with `uv publish` (first to TestPyPI to practice).
- Automate: a GitHub Action publishes when you push a version tag.

### Step 2: The public demo site
- Vercel site with Prettier pre-indexed and 5 to 10 **recorded** agent traces that replay. No live AI calls, so it costs nothing and never breaks.
- Your launch checklist (from your standing rules), all required before going live:
  - domain connected (a free `.vercel.app` address is allowed if you have no domain yet)
  - favicon
  - no "Made with AI" or builder tags
  - privacy policy page
  - terms and conditions page
- Check it in the browser at desktop and phone width before calling it done.

### Step 3: Publish the data
- Eval questions, gold answers and results on GitHub (and optionally Hugging Face Datasets), with a clear note on how they were made.

### Step 4: Show it to people
- **Demo video** (2 to 3 minutes): question, map animation, answer, results table.
- **Write-up** (blog post or dev.to): "Do coding agents need an index? I measured it on JavaScript." The debate angle gets attention.
- Share: LinkedIn, r/javascript or r/LocalLLaMA, Hacker News "Show HN." Real users opening issues is a strong signal.
- **Optional paper:** if the results are interesting, a short workshop paper or arXiv preprint. Big resume boost for ML roles, but only after the project is finished.

### Step 5: Resume and portfolio
- Replace Orphan Adoption with Cartograph.
- Bullet uses only measured numbers (template in the research report).
- Link: GitHub repo, live demo, video.

---

## Part 5: Interview preparation

### The 30-second pitch
"New developers get lost in big codebases, and AI can't read a whole repo at once. I built Cartograph: you ask a question in English, and an AI agent searches keyword, meaning and call-graph indexes to return exact file and line locations. You can watch its search on an interactive map of the code. I measured it against a grep-based agent on [N] questions mined from git history, and it reached [X] accuracy at top 5."

### Problems you will hit (and should be ready to explain)

| Problem | What it means | How we handle it |
|---|---|---|
| Dynamic calls in JS | Code like `handlers[name]()` hides which function runs | Two tiers: tree-sitter fast, Jelly precise; edges carry confidence |
| Stale index | Code changes after indexing | File hashes, re-index only changed files |
| Noisy auto-labels | Fix commits often touch unrelated files | Hand-check a sample, report noise rate |
| Agent loops or hallucinates | Repeats searches, invents answers | Step limits, must cite real file+line, "not found" allowed and scored |
| Hairball graph | Too many lines to read | Semantic zoom, communities, show only relevant area |
| Path explosion in "X before Y" | Too many paths in big graphs | Depth cap, stop at first counterexample |
| LLM cost during eval | Many questions x many configs | Cache responses, cheap model for development |
| Fair comparison | Easy to make baselines weak | Same LLM, same budget, only tools change |

### Questions to practise
1. Why hybrid search instead of only embeddings?
2. How does RRF work? Why `k = 60`?
3. What is HNSW and what does "approximate" give up?
4. How did you build and validate the call graph?
5. Time complexity of your impact BFS? (O(V + E) over the reachable part.)
6. How would you scale this to 1 million files?
7. What were your baselines and why are they fair?
8. What surprised you in the results?
9. What would you do differently?
10. How is this different from Cursor or Sourcegraph?

We'll write your own answers to these as we finish each phase, using your real results.

---

## Part 6: Questions answered in plain words

These came up while planning. Each ends with a line you can say in an interview.

### What does "X before Y" mean?
It asks about order: does the code always do X first and Y after?

```js
function checkout(cart, user) {
  validateUser(user);   // X: check the user
  saveOrder(cart);      // Y: save the order
}
function quickBuy(cart, user) {
  saveOrder(cart);      // Y first: the order is saved before anyone checks the user
  validateUser(user);
}
```
`quickBuy` is a bug and maybe a security hole. It gets harder when calls hide inside other functions (`checkout` calls `prepare()`, which calls `validateUser`), because text search can't see order through function calls. Cartograph follows the call graph and tracks what happens first. Real versions: file opened before read, payment charged before the confirmation email, input cleaned before going into a database query.

*Interview:* "Structural ordering queries are a graph path search where each step must happen after the previous one in its function, with a depth cap so it doesn't explode."

### Why only JavaScript (and TypeScript)?
1. The original Samsung problem asked for one language: JavaScript.
2. One language measured properly beats ten languages with no accuracy numbers (which is what most tools do).
3. JavaScript is popular and dynamic (`handlers[name]()` hides which function runs), so it's the interesting hard case.
TypeScript comes nearly free because tree-sitter and Jelly support it.

*Interview:* "I went deep on one language so I could measure call-graph accuracy honestly instead of claiming support for many."

### Is the tech stack too big?
Most of the list is basics every project has (Git, JSON, YAML, Markdown, npm, uv). The real choices are about 10, and each does one job: tree-sitter reads code, Postgres stores it, pgvector searches by meaning, the LLM decides what to search, FastAPI connects engine and website, Sigma.js draws the map, Docker makes setup repeatable. A big stack is bad only when you can't say why each tool is there. On the resume, list 6 to 8.

### Why did Khairiyat use Supabase, but Cartograph runs locally?
- Khairiyat: many users on many phones share the same data (schedules, NFC taps, caregivers checking progress). That data must live online where every phone can reach it, so Supabase hosted it (plus login and ready-made APIs).
- Cartograph: one developer indexes their own code on their own computer. Nobody else needs that data, so Postgres runs locally in Docker.
- Rule: shared data for many users over the internet means a hosted database. Personal data on one machine means a local database.
- Bonus: companies don't want their source code uploaded anywhere, so local is also a privacy feature.
- The public demo site replays pre-recorded searches, so it needs no online database either. Supabase can be added later for a live demo; it's the same Postgres.

*Interview:* "Everything runs locally, so source code never leaves the developer's machine."

### What does Docker do?
Normally, running Postgres with pgvector means installing Postgres, finding and installing the add-on, setting users, passwords and ports, with different steps on Windows, Mac and Linux. Docker packages the program with everything it needs into a sealed box (a **container**) that runs the same everywhere. Like handing someone a ready-made meal in a lunchbox instead of a recipe.
- **Image:** the packaged recipe (e.g. `pgvector/pgvector:pg17`).
- **Container:** a running copy of an image.
- **Docker Compose:** a file (`docker-compose.yml`) listing what to start; `docker compose up` starts it all.

*Interview:* "Docker makes the database setup reproducible: one command gives anyone the same Postgres + pgvector version."

### What does FastAPI do?
The website (TypeScript, in the browser) and the engine (Python) are separate programs. FastAPI turns Python functions into web addresses the website can call:

```python
@app.get("/search")
def search(question: str):
    return hybrid_search(question)   # sent back to the browser as JSON
```
Like a waiter: the website orders, FastAPI takes the order to the kitchen (the engine) and brings the food (JSON) back. Chosen because it's the most popular modern Python API framework (widely used for AI model serving), checks inputs automatically, makes a free interactive docs page at `/docs`, and supports streaming for the live map animation. In your Supabase projects, Supabase made the API for you; here you build it yourself.

*Interview:* "The React map calls a FastAPI server, and agent steps stream over Server-Sent Events so the map animates live."

---

## Part 7: How we'll work

- **Before each phase**, I explain what we're about to build and why, in this same style.
- **After each phase**, I add a short "what we did and what to say about it" note to `docs/LEARNING_LOG.md`, so you build your interview notes as you go.
- Every number in the README and resume comes from a real run. If something isn't tested, we say so.
