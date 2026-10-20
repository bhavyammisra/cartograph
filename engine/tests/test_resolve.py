from cartograph.parser import Import
from cartograph.resolve import CallRef, FileInfo, resolve

FILES = {
    "index.js": FileInfo([], []),
    "lib/app.js": FileInfo(
        [(1, "init", "init"), (2, "handle", "app.handle")],
        [Import("Router", "./router", None), Import("debug", "debug", None),
         Import("flat", "./utils", "flatten")],
    ),
    "lib/router/index.js": FileInfo([(3, "handle", "Router.handle"), (4, "route", "route")], []),
    "lib/utils.js": FileInfo([(5, "flatten", "flatten"), (6, "onlyHere", "onlyHere"),
                              (7, "send", "res.send"), (8, "map", "app.map")], []),
    "lib/other.js": FileInfo([(9, "send", "send")], []),
    "examples/a/index.js": FileInfo([], [Import("express", "../../", None)]),
}


def run(path, name, receiver=None):
    return resolve(FILES, [CallRef(99, path, name, receiver)])[0][1:]


def test_same_file_beats_everything():
    assert run("lib/app.js", "init") == (1, "same-file")
    assert run("lib/app.js", "handle", "this") == (2, "same-file")


def test_imports():
    assert run("lib/app.js", "route", "Router") == (4, "import")  # ./router -> router/index.js
    assert run("lib/app.js", "flat") == (5, "import")  # aliased destructured require
    assert run("lib/app.js", "debug") == (None, "external")


def test_calling_a_module_follows_its_exports():
    files = {
        "index.js": FileInfo([], [Import("module.exports", "./lib/express", None)]),
        "lib/express.js": FileInfo([(1, "createApplication", "createApplication")],
                                   [Import("module.exports", "", "createApplication")]),
        "examples/a/index.js": FileInfo([], [Import("express", "../../", None)]),
    }
    hit = resolve(files, [CallRef(9, "examples/a/index.js", "express", None)])[0][1:]
    assert hit == (1, "import")


def test_builtins_never_match_repo_functions():
    assert run("lib/app.js", "create", "Object") == (None, "builtin")
    assert run("lib/app.js", "Error") == (None, "builtin")
    assert run("lib/app.js", "map", "users") == (None, "unresolved")  # not app.map


def test_qualname_beats_ambiguous_short_name():
    assert run("lib/app.js", "send", "res") == (7, "qualname")  # two `send`s, one `res.send`
    assert run("lib/app.js", "send", "reply") == (None, "unresolved")


def test_fallbacks():
    assert run("lib/app.js", "onlyHere") == (6, "name-match")
    assert run("lib/app.js", "onlyHere", "res") == (None, "unresolved")  # receiver: no guessing
    assert run("lib/utils.js", "handle") == (None, "unresolved")  # two `handle`s


def test_alias_entries_count_as_one_function():
    files = {"r.js": FileInfo([(1, "header", "res.header"), (1, "set", "res.set")], [])}
    calls = [CallRef(1, "r.js", "set", "this"), CallRef(2, "r.js", "set", "res")]
    assert [r[1:] for r in resolve(files, calls)] == [(1, "same-file"), (1, "qualname")]
    assert run("lib/app.js", None, "fns[i]") == (None, "dynamic")
