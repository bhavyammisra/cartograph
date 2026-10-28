"""Link each call to the function it most likely invokes, and label how sure we are.

Labels, most to least certain:
  same-file   a function with that name is defined in the calling file
  import      the name (or its receiver) was imported from another file in the repo
  qualname    exactly one function is defined under that full name, e.g. res.send = function...
  name-match  plain foo() call, and exactly one function in the whole repo is named foo
  builtin     a JavaScript built-in (JSON.parse, Object.create, Error, setTimeout)
  external    the name comes from an npm package, not this repo
  unresolved  can't tell statically (common names, dynamic dispatch)
  dynamic     the call has no name at all, e.g. handlers[name]()
"""

import posixpath
from collections import defaultdict
from dataclasses import dataclass

from .parser import Import

EXTS = ["", ".js", ".ts", ".tsx", ".mjs", ".cjs", ".jsx"]
BUILTIN_GLOBALS = {
    "Object", "Array", "JSON", "Math", "Promise", "console", "Number", "String", "Boolean",
    "Date", "RegExp", "Error", "TypeError", "RangeError", "SyntaxError", "Buffer", "process",
    "Reflect", "Symbol", "Map", "Set", "WeakMap", "WeakSet", "Intl", "BigInt", "URL",
    "setTimeout", "setInterval", "setImmediate", "clearTimeout", "clearInterval", "parseInt",
    "parseFloat", "isNaN", "encodeURIComponent", "decodeURIComponent", "encodeURI", "decodeURI",
    "require", "Function", "globalThis", "window", "document",
}


@dataclass
class FileInfo:
    functions: list[tuple[int, str, str]]  # (id, name, qualname); module pseudo-functions excluded
    imports: list[Import]


@dataclass
class CallRef:
    id: int
    path: str  # file of the calling function
    name: str | None
    receiver: str | None


def import_target(path: str, source: str, files: dict[str, FileInfo]) -> str | None:
    """Repo file a relative import points to, or None if it's not a file in the repo."""
    base = posixpath.normpath(posixpath.join(posixpath.dirname(path), source))
    candidates = [base + e for e in EXTS] + [posixpath.join(base, "index" + e) for e in EXTS[1:]]
    return next((posixpath.normpath(c) for c in candidates if posixpath.normpath(c) in files), None)


def resolve(files: dict[str, FileInfo], calls: list[CallRef]) -> list[tuple[int, int | None, str]]:
    by_file: dict[str, dict[str, list[int]]] = {}
    global_names: dict[str, list[int]] = defaultdict(list)
    global_quals: dict[str, list[int]] = defaultdict(list)
    for path, info in files.items():
        names: dict[str, list[int]] = defaultdict(list)
        for fid, name, qualname in info.functions:
            names[name].append(fid)
            global_names[name].append(fid)
            global_quals[qualname].append(fid)
        by_file[path] = names
    imports = {path: {i.local: i for i in info.imports} for path, info in files.items()}

    def unique(ids: list[int]) -> int | None:
        return ids[0] if len(set(ids)) == 1 else None  # a function may appear under aliases

    def default_export(path: str, hops: int = 0) -> int | None:
        """The function a file exports as a whole, following re-exports:
        index.js `module.exports = require('./lib/express')` -> `= createApplication`."""
        exp = imports[path].get("module.exports")
        if exp is None or hops > 5:
            return None
        if exp.source == "":
            return unique(by_file[path].get(exp.imported or "", []))
        nxt = import_target(path, exp.source, files) if exp.source.startswith(".") else None
        return default_export(nxt, hops + 1) if nxt else None

    out: list[tuple[int, int | None, str]] = []
    for c in calls:
        if c.name is None:
            out.append((c.id, None, "dynamic"))
            continue
        if c.receiver in BUILTIN_GLOBALS or (c.receiver is None and c.name in BUILTIN_GLOBALS):
            out.append((c.id, None, "builtin"))
            continue
        # Plain call of an imported name (foo()), or a call on an imported module (utils.foo()).
        # Checked before same-file: `var send = require('send')` must beat a nearby
        # `res.send = function send() {}`, whose name is only visible inside its own body.
        imp = imports[c.path].get(c.name if c.receiver is None else c.receiver)
        if imp:
            if not imp.source.startswith("."):
                out.append((c.id, None, "external"))
                continue
            target = import_target(c.path, imp.source, files)
            wanted = c.name if c.receiver or imp.imported in (None, "default") else imp.imported
            if target and (hit := unique(by_file[target].get(wanted, []))):
                out.append((c.id, hit, "import"))
                continue
            # Calling the module itself: var express = require('../../'); express()
            if (target and c.receiver is None and imp.imported in (None, "default")
                    and (hit := default_export(target))):
                out.append((c.id, hit, "import"))
                continue
        local = by_file[c.path]
        if c.receiver in (None, "this") and (hit := unique(local.get(c.name, []))):
            out.append((c.id, hit, "same-file"))
            continue
        if c.receiver and (hit := unique(global_quals.get(f"{c.receiver}.{c.name}", []))):
            out.append((c.id, hit, "qualname"))
        # Short-name match only for plain foo(): x.foo() could be any object's foo (too many
        # false links in Express, e.g. this.router.handle -> app.handle).
        elif c.receiver is None and (hit := unique(global_names.get(c.name, []))):
            out.append((c.id, hit, "name-match"))
        else:
            out.append((c.id, None, "unresolved"))
    return out
