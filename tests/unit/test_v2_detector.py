"""Tests for the VL v2 pattern detector (Python -> macro compression)."""

import os
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from vl.v2 import compress_macros, expand_macros


def _norm(source: str) -> str:
    return textwrap.dedent(source).lstrip()


def _run(source: str, namespace=None):
    ns = dict(namespace or {})
    exec(compile(source, '<test>', 'exec'), ns)
    return ns


def _roundtrip_equiv(source: str, namespace: dict, result_var: str):
    """Original and compress->expand must produce the same result."""
    compressed, stats = compress_macros(source)
    assert stats, f"nothing detected in:\n{source}"
    reexpanded = expand_macros(compressed)
    original_ns = _run(source, namespace)
    roundtrip_ns = _run(reexpanded, namespace)
    assert original_ns[result_var] == roundtrip_ns[result_var]
    return compressed, stats


def test_detects_jload():
    source = _norm(
        """
        import json
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {'jload': 1}
    assert "config = jload('config.json')" in compressed


def test_detects_jsave_with_any_indent():
    source = _norm(
        """
        import json
        with open('out.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {'jsave': 1}
    assert "jsave(results, 'out.json')" in compressed


def test_jload_jsave_roundtrip_behavior(tmp_path):
    path = str(tmp_path / 'd.json')
    source = _norm(
        f"""
        import json
        payload = {{'a': [1, 2]}}
        with open({path!r}, 'w', encoding='utf-8') as f:
            json.dump(payload, f)
        with open({path!r}, 'r', encoding='utf-8') as f:
            result = json.load(f)
        """
    )

    compressed, stats = _roundtrip_equiv(source, {}, 'result')

    assert stats == {'jsave': 1, 'jload': 1}


def test_detects_read_lines_both_variants(tmp_path):
    path = str(tmp_path / 'in.txt')
    (tmp_path / 'in.txt').write_text('a\nb\n')
    for body in (
        "lines = [l.rstrip('\\n') for l in f]",
        "lines = f.read().splitlines()",
    ):
        source = f"with open({path!r}, 'r') as f:\n    {body}\n"

        compressed, stats = _roundtrip_equiv(source, {}, 'lines')

        assert stats == {'read_lines': 1}


def test_detects_group_agg_setdefault_form():
    source = _norm(
        """
        grouped = {}
        for user in users:
            if not (user['age'] > 18):
                continue
            grouped.setdefault(user['country'], []).append(user['revenue'])
        totals = {k: sum(v) for k, v in grouped.items()}
        """
    )
    users = [
        {'country': 'CH', 'age': 30, 'revenue': 100},
        {'country': 'CH', 'age': 10, 'revenue': 999},
        {'country': 'FR', 'age': 40, 'revenue': 50},
    ]

    compressed, stats = _roundtrip_equiv(source, {'users': users}, 'totals')

    assert stats == {'group_agg': 1}
    assert 'group_agg(users' in compressed


def test_detects_group_agg_legacy_readme_form():
    # The verbose idiom from the README, with field extraction in the agg
    source = _norm(
        """
        grouped = {}
        for user in adult_users:
            country = user['country']
            if country not in grouped:
                grouped[country] = []
            grouped[country].append(user)
        result = {k: sum(u['revenue'] for u in v) for k, v in grouped.items()}
        """
    )
    adult_users = [
        {'country': 'CH', 'revenue': 100},
        {'country': 'FR', 'revenue': 50},
        {'country': 'CH', 'revenue': 25},
    ]

    compressed, stats = _roundtrip_equiv(source, {'adult_users': adult_users}, 'result')

    assert stats == {'group_agg': 1}
    assert "val='revenue'" in compressed


def test_detects_group_agg_wrapping_if_filter():
    source = _norm(
        """
        groups = {}
        for row in rows:
            if row['ok']:
                groups.setdefault(row['kind'], []).append(row)
        counts = {k: len(v) for k, v in groups.items()}
        """
    )
    rows = [{'kind': 'a', 'ok': True}, {'kind': 'a', 'ok': False}, {'kind': 'b', 'ok': True}]

    compressed, stats = _roundtrip_equiv(source, {'rows': rows}, 'counts')

    assert stats == {'group_agg': 1}


def test_detects_group_agg_return_form():
    source = _norm(
        """
        def revenue_by_country(orders):
            grouped = {}
            for order in orders:
                country = order['country']
                if country not in grouped:
                    grouped[country] = []
                grouped[country].append(order)
            return {k: sum(o['amount'] for o in v) for k, v in grouped.items()}
        """
    )
    orders = [
        {'country': 'CH', 'amount': 10},
        {'country': 'FR', 'amount': 5},
        {'country': 'CH', 'amount': 1},
    ]

    compressed, stats = compress_macros(source)
    assert stats == {'group_agg': 1}
    assert 'return group_agg(orders' in compressed

    # Round-trip must execute identically
    reexpanded = expand_macros(compressed)
    ns_a = _run(source + "\nresult = revenue_by_country(orders)\n", {'orders': orders})
    ns_b = _run(reexpanded + "\nresult = revenue_by_country(orders)\n", {'orders': orders})
    assert ns_a['result'] == ns_b['result'] == {'CH': 11, 'FR': 5}


def test_detects_get_json_with_filter():
    source = _norm(
        """
        import requests
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        items = resp.json()
        items = [r for r in items if r['status'] == 'active']
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {'get_json': 1}
    assert "items = get_json(url, where=lambda r: r['status'] == 'active')" in compressed


def test_get_json_without_raise_for_status_not_compressed():
    # Compressing would silently add error-raising behavior
    source = _norm(
        """
        import requests
        resp = requests.get(url)
        items = resp.json()
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {}
    assert compressed == source


def test_handle_reused_later_not_compressed():
    # `f` escapes the with block and is used afterwards
    source = _norm(
        """
        import json
        with open('c.json', 'r') as f:
            data = json.load(f)
        print(f.closed)
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {}


def test_different_encoding_not_compressed():
    source = _norm(
        """
        import json
        with open('c.json', 'r', encoding='latin-1') as f:
            data = json.load(f)
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {}


def test_detects_patterns_inside_functions():
    source = _norm(
        """
        import json

        def load_config(path):
            with open(path, 'r') as f:
                cfg = json.load(f)
            return cfg
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {'jload': 1}
    assert 'cfg = jload(path)' in compressed


def test_sibling_patterns_sharing_handle_name_compress():
    # Two with-blocks both using `f` must not block each other
    source = _norm(
        """
        import json
        with open('a.json', 'r') as f:
            a = json.load(f)
        with open('b.json', 'r') as f:
            b = json.load(f)
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {'jload': 2}


def test_closure_reading_handle_not_compressed():
    # A nested function reads `f` as a free/global variable
    source = _norm(
        """
        import json
        with open('c.json', 'r') as f:
            data = json.load(f)

        def status():
            return f.closed
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {}


def test_conditional_rebind_then_read_not_compressed():
    # `f` is only rebound on one branch; the read afterwards may see the handle
    source = _norm(
        """
        import json
        with open('c.json', 'r') as f:
            data = json.load(f)
        if data:
            f = None
        print(f)
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {}


def test_unrelated_code_untouched():
    source = _norm(
        """
        def add(x, y):
            return x + y
        """
    )

    compressed, stats = compress_macros(source)

    assert stats == {}
    assert compressed == source
