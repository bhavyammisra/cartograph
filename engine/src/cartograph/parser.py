"""Turn one JS/TS file into functions (with their calls, in order) and imports, using tree-sitter."""

from dataclasses import dataclass, field

import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Node, Parser

PARSERS = {
    "javascript": Parser(Language(tsjs.language())),  # this grammar also covers JSX
    "typescript": Parser(Language(tsts.language_typescript())),
    "tsx": Parser(Language(tsts.language_tsx())),
}
EXTENSIONS = {
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".mts": "typescript", ".cts": "typescript", ".tsx": "tsx",
}
FUNCTION_TYPES = {
    "function_declaration", "function_expression", "arrow_function",
    "method_definition", "generator_function_declaration", "generator_function",
}


@dataclass
class Call:
    seq: int  # order inside the calling function, starting at 0
    line: int
    name: str | None  # called name: `foo` in foo(), `send` in res.send(); None if dynamic
    receiver: str | None  # `res` in res.send(), `this` in this.set(); None for plain foo()


@dataclass
class Function:
    name: str
    qualname: str  # e.g. `res.send`, `Router.handle`; same as name when there is no owner
    kind: str  # tree-sitter node type, or "module" for top-level code
    start_line: int
    end_line: int
    code: str
    calls: list[Call] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)  # extra names: a.x = a.y = function...


@dataclass
class Import:
    local: str  # name used in this file
    source: str  # module string, e.g. './router' or 'debug'
    imported: str | None  # exported name it refers to; None = whole module, 'default' = default


def text(node: Node | None) -> str:
    return node.text.decode("utf-8", "replace") if node else ""


def chained_names(node: Node) -> list[str]:
    """Outer targets of a chained assignment: ['res.set'] for res.set = res.header = function..."""
    out, p = [], node.parent.parent if node.parent else None
    while p is not None and p.type == "assignment_expression":
        out.append(text(p.child_by_field_name("left")))
        p = p.parent
    return out


def function_names(node: Node) -> tuple[str, str]:
    """Best name for a function node, and a qualified name showing its owner."""
    own = text(node.child_by_field_name("name"))
    parent = node.parent
    if node.type == "method_definition":
        cls = parent.parent if parent and parent.type == "class_body" else None
        owner = text(cls.child_by_field_name("name")) if cls else ""
        return own, f"{owner}.{own}" if owner else own
    if parent is None:
        return own or "<anonymous>", own or "<anonymous>"
    if parent.type == "variable_declarator":
        name = text(parent.child_by_field_name("name"))
        return own or name, name
    if parent.type == "assignment_expression":
        left = parent.child_by_field_name("left")
        prop = left.child_by_field_name("property") if left and left.type == "member_expression" else left
        return own or text(prop), text(left)
    if parent.type == "pair":
        key = text(parent.child_by_field_name("key"))
        return own or key, key
    return own or "<anonymous>", own or "<anonymous>"


def call_target(node: Node) -> tuple[str | None, str | None]:
    """(name, receiver) of what a call or `new` expression invokes."""
    fn = node.child_by_field_name("function" if node.type == "call_expression" else "constructor")
    if fn is None:
        return None, None
    if fn.type == "identifier":
        return text(fn), None
    if fn.type == "member_expression":
        return text(fn.child_by_field_name("property")), text(fn.child_by_field_name("object"))
    return None, text(fn)[:80]  # dynamic: fn()(), arr[i](), (a || b)()


def require_source(node: Node | None) -> str | None:
    """'x' if node is require('x'), else None."""
    if node is None or node.type != "call_expression":
        return None
    if text(node.child_by_field_name("function")) != "require":
        return None
    args = [a for a in node.child_by_field_name("arguments").named_children]
    return text(args[0])[1:-1] if args and args[0].type == "string" else None


def collect_imports(node: Node, out: list[Import]) -> None:
    if node.type == "import_statement":
        source = text(node.child_by_field_name("source"))[1:-1]
        for clause in (c for c in node.named_children if c.type == "import_clause"):
            for part in clause.named_children:
                if part.type == "identifier":
                    out.append(Import(text(part), source, "default"))
                elif part.type == "namespace_import":
                    out.append(Import(text(part.named_children[-1]), source, None))
                elif part.type == "named_imports":
                    for spec in part.named_children:
                        name = text(spec.child_by_field_name("name"))
                        alias = text(spec.child_by_field_name("alias")) or name
                        out.append(Import(alias, source, name))
    elif node.type == "variable_declarator":
        source = require_source(node.child_by_field_name("value"))
        target = node.child_by_field_name("name")
        if source is not None and target is not None:
            if target.type == "identifier":
                out.append(Import(text(target), source, None))
            elif target.type == "object_pattern":
                for p in target.named_children:
                    if p.type == "shorthand_property_identifier_pattern":
                        out.append(Import(text(p), source, text(p)))
                    elif p.type == "pair_pattern":
                        key, value = p.child_by_field_name("key"), p.child_by_field_name("value")
                        out.append(Import(text(value), source, text(key)))


def parse(source: bytes, lang: str, module_name: str) -> tuple[list[Function], list[Import]]:
    tree = PARSERS[lang].parse(source)
    root = tree.root_node
    # Top-level code (outside any function) becomes a "module" pseudo-function so its calls count.
    module = Function(module_name, module_name, "module", 1, root.end_point[0] + 1, "")
    functions, imports = [module], []

    # Explicit stack instead of recursion: deep expressions can exceed Python's recursion limit.
    stack: list[tuple[Node, Function, bool]] = [(root, module, False)]
    while stack:
        node, owner, done = stack.pop()
        if done:
            # Calls are recorded after their arguments (post-order): in foo(bar()), bar runs first.
            name, receiver = call_target(node)
            owner.calls.append(Call(len(owner.calls), node.start_point[0] + 1, name, receiver))
            continue
        collect_imports(node, imports)
        if node.type in FUNCTION_TYPES:
            name, qualname = function_names(node)
            owner = Function(name, qualname, node.type, node.start_point[0] + 1,
                             node.end_point[0] + 1, text(node), aliases=chained_names(node))
            functions.append(owner)
        elif node.type in ("call_expression", "new_expression") and require_source(node) is None:
            stack.append((node, owner, True))
        stack.extend((child, owner, False) for child in reversed(node.children))
    return functions, imports
