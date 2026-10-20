import argparse
import os
import time
from importlib.metadata import version
from pathlib import Path


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
    elif args.command == "jelly":
        import json

        from .jelly import compare, store_edges

        with connect() as conn:
            report = compare(conn, args.path, args.entries,
                             Path(".cache/jelly") / f"{args.path.resolve().name}.json")
            store_edges(conn, args.path, report.pop("_theirs"))
            report.pop("_ours")
        print(json.dumps(report, indent=1))
        if args.out:
            args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8",
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
                stats = index_repo(conn, args.path)
            else:
                stats = {f"embedded ({args.model})": embed_repo(conn, args.path, args.model)}
        for key, value in stats.items():
            print(f"{key:>20}  {value}")
        print(f"{'seconds':>20}  {time.perf_counter() - start:.2f}")
    else:
        parser.print_help()
