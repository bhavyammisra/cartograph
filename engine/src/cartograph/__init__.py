import argparse
import os
import time
from importlib.metadata import version
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="cartograph", description="Map and search a JS codebase.")
    parser.add_argument("--version", action="version", version=f"cartograph {version('cartograph')}")
    sub = parser.add_subparsers(dest="command")
    idx = sub.add_parser("index", help="parse a repository into the database")
    idx.add_argument("path", type=Path)
    emb = sub.add_parser("embed", help="add meaning vectors for an indexed repository")
    emb.add_argument("path", type=Path)
    emb.add_argument("--model", choices=["coderank", "jina"], default="coderank")
    mine_p = sub.add_parser("mine", help="build eval questions from issues and fix commits")
    mine_p.add_argument("repo", type=Path)
    mine_p.add_argument("--github", required=True, help="owner/name, e.g. expressjs/express")
    mine_p.add_argument("--prefix", default="lib/", help="only count functions under this path")
    mine_p.add_argument("--out", type=Path, required=True)
    ev = sub.add_parser("eval", help="score a retriever on a question set")
    ev.add_argument("repo", type=Path, help="repo folder that was indexed")
    ev.add_argument("--questions", type=Path, required=True)
    ev.add_argument("--retriever", choices=["bm25", "dense", "hybrid"], default="bm25")
    ev.add_argument("--model", choices=["coderank", "jina"], default="coderank",
                    help="embedding model for dense/hybrid")
    ev.add_argument("--out", type=Path, help="results folder (default: next to the questions)")
    args = parser.parse_args(argv)

    def connect():
        import psycopg

        from .store import DEFAULT_DB

        try:
            return psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DB), autocommit=True)
        except psycopg.OperationalError as e:
            parser.exit(1, f"Can't reach Postgres ({e}).\nIs it running? Try: docker compose up -d\n")

    if args.command == "eval":
        import json

        from .evaluate import evaluate, report
        from .search import BM25, Dense, Hybrid, load_corpus

        questions = [json.loads(line) for line in args.questions.read_text(encoding="utf-8")
                     .splitlines() if line.strip()]
        root = args.repo.resolve().as_posix()
        with connect() as conn:
            docs = load_corpus(conn, root)
            if args.retriever == "bm25":
                retriever, name = BM25(docs), "bm25"
            else:
                dense = Dense(conn, root, args.model)
                retriever = dense if args.retriever == "dense" else Hybrid(BM25(docs), dense)
                name = f"{args.retriever}-{args.model}"
            rows = evaluate(questions, docs, retriever)
        report(rows, f"{args.questions.stem}-{name}", args.out or args.questions.parent / "results")
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
