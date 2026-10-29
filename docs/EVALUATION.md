# How Cartograph is evaluated

Every number in the README comes from a run whose questions, answers and results are files in this repository. If something hasn't been measured, the docs say so.

## Question sets (`eval/express/`)

| File | Questions | How they were made |
|---|---|---|
| `mined.jsonl` | 127 (74 from issues, 53 from pull requests) | Mined from Express's history: a commit that fixes an issue becomes a question (the issue text) and its gold answer (the functions the commit changed). Headline numbers use issue text only, because PR text is written by the person who fixed it and often names the code. |
| `handwritten.jsonl` | 45 | Written by hand to cover question types the miner can't produce. Waiting for review. |
| `order.jsonl` | 35 | "Is X always called before Y?" with gold answers worked out by reading the code. Waiting for review. |

Noise check: a hand sample of mined questions is in `NOISE_CHECK.md`.

## Metrics

- **Acc@k:** a gold function is among the top k results.
- **MRR:** 1 / rank of the first gold function, averaged.
- **Recall@k (impact):** share of the functions that really changed together that appear in the top k guesses.
- **Ordering accuracy:** the answer ("always", "not always", "unreachable") matches the gold.

## Fair comparisons

- **Agents:** the Cartograph agent and the grep-only agent use the same model, prompt style and step budget; only their tools differ. A run is scored on the submitted answer first, then everything it was shown.
- **Impact:** a rolling evaluation, where each commit is predicted only from commits before it, with a same-file baseline.
- **Ordering:** compared with a naive "earlier line wins" baseline.
- **Claude Code + MCP:** same model, prompt and tools, with and without Cartograph; no shell (so no `git log`) and no web; every tool call is recorded.

## Reproducing

```bash
uv run --project engine cartograph eval targets/express --questions eval/express/mined.jsonl --retriever bm25
uv run --project engine cartograph eval targets/express --questions eval/express/mined.jsonl --retriever agent
uv run --project engine cartograph impact-eval targets/express --out eval/express/impact.json
uv run --project engine cartograph order-eval targets/express --questions eval/express/order.jsonl
```

CI re-runs the BM25 and ordering evaluations on Express (pinned to commit `0dee2c5`) on every push, and fails if either score drops below the published one.

## Performance

Measured 29 October 2026 on the development laptop (Windows 11, Python 3.12, Postgres 17 in Docker): wall-clock time and the peak memory of the whole process tree, with `uv run --no-project --with psutil python scripts/peakmem.py uv run --project engine cartograph index <repo>`.

| Repository | Files | Functions | Full index | Nothing changed | Peak memory |
|---|---|---|---|---|---|
| Express (`0dee2c5`) | 141 | 3,113 | 1.6 s | 0.07 s | 76 MB |
| Prettier (`519ce94`) | 5,804 | 9,363 | 33 s | 1.5 s | 93 MB |

Before this measurement, re-resolving every call one database row at a time made the Prettier index take 225 s, and 132 s even when nothing had changed. Two fixes: skip re-resolving when no file changed, and apply all links with one bulk update. The resolution counts were identical before and after.

## Known gaps

- Express is small; results are development numbers until repeated on Prettier.
- Gold answers are checked against today's code, not the code at the time of each fix.
- The Phase 4 agent numbers were measured before the agent learned to recover answers it wrote as text; they need a re-run.
- The hand-written and ordering questions were written by the author of the tool and are not yet independently reviewed.
