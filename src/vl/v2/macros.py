"""VL v2 macro registry and expander.

A macro is a single-line, valid-Python call that stands for a multi-line
Python pattern. LLMs read and write the compact form; ``expand_macros``
turns it back into plain Python for execution.

Why this shape: BPE tokenizers compress idiomatic Python extremely well,
so the only reliable way to save tokens is to remove *lines*, not
characters. Function-call syntax tokenizes as cheaply as any Python and
needs no special parsing. Every macro here must beat its own expansion
on a real tokenizer (tests/benchmarks/v2_macro_benchmark.py) to stay in
the registry.
"""

import ast
import copy
from typing import List, Optional


class MacroError(Exception):
    pass


def _unparse(node: ast.AST) -> str:
    return ast.unparse(node)


def _inline_predicate(func: ast.expr, var: str) -> str:
    """Return source for applying predicate ``func`` to variable ``var``.

    Lambdas are inlined (parameter substituted) for cleaner, cheaper code;
    anything else is called.
    """
    if isinstance(func, ast.Lambda) and len(func.args.args) == 1:
        param = func.args.args[0].arg

        class Sub(ast.NodeTransformer):
            def visit_Name(self, node: ast.Name):
                if node.id == param:
                    return ast.copy_location(ast.Name(id=var, ctx=node.ctx), node)
                return node

        body = Sub().visit(copy.deepcopy(func.body))
        return _unparse(body)
    return f"{_unparse(func)}({var})"


def _kwargs(call: ast.Call) -> dict:
    return {kw.arg: kw.value for kw in call.keywords if kw.arg}


class _Expansion:
    """One macro expansion: replacement statements + imports it needs."""

    def __init__(self, code: str, imports: Optional[List[str]] = None):
        self.statements = ast.parse(code).body
        self.imports = imports or []


# --- macro expanders -------------------------------------------------------
# Each takes (call, target, counter) and returns an _Expansion.
# ``target`` is the assignment target source ('' for statement macros).


def _expand_jload(call: ast.Call, target: str, n: int) -> _Expansion:
    if not target or len(call.args) != 1:
        raise MacroError("jload(path) must be assigned: data = jload(path)")
    path = _unparse(call.args[0])
    f = f"_f{n}"
    return _Expansion(
        f"with open({path}, 'r', encoding='utf-8') as {f}:\n"
        f"    {target} = json.load({f})",
        imports=["json"],
    )


def _expand_jsave(call: ast.Call, target: str, n: int) -> _Expansion:
    if target or len(call.args) != 2:
        raise MacroError("jsave(obj, path) is a statement: jsave(data, path)")
    obj, path = (_unparse(a) for a in call.args)
    f = f"_f{n}"
    return _Expansion(
        f"with open({path}, 'w', encoding='utf-8') as {f}:\n"
        f"    json.dump({obj}, {f}, indent=2)",
        imports=["json"],
    )


def _expand_group_agg(call: ast.Call, target: str, n: int) -> _Expansion:
    if not target or len(call.args) != 1:
        raise MacroError(
            "group_agg(items, by=..., val=..., fn=..., where=...) must be assigned"
        )
    items = _unparse(call.args[0])
    kw = _kwargs(call)
    if "by" not in kw:
        raise MacroError("group_agg requires by=")
    by = _unparse(kw["by"])
    fn = _unparse(kw["fn"]) if "fn" in kw else "sum"
    it, g, k, v = f"_x{n}", f"_g{n}", f"_k{n}", f"_v{n}"
    value = f"{it}[{_unparse(kw['val'])}]" if "val" in kw else it
    lines = [f"{g} = {{}}", f"for {it} in {items}:"]
    if "where" in kw:
        lines.append(f"    if not ({_inline_predicate(kw['where'], it)}):")
        lines.append("        continue")
    lines.append(f"    {g}.setdefault({it}[{by}], []).append({value})")
    lines.append(f"{target} = {{{k}: {fn}({v}) for {k}, {v} in {g}.items()}}")
    return _Expansion("\n".join(lines))


def _expand_get_json(call: ast.Call, target: str, n: int) -> _Expansion:
    if not target or len(call.args) != 1:
        raise MacroError("get_json(url, where=...) must be assigned")
    url = _unparse(call.args[0])
    kw = _kwargs(call)
    r, it = f"_r{n}", f"_x{n}"
    lines = [
        f"{r} = requests.get({url}, timeout=30)",
        f"{r}.raise_for_status()",
        f"{target} = {r}.json()",
    ]
    if "where" in kw:
        cond = _inline_predicate(kw["where"], it)
        lines.append(f"{target} = [{it} for {it} in {target} if {cond}]")
    return _Expansion("\n".join(lines), imports=["requests"])


def _expand_read_lines(call: ast.Call, target: str, n: int) -> _Expansion:
    if not target or len(call.args) != 1:
        raise MacroError("read_lines(path) must be assigned")
    path = _unparse(call.args[0])
    f, ln = f"_f{n}", f"_l{n}"
    return _Expansion(
        f"with open({path}, 'r', encoding='utf-8') as {f}:\n"
        f"    {target} = [{ln}.rstrip('\\n') for {ln} in {f}]"
    )


MACROS = {
    "jload": _expand_jload,
    "jsave": _expand_jsave,
    "group_agg": _expand_group_agg,
    "get_json": _expand_get_json,
    "read_lines": _expand_read_lines,
}

# Compact spec to include once per conversation when asking an LLM to
# write VL v2 code. Its token cost is counted by the benchmark
# (break-even = spec tokens / mean saving per use).
MACRO_SPEC = """VL v2 macros (valid Python calls; the compiler expands them):
data = jload(path)                      # read JSON file
jsave(obj, path)                        # write JSON file (indent=2)
lines = read_lines(path)                # file -> list of lines, no \\n
out = group_agg(items, by='key', val='field', fn=sum, where=lambda x: ...)
                                        # group dicts by key, aggregate field
items = get_json(url, where=lambda r: ...)  # HTTP GET -> filtered JSON list
"""


class _MacroTransformer(ast.NodeTransformer):
    def __init__(self):
        self.counter = 0
        self.needed_imports: List[str] = []
        self.errors: List[str] = []

    def _try_expand(self, stmt: ast.stmt) -> Optional[List[ast.stmt]]:
        target = ""
        if isinstance(stmt, ast.Assign):
            if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
                return None
            call = stmt.value
            target = stmt.targets[0].id
        elif isinstance(stmt, ast.Expr):
            call = stmt.value
        else:
            return None
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)):
            return None
        expander = MACROS.get(call.func.id)
        if expander is None:
            return None
        self.counter += 1
        try:
            expansion = expander(call, target, self.counter)
        except MacroError as exc:
            self.errors.append(str(exc))
            return None
        for imp in expansion.imports:
            if imp not in self.needed_imports:
                self.needed_imports.append(imp)
        return expansion.statements

    def generic_visit(self, node: ast.AST) -> ast.AST:
        node = super().generic_visit(node)
        for field in ("body", "orelse", "finalbody"):
            stmts = getattr(node, field, None)
            if not isinstance(stmts, list):
                continue
            new_stmts: List[ast.stmt] = []
            for stmt in stmts:
                expanded = self._try_expand(stmt)
                new_stmts.extend(expanded if expanded is not None else [stmt])
            setattr(node, field, new_stmts)
        return node


def _existing_imports(tree: ast.Module) -> set:
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def expand_macros(source: str) -> str:
    """Expand all VL v2 macro calls in ``source`` to plain Python."""
    tree = ast.parse(source)
    transformer = _MacroTransformer()
    tree = transformer.visit(tree)
    if transformer.errors:
        raise MacroError("; ".join(transformer.errors))
    missing = [m for m in transformer.needed_imports if m not in _existing_imports(tree)]
    insert_at = 0
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        insert_at = 1  # keep module docstring first
    for module in reversed(missing):
        tree.body.insert(insert_at, ast.Import(names=[ast.alias(name=module)]))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n"
