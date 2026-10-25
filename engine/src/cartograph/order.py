"""Ordering questions: is X always called before Y?

Inside one function, calls run in their recorded order (`seq`, arguments before the call that
takes them), and each call knows whether it always runs or only on some paths. Across functions,
a call to G "must reach" X if G always calls X (directly or through calls that always run).

X is always before Y in F when every call in F that may reach Y comes after a call that must
reach X. When not, the answer comes with a counterexample: the call path to a Y with no X before it.

shortcut: calls made by callbacks (arr.forEach(() => y())) and dynamic calls are invisible, so
"always" means "on every path we can see"; feed Jelly's callback edges in with an order if needed.
A target is a function's full name (`res.send`) or, for code outside the repo, a called name
(`setHeader`, `this.end`).
"""

from dataclasses import dataclass

Step = tuple[int, int]  # (function id, line of the call)


@dataclass(frozen=True)
class Site:
    seq: int
    line: int
    callee: int | None
    name: str | None
    receiver: str | None
    conditional: bool


class Order:
    def __init__(self, sites: dict[int, list[Site]], names: dict[int, str],
                 aliases: dict[int, list[str]] | None = None, paths: dict[int, str] | None = None):
        self.sites = {f: sorted(s, key=lambda s: s.seq) for f, s in sites.items()}
        self.names = names  # function id -> full name
        # every name a function answers to: res.set = res.header = function header(...)
        self.known = {f: {n, *(aliases or {}).get(f, ())} for f, n in names.items()}
        self.paths = paths or {}

    @classmethod
    def load(cls, conn, root: str) -> "Order":
        from .api import SCOPE

        rows = conn.execute(f"SELECT fn.id, fn.qualname, fn.aliases, f.path FROM functions fn {SCOPE}",
                            (root,)).fetchall()
        names = {f: q for f, q, _, _ in rows}
        sites: dict[int, list[Site]] = {f: [] for f in names}
        for caller, *rest in conn.execute(
                f"""SELECT c.caller_id, c.seq, c.line, c.callee_id, c.name, c.receiver, c.conditional
                    FROM calls c JOIN functions fn ON fn.id = c.caller_id {SCOPE}""", (root,)):
            sites[caller].append(Site(*rest))
        return cls(sites, names, {f: a for f, _, a, _ in rows}, {f: p for f, _, _, p in rows})

    def hits(self, s: Site, target: str) -> bool:
        if s.callee is not None:
            return target in self.known.get(s.callee, ())
        return target in (s.name, f"{s.receiver}.{s.name}")

    def must(self, f: int, x: str, seen: frozenset = frozenset()) -> bool:
        """Does every run of f call x?"""
        if f in seen:
            return False  # recursion: can't prove it
        return any(not s.conditional and (self.hits(s, x) or (
            s.callee is not None and self.must(s.callee, x, seen | {f}))) for s in self.sites.get(f, ()))

    def may(self, f: int, y: str, seen: frozenset = frozenset()) -> list[Step] | None:
        """A call path from f to y, if there is one."""
        if f in seen:
            return None
        for s in self.sites.get(f, ()):
            if self.hits(s, y):
                return [(f, s.line)]
            if s.callee is not None and (rest := self.may(s.callee, y, seen | {f})):
                return [(f, s.line), *rest]
        return None

    def before(self, f: int, x: str, y: str, seen: frozenset = frozenset()) -> list[Step] | None:
        """None if x is always called before any y in f; otherwise a path to a y with no x first."""
        sites = self.sites.get(f, ())
        first_x = next((s for s in sites if not s.conditional and (
            self.hits(s, x) or (s.callee is not None and self.must(s.callee, x)))), None)
        for s in sites:
            if self.hits(s, y):
                to_y = [(f, s.line)]
            elif s.callee is not None and (rest := self.may(s.callee, y, seen | {f})):
                to_y = [(f, s.line), *rest]
            else:
                continue
            if (first_x is not None and first_x.seq < s.seq) or self.hits(s, x):
                continue  # an x already ran, or this call is x itself and y happens inside it
            if s.callee is not None and s.callee not in seen | {f} and self.must(s.callee, x):
                # This call always reaches x too (even if the call itself is conditional):
                # the order is decided inside it.
                if (inner := self.before(s.callee, x, y, seen | {f})) is None:
                    continue
                return [(f, s.line), *inner]
            return to_y
        return None

    def ask(self, x: str, y: str, within: list[int]) -> dict:
        """Is x always before y, starting from each of `within`? Starts that never reach y don't count."""
        reach = [f for f in within if self.may(f, y)]
        counter = {self.where(f): [self.where(g, line) for g, line in path]
                   for f in reach if (path := self.before(f, x, y)) is not None}
        return {"answer": "unreachable" if not reach else "not always" if counter else "always",
                "starts_reaching_y": len(reach), "counterexamples": counter}

    def where(self, f: int, line: int | None = None) -> str:
        """`res.send (lib/response.js:215)`: a step a person can open."""
        place = self.paths.get(f, "")
        place += f":{line}" if place and line else f"line {line}" if line else ""
        return f"{self.names[f]} ({place})" if place else self.names[f]

    def entries(self) -> list[int]:
        """Functions nothing in the repo calls: where execution starts (exports, module code)."""
        called = {s.callee for f, sites in self.sites.items() for s in sites if s.callee != f}
        return [f for f in self.sites if f not in called]

    def naive(self, x: str, y: str, f: int) -> str:
        """Baseline: first x line before first y line in f's own calls, ignoring branches and calls."""
        lines = {t: min((s.line for s in self.sites.get(f, ()) if self.hits(s, t)), default=None)
                 for t in (x, y)}
        if lines[y] is None:
            return "unreachable"
        return "always" if lines[x] is not None and lines[x] <= lines[y] else "not always"
