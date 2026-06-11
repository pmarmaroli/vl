"""Correctness tests for VL v2 macro expansion: expansions must execute."""

import ast
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import pytest

from vl.v2 import MACRO_SPEC, MACROS, expand_macros
from vl.v2.macros import MacroError


def _run(source: str, namespace=None):
    ns = namespace or {}
    exec(compile(source, '<expanded>', 'exec'), ns)
    return ns


def test_group_agg_expansion_executes():
    source = (
        "totals = group_agg(users, by='country', val='revenue', fn=sum, "
        "where=lambda u: u['age'] > 18)\n"
    )
    users = [
        {'country': 'CH', 'age': 30, 'revenue': 100},
        {'country': 'CH', 'age': 17, 'revenue': 999},
        {'country': 'FR', 'age': 40, 'revenue': 50},
        {'country': 'CH', 'age': 25, 'revenue': 30},
    ]

    expanded = expand_macros(source)
    ns = _run(expanded, {'users': users})

    assert ns['totals'] == {'CH': 130, 'FR': 50}


def test_group_agg_without_val_or_where_collects_items():
    source = "groups = group_agg(rows, by='kind', fn=len)\n"
    rows = [{'kind': 'a'}, {'kind': 'b'}, {'kind': 'a'}]

    ns = _run(expand_macros(source), {'rows': rows})

    assert ns['groups'] == {'a': 2, 'b': 1}


def test_jload_jsave_roundtrip(tmp_path):
    path = tmp_path / 'data.json'
    source = (
        f"jsave({{'x': 1}}, {str(path)!r})\n"
        f"data = jload({str(path)!r})\n"
    )

    expanded = expand_macros(source)
    ns = _run(expanded)

    assert ns['data'] == {'x': 1}
    assert json.loads(path.read_text()) == {'x': 1}
    assert 'import json' in expanded


def test_read_lines_expansion_executes(tmp_path):
    path = tmp_path / 'input.txt'
    path.write_text('alpha\nbeta\n')
    source = f"lines = read_lines({str(path)!r})\n"

    ns = _run(expand_macros(source))

    assert ns['lines'] == ['alpha', 'beta']


def test_get_json_expansion_is_valid_python():
    source = "items = get_json(url, where=lambda r: r['ok'])\n"

    expanded = expand_macros(source)

    ast.parse(expanded)
    assert 'import requests' in expanded
    assert 'raise_for_status' in expanded
    # lambda must be inlined, not called
    assert 'lambda' not in expanded


def test_macros_inside_function_bodies_expand():
    source = (
        "def load(path):\n"
        "    data = jload(path)\n"
        "    return data\n"
    )

    expanded = expand_macros(source)

    assert 'json.load' in expanded
    ast.parse(expanded)


def test_existing_import_not_duplicated():
    source = "import json\nconfig = jload('c.json')\n"

    expanded = expand_macros(source)

    assert expanded.count('import json') == 1


def test_non_macro_code_passes_through():
    source = "def jloader():\n    return 1\nvalue = jloader()\n"

    expanded = expand_macros(source)

    assert 'jloader()' in expanded


def test_return_macro_expands(tmp_path):
    path = tmp_path / 'cfg.json'
    path.write_text('{"k": 7}')
    source = (
        "def load(path):\n"
        "    return jload(path)\n"
    )

    expanded = expand_macros(source)
    ns = _run(expanded)

    assert ns['load'](str(path)) == {'k': 7}


def test_misused_macro_raises():
    with pytest.raises(MacroError):
        expand_macros("jload('x.json')\n")  # missing assignment target


def test_spec_documents_every_macro():
    for name in MACROS:
        assert name in MACRO_SPEC
