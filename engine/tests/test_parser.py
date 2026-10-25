from cartograph.parser import Import, parse

SOURCE = b"""
var Router = require('./router');
const { flatten, merge: mergeAll } = require('./utils');
import send, { json as toJson } from './send.js';

res.send = function send(body) {
  this.set('Content-Type');
  helper(validate(body));
};

app.use = function (fn) {
  return Router.handle(fn);
};

function checkout(cart, user) {
  validateUser(user);
  saveOrder(cart);
}

class Cart {
  add(item) { new Item(item); }
}

const handlers = { pick: () => handlers[name]() };
app.listen(3000);
"""


def test_functions_and_names():
    functions, _ = parse(SOURCE, "javascript", "app.js")
    by_qual = {f.qualname: f for f in functions}
    assert set(by_qual) == {
        "app.js", "res.send", "app.use", "checkout", "Cart.add", "pick",
    }
    assert by_qual["app.use"].name == "use"
    assert by_qual["app.js"].kind == "module"
    assert (by_qual["checkout"].start_line, by_qual["checkout"].end_line) == (15, 18)


def test_calls_in_execution_order():
    functions, _ = parse(SOURCE, "javascript", "app.js")
    by_qual = {f.qualname: f for f in functions}
    calls = lambda q: [(c.name, c.receiver) for c in by_qual[q].calls]
    assert calls("res.send") == [("set", "this"), ("validate", None), ("helper", None)]
    assert calls("checkout") == [("validateUser", None), ("saveOrder", None)]
    assert calls("app.use") == [("handle", "Router")]
    assert calls("Cart.add") == [("Item", None)]
    assert calls("pick") == [(None, "handlers[name]")]  # dynamic call: name unknown
    # require() is not a call edge, and top-level calls belong to the module
    assert calls("app.js") == [("listen", "app")]
    assert [c.seq for c in by_qual["res.send"].calls] == [0, 1, 2]


def test_imports():
    _, imports = parse(SOURCE, "javascript", "app.js")
    assert {(i.local, i.source, i.imported) for i in imports} == {
        ("Router", "./router", None),
        ("flatten", "./utils", "flatten"),
        ("mergeAll", "./utils", "merge"),
        ("send", "./send.js", "default"),
        ("toJson", "./send.js", "json"),
    }


def test_module_exports_are_recorded():
    src = b"exports = module.exports = createApplication;\nfunction createApplication() {}"
    assert parse(src, "javascript", "e.js")[1] == [Import("module.exports", "", "createApplication")]
    src = b"module.exports = require('./lib/express');"
    assert parse(src, "javascript", "i.js")[1] == [Import("module.exports", "./lib/express", None)]


def test_chained_assignment_keeps_every_name():
    src = b"res.set = res.header = function header(f, v) {};"
    functions, _ = parse(src, "javascript", "r.js")
    assert [(f.qualname, f.aliases) for f in functions[1:]] == [("res.header", ["res.set"])]


def test_typescript_parses():
    src = b"export function total(xs: number[]): number { return sum(xs); }"
    functions, _ = parse(src, "typescript", "t.ts")
    assert [(f.name, [c.name for c in f.calls]) for f in functions[1:]] == [("total", ["sum"])]


def test_calls_know_whether_they_always_run():
    src = (b"function f() {\n  if (c()) a(); else b();\n  x = p() ? q() : r();\n  u() && v();\n"
           b"  for (i(); j(); k()) l();\n  switch (s()) { case 1: t(); }\n  try { y(); } catch (e) { z(); }\n"
           b"  w ||= o();\n  list.forEach(() => cb());\n  done();\n}\n")
    functions, _ = parse(src, "javascript", "m")
    f = next(fn for fn in functions if fn.name == "f")
    sometimes = {c.name for c in f.calls if c.conditional}
    assert sometimes == {"a", "b", "q", "r", "v", "k", "l", "t", "z", "o"}
    always = {c.name for c in f.calls if not c.conditional}
    assert always == {"c", "p", "u", "i", "j", "s", "y", "forEach", "done"}
    inner = next(fn for fn in functions if fn.kind == "arrow_function")
    assert [(c.name, c.conditional) for c in inner.calls] == [("cb", False)]  # its own function
