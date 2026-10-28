import argparse
import os
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any


def load_dotenv(path: Path = Path(__file__).parents[3] / ".env") -> None:
    """Read KEY=value lines from the repo's .env into the environment (never overrides)."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and not key.strip().startswith("#"):
                os.environ.setdefault(key.strip(), value.strip())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="cartograph", description="Map and search a JS codebase.")
    parser.add_argument("--version", action="version", version=f"cartograph {version('cartograph')}")
    sub = parser.add_subparsers(dest="command")
    idx = sub.add_parser("index", help="parse a repository into the database")
    idx.add_argument("path", type=Path)
    emb = sub.add_parser("embed", help="add meaning vectors for an indexed repository")
    emb.add_argument("path", type=Path)
    emb.add_argument("--model", choices=["coderank", "jina"], default="coderank")
    jel = sub.add_parser("jelly", help="run Jelly, compare call graphs, store Jelly's edges")
    jel.add_argument("path", type=Path)
    jel.add_argument("--entries", nargs="+", required=True,
                     help="files/folders to analyze, relative to the repo, e.g. lib examples")
    jel.add_argument("--out", type=Path, help="save the comparison report as JSON")
    mine_p = sub.add_parser("mine", help="build eval questions from issues and fix commits")
    mine_p.add_argument("repo", type=Path)
    mine_p.add_argument("--github", required=True, help="owner/name, e.g. expressjs/express")
    mine_p.add_argument("--prefix", default="lib/", help="only count functions under this path")
    mine_p.add_argument("--out", type=Path, required=True)
    ev = sub.add_parser("eval", help="score a retriever on a question set")
    ev.add_argument("repo", type=Path, help="repo folder that was indexed")
    ev.add_argument("--questions", type=Path, required=True)
    ev.add_argument("--retriever", default="bm25",
                    choices=["bm25", "dense", "hybrid", "agent", "grep-agent"])
    ev.add_argument("--model", choices=["coderank", "jina"], default="coderank",
                    help="embedding model for dense/hybrid")
    ev.add_argument("--llm", default="qwen3-4b", help="LLM for agents (see agent.LLMS)")
    ev.add_argument("--limit", type=int, help="only the first N questions (quick checks)")
    ev.add_argument("--out", type=Path, help="results folder (default: next to the questions)")
    srv = sub.add_parser("serve", help="run the API server for the map website")
    srv.add_argument("repo", type=Path)
    srv.add_argument("--port", type=int, default=8000)
    srv.add_argument("--host", default="127.0.0.1",
                     help="0.0.0.0 only inside a container: the API serves your source code")
    srv.add_argument("--llm", default="qwen3-4b")
    imp = sub.add_parser("impact-eval", help="check impact analysis against git co-change")
    imp.add_argument("repo", type=Path, help="indexed repo (a git checkout)")
    imp.add_argument("--prefix", default="lib/", help="only count functions under this path")
    imp.add_argument("--depth", type=int, default=3, help="call-graph hops to walk")
    imp.add_argument("--out", type=Path, help="save the report as JSON")
    order_p = sub.add_parser("order", help="is X always called before Y? (with a counterexample)")
    order_p.add_argument("repo", type=Path)
    order_p.add_argument("x", help="function full name (res.status) or called name (this.end)")
    order_p.add_argument("y")
    order_p.add_argument("--start", help="function to start from (default: every entry point)")
    order_ev = sub.add_parser("order-eval", help="score the ordering engine on a question set")
    order_ev.add_argument("repo", type=Path)
    order_ev.add_argument("--questions", type=Path, required=True)
    order_ev.add_argument("--out", type=Path, help="save the results as JSON")
    mcp_p = sub.add_parser("mcp", help="run the MCP server (stdio) for Claude Code and other agents")
    mcp_p.add_argument("repo", type=Path)
    ask = sub.add_parser("ask", help="ask one question and print every agent step")
    ask.add_argument("repo", type=Path)
    ask.add_argument("question")
    ask.add_argument("--llm", default="qwen3-4b")
    ask.add_argument("--grep", action="store_true", help="use the grep-only baseline agent")
    args = parser.parse_args(argv)
    load_dotenv()

    def connect():
        import psycopg

        from .store import DEFAULT_DB, SCHEMA

        try:
            conn = psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DB), autocommit=True)
        except psycopg.OperationalError as e:
            parser.exit(1, f"Can't reach Postgres ({e}).\nIs it running? Try: docker compose up -d\n")
        conn.execute(SCHEMA)  # idempotent: adds tables a newer version needs
        return conn

    if args.command == "eval":
        import json

        from .evaluate import evaluate, report
        from .search import BM25, Dense, Hybrid, load_corpus

        questions = [json.loads(line) for line in args.questions.read_text(encoding="utf-8")
                     .splitlines() if line.strip()][:args.limit]
        root = args.repo.resolve().as_posix()
        with connect() as conn:
            docs = load_corpus(conn, root)
            retriever: Any
            if args.retriever == "bm25":
                retriever, name = BM25(docs), "bm25"
            elif args.retriever in ("agent", "grep-agent"):
                from .agent import Agent

                mode = "index" if args.retriever == "agent" else "grep"
                retriever, name = Agent(conn, root, docs, args.llm, mode), f"{args.retriever}-{args.llm}"
            else:
                dense = Dense(conn, root, args.model)
                retriever = dense if args.retriever == "dense" else Hybrid(BM25(docs), dense)
                name = f"{args.retriever}-{args.model}"
            run = f"{args.questions.stem}-{name}" + (f"-first{args.limit}" if args.limit else "")
            out = args.out or args.questions.parent / "results"
            out.mkdir(parents=True, exist_ok=True)
            checkpoint = out / f"{run}.partial.jsonl"  # resume point if the run is interrupted
            rows = evaluate(questions, docs, retriever, checkpoint)
        report(rows, run, out)
        checkpoint.unlink(missing_ok=True)
    elif args.command == "ask":
        from .agent import Agent
        from .search import load_corpus

        root = args.repo.resolve().as_posix()
        with connect() as conn:
            docs = load_corpus(conn, root)
            agent = Agent(conn, root, docs, args.llm, "grep" if args.grep else "index")
            start = time.perf_counter()
            ranked = agent(args.question)
            for e in agent.last_extra["events"]:
                detail = e.get("args") if e["type"] != "text" else e["text"]
                print(f"step {e['step']} {e.get('tool', e['type'])} {detail}  "
                      f"-> {len(e.get('ids', []))} functions  ({e.get('ms', 0)} ms)")
            print("\nanswer:" if agent.last_extra["answer"] else "\nno answer submitted; best seen:")
            for fid in (agent.last_extra["answer"] or ranked[:3]):
                print("  ", agent.label(fid))
            print(f"\n{agent.last_extra['tokens']} tokens, {time.perf_counter() - start:.1f} s")
    elif args.command == "serve":
        import uvicorn

        from .api import create_app
        from .store import DEFAULT_DB

        connect().close()  # fail early with the friendly message if Postgres is down
        import json

        from .cochange import history_cache

        cache = history_cache(args.repo)  # written by `cartograph impact-eval`
        app = create_app(args.repo.resolve().as_posix(),
                         os.environ.get("DATABASE_URL", DEFAULT_DB), args.llm,
                         json.loads(cache.read_text()) if cache.exists() else None)
        print(f"Cartograph API on http://{args.host}:{args.port}  (docs: /docs)")
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    elif args.command == "mcp":
        import json

        from .cochange import history_cache
        from .mcp_server import build
        from .store import DEFAULT_DB

        connect().close()  # fail early with the friendly message if Postgres is down
        cache = history_cache(args.repo)
        build(args.repo.resolve().as_posix(), os.environ.get("DATABASE_URL", DEFAULT_DB),
              json.loads(cache.read_text()) if cache.exists() else None).run("stdio")
    elif args.command == "impact-eval":
        import json
        from collections import defaultdict

        from .api import call_edges, function_places
        from .cochange import history, history_cache, validate

        root = args.repo.resolve().as_posix()
        commits = history(args.repo, args.prefix, history_cache(args.repo))
        with connect() as conn:
            ids, place = function_places(conn, root)
            callers_of = defaultdict(set)
            for e in call_edges(conn, root):
                callers_of[e.target].add(e.source)
        checked = validate(commits, ids, callers_of, place, depth=args.depth)
        print(json.dumps(checked, indent=1))
        if args.out:
            args.out.write_text(json.dumps(checked, indent=1) + "\n", encoding="utf-8")
    elif args.command in ("order", "order-eval"):
        import json

        from .order import Order

        with connect() as conn:
            order = Order.load(conn, args.repo.resolve().as_posix())
        by_name: dict[str, list[int]] = {}
        for fid, name in order.names.items():
            by_name.setdefault(name, []).append(fid)

        def starts(name):
            if name is None:
                return order.entries()
            if len(by_name.get(name, [])) != 1:
                parser.exit(1, f"{name!r} names {len(by_name.get(name, []))} functions; need exactly 1\n")
            return by_name[name]

        if args.command == "order":
            print(json.dumps(order.ask(args.x, args.y, starts(args.start)), indent=1))
        else:
            rows = []
            for q in map(json.loads, filter(str.strip, args.questions.read_text(encoding="utf-8").splitlines())):
                within = starts(q["start"])
                got = order.ask(q["x"], q["y"], within)
                naive = [order.naive(q["x"], q["y"], f) for f in within]
                # Baseline over many starts: "not always" if any start says so; unreachable if all do.
                base = ("not always" if "not always" in naive else
                        "always" if "always" in naive else "unreachable")
                rows.append({"id": q["id"], "level": q["level"], "gold": q["answer"],
                             "cartograph": got["answer"], "naive": base,
                             "counterexample": next(iter(got["counterexamples"].items()), None)})
                mark = "ok " if got["answer"] == q["answer"] else "XX "
                print(f"{mark}{q['id']} L{q['level']} gold={q['answer']:<11} got={got['answer']:<11} "
                      f"naive={base:<11} {q['question']}")
            summary = {}
            for level in ("all", 1, 2, 3):
                part = [r for r in rows if level == "all" or r["level"] == level]
                summary[str(level)] = {"questions": len(part), **{
                    m: round(sum(r[m] == r["gold"] for r in part) / len(part), 3) for m in ("cartograph", "naive")}}
            print(json.dumps(summary, indent=1))
            if args.out:
                args.out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1) + "\n",
                                    encoding="utf-8")
    elif args.command == "jelly":
        import json

        from .jelly import compare, store_edges

        with connect() as conn:
            compared = compare(conn, args.path, args.entries,
                               Path(".cache/jelly") / f"{args.path.resolve().name}.json")
            store_edges(conn, args.path, compared.pop("_theirs"))
            compared.pop("_ours")
        print(json.dumps(compared, indent=1))
        if args.out:
            args.out.write_text(json.dumps(compared, indent=1) + "\n", encoding="utf-8",
                                newline="\n")
    elif args.command == "mine":
        import json

        from .mine import mine

        questions = mine(args.repo, args.github, args.prefix)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("".join(json.dumps(q) + "\n" for q in questions), encoding="utf-8",
                            newline="\n")
        issues = sum(q["source"] == "issue" for q in questions)
        print(f"{len(questions)} questions ({issues} from issues, {len(questions) - issues} "
              f"from PRs) -> {args.out}")
    elif args.command in ("index", "embed"):
        from .store import embed_repo, index_repo

        if not args.path.is_dir():
            parser.error(f"not a folder: {args.path}")
        start = time.perf_counter()
        with connect() as conn:
            if args.command == "index":
                stats: dict[str, object] = dict(index_repo(conn, args.path))
                # Re-parsed functions get new ids and lose their vectors: say so, or meaning
                # search quietly finds nothing.
                missing = conn.execute(
                    """SELECT count(*) FROM functions fn JOIN files f ON f.id = fn.file_id
                       JOIN repos r ON r.id = f.repo_id WHERE r.root = %s AND NOT f.is_test
                       AND fn.kind <> 'module' AND NOT EXISTS (SELECT 1 FROM embeddings e
                       WHERE e.function_id = fn.id)""", (args.path.resolve().as_posix(),)).fetchone()[0]
                if missing:
                    stats["no meaning vector"] = f"{missing} (run: cartograph embed {args.path})"
            else:
                stats = {f"embedded ({args.model})": embed_repo(conn, args.path, args.model)}
        for key, value in stats.items():
            print(f"{key:>20}  {value}")
        print(f"{'seconds':>20}  {time.perf_counter() - start:.2f}")
    else:
        parser.print_help()
