"""Index a repository into Postgres: walk files, parse changed ones, then re-resolve all calls."""

import hashlib
import os
from pathlib import Path

import psycopg

from .parser import EXTENSIONS, PARSER_VERSION, Import, parse
from .resolve import CallRef, FileInfo, resolve

DEFAULT_DB = "postgresql://cartograph:cartograph@localhost:5432/cartograph"
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "coverage", ".next", "vendor"}
TEST_MARKERS = ("/test/", "/tests/", "/__tests__/", ".test.", ".spec.")

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS repos (
  id serial PRIMARY KEY,
  root text UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
  id serial PRIMARY KEY,
  repo_id int NOT NULL REFERENCES repos ON DELETE CASCADE,
  path text NOT NULL,              -- relative to the repo root, forward slashes
  hash text NOT NULL,              -- sha256 of the content, to skip unchanged files
  lang text NOT NULL,
  is_test boolean NOT NULL,
  UNIQUE (repo_id, path)
);
CREATE TABLE IF NOT EXISTS functions (
  id serial PRIMARY KEY,
  file_id int NOT NULL REFERENCES files ON DELETE CASCADE,
  name text NOT NULL,
  qualname text NOT NULL,
  aliases text[] NOT NULL,         -- other assigned names: res.set = res.header = function...
  kind text NOT NULL,              -- tree-sitter node type, or 'module' for top-level code
  start_line int NOT NULL,
  end_line int NOT NULL,
  code text NOT NULL
);
CREATE TABLE IF NOT EXISTS calls (
  id serial PRIMARY KEY,
  caller_id int NOT NULL REFERENCES functions ON DELETE CASCADE,
  seq int NOT NULL,                -- execution order inside the caller
  line int NOT NULL,
  name text,
  receiver text,
  callee_id int REFERENCES functions ON DELETE SET NULL,
  resolution text
);
CREATE TABLE IF NOT EXISTS imports (
  file_id int NOT NULL REFERENCES files ON DELETE CASCADE,
  local text NOT NULL,
  source text NOT NULL,
  imported text
);
-- shortcut: no HNSW index (vector size differs per model, so the column is untyped and search
-- is an exact scan); add a per-model HNSW index once a repo has tens of thousands of functions
CREATE TABLE IF NOT EXISTS embeddings (
  function_id int NOT NULL REFERENCES functions ON DELETE CASCADE,
  model text NOT NULL,
  embedding vector NOT NULL,
  PRIMARY KEY (function_id, model)
);
-- Call edges from other analyzers (Jelly). Function ids change on re-index, so these are
-- dropped with their functions and must be re-imported (cartograph jelly) after indexing.
CREATE TABLE IF NOT EXISTS extra_edges (
  caller_id int NOT NULL REFERENCES functions ON DELETE CASCADE,
  callee_id int NOT NULL REFERENCES functions ON DELETE CASCADE,
  source text NOT NULL,
  PRIMARY KEY (caller_id, callee_id, source)
);
CREATE INDEX IF NOT EXISTS functions_file_idx ON functions (file_id);
ALTER TABLE calls ADD COLUMN IF NOT EXISTS conditional boolean NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS calls_caller_idx ON calls (caller_id);
CREATE INDEX IF NOT EXISTS calls_callee_idx ON calls (callee_id);
"""


def source_files(root: Path):
    """(relative posix path, absolute path, lang) for every JS/TS source file in the repo."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            ext = os.path.splitext(name)[1]
            if ext in EXTENSIONS and not name.endswith((".d.ts", ".min.js")):
                full = Path(dirpath, name)
                yield full.relative_to(root).as_posix(), full, EXTENSIONS[ext]


def clean(s: str) -> str:
    return s.replace("\x00", "")  # Postgres text can't hold NUL bytes


def index_repo(conn: psycopg.Connection, root: Path) -> dict[str, int]:
    root = root.resolve()
    stats = {"files": 0, "parsed": 0, "removed": 0}
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute("INSERT INTO repos (root) VALUES (%s) ON CONFLICT (root) DO UPDATE "
                    "SET root = EXCLUDED.root RETURNING id", (root.as_posix(),))
        repo_id = one(cur)[0]
        cur.execute("SELECT path, hash FROM files WHERE repo_id = %s", (repo_id,))
        known: dict[str, str] = dict(cur.fetchall())

        seen = set()
        for rel, full, lang in source_files(root):
            seen.add(rel)
            stats["files"] += 1
            data = full.read_bytes()
            digest = hashlib.sha256(PARSER_VERSION.encode() + data).hexdigest()
            if known.get(rel) == digest:
                continue
            stats["parsed"] += 1
            cur.execute("DELETE FROM files WHERE repo_id = %s AND path = %s", (repo_id, rel))
            is_test = any(m in f"/{rel}" for m in TEST_MARKERS)
            cur.execute("INSERT INTO files (repo_id, path, hash, lang, is_test) "
                        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                        (repo_id, rel, digest, lang, is_test))
            file_id = one(cur)[0]
            functions, imports = parse(data, lang, rel)
            # Bulk-load with COPY (row-by-row INSERTs took ~10x longer). Reserve ids first so
            # calls can point at their function.
            cur.execute("SELECT nextval(pg_get_serial_sequence('functions', 'id')) "
                        "FROM generate_series(1, %s)", (len(functions),))
            ids = [r[0] for r in cur.fetchall()]
            with cur.copy("COPY functions (id, file_id, name, qualname, aliases, kind, "
                          "start_line, end_line, code) FROM STDIN") as cp:
                for fid, f in zip(ids, functions, strict=True):
                    cp.write_row((fid, file_id, f.name, f.qualname, f.aliases, f.kind,
                                  f.start_line, f.end_line, clean(f.code)))
            with cur.copy("COPY calls (caller_id, seq, line, name, receiver, conditional) FROM STDIN") as cp:
                for fid, f in zip(ids, functions, strict=True):
                    for c in f.calls:
                        cp.write_row((fid, c.seq, c.line, c.name, c.receiver, c.conditional))
            with cur.copy("COPY imports (file_id, local, source, imported) FROM STDIN") as cp:
                for i in imports:
                    cp.write_row((file_id, i.local, i.source, i.imported))

        gone = [p for p in known if p not in seen]
        cur.execute("DELETE FROM files WHERE repo_id = %s AND path = ANY(%s)", (repo_id, gone))
        stats["removed"] = len(gone)

        # Any file change can change what other files' calls point to, so resolve everything again.
        resolve_repo(cur, repo_id)
        cur.execute("""SELECT count(*) FILTER (WHERE kind <> 'module') FROM functions fn
                       JOIN files f ON f.id = fn.file_id WHERE f.repo_id = %s""", (repo_id,))
        stats["functions"] = one(cur)[0]
        cur.execute("""SELECT c.resolution, count(*) FROM calls c
                       JOIN functions fn ON fn.id = c.caller_id JOIN files f ON f.id = fn.file_id
                       WHERE f.repo_id = %s GROUP BY 1""", (repo_id,))
        stats.update({f"calls:{r}": n for r, n in cur.fetchall()})
    return stats


def embed_repo(conn: psycopg.Connection, root: Path, model: str, batch: int = 64) -> int:
    """Embed every searchable function that has no vector for `model` yet. Returns how many."""
    from pgvector.psycopg import register_vector

    from .embed import Embedder

    register_vector(conn)
    rows = conn.execute(
        """SELECT fn.id, f.path, fn.qualname, fn.code FROM functions fn
           JOIN files f ON f.id = fn.file_id JOIN repos r ON r.id = f.repo_id
           WHERE r.root = %s AND NOT f.is_test AND fn.kind <> 'module'
           AND NOT EXISTS (SELECT 1 FROM embeddings e WHERE e.function_id = fn.id
                           AND e.model = %s)""", (root.resolve().as_posix(), model)).fetchall()
    if not rows:
        return 0
    embedder = Embedder(model)
    for start in range(0, len(rows), batch):  # commit per batch so an interrupted run keeps work
        chunk = rows[start:start + batch]
        # The function's own text omits `res.send =`, so put file and full name in front.
        vecs = embedder.encode([f"// {p}: {q}\n{code}" for _, p, q, code in chunk])
        with conn.transaction(), conn.cursor() as cur:
            cur.executemany("INSERT INTO embeddings (function_id, model, embedding) "
                            "VALUES (%s, %s, %s)", [(r[0], model, v) for r, v in zip(chunk, vecs)])
    return len(rows)


def one(cur) -> tuple:
    """The single row a query must return (an id from RETURNING, a count, a known function)."""
    row = cur.fetchone()
    if row is None:
        raise LookupError("query returned no row")
    return row


def resolve_repo(cur: psycopg.Cursor, repo_id: int) -> None:
    cur.execute("SELECT id, path FROM files WHERE repo_id = %s", (repo_id,))
    paths: dict[int, str] = dict(cur.fetchall())
    files = {p: FileInfo([], []) for p in paths.values()}
    cur.execute("""SELECT fn.file_id, fn.id, fn.name, fn.qualname, fn.aliases FROM functions fn
                   JOIN files f ON f.id = fn.file_id WHERE f.repo_id = %s AND fn.kind <> 'module'
                   AND fn.name <> '<anonymous>'""", (repo_id,))
    for file_id, fid, name, qualname, aliases in cur.fetchall():
        entries = files[paths[file_id]].functions
        entries.append((fid, name, qualname))
        # Every full name also counts by its last part: res.type = function contentType -> `type`.
        entries.extend((fid, q.rsplit(".", 1)[-1], q) for q in [qualname, *aliases])
    cur.execute("""SELECT i.file_id, i.local, i.source, i.imported FROM imports i JOIN files f
                   ON f.id = i.file_id WHERE f.repo_id = %s""", (repo_id,))
    for file_id, local, source, imported in cur.fetchall():
        files[paths[file_id]].imports.append(Import(local, source, imported))
    cur.execute("""SELECT c.id, fn.file_id, c.name, c.receiver FROM calls c
                   JOIN functions fn ON fn.id = c.caller_id JOIN files f ON f.id = fn.file_id
                   WHERE f.repo_id = %s""", (repo_id,))
    calls = [CallRef(cid, paths[file_id], name, recv) for cid, file_id, name, recv in cur]
    cur.executemany("UPDATE calls SET callee_id = %s, resolution = %s WHERE id = %s",
                    [(callee, label, cid) for cid, callee, label in resolve(files, calls)])
