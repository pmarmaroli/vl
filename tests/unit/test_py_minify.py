"""Tests for the token-oriented Python minifier."""

import ast
import os
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from vl.py_minify import minify


def _norm(source: str) -> str:
    return textwrap.dedent(source).lstrip()


def test_removes_comments_docstrings_and_blank_lines():
    source = _norm(
        '''
        """Module docstring."""

        # setup
        def total(items):
            """Sum prices."""
            result = 0  # accumulator

            for item in items:
                result += item['price']
            return result
        '''
    )

    out = minify(source)

    assert '"""' not in out
    assert '#' not in out
    assert '\n\n' not in out
    assert "result += item['price']" in out


def test_output_is_semantically_equivalent():
    source = _norm(
        '''
        def f(x):
            """doc"""
            # comment
            return x * 2

        class C:
            """doc"""
            def m(self):
                return f(21)
        '''
    )

    out = minify(source)

    ns_a, ns_b = {}, {}
    exec(compile(source, '<a>', 'exec'), ns_a)
    exec(compile(out, '<b>', 'exec'), ns_b)
    assert ns_a['C']().m() == ns_b['C']().m() == 42


def test_docstring_only_body_gets_pass():
    source = _norm(
        '''
        def noop():
            """Does nothing."""
        '''
    )

    out = minify(source)

    ast.parse(out)
    assert 'pass' in out
    assert 'Does nothing' not in out


def test_multiline_strings_untouched():
    source = 'TEMPLATE = """line1\n\nline2  # not a comment"""\n'

    out = minify(source)

    assert 'line1\n\nline2  # not a comment' in out


def test_hash_inside_string_preserved():
    source = 'url = "https://example.com/#anchor"\n'

    assert minify(source) == source


def test_invalid_python_returned_unchanged():
    source = 'def broken(:\n'

    assert minify(source) == source


def test_keep_docstrings_flag():
    source = _norm(
        '''
        def f():
            """keep me"""
            # but not me
            return 1
        '''
    )

    out = minify(source, keep_docstrings=True)

    assert 'keep me' in out
    assert 'but not me' not in out
