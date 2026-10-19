# Notes 02: tech choices, visualization prior art, eval, distribution (gathered 2026-10-20)

## Cursor semantic search (primary source)
- cursor.com/blog/semsearch (Nov 2025): Cursor Context Bench; semantic search raised agent accuracy ~12.5% avg (6.5%-23.5% by model); own trained embedding model. Semantic search + grep together is their production answer.

## SWE-PolyBench JS/TS detail (arXiv 2504.08703)
- JS repos: nodejs/node, vercel/next.js, mrdoob/three.js, facebook/react, twbs/bootstrap, prettier/prettier, angular/angular.js, sveltejs/svelte, atom/atom, serverless/serverless, axios/axios, lodash/lodash (PR pools; final 1,078 JS instances).
- TS repos: freeCodeCamp, vscode, angular, mui/material-ui, storybook, supabase, puppeteer, tailwindcss, code-server, realworld (729 instances).
- Verified split: 100 JS + 100 TS. HF: AmazonScience/SWE-PolyBench_Verified.
- File-level retrieval, JS: Aider-PB(Sonnet 3.5) recall 37.1 / precision 53.5; SWE-Agent 27.5/28.5; Agentless 23.4/35.2. TS: Aider 33.3/52.0. => JS localization is far from solved; Aider's repo-map (tree-sitter + PageRank) is the best of these.
- CST node metric: deepest class/function/module node overlapping the patch; precision/recall over node sets. Reusable for Cartograph function-level scoring.

## Structural NL queries (prior art)
- Semgrep: `foo() ... bar()` matches ordered statements in the same block; ellipsis does not jump blocks; single-file; not interprocedural. https://docs.semgrep.dev/writing-rules/pattern-syntax
- CodeQL JS: callEdge predicate, CFG modules; interprocedural ordering possible in principle but must be hand-written.
- "Structural Code Search using Natural Language Queries" arXiv 2507.02107 (Jul 2025, Limpanukorn et al., UCLA + Amazon): LLM translates NL -> Semgrep / GQL; 400-query benchmark over 10 JAVA projects; P/R 55-70%; beats semantic code search by up to 57% F1. => NL->structural for JavaScript with interprocedural ordering is open.
- Merlin (NL -> CodeQL with self-test loop, 182 Qs, 13 codebases); QLCoder (ICLR 2026, CVE -> CodeQL).

## JS call graphs
- Jelly (cs-au-dk/jelly): JS/TS static call graph; approximate interpretation (PLDI 2024, Laursen, Xu, Møller) raised recall 75.9% -> 88.1% on 36 projects with negligible precision loss. `--approx` flag. Can export call graph JSON. Strong candidate as "precise tier" to compare against tree-sitter-only edges.
- 2025 EMSE study (Springer 10.1007/s10664-025-10704-3) on LLMs for call graphs in Python/JS; SWARM-JS micro-benchmark.
- tree-sitter-only TS call graphs resolve identifier calls, this.method(), member calls on imported names; NOT calls through local variables / dynamic dispatch (witc docs). synaptree README admits mislinks.
- Stack graphs (GitHub): tree-sitter based name resolution, file-incremental; TS rules community-level.
- ACG ("Efficient construction of approximate call graphs for JavaScript IDE services", Feldthaus et al., ICSE 2013) is the classic field-based approach tree-sitter tools approximate.

## Embeddings (CPU)
- jina-code-embeddings-0.5b (494M) and 1.5b; avg 78.41% / 79.04% over 25 code retrieval benchmarks; 0.5b beats Qwen3-Embedding-0.6B by ~5 pts; GGUF 1-4 bit quantizations; CoIR 73.94 claimed (vendor). https://jina.ai/news/jina-code-embeddings-sota-code-retrieval-at-0-5b-and-1-5b
- nomic-ai/CodeRankEmbed: 137M bi-encoder, 8192 ctx, MIT, ~547MB, ONNX q8 community export exists; on Loc-Bench it alone hits 84.67% file Acc@5 (LocAgent paper). Best size/quality for CPU.
- nomic-embed-code: 7B (too big for CPU indexing of large repos).
- Granite-embedding-small-english-r2: CoIR 53.4 NDCG@10 (zero-shot code).
- EmbeddingGemma 300M: MTEB Code 68.76.
- CORE-Bench (EMNLP 2026, arXiv 2606.11864): 180K queries; performance drops sharply from classic code search to agentic-coding retrieval; simple SFT of existing embedders helps a lot => supports the optional fine-tuning step.
- transformers.js runs ONNX embeddings in Node on CPU (q8).

## Storage
- PGlite (electric-sql): WASM Postgres in Node, pgvector extension, file persistence, 10M weekly downloads (Jun 2026), single-user. => keeps Postgres+pgvector AND allows `npx` install with no Docker. Server Postgres/Supabase can be the same schema.

## Visualization prior art
- CodeSee: acquired by GitKraken May 2024, CodeSee had earlier announced shutting down commercial operations. Sourcetrail discontinued (2021), community fork exists.
- Google Code Wiki (public preview Nov 2025), DeepWiki: auto wikis + diagrams + chat. Static diagrams, not interactive graphs of functions.
- Agent trace viz: TraceView (arXiv 2606.22110, Jun 2026) graphs Thought/Action/Result of repair agents, NOT on a code map; "Illuminating LLM Coding Agents" (2508.12555) visual analytics of trajectories; agent-flow, zoetrope, TraceVista (live flow graphs of Claude Code sessions); VS Code "Coding Agent Trajectory Viewer". TraceProbe (2607.06184): 2,500 SWE-bench Verified trajectories; file choice too coarse to separate success/failure, function selection + search loops matter.
- RepoAtlas (arXiv 2609.16936, Sep 2026): projects task-relevant code-graph regions into visual + text views FOR THE AGENT; +2.4 resolve rate on SWE-bench Verified. Not a human-facing path replay.
- => No found tool overlays an agent's retrieval path on an interactive code map for humans. Novelty claim holds as of Oct 2026 (with search-based caveat).
- Libraries: Sigma.js (WebGL, graphology, thousands-100k), cosmos.gl (GPU force layout, 100k+), Cytoscape.js (rich layouts, slower past low thousands).

## Impact analysis validation
- Classic: Kagdi et al. WCRE 2010 / EMSE 2013 use commit co-change history as ground truth for impact sets, P/R; combined conceptual + evolutionary coupling beats either alone.
- Islam et al. SCAM 2018 transitive evolutionary coupling; ESEM 2024 integrate 12 change relationships with TARMAQ.
- => Validate Cartograph's BFS blast radius against real co-change (files/functions modified together in later commits). Standard method in SE literature, rarely done by tool builders.
- Existing PR blast-radius tools: repograph (Python AST), code-review-graph (GitHub Action), impactgraph (PyPI), N3MO, blast-radius-check. Crowded, none report accuracy.

## Auto-mined eval
- SWE-rebench V2: 32K+ tasks, 20 languages, from PR histories (no per-instance human verification). SWE-smith: synthetic bugs (Python).
- BugsJS: 453 manually validated JS bugs, 10 projects (Express, ESLint, Mongoose, Hexo, Karma...).
