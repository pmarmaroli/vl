"""Token-oriented Python minifier.

Produces Python source that is semantically identical to the input but
cheaper to send to an LLM: comments, docstrings and blank lines are
removed while the code itself is left untouched. Unlike a VL conversion,
the output is plain Python — the model needs no language spec and there
is no correctness risk from an unfamiliar syntax.

Measured with the Mistral Tekken tokenizer (a modern 130k-vocab BPE in
the same family as Claude/GPT tokenizers), this pass alone saves ~20-30%
of tokens on real-world Python files. See docs/token-analysis.md.

The result is verified before being returned: it must parse, and its AST
must match the original AST with docstrings deleted. If verification
fails the original source is returned unchanged.
"""

import argparse
import ast
import io
import sys
import tokenize
from pathlib import Path

# Ensure UTF-8 encoding for stdout/stderr on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")


def _blank_comments(source: str) -> str:
    """Remove comments using the tokenize module (string-literal safe)."""
    lines = source.splitlines(keepends=True)
    if not lines:
        return source
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            line = lines[row - 1]
            ending = "\n" if line.endswith("\n") else ""
            lines[row - 1] = line[:col].rstrip() + ending
    return "".join(lines)


def _protected_lines(source: str) -> set:
    """Line numbers inside multi-line string tokens (must not be touched)."""
    protected: set = set()
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type == tokenize.STRING and tok.end[0] > tok.start[0]:
                # interior lines plus the closing line
                protected.update(range(tok.start[0] + 1, tok.end[0] + 1))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return protected


def _docstring_nodes(tree: ast.Module):
    """Yield (parent, docstring_expr) pairs for every docstring in the tree."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                yield node, body[0]


def _strip_docstrings(source: str) -> str:
    """Remove docstrings by line range, inserting `pass` where required."""
    tree = ast.parse(source)
    lines = source.splitlines()
    drop: set = set()
    insert_pass: dict = {}
    for parent, doc in _docstring_nodes(tree):
        span = range(doc.lineno, doc.end_lineno + 1)
        if len(parent.body) == 1:
            if isinstance(parent, ast.Module):
                continue  # docstring-only module: keep it
            # docstring is the whole body; replace with `pass`
            indent = len(lines[doc.lineno - 1]) - len(lines[doc.lineno - 1].lstrip())
            insert_pass[doc.lineno] = " " * indent + "pass"
        drop.update(span)
    out = []
    for i, line in enumerate(lines, 1):
        if i in insert_pass:
            out.append(insert_pass[i])
        if i in drop:
            continue
        out.append(line)
    return "\n".join(out)


def _expected_tree(source: str) -> str:
    """AST dump of the original with docstrings removed (the minify target)."""
    tree = ast.parse(source)
    for parent, doc in _docstring_nodes(tree):
        if len(parent.body) == 1:
            if isinstance(parent, ast.Module):
                continue
            parent.body[0] = ast.Pass()
        else:
            parent.body.remove(doc)
    return ast.dump(tree)


def minify(source: str, keep_docstrings: bool = False) -> str:
    """Return a token-minified version of ``source``.

    The output is guaranteed semantically equivalent (identical AST, with
    docstrings removed unless ``keep_docstrings``). On any verification
    failure the original source is returned.
    """
    try:
        original_tree = ast.parse(source)
    except SyntaxError:
        return source

    result = _blank_comments(source)
    if not keep_docstrings:
        try:
            result = _strip_docstrings(result)
        except SyntaxError:
            return source
    protected = _protected_lines(result)
    result = "\n".join(
        l for i, l in enumerate(result.splitlines(), 1) if l.strip() or i in protected
    )
    if result and not result.endswith("\n"):
        result += "\n"

    # Verify: must parse and match the expected AST exactly.
    try:
        produced = ast.dump(ast.parse(result))
    except SyntaxError:
        return source
    expected = ast.dump(original_tree) if keep_docstrings else _expected_tree(source)
    if produced != expected:
        return source
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="vl.py_minify",
        description="Minify Python source for LLM token efficiency (semantics preserved)",
    )
    parser.add_argument("input", help="Python file to minify (use - for stdin)")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument(
        "--keep-docstrings", action="store_true", help="Keep docstrings in the output"
    )
    args = parser.parse_args(argv)

    if args.input == "-":
        source = sys.stdin.read()
    else:
        source = Path(args.input).read_text(encoding="utf-8")
    result = minify(source, keep_docstrings=args.keep_docstrings)
    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
