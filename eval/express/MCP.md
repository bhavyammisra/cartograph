# Cartograph as an MCP server for Claude Code (Express)

**Question:** does giving Claude Code Cartograph's tools help it find the code an issue is about?

Reproduce (needs the `claude` CLI signed in; uses your Claude allowance):
```
uv run --project engine python scripts/claude_eval.py --repo targets/express --questions eval/express/mined.jsonl --sample 20 --model sonnet
uv run --project engine python scripts/claude_eval.py --repo targets/express --questions eval/express/mined.jsonl --sample 20 --model sonnet --nudge --out eval/express/results/claude-code-mcp-nudged.jsonl
```

## Setup
- **Questions:** 20 issue-sourced questions from `mined.jsonl` (random sample, seed 0). The issue text was written by users, not by whoever fixed it. Gold: the functions the fix commit changed.
- **Claude Code** 2.1.300, headless (`claude -p`), model Sonnet, project settings only, no session saved.
- **Tools:** Read, Grep and Glob only, so no shell (no `git log` to find the fix commit) and no web.
- **Three conditions, same prompt:**
  1. **Alone:** Read, Grep, Glob.
  2. **+ Cartograph:** the same, plus Cartograph's 4 MCP tools (`search_code`, `get_function`, `impact`, `check_order`), with nothing in the prompt about them.
  3. **+ Cartograph, nudged:** the same as 2, plus one sentence at the end of the prompt: "This repository is indexed by Cartograph: prefer its MCP tools (search_code first)." That is the line a user would put in their CLAUDE.md.
- **Scoring:** Claude ends with up to 5 `path:line` lines. Each is mapped to the function containing that line and compared with the gold.
- **Tokens and cost:** from Claude Code's own output. Tool calls come from its event stream.

## Results

| | Top-1 right | Top-5 right | Right file | Input tokens, mean (median) | Output tokens | Turns | Seconds | Cost (API-equivalent) |
|---|---|---|---|---|---|---|---|---|
| Claude Code alone | 15/20 | 18/20 | 20/20 | 23,823 (22,214) | 617 | 3.75 | 18.3 | $0.45 |
| + Cartograph | 16/20 | 18/20 | 19/20 | 26,443 (24,842) | 628 | 3.50 | 22.4 | $0.47 |
| + Cartograph, nudged | 12/20 | 19/20 | 20/20 | 26,079 (24,904) | 520 | 3.65 | 26.1 | $0.44 |

Input tokens include cached prompt tokens. Cost is what Claude Code reports; on a subscription this comes out of the plan's usage.

## What happened
1. **Without a nudge, Claude Code never used Cartograph.** Every run had the tools connected (checked in the event stream). Claude called Grep and Read in all 20 runs and Cartograph in none. The +2.6k input tokens are just the tool descriptions being sent. Same answers, same steps, so the accuracy differences between conditions 1 and 2 are noise.
2. **With the nudge, it used Cartograph every time:** `search_code` in 20 of 20 runs (21 calls), and `get_function` twice in one run. It still read files in 15 runs, and used Grep in 8.
3. **No accuracy gain on Express.** Top-5: 19 vs 18. Top-1: 12 vs 15. In 4 of the 5 questions that changed, the right function dropped from first to second, behind a related function the search ranked higher (for example `res.redirect` ahead of `res.location`), and stayed in the top 5. One question went from wrong to right (express-842).
4. **No token or time savings.** Express is six library files. Grep finds the right function in one or two calls, so there is little for an index to save. The extra seconds come from starting the server and loading the embedding model for the first search (about 15 s).

## Verdict
On a small repo like Express, Cartograph's MCP tools add cost (about 10% more input tokens, plus a few seconds) and no measurable accuracy. Claude Code doesn't reach for unfamiliar tools unless told to. The case for an index is a repo where grep returns too much to read. That is untested here, and it's the next measurement (Prettier, many small files).

## Limits
- 20 questions, one small repo, one model; differences of 1 to 3 questions are noise.
- Gold answers are the functions a fix commit changed, checked against today's code.
- The first two conditions were run in two sittings, because a usage limit stopped the first one. The 12 "+ Cartograph" runs from before tool tracking was added were deleted and run again, so every run in the table has its tool calls recorded except the first 13 "alone" runs, which can't use Cartograph anyway.
