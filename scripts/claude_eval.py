"""Measure Cartograph as an MCP server for Claude Code: the same questions, answered by Claude Code
with only its file tools (Read, Grep, Glob) and with those plus Cartograph's tools.

No shell (no `git log` to find the fix commit) and no web, in both runs. Each answer is scored
against the gold functions of the mined questions; tokens, turns and time come from Claude Code's
JSON output. Checkpointed: re-running skips finished (question, condition) pairs.

    uv run --project engine python scripts/claude_eval.py --repo targets/express \
        --questions eval/express/mined.jsonl --sample 20 --model sonnet
"""

import argparse
import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parents[1] / "engine" / "src"))
from cartograph.api import SCOPE
from cartograph.store import DEFAULT_DB

ENGINE = Path(__file__).parents[1] / "engine"
PROMPT = """A user reported this about the code in the current directory:

<report>
{question}
</report>

Find the function(s) in this repository's source that would have to change to fix or implement it.
End your reply with up to 5 lines, best first, each exactly `path:line` (the line where the function \
starts, path relative to the repository root), and nothing after them."""


def run(question: str, repo: Path, with_cartograph: bool, model: str, cfg: Path) -> dict:
    tools = ["Read", "Grep", "Glob"]
    cmd = ["claude", "-p", PROMPT.format(question=question), "--output-format", "json",
           "--model", model, "--no-session-persistence", "--setting-sources", "project",
           "--strict-mcp-config", "--tools", ",".join(tools)]
    allowed = tools + (["mcp__cartograph"] if with_cartograph else [])
    if with_cartograph:
        cmd += ["--mcp-config", str(cfg)]
    cmd += ["--allowedTools", *allowed]
    start = time.perf_counter()
    out = subprocess.run(cmd, cwd=repo, capture_output=True, check=False, encoding="utf-8", errors="replace",
                         timeout=900)
    seconds = time.perf_counter() - start
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"error": (out.stderr or out.stdout)[-500:], "seconds": seconds}
    if data.get("is_error"):  # e.g. not signed in: not an answer, so don't score it
        return {"error": str(data.get("result"))[-500:], "seconds": seconds}
    return {"result": data.get("result", ""), "usage": data.get("usage", {}),
            "cost_usd": data.get("total_cost_usd"), "turns": data.get("num_turns"),
            "is_error": data.get("is_error"), "seconds": round(seconds, 1)}


def located(text: str, functions: list[tuple[str, str, int, int]]) -> list[tuple[str, str]]:
    """`path:line` answers -> (path, qualname) of the innermost function at that line, in order."""
    out = []
    for path, line in re.findall(r"([\w./-]+\.[cm]?[jt]sx?):(\d+)", text):
        path, line = path.removeprefix("./"), int(line)
        inside = [f for f in functions if f[0] == path and f[2] <= line <= f[3]]
        best = min(inside, key=lambda f: f[3] - f[2], default=None)
        if best and (best[0], best[1]) not in out:
            out.append((best[0], best[1]))
    return out[:5]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--questions", type=Path, required=True)
    p.add_argument("--sample", type=int, default=20)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--model", default="sonnet")
    p.add_argument("--out", type=Path, default=Path("eval/express/results/claude-code-mcp.jsonl"))
    a = p.parse_args()

    repo = a.repo.resolve()
    questions = [q for q in map(json.loads, a.questions.read_text(encoding="utf-8").splitlines())
                 if q.get("source") == "issue"]  # issue text: written by users, not by the fixer
    questions = random.Random(a.seed).sample(sorted(questions, key=lambda q: q["id"]), a.sample)
    cfg = a.out.with_suffix(".mcp.json")
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({"mcpServers": {"cartograph": {
        "command": "uv", "args": ["run", "--project", str(ENGINE), "--directory",
                                  str(Path.cwd()), "cartograph", "mcp", repo.as_posix()]}}}))
    with psycopg.connect(DEFAULT_DB) as conn:
        functions = conn.execute(f"SELECT f.path, fn.qualname, fn.start_line, fn.end_line "
                                 f"FROM functions fn {SCOPE} AND fn.kind <> 'module'",
                                 (repo.as_posix(),)).fetchall()

    done = set()
    if a.out.exists():
        done = {(r["id"], r["cartograph"]) for r in map(json.loads, a.out.read_text().splitlines())}
    for q in questions:
        gold = {(g["path"], g["qualname"]) for g in q["gold"]}
        for with_cartograph in (False, True):
            if (q["id"], with_cartograph) in done:
                continue
            r = run(q["question"], repo, with_cartograph, a.model, cfg)
            if "error" in r:
                sys.exit(f"{q['id']}: Claude Code failed, nothing recorded: {r['error']}")
            answer = located(r.get("result", ""), functions)
            row = {"id": q["id"], "cartograph": with_cartograph, "model": a.model,
                   "answer": answer, "hit@1": bool(answer[:1] and answer[0] in gold),
                   "hit@5": any(f in gold for f in answer),
                   "file@5": any(f[0] in {g[0] for g in gold} for f in answer), **r}
            with a.out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            print(f"{q['id']} {'cartograph' if with_cartograph else 'baseline  '} "
                  f"hit@1={row['hit@1']} hit@5={row['hit@5']} turns={r.get('turns')} "
                  f"{r.get('seconds')} s {r.get('error', '')[:200]}", flush=True)


if __name__ == "__main__":
    main()
