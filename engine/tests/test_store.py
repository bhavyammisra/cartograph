import os

import psycopg
import pytest

from cartograph.store import DEFAULT_DB, index_repo

try:
    CONN = psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DB), autocommit=True,
                           connect_timeout=2)
except psycopg.OperationalError:
    CONN = None


@pytest.mark.skipif(CONN is None, reason="Postgres not running")
def test_index_and_reindex(tmp_path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "a.js").write_text(
        "const { b } = require('./b');\nfunction a() { b(); missing(); }\n")
    (tmp_path / "lib" / "b.js").write_text("function b() {}\nmodule.exports = { b };\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("function ignored() {}")

    # Everything happens inside a transaction that is rolled back, so the real DB stays clean.
    with CONN.transaction(force_rollback=True):
        stats = index_repo(CONN, tmp_path)
        assert stats["files"] == 2 and stats["parsed"] == 2 and stats["functions"] == 2
        assert stats["calls:import"] == 1 and stats["calls:unresolved"] == 1

        again = index_repo(CONN, tmp_path)  # nothing changed: nothing re-parsed
        assert again["parsed"] == 0 and again["calls:import"] == 1

        (tmp_path / "lib" / "b.js").unlink()  # deleted file: its rows and edges go away
        gone = index_repo(CONN, tmp_path)
        assert gone["removed"] == 1 and gone["calls:unresolved"] == 2
