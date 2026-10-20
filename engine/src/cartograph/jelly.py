"""Run Jelly (a research-grade JavaScript static analyzer) and compare its call graph with ours.

Jelly tracks values (where functions flow), so it resolves calls tree-sitter can't. It is not
perfect truth either, so results read as "agreement with Jelly", not absolute accuracy.
"""

import json
import subprocess
from collections import defaultdict
from pathlib import Path

import psycopg

JELLY = "@cs-au-dk/jelly@0.13.0"
# Only ordinary function calls, comparable to what tree-sitter sees. No --approx: approximate
# interpretation executes the analyzed code, which a code-search tool must never do.
FLAGS = ["--ignore-unresolved", "--no-callgraph-require", "--no-callgraph-native",
         "--no-callgraph-external", "--no-callgraph-implicit", "--no-tty", "--no-print-progress",
         "-l", "error"]


def run_jelly(root: Path, entries: list[str], out: Path) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["npx", "--yes", JELLY, "-b", str(root), "-j", str(out), *FLAGS,
                    *[str(root / e) for e in entries]],
                   check=True, capture_output=True, shell=True)  # shell: npx is a .cmd on Windows
    return json.loads(out.read_text(encoding="utf-8"))


def jelly_edges(cg: dict, functions: dict[tuple[str, int, int], int],
                modules: dict[str, int]) -> tuple[set, int]:
    """Jelly's function->function edges mapped onto our function ids.

    Jelly locates a function as "file:startLine:startCol:endLine:endCol"; ours by file + line
    range, so (path, start_line, end_line) joins them. A file's top-level code is a function
    starting at 1:1 in Jelly and a `module` row for us. Returns (edges, unmatched functions)."""
    files = [f.replace("\\", "/") for f in cg["files"]]
    ours, unmatched = {}, 0
    for jid, loc in cg["functions"].items():
        f, sl, sc, el, _ = (int(x) for x in loc.split(":"))
        if "node_modules/" in files[f]:
            continue
        fid = modules.get(files[f]) if (sl, sc) == (1, 1) else None
        if fid is None:
            fid = functions.get((files[f], sl, el))
        if fid is not None:
            ours[int(jid)] = fid
        else:
            unmatched += 1
    return {(ours[a], ours[b]) for a, b in cg["fun2fun"] if a in ours and b in ours}, unmatched


def compare(conn: psycopg.Connection, root: Path, entries: list[str], cache: Path) -> dict:
    root_s = root.resolve().as_posix()
    cg = run_jelly(root.resolve(), entries, cache)
    rows = conn.execute(
        """SELECT fn.id, f.path, fn.start_line, fn.end_line, fn.kind FROM functions fn
           JOIN files f ON f.id = fn.file_id JOIN repos r ON r.id = f.repo_id
           WHERE r.root = %s AND NOT f.is_test""", (root_s,)).fetchall()
    functions = {(p, s, e): i for i, p, s, e, k in rows if k != "module"}
    modules = {p: i for i, p, s, e, k in rows if k == "module"}
    theirs, unmatched = jelly_edges(cg, functions, modules)
    labels = defaultdict(set)  # our resolved edges, by how sure we were
    for caller, callee, label in conn.execute(
            """SELECT DISTINCT c.caller_id, c.callee_id, c.resolution FROM calls c
               JOIN functions fn ON fn.id = c.caller_id JOIN files f ON f.id = fn.file_id
               JOIN repos r ON r.id = f.repo_id
               WHERE r.root = %s AND NOT f.is_test AND c.callee_id IS NOT NULL""", (root_s,)):
        labels[label].add((caller, callee))
    ours = set().union(*labels.values())
    both = ours & theirs
    report = {
        "jelly_functions_unmatched": unmatched,
        "our_edges": len(ours), "jelly_edges": len(theirs), "agree": len(both),
        "precision": round(len(both) / len(ours), 3) if ours else None,
        "recall": round(len(both) / len(theirs), 3) if theirs else None,
        "by_label": {k: {"edges": len(v), "also_in_jelly": len(v & theirs),
                         "precision": round(len(v & theirs) / len(v), 3)}
                     for k, v in sorted(labels.items())},
    }
    return report | {"_ours": ours, "_theirs": theirs}


def store_edges(conn: psycopg.Connection, root: Path, edges: set[tuple[int, int]]) -> None:
    """Replace this repo's Jelly edges with `edges` (our function ids)."""
    with conn.transaction():
        conn.execute("""DELETE FROM extra_edges e USING functions fn, files f, repos r
                        WHERE e.caller_id = fn.id AND fn.file_id = f.id AND f.repo_id = r.id
                        AND r.root = %s AND e.source = 'jelly'""", (root.resolve().as_posix(),))
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO extra_edges (caller_id, callee_id, source) "
                            "VALUES (%s, %s, 'jelly')", sorted(edges))
