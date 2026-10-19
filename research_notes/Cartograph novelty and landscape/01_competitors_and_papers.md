# Notes 01: competitors, MCP code graphs, papers (gathered 2026-10-20)

## Open-source code-graph MCP servers (crowded)
- Codebase-Memory (DeusData/codebase-memory-mcp), arXiv 2603.27277 (28 Mar 2026, Vogel et al.). Single C binary, tree-sitter, 66 languages, 14 MCP structural tools, call graph traversal, impact analysis, Louvain communities. Eval on 31 repos: answer quality 83% vs 92% for a file-exploration (grep/read) agent, ~10x fewer tokens, 2.1x fewer tool calls. https://arxiv.org/abs/2603.27277
  => KEY: graph-only LOST on answer quality to plain grep/read agent. Graph wins on tokens, not accuracy.
- sdsrss/code-graph-mcp: tree-sitter, 10 langs, semantic search, call graph traversal, HTTP route tracing, impact analysis; full tier for TS/JS. https://github.com/sdsrss/code-graph-mcp
- Phoenixrr2113/codebase-graph: tree-sitter, FalkorDB, vector + reranker, "bitemporal knowledge". https://github.com/Phoenixrr2113/codebase-graph
- maxh8086/synaptree-mcp: Neo4j, README admits dynamic dispatch / reflection mislinks. https://github.com/maxh8086/synaptree-mcp
- The-Data-Platform-Project/code-graph-mcp: tree-sitter into Postgres graph (same storage idea as Cartograph). https://github.com/The-Data-Platform-Project/code-graph-mcp
- tirth8205/code-review-graph: SQLite graph incl. test-coverage edges, review focus, claims token reductions. https://github.com/tirth8205/code-review-graph
- codeprysm (Rust). https://github.com/codeprysm/codeprysm
- Graphify (user already has it as a skill): knowledge graph w/ community detection.
- Self-reported claims everywhere; almost none publish retrieval accuracy on a labelled eval.

## Commercial
- Greptile: graph index of files/functions/deps; pivoted to PR code review; MCP server; ~$30/seat/mo (secondary sources). https://www.morphllm.com/comparisons/greptile-vs-copilot
- Augment Context Engine: embeddings + dependency graphs (vendor claim); MCP server since Feb 2026. https://www.augmentcode.com/tools/coderabbit-vs-greptile-vs-augment-cosmos
- Sourcegraph: code graph (SCIP), enterprise from ~$16K/yr (secondary). https://repowise.dev/blog/comparisons/sourcegraph-alternatives-2026
- DeepWiki: free auto-wiki + diagrams + Q&A for public repos.
- repowise.dev publishes "repository intelligence" buyer's guides 2026 -> the category has a name now.

## Grep vs embeddings debate (central to Cartograph's thesis)
- "Is Grep All You Need?" arXiv 2605.15184 (14 May 2026): on LongMemEval (116 Qs, NOT code), grep generally beat vector inside Claude Code / Codex / Gemini CLI harnesses; harness choice shifts results as much as retrieval method. https://arxiv.org/abs/2605.15184
- "Deep Agentic Search for Repository-Level Code QA" arXiv 2608.01507 (2 Aug 2026): on SWE-QA, semantic (vector index) 65.2% correct vs deep agentic grep-by-subagent 46.2%; retrieval < half the cost per correct answer; 41.8% of agentic failures at planner->subagent handoff, silent confident wrong answers. https://arxiv.org/abs/2608.01507
- Agent Retrieval Bench arXiv 2607.24882 (27 Jul 2026): 427 samples, 25 repos; tasks code2test, comment2context, trace2code, edit2ripple; Qwen3-Embedding-4B best MRR, 8B best Recall@20, Aider RepoMap best context yield at 8K tokens; logged agent trajectories miss ALL gold files on 27-35% of samples; no single family dominates; includes abstention (no-gold) cases. https://arxiv.org/abs/2607.24882
- Claim that Claude Code team dropped local vector DB for agentic search: only secondhand (Medium), unverified.
- Survey 2508.06401: BM25 filter then dense rerank cut irrelevant patches >1/3 in code tasks.

## Graph localization papers
- LocAgent (ACL 2025) 2503.09089: heterogeneous code graph + agent tools; SWE-Bench-Lite file Acc@5 ~94%, function Acc@10 ~77%; on Loc-Bench, CodeRankEmbed embedding retriever alone 84.67% file Acc@5 (strong!). Ablation: removing search-entity tool 88.32 -> 68.98.
- MULocBench 2509.25242: 1,100 issues, 46 Python repos, code+non-code files; best methods <40% file Acc@5; LocAgent max 35.2%.
- LARGER 2605.16352 (8 May 2026): lexical anchors -> graph anchors -> confidence-filtered neighborhood expansion (imports, call chains, type hierarchy, code-test links) inside the agent's search loop, no graph DB. +13.9 pts file Acc@5 on LocBench over strongest baseline. Closest academic analog to Cartograph's "BM25 + graph hop" idea.
- FastCode 2603.01012: 86.13% file Acc@1 with Gemini-3-Flash vs LocAgent 77.74%.
- SweRank+ 2512.20482: multilingual ranking, evaluates on SWE-PolyBench, SWE-Bench-Multilingual, Multi-SWE-Bench.
- SpIDER 2512.16956: spatially informed dense retrieval for issue localization.
- Multi-CoLoR 2602.19407: multi-language localization.
- RANGER 2509.25257: repo-level graph-enhanced retrieval agent.
- SHERLOC 2606.24820, "Reformulate, Retrieve, Localize" 2512.07022.

## JS/TS ready-made data
- SWE-PolyBench (AWS, Apr 2025): JavaScript 1,017-1,078 instances (4 repos), TypeScript 729 (5 repos); metrics include file-level AND CST-node-level retrieval precision/recall. 500 stratified subset. https://aws.amazon.com/blogs/devops/amazon-introduces-swe-polybench-a-multi-lingual-benchmark-for-ai-coding-agents
- Multi-SWE-bench (ByteDance, 2504.02605): 1,632 instances, 7 langs incl JS/TS. Some TS/JS repos exceed context for MagentLess.
- BugsJS (ICST 2019): 453 bugs, 10 server-side JS projects (Bower, ESLint, Express, Hessian.js, Hexo, Karma, Mongoose, Node-redis, Pencilblue, Shields), 444k LOC; bug report + tests + fix patch each. https://github.com/BugsJS
