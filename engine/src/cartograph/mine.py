"""Mine evaluation questions from a repo's history: issue text -> functions the fix commit changed.

shortcut: gold answers are checked against today's code (HEAD), not the code before each fix;
rebuild the pre-fix snapshot per question for the headline (Prettier) eval.
"""

import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from .parser import EXTENSIONS, parse

SKIP_SUBJECT = re.compile(r"^(docs|chore|build|ci|test|tests|style|deps|perf)\b|^(bump|upgrade)\b",
                          re.IGNORECASE)
LINKED_ISSUE = re.compile(r"(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s*:?\s+"
                          r"(?:https://github\.com/[\w.-]+/[\w.-]+/issues/|#)(\d+)", re.IGNORECASE)
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+", re.MULTILINE)
CACHE = Path(".cache/github")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True,
                          encoding="utf-8", errors="replace").stdout


def deepest_function(functions, line: int):
    """Smallest named function containing the line (module-level code doesn't count)."""
    inside = [f for f in functions[1:] if f.start_line <= line <= f.end_line]
    return min(inside, key=lambda f: f.end_line - f.start_line, default=None)


def changed_functions(repo: Path, sha: str, prefix: str) -> set[tuple[str, str]]:
    """(path, qualname) of every function whose old body the commit touched, under `prefix`."""
    out = set()
    names = git(repo, "diff", "--name-only", f"{sha}^", sha, "--", prefix).split()
    for path in names:
        ext = Path(path).suffix
        if ext not in EXTENSIONS:
            continue
        try:
            old = git(repo, "show", f"{sha}^:{path}")
        except subprocess.CalledProcessError:
            continue  # file is new in this commit: nothing existed to be found
        functions, _ = parse(old.encode(), EXTENSIONS[ext], path)
        diff = git(repo, "diff", "-U0", f"{sha}^", sha, "--", path)
        for start, count in HUNK.findall(diff):
            start, count = int(start), int(count or 1)
            # count == 0 is a pure insertion after line `start`: blame the code around it
            for line in range(start, start + max(count, 1)):
                f = deepest_function(functions, line)
                if f and f.name != "<anonymous>":
                    out.add((path, f.qualname))
    return out


def github_item(slug: str, number: int) -> dict | None:
    cached = CACHE / slug.replace("/", "__") / f"{number}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    r = subprocess.run(["gh", "api", f"repos/{slug}/issues/{number}"], check=False,
                       capture_output=True,
                       encoding="utf-8", errors="replace")
    item = json.loads(r.stdout) if r.returncode == 0 else None
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(item), encoding="utf-8")
    return item


def question_source(slug: str, number: int) -> tuple[dict, str] | None:
    """(issue, 'issue') if #number is an issue or a PR that links one; (pr, 'pr') otherwise."""
    item = github_item(slug, number)
    if not item:
        return None
    if "pull_request" not in item:
        return item, "issue"
    for linked in LINKED_ISSUE.findall(item.get("body") or ""):
        issue = github_item(slug, int(linked))
        if issue and "pull_request" not in issue:
            return issue, "issue"
    return item, "pr"


def mine(repo: Path, slug: str, prefix: str) -> list[dict]:
    head_files = {}
    for path in git(repo, "ls-files", prefix).split():
        if Path(path).suffix in EXTENSIONS:
            fns, _ = parse((repo / path).read_bytes(), EXTENSIONS[Path(path).suffix], path)
            head_files[path] = {f.qualname for f in fns[1:]}

    log = git(repo, "log", "--no-merges", "--format=%H%x00%s%x00%b%x1e", "--", prefix)
    by_issue: dict[int, dict] = {}
    gold: dict[int, set] = defaultdict(set)
    for entry in filter(str.strip, log.split("\x1e")):
        sha, subject, body = entry.strip().split("\x00")
        if SKIP_SUBJECT.match(subject):
            continue
        for number in dict.fromkeys(int(n) for n in re.findall(r"#(\d+)", subject + " " + body)):
            found = question_source(slug, number)
            if not found:
                continue
            item, kind = found
            changed = changed_functions(repo, sha, prefix)
            if not changed:
                continue
            n = item["number"]
            gold[n] |= changed
            by_issue.setdefault(n, {"item": item, "kind": kind, "commits": []})["commits"].append(sha)
            break

    questions = []
    for n, info in by_issue.items():
        # Keep a question only if every gold function still exists today (see shortcut above).
        if not all(q in head_files.get(p, ()) for p, q in gold[n]) or len(gold[n]) > 5:
            continue
        item = info["item"]
        text = f"{item['title']}\n\n{(item.get('body') or '').strip()}"[:2000]
        questions.append({
            "id": f"{slug.split('/')[1]}-{n}",
            "type": "mined",
            "source": info["kind"],
            "url": item["html_url"],
            "commits": info["commits"],
            "question": text,
            "gold": [{"path": p, "qualname": q} for p, q in sorted(gold[n])],
        })
    return sorted(questions, key=lambda q: q["id"])
