from cartograph.jelly import jelly_edges

CG = {
    "files": ["lib\\a.js", "node_modules\\dep\\x.js"],
    "functions": {
        "0": "0:1:1:40:1",    # lib/a.js top-level code
        "1": "0:3:10:9:2",    # a function on lines 3-9
        "2": "0:12:5:14:6",   # a function we don't know
        "3": "1:1:1:5:1",     # dependency code: ignored
    },
    "fun2fun": [[0, 1], [1, 3], [1, 2]],
}


def test_maps_functions_and_modules_skips_dependencies():
    edges, unmatched = jelly_edges(CG, {("lib/a.js", 3, 9): 101}, {"lib/a.js": 100})
    assert edges == {(100, 101)}  # module -> function; edges into deps/unknowns dropped
    assert unmatched == 1  # function 2 (dependency code isn't counted)
