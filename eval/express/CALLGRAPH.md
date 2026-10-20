# Call graph accuracy: Cartograph (tree-sitter) vs Jelly, on Express

20 October 2026. Scope: Express's own code (`lib/`, `examples/`, `index.js`), 50 files. Jelly 0.13.0, static analysis only (no approximate interpretation, which executes code), with Express's runtime dependencies installed so Jelly can analyze through them; only edges between Express's own functions are compared. Raw numbers: `callgraph-vs-jelly.json`. Reproduce: `cartograph jelly ../targets/express --entries lib examples index.js`.

## Raw agreement

| | Count |
|---|---|
| Our resolved call edges | 291 |
| Jelly's edges | 79 |
| In both | 62 |
| Our edges also in Jelly ("precision vs Jelly") | 21% |
| Jelly's edges also in ours ("recall vs Jelly") | 79% (was 44% before following `module.exports` re-exports) |

By our confidence label:

| Label | Edges | Also in Jelly |
|---|---|---|
| import | 34 | 97% |
| name-match | 8 | 75% |
| same-file | 80 | 25% |
| qualname | 169 | 2% |

## Why raw agreement understates our precision

Jelly lacks most `this.x()` / `res.x()` method calls: Express builds its `app`, `req` and `res` objects at run time (`Object.create`, `Object.setPrototypeOf`), and Jelly loses track of which methods they carry. So "not in Jelly" mostly means "Jelly couldn't see it", not "wrong".

**Hand check (random sample of 25 of our 229 edges not in Jelly, seed 5): 24 correct, 1 wrong.**
The wrong one: `this.get('env')` in `app.handle` linked to an unrelated getter named `get` in the same file (a same-file short-name collision).

**All 44 Jelly edges we missed (before the re-export fix) were real.** Groups: re-exported functions (`var express = require('../../'); express()`, ~29, now fixed), callbacks passed as arguments (~12), an immediately-invoked function (1), dispatch through an object (2). 17 remain missed, all callbacks or dynamic dispatch.

## Estimate

Counting the 62 shared edges as correct and the sampled 96% for the rest: about **97% of our edges are correct** (~282 of 291). Of the real edges found by either tool (~299), we find about **94%**, Jelly about **26%**.

Caveat: this is measured against the union of two static tools plus a hand sample. Calls neither tool can see (methods defined in loops such as `app[method] = ...`, which is how Express defines `app.get`) are outside both, so true recall is lower. A dynamic call graph from running Express's test suite would be the next level of evidence.

## Effect on the agent

Jelly's extra edges are stored (`extra_edges` table) and shown by the agent's `graph_neighbors` tool, labelled "found by Jelly". Only 2 of 172 eval questions have an answer touching one of the 17 Jelly-only edges; re-running both gave identical scores. On Express, Jelly's value is measurement, not accuracy.
