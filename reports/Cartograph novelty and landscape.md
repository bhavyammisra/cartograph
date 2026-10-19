# Cartograph novelty and landscape

Research date: 20 October 2026. Sources are linked inline. Raw notes are in `research_notes/Cartograph novelty and landscape/`.

## The short answer

The plain idea ("tree-sitter code graph + embeddings + BM25, exposed to an agent, with impact analysis") is no longer new. In 2026 there are at least ten open-source code-graph MCP servers doing roughly that, plus commercial engines from Augment, Greptile and Sourcegraph. If Cartograph is pitched as "a code graph for AI", it is one more of the same.

What is still open, and what a student can own:

1. **Proof, not claims.** Almost every tool in this space publishes self-reported token savings and no retrieval accuracy. Cartograph can be the one that reports measured accuracy on JavaScript, against a grep agent, with ablations. That also answers the most argued question in the field right now: grep, embeddings or graphs?
2. **"X before Y" queries for JavaScript.** Natural language to structural query has been done for Java (Semgrep/GQL, single function). Doing it for JS, across function boundaries, chosen by an agent, is open.
3. **Watching the search happen.** No tool found overlays an agent's retrieval path on an interactive code map for a human. The closest work visualizes agent steps as abstract flow graphs, or makes pictures for the agent rather than for people.
4. **Impact analysis you can trust.** Blast-radius PR bots exist, but none report whether their predictions are right. Checking predictions against the repo's own git history (what actually changed together) is a standard method in software engineering research that tool builders skip.

Recommended positioning line: *"Cartograph shows you where an AI looked, why it picked what it picked, and how accurate it actually is."*

---

## 1. What already exists

| Category | Examples | What they lack (the opening for Cartograph) |
|---|---|---|
| Code-graph MCP servers | [Codebase-Memory](https://arxiv.org/abs/2603.27277) (66 languages, Louvain communities, impact analysis), [code-graph-mcp](https://github.com/sdsrss/code-graph-mcp), [codebase-graph](https://github.com/Phoenixrr2113/codebase-graph), [synaptree-mcp](https://github.com/maxh8086/synaptree-mcp), [code-graph-mcp (Postgres)](https://github.com/The-Data-Platform-Project/code-graph-mcp), [code-review-graph](https://github.com/tirth8205/code-review-graph), [CodePrysm](https://github.com/codeprysm/codeprysm) | Self-reported numbers. No labelled retrieval eval. No measured call-graph accuracy (synaptree's README openly admits dynamic dispatch gets mislinked). No human-facing visual of what the agent did. |
| Commercial context engines | Augment Context Engine (embeddings + dependency graph, MCP since Feb 2026), Greptile (repo graph, now focused on PR review, about $30/seat/month), Sourcegraph (SCIP code graph, enterprise pricing) ([comparison](https://www.augmentcode.com/tools/coderabbit-vs-greptile-vs-augment-cosmos), [repowise guide](https://repowise.dev/blog/comparisons/sourcegraph-alternatives-2026)) | Closed. Internals mostly vendor claims. Not something a student competes with on scale; compete on transparency. |
| Coding agents | Cursor (trained its own embedding model; [semantic search raised agent accuracy about 12.5% on average](https://cursor.com/blog/semsearch)), Claude Code / Codex / Gemini CLI (agentic grep) | No map. No explanation of why a file was picked. |
| Auto-wikis | DeepWiki, Google Code Wiki ([launched Nov 2025](https://alternativeto.net/news/2025/11/google-launches-code-wiki-a-continuously-updated-and-gemini-powered-documentation-platform/)) | Static diagrams and prose. Not function-level, not interactive, no trace. They make "guided tours" a weak differentiator. |
| Code visualizers | CodeSee (acquired by GitKraken, [May 2024](https://www.gitkraken.com/blog/gitkraken-launches-devex-platform-acquires-codesee), after announcing it was shutting down commercial operations), Sourcetrail (discontinued 2021) | Lesson: maps alone did not sell. A map must answer a question the developer already has. Cartograph's map is driven by queries and impact, which is the right instinct. |
| PR blast-radius bots | [repograph](https://github.com/4ff4n/repograph), code-review-graph Action, [impactgraph](https://pypi.org/project/impactgraph/), N3MO, blast-radius-check | None report precision or recall of their impact predictions. |
| Agent trace viewers | [TraceView](https://arxiv.org/abs/2606.22110) (Jun 2026), [Illuminating LLM Coding Agents](https://arxiv.org/html/2508.12555), agent-flow, zoetrope, TraceVista, VS Code "Coding Agent Trajectory Viewer" ([topic list](https://github.com/topics/agent-visualization)) | They draw the agent's steps as their own graph (thought, action, result). None place the steps on the code's structure. |
| Visual views for the agent | [RepoAtlas](https://arxiv.org/abs/2609.16936) (Sep 2026) renders code-graph regions as images for the agent; +2.4 points resolve rate on SWE-bench Verified | Built for the model, not for a human watching. |

Uncertainty: the "nobody overlays agent paths on a code map" claim comes from searching, not from proof. Re-check before you put "first" anywhere; safer wording is "I didn't find an existing tool that does this."

---

## 2. The big 2026 debate: grep vs embeddings vs graphs

This is the most useful finding for the project, because Cartograph's eval can add real evidence to an open argument.

| Evidence | Result |
|---|---|
| [Cursor, semantic search](https://cursor.com/blog/semsearch) (Nov 2025) | Adding semantic search to the agent improved accuracy in every model tested, about 12.5% average (6.5% to 23.5%). |
| [Deep Agentic Search for repo QA](https://arxiv.org/abs/2608.01507) (Aug 2026, SWE-QA) | Vector index answered 65.2% correctly vs 46.2% for grep-by-subagent, at under half the cost per correct answer. 41.8% of agentic failures happened at the planner-to-subagent handoff and were silent, confident, wrong answers. |
| [Is Grep All You Need?](https://arxiv.org/abs/2605.15184) (May 2026) | Grep generally beat vectors inside Claude Code, Codex and Gemini CLI, but on a conversation-memory benchmark, not code. The harness mattered as much as the retrieval method. |
| [Agent Retrieval Bench](https://arxiv.org/abs/2607.24882) (Jul 2026, 25 repos) | No single method wins everywhere. Qwen3-Embedding best MRR, Aider's RepoMap best context per 8K tokens. Logged agent runs missed every correct file in 27 to 35% of samples. |
| [Codebase-Memory](https://arxiv.org/abs/2603.27277) (Mar 2026, 31 repos) | Graph-only tools: about 10x fewer tokens, but answer quality 83% vs 92% for a plain read-and-grep agent. |
| [LocAgent](https://arxiv.org/abs/2503.09089) (ACL 2025) | On Loc-Bench, a 137M embedding model (CodeRankEmbed) alone reached 84.67% file-level Acc@5, close to full agent systems. |
| [LARGER](https://arxiv.org/abs/2605.16352) (May 2026) | Start from lexical (grep/BM25) hits, then expand along graph edges (imports, calls, type hierarchy, tests): +13.9 points file Acc@5 on LocBench over the strongest baseline. |

What this means for Cartograph:

- **Your baseline must be a grep agent, not just BM25.** A BM25-only baseline is a straw man in 2026. The fair comparison is: grep agent vs BM25 vs embeddings vs hybrid (RRF) vs hybrid + graph hops vs full Cartograph agent.
- **The graph is a supplement, not the main retriever.** Codebase-Memory shows a graph alone loses on accuracy. LARGER shows "lexical anchor, then graph expansion" wins. Design the agent that way.
- **Report cost and tokens per correct answer**, not only accuracy. That is where graphs and indexes earn their place.
- **Interview story:** "There's an open argument about whether agents need indexes. I measured it on JavaScript. Here's when each one wins."

---

## 3. Novelty audit: what you can and can't claim

| Feature | Prior art | Verdict |
|---|---|---|
| Hybrid BM25 + dense + RRF | Everywhere (RAG standard, Augment, papers) | Not novel. Table stakes. |
| Tree-sitter call graph + MCP server | 10+ open-source projects | Not novel. Still worth shipping (convenience). |
| BFS impact / blast radius | Codebase-Memory, code-graph-mcp, PR bots | Not novel as a feature. **Novel if validated** against co-change history and reported with precision/recall. |
| Leiden/Louvain community map | Codebase-Memory, Graphify | Not novel. |
| "X before Y" structural queries | [NL to Semgrep/GQL for Java](https://arxiv.org/abs/2507.02107) (55 to 70% P/R, 400 queries, 10 Java projects). [Semgrep](https://docs.semgrep.dev/writing-rules/pattern-syntax) matches `foo() ... bar()` only inside one block, one file. | **Open for JavaScript, across function calls.** Strongest technical novelty. |
| Live agent path on a code map | Trace viewers draw abstract flow graphs; RepoAtlas draws for the agent | **Not found anywhere.** Strongest demo novelty. |
| "Why this result" provenance (which index found it, its rank, which edge led there) | Not found in code search tools | Novel and cheap: you already have the data. |
| Measured call-graph quality for JS (tree-sitter vs a real analyzer) | Tools don't report it | Novel for a tool. Easy with Jelly (below). |
| Auto-generated eval from the repo's own git history | SWE-rebench, SWE-PolyBench mine PRs at scale | Method not novel; **"evaluate on your own repo with one command" is** a convenience novelty. |

---

## 4. What to add, ranked

### Tier 1: must have (this is what makes the numbers credible)

1. **Three eval sets instead of one.**
   - *Hand-labelled set* (your 40 to 60 questions, split across meaning / usage / structural). Keep it.
   - *Auto-mined set from git history.* For each bug-fix commit with a linked issue, the question is the issue title and body, the gold answer is the functions the fix changed. Hundreds of questions for free, and it scales to any repo. Filter out commits that only touch tests or docs.
   - *External set for comparison.* [SWE-PolyBench](https://github.com/amazon-science/SWE-PolyBench) has a Verified split with 100 JavaScript and 100 TypeScript tasks, and published JS file-retrieval numbers to compare against: the best agent (Aider with Sonnet 3.5) reached 37.1% recall / 53.5% precision on JS files ([paper](https://arxiv.org/html/2504.08703)). Beating that on even a subset is a striking line. [BugsJS](https://github.com/BugsJS) (453 hand-validated bugs from Express, ESLint, Mongoose, Hexo, Karma and others) is a second option.
2. **Function-level metrics, not just file-level.** Use SWE-PolyBench's definition: the deepest function/class node overlapping the gold change. Report Acc@1/5/10, MRR, Recall@k, p50/p95 latency, tokens and cost per query, index time, index size. [TraceProbe](https://arxiv.org/abs/2607.06184) found file choice is too coarse to tell good runs from bad ones; function level is where the signal is.
3. **Ablation grid with a grep-agent baseline** (section 2). Same LLM, same budget, only retrieval tools change.
4. **Two-tier call graph with measured accuracy.** Fast tier: tree-sitter (resolves direct calls, `this.method()`, calls on imported names; misses calls through variables and dynamic dispatch). Precise tier: [Jelly](https://github.com/cs-au-dk/jelly) (BSD-3, `npm install -g @cs-au-dk/jelly`, outputs JSON with `-j`, has a built-in `--compare-callgraphs` for precision/recall). Jelly's approximate interpretation raised recall from 75.9% to 88.1% on 36 projects ([PLDI 2024](https://dl.acm.org/doi/10.1145/3656424)). Report "tree-sitter edges are X% precise and Y% complete vs Jelly". Each edge stores its source and confidence, and the map can draw unsure edges dashed.
5. **"Not found" answers.** Agent Retrieval Bench shows systems rarely abstain. Add a few questions with no answer in the repo and score whether the agent says so instead of making something up.

### Tier 2: the standout features

6. **"X before Y" queries.** Three levels, each testable:
   - same function: statement order from the tree-sitter AST (what Semgrep does);
   - across calls: X reaches Y along a call path, with X's call site before Y's in each function on the path;
   - entry-point order: on every path from a route handler / exported function, is `validateUser` called before `saveOrder`? Report the counterexample paths ("checkout skips validation here").
   Build a small published benchmark of 30 or so such queries with gold answers on the target repo. That alone is a citable artifact.
7. **Agent trace replay on the map, with provenance.** Every tool call becomes an event: query, index used, results with RRF rank and per-index rank, edges followed. The map replays it: visited nodes light up, graph hops draw as trails, discarded results fade, answers glow. Clicking an answer shows *why*: "BM25 rank 3, embedding rank 1, reached via `checkout -> charge`". Also flag diagnostics TraceProbe found useful: search loops and revisits.
8. **Impact analysis validated against history.** For each past commit that changed function f, predict f's blast radius with reverse-call-graph BFS, then check which other functions the same commit (or the next few) actually changed. Report precision/recall for: call graph only, co-change only, and both combined. Combining structural and history signals beat either alone in the classic study by [Kagdi et al. (WCRE 2010)](https://www.cs.wm.edu/semeru/papers/WCRE2010_KagGet.pdf). Then the PR comment can say "likely affected (seen changing together 7 times)" instead of a bare list.
9. **MCP server, measured.** Expose the same tools to Claude Code. Measure tokens and accuracy with and without Cartograph on your eval set. That is the convenience feature and a second number in one.

### Tier 3: defer or skip

- **Guided tours:** DeepWiki and Google Code Wiki already do this at scale. Only add if time remains, built on top of trace replay.
- **Multiple languages:** stay JS/TS. Depth beats breadth here.
- **VS Code extension:** later. MCP plus a web app covers most users.
- **Fine-tuning:** optional, but now well motivated. [CORE-Bench](https://arxiv.org/abs/2606.11864) (EMNLP 2026) found simple fine-tuning of existing embedding models gives large gains on agentic code retrieval. Your auto-mined set is the training data; keep the hand-labelled set held out.

---

## 5. Decisions the brief left open

| Question | Recommendation | Why |
|---|---|---|
| Postgres: Supabase vs local Docker | **[PGlite](https://pglite.dev) with pgvector** locally, same schema on Supabase for the hosted demo | PGlite is Postgres compiled to WASM, runs inside Node with no install, supports pgvector, persists to disk, about 10M weekly npm downloads ([Jun 2026](https://electric.ax/blog/2026/06/25/pglite-reaches-10-million-weekly-downloads.md)). Keeps your Postgres skills central and still allows `npx cartograph`. Limit: single process. |
| Embedding model on CPU | **[CodeRankEmbed](https://huggingface.co/nomic-ai/CodeRankEmbed)** (137M, MIT, 8K context) as default; **[jina-code-embeddings-0.5b](https://jina.ai/news/jina-code-embeddings-sota-code-retrieval-at-0-5b-and-1-5b)** (494M) as the quality comparison | CodeRankEmbed already scored 84.67% file Acc@5 on Loc-Bench. Jina reports the 0.5B beats Qwen3-Embedding-0.6B by about 5 points (vendor claim). Measure both; the comparison is itself a result. |
| Engine language | **TypeScript for the engine, Python for eval and fine-tuning** | Tree-sitter, Jelly, PGlite, the MCP SDK, transformers.js (ONNX on CPU) and React all live in the Node world, so one language ships as one `npx` command. Python stays where it is strongest. This changes the brief's "Python backend"; your call. |
| LLM for the agent | Any model with tool calling; pick one cheap and one strong, run both | The harness and model shift results a lot ("Is Grep All You Need?"), so two models make the findings sturdier. Check current prices before choosing; log cost per query. |
| Graph rendering | **Sigma.js + graphology**, layout precomputed at index time | WebGL, handles thousands to tens of thousands of nodes; Cytoscape.js slows past the low thousands. Render files/modules when zoomed out and functions when zoomed in, so it never becomes a hairball. |

---

## 6. Which repo to evaluate on

| Role | Repo | Why |
|---|---|---|
| Building and debugging | **Express** | Small, pure JS, in BugsJS. Fast to re-index while you iterate. |
| Headline eval | **Prettier** | Pure JavaScript, large, long history (9,600+ PRs), in SWE-PolyBench's JS pool, so there's an external number to compare against. |
| Generalization check | **ESLint** | Large plugin-style codebase (lots of "where do we handle X" questions), in BugsJS, rich history. |

Check before committing: how many SWE-PolyBench Verified JS tasks actually come from Prettier (the paper lists repos per PR pool, not final per-repo counts). If too few, use axios, lodash or three.js tasks from the same benchmark instead. Report file counts and LOC you measure, not ones quoted here.

---

## 7. Making it convenient (and recruiter-friendly)

- **One command:** `npx cartograph index .` then `npx cartograph open`. No Docker, no API key needed to browse the map.
- **Hosted demo that costs nothing to run:** a Vercel page with Prettier pre-indexed and 5 to 10 recorded agent traces that replay on the map. No live LLM calls, so it never breaks or bills you. Live querying stays local.
- **`npx cartograph eval`:** runs the auto-mined eval on *your* repo and prints the metrics table. Nobody else offers "how good is code search on my codebase?"
- **MCP server:** `cartograph mcp` for Claude Code / Cursor.
- **GitHub Action (stretch):** PR comment with the validated blast radius and a link to the map focused on changed functions.
- **README that leads with the results table and a 20-second GIF**, then setup. Recruiters read the first screen only.

Resume bullet shape (fill only with numbers you measure):

> Built Cartograph, an agentic code-search engine for JavaScript combining tree-sitter and Jelly call graphs, BM25 and pgvector embeddings (RRF); reached [X] function-level Acc@5 on [N] questions mined from git history vs [Y] for a grep-based agent, at [Z] s median latency on CPU.

Interview stories this sets up: the grep vs index debate with your own data; call-graph precision in a dynamic language; "X before Y" as graph search with ordering constraints; validating impact analysis against history.

---

## 8. Revised build order

Put the eval harness second, not after the agent, so every later feature is measured the day it lands.

1. Indexer: tree-sitter functions, calls, imports into PGlite. Express first.
2. Eval harness: auto-miner from git history + metrics + grep-agent and BM25 baselines.
3. Embeddings (CodeRankEmbed) + RRF hybrid; first ablation table.
4. Agent loop (plan, search, read, follow edges, answer, abstain) with event logging.
5. Jelly precise tier + call-graph accuracy report. Switch to Prettier for the headline eval.
6. Map (Sigma.js, communities, semantic zoom, click for code).
7. Trace replay + "why this result".
8. Impact analysis + co-change validation.
9. "X before Y" queries + their mini benchmark.
10. Packaging: npx, MCP, hosted demo, README, demo video. SWE-PolyBench subset run.

Each step is about a week; steps 8 and 9 can swap based on time.

---

## 9. Risks and open questions

- **Novelty claims are search-based.** Re-check the "agent path on a code map" claim close to publishing.
- **Several benchmark numbers come from abstracts or vendor pages** (Jina's scores, Codebase-Memory's 83% vs 92%). Fine for planning, but cite primary sources if you quote them.
- **The auto-mined eval has noise:** fix commits often touch unrelated files. Hand-check a random sample of 50 and report the noise rate.
- **Fair LLM comparisons cost money.** Budget it early; cache everything.
- **"X before Y" across functions can explode on big repos.** Cap path depth and say so.
- **Samsung's original setting** (voice-assistant codebases with agents and tools) has no public equivalent; JS open source is the honest stand-in.
