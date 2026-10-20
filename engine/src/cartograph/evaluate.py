"""Score a retriever on a question set: Acc@k, Recall@10, MRR, file-level Acc@5, latency."""

import json
import re
import statistics
import time
from collections.abc import Callable
from pathlib import Path

from .search import Doc

KS = (1, 5, 10)


def score_one(ranked: list[int], gold: set[int], file_of: dict[int, str]) -> dict[str, float]:
    """Metrics for one question. `ranked` = function ids best-first, `gold` = correct ids."""
    first = next((i for i, fid in enumerate(ranked) if fid in gold), None)
    out = {f"acc@{k}": float(first is not None and first < k) for k in KS}
    out["recall@10"] = len(gold & set(ranked[:10])) / len(gold)
    out["mrr"] = 1 / (first + 1) if first is not None else 0.0
    gold_files = {file_of[g] for g in gold}
    files = list(dict.fromkeys(file_of[f] for f in ranked))  # file order of first appearance
    out["file_acc@5"] = float(bool(gold_files & set(files[:5])))
    return out


def names_answer(text: str, gold: list[dict]) -> bool:
    """Does the question already name an answer function? Lets us report easy vs hard."""
    names = {g["qualname"].rsplit(".", 1)[-1] for g in gold}
    return any(re.search(rf"\b{re.escape(n)}\b", text) for n in names)


def gold_ids(question: dict, docs: list[Doc]) -> set[int]:
    wanted = {(g["path"], g["qualname"]) for g in question["gold"]}
    return {d.id for d in docs if (d.path, d.qualname) in wanted}


def evaluate(questions: list[dict], docs: list[Doc], retriever: Callable[[str], list[int]],
             checkpoint: Path | None = None):
    """Score every question. With `checkpoint`, each finished row is appended to that file and
    rows already in it are reused, so an interrupted multi-hour agent run resumes."""
    file_of = {d.id: d.path for d in docs}
    done = {}
    if checkpoint and checkpoint.exists():
        done = {r["id"]: r for r in map(json.loads, checkpoint.read_text(encoding="utf-8")
                                         .splitlines()) if r}
    rows = []
    for q in questions:
        gold = gold_ids(q, docs)
        if not gold:
            continue  # gold function missing from the corpus (e.g. index out of date)
        if q["id"] in done:
            rows.append(done[q["id"]])
            continue
        start = time.perf_counter()
        ranked = retriever(q["question"])
        ms = (time.perf_counter() - start) * 1000
        row = {"id": q["id"], "source": q["source"], "type": q["type"],
               "names_answer": names_answer(q["question"], q["gold"]), "ms": ms,
               "top5": ranked[:5], **score_one(ranked, gold, file_of)}
        if extra := getattr(retriever, "last_extra", None):  # agents: score the answer itself
            row |= {"acc@answer": float(bool(gold & set(extra["answer"]))),
                    "steps": extra["steps"], "tokens": extra["tokens"],
                    "answer": extra["answer"], "events": extra["events"]}
        rows.append(row)
        if checkpoint:
            with checkpoint.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(row) + "\n")
        print(f"  {len(rows)}/{len(questions)} {q['id']}: acc@5={row['acc@5']:.0f} "
              f"{ms / 1000:.1f}s", flush=True)
    return rows


def summarize(rows: list[dict]) -> dict[str, float]:
    if not rows:
        return {"n": 0}
    metrics = [k for k in rows[0]
               if k.startswith(("acc", "recall", "mrr", "file")) or k in ("steps", "tokens")]
    out = {"n": len(rows)} | {m: round(statistics.mean(r[m] for r in rows), 3) for m in metrics}
    ms = sorted(r["ms"] for r in rows)
    out["p50_ms"] = round(ms[len(ms) // 2], 1)
    out["p95_ms"] = round(ms[min(len(ms) - 1, int(len(ms) * 0.95))], 1)
    return out


def report(rows: list[dict], name: str, out_dir: Path) -> None:
    groups = {"all": rows}
    for key in ("source", "type"):
        for value in sorted({r[key] for r in rows}):
            groups[f"{key}={value}"] = [r for r in rows if r[key] == value]
    groups["answer not named"] = [r for r in rows if not r["names_answer"]]
    summary = {g: summarize(rs) for g, rs in groups.items()}
    cols = ["n", "acc@1", "acc@5", "acc@10", "recall@10", "mrr", "file_acc@5", "p50_ms"]
    if "acc@answer" in rows[0]:
        cols += ["acc@answer", "steps", "tokens"]
    print(f"\n{name}\n{'group':<26}" + "".join(f"{c:>11}" for c in cols))
    for g, s in summary.items():
        print(f"{g:<26}" + "".join(f"{s.get(c, '-'):>11}" for c in cols))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}.json").write_text(
        json.dumps({"summary": summary, "questions": rows}, indent=1), encoding="utf-8",
        newline="\n")
