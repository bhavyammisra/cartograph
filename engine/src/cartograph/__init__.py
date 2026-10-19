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
    args = parser.parse_args(argv)

    if args.command == "index":
        import psycopg

        from .store import DEFAULT_DB, index_repo

        if not args.path.is_dir():
            parser.error(f"not a folder: {args.path}")
        url = os.environ.get("DATABASE_URL", DEFAULT_DB)
        try:
            conn = psycopg.connect(url, autocommit=True)
        except psycopg.OperationalError as e:
            parser.exit(1, f"Can't reach Postgres ({e}).\nIs it running? Try: docker compose up -d\n")
        start = time.perf_counter()
        with conn:
            stats = index_repo(conn, args.path)
        for key, value in stats.items():
            print(f"{key:>20}  {value}")
        print(f"{'seconds':>20}  {time.perf_counter() - start:.2f}")
    else:
        parser.print_help()
