from collections import Counter, defaultdict

from cartograph.cochange import add_pairs, score, validate


def test_pairs_and_score():
    counts = defaultdict(Counter)
    add_pairs(counts, [1, 2])
    add_pairs(counts, [1, 2, 3])
    assert counts[1][2] == 2 and counts[3][1] == 1
    s = score([2, 9], {2, 3})
    assert (s["precision"], s["recall"], s["size"]) == (0.5, 0.5, 2)
    assert score([], {2})["precision"] is None


def test_each_commit_is_predicted_from_older_commits_only():
    def commit(t, *names):
        return {"time": t, "changed": [["a.js", n] for n in names]}

    # The first commit only teaches (warm-up); the second must be predicted from the first.
    commits = [commit(2, "f", "g"), commit(1, "f", "g")]  # out of order on purpose
    ids = {("a.js", "f"): 1, ("a.js", "g"): 2, ("a.js", "h"): 3}
    callers_of = {1: {3}}  # h calls f, but h never changes with it
    place = {1: ("a.js", 10), 2: ("a.js", 50), 3: ("a.js", 20)}
    report = validate(commits, ids, callers_of, place, warm_up=0.5)
    assert report["commits"] == {"with_2_plus_functions": 2, "warm_up": 1, "tested": 1,
                                 "tested_from": 2}
    m = report["methods"]
    assert m["co-change history"]["recall"] == 1.0 and m["co-change history"]["precision"] == 1.0
    assert m["call graph"]["recall"] == 0.0  # seed f predicts h, seed g predicts nothing
    assert m["call graph"]["predicts_something"] == 0.5
    # Baseline for seed f ranks h (line 20) before g (line 50).
    assert m["same file (baseline)"]["recall"] == 1.0 and m["same file (baseline)"]["precision"] == 0.5


def test_history_does_not_see_the_commit_it_predicts():
    commits = [{"time": 1, "changed": [["a.js", "f"], ["a.js", "g"]]}]
    ids = {("a.js", "f"): 1, ("a.js", "g"): 2}
    report = validate(commits, ids, {}, {1: ("a.js", 1), 2: ("a.js", 9)}, warm_up=0)
    assert report["methods"]["co-change history"]["recall"] == 0.0
