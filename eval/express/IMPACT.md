# Impact analysis vs git co-change (Express)

**Question:** when a developer changed function f, could we have predicted the other functions they changed in the same commit?

Reproduce: `uv run --project engine cartograph impact-eval targets/express --out eval/express/impact.json`

## Setup
- **History:** every non-merge commit touching `lib/` (2,321 commits). For each one, the functions whose old body the diff touched (same rule as the question miner).
- **Kept:** commits that changed 2 to 30 functions that still exist today: 102 commits. Bigger commits are mass refactors; functions that no longer exist can't be checked against today's graph.
- **Rolling, no peeking:** each commit is predicted only from commits before it. The first 20 commits only teach. Tested: 82 commits from November 2011 on, 245 cases (each changed function takes a turn as "the one being edited").
- **Methods:**
  - *Call graph:* everything that calls f, up to 3 hops (`/api/impact`), nearest first.
  - *Co-change history:* functions that changed together with f in earlier commits, most often first.
  - *Both:* history first, then the call graph.
  - *Same file (baseline):* the rest of f's file, closest lines first.

## Results

| Method | Recall@5 | Recall@10 | Recall (all guesses) | Precision | Guesses (mean) | Has a guess |
|---|---|---|---|---|---|---|
| Call graph (3 hops) | 0.048 | 0.073 | 0.123 | 0.033 | 19.1 | 76% |
| Co-change history | 0.294 | 0.380 | 0.400 | 0.254 | 5.3 | 80% |
| Both | **0.311** | 0.411 | 0.452 | 0.134 | 23.8 | 92% |
| Same file, nearest first | 0.266 | **0.427** | 0.782 | 0.113 | 29.9 | 100% |

Recall: share of the functions that really changed that the method found. Precision: share of its guesses that really changed (averaged over cases where it guessed anything). Depth 1 call graph: recall@5 0.045, precision 0.098.

## What it means
1. **The call graph does not predict what gets edited together.** Recall@5 is 0.048. Changing a function rarely forces its callers to change: most edits keep the function's contract. The call graph answers a different question, "who depends on this", which is what you re-test, not what you edit.
2. **History is the best single predictor for what you'll edit next:** about 6x the call graph's recall@5 with a quarter of the guesses, and the most precise method (0.254).
3. **Both combined is best in the top 5** (0.311), narrowly ahead of the same-file baseline (0.266).
4. **The baseline is strong on Express** because the library is six files: `lib/` has 109 named functions, 41 of them in `response.js`, so "same file" covers a large share of the codebase. Expect it to be weaker on a repo with many small files; Prettier will tell.

## What the product does with it
The function panel shows both, labelled for what they are:
- **Often changed with:** from history, with how many commits (`cartograph impact-eval` mines and caches it; `serve` loads the cache).
- **Called by:** from the call graph; `/api/impact` gives the full 3-hop list.

## Limits
- 245 cases from one small repo; differences of a few points are within noise.
- The call graph is today's, not the graph at each commit's time.
- A changed function is matched by file and full name; renamed or moved functions drop out (459 of 561 multi-function commits were lost this way or were too big).
