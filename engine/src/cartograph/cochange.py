"""Check impact analysis against history: when a commit changed function f, did each method
predict the other functions that same commit had to change?

Each commit is predicted from older commits only, so nothing is learned from the answers. Methods: call graph (reverse walk), co-change history, both, and a same-file baseline.

shortcut: the call graph is today's (HEAD), not the graph at each test commit; build per-commit
graphs if the call-graph numbers need to be exact.
"""

import json
import subprocess
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from .graph import impact
from .mine import changed_functions, git

MAX_CHANGED = 30  # bigger commits are mass refactors/renames: they say nothing about coupling


def history_cache(repo: Path) -> Path:
    return Path(".cache/cochange") / f"{repo.resolve().name}.json"


def history(repo: Path, prefix: str, cache: Path) -> list[dict]:
    """Every non-merge commit touching `prefix`, oldest first, with the functions it changed."""
    done = {c["sha"]: c for c in json.loads(cache.read_text())} if cache.exists() else {}
    log = git(repo, "log", "--no-merges", "--reverse", "--format=%H %ct", "--", prefix).split("\n")
    commits = []
    for line in filter(None, log):
        sha, ts = line.split()
        if sha not in done:
            try:
                changed = sorted(map(list, changed_functions(repo, sha, prefix)))
            except subprocess.CalledProcessError:
                changed = []  # the root commit: no parent to compare with
            done[sha] = {"sha": sha, "time": int(ts), "changed": changed}
        commits.append(done[sha])
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(commits))
    return commits


def add_pairs(counts: dict[int, Counter], ids: list[int]) -> None:
    """Record that these functions changed together in one commit."""
    for a, b in combinations(ids, 2):
        counts[a][b] += 1
        counts[b][a] += 1


def usable(commits: list[dict], ids: dict[tuple[str, str], int]) -> list[tuple[dict, list[int]]]:
    """Oldest first: commits with today's ids of the 2 to MAX_CHANGED functions they changed.
    Only functions that still exist today can be shown or checked against today's graph."""
    out = []
    for c in sorted(commits, key=lambda c: c["time"]):
        found = sorted({ids[(p, q)] for p, q in c["changed"] if (p, q) in ids})
        if 2 <= len(found) <= MAX_CHANGED:
            out.append((c, found))
    return out


def changed_together(commits: list[dict], ids: dict[tuple[str, str], int]) -> dict[int, Counter]:
    """For the website: for each function, the functions that changed with it, and how often."""
    counts: dict[int, Counter] = defaultdict(Counter)
    for _, found in usable(commits, ids):
        add_pairs(counts, found)
    return counts


def score(ranked: list[int], truth: set[int]) -> dict:
    """Set precision/recall of the whole prediction, and recall of its top 5 and top 10."""
    hit = len(set(ranked) & truth)
    return {"precision": hit / len(ranked) if ranked else None, "recall": hit / len(truth),
            "recall@5": len(set(ranked[:5]) & truth) / len(truth),
            "recall@10": len(set(ranked[:10]) & truth) / len(truth), "size": len(ranked)}


def validate(commits: list[dict], ids: dict[tuple[str, str], int], callers_of: dict[int, set[int]],
             place: dict[int, tuple[str, int]], warm_up: float = 0.2, depth: int = 3) -> dict:
    """Rolling check: each commit is predicted from the commits before it only. The first
    `warm_up` share only teaches. place: function id -> (file, start line)."""
    kept = usable(commits, ids)
    in_file = defaultdict(list)
    for fid, (path, _) in place.items():
        in_file[path].append(fid)

    def call_graph(f):
        dist = impact(callers_of, f, depth)
        return sorted(dist, key=lambda g: (dist[g], g))

    def history_(f):
        return [g for g, _ in counts[f].most_common()] if f in counts else []

    def nearby(f):  # baseline: the rest of the file, closest lines first
        path, line = place[f]
        return sorted((g for g in in_file[path] if g != f), key=lambda g: abs(place[g][1] - line))

    methods = {
        "call graph": call_graph,
        "co-change history": history_,
        "both": lambda f: list(dict.fromkeys(history_(f) + call_graph(f))),
        "same file (baseline)": nearby,
    }
    counts: dict[int, Counter] = defaultdict(Counter)
    rows = {m: defaultdict(list) for m in methods}
    warm, seeds = int(len(kept) * warm_up), 0
    for i, (_, found) in enumerate(kept):
        if i >= warm:
            for f in found:  # each changed function takes a turn as "the one being edited"
                seeds += 1
                for m, predict in methods.items():
                    for k, v in score(predict(f), set(found) - {f}).items():
                        if v is not None:
                            rows[m][k].append(v)
        add_pairs(counts, found)  # only now does history learn this commit

    def mean(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    return {
        "commits": {"with_2_plus_functions": len(kept), "warm_up": warm,
                    "tested": len(kept) - warm,
                    "tested_from": kept[warm][0]["time"] if warm < len(kept) else None},
        "seeds": seeds,
        "depth": depth,
        "methods": {m: {"recall@5": mean(v["recall@5"]), "recall@10": mean(v["recall@10"]),
                        "recall": mean(v["recall"]), "precision": mean(v["precision"]),
                        "predicts_something": round(len(v["precision"]) / seeds, 3) if seeds else None,
                        "mean_size": mean(v["size"])}
                    for m, v in rows.items()},
    }
