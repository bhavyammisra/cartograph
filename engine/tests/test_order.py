from cartograph.order import Order
from cartograph.parser import parse

SRC = b"""
function status(c) { this.code = c; }
function send(b) { this.end(b); }
function ok(res) { status(200); send('hi'); }
function maybe(res, c) { if (c) status(500); send('x'); }
function wrapped(res) { finish(); }
function finish() { status(201); send('y'); }
function backwards(res) { send(status(1)); }
function recurse(n) { if (n) recurse(n - 1); send(''); }
function guarded(res, ok) { if (ok) finish(); }
"""


def build() -> Order:
    functions, _ = parse(SRC, "javascript", "m")
    ids = {f.qualname: i for i, f in enumerate(functions)}
    sites = {}
    for i, f in enumerate(functions):
        sites[i] = [(c.seq, c.line, ids.get(c.name), c.name, c.receiver, c.conditional)
                    for c in f.calls]
    from cartograph.order import Site

    return Order({i: [Site(*s) for s in v] for i, v in sites.items()},
                 {i: f.qualname for i, f in enumerate(functions)}), ids


def test_levels_one_and_two():
    order, ids = build()
    assert order.ask("status", "send", [ids["ok"]])["answer"] == "always"
    # A status call inside an if doesn't count: counterexample is the send on line 5.
    r = order.ask("status", "send", [ids["maybe"]])
    assert r["answer"] == "not always" and r["counterexamples"]["maybe"] == ["maybe (line 5)"]
    assert order.ask("status", "send", [ids["wrapped"]])["answer"] == "always"  # through finish()
    # A conditional call is fine when the function it calls does status() before send() itself.
    assert order.ask("status", "send", [ids["guarded"]])["answer"] == "always"
    assert order.ask("status", "send", [ids["backwards"]])["answer"] == "always"  # args run first
    assert order.ask("send", "status", [ids["backwards"]])["answer"] == "not always"
    assert order.ask("status", "send", [ids["status"]])["answer"] == "unreachable"
    # Outside code by called name, reached through send(): this.end
    r = order.ask("status", "this.end", [ids["maybe"]])
    assert r["counterexamples"]["maybe"] == ["maybe (line 5)", "send (line 3)"]


def test_entry_points_and_baseline():
    order, ids = build()
    r = order.ask("status", "send", order.entries())
    assert r["answer"] == "not always" and set(r["counterexamples"]) == {"maybe", "recurse"}
    assert order.naive("status", "send", ids["maybe"]) == "always"  # fooled by the if
    assert order.naive("status", "send", ids["wrapped"]) == "unreachable"  # can't see through calls
