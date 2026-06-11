"""VL v2 pattern detector: compress expanded Python patterns into macro calls.

The inverse of ``expand_macros``: recognizes the multi-line Python idioms
that the registry macros stand for and rewrites them as single-line macro
calls, so existing code can be compressed before being sent to an LLM.

Matchers are deliberately conservative. A rewrite only happens when:
  - the statement shape matches a known pattern exactly, and
  - the pattern's internal names (file handle, loop variable, accumulator,
    response object) are not referenced anywhere else in the module — they
    leak out of ``with``/``for`` blocks in Python, so reusing them later
    would make the rewrite change behavior.

Known normalizations (documented, considered acceptable for LLM-context
use; avoid --compress if they matter):
  - ``jsave``: ``json.dump`` indent is normalized to 2 on round-trip.
  - ``get_json``: timeout is normalized to 30 on round-trip.
"""

import ast
import copy
import symtable
from typing import Dict, List, Optional, Tuple


def _is_name(node: ast.AST, name: Optional[str] = None) -> bool:
    return isinstance(node, ast.Name) and (name is None or node.id == name)


def _is_const(node: ast.AST, value=None) -> bool:
    return isinstance(node, ast.Constant) and (value is None or node.value == value)


def _is_attr_call(node: ast.AST, obj_name: str, attr: str) -> bool:
    """Match ``obj_name.attr(...)``."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == attr
        and _is_name(node.func.value, obj_name)
    )


def _match_open(call: ast.AST, mode: str, allow_newline: bool = False) -> Optional[ast.expr]:
    """Match ``open(path[, mode][, encoding='utf-8'][, newline=''])``.

    Returns the path expression. ``mode`` 'r' also accepts the implicit
    default; ``newline=''`` is only accepted when ``allow_newline`` (the
    csv case). Any other mode, a non-utf-8 encoding, or extra arguments
    → no match (round-trip would change behavior).
    """
    if not (isinstance(call, ast.Call) and _is_name(call.func, "open")):
        return None
    if len(call.args) < 1 or len(call.args) > 2:
        return None
    if len(call.args) == 2:
        if not _is_const(call.args[1], mode):
            return None
    elif mode != "r":
        return None
    for kw in call.keywords:
        if kw.arg == "encoding" and _is_const(kw.value, "utf-8"):
            continue
        if kw.arg == "mode" and _is_const(kw.value, mode):
            continue
        if allow_newline and kw.arg == "newline" and _is_const(kw.value, ""):
            continue
        return None
    return call.args[0]


def _single_with(stmt: ast.AST) -> Optional[Tuple[ast.expr, str, List[ast.stmt]]]:
    """Match ``with <expr> as NAME:`` — return (context_expr, NAME, body)."""
    if not isinstance(stmt, ast.With) or len(stmt.items) != 1:
        return None
    item = stmt.items[0]
    if not (item.optional_vars is not None and _is_name(item.optional_vars)):
        return None
    return item.context_expr, item.optional_vars.id, stmt.body


class _Match:
    """A successful pattern match: replacement source + consumed statements."""

    def __init__(self, macro: str, replacement: str, consumed: int, internal_names: List[str]):
        self.macro = macro
        self.replacement = replacement
        self.consumed = consumed
        self.internal_names = internal_names


# --- per-macro matchers ----------------------------------------------------
# Each takes the statement window stmts[i:] and returns a _Match or None.


def _match_jload(stmts: List[ast.stmt]) -> Optional[_Match]:
    w = _single_with(stmts[0])
    if w is None:
        return None
    ctx, fname, body = w
    path = _match_open(ctx, "r")
    if path is None or len(body) != 1:
        return None
    inner = body[0]
    if not (isinstance(inner, ast.Assign) and len(inner.targets) == 1 and _is_name(inner.targets[0])):
        return None
    call = inner.value
    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "load"
        and _is_name(call.func.value, "json")
        and len(call.args) == 1
        and _is_name(call.args[0], fname)
        and not call.keywords
    ):
        return None
    target = inner.targets[0].id
    return _Match("jload", f"{target} = jload({ast.unparse(path)})", 1, [fname])


def _match_jsave(stmts: List[ast.stmt]) -> Optional[_Match]:
    w = _single_with(stmts[0])
    if w is None:
        return None
    ctx, fname, body = w
    path = _match_open(ctx, "w")
    if path is None or len(body) != 1:
        return None
    inner = body[0]
    if not isinstance(inner, ast.Expr):
        return None
    call = inner.value
    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "dump"
        and _is_name(call.func.value, "json")
        and len(call.args) == 2
        and _is_name(call.args[1], fname)
        and all(kw.arg == "indent" for kw in call.keywords)
    ):
        return None
    obj = ast.unparse(call.args[0])
    return _Match("jsave", f"jsave({obj}, {ast.unparse(path)})", 1, [fname])


def _match_read_lines(stmts: List[ast.stmt]) -> Optional[_Match]:
    w = _single_with(stmts[0])
    if w is None:
        return None
    ctx, fname, body = w
    path = _match_open(ctx, "r")
    if path is None or len(body) != 1:
        return None
    inner = body[0]
    if not (isinstance(inner, ast.Assign) and len(inner.targets) == 1 and _is_name(inner.targets[0])):
        return None
    value = inner.value
    matched = False
    # Variant 1: [l.rstrip('\n') for l in f]
    if (
        isinstance(value, ast.ListComp)
        and len(value.generators) == 1
        and not value.generators[0].ifs
        and _is_name(value.generators[0].iter, fname)
        and _is_name(value.generators[0].target)
    ):
        loop_var = value.generators[0].target.id
        elt = value.elt
        if (
            isinstance(elt, ast.Call)
            and isinstance(elt.func, ast.Attribute)
            and elt.func.attr == "rstrip"
            and _is_name(elt.func.value, loop_var)
            and len(elt.args) == 1
            and _is_const(elt.args[0], "\n")
        ):
            matched = True
    # Variant 2: f.read().splitlines()
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr == "splitlines"
        and not value.args
        and not value.keywords
        and _is_attr_call(value.func.value, fname, "read")
        and not value.func.value.args
    ):
        matched = True
    if not matched:
        return None
    target = inner.targets[0].id
    return _Match("read_lines", f"{target} = read_lines({ast.unparse(path)})", 1, [fname])


def _match_get_json(stmts: List[ast.stmt]) -> Optional[_Match]:
    # r = requests.get(url[, timeout=ANY])
    if len(stmts) < 3:
        return None
    s0 = stmts[0]
    if not (isinstance(s0, ast.Assign) and len(s0.targets) == 1 and _is_name(s0.targets[0])):
        return None
    call = s0.value
    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "get"
        and _is_name(call.func.value, "requests")
        and len(call.args) == 1
        and all(kw.arg == "timeout" for kw in call.keywords)
    ):
        return None
    rname = s0.targets[0].id
    url = ast.unparse(call.args[0])
    # r.raise_for_status() — required: compressing without it would silently
    # add error-raising behavior on round-trip.
    s1 = stmts[1]
    if not (isinstance(s1, ast.Expr) and _is_attr_call(s1.value, rname, "raise_for_status")):
        return None
    # target = r.json()
    s2 = stmts[2]
    if not (
        isinstance(s2, ast.Assign)
        and len(s2.targets) == 1
        and _is_name(s2.targets[0])
        and _is_attr_call(s2.value, rname, "json")
        and not s2.value.args
    ):
        return None
    target = s2.targets[0].id
    consumed = 3
    where = ""
    # Optional: target = [x for x in target if COND]
    if len(stmts) > 3:
        s3 = stmts[3]
        if (
            isinstance(s3, ast.Assign)
            and len(s3.targets) == 1
            and _is_name(s3.targets[0], target)
            and isinstance(s3.value, ast.ListComp)
            and len(s3.value.generators) == 1
        ):
            gen = s3.value.generators[0]
            if (
                _is_name(gen.iter, target)
                and _is_name(gen.target)
                and len(gen.ifs) == 1
                and _is_name(s3.value.elt, gen.target.id)
            ):
                where = f", where=lambda {gen.target.id}: {ast.unparse(gen.ifs[0])}"
                consumed = 4
    return _Match("get_json", f"{target} = get_json({url}{where})", consumed, [rname])


def _match_append_stmt(stmt: ast.stmt, gname: str, itname: str):
    """Match ``g.setdefault(it[KEY], []).append(VAL)``.

    Returns (key_src, val) where val is None (whole item) or the field
    expression source, or None if no match.
    """
    if not isinstance(stmt, ast.Expr):
        return None
    call = stmt.value
    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "append"
        and len(call.args) == 1
    ):
        return None
    sd = call.func.value
    if not (
        isinstance(sd, ast.Call)
        and isinstance(sd.func, ast.Attribute)
        and sd.func.attr == "setdefault"
        and _is_name(sd.func.value, gname)
        and len(sd.args) == 2
        and isinstance(sd.args[1], ast.List)
        and not sd.args[1].elts
    ):
        return None
    keyexpr = sd.args[0]
    if not (
        isinstance(keyexpr, ast.Subscript)
        and _is_name(keyexpr.value, itname)
    ):
        return None
    key_src = ast.unparse(keyexpr.slice)
    appended = call.args[0]
    if _is_name(appended, itname):
        return key_src, None
    if isinstance(appended, ast.Subscript) and _is_name(appended.value, itname):
        return key_src, ast.unparse(appended.slice)
    return None


def _match_legacy_append(body: List[ast.stmt], gname: str, itname: str):
    """Match the verbose 3-statement accumulate idiom:

        k = it[KEY]
        if k not in g:
            g[k] = []
        g[k].append(VAL)

    Returns (key_src, val, key_var) or None.
    """
    if len(body) != 3:
        return None
    s0, s1, s2 = body
    if not (
        isinstance(s0, ast.Assign)
        and len(s0.targets) == 1
        and _is_name(s0.targets[0])
        and isinstance(s0.value, ast.Subscript)
        and _is_name(s0.value.value, itname)
    ):
        return None
    kvar = s0.targets[0].id
    key_src = ast.unparse(s0.value.slice)
    # if k not in g: g[k] = []
    if not (
        isinstance(s1, ast.If)
        and not s1.orelse
        and len(s1.body) == 1
        and isinstance(s1.test, ast.Compare)
        and len(s1.test.ops) == 1
        and isinstance(s1.test.ops[0], ast.NotIn)
        and _is_name(s1.test.left, kvar)
        and _is_name(s1.test.comparators[0], gname)
    ):
        return None
    init = s1.body[0]
    if not (
        isinstance(init, ast.Assign)
        and len(init.targets) == 1
        and isinstance(init.targets[0], ast.Subscript)
        and _is_name(init.targets[0].value, gname)
        and _is_name(init.targets[0].slice, kvar)
        and isinstance(init.value, ast.List)
        and not init.value.elts
    ):
        return None
    # g[k].append(VAL)
    if not (
        isinstance(s2, ast.Expr)
        and isinstance(s2.value, ast.Call)
        and isinstance(s2.value.func, ast.Attribute)
        and s2.value.func.attr == "append"
        and isinstance(s2.value.func.value, ast.Subscript)
        and _is_name(s2.value.func.value.value, gname)
        and _is_name(s2.value.func.value.slice, kvar)
        and len(s2.value.args) == 1
    ):
        return None
    appended = s2.value.args[0]
    if _is_name(appended, itname):
        return key_src, None, kvar
    if isinstance(appended, ast.Subscript) and _is_name(appended.value, itname):
        return key_src, ast.unparse(appended.slice), kvar
    return None


def _parse_group_pattern(stmts: List[ast.stmt]) -> Optional[dict]:
    if len(stmts) < 3:
        return None
    # g = {}
    s0 = stmts[0]
    if not (
        isinstance(s0, ast.Assign)
        and len(s0.targets) == 1
        and _is_name(s0.targets[0])
        and isinstance(s0.value, ast.Dict)
        and not s0.value.keys
    ):
        return None
    gname = s0.targets[0].id
    # for it in items: ...
    s1 = stmts[1]
    if not (isinstance(s1, ast.For) and _is_name(s1.target) and not s1.orelse):
        return None
    itname = s1.target.id
    items = ast.unparse(s1.iter)
    body = s1.body
    where = ""
    # Optional filter prefix: `if not COND: continue` / `if COND: continue`
    if (
        body
        and isinstance(body[0], ast.If)
        and not body[0].orelse
        and len(body[0].body) == 1
        and isinstance(body[0].body[0], ast.Continue)
    ):
        test = body[0].test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            cond = ast.unparse(test.operand)
        else:
            cond = f"not ({ast.unparse(test)})"
        where = f", where=lambda {itname}: {cond}"
        body = body[1:]
    # Or wrapping filter: `if COND:` around the whole accumulate body
    elif len(body) == 1 and isinstance(body[0], ast.If) and not body[0].orelse and body[0].body:
        inner = body[0]
        if _match_append_stmt(inner.body[0], gname, itname) or _match_legacy_append(
            inner.body, gname, itname
        ):
            where = f", where=lambda {itname}: {ast.unparse(inner.test)}"
            body = inner.body
    # Accumulate step
    kvar = None
    if len(body) == 1:
        acc = _match_append_stmt(body[0], gname, itname)
        if acc is None:
            return None
        key_src, val = acc
    else:
        acc = _match_legacy_append(body, gname, itname)
        if acc is None:
            return None
        key_src, val, kvar = acc
    # target = {k: FN(v) for k, v in g.items()}  — or  return {...}
    s2 = stmts[2]
    if isinstance(s2, ast.Assign) and len(s2.targets) == 1 and _is_name(s2.targets[0]):
        result_prefix = f"{s2.targets[0].id} = "
        comp = s2.value
    elif isinstance(s2, ast.Return) and s2.value is not None:
        result_prefix = "return "
        comp = s2.value
    else:
        return None
    if not (isinstance(comp, ast.DictComp) and len(comp.generators) == 1):
        return None
    gen = comp.generators[0]
    if not (
        isinstance(gen.target, ast.Tuple)
        and len(gen.target.elts) == 2
        and _is_name(gen.target.elts[0])
        and _is_name(gen.target.elts[1])
        and not gen.ifs
        and _is_attr_call(gen.iter, gname, "items")
        and not gen.iter.args
    ):
        return None
    k_id, v_id = gen.target.elts[0].id, gen.target.elts[1].id
    if not _is_name(comp.key, k_id):
        return None
    agg = comp.value
    if not (isinstance(agg, ast.Call) and _is_name(agg.func) and len(agg.args) == 1 and not agg.keywords):
        return None
    fn = agg.func.id
    arg = agg.args[0]
    if _is_name(arg, v_id):
        pass  # fn(v): val determined by what was appended
    elif (
        val is None
        and isinstance(arg, ast.GeneratorExp)
        and len(arg.generators) == 1
        and _is_name(arg.generators[0].iter, v_id)
        and _is_name(arg.generators[0].target)
        and not arg.generators[0].ifs
        and isinstance(arg.elt, ast.Subscript)
        and _is_name(arg.elt.value, arg.generators[0].target.id)
    ):
        # fn(x[FIELD] for x in v) over whole items == append it[FIELD] + fn(v)
        val = ast.unparse(arg.elt.slice)
    else:
        return None
    internal = [gname, itname, k_id, v_id] + ([kvar] if kvar else [])
    return {
        "items": items,
        "itname": itname,
        "by": key_src,
        "val": val,
        "fn": fn,
        "where": where,
        "result_prefix": result_prefix,
        "internal": internal,
    }


def _group_match_from_parts(parts: dict, consumed: int) -> _Match:
    val_part = f", val={parts['val']}" if parts["val"] is not None else ""
    return _Match(
        "group_agg",
        f"{parts['result_prefix']}group_agg({parts['items']}, "
        f"by={parts['by']}{val_part}, fn={parts['fn']}{parts['where']})",
        consumed,
        parts["internal"],
    )


def _match_group_agg(stmts: List[ast.stmt]) -> Optional[_Match]:
    parts = _parse_group_pattern(stmts)
    if parts is None:
        return None
    return _group_match_from_parts(parts, 3)


def _match_prefiltered_group_agg(stmts: List[ast.stmt]) -> Optional[_Match]:
    """Match a filter comprehension feeding the group pattern:

        adults = [u for u in users if u['age'] > 18]
        grouped = {}
        for user in adults: ...
        result = {k: FN(v) for k, v in grouped.items()}

    Folds the filter into the macro's where= and consumes all 4 statements.
    """
    if len(stmts) < 4:
        return None
    s0 = stmts[0]
    if not (
        isinstance(s0, ast.Assign)
        and len(s0.targets) == 1
        and _is_name(s0.targets[0])
        and isinstance(s0.value, ast.ListComp)
        and len(s0.value.generators) == 1
    ):
        return None
    gen = s0.value.generators[0]
    if not (
        _is_name(gen.target)
        and len(gen.ifs) == 1
        and _is_name(s0.value.elt, gen.target.id)
        and not gen.is_async
    ):
        return None
    filtered_name = s0.targets[0].id
    parts = _parse_group_pattern(stmts[1:])
    if parts is None or parts["items"] != filtered_name:
        return None
    if parts["where"]:
        return None  # combining two filters is out of scope
    # Rename the comprehension variable to the group loop variable
    cond_var, itname = gen.target.id, parts["itname"]

    class Sub(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name):
            if node.id == cond_var:
                return ast.copy_location(ast.Name(id=itname, ctx=node.ctx), node)
            return node

    cond = Sub().visit(copy.deepcopy(gen.ifs[0]))
    parts = dict(parts)
    parts["items"] = ast.unparse(gen.iter)
    parts["where"] = f", where=lambda {itname}: {ast.unparse(cond)}"
    parts["internal"] = parts["internal"] + [filtered_name]
    return _group_match_from_parts(parts, 4)


def _match_csv_rows(stmts: List[ast.stmt]) -> Optional[_Match]:
    w = _single_with(stmts[0])
    if w is None:
        return None
    ctx, fname, body = w
    path = _match_open(ctx, "r", allow_newline=True)
    if path is None or len(body) != 1:
        return None
    inner = body[0]
    if not (isinstance(inner, ast.Assign) and len(inner.targets) == 1 and _is_name(inner.targets[0])):
        return None
    value = inner.value
    # list(csv.DictReader(f))
    if not (
        isinstance(value, ast.Call)
        and _is_name(value.func, "list")
        and len(value.args) == 1
        and not value.keywords
    ):
        return None
    reader = value.args[0]
    if not (
        isinstance(reader, ast.Call)
        and isinstance(reader.func, ast.Attribute)
        and reader.func.attr == "DictReader"
        and _is_name(reader.func.value, "csv")
        and len(reader.args) == 1
        and _is_name(reader.args[0], fname)
        and not reader.keywords
    ):
        return None
    target = inner.targets[0].id
    return _Match("csv_rows", f"{target} = csv_rows({ast.unparse(path)})", 1, [fname])


def _match_run_cmd(stmts: List[ast.stmt]) -> Optional[_Match]:
    s0 = stmts[0]
    if not (isinstance(s0, ast.Assign) and len(s0.targets) == 1 and _is_name(s0.targets[0])):
        return None
    call = s0.value
    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "run"
        and _is_name(call.func.value, "subprocess")
        and len(call.args) == 1
    ):
        return None
    # Exact kwargs required: anything else changes behavior on round-trip
    kwargs = {kw.arg: kw.value for kw in call.keywords}
    if set(kwargs) != {"capture_output", "text", "check"}:
        return None
    if not all(_is_const(kwargs[k], True) for k in ("capture_output", "text", "check")):
        return None
    target = s0.targets[0].id
    return _Match("run_cmd", f"{target} = run_cmd({ast.unparse(call.args[0])})", 1, [])


# Longer patterns first so they win over their sub-patterns
_MATCHERS = [
    _match_jload,
    _match_jsave,
    _match_read_lines,
    _match_csv_rows,
    _match_run_cmd,
    _match_get_json,
    _match_prefiltered_group_agg,
    _match_group_agg,
]


def _free_or_global_names(source: str) -> set:
    """Names read as free/global variables in any nested scope.

    A pattern's internal name (file handle, loop var, ...) leaking into a
    closure or being read as an implicit global elsewhere makes removal
    unsafe.
    """
    unsafe: set = set()

    def rec(table: symtable.SymbolTable, top: bool):
        if not top:
            for sym in table.get_symbols():
                if sym.is_referenced() and (sym.is_free() or sym.is_global()):
                    unsafe.add(sym.get_name())
        for child in table.get_children():
            rec(child, False)

    rec(symtable.symtable(source, "<src>", "exec"), True)
    return unsafe


def _leak_is_read(following: List[ast.stmt], name: str) -> bool:
    """True if ``name`` may be *read* (rather than rebound first) in the
    statements that execute after a matched pattern.

    Statements are examined in order; the first one mentioning the name
    decides. Simple rebinding statements (Assign/With/For) are judged by
    the position of the first occurrence within them; anything more
    complex (conditional rebinds, augmented assignment, del, expressions)
    is conservatively treated as a read.
    """
    for stmt in following:
        mentions = [n for n in ast.walk(stmt) if isinstance(n, ast.Name) and n.id == name]
        if not mentions:
            continue
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # Occurrences in nested scopes are either local there (fine)
            # or free/global — handled by _free_or_global_names.
            continue
        if isinstance(stmt, (ast.Assign, ast.With, ast.For)):
            first = sorted(
                (n.lineno, n.col_offset, isinstance(n.ctx, ast.Store)) for n in mentions
            )[0]
            return not first[2]
        return True
    return False


def compress_macros(source: str) -> Tuple[str, Dict[str, int]]:
    """Rewrite known patterns in ``source`` as macro calls.

    Returns (new_source, stats) where stats maps macro name → rewrite count.
    Unrecognized code is left untouched. If nothing matches, the original
    source is returned verbatim.
    """
    tree = ast.parse(source)
    stats: Dict[str, int] = {}
    scope_unsafe = _free_or_global_names(source)

    def process_body(stmts: List[ast.stmt], following: List[ast.stmt]) -> List[ast.stmt]:
        out: List[ast.stmt] = []
        i = 0
        while i < len(stmts):
            match = None
            for matcher in _MATCHERS:
                m = matcher(stmts[i:])
                if m is None:
                    continue
                rest = stmts[i + m.consumed :] + following
                if any(
                    name in scope_unsafe or _leak_is_read(rest, name)
                    for name in m.internal_names
                ):
                    continue
                match = m
                break
            if match is not None:
                out.extend(ast.parse(match.replacement).body)
                stats[match.macro] = stats.get(match.macro, 0) + 1
                i += match.consumed
            else:
                stmt = stmts[i]
                is_scope = isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                # Locals die with the scope, so a new scope resets `following`
                inner_following = [] if is_scope else stmts[i + 1 :] + following
                for field in ("body", "orelse", "finalbody"):
                    inner = getattr(stmt, field, None)
                    if isinstance(inner, list) and inner and isinstance(inner[0], ast.stmt):
                        setattr(stmt, field, process_body(inner, inner_following))
                out.append(stmt)
                i += 1
        return out

    tree.body = process_body(tree.body, [])
    if not stats:
        return source, stats
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n", stats
