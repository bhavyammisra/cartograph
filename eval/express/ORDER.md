# "Is X always called before Y?" (Express)

A small benchmark of ordering questions, and how Cartograph's ordering engine does on it.

Reproduce:
```
uv run --project engine cartograph order-eval targets/express --questions eval/express/order.jsonl --out eval/express/results/order.json
uv run --project engine cartograph order targets/express res.status this.end          # one question, every entry point
uv run --project engine cartograph order targets/express res.status this.end --start res.send
```

## The questions
35 questions in `order.jsonl`. Answers are written from reading the Express source, with a one-line reason for each. Three possible answers:
- **always:** on every path, X has been called before any call to Y.
- **not always:** some path reaches Y without X first.
- **unreachable:** the starting function never reaches Y.

| Level | What it tests | Questions |
|---|---|---|
| 1 | X and Y called directly by one function, with branches between them | 18 |
| 2 | X or Y reached through other functions | 10 |
| 3 | From every entry point (functions nothing in the repo calls, including the example apps) | 7 |

`"reviewed": false`: Bhavyam has not checked the gold answers yet.

## How the engine works
- **Order inside a function:** calls are kept in the order they run (arguments before the call that uses them).
- **Branch flag:** each call is marked "always runs" or "only sometimes". Sometimes means inside an if/else arm, a `case`, a `catch`, a loop body or a loop's update step, the right side of `&&`, `||` or `??`, or a ternary arm.
- **Across calls:** a call to G "must reach" X if G always calls X, directly or through calls that always run.
- **The rule:** X is always before Y when every call that may reach Y either comes after a call that must reach X, or is itself a call whose function always does X before Y.
- **Proof:** a "not always" answer comes with a counterexample, a call path to a Y with no X before it. For example: `restrict (examples/auth/index.js:80) → res.redirect (lib/response.js:839) → res.location (lib/response.js:798)`.

## Results

| | All (35) | Level 1 (18) | Level 2 (10) | Level 3 (7) |
|---|---|---|---|---|
| Cartograph | **0.943** (33) | 1.000 | 0.800 | 1.000 |
| Naive baseline | 0.343 (12) | 0.556 | 0.100 | 0.143 |

**Naive baseline:** "X's first line comes before Y's first line in the same function". It is fooled by every branch (it said "always" for all 8 level-1 "not always" questions) and can't see through calls (it answers "unreachable" for most level-2 and level-3 questions).

## The two misses (known limits)
- **order-24, a callback:** `res.render` sends only inside the callback it passes to `app.render`. That call is made by a function value, not by name, so the engine can't see that `res.send` is reached at all.
- **order-26, depends on a value:** `app.set('etag', ...)` runs the `case 'etag'` branch, but the engine treats every `case` as "sometimes" and doesn't look at the value being switched on.

## Also limited
- An `if/else` where both arms call X still counts as "sometimes" (no question here depends on it).
- "Always" means "on every path the call graph can see". Wrong call links mislead it. While writing these questions we found two resolver errors: in `res.sendFile`, `send(...)` (the npm module) is linked to `res.send`, and in `res.download`, `resolve(...)` (Node's path module) is linked to `View.prototype.resolve`. No question here depends on those links.

## Fair warning about the numbers
I wrote the questions after designing the engine, so they may favour what it handles. One engine bug was found and fixed while checking a counterexample during this run: a conditional call to a function that does X before Y was wrongly treated as a counterexample. The fix didn't change any answer, only a proof (order-27). The score is from 35 questions on one repo; treat it as a smoke test, not a headline number, until the questions are reviewed and extended to Prettier.
