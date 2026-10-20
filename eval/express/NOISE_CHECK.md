# Noise check: mined Express questions

20 questions sampled at random (seed 20) from the 74 issue-sourced questions in `mined.jsonl`. For each: issue title, fix commit subject, and gold functions, judged by hand (20 October 2026).

**Result: 18 clean, 2 noisy (10%).**

| Question | Verdict | Note |
|---|---|---|
| express-1826 | clean | |
| express-2546 | clean | |
| express-1619 | clean | |
| express-2897 | clean | `text` is a nested callback inside `res.redirect` |
| express-2116 | **noisy** | Fix also changed `app.listen` and `app.init`, unrelated to the HEAD-method bug |
| express-1154 | clean | |
| express-4834 | clean | |
| express-808 | clean | |
| express-1382 | clean | |
| express-1623 | clean | includes a revert commit; gold still `res.send` |
| express-1744 | clean | |
| express-2104 | clean | |
| express-2467 | clean | |
| express-6391 | clean | |
| express-2668 | clean | bug reported on `app.render`, fixed in `View.prototype.render` (a good hard case) |
| express-2356 | clean | |
| express-2284 | clean | |
| express-731 | clean | |
| express-887 | **noisy** | vague feature request; weak link to `app.defaultConfiguration` |
| express-6896 | clean | refactor request, gold correct |

Known limit: gold is checked against today's code, not the code before each fix (see `engine/src/cartograph/mine.py`).
