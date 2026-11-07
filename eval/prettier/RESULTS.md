# Prettier results

[Prettier](https://github.com/prettier/prettier) at `519ce94`: 5,804 files, 9,363 functions (Express has 141 files). Measured 29 October to 8 November 2026 on the development laptop (i5-12450HX, RTX 2050 4 GB).

## Questions
- `mined.jsonl`: 561 questions mined from Prettier's history (`cartograph mine`). The text is a GitHub issue (232) or, when a fix links no issue, its pull request (329). The answer ("gold") is the functions the fix commit changed under `src/`.
- `issues-sample60.jsonl`: 60 of the issue questions, drawn at random, for the slow methods (agents, Claude Code).
- Noise check: 12 of 12 hand-checked gold sets point at the right code ([NOISE_CHECK.md](NOISE_CHECK.md)).

This is a much harder set than Express. Issue reports describe formatting output with code samples and almost never name Prettier's functions: 503 of 561 questions don't contain the answer's name. The gold is often a large generic printer function such as `genericPrint`.

## Search, all 561 questions
Acc@k: a gold function is in the top k. File@5: a gold file is in the top 5.

| Method | Issues (232) Acc@5 | PRs (329) Acc@5 | All Acc@1 | All Acc@5 | All File@5 |
|---|---|---|---|---|---|
| BM25 keyword search | 0.164 | 0.073 | 0.045 | 0.111 | 0.164 |
| Meaning search (CodeRankEmbed) | 0.103 | **0.304** | **0.118** | **0.221** | **0.426** |
| Hybrid (RRF of both) | 0.164 | 0.191 | 0.066 | 0.180 | 0.321 |

Meaning search is best on pull-request text (written by maintainers, in code vocabulary) and worst on issue text (written by users, about output). Hybrid doesn't beat the better of its two parts on either kind. On Express hybrid won (0.78 vs 0.70 for BM25).

## Agents, 60 issue questions
Same free local model (Qwen3 4B in Ollama), same step budget (8), same questions; only the tools differ. "Answer right": the function the agent finally submitted is a gold one.

| Method | Acc@1 | Acc@5 | Acc@10 | File@5 | Answer right | Steps | Median time |
|---|---|---|---|---|---|---|---|
| BM25 keyword search | 0.033 | 0.133 | 0.233 | 0.183 | | | |
| Hybrid search | 0.050 | 0.150 | 0.233 | 0.283 | | | |
| Grep-only agent | **0.133** | 0.150 | 0.167 | 0.200 | 0.083 | 5.2 | 36 s |
| **Cartograph agent** | 0.117 | **0.233** | **0.283** | **0.417** | **0.150** | 6.4 | 48 s |

The Cartograph agent finds a right function in its top 5 for 14 of 60 reports, against 9 for the grep agent, and the right file twice as often (25 vs 12). Its final answer is right about twice as often (9 vs 5). Top-1 is a tie within noise (7 vs 8). It costs about 1 more step and 12 s more per question.

## Claude Code with Cartograph's MCP tools, 20 issue questions
Same setup as [the Express run](../express/MCP.md): Claude Code 2.1.300, `claude -p`, Sonnet, only Read, Grep and Glob (no shell, no web), 20 questions drawn from `issues-sample60.jsonl` (seed 0). Reproduce:
```
uv run --project engine python scripts/claude_eval.py --repo targets/prettier --questions eval/prettier/issues-sample60.jsonl --sample 20 --model sonnet --out eval/prettier/results/claude-code-mcp.jsonl
uv run --project engine python scripts/claude_eval.py --repo targets/prettier --questions eval/prettier/issues-sample60.jsonl --sample 20 --model sonnet --nudge --out eval/prettier/results/claude-code-mcp-nudged.jsonl
```

| | Top-1 right | Top-5 right | Right file | Input tokens, mean (median) | Output tokens | Turns | Seconds | Cost (API-equivalent) |
|---|---|---|---|---|---|---|---|---|
| Claude Code alone | 9/20 | 13/20 | 13/20 | 68,761 (51,516) | 1,888 | 8.15 | 27.4 | $1.17 |
| + Cartograph, no hint | 13/20 | 17/20 | 17/20 | 69,756 (61,860) | 1,769 | 8.30 | 28.5 | $1.13 |
| + Cartograph, nudged | 9/20 | 14/20 | 16/20 | **49,315 (41,370)** | **1,314** | **6.35** | 27.9 | **$0.87** |

"Nudged" adds one sentence to the prompt: "This repository is indexed by Cartograph: prefer its MCP tools (search_code first)."

### What happened
1. **Without the hint, Claude Code used Cartograph in 3 of 20 runs** (one `search_code` call each; all 3 were right). On Express it used it in 0 of 20.
2. **The 13 vs 17 gap is mostly noise.** In the 17 questions where the "no hint" run never touched Cartograph, both conditions had identical tools, yet 4 answers changed (3 better, 1 worse). Two of the alone runs also stopped before giving any `path:line` answer. Differences of up to about 4 questions out of 20 are run-to-run variation.
3. **With the hint, accuracy is the same as alone (14 vs 13) and it is cheaper:** 28% fewer input tokens, 30% fewer output tokens, 22% fewer turns, 26% lower cost, same wall time. It called `search_code` in all 20 runs (25 Cartograph calls) and used Grep in 15 runs instead of 20.
4. On Express the same hint cost about 10% more input tokens. The difference: on a 6-file library one grep finds the function; on Prettier grep returns many files to read, and a ranked list of functions replaces part of that reading.

### Verdict
On a large repository, pointing Claude Code at Cartograph cut its token use by about a quarter at the same accuracy. It did not make it more accurate in this sample. Left unprompted, Claude Code rarely uses the tools.

## Limits
- 60 agent questions and 20 Claude Code questions from one repository. Differences of a few questions are noise; the token difference is the clearest signal, and it is also from only 20 runs per condition.
- Gold answers are the functions a fix commit changed, checked against today's code (not the code at the time of each fix).
- The local agent run was interrupted twice (Docker stopped overnight) and resumed from its checkpoint; finished questions were not re-run.
