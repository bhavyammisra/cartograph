"""Retrievers over a repo's indexed functions. Each takes a question and returns ranked function ids."""

import re
from dataclasses import dataclass

import bm25s
import psycopg

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "it", "for", "on", "with", "as", "be",
    "this", "that", "are", "was", "not", "but", "if", "when", "by", "at", "from", "i", "we", "you",
    "my", "can", "do", "does", "should", "would", "will", "there", "have", "has", "so", "what",
}


def tokenize(text: str) -> list[str]:
    """Words, with code names split: getUserById -> get user by id, user_name -> user name."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 1 and w not in STOPWORDS]


@dataclass
class Doc:
    id: int
    path: str
    qualname: str
    text: str  # what keyword search sees: path, names and code


def load_corpus(conn: psycopg.Connection, root: str) -> list[Doc]:
    """Every named or anonymous function in non-test files of the repo indexed at `root`."""
    rows = conn.execute(
        """SELECT fn.id, f.path, fn.qualname, array_to_string(fn.aliases, ' '), fn.code
           FROM functions fn JOIN files f ON f.id = fn.file_id JOIN repos r ON r.id = f.repo_id
           WHERE r.root = %s AND NOT f.is_test AND fn.kind <> 'module' ORDER BY fn.id""",
        (root,)).fetchall()
    if not rows:
        raise SystemExit(f"Nothing indexed for {root}. Run: cartograph index {root}")
    return [Doc(i, p, q, f"{p} {q} {a} {code}") for i, p, q, a, code in rows]


class BM25:
    def __init__(self, docs: list[Doc]):
        self.ids = [d.id for d in docs]
        self.model = bm25s.BM25()
        self.model.index([tokenize(d.text) for d in docs], show_progress=False)

    def __call__(self, question: str, k: int = 50) -> list[int]:
        tokens = tokenize(question)
        if not tokens:
            return []
        hits, _ = self.model.retrieve([tokens], k=min(k, len(self.ids)), show_progress=False)
        return [self.ids[i] for i in hits[0]]
